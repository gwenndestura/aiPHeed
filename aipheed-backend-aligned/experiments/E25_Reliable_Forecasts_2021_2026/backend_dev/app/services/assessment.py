"""
app/services/assessment.py
--------------------------
Province assessments from the revised pipeline (isolated development backend).

Source: data/revised/revised_forecasts_retrospective.parquet, written by scripts/build_revised_forecasts.py
(time-valid LightGBM forecasts; one artifact, so the API, the dashboard payload and the evaluation
all read the same probabilities). The classification is recomputed here with the single shared rule
(app/ml/features/risk_score_v2.final_classification) and checked against the artifact.

Kept separate in every payload:
  forecast                  LightGBM probability + HIGH / LOW / INSUFFICIENT_DATA (fixed 0.50 rule)
  regionalHungerSignal      SWS Balance-Luzon hunger: ONE regional value, identical for all provinces
  provincialFoodPriceEvidence  provincial food-price indicators (supporting evidence, not food insecurity)
  supportingStressScore     last published Equation 3 stress, split into regional and provincial parts
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd

from app.ml.features import risk_score_v2 as R

ARTIFACT = Path("data/revised/datadriven_forecasts_retrospective.parquet")   # E7 M6 (protocol-fixed); E6 artifact kept
GROUP_LABELS = {"R": "regional hunger and persistence (shared regional signal + last published stress)",
                "GP": "provincial government indicators (food CPI, inflation, rice prices, poverty)",
                "GN": "national/regional government indicators (identical for all provinces)",
                "N": "news-derived indicators (FSSI, article counts, trigger shares)"}
LABELS = Path("data/processed/labels.parquet")
NAMES = {"PH040100000": "Cavite", "PH040200000": "Laguna", "PH040300000": "Quezon",
         "PH040400000": "Rizal", "PH040500000": "Batangas"}
REGIONAL_SCOPE = ("SWS Balance Luzon stratum: all of Luzon outside Metro Manila. It is a regional signal, "
                  "identical for all five provinces, and NOT a province-specific measurement of hunger.")
LIMITATIONS = [
    "The probability is for an Equation 3 stress event, a proxy built from regional hunger and provincial "
    "food-price pressure. No province-level food-insecurity outcome exists to validate it.",
    "Regional hunger dominates the stress score (about 65% of its historical variance; 81% of historical labels "
    "equal the regional-only call), so provinces usually move together.",
    "Evaluation rests on 7 reused quarters (35 rows; about 7 independent quarters) with only 2 LOW reference labels "
    "under the frozen reference; results are exploratory, not independent validation.",
    "Probabilities are not calibrated: the training-only calibration check never had enough out-of-fold evidence.",
    "Provincial CPI publication dates are proxies (national release + 14 days).",
    "News evidence is very thin: in 2021-2025 only 36 articles were both rated relevant and geocoded to a province, "
    "and no province-quarter reached the 5-article minimum; news contributions are therefore weak evidence.",
    "Group contributions describe the fitted model (log-odds); they are not causal effects, and correlated "
    "indicators can share or shift contribution.",
    "The HIGH/LOW reference is empirical (the thesis median rule, frozen), not an official DA or government cutoff.",
]


class AssessmentQuarterNotFound(LookupError):
    pass


@lru_cache(maxsize=1)
def _artifact() -> tuple[pd.DataFrame, dict]:
    a = pd.read_parquet(ARTIFACT)
    meta = json.loads(ARTIFACT.with_name(ARTIFACT.stem + "_meta.json").read_text(encoding="utf-8"))
    return a, meta


@lru_cache(maxsize=1)
def _labels() -> pd.DataFrame:
    lab = pd.read_parquet(LABELS)
    return lab[(lab["quarter"] >= "2021-Q1") & (lab["quarter"] <= "2025-Q4")][["province_code", "quarter", "stress_score"]]


def _num(v, nd=3):
    return None if v is None or (isinstance(v, float) and np.isnan(v)) or pd.isna(v) else round(float(v), nd)


def _factors(s: str) -> list[dict]:
    out = []
    for part in [p.strip() for p in (s or "").split(";") if p.strip()]:
        name, val = part.rsplit(" ", 1)
        out.append({"feature": name, "direction": "raises" if val.startswith("+") else "lowers",
                    "logOddsContribution": float(val)})
    return out


def _contributions(r: pd.Series) -> dict:
    sel = [g for g in str(r.get("selected_groups") or "").split("+") if g]
    groups = {}
    for g, label in GROUP_LABELS.items():
        v = r.get(f"contrib_{g}")
        groups[g] = {"label": label, "included": g in sel,
                     "logOddsContribution": None if v is None or pd.isna(v) or g not in sel else round(float(v), 3)}
    return {"selectedGroups": sel, "groups": groups,
            "note": "Each group's summed LightGBM contribution to this forecast (log-odds; positive raises P(HIGH)). "
                    "Groups were chosen using training data only; a group that is not included did not improve "
                    "inner validation. Contributions are descriptive, not causal."}


def _stress_parts(anchor: str | None, province: str) -> dict:
    if not isinstance(anchor, str):
        return {"lastPublishedStress": None, "anchorQuarter": None}
    q = _labels()[_labels()["quarter"] == anchor]
    regional = float(q["stress_score"].mean())
    own = q.loc[q["province_code"] == province, "stress_score"]
    s = float(own.iloc[0]) if len(own) else None
    return {"lastPublishedStress": _num(s), "anchorQuarter": anchor,
            "regionalComponent": _num(regional), "provincialComponent": _num(None if s is None else s - regional),
            "meaning": "Equation 3 stress of the latest published label: regional hunger % plus 2 x the province's "
                       "food-inflation gap to the five-province mean. A supporting score, not a probability."}


def _rationale(r: pd.Series, cls: str) -> str:
    sws = f"regional hunger signal {r['sws_hunger']:.1f}% ({r['sws_round']}, shared by all provinces)"
    price = ("provincial food inflation not available" if pd.isna(r.get("inflation_rate")) else
             f"food inflation {r['inflation_rate']:.1f}% in {r['cpi_reference_quarter']} "
             f"({r['relative_pressure']:+.1f} pp vs the five-province mean)")
    if cls == R.INSUFFICIENT_DATA:
        return f"INSUFFICIENT DATA: {r['insufficient_reasons']}. No HIGH/LOW classification is made."
    word = "at or above" if cls == R.HIGH else "below"
    return (f"{cls}: LightGBM probability {r['probability']:.2f} is {word} the fixed 0.50 threshold. "
            f"Evidence available at the forecast date: {sws}; {price}.")


def assessments(quarter: str) -> dict:
    a, meta = _artifact()
    rows = a[a["target_quarter"] == quarter]
    if rows.empty:
        raise AssessmentQuarterNotFound(quarter)
    provinces = []
    for _, r in rows.sort_values("province_code").iterrows():
        reasons = [x.strip() for x in str(r["insufficient_reasons"] or "").split(";") if x.strip()]
        p = None if pd.isna(r["probability"]) else float(r["probability"])
        cls = R.final_classification(p, reasons)
        if cls != r["classification"]:
            raise RuntimeError(f"classification mismatch for {r['province_code']} {quarter}")
        provinces.append({
            "provinceCode": r["province_code"], "provinceName": NAMES[r["province_code"]], "quarter": quarter,
            "forecast": {
                "probability": _num(p, 4), "classification": cls, "threshold": R.PROBABILITY_CUTOFF,
                "rule": "HIGH if probability >= 0.50; LOW if < 0.50; INSUFFICIENT_DATA if required data are missing or stale",
                "forecastOrigin": str(r["origin"])[:10], "horizon": "1 quarter ahead (issued at the start of the quarter)",
                "model": "LightGBM (compact; monotone on regional hunger and last published stress; no class weighting; "
                         "indicator groups chosen by a training-only inner walk-forward)",
                "calibrated": bool(meta["calibration_by_quarter"].get(quarter, {}).get("applied", False)),
                "probabilityMeaning": (f"LightGBM probability that this province's Equation 3 stress in {quarter} exceeds "
                                       f"the frozen reference {meta['tau']:.3f} (median stress of labels published before "
                                       f"{meta['tau_as_of']}). Not a validated province-level food-insecurity rate."),
                "trainingQuarters": int(r["n_train_quarters"])},
            "regionalHungerSignal": {
                "value": _num(r["sws_hunger"]), "unit": "% of respondents reporting involuntary hunger (SWS)",
                "round": r["sws_round"], "roundQuarter": r["sws_round_quarter"], "published": str(r["sws_published"])[:10],
                "dateType": r["sws_date_type"], "ageQuarters": _num(r["sws_age"], 0), "scope": REGIONAL_SCOPE,
                "sharedAcrossProvinces": True},
            "provincialFoodPriceEvidence": {
                "referenceQuarter": r["cpi_reference_quarter"], "published": r["cpi_published"],
                "dateType": r["cpi_date_type"], "inflationRatePct": _num(r["inflation_rate"]),
                "relativePressurePp": _num(r["relative_pressure"]), "inflationChangePp": _num(r["inflation_change"]),
                "priceIndexLevel": _num(r["price_index_level"], 1),
                "notes": ["Supporting economic evidence, not a measurement of food insecurity.",
                          "The index level shows how high prices are; the inflation rate shows how fast they are rising "
                          "now. Slowing inflation does not mean prices have returned to earlier levels."]},
            "supportingStressScore": _stress_parts(r["anchor_quarter"], r["province_code"]),
            "mainFactors": _factors(r["top_factors"]),
            "evidenceContributions": _contributions(r),
            "missingDataWarnings": reasons,
            "rationale": _rationale(r, cls),
            "limitations": LIMITATIONS,
        })
    counts = pd.Series([p["forecast"]["classification"] for p in provinces]).value_counts().to_dict()
    first = rows.iloc[0]
    return {"quarter": quarter, "provinces": provinces,
            "region": {"regionalHungerSignal": provinces[0]["regionalHungerSignal"],
                       "classificationCounts": {k: int(counts.get(k, 0)) for k in (R.HIGH, R.LOW, R.INSUFFICIENT_DATA)},
                       "note": "Provinces that share the elevated regional hunger signal often receive the same "
                               "classification; differences between them come only from provincial food-price evidence."},
            "methodology": {"reference": meta["tau"], "referenceAsOf": meta["tau_as_of"],
                            "artifactSha256": meta["sha256"]["artifact"], "forecastOrigin": str(first["origin"])[:10]}}


def quarters() -> list[dict]:
    a, _ = _artifact()
    out = []
    for q, g in a.groupby("target_quarter"):
        c = g["classification"].value_counts().to_dict()
        out.append({"quarter": q, **{k: int(c.get(k, 0)) for k in (R.HIGH, R.LOW, R.INSUFFICIENT_DATA)}})
    return out


def methodology() -> dict:
    _, meta = _artifact()
    return {
        "classificationRule": {"HIGH": "final probability >= 0.50", "LOW": "final probability < 0.50",
                               "INSUFFICIENT_DATA": "a required input is missing, the SWS input is older than "
                               f"{R.SWS_MAX_AGE_QUARTERS} quarters, fewer than {R.MIN_REFERENCE_QUARTERS} eligible "
                               "training quarters, or one-class training labels", "threshold": R.PROBABILITY_CUTOFF},
        "target": {"formula": "stress = SWS_t + 2 x (provincial food CPI YoY - five-province mean); event: stress > reference",
                   "coefficient2": "documented but unvalidated; no outcome data exist to estimate it",
                   "reference": meta["tau"], "referenceAsOf": meta["tau_as_of"], "referenceQuarters": meta["tau_quarters"],
                   "status": "empirical (thesis median rule, frozen); not an official DA cutoff"},
        "model": meta["model"], "groupSelectionByQuarter": meta.get("selection_by_quarter"), "calibration": "Platt scaling only with >= 8 inner out-of-fold quarters and >= 10 rows per "
                                                "class; never met, so probabilities are uncalibrated",
        "regionalHungerScope": REGIONAL_SCOPE, "limitations": LIMITATIONS,
    }
