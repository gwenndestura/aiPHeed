"""
E159 ranking test, per docs/e159/RANKING_TEST_CRITERIA.md (fixed before results).

    python -m app.e159.ranking
"""
from __future__ import annotations

import json
from itertools import combinations

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

from app.paths import BACKEND_DIR

D = BACKEND_DIR / "data"
OUT = D / "e159" / "out"
ARMS = {"E158": "mu_E158", "PERS": "y_anchor"}
CAL = ["Batangas", "Cavite", "Laguna", "Quezon", "Rizal"]
pct = lambda y: 100 / (1 + np.exp(-y))


def pairs(x: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (s, r), g in x.groupby(["survey", "region"]):
        for a, b in combinations(g.index, 2):
            dy = x.at[a, "y_true"] - x.at[b, "y_true"]
            if dy == 0:
                continue
            o = {"cluster": f"{s}|{r}", "survey": s, "region": r, "a": x.at[a, "province"], "b": x.at[b, "province"], "gap_pts": abs(pct(x.at[a, "y_true"]) - pct(x.at[b, "y_true"]))}
            for k, c in ARMS.items():
                d = x.at[a, c] - x.at[b, c]
                o[k] = 0.5 if d == 0 else float(np.sign(d) == np.sign(dy))
            rows.append(o)
    return pd.DataFrame(rows)


def boot_conc(P: pd.DataFrame, rng, n=2000):
    cl = P["cluster"].unique()
    by = {c: P[P["cluster"] == c] for c in cl}
    est = {k: P[k].mean() for k in ARMS} | {"diff": P["E158"].mean() - P["PERS"].mean()}
    bs = {k: [] for k in est}
    for _ in range(n):
        S = pd.concat([by[c] for c in rng.choice(cl, len(cl))])
        for k in ARMS:
            bs[k].append(S[k].mean())
        bs["diff"].append(S["E158"].mean() - S["PERS"].mean())
    return {k: {"est": round(float(est[k]), 3), "ci95": [round(float(np.percentile(bs[k], 2.5)), 3), round(float(np.percentile(bs[k], 97.5)), 3)]} for k in est}


def spear(x: pd.DataFrame):
    return {s: {k: round(float(spearmanr(g[c], g["y_true"]).correlation), 3) for k, c in ARMS.items()} | {"n": int(len(g))} for s, g in x.groupby("survey")}


def run():
    OUT.mkdir(parents=True, exist_ok=True)
    F = pd.read_csv(D / "e158" / "out" / "oof.csv")
    res = {}
    for L in (1, 2, 3, 4):
        x = F[F["lead"] == L].reset_index(drop=True)
        rng = np.random.default_rng(159)
        P = pairs(x)
        big = P[P["gap_pts"] >= 5]
        sp = spear(x)
        r = {"rows": int(len(x)), "pairs": int(len(P)), "concordance": boot_conc(P, rng), "large_gap_pairs": int(len(big)), "concordance_large_gap": boot_conc(big, rng) if len(big) else None, "spearman_by_round": sp, "spearman_mean": {k: round(float(np.mean([v[k] for v in sp.values()])), 3) for k in ARMS}}
        if L == 1:
            P.to_csv(OUT / "pairs_lead1.csv", index=False, lineterminator="\n")
            c = r["concordance"]
            r["R1_within_region"] = c["E158"]["ci95"][0] > 0.5
            r["R2_all_rounds_positive"] = all(v["E158"] > 0 for v in sp.values())
            r["R3_beats_latest_survey"] = c["diff"]["ci95"][0] > 0
            cal = x[x["province"].isin(CAL)].assign(survey_pct=lambda d: pct(d["y_true"]).round(1), e158_pct=lambda d: pct(d["mu_E158"]).round(1), latest_pct=lambda d: pct(d["y_anchor"]).round(1))
            r["calabarzon_rows"] = cal[["survey", "province", "latest_pct", "e158_pct", "survey_pct"]].to_dict("records")
            r["calabarzon_pairs"] = P[P["region"] == "CALABARZON"].round(1).to_dict("records")
        res[f"lead{L}"] = r
    (OUT / "results.json").write_text(json.dumps(res, indent=1, default=float), newline="\n")
    print(json.dumps(res, indent=1, default=float))


if __name__ == "__main__":
    run()
