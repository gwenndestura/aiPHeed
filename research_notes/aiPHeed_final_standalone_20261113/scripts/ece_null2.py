r"""Pass rates of a PERFECTLY calibrated forecaster for the proposed Rule 6 ranges, and the n at which ECE <= 0.05 becomes
attainable (no model output read). Run: python -I ece_null2.py"""
import json
from pathlib import Path
import numpy as np
from calib import ece, slope, intercept

rng = np.random.default_rng(7)
out = {}
for n in (72, 150, 300, 600, 1000):
    E, S, I, M = [], [], [], []
    for _ in range(1000 if n <= 300 else 400):
        p = np.clip(rng.beta(1.4, 2.6, n), 0.01, 0.99)
        y = rng.binomial(1, p)
        E.append(ece(p, y)); S.append(slope(p, y)); I.append(intercept(p, y)); M.append(p.mean() - y.mean())
    E, S, I, M = map(np.array, (E, S, I, M))
    out[n] = {"ECE_p95": round(float(np.percentile(E, 95)), 3), "P(ECE<=0.05)": round(float((E <= 0.05).mean()), 3),
              "P(slope in 0.8-1.2)": round(float(((S >= .8) & (S <= 1.2)).mean()), 3),
              "P(|logit intercept|<=0.10)": round(float((abs(I) <= .1).mean()), 3),
              "P(|mean p - rate|<=0.10)": round(float((abs(M) <= .1).mean()), 3)}
Path(__file__).resolve().parents[1].joinpath("evidence", "P0_threshold_pass_rates_perfect_model.json").write_text(json.dumps(out, indent=1))
print(json.dumps(out, indent=1))
