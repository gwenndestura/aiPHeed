r"""Candidate-independent check of the proposed calibration thresholds at n = 72 (no model output is read).
A perfectly calibrated forecaster: p ~ Beta(a, b) with mean 0.35 (the HIGH share of the evaluation design: 25 of 72), y ~ Bernoulli(p).
Reports the sampling distribution of ECE (10 equal-width bins), calibration slope and logit intercept. Run: python -I ece_null.py"""
import json
from pathlib import Path
import numpy as np
from calib import ece as _ece, slope as _slope, intercept as _int

rng = np.random.default_rng(20261113)
out = {}
for conc in (2.0, 4.0, 8.0):                       # spread of forecasts: low concentration = more extreme probabilities
    a, b = 0.35 * conc, 0.65 * conc
    E, S, I, M = [], [], [], []
    for _ in range(2000):
        p = np.clip(rng.beta(a, b, 72), 0.01, 0.99)
        y = rng.binomial(1, p)
        E.append(_ece(p, y))
        S.append(_slope(p, y))
        I.append(_int(p, y))
        M.append(p.mean() - y.mean())
    q = lambda v: [round(float(np.percentile(v, x)), 3) for x in (2.5, 50, 97.5)]
    out[f"beta_concentration_{conc}"] = {"ECE_10bin_p2.5_p50_p97.5": q(E), "share_ECE_above_0.05": round(float(np.mean(np.array(E) > 0.05)), 3),
                                          "slope": q(S), "logit_intercept": q(I), "mean_p_minus_rate": q(M)}
Path(__file__).resolve().parents[1].joinpath("evidence", "P0_threshold_sampling_null.json").write_text(json.dumps(out, indent=1))
print(json.dumps(out, indent=1))
