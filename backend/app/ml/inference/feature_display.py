"""
app/ml/inference/feature_display.py
-------------------------------------
Human-readable display names, groupings, and unit labels for all 45
LightGBM input features.

Used by:
  - explainer.py   → annotates SHAP records before DB insert
  - API schemas    → surfaced to the dashboard as display_name / feature_group

Groups (5 categories matching the dashboard Risk Drivers panel):
  market       — food prices, rice, commodities, CPI gap
  climate      — typhoons, rainfall, ENSO, drought
  employment   — unemployment, poverty
  macro_ofw    — OFW remittances, FX rate, fuel prices
  nlp          — FSSI sentiment score and NLP trigger proportions
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# FEATURE_DISPLAY_MAP
# ---------------------------------------------------------------------------
# key   : raw feature name (matches FEATURE_COLS in predictor.py / explainer.py)
# value : dict with:
#   display_name  — short human-readable label for the dashboard
#   feature_group — one of: market | climate | employment | macro_ofw | nlp
#   unit          — display unit string (for tooltip / detail panel)
# ---------------------------------------------------------------------------

FEATURE_DISPLAY_MAP: dict[str, dict[str, str]] = {
    # ── Food & Market Prices ────────────────────────────────────────────────
    "food_cpi": {
        "display_name": "Food CPI Level",
        "feature_group": "market",
        "unit": "index",
    },
    "food_cpi_yoy": {
        "display_name": "Food CPI YoY Growth",
        "feature_group": "market",
        "unit": "% change",
    },
    "food_cpi_yoy_lag1": {
        "display_name": "Food CPI Growth (Prior Qtr)",
        "feature_group": "market",
        "unit": "% change",
    },
    "food_cpi_yoy_accel": {
        "display_name": "Food CPI Growth Acceleration",
        "feature_group": "market",
        "unit": "Δ pp",
    },
    "food_minus_headline_yoy": {
        "display_name": "Food vs Headline CPI Gap",
        "feature_group": "market",
        "unit": "pp",
    },
    "food_minus_headline_yoy_lag1": {
        "display_name": "Food vs Headline Gap (Prior Qtr)",
        "feature_group": "market",
        "unit": "pp",
    },
    "food_minus_headline_yoy_accel": {
        "display_name": "Food vs Headline Gap Acceleration",
        "feature_group": "market",
        "unit": "Δ pp",
    },
    "headline_cpi": {
        "display_name": "Headline CPI",
        "feature_group": "market",
        "unit": "index",
    },
    "rice_price_regular": {
        "display_name": "Rice Price (Regular Milled)",
        "feature_group": "market",
        "unit": "PHP/kg",
    },
    "rice_price_regular_lag1": {
        "display_name": "Rice Price (Prior Quarter)",
        "feature_group": "market",
        "unit": "PHP/kg",
    },
    "rice_price_regular_accel": {
        "display_name": "Rice Price Change",
        "feature_group": "market",
        "unit": "PHP/kg Δ",
    },
    # ── Commodity Basket ───────────────────────────────────────────────────
    "commodity_fruit_veg": {
        "display_name": "Fruit & Vegetable Prices",
        "feature_group": "market",
        "unit": "PHP/kg",
    },
    "commodity_leafy_veg": {
        "display_name": "Leafy Vegetable Prices",
        "feature_group": "market",
        "unit": "PHP/kg",
    },
    "commodity_livestock": {
        "display_name": "Livestock Prices",
        "feature_group": "market",
        "unit": "PHP/kg",
    },
    "commodity_poultry": {
        "display_name": "Poultry Prices",
        "feature_group": "market",
        "unit": "PHP/kg",
    },
    "commodity_rootcrops": {
        "display_name": "Root Crop Prices",
        "feature_group": "market",
        "unit": "PHP/kg",
    },
    # ── Climate & Natural Hazards ──────────────────────────────────────────
    "tc_count": {
        "display_name": "Typhoon Count",
        "feature_group": "climate",
        "unit": "count",
    },
    "tc_severe_flag": {
        "display_name": "Severe Typhoon",
        "feature_group": "climate",
        "unit": "flag (0/1)",
    },
    "rainfall_anomaly_pct": {
        "display_name": "Rainfall Anomaly",
        "feature_group": "climate",
        "unit": "% vs normal",
    },
    "rainfall_anomaly_pct_lag1": {
        "display_name": "Rainfall Anomaly (Prior Qtr)",
        "feature_group": "climate",
        "unit": "% vs normal",
    },
    "rainfall_anomaly_pct_accel": {
        "display_name": "Rainfall Anomaly Change",
        "feature_group": "climate",
        "unit": "Δ pp",
    },
    "drought_alert": {
        "display_name": "Drought Alert",
        "feature_group": "climate",
        "unit": "flag (0/1)",
    },
    "enso_numeric": {
        "display_name": "ENSO Phase",
        "feature_group": "climate",
        "unit": "-1 La Niña / 0 Neutral / +1 El Niño",
    },
    # ── Employment & Poverty ───────────────────────────────────────────────
    "unemployment_rate": {
        "display_name": "Unemployment Rate",
        "feature_group": "employment",
        "unit": "%",
    },
    "unemployment_rate_lag1": {
        "display_name": "Unemployment Rate (Prior Qtr)",
        "feature_group": "employment",
        "unit": "%",
    },
    "unemployment_rate_accel": {
        "display_name": "Unemployment Rate Change",
        "feature_group": "employment",
        "unit": "Δ pp",
    },
    "poverty_incidence": {
        "display_name": "Poverty Incidence",
        "feature_group": "employment",
        "unit": "%",
    },
    # ── OFW Remittances & Macroeconomic ────────────────────────────────────
    "ofw_remit_yoy_pct": {
        "display_name": "OFW Remittance Growth",
        "feature_group": "macro_ofw",
        "unit": "% YoY",
    },
    "ofw_remit_yoy_pct_lag1": {
        "display_name": "OFW Remittance Growth (Prior Qtr)",
        "feature_group": "macro_ofw",
        "unit": "% YoY",
    },
    "ofw_remit_yoy_pct_accel": {
        "display_name": "OFW Remittance Change",
        "feature_group": "macro_ofw",
        "unit": "Δ pp",
    },
    "fx_usd_php_avg": {
        "display_name": "USD/PHP Exchange Rate",
        "feature_group": "macro_ofw",
        "unit": "PHP per USD",
    },
    "diesel_php_per_l": {
        "display_name": "Diesel Price",
        "feature_group": "macro_ofw",
        "unit": "PHP/L",
    },
    "diesel_php_per_l_lag1": {
        "display_name": "Diesel Price (Prior Quarter)",
        "feature_group": "macro_ofw",
        "unit": "PHP/L",
    },
    "diesel_php_per_l_accel": {
        "display_name": "Diesel Price Change",
        "feature_group": "macro_ofw",
        "unit": "PHP/L Δ",
    },
    "gasoline_php_per_l": {
        "display_name": "Gasoline Price",
        "feature_group": "macro_ofw",
        "unit": "PHP/L",
    },
    "brent_usd_per_bbl": {
        "display_name": "Brent Crude Oil Price",
        "feature_group": "macro_ofw",
        "unit": "USD/bbl",
    },
    # ── NLP Sentiment (FSSI) ───────────────────────────────────────────────
    "FSSI": {
        "display_name": "Food Stress Sentiment Index",
        "feature_group": "nlp",
        "unit": "score 0–1",
    },
    "FSSI_lag1": {
        "display_name": "FSSI (Prior Quarter)",
        "feature_group": "nlp",
        "unit": "score 0–1",
    },
    "FSSI_lag2": {
        "display_name": "FSSI (2 Quarters Prior)",
        "feature_group": "nlp",
        "unit": "score 0–1",
    },
    "FSSI_accel": {
        "display_name": "FSSI Acceleration",
        "feature_group": "nlp",
        "unit": "Δ score",
    },
    # ── NLP Trigger Proportions ────────────────────────────────────────────
    "trigger_market": {
        "display_name": "Market & Price News Signal",
        "feature_group": "nlp",
        "unit": "proportion 0–1",
    },
    "trigger_climate": {
        "display_name": "Climate & Hazard News Signal",
        "feature_group": "nlp",
        "unit": "proportion 0–1",
    },
    "trigger_employment": {
        "display_name": "Employment News Signal",
        "feature_group": "nlp",
        "unit": "proportion 0–1",
    },
    "trigger_ofw_remittance": {
        "display_name": "OFW Remittance News Signal",
        "feature_group": "nlp",
        "unit": "proportion 0–1",
    },
    "trigger_fish_kill": {
        "display_name": "Fish Kill / Aquaculture News Signal",
        "feature_group": "nlp",
        "unit": "proportion 0–1",
    },
}


# ---------------------------------------------------------------------------
# Food-availability target features (added 2026-09-01)
# ---------------------------------------------------------------------------
# The model predicts a production shortfall per province-commodity series, so
# the series' own history and its position in the annual cycle are first-class
# drivers. Empirically they are the strongest: the annual cycle alone was worth
# +0.11 accuracy.
FEATURE_DISPLAY_MAP.update({
    "shock_lag1":   {"display_name": "Shortfall last quarter",
                     "feature_group": "series_history", "unit": "0/1"},
    "shock_lag2":   {"display_name": "Shortfall two quarters ago",
                     "feature_group": "series_history", "unit": "0/1"},
    "dev_lag1":     {"display_name": "Deviation from normal, last quarter",
                     "feature_group": "series_history", "unit": "%"},
    "group_code":   {"display_name": "Commodity group",
                     "feature_group": "series_history", "unit": "code"},
    "province_idx": {"display_name": "Province",
                     "feature_group": "series_history", "unit": "code"},
    "commodity_te": {"display_name": "Commodity historical shortfall rate",
                     "feature_group": "series_history", "unit": "rate"},
    "shock_lag4":   {"display_name": "Shortfall same quarter last year",
                     "feature_group": "seasonal", "unit": "0/1"},
    "dev_lag4":     {"display_name": "Deviation same quarter last year",
                     "feature_group": "seasonal", "unit": "%"},
    "dev_roll4":    {"display_name": "Average deviation, past year",
                     "feature_group": "seasonal", "unit": "%"},
    "series_vol":   {"display_name": "Series volatility",
                     "feature_group": "seasonal", "unit": "%"},
    "quarter_num":  {"display_name": "Quarter of year",
                     "feature_group": "seasonal", "unit": "1-4"},
    "matched_articles": {"display_name": "Matched news articles",
                         "feature_group": "nlp", "unit": "count"},
    "matched_lag1":     {"display_name": "Matched articles, last quarter",
                         "feature_group": "nlp", "unit": "count"},
    "total_articles":   {"display_name": "All food-insecurity articles",
                         "feature_group": "nlp", "unit": "count"},
})

# ---------------------------------------------------------------------------
# DRIVER_GROUP_FEATURES
# ---------------------------------------------------------------------------
# Maps each Risk Driver panel category to the feature names whose SHAP values
# should be SUMMED to produce that driver's net contribution.
#
# This is how group_shap is computed:
#   group_shap["market"] = sum(shap[f] for f in DRIVER_GROUP_FEATURES["market"])
#
# Sign of group_shap determines direction:
#   positive  → risk-increasing  (shown in red)
#   negative  → protective / suppressor  (shown in yellow, labeled PROTECTIVE)
# ---------------------------------------------------------------------------

## ---------------------------------------------------------------------------
## Presentation scheme: five thesis-defined categories (reinstated 2026-09-20)
## ---------------------------------------------------------------------------
## This app previously shipped a seven-group scheme (see git history) after
## finding that a strict five-category panel misrepresented two of the labels:
##   - "OFW Remittance" was roughly half diesel/fuel-price features -- a rising
##     bar there could mean fuel, not remittances.
##   - Folding the fish-kill news signal into a broader "News Coverage" bucket
##     (FSSI + article counts) was judged noisy (~88% non-signal at province
##     level) if presented as its own driver.
## The thesis defense requires exactly five named categories
## (Market/Prices, Climate Stress, Fish Kill, Employment, OFW Remittance), so
## this reverts to that scheme -- but keeps the fix for the mislabeling problem
## that motivated the seven-group change in the first place, rather than
## silently reintroducing it:
##   - OFW Remittance now contains ONLY the real remittance features
##     (ofw_remit_yoy_pct*, trigger_ofw_remittance). The fuel/FX features that
##     used to sit here move to Market/Prices, where "a rising bar might mean
##     transport/input costs, not just farmgate prices" is at least consistent
##     with what that label already covers.
##   - Fish Kill contains ONLY the real fish-kill-specific signal
##     (trigger_fish_kill), not the broader, noisier FSSI/article-count
##     features -- so the bar reflects what it's named, at the cost of being a
##     thinner signal (few articles mention fish kills specifically; see the
##     `newsSignalProportion` caveat surfaced alongside it).
## The model's other real, often-dominant drivers -- the commodity series' own
## recent history and seasonal position (previously "series_history" /
## "seasonal"), plus general food-insecurity news volume/sentiment (FSSI,
## matched/total article counts) -- are NOT dropped from the model, only from
## this five-category presentation. Their combined share is disclosed via
## `other_pct` in build_drivers() and surfaced in the narrative text, rather
## than folded into one of the five bars (which would inflate that bar beyond
## what it actually represents) or hidden.
DRIVER_GROUP_FEATURES: dict[str, list[str]] = {
    "market": [
        "food_cpi", "food_cpi_yoy", "food_cpi_yoy_lag1", "food_cpi_yoy_accel",
        "food_minus_headline_yoy", "food_minus_headline_yoy_lag1", "food_minus_headline_yoy_accel",
        "headline_cpi",
        "rice_price_regular", "rice_price_regular_lag1", "rice_price_regular_accel",
        "commodity_fruit_veg", "commodity_leafy_veg", "commodity_livestock",
        "commodity_poultry", "commodity_rootcrops",
        "trigger_market",
        # Fuel/transport/FX costs feed into commodity prices; kept here
        # rather than under OFW Remittance, which is what made that label
        # misleading before (see note above).
        "fx_usd_php_avg", "diesel_php_per_l", "diesel_php_per_l_lag1",
        "diesel_php_per_l_accel", "gasoline_php_per_l", "brent_usd_per_bbl",
    ],
    "climate": [
        "tc_count", "tc_severe_flag",
        "rainfall_anomaly_pct", "rainfall_anomaly_pct_lag1", "rainfall_anomaly_pct_accel",
        "drought_alert", "enso_numeric",
        "trigger_climate",
    ],
    "fish_kill": [
        "trigger_fish_kill",
    ],
    "employment": [
        "unemployment_rate", "unemployment_rate_lag1", "unemployment_rate_accel",
        "poverty_incidence",
        "trigger_employment",
    ],
    "ofw_remittance": [
        "ofw_remit_yoy_pct", "ofw_remit_yoy_pct_lag1", "ofw_remit_yoy_pct_accel",
        "trigger_ofw_remittance",
    ],
}

# Real, trained model features that are NOT itemized among the five thesis
# categories above -- the commodity series' own recent/seasonal dynamics and
# general (non-fish-kill-specific) news volume/sentiment. Real and often the
# largest single drivers (the annual-cycle features alone were worth +0.11
# accuracy) -- excluded from the five bars on purpose so no bar overstates
# its share, and their combined magnitude is disclosed separately rather
# than hidden. See build_drivers()'s `other_pct`.
UNGROUPED_FEATURES: list[str] = [
    "FSSI", "FSSI_lag1", "FSSI_lag2", "FSSI_accel",
    "matched_articles", "matched_lag1", "total_articles",
    "shock_lag1", "shock_lag2", "dev_lag1",
    "group_code", "province_idx", "commodity_te",
    "shock_lag4", "dev_lag4", "dev_roll4", "series_vol", "quarter_num",
]

DRIVER_GROUP_LABELS: dict[str, str] = {
    "market":         "Market / Prices",
    "climate":        "Climate Stress",
    "fish_kill":      "Fish Kill",
    "employment":     "Employment",
    "ofw_remittance": "OFW Remittance",
}
