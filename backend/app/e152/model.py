"""
E152: one locked experiment (docs/e152/PROTOCOL.md). One run only; the score stays HFIAS moderate-or-severe, HIGH at 50.

Adds to the E151 required model: local prices, complete rainfall, their since-survey means, regional means, SWS change since the anchor, and a regional drift term.

    python -m app.e152.model lock | run | live
"""
from __future__ import annotations

import hashlib
import json
import sys
import warnings
from datetime import datetime, timezone

import lightgbm as lgb
import numpy as np
import pandas as pd
from joblib import Parallel, delayed
from scipy.stats import norm
from sklearn.model_selection import GroupKFold

from app.e144 import data as D
from app.e147 import evaluate as E7
from app.e147 import features as Fe
from app.e148 import model as M8
from app.e148 import panel as Pn
from app.e150 import evaluate as Ev
from app.e150 import model as M
from app.e150.issue import expit100
from app.e151 import OUT as OUT51
from app.e151 import prov as Pv
from app.e152.panel import OUT
from app.fi5.target import qindex, qlabel
from app.paths import BACKEND_DIR

warnings.filterwarnings("ignore")
LOCAL = ["l_fg_yoy", "l_rice_yoy", "l_rice_rel", "l_fg_rel", "l_terms", "l_rain3", "l_rain6", "r_fg_yoy", "r_rice_yoy", "r_rain3"]
SINCE = ["l_fg_yoy", "l_rice_yoy", "l_rain3"]
NEW = LOCAL + [c + "_since" for c in SINCE] + ["sws_since"]
ALL = Pv.GNT_COLS + NEW
WEIGHT = [1.0, 0.5]
SHRINK = 3.0
ARMS = {"E152": (ALL, True), "no_drift": (ALL, False), "no_new_inputs": (Pv.GNT_COLS, True), "E151_inputs_cv": (Pv.GNT_COLS, False)}
CAL = ["Batangas", "Cavite", "Laguna", "Quezon", "Rizal"]
FILES = [BACKEND_DIR / "app" / "e152" / "model.py", BACKEND_DIR / "app" / "e152" / "panel.py", BACKEND_DIR.parent / "docs" / "e152" / "PROTOCOL.md", OUT / "local_panel.parquet"]


def _sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def lock():
    (OUT / "lock.json").write_text(json.dumps({"locked_utc": datetime.now(timezone.utc).isoformat(), "hashes": {p.name: _sha(p) for p in FILES}}, indent=1), newline="\n")
    print("locked", {p.name: _sha(p)[:12] for p in FILES})


def _sws():
    s = D.sws_quarterly()
    return s


def add_new(d: pd.DataFrame, L, sw) -> pd.DataFrame:
    """Adds local inputs as of each row's issue quarter. Nothing later than the row's issue quarter is read."""
    d = d.reset_index(drop=True).copy()
    m = d[["key", "i"]].merge(L, left_on=["key", "i"], right_on=["key", "qi"], how="left")
    for c in LOCAL:
        d[c] = m[c].values
    idx = L.set_index(["key", "qi"]).sort_index()
    for c in SINCE:
        vals = []
        for k, a, i in zip(d["key"], d["rq_anchor"], d["i"]):
            v = [idx.at[(k, q), c] for q in range(int(a) + 1, int(i) + 1) if (k, q) in idx.index]
            v = [x for x in v if x == x]
            vals.append(float(np.mean(v)) if v else np.nan)
        d[c + "_since"] = vals
    out = []
    for ar, a, i in zip(d["sws_area"], d["rq_anchor"], d["i"]):
        g = sw[(sw["area"] == ar) & (sw["published"] < Pn.q_start(int(i)))].sort_values("qi")
        g0 = g[g["qi"] <= int(a)]
        out.append(float(Fe._logit(g["hunger"].iloc[-1]) - Fe._logit(g0["hunger"].iloc[-1])) if len(g) and len(g0) else np.nan)
    d["sws_since"] = out
    return d


def drift(tr: pd.DataFrame, te: pd.DataFrame) -> np.ndarray:
    """Regional drift: as-of Lead 1 errors of rounds already released, for provinces in the same region, shrunk, applied only where the province's own last survey is older than that round. Uses released rounds only."""
    r1 = tr[tr["lead"] == 1].copy()
    out = np.zeros(len(te))
    for j, (reg, a) in enumerate(zip(te["region"], te["rq_anchor"])):
        g = r1[(r1["region"] == reg) & (r1["survey"].map(M8.RQ) > int(a))]
        if len(g):
            out[j] = float(g["e"].sum() / (len(g) + SHRINK))
    return out


def fit_arm(tr, cols):
    """Cross-validated LightGBM across regions, trees as in E151; the weight on the adjustment is chosen by soft Brier inside training rows."""
    d = tr.reset_index(drop=True)
    use = [c for c in cols if d[c].notna().any() and d[c].nunique() > 1]
    par = dict(M.PARAMS, monotone_constraints=[Pv.SIGN.get(c, 0) for c in use], monotone_constraints_method="basic", random_state=Pv.SEED)
    w = 1.0 / (d["se_true"] ** 2 + 0.05)
    folds = list(GroupKFold(min(5, d["region"].nunique())).split(d, groups=d["region"]))
    best = (np.inf, None, None)
    for n in Pv.Res2.GRID:
        pred = np.zeros(len(d))
        for a, b in folds:
            pred[b] = lgb.LGBMRegressor(n_estimators=n, **par).fit(d.iloc[a][use], d.iloc[a]["e"], sample_weight=w.iloc[a]).predict(d.iloc[b][use])
        sse = float(np.sum(w * (d["e"] - pred) ** 2))
        if sse < best[0]:
            best = (sse, n, pred.copy())
    n, pred = best[1], best[2]
    scores = {}
    for wt in WEIGHT:
        res = d["e"].values - wt * pred
        p = norm.cdf((d["base"].values + wt * pred) / max(1e-3, np.std(res)))
        scores[wt] = float(np.mean((p - d["q_true"].values) ** 2))
    wt = min(WEIGHT, key=lambda v: round(scores[v], 6))
    res = d["e"].values - wt * pred
    m = lgb.LGBMRegressor(n_estimators=n, **par).fit(d[use], d["e"], sample_weight=w)
    return {"m": m, "use": use, "wt": wt, "n": n, "sd": float(np.std(res)), "half": float(np.quantile(np.abs(res), 0.9)), "cv": scores}


def task(survey, L, sw):
    Fe.LT = 0.0
    M.Hier, M.Store = Pv.Hier2, Pv.Store2
    S = Pv.Store2(None)
    P = M.Pipeline(S, M8.RQ[survey] - 1, Pv.ROUNDS, Pv.ORIGIN[survey])
    tg = Ev.targets_2021(S) if survey == "ENNS2021" else M8.targets(S.s8, [survey])
    te = add_new(Pv.add_inputs(S, M.rows_for(S, tg, [1], Pv.ORIGIN[survey])), L, sw)
    tr = add_new(Pv.add_inputs(S, P.tr), L, sw)
    base, _ = P.hier.predict(te, te["T"].values)
    dr = drift(tr, te)
    o = te[["key", "province", "region", "island", "sws_area", "survey", "T", "lead", "y_anchor", "gap_q"] + [x for x in ("y_true", "se_true", "q_true") if x in te]].copy()
    o["drift"], o["base"] = dr, base
    meta = {}
    for arm, (cols, use_drift) in ARMS.items():
        f = fit_arm(tr, cols)
        mu = base + (dr if use_drift else 0.0) + f["wt"] * f["m"].predict(te[f["use"]])
        o[f"mu_{arm}"], o[arm], o[f"half_{arm}"] = mu, norm.cdf(mu / f["sd"]), f["half"]
        meta[arm] = {"weight": f["wt"], "trees": f["n"], "cv": f["cv"]}
    return o, {"survey": survey, "train_rows": int(len(tr)), "arms": meta, "drift_nonzero": int((dr != 0).sum()), "drift_mean_abs": float(np.abs(dr).mean())}


def rep(g, a, rng):
    g = g.reset_index(drop=True)
    m = Pv.met(g, a)
    y = g["y_high"].values
    d = E7.diff_ci(g, a, "PERS", "q_true", rng, n=2000)
    d2 = E7.diff_ci(g, a, "GNT", "q_true", rng, n=2000)
    sc = Pv.scale_test(g, a, rng, n=2000)
    within = float(np.mean([np.corrcoef(x[f"mu_{a}"], x["y_true"])[0, 1] for _, x in g.groupby("survey")]))
    return {"n": int(len(g)), "n_high": int(y.sum()), "n_correct": int(((g[a] >= .5) == (y == 1)).sum()), "accuracy": m["accuracy"], "balanced": m["balanced_accuracy"], "high_recall": m["recall"], "low_recall": m["low_recall"], "auc": m["auc"], "brier": m["brier"], "mae_points": m["mae_points"], "coverage_90": m["coverage_90"], "confusion": m["confusion"], "majority_rule": float(max(y.mean(), 1 - y.mean())), "share_forecast_high": float((g[a] >= .5).mean()), "within_round_corr": within, "minus_persistence": d, "minus_e151": d2, "slope_ci95": sc["slope_ci95"], "mean_error_ci95": sc["mean_error_ci95"], "may_be_called_prevalence": sc["may_be_called_prevalence"]}


def run():
    lk = json.loads((OUT / "lock.json").read_text())
    bad = [p.name for p in FILES if _sha(p) != lk["hashes"][p.name]]
    if bad:
        raise RuntimeError(f"lock mismatch {bad}")
    if (OUT / "results.json").exists():
        raise SystemExit("this experiment has already run; the protocol allows one")
    L = pd.read_parquet(OUT / "local_panel.parquet")
    sw = _sws()
    out = Parallel(n_jobs=3)(delayed(task)(s, L, sw) for s in ("ENNS2018", "ENNS2019", "ENNS2021"))
    F = Pv.label_2021(pd.concat([a for a, _ in out], ignore_index=True))
    G = pd.read_csv(OUT51 / "prov_oof.csv")
    G = G[G["lead"] == 1][["key", "survey", "PERS", "mu_PERS", "half_PERS", "GNT", "mu_GNT", "half_GNT"]]
    F = F.merge(G, on=["key", "survey"])
    F.to_csv(OUT / "oof.csv", index=False, lineterminator="\n")
    rng = np.random.default_rng(152)
    res = {"status": "one locked experiment; every test row was read by earlier work, and its errors were studied before this design, so it is retrospective", "meta": [x for _, x in out], "arms": {}}
    for a in ARMS:
        res["arms"][a] = {"pool": rep(F, a, rng), "round_2021": rep(F[F["survey"] == "ENNS2021"], a, rng), "round_2018": rep(F[F["survey"] == "ENNS2018"], a, rng), "round_2019": rep(F[F["survey"] == "ENNS2019"], a, rng)}
    (OUT / "results.json").write_text(json.dumps(res, indent=1, default=float), newline="\n")
    print(json.dumps(res, default=float))


def live():
    """Forecast of 2027-Q1, issue 2026-10-01; sealed once. Uses the E152 arm only."""
    Fe.LT = 0.0
    M.Hier, M.Store = Pv.Hier2, Pv.Store2
    ISSUE = qindex("2026-Q4")
    S = Pv.Store2(Pv.target_rows(with_2021=True))
    P = M.Pipeline(S, ISSUE, Pv.ROUNDS, "F")
    L, sw = pd.read_parquet(OUT / "local_panel.parquet"), _sws()
    tr = add_new(Pv.add_inputs(S, P.tr), L, sw)
    b = S.base.drop_duplicates("key")
    five = b[b["province"].isin(CAL)]
    te = add_new(Pv.add_inputs(S, M.rows_for(S, five.assign(T=ISSUE + 1, survey="LIVE").drop(columns=["y", "se_y", "q_high", "p"]), [1], "F")), L, sw)
    base, _ = P.hier.predict(te, te["T"].values)
    dr = drift(tr, te)
    f = fit_arm(tr, ALL)
    mu = base + dr + f["wt"] * f["m"].predict(te[f["use"]])
    rows = [{"province": te["province"].iloc[k], "target_quarter": qlabel(ISSUE + 1), "latest_survey": round(float(expit100(te["y_anchor"].iloc[k])), 1), "drift_logit": round(float(dr[k]), 3), "score": round(float(expit100(mu[k])), 1), "low90": round(float(expit100(mu[k] - f["half"])), 1), "high90": round(float(expit100(mu[k] + f["half"])), 1), "p_high": round(float(norm.cdf(mu[k] / f["sd"])), 3), "class": "HIGH" if mu[k] >= 0 else "LOW"} for k in range(len(te))]
    C = np.abs(f["m"].booster_.predict(tr[f["use"]], pred_contrib=True)[:, :-1]).mean(axis=0)
    from app.e151.issue import group_of
    gs = {}
    for nm, v in zip(f["use"], C):
        g = "local_new" if nm in NEW else group_of(nm)
        gs[g] = gs.get(g, 0.0) + float(v)
    tot = sum(gs.values()) or 1.0
    out = {"weight": f["wt"], "trees": f["n"], "forecasts": rows, "shap_share": {k: round(v / tot, 4) for k, v in sorted(gs.items(), key=lambda t: -t[1])}, "top_inputs": sorted(zip(f["use"], [round(float(x), 4) for x in C]), key=lambda t: -t[1])[:12]}
    (OUT / "live.json").write_text(json.dumps(out, indent=1, default=float), newline="\n")
    s = OUT / "sealed_2027-Q1.json"
    if not s.exists():
        s.write_text(json.dumps({"sealed_utc": datetime.now(timezone.utc).isoformat(), **out}, indent=1, default=float), newline="\n")
    print("seal", _sha(s))
    print(json.dumps(out, default=float))


if __name__ == "__main__":
    {"lock": lock, "run": run, "live": live}[sys.argv[1]]()
