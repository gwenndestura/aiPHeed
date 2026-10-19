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
import unicodedata
from pathlib import Path

import pandas as pd

from app.ml.inference.disaggregator import Disaggregator
from app.ml.inference.explainer import Explainer
from app.ml.inference.predictor import Predictor
from app.ml.inference import e31_engine as E31
from app.ml.inference import e41_lead2 as E41L2
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
        "class of the composite food stress label (S1 = SWS regional hunger + "
        "2 x the province's food-CPI deviation from the five-province mean), "
        "HIGH when S1 is above the trailing median of the published quarters."
    ),
    "unit": "probability (0-1)",
    "horizon": "One quarter ahead (lead 1), issued at the start of the quarter with information published before it; "
               "not validated against the baselines (E36)",
    "source": (
        "SWS Balance Luzon hunger rounds, PSA provincial food and rice CPI, and "
        "validated Google News titles (FSSI-v2), CALABARZON, 2021 to 14 October 2026"
    ),
    "caveat": (
        "Risk rankings are indicative, not absolute. They are relative ordinal "
        "estimates of potential risk and must not be construed as official "
        "food insecurity classifications or policy recommendations."
    ),
}



def indicator_for(quarter: str) -> dict:
    """E42: the definition of the number actually served for this quarter. With AIPHEED_LEAD2_MODEL=e41/e42 the
    target quarter carries the price-pressure probability, so it must not be described as the v1 label."""
    if not (E41L2.serves(quarter) or E41L2.governs()):
        return INDICATOR
    rec = E41L2.record()
    if "indicator" in rec:                                        # E43 states the definition of its own score
        return rec["indicator"]
    return {"id": "price_pressure_probability", "name": "Food Price Pressure Probability (experimental)",
            "definition": rec["scoreTypes"]["price_pressure_probability"], "unit": "probability (0-1)",
            "horizon": f"Lead 2: issued {rec['origin']} for {rec['targetQuarter']} with information published before "
                       f"the origin; experimental, not validated (E41/E42)",
            "source": "PSA provincial food CPI (OpenStat 0012M4ACP22/23), CALABARZON, 2021-01 to "
                      + rec["information"]["cpiMonthsThrough"],
            "caveat": "Price pressure is not food insecurity. Indicative decision support only; not an official "
                      "classification or policy recommendation."}

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

# E36: the served estimates come from the E36 record (aiPHeed-E36-LGBM). Every row is lead 1, so both ids show the
# same rows; "nowcast" is kept for contract compatibility. The E31 (PCF21) record stays available via
# AIPHEED_E31_RECORD.
E31_HORIZON_INFO = {
    FORECAST: {
        "id": FORECAST, "name": "One-quarter-ahead forecasts (lead 1)",
        "question": "What did the served LightGBM estimate one quarter ahead, using only information released before "
                    "the quarter began?",
        "definition": ("aiPHeed-E36-LGBM estimates of P(S1 = H + 2D above its trailing-median threshold) one quarter "
                       "ahead: development backtests 2023-Q1..2026-Q3 (refitted at each origin, nested selection) and "
                       "the 2026-Q4 forecast frozen at origin 2026-10-01. News evidence is the previous quarter's. "
                       "Not validated: no baseline is beaten significantly (E36)."),
        "evidenceStatus": "EXPERIMENTAL", "resultsFile": "data/e36/e36_record.json"},
    NOWCAST: {
        "id": NOWCAST, "name": "Latest estimate per quarter",
        "question": "What is the best available estimate for each quarter, including the one under way?",
        "definition": ("The E36 model issues no same-quarter nowcast: every quarter, including 2026-Q4, shows its "
                       "one-quarter-ahead (lead 1) estimate, labelled with its mode."),
        "evidenceStatus": "EXPERIMENTAL", "resultsFile": "data/e36/e36_record.json"},
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


def forecast_target() -> dict:
    """The dashboard's dynamic forecast target (app/quarterly/target.py; Asia/Manila; next calendar quarter)."""
    from app.quarterly.target import forecast_target as _ft

    return _ft()


def latest_quarter(horizon: str = DEFAULT_HORIZON) -> str:
    if e31_active():
        target = forecast_target()["target_quarter"]
        served = set(available_quarters(FORECAST)) | set(available_quarters(NOWCAST))
        if target in served:
            return target                 # the dynamic next-quarter target, when its forecast exists
        older = [q for q in available_quarters(horizon) if ref.quarter_index(q) <= ref.quarter_index(target)]
        if older:                         # never relabelled: the newest quarter that HAS a record, under its own id
            return older[-1]
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
    if E41L2.governs():
        if quarter not in E41L2.candidate_quarters():
            raise QuarterNotAvailable(candidate_unavailable_reason(quarter))
        return quarter                    # E52: a CPI-only target also covers quarters without an SWS round
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
        target = forecast_target()
        last = ref.quarter_index(out[-1]["id"])
        for i in range(last + 1, ref.quarter_index(target["target_quarter"]) + 1):
            q = f"{i // 4}-Q{i % 4 + 1}"          # quarters up to the target that have no record yet
            year, qn = ref.quarter_parts(q)
            out.append({"id": q, "year": year, "q": qn, "label": f"Q{qn}", "monthsLabel": ref.QUARTER_MONTHS[qn],
                        "state": "unavailable",
                        "reason": (f"The forecast for {q} has not been generated. It is issued at the origin "
                                   f"{target['origin']} with information published before it, once those inputs "
                                   "are authorized and the forecasting pipeline has run. No older forecast is "
                                   "shown in its place.")})
    if E41L2.governs():
        have = set(E41L2.candidate_quarters())
        for r in out:
            if r["id"] not in have and r["state"] != "unavailable":
                r["state"], r["reason"] = "unavailable", candidate_unavailable_reason(r["id"])
            elif r["id"] in have and r["state"] == "unavailable":
                r["state"] = "actual"     # E52: the candidate's backtest covers a quarter the base engine lacks
                r.pop("reason", None)
    return out


def candidate_unavailable_reason(quarter: str) -> str:
    """E46: why a quarter shows no score while a Lead-2 candidate governs the dashboard."""
    qs = E41L2.candidate_quarters()
    return (f"No estimate of the served score for {quarter}. The experimental Lead-2 model ({E41L2.mode().upper()}) has "
            f"as-of estimates for {qs[0]} to {qs[-1]} (quarters with an approved SWS round); showing another model's "
            "score of a different target here would not be comparable. This is missing data, not a low score.")


def _lead2_key() -> str:
    """Cache key part: the Lead-2 mode and whether it governs every quarter at this moment (it depends on the clock)."""
    return E41L2.mode() + (":governs" if E41L2.governs() else "")


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

def _province_forecasts(quarter: str, horizon: str = DEFAULT_HORIZON) -> list[dict]:
    """Raw model output for one quarter, from whichever engine the horizon names (cache keyed by the Lead-2 mode)."""
    return _province_forecasts_cached(quarter, horizon, _lead2_key())


@functools.lru_cache(maxsize=64)
def _province_forecasts_cached(quarter: str, horizon: str, lead2_mode: str) -> list[dict]:
    # E41: with AIPHEED_LEAD2_MODEL=e41, the candidate's frozen Lead-2 forecast replaces the E38 row for exactly its
    # target quarter; every other quarter, and the default mode, are unchanged.
    if lead2_mode.endswith(":governs"):              # E46: one score on every quarter (candidate's own estimates)
        return E41L2.rows_for(quarter)
    if E41L2.serves(quarter):
        return E41L2.forecast_rows(quarter)
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


def _comparable(quarter: str, prev_q: str, horizon: str) -> bool:
    """E35-D3: a change is shown only between consecutive quarters estimated the same way (same lead; a nowcast is
    never compared with a forecast). Across a gap (2025-Q1 -> 2025-Q4) it would mix three quarters of change."""
    if ref.quarter_index(quarter) - ref.quarter_index(prev_q) != 1:
        return False
    if E41L2.governs():                              # every candidate estimate is a Lead-2 estimate of the same event
        have = set(E41L2.candidate_quarters())
        return quarter in have and prev_q in have
    if not e31_active():
        return True
    a = E31.quarter_row(quarter, horizon) or E31.quarter_row(quarter, NOWCAST if horizon == FORECAST else FORECAST)
    b = E31.quarter_row(prev_q, horizon)
    return bool(a and b) and a["lead"] == b["lead"] and (a["mode"] == "NOWCAST") == (b["mode"] == "NOWCAST")


def _qoq(current: float, quarter: str, code: str,
         horizon: str = DEFAULT_HORIZON) -> tuple[float | None, float | None]:
    """Absolute and percentage change against the previous quarter, when the two are comparable (E35-D3)."""
    prev_q = _previous_quarter(quarter, horizon)
    if prev_q is None or not _comparable(quarter, prev_q, horizon):
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
    """E35-D7: population-weighted mean of the PSA 2021 municipal SAE (2024 POPCEN weights) over the LGUs that have
    an estimate. It is not a PSA province figure and never mixes in a substitute (Lucena City has none)."""
    if e31_active() and LGU_PROVENANCE_PATH.exists():
        df = pd.read_csv(LGU_PROVENANCE_PATH, dtype={"lgu_code": str})
        df = df[df["poverty_lgu_estimate"].notna()].copy()
        df["province_code"] = df["province"].map({m["name"]: m["code"] for m in ref.PROVINCES.values()})
        df["w"] = df["population_2024"] * df["poverty_lgu_estimate"]
        g = df.groupby("province_code")[["w", "population_2024"]].sum()
        return (g["w"] / g["population_2024"]).round(1).to_dict()
    if not LGU_POVERTY_PATH.exists():
        return {}
    df = pd.read_parquet(LGU_POVERTY_PATH)
    return df.groupby("province_code")["poverty_incidence_pct"].mean().round(1).to_dict()


@functools.lru_cache(maxsize=1)
def _province_population() -> dict[str, int]:
    roster = ref.lgu_roster()
    return roster.groupby("province_code")["population_2024"].sum().astype(int).to_dict()


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
            "povertyRateBasis": POVERTY_RATE_BASIS,
            "currentQuarter": quarter,
            "riskScore": score,
            "riskLevel": ref.risk_level(score),
            "qoqChange": delta,
            "qoqChangePct": pct,
            "riskLabel": record.get("risk_label"),
            # E41: what the score is (present only for the E41 candidate; absent rows keep the E38 meaning)
            **({"scoreType": record["score_type"], "scoreDefinition": record["score_definition"],
                "riskBand": record["band"]} if record.get("score_type") else {}),
            # E46: what kind of estimate this is, and the observed outcome of the same event (backtest quarters only)
            **({"estimateKind": record["estimate_kind"], "observedOutcome": record.get("observed_label")}
               if record.get("estimate_kind") else {}),
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
        # E39: equal scores share one rank (competition ranking: 1, 1, 3, ...) instead of consecutive ranks that
        # pretended an order (five 0.40 scores were ranked 1-5). The API rank stays an integer.
        row["rank"] = 1 + sum(1 for o in published if o["riskScore"] > row["riskScore"])
        row["rankTied"] = sum(1 for o in published if o["riskScore"] == row["riskScore"]) > 1
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
        "indicator": indicator_for(quarter),
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

def _municipal_frame(quarter: str) -> pd.DataFrame:
    return _municipal_frame_cached(quarter, _lead2_key())


@functools.lru_cache(maxsize=32)
def _municipal_frame_cached(quarter: str, lead2_mode: str) -> pd.DataFrame:
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


POVERTY_RATE_BASIS = (
    "Population-weighted mean of the PSA 2021 city and municipal Small Area Estimates of poverty incidence (2024 "
    "POPCEN weights), over the cities and municipalities with an estimate; Lucena City has none (highly urbanized "
    "city, not in the PSA no-HUC table). Derived by aiPHeed; not an official PSA province figure."
)
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
    return {"povertyEstimateKind": "province substitute (no municipal estimate)",
            "povertyValueUsed": p["value_used"] if p else None,
            "povertyLimitation": ("No PSA 2021 municipal poverty estimate exists for this LGU (a highly urbanized "
                                  "city, excluded from the PSA no-HUC table). The ranking uses the province value "
                                  "stored in the aiPHeed inputs as a substitute; its source workbook is not in the "
                                  "repository, so it is unverified.")}


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
            "population": int(meta["population_2024"]),
            "densityPerKm2": float(meta["densityPerKm2"]),
            "povertyRate": poverty.get(code),
            **_poverty_provenance(code, poverty.get(code)),
            "quarter": quarter,
            "riskIndex": score,
            # E45 (user decision 2026-10-17): the approved map colours every LGU with the approved risk palette, so the
            # LGU index gets the same display band as a province (ref.risk_level, cutoff 0.50). It stays a relative
            # position from the province forecast and PSA poverty/density (riskLevelBasis), not a municipal forecast.
            # A null index keeps a null band, which the approved map shows as "No data available".
            "riskLevel": None if score is None else ref.risk_level(score),
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
    "(40%) within the province, shown on the map with the province risk colours (display cutoff 0.50). The province "
    "estimate is not validated; this is not a measured or official municipal food-insecurity classification.")


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


def _drivers(province_code: str, quarter: str) -> dict:
    return _drivers_cached(province_code, quarter, _lead2_key())


@functools.lru_cache(maxsize=256)
def _drivers_cached(province_code: str, quarter: str, lead2_mode: str) -> dict:
    if E41L2.serves(quarter):
        return E41L2.drivers(province_code, quarter)
    if lead2_mode.endswith(":governs") and E41L2.has_past_drivers(quarter):
        return E41L2.drivers(province_code, quarter)  # E47: as-of attribution refitted at that quarter's issue date
    if lead2_mode.endswith(":governs"):              # E46: backtest quarters carry no recorded attribution
        return {"drivers": [{"driver_group": g, "driver_label": lab, "group_shap": 0.0, "direction": "increases_risk",
                             "trigger_proportion": None} for g, lab in E41L2.GROUP_LABELS.items()],
                "article_count": 0, "other_pct": 0.0, "evidence_quarter": None}
    explainer = _explainer()
    records = explainer.explain_province_quarter(province_code, quarter)
    return explainer.build_drivers(province_code, quarter, records)


# E42: what each of the five trigger groups is in the served forecast, so the dashboard never states a direction for a
# group that has no model input or no official data (the "0% Weather is hurting food supply" defect).
TRIGGER_STATUS_NOTES = {
    "contributes": "This factor is a model input and moved this forecast in the direction shown.",
    "no_effect": "This factor is a model input but did not measurably move this forecast.",
    "no_model_input": "The current model has no input for this factor, so it neither raised nor lowered the score. "
                      "News shares and official indicators, where available, are shown as evidence only.",
    "no_data": "No official in-window data series exists for this factor (E41/E42 search), so it is not part of the "
               "forecast. Missing data is not evidence of low risk.",
    "data_not_in_model": "Official data for this factor exist and are shown as evidence, but the served model does "
                         "not use them, so they neither raised nor lowered the score.",
    "stale": "The latest official observation for this factor is more than two quarters old at the forecast date; "
             "treat its contribution with caution.",
    "insufficient_data": "None of this factor's inputs had a published value at this forecast's issue date, so no "
                         "contribution is reported. Missing data is not evidence of low risk.",
    "not_recorded": "This quarter shows the experimental model's backtest or earlier forecast; trigger contributions "
                    "are recorded only for the issued forecast, so no direction is stated here.",
}
NO_OFFICIAL_DATA_GROUPS = frozenset({"ofw_remittance"})
REGION_EVIDENCE_NOTE = ("Average of the five provinces' model attributions for this quarter. Open a province to see "
                        "the official figures behind this factor.")


def _model_trigger_groups(quarter: str) -> frozenset[str]:
    if E41L2.serves(quarter):
        return frozenset({"market"})
    if e31_active():
        return frozenset(g for g, fs in E31.TRIGGER_GROUP_FEATURES.items() if fs)
    return frozenset(E31.TRIGGER_GROUP_FEATURES)


def trigger_status(key: str, quarter: str, pct: int, code: str | None = None) -> str:
    if E41L2.governs() and not E41L2.serves(quarter) and not E41L2.has_past_drivers(quarter):
        return "not_recorded"
    own = E41L2.trigger_statuses(quarter, code)                  # E43 records state their own statuses
    if own and key in own:
        return "no_effect" if own[key] == "contributes" and pct == 0 else own[key]
    if key in _model_trigger_groups(quarter):
        return "contributes" if pct > 0 else "no_effect"
    return "no_data" if key in NO_OFFICIAL_DATA_GROUPS else "no_model_input"


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
            "status": (st := trigger_status(d["driver_group"], quarter, pct, province_code)),
            "statusNote": TRIGGER_STATUS_NOTES[st],
            "evidenceNote": E41L2.trigger_evidence(quarter, province_code).get(d["driver_group"]),
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
        # E36/E38: share of the model's attribution outside the five trigger groups (E20 convention)
        "otherPct": built.get("other_pct"),
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
            "status": (st := trigger_status(key, quarter, pct)),
            "statusNote": TRIGGER_STATUS_NOTES[st],
            # E47: the region pools five provinces' attributions, so it states that rather than a generic claim
            # ("prices are too high") that no regional observation supports
            "evidenceNote": (REGION_EVIDENCE_NOTE if (E41L2.serves(quarter) or E41L2.has_past_drivers(quarter))
                             else None),
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


# E52: what each experimental candidate's probability is of, in plain words
CANDIDATE_EVENTS = {
    "e58": "food-insecurity risk (high regional hunger together with provincial food-price pressure)",
    "e56": "food-insecurity risk (high regional hunger together with provincial food-price pressure)",
    "e55": "food-insecurity risk (high regional hunger together with provincial food-price pressure)",
    "e53": "food-price pressure",
    "e52": "food-price pressure",
    "e46": "food stress (high hunger together with food-price pressure)",
    "e44": "food stress (high hunger together with food-price pressure)",
    "e43": "food stress (high hunger together with food-price pressure)",
}
LIMITED_STATUSES = ("insufficient_data", "stale", "no_data")
LABEL_OF = {"market": "Market / Prices", "climate": "Climate Stress", "fish_kill": "Fish Kill",
            "employment": "Employment", "ofw_remittance": "OFW Remittance"}


def plain_summary(province_code: str | None, quarter: str, name: str, triggers: list[dict]) -> dict | None:
    """
    E52: plain-language reading of the governing experimental candidate's estimate for one subject-quarter: result
    (HIGH/LOW at 0.5), probability, target quarter, the top two or three contributing groups with direction and
    evidence, data status and one sentence. None unless a Lead-2 candidate governs the dashboard and covers the
    quarter. Region scope uses the mean of the five provincial probabilities and carries no province evidence.
    ASCII only (PDF export).
    """
    if not E41L2.governs():
        return None
    rows = E41L2.rows_for(quarter)
    if not rows:
        return None
    if province_code:
        rows = [r for r in rows if r["province_code"] == province_code]
        if not rows:
            return None
    p = sum(r["risk_probability"] for r in rows) / len(rows)
    kind = rows[0]["estimate_kind"]
    obs = rows[0]["observed_label"] if province_code else None
    result = "HIGH" if p >= 0.5 else "LOW"
    event = CANDIDATE_EVENTS.get(E41L2.mode(), "the experimental Lead-2 score")

    statuses = {t["key"]: t["status"] for t in triggers}
    contributing = [t for t in triggers if t["status"] == "contributes" and t["pct"] > 0]
    reasons = [t for t in contributing if t["pct"] >= 10][:3] or contributing[:1]
    if "not_recorded" in statuses.values() or not triggers:
        data_status, data_note = "unavailable", "Factor contributions were not recorded for this estimate."
        reasons = []
    else:
        limited = [t["label"] for t in triggers if t["status"] in LIMITED_STATUSES]
        thin = any(r["data_sufficiency_flag"] != "SUFFICIENT" for r in rows)
        partial = E41L2.partial_inputs(quarter, province_code)     # E53: groups with some inputs missing at issue
        partial = [LABEL_OF.get(g, g) for g in partial if LABEL_OF.get(g, g) not in limited]
        if limited or thin or partial:
            data_status = "limited"
            data_note = "; ".join(filter(None, [
                f"no current observation for {', '.join(limited)}" if limited else "",
                f"some inputs not available at the issue date for {', '.join(partial)}" if partial else "",
                "few news articles this quarter" if thin else ""]))
            data_note = data_note[0].upper() + data_note[1:] + "."     # not str.capitalize(): keeps group names
        else:
            data_status, data_note = "sufficient", "Every factor group had observed data at the issue date."

    def verb(t: dict) -> str:
        return "raised" if t["direction"] == "increases_risk" else "lowered"

    if kind == "forecast":
        head = f"{event[0].upper()}{event[1:]} in {name} for {quarter} is forecast {result} ({p:.0%} probability)"
    elif kind == "earlier_forecast":
        head = (f"The earlier Lead-2 forecast of {event} in {name} for {quarter} was {result} ({p:.0%} probability; "
                f"outcome not yet published)")
    else:
        head = (f"The backtest estimate of {event} in {name} for {quarter} was {result} ({p:.0%} probability"
                + (f"; observed {obs})" if obs else ")"))
    comp = _forecast_components(province_code, quarter) if kind == "forecast" else None
    if comp:
        # E61: the two parts are not independent, so their product is a score, not a tested probability (same value)
        head = (f"{event[0].upper()}{event[1:]} in {name} for {quarter} is forecast {result} (model score {p:.0%}: the "
                f"two parts that follow, multiplied together; not a tested probability)")
    if reasons:
        parts = [f"{t['label']} {verb(t)} it" for t in reasons]
        why = parts[0] if len(parts) == 1 else ", ".join(parts[:-1]) + " and " + parts[-1]
        if comp:
            # E61: say which of the two required conditions makes the estimate low or high before naming factors
            sentence = (f"{head}: regional hunger is {_likely(comp['hunger'])} to stay above 11.3% "
                        f"({comp['hunger']:.0%}) and provincial food-price pressure is {_likely(comp['price'])} "
                        f"({comp['price_text']}); the target needs both. Within the price part, {why}.")
        else:
            sentence = f"{head}, mainly because {why}."
    else:
        sentence = f"{head}; no factor breakdown is available for it."
    # E58: the two-signal early warning (model warning for DA review), appended to the same sentence field
    warnings = E41L2.early_warning(quarter, province_code)
    if province_code and warnings:
        text = warnings[0]["text"]
        if comp:                                         # same wording rule as the head (record text kept as stored)
            text = text.replace("HIGH-risk probability", "HIGH-risk score")
        sentence = f"{sentence} {text}"
    elif warnings:
        active = [w for w in warnings if w["warn"]]
        sentence += (" Early warnings: " + "; ".join(f"{w['province']} {w['level']} ({w['direction']})" for w in active) + "."
                     if active else " No province has an early warning for this quarter.")
    # E61: what a two-part forecast does and does not mean goes into the same sentence field the dashboard already
    # shows, so the approved layout is unchanged (no new UI element)
    # E62: the employment note follows every group drawn as a bar (contributing), not only the named reasons, so a
    # province whose Employment bar is below the 10% naming line (Rizal, Batangas 2027-Q1) still gets it
    caveat = (_forecast_caveat(province_code, comp, contributing,
                               [LABEL_OF.get(g, g) for g in E41L2.partial_inputs(quarter, province_code)])
              if comp else None)
    if caveat:
        sentence = f"{sentence} {caveat}"
    return {
        "event": event, "targetQuarter": quarter, "estimateKind": kind,
        "issued": rows[0]["origin"], "probability": round(p, 4), "result": result, "observedOutcome": obs,
        "reasons": [{"key": t["key"], "label": t["label"], "direction": t["direction"], "pct": t["pct"],
                     "evidence": t.get("evidenceNote")} for t in reasons],
        "dataStatus": data_status, "dataStatusNote": data_note, "sentence": _ascii(sentence),
        **({"earlyWarning": warnings} if warnings else {}),
        **({"components": {"probabilityHungerElevated": round(comp["hunger"], 4),
                           "probabilityPricePressure": round(comp["price"], 4),
                           "combination": "product of the two parts (an approximation: the two conditions are not "
                                          "independent; the joint probability cannot exceed the smaller part)"},
            "caveat": _ascii(caveat)} if comp else {}),
    }


# E61 (aipheed-backend-aligned/experiments/E61_E58_Low_Forecast_Investigation, out/a2_calibration_joint.json,
# low_probability_cutoffs["E56_p_price<0.2"]): in the 50-row rolling-origin back-test, 3 of 11 price-part probabilities
# below 0.2 were followed by a HIGH outcome (Wilson 95% CI 10%-57%). Checked against that file by a test.
E61_LOW_PRICE_BACKTEST = {"n": 11, "high": 3, "cutoff": 0.2}


def _likely(p: float) -> str:
    return "likely" if p >= 0.5 else "unlikely"


def _forecast_components(province_code: str | None, quarter: str) -> dict | None:
    """E61: the two parts of a Lead-2 record's issued forecast (records E55+ store them); region = province range."""
    rec = E41L2.record()
    if quarter != rec.get("targetQuarter"):
        return None
    provs = rec["provinces"]
    comps = {c: v.get("forecast", {}).get("components") or {} for c, v in provs.items()}
    if not all({"probabilityHungerElevated", "probabilityPricePressure"} <= set(c) for c in comps.values()):
        return None                                     # E43-E53 records store other components (or a price-only target)
    if province_code:
        c = comps[province_code]
        return {"hunger": c["probabilityHungerElevated"], "price": c["probabilityPricePressure"],
                "price_text": f"{c['probabilityPricePressure']:.0%}", "entry": provs[province_code]}
    prices = [c["probabilityPricePressure"] for c in comps.values()]
    lo, hi = min(prices), max(prices)
    return {"hunger": sum(c["probabilityHungerElevated"] for c in comps.values()) / len(comps),
            "price": sum(prices) / len(prices),
            "price_text": f"{lo:.0%} to {hi:.0%} across the five provinces" if round(lo, 2) != round(hi, 2) else f"{lo:.0%}",
            "entry": None}


def _forecast_caveat(province_code: str | None, comp: dict, shown: list[dict], partial: list[str] = ()) -> str:
    """E61: what the low/high value does and does not mean, from the record's own observations only. `shown` is every
    factor group with a non-zero contribution (each drawn as a bar)."""
    out = []
    v = comp["entry"]
    if v is not None:
        ob = v.get("observed", {})
        f, g = ob.get("foodInflationLatestMonths", {}), ob.get("foodMinusHeadline", {})
        h = ob.get("hungerRegional", {})
        months = E41L2.record().get("dataFreshness", {}).get("latestPredictorPeriods", {})
        cpi_to = next((p for k, p in months.items() if "CPI YoY" in k), None)
        if f.get("value") is not None and g.get("value") is not None:
            headline = f["value"] - g["value"]
            out.append(f"Food prices in {v['name']} were {f['value']:.1f}% higher than a year earlier"
                       + (f" (latest months to {cpi_to})" if cpi_to else "")
                       + f"; the price condition needs more than {f["provinceReferenceP60"]:.2f}% (this province's "
                       f"usual 2021-2022 level) or food prices rising faster than prices overall.")
            if headline > f["value"]:
                out.append(f"Prices overall rose faster ({headline:.1f}%), which this target counts as less "
                           f"food-price pressure, although it also means a peso buys less.")
        if h.get("value") is not None:
            out.append(f"Regional hunger (SWS, Balance Luzon) was {h['value']:.1f}% in {h['quarter']}, "
                       f"{'above' if h['value'] > 11.3 else 'at or below'} the 11.3% line.")
        if comp["price"] < 0.5:
            out.append("Slower food inflation does not mean food has become affordable; it means prices are rising "
                       "more slowly.")
        emp = ob.get("employment", {})
        if (any(r["key"] == "employment" and r["direction"] == "protective" for r in shown)
                and (emp.get("unemploymentChangeYoY") or 0) > 0):
            out.append(f"The model lowered its estimate while national unemployment rose "
                       f"({emp['unemploymentChangeYoY']:+.2f} points); this is a statistical pattern in a short "
                       f"history, not evidence that job losses reduce food stress.")
    if partial:
        # E61: a LightGBM split sends a missing input down a branch learned from other missing rows, so the group's
        # attribution then reflects the missing value, not an observed figure
        out.append(f"Some {', '.join(partial)} figures were not yet published when the forecast was issued; the "
                   f"model's effect for {'that group' if len(partial) == 1 else 'those groups'} partly or wholly reflects "
                   f"how it handles a missing figure, not an observed value.")
    if comp["price"] < E61_LOW_PRICE_BACKTEST["cutoff"]:
        b = E61_LOW_PRICE_BACKTEST
        out.append(f"In back-tests, {b['high']} of {b['n']} price-pressure probabilities below "
                   f"{b['cutoff']:.0%} were followed by HIGH, so a low value can miss emerging stress; treat it "
                   f"as uncertain.")
    out.append("This is an experimental forecast of a food-stress risk indicator (SWS regional hunger and PSA "
               "food prices), not a measure of household food insecurity.")
    return " ".join(out)


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


# Kept from the main backend when E31 was promoted (E34): the plain-language report helpers
# (plain_report, report_data, report_text) import these. Pure text functions; the E31 data layer
# does not call them.
# Typographic characters that reach this module through labels or names and
# break jsPDF/reportlab. Anything else non-ASCII is decomposed and dropped.
_ASCII_FOLD = str.maketrans({
    "\u2014": "-", "\u2013": "-", "\u2012": "-", "\u2212": "-",
    "\u2018": "'", "\u2019": "'", "\u201c": '"', "\u201d": '"',
    "\u00b7": "-", "\u2026": "...", "\u00a0": " ",
})


def _ascii(text: str) -> str:
    folded = unicodedata.normalize("NFKD", text.translate(_ASCII_FOLD))
    return folded.encode("ascii", "ignore").decode("ascii")


def _join_series(items: list[str]) -> str:
    if len(items) <= 1:
        return "".join(items)
    if len(items) == 2:
        return f"{items[0]} and {items[1]}"
    return f"{', '.join(items[:-1])}, and {items[-1]}"


def compose_formal_interpretation(
    name: str, quarter: str, triggers: list[dict], other_pct: float = 0.0,
    withheld: bool = False, brief: bool = False,
) -> str:
    """
    Third-person, academic interpretation of a breakdown, for the PDF report.

    The on-screen caption stays with compose_narrative(); this is the formal
    counterpart the exported report prints under "Interpretation". Every
    sentence is driven by the actual shares and signs, so two quarters with
    different SHAP output never read the same. Plain ASCII for the same reason
    as compose_narrative().

    `withheld` reports the province-quarter as withheld from publication and
    nothing else. `brief` shortens the closing "other share" explanation for
    multi-province reports, where the table caption already defines it.
    """
    period = quarter.replace("-", " ")
    if withheld:
        return _ascii(
            f"The SHAP breakdown for {name} in {period} is withheld from publication."
        )
    if not triggers:
        return _ascii(
            f"No SHAP breakdown is available for {name} in {period}. "
            f"Consequently, the contribution of the driver groups to the forecast "
            f"for this period cannot be interpreted."
        )

    def effect(t: dict) -> str:
        return ("increases the predicted Risk Level score" if t["direction"] == "increases_risk"
                else "decreases the predicted Risk Level score")

    def tag(t: dict) -> str:
        sign = "increasing" if t["direction"] == "increases_risk" else "decreasing"
        return f"{t['label']} ({t['pct']}%, {sign})"

    cutoff = ref.TRIGGER_RED_CUTOFF
    ranked = sorted(triggers, key=lambda t: t["pct"], reverse=True)
    top = ranked[0]
    above = [t for t in ranked if t["pct"] > cutoff]
    below = [t for t in ranked if t["pct"] <= cutoff]
    n = len(ranked)

    sentences = [
        f"For {name} in {period}, the SHAP decomposition assigns the largest share "
        f"of the attributed model output among the {n} driver groups to "
        f"{top['label']} ({top['pct']}%), which {effect(top)}."
    ]

    if not above:
        sentences.append(
            f"No driver group exceeds the {cutoff}% even-share cutoff, indicating that "
            f"the attributed output is distributed approximately evenly across the groups."
        )
    else:
        raising = [f"{t['label']} ({t['pct']}%)" for t in above if t["direction"] == "increases_risk"]
        lowering = [f"{t['label']} ({t['pct']}%)" for t in above if t["direction"] != "increases_risk"]
        if len(above) == 1:
            sentences.append(
                f"{top['label']} is the only driver group whose share exceeds the "
                f"{cutoff}% even-share cutoff."
            )
        else:
            clauses = []
            if raising:
                verb = "increases" if len(raising) == 1 else "increase"
                clauses.append(f"{_join_series(raising)} {verb} the predicted Risk Level score")
            if lowering:
                verb = "decreases" if len(lowering) == 1 else "decrease"
                clauses.append(f"{_join_series(lowering)} {verb} it")
            sentences.append(
                f"Among the {len(above)} groups exceeding the {cutoff}% even-share "
                f"cutoff, {', whereas '.join(clauses)}."
            )

    if below:
        active = [t for t in below if t["pct"] > 0]
        silent = [t["label"] for t in below if t["pct"] == 0]
        if active:
            verb = "falls" if len(active) == 1 else "fall"
            sentences.append(
                f"By comparison, {_join_series([tag(t) for t in active])} {verb} at or "
                f"below the cutoff and therefore exert{'s' if len(active) == 1 else ''} "
                f"a comparatively limited influence on the forecast."
            )
        if silent:
            verb = "receives" if len(silent) == 1 else "receive"
            sentences.append(
                f"{_join_series(silent)} {verb} no measurable share in this period."
            )
        # In brief mode a single group above the cutoff has already been
        # stated with its share, so the totals would only repeat it.
        if above and not (brief and len(above) == 1):
            sentences.append(
                f"Taken together, the groups above the cutoff account for "
                f"{sum(t['pct'] for t in above)}% of the attributed share, compared with "
                f"{sum(t['pct'] for t in below)}% for the groups at or below it."
            )

    if other_pct >= 1.0 and brief:
        sentences.append(
            f"The {n} groups represent {round(100 - other_pct, 1)}% of the total "
            f"SHAP-explained output; the remaining {other_pct}% comes from the Food Stress "
            f"Sentiment Index features, which are reported separately."
        )
    elif other_pct >= 1.0:
        sentences.append(
            f"The percentages above are normalized among the {n} driver groups, which "
            f"together represent {round(100 - other_pct, 1)}% of the total SHAP-explained "
            f"output. The remaining {other_pct}% is attributable to model inputs outside "
            f"these groups, namely the Food Stress Sentiment Index (FSSI), its values in the "
            f"two preceding quarters, and its acceleration. These inputs are reported "
            f"separately rather than allocated to any single driver group."
        )

    return _ascii(" ".join(sentences))


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
        # E45: the same restored feed window the news panel lists, so every surface quotes one count
        return len(_feed_window(province_code, e31_news_evidence(quarter)[0])[0])
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


def _lead2_news_evidence(quarter: str) -> tuple[str, str, str] | None:
    """E62: when a Lead-2 candidate governs, the news beside an estimate follows THAT estimate's timing, not E31's
    one-quarter-ahead rule. A Lead-2 estimate of quarter q is made as of day 1 of q-1 with news of q-2, so an earlier
    forecast (2026-Q4, issued 2026-07-01) is shown with 2026-Q2 news, never with articles published after its issue
    date; a backtest quarter still shows its own news, with the correct timing note."""
    if not E41L2.governs() or quarter not in E41L2.candidate_quarters():
        return None
    rows = E41L2.rows_for(quarter)
    if not rows:
        return None
    kind, origin = rows[0]["estimate_kind"], rows[0]["origin"]
    news_q = _shift_q(quarter, -2)
    if kind in ("forecast", "earlier_forecast"):
        return (news_q, "FORECAST",
                f"Supporting news for the {quarter} forecast: {news_q} articles published before {origin}, its issue "
                f"date (full quarter). This two-quarter-ahead forecast uses news of the quarter before its issue date, "
                f"never news published after it or of its own target quarter.")
    return (quarter, "OBSERVED",
            f"News published in {quarter} (describes the quarter; its two-quarter-ahead estimate was made as of "
            f"{origin} with {news_q} news).")


def e31_news_evidence(quarter: str) -> tuple[str, str, str]:
    """(evidence quarter, mode, note) for the news shown beside an estimate (app.news.alignment policy)."""
    lead2 = _lead2_news_evidence(quarter)
    if lead2 is not None:
        return lead2
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


TRIGGER_LABELS = {"market": "Market / Prices", "climate": "Climate Stress", "fish_kill": "Fish Kill",
                  "employment": "Employment", "ofw_remittance": "OFW Remittance"}
FEED_MIN_ARTICLES, FEED_MAX_BACK = 5, 3
# A trigger keyword alone ("flood", "price surge") also matches politics and transport stories; an unvalidated title
# must additionally name a food, farm, fisheries, livelihood or remittance context to enter the feed.
FOOD_CONTEXT = __import__("re").compile(
    r"\b(food|rice|bigas|palay|farm\w*|crop\w*|harvest\w*|agri\w*|fish\w*|aquaculture|livestock|poultry|pork|hog\w*|"
    r"chicken|egg\w*|vegetable\w*|sugar|corn|coconut|drought|tagtuyot|el ni[nñ]o|hunger|gutom|nutrition|"
    r"livelihood\w*|remittance\w*|ofws?|jobless\w*|unemploy\w*|layoff\w*|retrench\w*|pagkain|presyo|irrigation|"
    r"water crisis|water shortage|dry spell)\b", __import__("re").IGNORECASE)


@functools.lru_cache(maxsize=1)
def _news_pool() -> list[dict]:
    """E45: the dashboard news feed pool. Province-attributed titles from the E31 store that are either validated
    by relevance rule R1.1 (the articles behind FSSI-v2) or match a food-stress trigger keyword
    (app/ml/nlp/trigger_classifier.py). Titles that only pass the generic food filter (restaurant guides, PPE
    production, ...) are excluded. Every article keeps its publisher date; all were collected retrospectively."""
    import json as _json

    from app.ml.nlp.trigger_classifier import classify_triggers

    validated = {a["article_key"]: a for a in _e31_articles()}
    path = E31.NEWS_STORE / "articles.jsonl"
    codes = {meta["code"]: meta["name"] for meta in ref.PROVINCES.values()}
    pool, seen = [], set()
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            a = _json.loads(line)
            code = a.get("geo_province_code")
            if code not in codes or a["article_key"] in seen:
                continue
            title = (a.get("title") or "").strip()
            trig = classify_triggers(title)
            v = validated.get(a["article_key"])
            if v is None and not (trig and FOOD_CONTEXT.search(title)):
                continue
            seen.add(a["article_key"])
            pool.append({
                "key": a["article_key"], "title": title, "outlet": a.get("source_domain") or "",
                "date": (a.get("published_ph") or a.get("ph_date") or "")[:10], "quarter": a["quarter"],
                "province_code": code, "province": codes[code], "link": a.get("link") or "",
                "status": "validated" if v is not None else "trigger_match",
                "relevance": v["relevance"] if v is not None else None, "triggers": trig,
                "retrospective": str(a.get("first_seen_at", ""))[:10] > (a.get("ph_date") or "")[:10],
            })
    pool.sort(key=lambda r: r["date"], reverse=True)
    return pool


def _feed_window(province_code: str | None, ev_q: str) -> tuple[list[dict], list[str]]:
    pool = [r for r in _news_pool() if province_code is None or r["province_code"] == province_code]
    quarters, rows = [], []
    for back in range(FEED_MAX_BACK + 1):
        quarters.append(_shift_q(ev_q, -back))
        rows = [r for r in pool if r["quarter"] in quarters]
        if len(rows) >= FEED_MIN_ARTICLES:
            break
    return rows, quarters


def _shift_q(q: str, k: int) -> str:
    i = int(q[:4]) * 4 + int(q[-1]) - 1 + k
    return f"{i // 4}-Q{i % 4 + 1}"


def _e31_news(province_code: str | None, quarter: str, page: int, page_size: int) -> dict:
    """E45: the restored feed (validated + trigger-matched titles) for the estimate's evidence window, newest first."""
    ev_q, ev_mode, ev_note = e31_news_evidence(quarter)
    rows, window = _feed_window(province_code, ev_q)
    counts: dict[str, int] = {}
    for r in rows:
        k = r["relevance"] or "TRIGGER"
        counts[k] = counts.get(k, 0) + 1
    labels = list(counts)
    pcts = _integer_shares([counts[k] for k in labels])
    names = {**E31_TOPICS, "TRIGGER": ("trigger_match", "Food-stress trigger keyword match (not validated)")}
    topics = [{"key": names[k][0], "label": names[k][1], "count": counts[k], "pct": p} for k, p in zip(labels, pcts)]
    start = (page - 1) * page_size
    data = [{"id": r["key"], "title": r["title"], "source": r["outlet"], "date": r["date"], "url": r["link"],
             "excerpt": "", "topicKey": names[r["relevance"] or "TRIGGER"][0],
             "topicLabel": names[r["relevance"] or "TRIGGER"][1], "relevanceScore": None,
             "relevanceStatus": r["status"],
             "relevanceLabel": ("Validated food-stress article (rule R1.1)" if r["status"] == "validated"
                                else "Trigger keyword match (not validated by rule R1.1)"),
             "province": r["province"], "provinceCode": r["province_code"],
             "triggers": [TRIGGER_LABELS[t] for t in r["triggers"]], "quarter": r["quarter"],
             "collectedRetrospectively": r["retrospective"]}
            for r in rows[start:start + page_size]]
    n_val = sum(r["status"] == "validated" for r in rows)
    note = (f"{len(rows)} article(s) from {', '.join(sorted(window))}: {n_val} validated by rule R1.1 and "
            f"{len(rows) - n_val} matched by food-stress trigger keywords. Headlines only (the source gives no lead "
            f"text). Collected retrospectively in October 2026 by publication date"
            + ("; the window was extended to earlier quarters because the evidence quarter had fewer than "
               f"{FEED_MIN_ARTICLES} articles." if len(window) > 1 else "."))
    return {"articleCount": len(rows), "provinceAttributed": len(rows), "topics": topics, "data": data,
            "total": len(rows), "evidenceQuarter": ev_q, "sourceQuarter": ev_q, "evidenceMode": ev_mode,
            "evidenceNote": ev_note, "windowQuarters": sorted(window), "validatedCount": n_val,
            "triggerMatchCount": len(rows) - n_val, "feedNote": note}


def _e31_news_validated_only(province_code: str | None, quarter: str, page: int, page_size: int) -> dict:
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
    rec = E31.record()
    v = rec["validation"]

    def r(x):
        return round(x, 4) if isinstance(x, (int, float)) else None

    if rec.get("schema") == "e36/1":
        # E36: the served LightGBM and the six Chapter I baselines on identical lead-1 rows (nested walk-forward).
        ev = v["model_evaluation"]
        rows = {x["key"]: x for x in ev["rows"]}
        m = rows["E36-LGBM"]
        return {
            "horizon": horizon, "evaluation": ev["basis"], "maxReliableLeadTime": None, "accuracyThreshold": None,
            "nFeatures": len(rec["served_engine"]["config"]["features"]),
            "accuracy": r(m["accuracy_lead1"]), "precision": r(m["precision"]), "recall": r(m["recall"]),
            "f1": r(m["f1"]), "rocAuc": r(m["roc_auc"]), "cvF1": None,
            "correct": m["correct"], "n": m["n"], "accuracyCi95": m["accuracy_ci95"],
            "balancedAccuracy": r(m["balanced_accuracy"]), "brier": r(m["brier"]),
            "targets": {"f1": None, "rocAuc": None, "meetsF1": None, "meetsRocAuc": None,
                        "note": v["threshold_75pct"]["verdict"]},
            "leadTimeScan": [{"lead": 1, "accuracy": r(m["accuracy_lead1"]), "precision": r(m["precision"]),
                              "recall": r(m["recall"]), "f1": r(m["f1"]), "roc_auc": r(m["roc_auc"]),
                              "brier": r(m["brier"])}],
            "baselines": {x["arm"]: r(x["accuracy_lead1"]) for k, x in rows.items() if k != "E36-LGBM"},
            "sameFoldsAsBaselines": {"accuracy": r(m["accuracy_lead1"]), "weighted_f1": r(m["f1"]),
                                     "roc_auc": r(m["roc_auc"])},
            "unseenQuarter": v["prospective_2026Q4"],
        }

    arms = v["development_metrics_T1"]["arms"]
    m = arms["PCF21_E25"]["by_lead"]["1"]

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
