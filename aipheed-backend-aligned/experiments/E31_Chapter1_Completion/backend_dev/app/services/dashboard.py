"""
app/services/dashboard.py
--------------------------
Read model output and shape it for the dashboard.

Everything the frontend renders resolves here. The rules this module enforces:

* A quarter is scorable only if the model panel carries it. The calendar does
  not decide; PSA's publication lag does. Quarters outside that range raise
  QuarterNotAvailable rather than returning a zero-filled forecast, so the map
  greys out instead of showing a confident-looking 0.00.
* riskScore is the LightGBM probability that a province is at HIGH food
  insecurity risk at the Maximum Reliable Lead Time (Equation 5). It is a
  relative ordinal estimate of potential risk, not a definitive determination
  of food insecurity status, and every response says so in `indicator`.
* Driver percentages are integers summing to exactly 100 (largest remainder).

Scoring a quarter costs a model pass and SHAP costs a TreeExplainer pass, so
both are memoised per quarter for the life of the process.
"""

from __future__ import annotations

import functools
import json
import logging
from pathlib import Path

import pandas as pd

from app.ml.inference.disaggregator import Disaggregator
from app.ml.inference.explainer import Explainer
from app.ml.inference.predictor import Predictor
from app.ml.inference import e31_engine as E31
from app.services import reference as ref

logger = logging.getLogger(__name__)

CORPUS_PATH = Path("data/processed/corpus_geocoded.parquet")
LGU_POVERTY_PATH = Path("data/processed/lgu_poverty.parquet")
RESULTS_PATH = Path("data/processed/final_results.json")

# What the number on screen actually is. Carried on every forecast response so
# no surface can relabel it on its own.
INDICATOR = {
    "id": "food_insecurity_risk_probability",
    "name": "Food Insecurity Risk Probability",
    "definition": (
        "LightGBM probability that a CALABARZON province falls in the HIGH "
        "class of the composite food stress label — SWS quarterly hunger "
        "prevalence combined with the province's food CPI deviation from the "
        "regional mean, thresholded at the global median (Equation 3)."
    ),
    "unit": "probability (0-1)",
    "horizon": "Same-quarter estimate (lead 0); no forward lead time has been validated against the baselines (E27)",
    "source": (
        "Filipino-English news corpus (RSS, Google News, GDELT) and PSA, BSP, "
        "DOE, PAGASA, PhilRice and SWS indicators, CALABARZON, 2020-2025"
    ),
    "caveat": (
        "Risk rankings are indicative, not absolute. They are relative ordinal "
        "estimates of potential risk and must not be construed as official "
        "food insecurity classifications or policy recommendations."
    ),
}


# The corpus labels topics with two vocabularies: the NLI hypothesis sentence
# the classifier scored against, and a handful of bare slugs from an earlier
# pass. Neither belongs on screen, and the two overlap, so both fold into one
# set of stable keys here.
TOPIC_MAP: dict[str, tuple[str, str]] = {
    "This article is about food prices, food supply problems, or difficulty accessing food":
        ("food_prices", "Food prices & supply"),
    "food_price_change": ("food_prices", "Food prices & supply"),
    "This article is about farmland loss, crop damage, or reduced harvests":
        ("crop_damage", "Crop damage & harvest loss"),
    "This article is about government food assistance, rice subsidies, or relief distribution":
        ("food_assistance", "Food assistance & relief"),
    "This article is about hunger, malnutrition, or nutrition and feeding programs":
        ("hunger_nutrition", "Hunger & nutrition"),
    "food_insecurity_general": ("hunger_nutrition", "Hunger & nutrition"),
    "This article is about overseas Filipino workers or remittances supporting families":
        ("ofw", "OFW & remittances"),
    "This article is about fish kills, fishing bans, or aquaculture losses":
        ("fishkill", "Fish kill & fisheries"),
    "This article is about evacuation or displacement of families due to disaster":
        ("displacement", "Disaster displacement"),
    "disaster_displacement": ("displacement", "Disaster displacement"),
    "This article is about strikes, protests, or unrest disrupting food or livelihoods":
        ("unrest", "Strikes & unrest"),
    "This article is about roads, transport, or storage problems affecting food supply":
        ("logistics", "Transport & storage"),
    "This article is about poverty, unemployment, or economic hardship of families":
        ("poverty", "Poverty & unemployment"),
    "poverty_hardship": ("poverty", "Poverty & unemployment"),
}

UNCLASSIFIED = ("unclassified", "Unclassified")


class QuarterNotAvailable(Exception):
    """Raised when a quarter is outside the range the model can score."""


class SubjectNotFound(Exception):
    """Raised when a province or municipality id does not resolve."""


class ForecastWithheld(Exception):
    """
    Raised when an admin has rejected this province-quarter.

    Deliberately distinct from QuarterNotAvailable: one forecast was never
    generated, the other was generated and held back. The map shows different
    text for each, and conflating them would misreport an editorial decision
    as a data gap.
    """

    def __init__(self, message: str, reason: str | None = None):
        super().__init__(message)
        self.reason = reason


# ---------------------------------------------------------------------------
# Timeline
# ---------------------------------------------------------------------------

# Rule 2, Single Forecast Horizon: one LightGBM model is evaluated across
# multiple forward lead times, and the furthest one achieving reliable
# classification is adopted as THE operational forecast horizon. There is
# therefore one engine and one horizon.
#
# "nowcast" is retained as an accepted alias so the published frontend contract
# does not break; it resolves to the same single model. Both ids describe the
# forecast at the Maximum Reliable Lead Time, which is 0 quarters when no
# forward horizon clears the Section 3.4.4 threshold.
FORECAST = "forecast"
NOWCAST = "nowcast"
HORIZONS = (FORECAST, NOWCAST)
DEFAULT_HORIZON = FORECAST

HORIZON_INFO = {
    FORECAST: {
        "id": FORECAST,
        "name": "Province food insecurity risk estimate (experimental)",
        "question": (
            "Which CALABARZON provinces are at high risk of food insecurity at "
            "the furthest lead time the model forecasts reliably?"
        ),
        # E27 fix: the old text claimed a horizon adopted by a 75%-accuracy rule. No lead time has been
        # validated against the baselines (E25-E27), and 75% accuracy is not evidence of skill here.
        "definition": (
            "One LightGBM classifier, evaluated across lead times 1 through 8 "
            "quarters by walk-forward expanding-window cross-validation. No "
            "lead time has been validated: no model beat the persistence, "
            "calibrated-persistence, always-HIGH and climatology baselines, "
            "so every output is an experimental same-quarter estimate."
        ),
        "evidenceStatus": "EXPERIMENTAL",
        "resultsFile": "training_results.json",
    },
}
# The alias resolves to the same entry; see the Rule 2 note above.
HORIZON_INFO[NOWCAST] = {**HORIZON_INFO[FORECAST], "id": NOWCAST, "alias_of": FORECAST}

# E31: the served estimates come from the E31 record (PCF21). The two ids are now different views.
E31_HORIZON_INFO = {
    FORECAST: {
        "id": FORECAST, "name": "One-quarter-ahead forecasts (lead 1)",
        "question": "What did the served engine estimate one quarter ahead, using only information released before "
                    "the quarter began?",
        "definition": ("PCF21 estimates of P(S1 = H + 2D above its trailing-median threshold) one quarter ahead: "
                       "development backtests 2023-Q4..2026-Q2, the 2026-Q3 forecast frozen on 1 July 2026 and "
                       "scored on its released outcome, and the 2027-Q1 forecast (cutoff 2026-10-14). News evidence "
                       "is the previous quarter's. No lead is validated against persistence and always-HIGH."),
        "evidenceStatus": "EXPERIMENTAL", "resultsFile": "data/e31/e31_record.json"},
    NOWCAST: {
        "id": NOWCAST, "name": "Latest estimate per quarter (nowcast for the quarter under way)",
        "question": "What is the best available estimate for each quarter, including the one under way?",
        "definition": ("The same-quarter nowcast where the quarter is under way (2026-Q4, inputs and same-quarter "
                       "news released by 2026-10-14) and the lead-1 estimate for every other quarter. Each row is "
                       "labelled with its mode; lead 0 has never been evaluated."),
        "evidenceStatus": "EXPERIMENTAL", "resultsFile": "data/e31/e31_record.json"},
}


def e31_active() -> bool:
    """E31: the dashboard serves the E31 record unless AIPHEED_DATA_LAYER=legacy (the pre-E31 production model)."""
    import os

    return os.getenv("AIPHEED_DATA_LAYER", "e31").lower() != "legacy" and E31.available()


def _engine(horizon: str = DEFAULT_HORIZON):
    """
    E31: the served PCF21 estimates from the E31 record. "forecast" = lead-1 estimates (backtests, the frozen
    2026-Q3 forecast, the 2027-Q1 forecast); "nowcast" = the 2026-Q4 same-quarter estimate. Legacy: the single
    LightGBM Predictor (Rule 2), with the horizon accepted only for contract compatibility.
    """
    if e31_active():
        return E31.E31Engine(horizon)
    return Predictor()


def _explainer():
    return E31.E31Explainer() if e31_active() else Explainer()


def check_horizon(horizon: str | None) -> str:
    h = (horizon or DEFAULT_HORIZON).lower()
    if h not in HORIZONS:
        raise SubjectNotFound(
            f"Unknown horizon '{horizon}'. Expected one of {', '.join(HORIZONS)}."
        )
    return h


@functools.lru_cache(maxsize=4)
def available_quarters(horizon: str = DEFAULT_HORIZON) -> list[str]:
    return _engine(horizon).available_quarters()


def latest_quarter(horizon: str = DEFAULT_HORIZON) -> str:
    if e31_active() and horizon == NOWCAST and E31.current_quarter():
        return E31.current_quarter()      # the default view opens on the quarter under way, not on the forecast
    quarters = available_quarters(horizon)
    if not quarters:
        raise QuarterNotAvailable("The model panel is empty; no quarter is scorable.")
    return quarters[-1]


def resolve_quarter(quarter: str | None, horizon: str = DEFAULT_HORIZON) -> str:
    """Default to the latest scorable quarter; reject anything unscorable."""
    if quarter is None:
        return latest_quarter(horizon)
    if not ref.is_valid_quarter(quarter):
        raise QuarterNotAvailable(f"'{quarter}' is not a quarter id (expected YYYY-Qn).")
    if quarter not in available_quarters(horizon) and e31_active():
        other = NOWCAST if horizon == FORECAST else FORECAST
        if quarter in available_quarters(other):      # E31: a nowcast-only quarter (2026-Q4) is still served
            return quarter
    if quarter not in available_quarters(horizon):
        raise QuarterNotAvailable(
            f"No {horizon} exists for {quarter}. The {horizon} model can score "
            f"{available_quarters(horizon)[0]} through {latest_quarter(horizon)}."
        )
    return quarter


def timeline(horizon: str = DEFAULT_HORIZON) -> list[dict]:
    """
    Every scorable quarter for this horizon, oldest first.

    Every quarter but the newest is marked `actual`. The newest is marked
    `forecast` because it is the one the model projects forward to at the
    Maximum Reliable Lead Time.
    """
    quarters = available_quarters(horizon)
    latest = quarters[-1] if quarters else None
    # E27 fix: with a Maximum Reliable Lead Time of 0 the newest quarter is a same-quarter estimate of an
    # observed quarter, not a forecast; "current" is the contract's state for it.
    newest_state = "forecast" if _engine(horizon).lead_time > 0 else "current"
    out = []
    for q in quarters:
        year, qn = ref.quarter_parts(q)
        if e31_active():                   # E31: the state is the row's own mode
            mode = E31.quarter_row(q, horizon)["mode"]
            state = {"FORECAST": "forecast", "NOWCAST": "current"}.get(mode, "actual")
        elif q == latest:
            state = newest_state
        else:
            state = "actual"
        out.append({
            "id": q,
            "year": year,
            "q": qn,
            "label": f"Q{qn}",
            "monthsLabel": ref.QUARTER_MONTHS[qn],
            "state": state,
        })
    if e31_active() and out:
        out = _e31_fill_gaps(out, horizon)
    return out


def _e31_unavailable_reason(quarter: str, horizon: str) -> str:
    """Why the E31 record has no row for this quarter in this view (E34, D1). Derived from the data, never assumed."""
    other = NOWCAST if horizon == FORECAST else FORECAST
    if quarter in available_quarters(other):
        return (f"{quarter} is the quarter under way; its estimate is a same-quarter nowcast, shown in the nowcast "
                "view. A forecast view never shows a nowcast.")
    p = Path("data/inputs/sws_rounds.csv")
    if p.exists():
        r = pd.read_csv(p)
        r = r[r["quarter"] == quarter]
        if len(r) and not r["definition_A"].astype(str).str.lower().eq("true").any():
            return (f"No estimate for {quarter}: its SWS hunger rounds are recorded as supplementary, not as the "
                    "approved (definition A) series, so the quarter has no approved label to estimate or score. "
                    "This is missing data, not a low score.")
        if not len(r):
            return (f"No estimate for {quarter}: no SWS hunger round is recorded for it. This is missing data, not a "
                    "low score.")
    return f"The E31 record holds no estimate for {quarter}. This is missing data, not a low score."


def _e31_fill_gaps(rows: list[dict], horizon: str) -> list[dict]:
    """List every quarter between the first and last served one; gaps become "unavailable" with a reason (E34, D1)."""
    have = {r["id"]: r for r in rows}
    idx = [ref.quarter_index(r["id"]) for r in rows]
    out = []
    for i in range(min(idx), max(idx) + 1):
        q = f"{i // 4}-Q{i % 4 + 1}"
        if q in have:
            out.append(have[q])
            continue
        year, qn = ref.quarter_parts(q)
        out.append({"id": q, "year": year, "q": qn, "label": f"Q{qn}", "monthsLabel": ref.QUARTER_MONTHS[qn],
                    "state": "unavailable", "reason": _e31_unavailable_reason(q, horizon)})
    return out


def is_estimate_quarter(quarter: str) -> bool:
    """E31: True for the quarters whose outcome is not yet known (the 2026-Q4 nowcast, the 2027-Q1 forecast); False for
    backtests and the scored 2026-Q3. Same rule as /config quarterRange.forecastQuarters (E34, D2)."""
    if not e31_active():
        return False
    row = E31.quarter_row(quarter, NOWCAST)
    return bool(row) and row["mode"] in ("FORECAST", "NOWCAST")


# ---------------------------------------------------------------------------
# Province-level forecasts
# ---------------------------------------------------------------------------

@functools.lru_cache(maxsize=64)
def _province_forecasts(quarter: str, horizon: str = DEFAULT_HORIZON) -> list[dict]:
    """Raw model output for one quarter, from whichever engine the horizon names."""
    out = _engine(horizon).forecast_quarter(quarter)
    if not out and e31_active():                       # E31: the quarter exists only under the other mode
        out = _engine(NOWCAST if horizon == FORECAST else FORECAST).forecast_quarter(quarter)
    return out


def province_forecast_map(quarter: str, horizon: str = DEFAULT_HORIZON) -> dict[str, dict]:
    return {r["province_code"]: r for r in _province_forecasts(quarter, horizon)}


def _previous_quarter(quarter: str, horizon: str = DEFAULT_HORIZON) -> str | None:
    quarters = available_quarters(horizon)
    i = quarters.index(quarter) if quarter in quarters else -1
    return quarters[i - 1] if i > 0 else None


def _qoq(current: float, quarter: str, code: str,
         horizon: str = DEFAULT_HORIZON) -> tuple[float | None, float | None]:
    """Absolute and percentage change against the previous scorable quarter."""
    prev_q = _previous_quarter(quarter, horizon)
    if prev_q is None:
        return None, None
    prev = province_forecast_map(prev_q, horizon).get(code)
    if prev is None:
        return None, None
    prev_score = prev["risk_probability"]
    delta = round(current - prev_score, 4)
    pct = round((current - prev_score) / prev_score * 100, 1) if prev_score else None
    return delta, pct


@functools.lru_cache(maxsize=1)
def _province_poverty() -> dict[str, float]:
    """Province-mean PSA 2021 poverty incidence, from the LGU table."""
    if e31_active() and LGU_PROVENANCE_PATH.exists():
        df = pd.read_csv(LGU_PROVENANCE_PATH, dtype={"lgu_code": str})
        df["province_code"] = df["province"].map({m["name"]: m["code"] for m in ref.PROVINCES.values()})
        return df.groupby("province_code")["poverty_value_used"].mean().round(1).to_dict()
    if not LGU_POVERTY_PATH.exists():
        return {}
    df = pd.read_parquet(LGU_POVERTY_PATH)
    return df.groupby("province_code")["poverty_incidence_pct"].mean().round(1).to_dict()


@functools.lru_cache(maxsize=1)
def _province_population() -> dict[str, int]:
    roster = ref.lgu_roster()
    return roster.groupby("province_code")["population_2020"].sum().astype(int).to_dict()


def province_summary(
    quarter: str,
    withheld: frozenset[str] = frozenset(),
    horizon: str = DEFAULT_HORIZON,
) -> list[dict]:
    """
    One headline row per province, ranked by risk descending.

    A province in `withheld` keeps its geography and population but its score
    is blanked. Returning the number alongside a "rejected" flag and trusting
    every caller to hide it would defeat the rejection -- and with five
    provinces and a published regional mean, one leaked score is enough to
    reconstruct a withheld one.
    """
    poverty = _province_poverty()
    population = _province_population()
    rows = []
    for record in _province_forecasts(quarter, horizon):
        code = record["province_code"]
        slug = ref.province_slug(code)
        if slug is None:
            continue
        score = record["risk_probability"]
        delta, pct = _qoq(score, quarter, code, horizon)
        meta = ref.PROVINCES[slug]
        rows.append({
            "id": slug,
            "name": meta["name"],
            "provinceCode": code,
            "centroid": {"lat": meta["lat"], "lng": meta["lng"]},
            "population": population.get(code),
            "povertyRate": poverty.get(code),
            "currentQuarter": quarter,
            "riskScore": score,
            "riskLevel": ref.risk_level(score),
            "qoqChange": delta,
            "qoqChangePct": pct,
            "riskLabel": record.get("risk_label"),
            "evidenceStatus": "EXPERIMENTAL",
            "riskLevelBasis": RISK_LEVEL_BASIS,
            # Rule 6: every forecast carries an explicit horizon label, a
            # confidence statement and a verification date.
            "forecastHorizonQuarters": record.get("forecast_horizon_quarters"),
            "horizonLabel": record.get("horizon_label"),
            "confidenceStatement": record.get("confidence_statement"),
            "verificationDate": record.get("verification_date"),
            "articleCount": article_count(code, quarter),
            "limitedSignal": record.get("data_sufficiency_flag") == "LIMITED_SIGNAL",
            "horizon": horizon,
            "withheld": False,
        })

    # Rank the published provinces by the model's own probability. A withheld
    # province is left out: ranking it, or ranking the others around it, would
    # reveal where its score sits.
    published = sorted(
        (r for r in rows if r["id"] not in withheld and r["riskScore"] is not None),
        key=lambda r: r["riskScore"], reverse=True,
    )
    for i, row in enumerate(published):
        nxt = published[i + 1] if i + 1 < len(published) else None
        row["rank"] = i + 1
        row["rankOf"] = len(published)
        row["gapToNextLower"] = (round(row["riskScore"] - nxt["riskScore"], 4)
                                 if nxt else None)
        row["tiedWithNextLower"] = (row["gapToNextLower"] == 0.0) if nxt else None

    for row in rows:
        if row["id"] in withheld:
            row.update({
                "riskScore": None,
                "riskLevel": None,
                "qoqChange": None,
                "qoqChangePct": None,
                "riskLabel": None,
                "withheld": True,
            })

    rows.sort(key=lambda r: (r["riskScore"] is not None, r["riskScore"] or 0), reverse=True)
    return rows


RANKING_METHOD = (
    "Provinces are ordered by the model's risk probability for the quarter. "
    "The gap is the difference in probability to the next province down; "
    "provinces with the same probability are marked as tied rather than "
    "ordered arbitrarily. The features listed for each province are the SHAP "
    "contributions (Equation 7) that differ most between it and the next "
    "province down; because SHAP values are additive, all the differences "
    "together equal the gap. The ranking is relative and indicative, not an "
    "official classification."
)


def ranking(quarter: str, withheld: frozenset[str] = frozenset(),
            horizon: str = DEFAULT_HORIZON) -> dict:
    """
    The published provinces in rank order, each with the SHAP features that
    separate it from the next province down (Section 1.2; Equation 7).
    """
    rows = [r for r in province_summary(quarter, withheld, horizon)
            if not r["withheld"] and r["riskScore"] is not None]
    rows.sort(key=lambda r: r["rank"])
    explainer = _explainer()
    shap_by = {r["provinceCode"]: explainer.explain_province_quarter(r["provinceCode"], quarter)
               for r in rows}

    data = []
    for i, r in enumerate(rows):
        nxt = rows[i + 1] if i + 1 < len(rows) else None
        why = []
        if nxt is not None:
            other = {d["feature_name"]: d for d in shap_by[nxt["provinceCode"]]}
            for d in shap_by[r["provinceCode"]]:
                o = other.get(d["feature_name"])
                if o is None:
                    continue
                why.append({
                    "feature": d["feature_name"],
                    "label": d["display_name"],
                    "difference": round(d["shap_value"] - o["shap_value"], 4),
                    "value": d["feature_value"],
                    "valueNextLower": o["feature_value"],
                })
            why.sort(key=lambda x: abs(x["difference"]), reverse=True)
        data.append({
            "id": r["id"], "name": r["name"], "provinceCode": r["provinceCode"],
            "riskScore": r["riskScore"], "riskLevel": r["riskLevel"],
            "rank": r["rank"], "rankOf": r["rankOf"], "qoqChange": r["qoqChange"],
            "gapToNextLower": r["gapToNextLower"],
            "tiedWithNextLower": r["tiedWithNextLower"],
            "nextLowerId": nxt["id"] if nxt else None,
            "whyAboveNextLower": why[:3],
            "limitedSignal": r["limitedSignal"],
        })
    return {
        "quarter": quarter,
        "indicator": INDICATOR,
        "method": RANKING_METHOD,
        "horizonLabel": rows[0]["horizonLabel"] if rows else "",
        "data": data,
    }


def region_forecast(quarter: str, withheld: frozenset[str] = frozenset(),
                    horizon: str = DEFAULT_HORIZON) -> dict:
    """
    CALABARZON roll-up: the mean of the published province scores.

    The model has no region-level series of its own, so this is an average of
    province output rather than a separate prediction.

    Withheld provinces are excluded from the mean, not counted as zero. With
    five provinces, a mean over all five plus four published scores gives the
    fifth exactly -- so a rejection has to shrink the denominator, and the
    response says how many provinces it covers.
    """
    provinces = province_summary(quarter, withheld, horizon)
    published = [p for p in provinces if not p["withheld"]]
    scores = [p["riskScore"] for p in published]
    score = round(sum(scores) / len(scores), 4) if scores else None

    delta = None
    prev_q = _previous_quarter(quarter, horizon)
    if prev_q and score is not None:
        # Compare like with like: the same provinces, one quarter earlier.
        prev_scores = [
            p["riskScore"] for p in province_summary(prev_q, withheld, horizon)
            if not p["withheld"]
        ]
        if prev_scores:
            delta = round(score - sum(prev_scores) / len(prev_scores), 4)

    return {
        "scope": "region",
        "id": ref.REGION_ID,
        "name": ref.REGION_NAME,
        "riskScore": score,
        "riskLevel": ref.risk_level(score) if score is not None else None,
        "qoqChange": delta,
        "horizonLabel": next(
            (p.get("horizonLabel") for p in published if p.get("horizonLabel")), None),
        "confidenceStatement": next(
            (p.get("confidenceStatement") for p in published
             if p.get("confidenceStatement")), None),
        "provinceCounts": {
            "high": sum(1 for p in published if p["riskLevel"] == "high"),
            "low": sum(1 for p in published if p["riskLevel"] == "low"),
            "limited": sum(1 for p in published if p["limitedSignal"]),
            "withheld": len(provinces) - len(published),
        },
        "provincesIncluded": len(published),
        "horizon": horizon,
        "limitedSignal": all(p["limitedSignal"] for p in published) if published else True,
        "derivation": (
            f"Mean of {len(published)} published province scores; the model has "
            "no region-level series."
        ),
    }


# ---------------------------------------------------------------------------
# Municipal disaggregation
# ---------------------------------------------------------------------------

@functools.lru_cache(maxsize=32)
def _municipal_frame(quarter: str) -> pd.DataFrame:
    forecasts = _province_forecasts(quarter)
    if e31_active():
        if not forecasts:                      # a quarter that exists only as a nowcast (2026-Q4)
            forecasts = _province_forecasts(quarter, NOWCAST)
        return E31.E31Disaggregator().disaggregate(forecasts, quarter=quarter)
    return Disaggregator().disaggregate(forecasts, quarter=quarter)


@functools.lru_cache(maxsize=1)
def _lgu_poverty_map() -> dict[str, float]:
    if e31_active() and LGU_PROVENANCE_PATH.exists():     # measured municipal SAE only; substitutes stay null
        df = pd.read_csv(LGU_PROVENANCE_PATH, dtype={"lgu_code": str})
        return {str(r.lgu_code).zfill(9): float(r.poverty_lgu_estimate) for r in df.itertuples()
                if pd.notna(r.poverty_lgu_estimate)}
    if not LGU_POVERTY_PATH.exists():
        return {}
    df = pd.read_parquet(LGU_POVERTY_PATH)
    return {
        str(c): float(v)
        for c, v in zip(df["lgu_code"], df["poverty_incidence_pct"])
    }


RISK_LEVEL_BASIS = (
    "Band of an unvalidated relative score (>= 0.50 shown as high); not a validated classification and not a "
    "measured local food-insecurity rate."
)
LGU_PROVENANCE_PATH = Path("data/inputs/lgu_vulnerability.csv")


@functools.lru_cache(maxsize=1)
def _lgu_provenance() -> dict[str, dict]:
    if not LGU_PROVENANCE_PATH.exists():
        return {}
    df = pd.read_csv(LGU_PROVENANCE_PATH, dtype={"lgu_code": str})
    return {r.lgu_code: {"value_used": float(r.poverty_value_used), "has_own": bool(pd.notna(r.poverty_lgu_estimate))}
            for r in df.itertuples()}


def _poverty_provenance(code: str, own: float | None) -> dict:
    """E27 fix: say what the ranking used for an LGU's poverty term and why, instead of returning a bare null."""
    p = _lgu_provenance().get(code)
    if own is not None or (p and p["has_own"]):
        return {"povertyEstimateKind": "PSA municipal SAE estimate (2021)",
                "povertyValueUsed": own if own is not None else p["value_used"], "povertyLimitation": None}
    return {"povertyEstimateKind": "province-mean substitute (no municipal estimate)",
            "povertyValueUsed": p["value_used"] if p else None,
            "povertyLimitation": ("No PSA municipal poverty estimate is available for this LGU; the ranking uses a "
                                  "province-mean substitute, so its position within the province reflects "
                                  "population density only.")}


def municipality_summary(quarter: str, province_id: str | None = None) -> list[dict]:
    """
    The 142 LGU indices for a quarter, optionally filtered to one province.

    These are reweighted province numbers, not independent municipal
    forecasts; disaggregationLabel travels with every row and says so.
    """
    frame = _municipal_frame(quarter)
    roster = ref.lgu_roster().set_index("lgu_psgc")
    poverty = _lgu_poverty_map()

    rows = []
    for _, r in frame.iterrows():
        code = str(r["lgu_code"])
        if code not in roster.index:
            continue
        meta = roster.loc[code]
        if province_id and meta["provinceId"] != province_id:
            continue
        # E28 fix: a province without an estimate gives risk_index = null; float(None) used to crash the endpoint.
        score = None if r["risk_index"] is None or pd.isna(r["risk_index"]) else round(float(r["risk_index"]), 4)
        rank_r = r.get("rank_region")
        rank_p = r.get("rank_in_province")
        rows.append({
            "id": meta["id"],
            "name": meta["lgu_name"],
            "provinceId": meta["provinceId"],
            "lguCode": code,
            "classification": meta["classification"],
            "population": int(meta["population_2020"]),
            "densityPerKm2": float(meta["densityPerKm2"]),
            "povertyRate": poverty.get(code),
            **_poverty_provenance(code, poverty.get(code)),
            "quarter": quarter,
            "riskIndex": score,
            # E28 fix: no HIGH/LOW band for an LGU. The province estimate it is derived from is not validated
            # (E25-E28), and a disaggregated index is a relative position, not a classification (Chapter I, 1.7).
            "riskLevel": None,
            "rankRegion": None if rank_r is None or pd.isna(rank_r) else int(rank_r),
            "rankInProvince": None if rank_p is None or pd.isna(rank_p) else int(rank_p),
            "tied": bool(r.get("tied", False)),
            "evidenceStatus": "EXPERIMENTAL",
            "riskLevelBasis": LGU_POSITION_BASIS,
            "disaggregationLabel": r["disaggregation_label"],
            "limitedSignal": r.get("data_sufficiency_flag") == "LIMITED_SIGNAL",
            "noProvinceEstimate": score is None,
        })
    rows.sort(key=lambda x: (x["riskIndex"] is None, -(x["riskIndex"] or 0.0), x["lguCode"]))
    return rows


LGU_POSITION_BASIS = (
    "Relative position only: the province estimate re-weighted by PSA poverty incidence (60%) and population density "
    "(40%) within the province. No HIGH/LOW band is shown because the province estimate is not validated; this is not "
    "a measured or official municipal food-insecurity classification.")


def municipality_forecast(municipality_id: str, quarter: str) -> dict:
    match = [
        m for m in municipality_summary(quarter)
        if m["id"] == municipality_id.lower()
    ]
    if not match:
        raise SubjectNotFound(f"Unknown municipality id '{municipality_id}'.")
    return match[0]


# ---------------------------------------------------------------------------
# Explainability
# ---------------------------------------------------------------------------

def _integer_shares(values: list[float]) -> list[int]:
    """
    Largest-remainder rounding so the percentages sum to exactly 100.

    Naive rounding drifts to 99 or 101 and the UI renders a bar chart that
    does not close.
    """
    total = sum(values)
    if total <= 0:
        return [0] * len(values)
    exact = [v / total * 100 for v in values]
    floors = [int(x) for x in exact]
    remainder = 100 - sum(floors)
    order = sorted(range(len(exact)), key=lambda i: exact[i] - floors[i], reverse=True)
    for i in order[:remainder]:
        floors[i] += 1
    return floors


@functools.lru_cache(maxsize=256)
def _drivers(province_code: str, quarter: str) -> dict:
    explainer = _explainer()
    records = explainer.explain_province_quarter(province_code, quarter)
    return explainer.build_drivers(province_code, quarter, records)


def trigger_color(pct: int, direction: str) -> str:
    """
    Bar colour for a driver group.

    The frontend contract froze this as "pct > 20 => red", which was written
    when every contribution was assumed to push risk up. Grouped SHAP is
    signed, so that rule paints a large PROTECTIVE driver red -- the reader
    sees the biggest bar in the alarm colour while it is holding the score
    down. Size decides whether a group is prominent; direction decides which
    prominent colour it gets.
    """
    if pct <= ref.TRIGGER_RED_CUTOFF:
        return "yellow"
    return "red" if direction == "increases_risk" else "green"


def explainability(province_code: str, quarter: str) -> dict:
    """
    Grouped SHAP for one province-quarter, ranked and normalised to 100%.

    Every group with a contribution is returned. The groups follow the approved
    feature vector of Equation 5 -- news sentiment, food prices, weather,
    employment, macro/OFW -- so a panel built for those five categories fits
    without anything being dropped.
    """
    built = _drivers(province_code, quarter)
    drivers = built["drivers"]
    pcts = _integer_shares([abs(d["group_shap"]) for d in drivers])

    triggers = []
    for d, pct in zip(drivers, pcts):
        triggers.append({
            "key": d["driver_group"],
            "label": d["driver_label"],
            "share": round(pct / 100, 4),
            "pct": pct,
            "signedContribution": d["group_shap"],
            "direction": d["direction"],
            "color": trigger_color(pct, d["direction"]),
            "newsSignalProportion": d["trigger_proportion"],
        })
    triggers.sort(key=lambda t: t["pct"], reverse=True)
    return {
        "quarter": quarter,
        "triggers": triggers,
        # The corpus is the single article count every surface quotes. The
        # trigger table keeps its own tally over a narrower keyword-matched
        # subset; it is reported separately rather than silently substituted.
        "articleCount": article_count(province_code, quarter),
        "triggerMatchedArticles": built["article_count"],
    }


def explainability_region(quarter: str) -> dict:
    """
    Regional breakdown: the five province explanations pooled.

    Groups are ranked by summed absolute contribution across provinces, while
    `signedContribution` averages so the direction still reads correctly -- a
    group that raises risk in one province and lowers it in another should not
    disappear from the ranking just because the two cancel.
    """
    per_province = [
        explainability(ref.province_code(slug), quarter) for slug in ref.PROVINCES
    ]

    totals: dict[str, dict] = {}
    for result in per_province:
        for t in result["triggers"]:
            acc = totals.setdefault(t["key"], {
                "key": t["key"], "label": t["label"],
                "signed": 0.0, "raw": 0.0, "news": [],
            })
            acc["raw"] += abs(t["signedContribution"])
            acc["signed"] += t["signedContribution"]
            if t["newsSignalProportion"] is not None:
                acc["news"].append(t["newsSignalProportion"])

    keys = list(totals)
    pcts = _integer_shares([totals[k]["raw"] for k in keys])

    triggers = []
    for key, pct in zip(keys, pcts):
        acc = totals[key]
        direction = "increases_risk" if acc["signed"] >= 0 else "protective"
        triggers.append({
            "key": key,
            "label": acc["label"],
            "share": round(pct / 100, 4),
            "pct": pct,
            "signedContribution": round(acc["signed"] / len(per_province), 4),
            "direction": direction,
            "color": trigger_color(pct, direction),
            "newsSignalProportion": (
                round(sum(acc["news"]) / len(acc["news"]), 4) if acc["news"] else None
            ),
        })
    triggers.sort(key=lambda t: t["pct"], reverse=True)

    return {
        "quarter": quarter,
        "triggers": triggers,
        "articleCount": sum(r["articleCount"] for r in per_province),
        "triggerMatchedArticles": sum(r["triggerMatchedArticles"] for r in per_province),
    }


def compose_narrative(name: str, quarter: str, triggers: list[dict]) -> str:
    """
    Plain-ASCII summary of a breakdown, for the chart caption and the PDF.

    ASCII only: it is drawn verbatim into PDFs by both jsPDF on the client and
    reportlab here, and a typographic dash breaks the export.
    """
    if not triggers:
        return f"No explainability is available for {name} in {quarter}."

    ranked = ", ".join(f"{t['label']} {t['pct']}%" for t in triggers[:5])
    top = triggers[0]
    direction = (
        "pushing the score up" if top["direction"] == "increases_risk"
        else "holding the score down"
    )

    cutoff = ref.TRIGGER_RED_CUTOFF
    raising = [t["label"] for t in triggers
               if t["pct"] > cutoff and t["direction"] == "increases_risk"]
    lowering = [t["label"] for t in triggers
                if t["pct"] > cutoff and t["direction"] == "protective"]

    def phrase(labels: list[str]) -> str:
        joined = (
            " and ".join([", ".join(labels[:-1]), labels[-1]])
            if len(labels) > 1 else labels[0]
        )
        return f"{joined} {'clears' if len(labels) == 1 else 'clear'}"

    parts = []
    if raising:
        parts.append(f"{phrase(raising)} the {cutoff}% line while raising the score.")
    if lowering:
        parts.append(f"{phrase(lowering)} the {cutoff}% line while lowering it.")
    flagged = " ".join(parts) or f"No single group clears the {cutoff}% line this quarter."

    return (
        f"For {name} in {quarter}, the model's prediction breaks down as: {ranked}. "
        f"{top['label']} is the largest single contributor, {direction}. {flagged} "
        f"Shares are SHAP contributions to the province's food insecurity risk "
        f"probability, recomputed every quarter."
    )


# ---------------------------------------------------------------------------
# Model performance
# ---------------------------------------------------------------------------

@functools.lru_cache(maxsize=4)
def model_performance(horizon: str = DEFAULT_HORIZON) -> dict:
    """
    The Specific Objective 2 metrics, with the Research Question 3 baselines
    they must be quoted against.

    Objective 2 names accuracy, precision, recall, F1-score, AUC-ROC and the
    Maximum Reliable Lead Time. All six are reported here from
    training_results.json, written by trainer.train_model().

    Accuracy alone is not enough: Research Question 3 asks how the combined
    LightGBM compares against six baselines, so whichever of them the last
    evaluation run produced travel with the number wherever it is displayed.
    A metric absent from the results file is reported as null, never as 0.0 --
    a displayed precision of 0.0000 reads as "the model gets nothing right"
    rather than "this results file predates the metric".
    """
    if e31_active():
        return e31_model_performance(horizon)
    path = Path("data/processed/training_results.json")
    if not path.exists():
        return {}
    results = json.loads(path.read_text())

    def _m(key: str) -> float | None:
        v = results.get(key)
        return round(v, 4) if isinstance(v, (int, float)) else None

    baselines: dict[str, float | None] = {}
    eval_path = Path("data/processed/eval_results.json")
    if eval_path.exists():
        rows = json.loads(eval_path.read_text()).get("baselines", {})
        for name, block in rows.items():
            acc = block.get("overall", {}).get("accuracy")
            baselines[name] = round(acc, 4) if isinstance(acc, (int, float)) else None

    return {
        "horizon": horizon,
        "evaluation": (
            "holdout — the last 4 quarters, never exposed to the Optuna search "
            "(Algorithm 4)"
        ),
        "maxReliableLeadTime": results.get("max_reliable_lead_time"),
        "accuracyThreshold": _m("accuracy_threshold"),
        "nFeatures": results.get("n_features"),
        "accuracy":  _m("holdout_accuracy"),
        "precision": _m("holdout_precision"),
        "recall":    _m("holdout_recall"),
        "f1":        _m("holdout_f1"),
        "rocAuc":    _m("holdout_roc_auc"),
        "cvF1":      _m("best_cv_f1"),
        "targets": {
            "f1": 0.75,
            "rocAuc": 0.80,
            "meetsF1": results.get("meets_f1_target"),
            "meetsRocAuc": results.get("meets_roc_auc_target"),
        },
        # Per-k scan from Algorithm 3: accuracy, precision, recall, F1 and
        # AUC-ROC at every lead time tested, so the horizon choice is legible.
        "leadTimeScan": results.get("lead_time_scan", []),
        # Accuracy of each Research Question 3 comparison model on the same
        # walk-forward folds. Empty until run_baseline_evaluation() has run.
        "baselines": baselines,
        # The model scored on the same walk-forward folds as the baselines.
        # Research Question 3 asks how the model compares against them, and a
        # comparison requires one evaluation set: the holdout figures above are
        # Algorithm 4's acceptance test on the last four quarters, while the
        # baselines run across every fold. These are the model's five metrics
        # under the same walk-forward cross-validation the baselines use.
        "sameFoldsAsBaselines": results.get("walk_forward_same_folds_as_baselines"),
    }


# ---------------------------------------------------------------------------
# News corpus
# ---------------------------------------------------------------------------

@functools.lru_cache(maxsize=1)
def _corpus() -> pd.DataFrame:
    """
    Relevant, geocoded articles with display fields normalised once.

    `published` arrives as a mix of ISO dates and raw RSS timestamps, and the
    topic column carries classifier hypothesis sentences. Both are cleaned here
    so no route has to reformat them.
    """
    if not CORPUS_PATH.exists():
        return pd.DataFrame()
    df = pd.read_parquet(CORPUS_PATH)
    if "is_relevant" in df.columns:
        df = df[df["is_relevant"].astype("boolean").fillna(False)].copy()

    published = pd.to_datetime(df.get("published"), errors="coerce", utc=True, format="mixed")
    # E27 fix: show the Philippine calendar date, the clock that assigns the article's quarter
    # (app.ml.corpus._dates.quarter_of_publication). A UTC date put early-morning articles on the previous day,
    # and on the first day of a quarter, visibly in the previous quarter.
    df["_date"] = published.dt.tz_convert("Asia/Manila").dt.strftime("%Y-%m-%d")
    df["_sort_date"] = published

    topics = df.get("top_topic_name")
    mapped = topics.map(lambda t: TOPIC_MAP.get(t, UNCLASSIFIED)) if topics is not None else None
    df["_topic_key"] = [m[0] for m in mapped] if mapped is not None else UNCLASSIFIED[0]
    df["_topic_label"] = [m[1] for m in mapped] if mapped is not None else UNCLASSIFIED[1]
    return df


def _e31_articles() -> list[dict]:
    return E31.record()["news"]["articles"]


def article_count(province_code: str | None, quarter: str) -> int:
    if e31_active():
        quarter = e31_news_evidence(quarter)[0]
        return sum(1 for a in _e31_articles() if a["quarter"] == quarter
                   and (province_code is None or a["province_code"] == province_code))
    df = _corpus()
    if df.empty:
        return 0
    mask = df["quarter"] == quarter
    if province_code:
        mask &= df["province_code"] == province_code
    return int(mask.sum())


def news(province_code: str | None, quarter: str, page: int, page_size: int) -> dict:
    """
    Analysed articles for a subject-quarter, with the topic mix.

    `provinceAttributed` is reported alongside the total because most of the
    corpus is not pinned to a province: for region scope the two differ sharply,
    and without it the regional count looks irreconcilable with the five
    province counts that are supposed to add up to it.
    """
    if e31_active():
        return _e31_news(province_code, quarter, page, page_size)
    df = _corpus()
    if df.empty:
        return {"articleCount": 0, "provinceAttributed": 0,
                "topics": [], "data": [], "total": 0}

    subset = df[df["quarter"] == quarter]
    if province_code:
        subset = subset[subset["province_code"] == province_code]

    province_codes = {meta["code"] for meta in ref.PROVINCES.values()}
    attributed = int(subset["province_code"].isin(province_codes).sum())

    topics = []
    if not subset.empty:
        counts = subset["_topic_label"].value_counts()
        pcts = _integer_shares(counts.tolist())
        key_of = {label: key for key, label in TOPIC_MAP.values()}
        key_of[UNCLASSIFIED[1]] = UNCLASSIFIED[0]
        topics = [
            {"key": key_of.get(label, UNCLASSIFIED[0]), "label": label,
             "count": int(v), "pct": p}
            for (label, v), p in zip(counts.items(), pcts)
        ]

    window = subset.sort_values("_sort_date", ascending=False, na_position="last")
    start = (page - 1) * page_size
    window = window.iloc[start:start + page_size]
    articles = [
        {
            "id": str(r.get("article_id") or ""),
            "title": str(r.get("title") or ""),
            "source": str(r.get("source_domain") or ""),
            "date": r["_date"] if pd.notna(r["_date"]) else None,
            "url": str(r.get("link") or ""),
            "excerpt": str(r.get("summary") or "")[:400],
            "topicKey": r["_topic_key"],
            "topicLabel": r["_topic_label"],
            "relevanceScore": (
                round(float(r["food_insecurity_score"]), 4)
                if pd.notna(r.get("food_insecurity_score")) else None
            ),
        }
        for _, r in window.iterrows()
    ]
    return {
        "articleCount": int(len(subset)),
        "provinceAttributed": attributed,
        "topics": topics,
        "data": articles,
        "total": int(len(subset)),
    }



# ---------------------------------------------------------------------------
# E31 data layer: news and model performance from the E31 record
# ---------------------------------------------------------------------------

E31_TOPICS = {"DIRECT": ("direct", "Direct food-insecurity report"),
              "INDIRECT": ("indirect", "Food-system stress (prices, losses, supply)")}


def e31_news_evidence(quarter: str) -> tuple[str, str, str]:
    """(evidence quarter, mode, note) for the news shown beside an estimate (app.news.alignment policy)."""
    r = E31.quarter_row(quarter, NOWCAST)
    if r is not None and r["mode"] == "FORECAST":
        w = r["provenance"]["news_evidence_window"]
        return (w["evidence_quarter"], "FORECAST",
                f"Supporting news for the {quarter} forecast: {w['evidence_quarter']} articles published by "
                f"{w['information_cutoff_ph'][:10]} ({w['coverage'].lower()} quarter). A forecast never uses news of "
                f"its own target quarter.")
    if r is not None and r["mode"] == "NOWCAST":
        w = r["provenance"]["news_evidence_window"]
        return (quarter, "NOWCAST", f"Same-quarter news published by {w['information_cutoff_ph'][:10]} "
                                    f"({w['days_covered']} of {w['days_in_quarter']} days).")
    return (quarter, "OBSERVED", f"News published in {quarter} (describes the quarter; its one-quarter-ahead "
                                 f"estimate was made with the previous quarter's news).")


def _e31_news(province_code: str | None, quarter: str, page: int, page_size: int) -> dict:
    """Validated articles (relevance rule R1.1) behind a subject-quarter's estimate, newest first. Titles only: the
    source gives no lead text, so the excerpt is empty rather than invented."""
    ev_q, ev_mode, ev_note = e31_news_evidence(quarter)
    quarter = ev_q
    rows = [a for a in _e31_articles() if a["quarter"] == quarter
            and (province_code is None or a["province_code"] == province_code)]
    counts: dict[str, int] = {}
    for a in rows:
        counts[a["relevance"]] = counts.get(a["relevance"], 0) + 1
    labels = list(counts)
    pcts = _integer_shares([counts[k] for k in labels])
    topics = [{"key": E31_TOPICS[k][0], "label": E31_TOPICS[k][1], "count": counts[k], "pct": p}
              for k, p in zip(labels, pcts)]
    start = (page - 1) * page_size
    data = [{"id": a["article_key"], "title": a["title"], "source": a["outlet"], "date": a["published_ph"][:10],
             "url": a["link"], "excerpt": "", "topicKey": E31_TOPICS[a["relevance"]][0],
             "topicLabel": E31_TOPICS[a["relevance"]][1], "relevanceScore": None}
            for a in rows[start:start + page_size]]
    # every validated article is province-attributed (R1.1 runs on attributed titles), so the two counts agree
    return {"articleCount": len(rows), "provinceAttributed": len(rows),
            "topics": topics, "data": data, "total": len(rows), "evidenceQuarter": ev_q, "sourceQuarter": ev_q,
            "evidenceMode": ev_mode, "evidenceNote": ev_note}


def e31_model_performance(horizon: str = DEFAULT_HORIZON) -> dict:
    """Objective 2 metrics of the served engine and the Objective 4 baselines, on the SAME walk-forward rows (E28
    frozen protocol, lead 1, development evidence), plus the one unseen quarter. Nulls stay null."""
    v = E31.record()["validation"]
    arms = v["development_metrics_T1"]["arms"]
    m = arms["PCF21_E25"]["by_lead"]["1"]

    def r(x):
        return round(x, 4) if isinstance(x, (int, float)) else None

    return {
        "horizon": horizon,
        "evaluation": v["development_metrics_T1"]["basis"],
        "maxReliableLeadTime": None,
        "accuracyThreshold": None,
        "nFeatures": 2,
        "accuracy": r(m["accuracy"]), "precision": r(m["precision"]), "recall": r(m["recall"]), "f1": r(m["f1"]),
        "rocAuc": r(m["roc_auc"]), "cvF1": None,
        "targets": {"f1": None, "rocAuc": None, "meetsF1": None, "meetsRocAuc": None,
                    "note": v["threshold_75pct"]["verdict"]},
        "leadTimeScan": [{"lead": int(L), **{k: r(x.get(k)) for k in ("accuracy", "precision", "recall", "f1",
                                                                     "roc_auc", "brier")}}
                         for L, x in arms["PCF21_E25"]["by_lead"].items()],
        "baselines": {a["label"]: r(a["by_lead"]["1"]["accuracy"]) for k, a in arms.items() if k != "PCF21_E25"},
        # the walk-forward rows ARE the baselines' rows (E28 protocol), so the same-fold figures are these
        "sameFoldsAsBaselines": {"accuracy": r(m["accuracy"]), "weighted_f1": r(m["f1"]), "roc_auc": r(m["roc_auc"])},
        "unseenQuarter": v["unseen_quarter_2026Q3"],
    }
