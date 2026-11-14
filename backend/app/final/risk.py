"""
FOOD INSECURITY RISK of a province for a forecast quarter (methodology decision 2026-11-14, docs/food_insecurity_risk/).

Definition (risk in the epidemiological sense; same construction as FAO's prevalence of undernourishment, which FAO defines as the
probability that a randomly selected individual is undernourished):

    Food insecurity risk = the probability that a randomly selected household in the province is moderately or severely food
    insecure (FNRI Household Food Insecurity Access Scale, HFIAS) in the forecast quarter, given the information published before
    the issue date.

FINAL forecasts the province's HFIAS moderate+severe proportion P on the logit scale: logit(P) ~ Normal(mu, sd^2), where mu is the
mean over the 5 seeds of anchor + elapsed-time x LightGBM rate and sd is the model's own forecast-error scale for that elapsed time
(app.e164.auto.scale). By the law of total probability the risk for a random household is the EXPECTED proportion

    risk = E[P] = integral of sigmoid(z) N(z; mu, sd^2) dz        (Gauss-Hermite quadrature, 64 nodes)

This differs from the previously served value sigmoid(mu), which is the MEDIAN forecast proportion and ignores the forecast
uncertainty. It is not the probability of HIGH (P(P >= 0.5) = Phi(mu / sd)), which answers a different question.

Classification: HIGH RISK when risk >= 0.50. Because the normal is symmetric and sigmoid(-z) = 1 - sigmoid(z), E[P] >= 0.5 exactly
when mu >= 0, so the class is identical to FINAL's validated class (P(HIGH) >= 0.5). Nothing about the model or its classes changes.
"""
from __future__ import annotations

import math

import numpy as np

_X, _W = np.polynomial.hermite.hermgauss(64)
_LOGIT = lambda p: math.log(p / (1 - p))


def expected_risk(mu, sd):
    """E[sigmoid(Z)], Z ~ N(mu, sd^2), elementwise; sd = 0 gives sigmoid(mu)."""
    mu = np.asarray(mu, float)
    sd = np.broadcast_to(np.asarray(sd, float), mu.shape)
    z = mu[..., None] + math.sqrt(2.0) * sd[..., None] * _X
    out = (1.0 / (1.0 + np.exp(-z))) @ _W / math.sqrt(math.pi)
    return float(out) if out.ndim == 0 else out


def sd_from_range(level_pct: float, low_pct: float, high_pct: float) -> float:
    """The forecast sd from a stored 90% range (logit(high) - logit(low) = 2 x 1.645 x sd). Used for ledger records that keep only the
    rounded level and range; issue rows use the exact mu and sd (shap_live_summary.csv)."""
    return (_LOGIT(high_pct / 100) - _LOGIT(low_pct / 100)) / (2 * 1.645)


def risk_from_record(level_pct: float, low_pct: float, high_pct: float) -> float:
    """Risk (0-1) from a ledger record (level and 90% range in %), reproducing the issue value to rounding."""
    return expected_risk(_LOGIT(level_pct / 100), sd_from_range(level_pct, low_pct, high_pct))
