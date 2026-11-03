# FOOD_INSECURITY_SYSTEM, Step 2: serving mode `foodinsecurity` (backend only)

**Switch.** `AIPHEED_LEAD2_MODEL=thesis` and `AIPHEED_MAP_MODEL=foodinsecurity`. The default (`AIPHEED_MAP_MODEL`
unset, which is FIRI v2) and `ch1` are unchanged.

**What is served** (`backend/app/ml/inference/foodinsecurity_system.py`; rows from `runner/export_fi.py` into
`backend/data/foodinsecurity_engine/`):
- **Headline, every province:** the IMPROVE_V2 reference model (REF), P(Balance Luzon SWS hunger > 11.3%), HIGH at
  0.50. This is CH3_AMENDMENT §2.1 Option A, chosen by the team, pending adviser confirmation.
- **Leads 1 and 2 only.** The Maximum Reliable Lead Time is 2 (IMPROVE_V2_LEADS: Lead 3 accuracy 0.726). The rows are
  the Lead-1 walk-forward forecasts for 2023-Q1..2026-Q3, plus the forecasts issued 2026-10-01: 2026-Q4 (Lead 1) and
  2027-Q1 (Lead 2). The 2027-Q1 row equals the sealed forecast (SHA-256 `94c62596…`).
- **Beside the headline, never multiplied:**
  - the province food-price pressure: the served P0H4 price part, read from `backend/data/ch1_engine/rows.csv`, banded
    Low < 0.33 ≤ Medium < 0.67 ≤ High;
  - the PSA vulnerability rank: 0.6 × poverty + 0.4 × density, min-max over the five provinces.

  The province list is ordered by price pressure, then by vulnerability rank. The map's rank numbers stay tied,
  because the probability is equal.

**Existing fields, filled honestly** (no field renamed, removed or added):

| Field | Content |
|---|---|
| `summary.sentence` (first sentence is shown) | Class and regional probability; for past quarters "past forecast; actual: HIGH/LOW (SWS hunger x%)"; the latest SWS reading with its quarter and publication date; "classification is regional, province differences come from food prices and vulnerability"; the province's price band and vulnerability rank; the lead's reliability; for an issued HIGH forecast, the human-confirmation flag |
| `note` (explainability), `summary.caveat`, `indicator.caveat` | The regional statement; FNRI 2023 CALABARZON 19.1% (95% CI 17.0–21.1) as face validity; development evidence; R7 failure |
| `triggers[].evidenceNote` / `plainEvidence` | The bars are SHAP of the regional forecast, the same for every province; past SWS hunger goes into `otherPct`; Employment and OFW are "not an input" (status `no_model_input`); the Market card states the province's price band |
| `summary.components.combination` | "not combined: … never multiplies it" |
| `riskLevelBasis`, LGU `riskLevelBasis` / `disaggregationLabel`, report cover, notes and method table | The same design in words |

**Rule 1.** In this mode, `review.rejected_pairs` also withholds every issued forecast (2026-Q4, 2027-Q1) that has no
Approved (`Published`) review record. The map shows it as withheld with no score. `/forecast` and `/explainability`
return `forecast_withheld`, and the reports treat it as withheld, until an administrator approves it in the existing
review queue.
Walk-forward quarters are not gated.

**Rule 7.**
- A HIGH issued forecast carries the flag "flagged for human confirmation by a DA Region IV-A administrator before any
  action; no notification is sent to DSWD or any agency automatically".
- `alert_candidates()` and `stage_alerts(db)` stage ONE regional alert per HIGH forecast quarter
  (`REGIONAL_FOOD_INSECURITY_HIGH`). It is STAGED only: it is public only after an administrator confirms it.
- Nothing calls `stage_alerts` automatically, and the module imports no mailer.

**Hook.** `served_risk.py` returns `ch1_system` or `foodinsecurity_system`. The call sites that imported `ch1_system`
import it instead and read the same names. Six ch1-specific texts became `getattr(CH1, NAME, <ch1 text>)`, so ch1
text is unchanged. The cache key gets `+fi` only in this mode.

**Tests.** `backend/tests/integration/test_foodinsecurity_mode.py` (17 tests).
