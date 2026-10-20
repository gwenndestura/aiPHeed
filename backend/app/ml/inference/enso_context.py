"""
E65: official PAGASA ENSO status beside the experimental Lead-2 (E56/E58) forecasts, and what the model does with ENSO.

The E56 model's only ENSO inputs are the observed NOAA ONI phase codes of quarters t-1 and t-2 (El Nino +1 / neutral 0 /
La Nina -1, no strength). PAGASA's alerts, advisories, strength outlooks and rainfall/drought outlooks are NOT inputs.
This module states that next to the forecasts, using only PAGASA items dated before each issue date as "available";
later items are labelled as published after the issue date. It changes no number.

Sources: aipheed-backend-aligned/experiments/E65_El_Nino_Risk_Drop_Audit/sources/SOURCES.md (PAGASA press releases and
El Nino Advisories Nos. 1-5). Model facts: E65 tables/r2_enso_counterfactuals.csv, out/r1_trace.json (checked by
tests/integration/test_e65_el_nino_audit.py).
"""
from __future__ import annotations

# (date issued, short status) -- PAGASA ENSO Alert and Warning System, 2023-2026 (ASCII: PDF export)
PAGASA_ENSO = [
    ("2023-03-24", "El Nino Watch"),
    ("2023-05-02", "El Nino Alert"),
    ("2023-07-04", "El Nino Advisory: El Nino present"),
    ("2024-03-07", "El Nino Advisory No. 9 and La Nina Watch"),
    ("2024-06-07", "El Nino Final Advisory (La Nina Watch continues)"),
    ("2024-07-12", "La Nina Alert"),
    ("2025-01-06", "La Nina Advisory: La Nina present"),
    ("2025-04-04", "termination of the La Nina Alert"),
    ("2025-08-26", "La Nina Watch"),
    ("2025-09-15", "La Nina Alert"),
    ("2025-10-10", "La Nina Advisory: La Nina present"),
    ("2026-03-09", "La Nina Final Advisory"),
    ("2026-03-25", "El Nino Watch"),
    ("2026-04-22", "El Nino Alert (79% chance of El Nino in June-August 2026, likely to persist until early 2027)"),
    ("2026-06-09", "El Nino Advisory No. 1: El Nino conditions present; over 80% chance of a full El Nino lasting "
                   "until early 2027"),
    ("2026-07-06", "El Nino Advisory No. 2: weak to moderate El Nino; models suggest very strong by "
                   "October-December 2026"),
    ("2026-08-06", "El Nino Advisory No. 3: moderate El Nino; may reach very strong before the end of 2026 and last "
                   "until the first half of 2027"),
    ("2026-09-07", "El Nino Advisory No. 4: moderate to strong El Nino; may reach very strong, peaking toward the end "
                   "of 2026 and lasting until the first half of 2027"),
    ("2026-09-23", "Climate Advisory: a strong El Nino intensifying to very strong in September-December 2026 and "
                   "persisting through the first half of 2027, with risk of agricultural dry spells"),
    ("2026-10-07", "El Nino Advisory No. 5: strong to very strong El Nino; may peak before the end of 2026 and last "
                   "until the first half of 2027"),
]

# What the issued E56 models did with ENSO (E65 r1/r2, recomputed from the frozen procedure). Keyed by target quarter.
E65_ENSO_USE = {
    "2027-Q1": {"issued": "2026-10-01", "enso_input": "El Nino in 2026-Q2, coded +1 without its strength",
                "enso_l2_input": "neutral in 2026-Q1", "price_part_enso_splits": 0,
                "hunger_part": (0.8954, 0.9623),
                "counterfactual": "Setting the ENSO inputs to neutral lowers this score by at most about 1 percentage "
                                  "point",
                "typhoon_note": "storm tracks were fetched on 2026-09-09, so storms after that date in 2026-Q3 are "
                                "not counted"},
    "2026-Q4": {"issued": "2026-07-01", "enso_input": "neutral in 2026-Q1",
                "enso_l2_input": "La Nina in 2025-Q4", "price_part_enso_splits": 0,
                "hunger_part": (0.9976, 0.9972),
                "counterfactual": "Coding both ENSO inputs as El Nino changes this score by less than 0.1 percentage "
                                  "point",
                "typhoon_note": None},
}
MODES = ("e56", "e58", "e66", "e67")     # the records E65 verified (e66 serves the E58 record); others not described


def _el_nino_alert(text: str) -> bool:
    return text.startswith(("El Nino Alert", "El Nino Advisory", "Climate Advisory"))


def available_at(issue_date: str) -> list[tuple[str, str]]:
    """PAGASA items issued strictly before the issue date (the forecast's information cutoff)."""
    return [(d, s) for d, s in PAGASA_ENSO if d < issue_date]


def published_after(issue_date: str, until: str | None = None) -> list[tuple[str, str]]:
    return [(d, s) for d, s in PAGASA_ENSO if d >= issue_date and (until is None or d <= until)]


def forecast_sentence(target_quarter: str, mode: str, today: str | None = None) -> str | None:
    """Sentence appended to the issued/earlier forecast summary: the official El Nino status known at the issue date,
    how (little) the model uses ENSO, and what a low score does not show. None if E65 did not verify this forecast."""
    use = E65_ENSO_USE.get(target_quarter)
    if mode not in MODES or use is None:
        return None
    before = available_at(use["issued"])
    if not before or not _el_nino_alert(before[-1][1]):
        return None
    d, s = before[-1]
    lo, hi = use["hunger_part"]
    out = (f"Climate: before this forecast was issued ({use['issued']}), PAGASA's latest ENSO statement ({d}) was "
           f"\"{s}\". This is not a model input. The model's only ENSO input is the observed ENSO phase "
           f"({use['enso_input']}; {use['enso_l2_input']}); it enters the regional hunger part only"
           + (f" (which it moves from {lo:.0%} to {hi:.0%})" if hi - lo >= 0.01 else "")
           + ". The food-price part has no ENSO input, projects food prices flat from the latest month, and no "
           "rainfall or drought data are used, so a drought-driven rise in food prices would show up only after it "
           f"appears in the CPI. {use['counterfactual']}. A LOW score is therefore not evidence that the El Nino "
           "poses no food risk.")
    later = published_after(use["issued"], today)
    if later:
        ld, ls = later[-1]
        out += f" Published after the issue date: PAGASA {ld}, \"{ls}\"."
    return out


def climate_evidence(target_quarter: str, mode: str) -> str | None:
    """Text appended to the Climate Stress trigger's evidence note for the same forecasts."""
    use = E65_ENSO_USE.get(target_quarter)
    if mode not in MODES or use is None:
        return None
    before = available_at(use["issued"])
    lo, hi = use["hunger_part"]
    status = f"PAGASA at the issue date ({use['issued']}): {before[-1][1]} ({before[-1][0]})" if before else None
    parts = [p for p in (
        status,
        f"not a model input; the model uses only the observed ENSO phase ({use['enso_input']}) and no rainfall or "
        f"drought series",
        (f"the ENSO code acts in the regional hunger part (chance of hunger above 11.3%: {lo:.0%} with neutral, "
         f"{hi:.0%} as coded), which the bars do not show; the bars show the food-price part" if hi - lo >= 0.01 else None),
        use["typhoon_note"]) if p]
    return "; ".join(parts) + "."
