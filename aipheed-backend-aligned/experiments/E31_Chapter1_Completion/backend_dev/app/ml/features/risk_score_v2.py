"""
Candidate risk score "S1" (review candidate; NOT wired into labels, training or the dashboard).

Formula (Equation 3, approved weights, unchanged):
    stress(p,t) = SWS_t + ALPHA * (food_cpi_yoy(p,t) - regional_mean_t),   ALPHA = 2
      SWS_t            Balance-Luzon involuntary-hunger prevalence, % (mean of the quarter's rounds)
      food_cpi_yoy     provincial food CPI year-on-year change, %
      regional_mean_t  mean of the five provinces' food_cpi_yoy in quarter t

What changes relative to app/ml/features/label_generator.py (see
experiments/2026-10-11_devprotocol/SCORING_FORMULA_REPORT.md):
  1. Missing inputs give NaN, never 0.0. label_generator fills a missing CPI value with 0.0,
     which reads "no data" as "0% food inflation" and shifts the regional mean.
  2. The regional mean is defined only when all five provinces have a value for that quarter.
  3. The HIGH/LOW threshold is a FROZEN, POINT-IN-TIME reference: the median stress of the
     labels published before a stated date (as_of). It is not the median of all rows
     (leaky in retrospect) and not a per-fold median (drifting meaning).
     With as_of = 2023-10-01 it is 10.843; with as_of after all 2021-2025 labels are published
     it is the approved 14.345.
  4. HIGH means stress > threshold (strict); stress == threshold is LOW; NaN is "insufficient data".

The threshold is EMPIRICAL (the thesis median rule). It is not an official DA or government cutoff.
"""
from __future__ import annotations

from typing import Callable, Iterable

import numpy as np
import pandas as pd

ALPHA = 2.0
PROVINCES = ("PH040100000", "PH040200000", "PH040300000", "PH040400000", "PH040500000")
MIN_REFERENCE_QUARTERS = 8          # Chapter III Algorithm 3 minimum training window
PROBABILITY_CUTOFF = 0.50           # FIXED operational rule: final probability >= 0.50 -> HIGH
HIGH, LOW = "HIGH", "LOW"
INSUFFICIENT_DATA = "INSUFFICIENT_DATA"
# The latest SWS round is normally 1-2 quarters old at a forecast origin (2021-2025). Older than
# this, the regional hunger input is treated as stale and no forecast is classified.
SWS_MAX_AGE_QUARTERS = 3


class InsufficientReference(ValueError):
    """Too few published, complete quarters to set a reference threshold."""


def compute_stress(sws: pd.DataFrame, cpi: pd.DataFrame) -> pd.DataFrame:
    """
    sws: columns [quarter, sws_hunger_pct] (one row per SWS round; rounds in a quarter are averaged)
    cpi: columns [province_code, quarter, food_cpi_yoy]
    Returns one row per (province_code, quarter) present in `cpi`, with NaN where any input is missing.
    """
    s = sws.copy()
    s["sws_hunger_pct"] = pd.to_numeric(s["sws_hunger_pct"], errors="coerce")
    s = s.groupby("quarter", as_index=False)["sws_hunger_pct"].mean()

    c = cpi[cpi["province_code"].isin(PROVINCES)][["province_code", "quarter", "food_cpi_yoy"]].copy()
    c["food_cpi_yoy"] = pd.to_numeric(c["food_cpi_yoy"], errors="coerce")          # no fillna
    if c.duplicated(["province_code", "quarter"]).any():
        raise ValueError("duplicate province-quarter CPI rows")
    complete = c.groupby("quarter")["food_cpi_yoy"].apply(lambda v: v.notna().sum() == len(PROVINCES))
    reg = c.groupby("quarter")["food_cpi_yoy"].mean().where(complete)                # NaN unless all five present
    c["regional_mean"] = c["quarter"].map(reg)
    c["deviation"] = c["food_cpi_yoy"] - c["regional_mean"]
    out = c.merge(s, on="quarter", how="left")
    out["stress"] = out["sws_hunger_pct"] + ALPHA * out["deviation"]                 # NaN propagates
    return out.sort_values(["quarter", "province_code"]).reset_index(drop=True)


def reference_threshold(stress: pd.DataFrame, published: Callable[[str], pd.Timestamp | None],
                        as_of: pd.Timestamp, min_quarters: int = MIN_REFERENCE_QUARTERS) -> tuple[float, list[str]]:
    """
    Median stress over quarters whose label was published strictly before `as_of`.
    `published(quarter)` returns the label publication date, or None when unknown (then excluded: Rule L4).
    Only quarters with all five provinces scored are used.
    """
    as_of = pd.Timestamp(as_of)
    full = stress.dropna(subset=["stress"]).groupby("quarter").filter(lambda g: len(g) == len(PROVINCES))
    quarters = []
    for q in sorted(full["quarter"].unique()):
        d = published(q)
        if d is not None and pd.Timestamp(d) < as_of:
            quarters.append(q)
    if len(quarters) < min_quarters:
        raise InsufficientReference(f"{len(quarters)} published complete quarters before {as_of.date()} "
                                    f"(< {min_quarters})")
    return float(full[full["quarter"].isin(quarters)]["stress"].median()), quarters


def classify(stress: Iterable[float], threshold: float) -> list[str | None]:
    """HIGH if stress > threshold, LOW if stress <= threshold, None (insufficient data) if missing."""
    if threshold is None or not np.isfinite(threshold):
        raise ValueError("threshold must be a finite number")
    out = []
    for v in stress:
        if v is None or (isinstance(v, float) and np.isnan(v)):
            out.append(None)
        else:
            out.append(HIGH if float(v) > threshold else LOW)
    return out


def classify_probability(p: Iterable[float], cutoff: float = PROBABILITY_CUTOFF) -> list[str | None]:
    """Display label for a model probability of the S1 event: HIGH if p >= cutoff."""
    out = []
    for v in p:
        if v is None or (isinstance(v, float) and np.isnan(v)):
            out.append(None)
        elif not 0.0 <= float(v) <= 1.0:
            raise ValueError(f"probability out of range: {v}")
        else:
            out.append(HIGH if float(v) >= cutoff else LOW)
    return out


# ---------------------------------------------------------------------------
# Decomposition: the regional and provincial parts of the score are reported separately
# ---------------------------------------------------------------------------
def decompose_stress(stress_rows: pd.DataFrame) -> pd.DataFrame:
    """
    Split stress into its two components:
      regional_component   = SWS_t (Balance-Luzon hunger %, ONE value shared by all five provinces)
      provincial_component = ALPHA * deviation (pp of food inflation relative to the five-province mean)
    The provincial components of a complete quarter sum to zero.
    """
    out = stress_rows.copy()
    out["regional_component"] = out["sws_hunger_pct"]
    out["provincial_component"] = ALPHA * out["deviation"]
    return out


# ---------------------------------------------------------------------------
# Supporting provincial food-price evidence (NOT probabilities, NOT food-insecurity measurements)
# ---------------------------------------------------------------------------
def price_pressure_indicators(cpi: pd.DataFrame) -> pd.DataFrame:
    """
    cpi: columns [province_code, quarter, food_cpi (index, 2018=100), food_cpi_yoy (%)]
    Returns, per province-quarter:
      price_index_level     food CPI index: a LEVEL, not current price pressure
      inflation_rate        food CPI year-on-year % (current price pressure)
      inflation_change      inflation_rate minus the previous quarter's (pp): acceleration / deceleration
      relative_pressure     inflation_rate minus the five-province mean (pp); NaN unless all five present
    Missing inputs stay NaN.
    """
    c = cpi[cpi["province_code"].isin(PROVINCES)][["province_code", "quarter", "food_cpi", "food_cpi_yoy"]].copy()
    c["food_cpi"] = pd.to_numeric(c["food_cpi"], errors="coerce")
    c["food_cpi_yoy"] = pd.to_numeric(c["food_cpi_yoy"], errors="coerce")
    c = c.sort_values(["province_code", "quarter"])
    complete = c.groupby("quarter")["food_cpi_yoy"].apply(lambda v: v.notna().sum() == len(PROVINCES))
    reg = c.groupby("quarter")["food_cpi_yoy"].mean().where(complete)
    c["price_index_level"] = c["food_cpi"]
    c["inflation_rate"] = c["food_cpi_yoy"]
    prev = c.groupby("province_code")["food_cpi_yoy"].shift(1)
    prev_q = c.groupby("province_code")["quarter"].shift(1)
    consecutive = prev_q == c["quarter"].map(_previous_quarter)
    c["inflation_change"] = (c["food_cpi_yoy"] - prev).where(consecutive)
    c["relative_pressure"] = c["food_cpi_yoy"] - c["quarter"].map(reg)
    return c.drop(columns=["food_cpi", "food_cpi_yoy"]).reset_index(drop=True)


def _previous_quarter(q: str) -> str:
    y, k = int(q[:4]), int(q[-1])
    return f"{y - 1}-Q4" if k == 1 else f"{y}-Q{k - 1}"


# ---------------------------------------------------------------------------
# Final classification: one rule for the API, the dashboard, reports and tests
# ---------------------------------------------------------------------------
def final_classification(probability: float | None, insufficient_reasons: Iterable[str] = ()) -> str:
    """
    HIGH if the final forecast probability >= 0.50; LOW if < 0.50;
    INSUFFICIENT_DATA if any required input is missing or stale, or the probability itself is missing.
    INSUFFICIENT_DATA is never converted to HIGH or LOW, and missing values are never treated as zero.
    """
    if list(insufficient_reasons):
        return INSUFFICIENT_DATA
    if probability is None or (isinstance(probability, float) and np.isnan(probability)):
        return INSUFFICIENT_DATA
    p = float(probability)
    if not 0.0 <= p <= 1.0:
        raise ValueError(f"probability out of range: {probability}")
    return HIGH if p >= PROBABILITY_CUTOFF else LOW
