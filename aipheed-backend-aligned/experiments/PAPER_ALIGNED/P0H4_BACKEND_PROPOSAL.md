# Proposal: serve P0H4 as the main model (backend only; NOT implemented)

**Status:** proposal for approval, 2026-11-03. Nothing in `backend/`, `frontend/`, `render.yaml` or the Dockerfile
has been changed for it.

## 1. What already exists

The `ch1` serving mode (`AIPHEED_LEAD2_MODEL=thesis` + `AIPHEED_MAP_MODEL=ch1`,
`backend/app/ml/inference/ch1_system.py`) already serves P0H4's exported rows (`backend/data/ch1_engine/`).

It fills the existing fields:
- `riskScore` = P(HIGH);
- `summary.components` = the hunger and price parts;
- driver bars = SHAP of the price part;
- the reports describe P0H4.

**The case you asked about is already explained in the summary sentence.** A LOW province with high hunger reads, for
Quezon 2026-Q4 (checked on the API today):

> "FOOD-INSECURITY RISK for Quezon, 2026-Q4: LOW (probability 0.26; hunger condition 84%, food-price condition 30%),
> because food prices are not likely to rise unusually fast; Lead-1 forecast: this horizon passed the reliability
> test (accuracy 0.84 on 70 past province-quarters)."

**Deployment does not use it.** `render.yaml` sets `AIPHEED_LEAD2_MODEL=thesis` and `AIPHEED_STRICT_MODEL=1`, with no
`AIPHEED_MAP_MODEL`. The Dockerfile does the same. Production therefore serves **FIRI v2** (the default), not P0H4.
**I will not change `render.yaml` or the Dockerfile without your approval.**

## 2. Proposed backend changes (existing text fields only; no field renamed, removed or added)

| # | Where (file) | Field | Today in ch1 mode | Proposed |
|---|---|---|---|---|
| 1 | `ch1_system.province_row` | `confidenceStatement` (map and `/forecast`) | "Quezon, 2026-Q4: LOW food-insecurity risk (probability 0.26). Lead-1 forecast: …" (no hunger part) | Add the two conditions: "… LOW (probability 0.26): regional hunger above 11.3% is likely (84%), but this province's food prices are not likely to rise unusually fast (30%); HIGH needs both" |
| 2 | `ch1_system.sentence` | `summary.sentence` (only the first sentence is shown) | Has both parts, but not the SWS reading itself | Add the latest SWS Balance Luzon reading, its quarter and publication date (`h_last`, `sws_newest_q`, `sws_newest_published` are already in rows.csv). For past quarters: "past forecast; actual: HIGH/LOW" (the `observed` column) |
| 3 | `ch1_system.reliability_text` | `horizonLabel`, `summary.sentence` | Lead 2: "experimental … does not pass the seven reliability rules" | State both rules: "Lead 2 passes the paper's 75% accuracy rule (0.769, Maximum Reliable Lead Time 2) but not the stricter stability rules (it caught 6 of 17 HIGH cases)". The paper's rule needs one number, `max_reliable_lead_alg3 = 2`. I propose reading it from `PAPER_ALIGNED/p0h4_alg3.json`, **not** writing it into evaluation.json, which stays unchanged |
| 4 | `ch1_system.INDICATOR["caveat"]`, `reliability_sentences()`; `insights.CH1_EXPLAINABILITY_NOTE` | `summary.caveat`, explainability `note`, report notes | No FNRI context | Add: "Face validity: DOST-FNRI 2023 found 19.1% of CALABARZON households moderately or severely food insecure (95% CI 17.0–21.1), a different measure, context only." Add the H3 finding in the reports: the government-only LightGBM was more accurate at Lead 1 |
| 5 | `ch1_system.evidence_note` | driver `evidenceNote` | Says the bars leave out the hunger condition (correct) | Keep. Add the hunger part's value in words when it decides the class ("here 84%: the class is set by food prices") |
| 6 | Rule 1, `review.rejected_pairs` | `withheld` on the map; 404 `forecast_withheld` | ch1 mode shows issued forecasts before any approval (only rejections are withheld) | Withhold issued P0H4 forecasts (issue date ≥ 2026-10-01) until an administrator approves them in the existing review queue. Walk-forward quarters stay public |
| 7 | Rule 7, alerts | staged alerts | Nothing stages P0H4 HIGH forecasts; ch1 mode drops the E58 warning | Stage one alert per HIGH province forecast (STAGED only; an admin confirms). Add "flagged for human confirmation; no automatic notification to DSWD or any agency" to the HIGH `confidenceStatement`. No caller sends mail |

All of this is gated on `AIPHEED_MAP_MODEL=ch1`. The FIRI default stays unchanged, and P0H4's rows.csv,
evaluation.json, PREREG_LEAD2, its addenda and the seals are untouched.

**Tests to add.** Each new text appears in its field. The Lead-2 text names both rules. A forecast quarter is withheld
until approved and shown after approval. HIGH forecasts are staged and never confirmed automatically. The FIRI default
is unchanged. Then the full backend suite runs (baseline today: 987 passed, 18 skipped).

## 3. Decisions needed from you

1. **Lead 2 for 2027-Q1: official P0H4 or the mid-quarter update?** Since 2026-11-01, ch1 mode serves the M3 update
   for 2027-Q1. M3 is the same P0H4, issued one month later with the newest SWS reading and CPI (model `P0H4-M3`,
   sealed `backend/seals/2026-11-01_2027-Q1_M3.json`). The two give different classes:

   | Version | Hunger part | Cavite | Other provinces | Result |
   |---|---|---|---|---|
   | Official Lead-2 row (issued 2026-10-01) | 0.81 | 0.10 | 0.03–0.10 | **all five LOW** |
   | M3 (issued 2026-11-01) | 0.98 | **HIGH, 0.52** | Rizal 0.35, Quezon 0.31, Laguna 0.11, Batangas 0.06 | Cavite HIGH, rest LOW |

   `AIPHEED_LEAD2_UPDATE=official` turns M3 off. Which should the main model show?
2. **Deployment configuration.** Add `AIPHEED_MAP_MODEL=ch1` to `render.yaml` (and the Dockerfile `ENV`)? I will ask
   again before editing either.
3. **The uncommitted `foodinsecurity` serving mode from the previous step** is still in the working tree:
   - new: `foodinsecurity_system.py`, `served_risk.py`, `data/foodinsecurity_engine/`, its test file and
     `FOOD_INSECURITY_SYSTEM/`;
   - hooks in `dashboard.py`, `final.py`, `insights.py`, `report.py`, `report_data_e31.py`, `review.py`.

   Its Rule 1 gate and Rule 7 staging could be reused for items 6 and 7. The options are:
   - (a) commit it as the documented, non-default alternative;
   - (b) keep it uncommitted;
   - (c) remove it.

   It has not been committed or removed.

## 4. Screen problems only the frontend could fix (not part of this proposal)

- **Only the first sentence is shown.** The Why panel (`frontend/src/lib/summaryHeadline.ts`) shows only the first
  sentence of `summary.sentence`, so everything above must fit into one sentence. The explainability `note` and
  `summary.caveat` (where the FNRI line would go) are not rendered on the main screen.
- **No place for the two conditions.** There is no visual element for the two conditions beside the probability. The
  hunger part is in `summary.components` but not drawn.
- **Withheld wording.** The map legend says "withheld by DA or not enough data", and the Landing page says "every
  estimate is shown publicly unless an administrator rejects it". Both would be wrong once Rule 1 holds forecasts
  until approval (item 6).
- **No reliability badge.** No badge distinguishes "reliable under the paper's rule" from "reliable under the strict
  rules".
