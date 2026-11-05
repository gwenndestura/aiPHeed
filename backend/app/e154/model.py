"""
E154: 11 meaningful inputs, one-split trees, no tuning at all (docs/e154/PROTOCOL.md). One locked run.

    python -m app.e154.model lock | run
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

from app.e147 import evaluate as E7
from app.e147 import features as Fe
from app.e148 import model as M8
from app.e150 import evaluate as Ev
from app.e150 import model as M
from app.e151 import OUT as OUT51
from app.e151 import prov as Pv
from app.paths import BACKEND_DIR

warnings.filterwarnings("ignore")
ROOT = BACKEND_DIR / "data" / "e154"
OUT, RAW = ROOT / "out", ROOT / "raw"
INPUTS = {"market": ["cpi_since", "cpi_food_rel_nat"], "climate": ["soil_since", "rain_since", "agri_since", "tc_rate_since"], "employment": ["unemp_chg_since", "income_growth"], "remittance": ["remit_since"], "poverty": ["p_poverty", "income_rel"]}
COLS = [c for g in INPUTS.values() for c in g]
SIGNS = {**Pv.SIGN, "income_growth": -1, "income_rel": -1, "cpi_food_rel_nat": 1, "p_poverty": 1}
PAR = dict(objective="regression", n_estimators=200, learning_rate=0.02, num_leaves=2, max_depth=1, min_child_samples=20, reg_lambda=20.0, subsample=0.8, subsample_freq=1, colsample_bytree=0.8, n_jobs=1, verbose=-1)
SEEDS, SHUFFLES, LEADS = 10, 100, [1, 2, 3, 4]
REG = {"National Capital": "NCR", "(CAR)": "CAR", "Ilocos": "Ilocos", "Cagayan Valley": "Cagayan Valley", "Central Luzon": "Central Luzon", "CALABARZON": "CALABARZON", "MIMAROPA": "MIMAROPA", "Bicol": "Bicol", "Western Visayas": "Western Visayas", "Central Visayas": "Central Visayas", "Eastern Visayas": "Eastern Visayas", "Zamboanga": "Zamboanga Peninsula", "Northern Mindanao": "Northern Mindanao", "Davao": "Davao", "SOCCSKSARGEN": "SOCCSKSARGEN", "Caraga": "Caraga", "BARMM": "ARMM"}
FILES = [BACKEND_DIR / "app" / "e154" / "model.py", BACKEND_DIR.parent / "docs" / "e154" / "PROTOCOL.md", RAW / "regional_income_long.csv"]


def _sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def lock():
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "lock.json").write_text(json.dumps({"locked_utc": datetime.now(timezone.utc).isoformat(), "hashes": {p.name: _sha(p) for p in FILES}}, indent=1), newline="\n")
    print("locked", {p.name: _sha(p)[:12] for p in FILES})


def income() -> pd.DataFrame:
    t = pd.read_csv(RAW / "regional_income_long.csv")
    t = t[(t["table"] == "hfce_pc") & t["type of valuation"].str.contains("Constant")].copy()
    t["reg"] = t["region"].map(lambda s: next((v for k, v in REG.items() if k in s), None))
    return t.dropna(subset=["reg"]).pivot_table(index="year", columns="reg", values="value").pipe(np.log)


def available_year(i: int) -> int:
    """Regional accounts for year Y are assumed public from Q3 of Y + 1."""
    y, q = i // 4, i % 4 + 1
    return y - 1 if q >= 3 else y - 2


def add_income(d: pd.DataFrame, H: pd.DataFrame) -> pd.DataFrame:
    d = d.reset_index(drop=True).copy()
    g, r = [], []
    for reg, a, i in zip(d["region"], d["rq_anchor"], d["i"]):
        y = available_year(int(i))
        if reg not in H.columns or y not in H.index:
            g.append(np.nan)
            r.append(np.nan)
            continue
        a_y = min(int(a) // 4, y)
        g.append(float((H.at[y, reg] - H.at[a_y, reg]) / max(1, y - a_y)) if a_y in H.index else np.nan)
        r.append(float(H.at[y, reg] - H.loc[y].mean()))
    d["income_growth"], d["income_rel"] = g, r
    return d


def fit_predict(tr, te, y=None, seeds=SEEDS):
    use = [c for c in COLS if tr[c].notna().any() and tr[c].nunique() > 1]
    w = 1.0 / (tr["se_true"] ** 2 + 0.05)
    t = tr["e"] if y is None else pd.Series(y, index=tr.index)
    par = dict(PAR, monotone_constraints=[SIGNS.get(c, 0) for c in use], monotone_constraints_method="basic")
    ms = [lgb.LGBMRegressor(**par, random_state=154 + s).fit(tr[use], t, sample_weight=w) for s in range(seeds)]
    return np.mean([m.predict(te[use]) for m in ms], axis=0), np.mean([m.predict(tr[use]) for m in ms], axis=0), ms[0], use


def task(survey, H):
    Fe.LT = 0.0
    M.Hier, M.Store = Pv.Hier2, Pv.Store2
    S = Pv.Store2(None)
    out = []
    nulls = {}
    tg0 = Ev.targets_2021(S) if survey == "ENNS2021" else M8.targets(S.s8, [survey])
    meta = {}
    for h in LEADS:
        i = M8.RQ[survey] - h
        if not M.released(i, Pv.ROUNDS):
            continue
        P = M.Pipeline(S, i, Pv.ROUNDS, Pv.ORIGIN[survey])
        tr = add_income(Pv.add_inputs(S, P.tr), H)
        te = add_income(Pv.add_inputs(S, M.rows_for(S, tg0, [h], Pv.ORIGIN[survey])), H)
        base, _ = P.hier.predict(te, te["T"].values)
        pte, ptr, _m, use = fit_predict(tr, te)
        res = tr["e"].values - ptr
        # the honest error size comes from leaving each round out, not from in-sample fit
        oof = np.zeros(len(tr))
        s = tr["survey"].values
        groups = [(np.where(s != u)[0], np.where(s == u)[0]) for u in pd.unique(s)] if pd.Series(s).nunique() >= 2 else [(np.where(tr["region"].values != r)[0], np.where(tr["region"].values == r)[0]) for r in pd.unique(tr["region"])]
        for a, b in groups:
            oof[b] = fit_predict(tr.iloc[a], tr.iloc[b], seeds=2)[0]
        r_o = tr["e"].values - oof
        sd, half = float(np.std(r_o)), float(np.quantile(np.abs(r_o), 0.9))
        o = te[["key", "province", "region", "island", "sws_area", "survey", "T", "lead", "y_anchor", "gap_q", "i"] + [x for x in ("y_true", "se_true", "q_true") if x in te] + ["income_growth", "income_rel"]].copy()
        o["mu_ANCHOR2"], o["ANCHOR2"] = base, norm.cdf(base / P.sigma_base)
        lvl = float(np.mean(tr["e"]))
        o["mu_LEVEL"], o["LEVEL"], o["half_LEVEL"] = base + lvl, norm.cdf((base + lvl) / float(np.std(tr["e"]))), float(np.quantile(np.abs(tr["e"] - lvl), 0.9))
        o["mu_E154"], o["E154"], o["half_E154"] = base + pte, norm.cdf((base + pte) / sd), half
        out.append(o)
        if h == 1:
            meta = {"survey": survey, "train_rows": int(len(tr)), "in_sample_mse": float(np.mean(res ** 2)), "held_out_mse": float(np.mean(r_o ** 2)), "overfit_ratio": float(np.mean(r_o ** 2) / np.mean(res ** 2)), "used": use}
            r = np.random.default_rng(154)
            nl = []
            for _ in range(SHUFFLES):
                y = tr["e"].copy().values
                for _, ix in tr.groupby(["survey", "lead"]).indices.items():
                    y[ix] = r.permutation(y[ix])
                nl.append(base + fit_predict(tr, te, y=y, seeds=1)[0])
            nulls = {"key": te["key"].values, "mu": np.array(nl)}
    return pd.concat(out, ignore_index=True), meta, nulls


def run():
    lk = json.loads((OUT / "lock.json").read_text())
    bad = [p.name for p in FILES if _sha(p) != lk["hashes"][p.name]]
    if bad:
        raise RuntimeError(f"lock mismatch {bad}")
    if (OUT / "results.json").exists():
        raise SystemExit("this experiment has already run; the protocol allows one")
    H = income()
    R = Parallel(n_jobs=3)(delayed(task)(s, H) for s in ("ENNS2018", "ENNS2019", "ENNS2021"))
    F = Pv.label_2021(pd.concat([a for a, _, _ in R], ignore_index=True))
    G = pd.read_csv(OUT51 / "prov_oof.csv")[["key", "survey", "lead", "PERS", "mu_PERS", "half_PERS", "GNT", "mu_GNT", "half_GNT", "mu_ANCHOR", "ANCHOR"]]
    F = F.merge(G, on=["key", "survey", "lead"])
    F.to_csv(OUT / "oof.csv", index=False, lineterminator="\n")
    rng = np.random.default_rng(154)
    def rep(g, a):
        g = g.reset_index(drop=True)
        m = Pv.met(g, a)
        y = g["y_high"].values
        sc = Pv.scale_test(g, a, rng, n=2000) if f"half_{a}" in g else {}
        return {"n": int(len(g)), "n_high": int(y.sum()), "n_correct": int(((g[a] >= .5) == (y == 1)).sum()), "accuracy": m["accuracy"], "balanced": m["balanced_accuracy"], "high_recall": m["recall"], "low_recall": m["low_recall"], "auc": m["auc"], "brier": m["brier"], "mae_points": m["mae_points"], "coverage_90": m.get("coverage_90"), "confusion": m["confusion"], "majority_rule": float(max(y.mean(), 1 - y.mean())), "share_high": float((g[a] >= .5).mean()), "within_round_corr": float(np.mean([np.corrcoef(x[f"mu_{a}"], x["y_true"])[0, 1] for _, x in g.groupby("survey")])), "minus_persistence": E7.diff_ci(g, a, "PERS", "q_true", rng, n=2000), "minus_e151": E7.diff_ci(g, a, "GNT", "q_true", rng, n=2000), "minus_level": E7.diff_ci(g, a, "LEVEL", "q_true", rng, n=2000) if a != "LEVEL" else None, "slope_ci95": sc.get("slope_ci95"), "mean_error_ci95": sc.get("mean_error_ci95"), "may_be_called_prevalence": sc.get("may_be_called_prevalence")}
    x = F[F["lead"] == 1]
    res = {"status": "one locked run, no tuning; fifth look at these rows; retrospective", "meta": [m for _, m, _ in R], "by_lead": {}}
    for h in LEADS:
        g = F[F["lead"] == h]
        res["by_lead"][f"L{h}"] = {a: rep(g, a) for a in ("E154", "LEVEL", "GNT")}
    for s in ("ENNS2018", "ENNS2019", "ENNS2021"):
        res["L1_" + s] = {a: rep(x[x["survey"] == s], a) for a in ("E154", "LEVEL", "GNT")}
    # shuffled inputs, pool
    acc = np.zeros(SHUFFLES)
    for _, _, n in R:
        lab = x.set_index("key")
        for j, k in enumerate(n["key"]):
            pass
    tot = 0
    for (_, m, n) in R:
        lab = x[x["survey"] == m["survey"]].set_index("key").reindex(n["key"])
        ok = lab["y_high"].notna().values
        acc += ((n["mu"][:, ok] >= 0) == (lab["y_high"].values[ok] == 1)).sum(axis=1)
        tot += int(ok.sum())
    acc /= tot
    real = res["by_lead"]["L1"]["E154"]["accuracy"]
    res["shuffled_input_null_L1"] = {"mean": float(acc.mean()), "p95": float(np.percentile(acc, 95)), "share_at_or_above_real": float(np.mean(acc >= real)), "n_rows": tot}
    p = res["by_lead"]["L1"]["E154"]
    res["adopt"] = bool(p["accuracy"] >= 0.75 and p["brier"] <= res["by_lead"]["L1"]["GNT"]["brier"] and real > res["shuffled_input_null_L1"]["p95"])
    (OUT / "results.json").write_text(json.dumps(res, indent=1, default=float), newline="\n")
    print(json.dumps(res, default=float)[:300])


if __name__ == "__main__":
    {"lock": lock, "run": run}[sys.argv[1]]()
