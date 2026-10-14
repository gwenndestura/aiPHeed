"""E26 design calculation (no data of any kind): how strong must the agreement between aiPHeed's ordering and an
authorized local food-insecurity outcome be before a cross-sectional validation can detect it? Synthetic bivariate
normal scores with latent correlation r; one-sided Spearman test at alpha 0.05 (exact permutation for n <= 7,
t approximation otherwise). Not part of the frozen protocol; it sizes the data request in MISSING_OBSERVATIONS_SPEC.md.
Usage: python -B runner/local_power.py   -> runs/local_power.json"""
from __future__ import annotations

import itertools
import math
import json
from pathlib import Path

import numpy as np
from scipy.stats import rankdata, spearmanr, t as tdist

EXP = Path(__file__).resolve().parents[1]
SEED, NSIM, ALPHA = 20261014, 4000, 0.05
UNITS = {"5 provinces": 5, "6 FNRI domains (5 provinces + Lucena City)": 6, "one province's LGUs (about 30)": 30,
         "Quezon's LGUs (40)": 40, "75 LGUs": 75, "all 142 LGUs": 142}
RHOS = [0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]


def exact_null(n):
    base = np.arange(1, n + 1)
    return np.sort([spearmanr(base, p).statistic for p in itertools.permutations(base)])


def pvalue(rs, n, null):
    if null is not None:
        return float(np.mean(null >= rs - 1e-12))
    if rs >= 1:
        return 0.0
    tt = rs * np.sqrt((n - 2) / (1 - rs * rs))
    return float(tdist.sf(tt, n - 2))


def main():
    rng = np.random.default_rng(SEED)
    out = {"alpha_one_sided": ALPHA, "simulations": NSIM, "seed": SEED, "units": {}}
    for label, n in UNITS.items():
        null = exact_null(n) if n <= 7 else None
        row = {"n": n, "smallest_attainable_p": (1 / math.factorial(n)) if n <= 7 else None, "power": {}}
        if null is not None:
            row["spearman_needed_for_p_below_alpha"] = float(min(r for r in np.unique(null) if np.mean(null >= r - 1e-12) < ALPHA))
        for r in RHOS:
            cov = [[1, r], [r, 1]]
            hits = 0
            for _ in range(NSIM):
                x = rng.multivariate_normal([0, 0], cov, size=n)
                rs = float(spearmanr(rankdata(x[:, 0]), rankdata(x[:, 1])).statistic)
                hits += pvalue(rs, n, null) < ALPHA
            row["power"][str(r)] = hits / NSIM
        row["smallest_r_with_80pct_power"] = next((float(r) for r in RHOS if row["power"][str(r)] >= 0.8), None)
        out["units"][label] = row
    (EXP / "runs" / "local_power.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    for k, v in out["units"].items():
        print(k, v["n"], v.get("spearman_needed_for_p_below_alpha"), v["smallest_r_with_80pct_power"],
              {r: round(p, 2) for r, p in v["power"].items()})


if __name__ == "__main__":
    main()
