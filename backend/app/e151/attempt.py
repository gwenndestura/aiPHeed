"""
E151 one locked improvement attempt (deviation D5). One run only.

Every choice for a target round is made inside that round's training rows, by cross-validation across regions, on rounds released before the issue date. The target round's outcomes play no part.
Candidates: input set (required, government, market + climate + poverty, the last with overall news), weight on the LightGBM adjustment (1 or 0.5), correction of mean training error (no or yes).
Rule: lowest soft Brier in cross-validation; ties go to the earlier candidate in the list.

    python -m app.e151.attempt lock | run -> data/e151/out/attempt_lock.json, attempt_results.json, attempt_oof.csv
"""
from __future__ import annotations

import hashlib
import json
import sys
import warnings
from datetime import datetime, timezone
from itertools import product

import lightgbm as lgb
import numpy as np
import pandas as pd
from joblib import Parallel, delayed
from scipy.stats import norm
from sklearn.model_selection import GroupKFold

from app.e147 import evaluate as E7
from app.e147 import features as Fe
from app.e148 import model as M8
from app.e150 import evaluate as Ev
from app.e150 import model as M
from app.e151 import OUT
from app.e151 import prov as Pv
from app.paths import BACKEND_DIR

warnings.filterwarnings("ignore")
G3 = [c for g in ("market", "climate", "poverty") for c in M.GROUPS[g]] + ["gap_q", "lead"]
SETS = {"required": Pv.GNT_COLS, "government": Pv.GOV_COLS, "three_groups": G3, "three_groups_overall_news": G3 + Pv.NEWS_OVERALL}
WEIGHT = [1.0, 0.5]
BIAS = [False, True]
FILES = [BACKEND_DIR / "app" / "e151" / "attempt.py", BACKEND_DIR.parent / "docs" / "e151" / "PROTOCOL.md"]


def _sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def lock():
    (OUT / "attempt_lock.json").write_text(json.dumps({"locked_utc": datetime.now(timezone.utc).isoformat(), "hashes": {p.name: _sha(p) for p in FILES}, "candidates": {"sets": list(SETS), "weight": WEIGHT, "bias": BIAS}}, indent=1), newline="\n")
    print("locked")


def _cv(tr, cols):
    """Out-of-fold LightGBM adjustments across regions, trees chosen as in Res2, plus the fold ids."""
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
    fid = np.zeros(len(d), int)
    for k, (_, b) in enumerate(folds):
        fid[b] = k
    return use, par, best[1], best[2], fid


def task(survey):
    Fe.LT = 0.0
    M.Hier, M.Store = Pv.Hier2, Pv.Store2
    S = Pv.Store2(None)
    i = M8.RQ[survey] - 1
    P = M.Pipeline(S, i, Pv.ROUNDS, Pv.ORIGIN[survey])
    tg = Ev.targets_2021(S) if survey == "ENNS2021" else M8.targets(S.s8, [survey])
    te = Pv.add_inputs(S, M.rows_for(S, tg, [1], Pv.ORIGIN[survey]))
    tr = Pv.add_inputs(S, P.tr).reset_index(drop=True)
    base_te, _ = P.hier.predict(te, te["T"].values)
    fits, rank = {}, []
    y, q = tr["e"].values, tr["q_true"].values
    tb = tr["base"].values
    for name, cols in SETS.items():
        fits[name] = _cv(tr, cols)
        _, _, _, pred, fid = fits[name]
        for wt, bias in product(WEIGHT, BIAS):
            # bias correction for a fold uses only the other folds
            adj = np.array([np.mean((y - wt * pred)[fid != f]) if bias else 0.0 for f in fid])
            res = y - wt * pred - adj
            p = norm.cdf((tb + wt * pred + adj) / max(1e-3, np.std(res)))
            rank.append({"set": name, "weight": wt, "bias": bias, "cv_soft_brier": float(np.mean((p - q) ** 2)), "cv_rmse": float(np.sqrt(np.mean(res ** 2)))})
    R = pd.DataFrame(rank)
    pick = R.loc[R["cv_soft_brier"].round(6).idxmin()].to_dict()
    use, par, n, pred, _ = fits[pick["set"]]
    w = 1.0 / (tr["se_true"] ** 2 + 0.05)
    m = lgb.LGBMRegressor(n_estimators=n, **par).fit(tr[use], tr["e"], sample_weight=w)
    c = float(np.mean(y - pick["weight"] * pred)) if pick["bias"] else 0.0
    res = y - pick["weight"] * pred - c
    o = te[["key", "province", "region", "island", "sws_area", "survey", "T", "lead", "y_anchor", "gap_q"] + [x for x in ("y_true", "se_true", "q_true") if x in te]].copy()
    o["mu_A"] = base_te + pick["weight"] * m.predict(te[use]) + c
    o["A"], o["half_A"] = norm.cdf(o["mu_A"] / float(np.std(res))), float(np.quantile(np.abs(res), 0.9))
    return o, {"survey": survey, "pick": pick, "train_rows": int(len(tr)), "grid": R.round(5).to_dict(orient="records")}


def run():
    lk = json.loads((OUT / "attempt_lock.json").read_text())
    bad = [p.name for p in FILES if _sha(p) != lk["hashes"][p.name]]
    if bad:
        raise RuntimeError(f"lock mismatch {bad}")
    if (OUT / "attempt_results.json").exists():
        raise SystemExit("this attempt has already run; the protocol allows one")
    out = Parallel(n_jobs=3)(delayed(task)(s) for s in ("ENNS2018", "ENNS2019", "ENNS2021"))
    F = Pv.label_2021(pd.concat([a for a, _ in out], ignore_index=True))
    G = pd.read_csv(OUT / "prov_oof.csv")
    G = G[G["lead"] == 1][["key", "survey", "PERS", "mu_PERS", "half_PERS", "GNT", "mu_GNT", "half_GNT"]]
    F = F.merge(G, on=["key", "survey"])
    F.to_csv(OUT / "attempt_oof.csv", index=False, lineterminator="\n")
    rng = np.random.default_rng(151)
    def rep(g):
        g = g.reset_index(drop=True)
        m = Pv.met(g, "A")
        y = g["y_high"].values
        d = E7.diff_ci(g, "A", "PERS", "q_true", rng, n=2000)
        d2 = E7.diff_ci(g, "A", "GNT", "q_true", rng, n=2000)
        sc = Pv.scale_test(g, "A", rng, n=2000)
        return {"n": int(len(g)), "n_high": int(y.sum()), "n_correct": int(((g["A"] >= .5) == (y == 1)).sum()), "accuracy": m["accuracy"], "balanced": m["balanced_accuracy"], "high_recall": m["recall"], "low_recall": m["low_recall"], "auc": m["auc"], "brier": m["brier"], "mae_points": m["mae_points"], "coverage_90": m["coverage_90"], "confusion": m["confusion"], "majority_rule": float(max(y.mean(), 1 - y.mean())), "share_forecast_high": float((g["A"] >= .5).mean()), "minus_persistence": d, "minus_required_model": d2, "slope_ci95": sc["slope_ci95"], "mean_error_ci95": sc["mean_error_ci95"], "may_be_called_prevalence": sc["may_be_called_prevalence"]}
    res = {"status": "one locked attempt; every row was read by earlier work, so this is retrospective", "picks": [{k: v for k, v in x.items() if k != "grid"} for _, x in out], "pool": rep(F), "round_2021": rep(F[F["survey"] == "ENNS2021"]), "round_2018": rep(F[F["survey"] == "ENNS2018"]), "round_2019": rep(F[F["survey"] == "ENNS2019"]), "grids": {x["survey"]: x["grid"] for _, x in out}}
    (OUT / "attempt_results.json").write_text(json.dumps(res, indent=1, default=float), newline="\n")
    print(json.dumps({k: v for k, v in res.items() if k != "grids"}, indent=0, default=float))
    print(F[F["region"] == "CALABARZON"][["province", "survey", "y_high", "A"]].round(3).to_string())


if __name__ == "__main__":
    {"lock": lock, "run": run}[sys.argv[1]]()
