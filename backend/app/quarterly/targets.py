"""
app/quarterly/targets.py  (E29, decision D10)
---------------------------------------------
Versioned target registry. Every result, record and display names its target by id, and the registry states what the
target measures. The point is that the three things aiPHeed touches are never confused:

    food insecurity   - a household's inadequate access to food (FIES / FNRI / CBMS measure it directly)
    hunger            - SWS self-rated involuntary hunger: a measured experience, Balance Luzon (regional)
    price pressure    - relative provincial food inflation: a constructed market indicator

A new or adviser-approved target is added as a NEW id with its own definition, lineage and protocol; an existing id is
never redefined.
"""
from __future__ import annotations

TARGETS: dict[str, dict] = {
    "T1_A": {
        "version": "E25 (frozen 2026-10-14)",
        "status": "APPROVED",
        "definition": "S1 = H + 2D > tau; H = mean SWS Balance Luzon hunger of the quarter's definition-A production "
                      "rounds; D = provincial food CPI YoY minus the CALABARZON mean; tau = median of S1 labels "
                      "published before the forecast origin",
        "construct": "composite food-stress proxy: measured regional hunger plus constructed provincial price pressure",
        "measures_food_insecurity_directly": False,
        "geography": "H regional (Balance Luzon, shared by all five provinces); D provincial",
        "independent_unit": "forecast date (the five provinces of a date share one H)",
        "may_be_called": ["food-stress label", "composite food-stress proxy"],
        "must_not_be_called": ["measured provincial food insecurity", "official food-insecurity classification"],
    },
    "T2": {
        "version": "E25 (frozen 2026-10-14)",
        "status": "EXPLORATORY_INDICATOR",
        "definition": "D > 0: provincial food CPI YoY above the CALABARZON mean",
        "construct": "relative provincial food-price pressure (constructed from PSA CPI)",
        "measures_food_insecurity_directly": False,
        "geography": "provincial",
        "independent_unit": "province-date (partly dependent: D is relative to the regional mean)",
        "may_be_called": ["price pressure", "relative food-price pressure"],
        "must_not_be_called": ["food insecurity", "food-insecurity risk", "hunger"],
    },
    "H": {
        "version": "observation",
        "status": "MEASURED_OBSERVATION",
        "definition": "SWS self-rated involuntary hunger, Balance Luzon, per round",
        "construct": "experienced hunger (survey)",
        "measures_food_insecurity_directly": "partly (one severe dimension), regional only",
        "geography": "regional (Balance Luzon); never a provincial measurement",
        "independent_unit": "survey round",
        "may_be_called": ["regional hunger (SWS, Balance Luzon)"],
        "must_not_be_called": ["provincial hunger", "CALABARZON hunger rate", "municipal hunger"],
    },
}


def describe(target_id: str) -> dict:
    if target_id not in TARGETS:
        raise KeyError(f"unknown target {target_id!r}; add a new versioned entry, never reuse an id")
    return TARGETS[target_id]


def wording_violations(target_id: str, text: str) -> list[str]:
    """Phrases in `text` that a display of this target must not use (negated uses such as 'not food insecurity' or
    'never a food-insecurity forecast' are allowed)."""
    t = " ".join((text or "").lower().split())
    bad = []
    for phrase in TARGETS[target_id]["must_not_be_called"]:
        p = phrase.lower()
        i = t.find(p)
        while i != -1:
            before = t[max(0, i - 24):i]
            if not any(n in before for n in ("not ", "never ", "no ", "not a ", "isn't ", "rather than ")):
                bad.append(phrase)
                break
            i = t.find(p, i + 1)
    return bad
