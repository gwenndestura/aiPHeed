"""
v9 Stage 1(c): runs docs/aipheed/v9/STAGE1_CIRCULARITY_PROTOCOL.md (DEVELOPMENT only). Refuses to run if the protocol
file no longer matches its hash. Writes docs/aipheed/v9/results/stage1_*.
"""
from __future__ import annotations

import hashlib
import json
import math
import sys
from pathlib import Path

import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, matthews_corrcoef, roc_auc_score

from app.forecasting.sws import load_rounds, qi, qs
from app.forecasting.v6.lgbm import MAX_ROUNDS, MIN_ROWS, PARAMS, STOP
from app.forecasting.v9 import labels as L

ROOT = Path(__file__).resolve().parents[2]
V9 = ROOT / "docs" / "aipheed" / "v9"
OUT = V9 / "results"
LABELS = {"L-COMP": "L_COMP", "L-SWS": "L_SWS", "L-CPI": "L_CPI"}
FSETS = {"F-ALL": L.PRICE + L.OTHER, "F-NOCPI": L.OTHER}
EVAL_FROM, EVAL_TO = "2024-Q1", "2026-Q3"


def sha_lf(p: Path) -> str:
    return hashlib.sha256(p.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def build(lead: int, t: pd.DataFrame, prices, news, rounds) -> pd.DataFrame:
    rows = []
    have = set(t.quarter)
    for dash in (qs(i) for i in range(qi("2021-Q3"), qi(EVAL_TO) + 2)):
        target = qs(qi(dash) - 1 + lead)
        if target in have:
            rows.append(L.features(dash, lead, prices, news, rounds))
    x = pd.concat(rows, ignore_index=True)
    y = t[["province_code", "quarter", "known", *LABELS.values()]].rename(columns={"quarter": "target"})
    return x.merge(y, on=["province_code", "target"], how="inner")


def fit_predict(train: pd.DataFrame, test: pd.DataFrame, cols: list, ycol: str):
    rate = float(train[ycol].mean()) if len(train) else 0.5
    if len(train) < MIN_ROWS or train[ycol].nunique() < 2:
        return np.full(len(test), rate), 0
    iss = sorted(train.issue.unique())
    inner = train[train.issue.isin(iss[-max(2, math.ceil(0.25 * len(iss))):])]
    early = train[~train.issue.isin(inner.issue.unique())]
    if len(early) < 10 or early[ycol].nunique() < 2:
        return np.full(len(test), rate), 0
    p = {**PARAMS, "objective": "binary"}
    a = lgb.Dataset(early[cols].astype(float), early[ycol].astype(float), free_raw_data=False)
    b = lgb.Dataset(inner[cols].astype(float), inner[ycol].astype(float), reference=a)
    m = lgb.train(p, a, num_boost_round=MAX_ROUNDS, valid_sets=[b], callbacks=[lgb.early_stopping(STOP, verbose=False)])
    best = m.best_iteration or 0
    if best <= 0:
        return np.full(len(test), rate), 0
    final = lgb.train(p, lgb.Dataset(train[cols].astype(float), train[ycol].astype(float)), num_boost_round=best)
    return final.predict(test[cols].astype(float)), best


def metrics(y, p) -> dict:
    y, p = np.asarray(y, float), np.asarray(p, float)
    c = (p >= 0.5).astype(int)
    tp, fp = ((c == 1) & (y == 1)).sum(), ((c == 1) & (y == 0)).sum()
    fn, tn = ((c == 0) & (y == 1)).sum(), ((c == 0) & (y == 0)).sum()
    rec = tp / (tp + fn) if tp + fn else float("nan")
    spec = tn / (tn + fp) if tn + fp else float("nan")
    pre = tp / (tp + fp) if tp + fp else float("nan")
    two = len(set(y)) == 2
    return {"n": len(y), "base_rate": y.mean(), "accuracy": (c == y).mean(), "balanced_accuracy": np.nanmean([rec, spec]),
            "precision": pre, "recall": rec, "f1": 2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else float("nan"),
            "auc": roc_auc_score(y, p) if two else float("nan"),
            "pr_auc": average_precision_score(y, p) if two else float("nan"),
            "mcc": matthews_corrcoef(y, c) if two else float("nan"), "brier": ((p - y) ** 2).mean()}


def block_ci(d: pd.DataFrame, fn, draws=2000, block=3, seed=2026):
    """Moving-block bootstrap over ordered target quarters; d has column target."""
    order = sorted(d.target.unique(), key=qi)
    groups = {q: d[d.target == q] for q in order}
    rng, n, out = np.random.default_rng(seed), len(order), []
    for _ in range(draws):
        pick = []
        while len(pick) < n:
            s = int(rng.integers(0, n - block + 1))
            pick += order[s:s + block]
        v = fn(pd.concat([groups[q] for q in pick[:n]]))
        if v == v:
            out.append(v)
    return (float(np.quantile(out, .025)), float(np.quantile(out, .975))) if out else (float("nan"), float("nan"))


def safe_auc(y, p):
    return roc_auc_score(y, p) if len(set(y)) == 2 else float("nan")


def mechanical(t, prices, sha) -> dict:
    tail = t[t.quarter >= EVAL_FROM]
    mech = {"protocol_sha256_lf": sha, "n_rows": len(t), "quarters": sorted(t.quarter.unique(), key=qi)}
    mech["stress_var_total"] = float(t.stress.var(ddof=0))
    mech["stress_var_between_quarters"] = float(t.groupby("quarter").stress.transform("mean").var(ddof=0))
    mech["stress_var_share_between"] = mech["stress_var_between_quarters"] / mech["stress_var_total"]
    mech["stress_quarter_mean_equals_sws"] = bool(np.allclose(t.groupby("quarter").stress.mean(), t.groupby("quarter").sws.mean()))
    mech["base_rate"] = {k: float(t[v].mean()) for k, v in LABELS.items()}
    mech["base_rate_eval_rows"] = {k: float(tail[v].mean()) for k, v in LABELS.items()}
    mech["base_rate_before_eval_rows"] = {k: float(t[t.quarter < EVAL_FROM][v].mean()) for k, v in LABELS.items()}
    mech["quarters_all_5_same"] = {k: float(t.groupby("quarter")[v].nunique().eq(1).mean()) for k, v in LABELS.items()}
    prev = prices.assign(qi=prices.qi + 1)[["province_code", "qi", "cpi_flag"]].rename(columns={"cpi_flag": "flag_prev"})
    j = prices.merge(prev, on=["province_code", "qi"]).dropna(subset=["flag_prev", "cpi_flag"])
    j["L"] = ((j.cpi_flag == 1) & (j.flag_prev == 1)).astype(int)
    mech["P_LCPI_given_prev_flag_0"] = float(j[j.flag_prev == 0].L.mean())
    mech["P_LCPI_given_prev_flag_1"] = float(j[j.flag_prev == 1].L.mean())
    mech["L_SWS_L_CPI_agreement"] = float((t.L_SWS == t.L_CPI).mean())
    mech["L_SWS_L_CPI_phi"] = float(matthews_corrcoef(t.L_SWS, t.L_CPI))
    mech["L_COMP_L_SWS_agreement"] = float((t.L_COMP == t.L_SWS).mean())
    mech["L_COMP_L_CPI_agreement"] = float((t.L_COMP == t.L_CPI).mean())
    # data/thesis/panel.parquet: is its label_stress the CPI rule (with the 2020 base it was built with)?
    panel = pd.read_parquet(ROOT / "backend" / "data" / "thesis" / "panel.parquet")
    b = pd.read_parquet(L.PROC / "psa_indicators.parquet")
    b = b[b.province_code.isin(L.PROVINCES) & (b.quarter <= L.LAST_DEV_QUARTER)].sort_values(["province_code", "quarter"]).copy()
    g = b.groupby("province_code").food_cpi
    m_ = g.transform(lambda s: s.rolling(24, min_periods=4).mean())
    s_ = g.transform(lambda s: s.rolling(24, min_periods=4).std())
    b["flag"] = (b.food_cpi > m_ + s_).astype(int)
    b["lab"] = ((b.flag == 1) & (b.groupby("province_code").flag.shift(1).fillna(0) == 1)).astype(int)
    c = panel.merge(b[["province_code", "quarter", "lab"]], on=["province_code", "quarter"])
    mech["panel_label_stress_equals_cpi_rule"] = {"rows": len(c), "equal": int((c.label_stress == c.lab).sum()),
                                                  "base_rate_from_2024": float(c[c.quarter >= "2024-Q1"].label_stress.mean())}
    mech["unemployment_quarters_with_provincial_variation"] = int(prices.groupby("quarter").unemployment_rate.nunique().gt(1).sum())
    return mech


def main() -> int:
    expected = (OUT / "STAGE1_PROTOCOL_SHA256.txt").read_text().split()[0]
    got = sha_lf(V9 / "STAGE1_CIRCULARITY_PROTOCOL.md")
    if got != expected:
        print("protocol hash mismatch", got, expected)
        return 2
    # The working tree is shared with another session whose mutation checks edit v6/lgbm.py in place; refuse those params.
    assert PARAMS["num_leaves"] == 4 and PARAMS["max_depth"] == 2 and PARAMS["min_data_in_leaf"] == 10, PARAMS
    t, prices, news, rounds = L.label_table(), L.price_table(), L.news_table(), load_rounds()
    assert t.quarter.nunique() == 17 and len(t) == 85, (t.quarter.nunique(), len(t))
    mech = mechanical(t, prices, got)
    rows, cis, preds = [], [], []
    for lead in (1, 2):
        a = build(lead, t, prices, news, rounds)
        for lname, ycol in LABELS.items():
            te = a[(a.target >= EVAL_FROM) & (a.target <= EVAL_TO)]
            pers = []
            for r in te.itertuples():
                k = t[(t.province_code == r.province_code) & (t.known < r.issue)]
                pers.append(float(k.sort_values("qi")[ycol].iloc[-1]) if len(k) else np.nan)
            te = te.assign(persist=pers)
            ok = te.persist.notna()
            base = {"lead": lead, "label": lname}
            rows.append({**base, "model": "ALWAYS-HIGH", **metrics(te[ycol], np.ones(len(te)))})
            rows.append({**base, "model": "ALWAYS-LOW", **metrics(te[ycol], np.zeros(len(te)))})
            rows.append({**base, "model": "PERSIST", **metrics(te[ok][ycol], te[ok].persist)})
            store = {}
            for fname, cols in FSETS.items():
                ps = []
                for iss in sorted(te.issue.unique()):
                    tr = a[(a.issue < iss) & (a.known < iss)]
                    cur = te[te.issue == iss]
                    p, best = fit_predict(tr, cur, cols, ycol)
                    ps.append(cur[["province_code", "target", ycol]].rename(columns={ycol: "y"}).assign(
                        p=p, best=best, n_train=len(tr), lead=lead, label=lname, fset=fname))
                d = pd.concat(ps, ignore_index=True)
                store[fname] = d
                preds.append(d)
                rows.append({**base, "model": f"LGBM {fname}", **metrics(d.y, d.p),
                             "quarters_with_a_fit": int((d.best > 0).sum() / 5), "quarters": d.target.nunique()})
                for stat, fn in (("auc", lambda x: safe_auc(x.y, x.p)),
                                 ("balanced_accuracy", lambda x: metrics(x.y, x.p)["balanced_accuracy"])):
                    cis.append({**base, "model": fname, "stat": stat, "ci": block_ci(d, fn)})
            m = store["F-ALL"].merge(store["F-NOCPI"], on=["province_code", "target", "y"], suffixes=("_a", "_n"))
            cis.append({**base, "model": "F-ALL minus F-NOCPI", "stat": "auc_diff",
                        "ci": block_ci(m, lambda x: safe_auc(x.y, x.p_a) - safe_auc(x.y, x.p_n))})
    res = pd.DataFrame(rows)
    res.to_csv(OUT / "stage1_label_skill.csv", index=False, float_format="%.4f")
    pd.concat(preds).to_csv(OUT / "stage1_predictions.csv", index=False, float_format="%.5f")
    (OUT / "stage1_mechanical.json").write_text(json.dumps(mech, indent=1, default=str))
    ci = pd.DataFrame([{**{k: v for k, v in c.items() if k != "ci"}, "lo": c["ci"][0], "hi": c["ci"][1]} for c in cis])
    ci.to_csv(OUT / "stage1_ci.csv", index=False, float_format="%.4f")
    print(json.dumps(mech, indent=1, default=str))
    print(res.drop(columns=["pr_auc", "mcc"]).round(3).to_string())
    print(ci.round(3).to_string())
    return 0


if __name__ == "__main__":
    sys.exit(main())
