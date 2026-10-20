"""E73: scoring pipeline for a prospective quarterly provincial household FIES survey, the direct outcome aiPHeed
lacks (FOOD_INSECURITY_DIMENSIONAL_FRAMEWORK_AND_VALIDATION_PROTOCOL.md section 6). No survey has been conducted; the
functions below are tested on SYNTHETIC responses only.

Instrument: the eight FAO FIES items (Ballard, Kepple and Cafiero 2013), 12-month or 30-day recall fixed per round
(aiPHeed uses 3-month recall to match the quarter), yes = 1, no = 0, don't know / refused = missing.
Classification here is the raw-score approximation (moderate or severe: raw score >= 4; severe: >= 7). The official
estimate must use the FAO Rasch model with equating to the FIES global standard (FAO RM.weights / FIES app); the raw-score
figures are for operational monitoring only and are labelled as such.
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd

ITEMS = ["WORRIED", "HEALTHY", "FEWFOOD", "SKIPPED", "ATELESS", "RANOUT", "HUNGRY", "WHLDAY"]
REQUIRED = ["household_id", "province_code", "lgu_code", "quarter", "interview_date", "weight", "cluster_id"] + ITEMS
MOD_SEV, SEVERE = 4, 7
DETERIORATION_POINTS = 5.0


def validate(df: pd.DataFrame) -> list[str]:
    errs = [f"missing column {c}" for c in REQUIRED if c not in df.columns]
    if errs:
        return errs
    for c in ITEMS:
        bad = ~df[c].isin([0, 1]) & df[c].notna()
        if bad.any():
            errs.append(f"{c}: {int(bad.sum())} values not in {{0, 1, missing}}")
    if (df["weight"] <= 0).any():
        errs.append("non-positive weights")
    if df["household_id"].duplicated().any():
        errs.append("duplicate household_id")
    return errs


def classify(df: pd.DataFrame) -> pd.DataFrame:
    """Raw score on complete cases (all eight items answered); incomplete cases are excluded and counted."""
    out = df.copy()
    complete = out[ITEMS].notna().all(axis=1)
    out["complete"] = complete
    out["raw"] = out[ITEMS].sum(axis=1).where(complete)
    out["mod_sev"] = (out["raw"] >= MOD_SEV).astype(float).where(complete)
    out["severe"] = (out["raw"] >= SEVERE).astype(float).where(complete)
    return out


def kish_deff(w: np.ndarray) -> float:
    w = np.asarray(w, float)
    return float(len(w) * (w ** 2).sum() / (w.sum() ** 2))


def estimate(df: pd.DataFrame, by=("province_code", "quarter"), cluster_deff: float = 1.5, z: float = 1.959964) -> pd.DataFrame:
    """Weighted prevalence of moderate-or-severe food insecurity per province-quarter with a design-adjusted 95% CI
    (Kish weighting effect x an assumed clustering effect; replace with the design-based variance once the design is
    fixed)."""
    c = classify(df)
    inc = c[~c["complete"]].groupby(list(by)).size().to_dict()
    rows = []
    for key, g in c[c["complete"]].groupby(list(by)):
        w = g["weight"].to_numpy(float)
        p = float(np.average(g["mod_sev"], weights=w))
        deff = kish_deff(w) * cluster_deff
        neff = len(g) / deff
        se = math.sqrt(max(p * (1 - p), 1e-12) / neff)
        rows.append({**dict(zip(by, key if isinstance(key, tuple) else (key,))), "n": int(len(g)), "n_eff": neff,
                     "prevalence_mod_sev": p, "ci95": [max(0.0, p - z * se), min(1.0, p + z * se)], "deff": deff,
                     "severe": float(np.average(g["severe"], weights=w)),
                     "incomplete_excluded": int(inc.get(key, 0))})
    return pd.DataFrame(rows)


def sample_size(margin_points: float = 5.0, p: float = 0.5, deff: float = 2.0, z: float = 1.959964, response_rate: float = 0.85) -> int:
    """Households to field per province per quarter for a +/- margin_points 95% CI on the prevalence."""
    e = margin_points / 100
    return int(math.ceil(deff * z * z * p * (1 - p) / (e * e) / response_rate))


def deterioration(est: pd.DataFrame, z90: float = 1.644854) -> pd.DataFrame:
    """Pre-specified outcome class: HIGH (deteriorated) iff the prevalence exceeds the province's baseline (mean of its
    first two rounds) by >= 5 points AND the 90% lower bound of that difference is > 0. Baseline rounds get no class."""
    out = []
    for p, g in est.sort_values("quarter").groupby("province_code"):
        g = g.reset_index(drop=True)
        if len(g) < 3:
            continue
        base = g.loc[:1, "prevalence_mod_sev"].mean()
        base_se = math.sqrt(sum(((r.ci95[1] - r.ci95[0]) / (2 * 1.959964)) ** 2 for r in g.loc[:1].itertuples()) / 4)
        for r in g.loc[2:].itertuples():
            se = (r.ci95[1] - r.ci95[0]) / (2 * 1.959964)
            diff = r.prevalence_mod_sev - base
            lo = diff - z90 * math.sqrt(se ** 2 + base_se ** 2)
            out.append({"province_code": p, "quarter": r.quarter, "baseline": base, "prevalence": r.prevalence_mod_sev,
                        "diff_points": 100 * diff, "lower90_points": 100 * lo,
                        "HIGH": int(100 * diff >= DETERIORATION_POINTS and lo > 0)})
    return pd.DataFrame(out)


def join_forecasts(outcome: pd.DataFrame, sealed: pd.DataFrame, pcol: str) -> pd.DataFrame:
    """Sealed province forecasts (columns target, province_code, pcol) joined to the survey outcome class."""
    j = sealed.rename(columns={"target": "quarter"}).merge(outcome, on=["province_code", "quarter"], how="inner")
    j["correct"] = ((j[pcol] >= 0.5).astype(int) == j["HIGH"]).astype(int)
    return j
