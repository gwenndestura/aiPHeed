r"""Paired comparison of FINAL (5-seed mean, parts_lead) with the stored baselines of the E158 label table on identical rows, per lead:
PERS (latest survey), GNT, PSA (PSA-only), LR, LR_NEWS, NEWS. Brier difference with 95 % province-round bootstrap interval; balanced
accuracy. Retrospective, reused rows. Run: python -I baselines.py"""
import glob, json
from pathlib import Path
import numpy as np, pandas as pd
HERE = Path(__file__).resolve().parents[1]
LAB = pd.read_csv("C:/Users/admin/aipheed_e145/backend/data/e158/out/oof.csv")
B = [c for c in ("PERS", "GNT", "PSA", "LR", "LR_NEWS", "NEWS") if c in LAB]
F = pd.concat([pd.read_csv(f) for f in glob.glob(str(HERE / "parts_lead" / "FINALL__*.csv"))]).groupby(["key", "survey", "lead"], as_index=False)["p"].mean()
M = F.merge(LAB[["key", "survey", "lead", "y_high"] + B], on=["key", "survey", "lead"])
rng = np.random.default_rng(7)
ba = lambda p, y: 0.5 * (((p >= .5) & (y == 1)).sum() / (y == 1).sum() + ((p < .5) & (y == 0)).sum() / (y == 0).sum())
rows = []
for L, g in M.groupby("lead"):
    y = g.y_high.values
    for b in B:
        x = g[g[b].notna()]
        if len(x) < 20:
            continue
        d = (x.p - x.y_high) ** 2 - (x[b] - x.y_high) ** 2
        bs = [d.values[rng.integers(0, len(d), len(d))].mean() for _ in range(4000)]
        rows.append({"lead": L, "baseline": b, "n": len(x), "FINAL_BA": round(ba(x.p.values, x.y_high.values), 3), "baseline_BA": round(ba(x[b].values, x.y_high.values), 3),
                     "brier_FINAL_minus_baseline": round(float(d.mean()), 4), "ci95": [round(float(np.percentile(bs, 2.5)), 4), round(float(np.percentile(bs, 97.5)), 4)],
                     "FINAL_better_significant": bool(np.percentile(bs, 97.5) < 0)})
T = pd.DataFrame(rows)
T.to_csv(HERE / "evidence" / "LEAD_baselines_paired.csv", index=False)
print(T.to_string(index=False))
