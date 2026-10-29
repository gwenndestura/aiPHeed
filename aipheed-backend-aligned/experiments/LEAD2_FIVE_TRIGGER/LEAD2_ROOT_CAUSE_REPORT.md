# LEAD2_ROOT_CAUSE: can Lead 2 be made reliable by correcting its root causes? (2026-10-29)

**Branch:** `aiPHeed/lead2-lgbm-tuning` (local).

| Item | Location |
|---|---|
| Error analysis | `runner/rootcause_errors.py` → `out/rootcause_errors.csv`, `out/rootcause_errors.json` (committed 634ea54 with the protocol, before scoring) |
| Protocol | `PROTOCOL_LEAD2_ROOT_CAUSE.md` (SHA-256 5850dee2…) |
| Scoring | `runner/root_cause.py` → `out/root_cause.json`, `out/root_cause_rows.csv` |
| Prospective seal | `runner/cr_anc_seal.py` → `sealed/cranc_prospective.csv` (SHA-256 07c99e56…) |
| Release-date addendum | `ADDENDUM_ROOT_CAUSE_RELEASE_DATES.md` |
| Tests | `backend/tests/integration/test_lead2_root_cause.py` |

All historical quarters are **development evidence**. Prospective validation awaits the sealed forecasts' outcomes.

## Conclusion

**No candidate meets every frozen requirement. P0H4 stays served. CR remains the research candidate, now joined by CR-ANC as the strongest one.**

| Correction | What it targeted | Result |
|---|---|---|
| **CR-ANC** (anchored projections at the refreshed cut-off) | Price reversals | Best Lead-2 probabilities of any configuration (Brier 0.132; −0.036 vs P0H4-U, p .039), passes R1-R7 at Leads 1 and 2, stable across all 8 model settings. Fails the adoption rule on precision (−0.025 vs the 0.02 limit) and on false alarms vs hits (4 vs 3). Its mechanism hypothesis was not confirmed (see C). |
| CR-T (decision cut from earlier outcomes) | Missed HIGH cases | Failed: 18 false alarms |
| CR-WCAL (Platt from earlier forecasts) | Unstable calibration | Failed: degenerate early maps, Lead 1 loses R3 and R6 |

- **Lead 2 within reach, but not shown.** With the existing observations a stronger Lead 2 is within reach retrospectively, but not demonstrably. CR-ANC's pass or fail flips with the unverified CPI release date: it passes everything at day 20, fails R6 at day 15, and fails the rule at day 10.
- **Maximum reliable horizon: Lead 1.**

## A. Reproduction

Reproduced from the committed inputs (`out/cr_resolve.json`; this run used the same rows):
- P0H4-U and CR refits: max |Δ| 4.9e-7.
- CR-ANC's anchored columns reproduce `features_v2` at the quarter-start cut-off to 5e-10.
- P0H4 Lead 2: 0.769, fails R3, R5, R6. P0H4-U: 0.800, fails R6. CR: 0.800, 11/7/6/41, fails the rule (3 new false alarms vs 2 new hits). CR-CAL: 0.769, fails R6.

## B. Row-level analysis of CR's 13 Lead-2 errors (`out/rootcause_errors.csv`)

Every row lists:
- issue date, lead, true and predicted class, probability, cut, π_H, π_P;
- SWS reading used and realised;
- projected and realised price margins;
- all 20 issue-time inputs of the 12 families;
- the five trigger-group conditions (inputs beyond the training 75th percentile).

| Pattern | Rows | Evidence |
|---|---|---|
| **Hunger cap**: Laguna, Quezon, Batangas 2023-Q4 (misses) | 3 | **Supported by the data.** At the re-issue (2023-08-03) the newest SWS reading (2023-Q2) was exactly 11.3, so π_H = 0.5 and P < 0.5 whatever the price part. The realised value was 14.3. No later reading existed by the window cap. The price parts were 0.51-0.56, so these would have been hits with the true hunger condition. The projected price margins were negative (−0.79 to −1.06) while the realised margins were barely positive (+0.11 to +0.86), so the price part was itself borderline. |
| **Price fell after the issue** (false alarms): Rizal 2024-Q2; Cavite and Rizal 2025-Q2; Laguna and Quezon 2026-Q2 | 5 | **Supported.** Projected margins +0.43 to +2.33; realised −0.07 to −3.02. |
| **Price rose after the issue** (misses): Cavite and Laguna 2024-Q4; Laguna 2025-Q3 | 3 | **Supported.** Realised margins only +0.19 to +0.69, borderline labels. |
| **Model behaviour** (false alarms): Laguna and Batangas 2024-Q3 | 2 | **Hypothesis.** The projections were negative (−1.3, −1.4), but π_P was 0.77 / 0.61 while the rice inputs (A3, world rice) were in their top quartile during the 2024 rice spike. |

**Erratum.** The frozen protocol and commit 634ea54 say "6 of 7 false alarms are price reversals". The data shows **5 of 7** (plus 2 model-behaviour cases). The protocol is hash-frozen and was not edited. This does not affect any candidate, because CR-ANC was motivated by the reversal pattern, which holds either way.

**Which component fails** (all 65 Lead-2 rows):
- The hunger part is right on 85% of rows (it equals the latest-reading rule except at the 11.3 tie).
- CR's price part is right on 69% (P0H4-U 60%).
- Oracle accuracy: true price × CR hunger part = **0.938**; true hunger × CR price part = 0.769.
- **The price part is the binding limit; the hunger part is limited by survey timing.**

**Missingness:**
- N1 (FSSI news) is missing in 83% of Lead-2 rows and in 92% of error rows, so the gap is general, not error-specific.
- A3 is missing in 8% of rows and in none of the error rows.
- News dates: all 1,575 dated rows were published before the issue.

## C. Target audit (no target replaced)

| Analysis | Finding |
|---|---|
| A. Frozen target | Kept for every official comparison |
| B. Construction | The hunger cap is a tie at exactly 11.3 in one survey round, not a formula defect. Thresholds are each province's 2021-22 P60, fixed before the evaluation. Target quarter = origin + lead for every row. In hunger quarters the label equals the price condition (100% since 2023-Q4). |
| C. Alternative targets (sensitivity, not selection) | **Regional hunger condition alone** (observed food insecurity, regional): the latest-reading rule is right on 85% of Lead-2 rows and is itself persistence, so no model has beaten it (E109-E113). **Provincial price condition alone** (proxy, not food insecurity): CR price part 69% vs 57% for the last known condition. Neither is a provincial food-insecurity outcome. The strongest defensible target with the existing observations is the current one: regional observed hunger × provincial price pressure. Province-specific food insecurity needs a repeated provincial outcome (CBMS or FNRI FIES). |

## D. Corrections tested (protocol frozen before scoring; every result reported)

**Lead 2** (65 rows, 13 quarters, 17 HIGH). Δ Brier is against P0H4-U.

| Candidate | Accuracy (90% CI) | Balanced | Precision | Recall | F1 | TP FP FN TN | Brier (Δ, p) | Calibration slope / in-the-large | 2023-24 / 2025-26 accuracy | Failed criteria | Adoption rule |
|---|---|---|---|---|---|---|---|---|---|---|---|
| P0H4 (served) | 0.769 (0.65-0.88) | 0.635 | 0.60 | 0.35 | 0.44 | 6 4 11 44 | 0.194 (+0.027) | 0.47 / +0.03 | 0.686 / 0.867 | R3 R5 R6 | — |
| P0H4-U | 0.800 (0.71-0.89) | 0.732 | 0.63 | 0.59 | 0.61 | 10 6 7 42 | 0.167 | 1.04 / +0.07 | 0.771 / 0.833 | R6 | baseline |
| CR | 0.800 (0.71-0.89) | 0.751 | 0.61 | 0.65 | 0.63 | 11 7 6 41 | 0.147 (−0.020, .11) | 1.50 / +0.09 | 0.771 / 0.833 | — | fails 1 |
| CR-CAL | 0.769 | 0.711 | 0.56 | 0.59 | 0.57 | 10 8 7 40 | 0.144 (−0.023, .09) | 1.29 / +0.07 | 0.771 / 0.767 | R6 | fails 5 |
| **CR-ANC** | **0.800 (0.69-0.91)** | **0.770** | **0.60** | **0.71** | **0.65** | **12 8 5 40** | **0.132 (−0.036, .039)** | 1.45 / +0.06 | 0.771 / 0.833 | **—** | **fails 2** |
| CR-T | 0.677 | 0.724 | 0.44 | 0.82 | 0.57 | 14 18 3 30 | 0.147 | — | 0.800 / 0.533 | R2 R4 R6 R7 | fails 4 |
| CR-WCAL | 0.800 | 0.808 | 0.58 | 0.82 | 0.68 | 14 10 3 38 | 0.151 (−0.016, .20) | 0.49 / +0.13 | 0.800 / 0.800 | R6 (Lead 1: R3, R6) | fails 5 |
| Always LOW / persistence | 0.738 / 0.723 | — | — | — | — | — | — / 0.277 | — | — | — | — |

**Lead 1** (accuracy, Brier, failed criteria):
- P0H4 / P0H4-U: 0.843, 0.132, none.
- CR: 0.871, 0.123, none.
- **CR-ANC: 0.886, 0.112, none.**
- CR-T: 0.829, none.
- CR-WCAL: 0.814, fails R3 and R6.

**Lead 3:** all fail. CR-ANC 0.633, the same as P0H4-U; CR 0.533.

**What each correction did:**
- **CR-ANC.**
  - **Changed calls vs CR:** caught Laguna 2024-Q4 and Laguna 2025-Q3 (two small price rises), lost Quezon 2024-Q2 (CR 0.501), and added a false alarm at Rizal 2026-Q2.
  - **Mechanism:** the protocol's hypothesis (fewer reversal false alarms) was **not confirmed**. None of the five reversals was removed. The gain is in recall and in probability quality.
  - **Adoption rule, frozen:** it fails `2_L2_precision_within_0.02` (0.600 vs 0.625) and `2_new_FA_le_new_hits` (4 vs 3).
  - **R6 margin:** precision is exactly 0.600, so one more false alarm would break R6.
- **CR-T.** Earlier outcomes push the cut to 0.25 from 2024-Q2. That buys 4 new hits for 12 new false alarms, the same failure as C0-T in §11.
- **CR-WCAL.** The calibration data are CR's own earlier out-of-sample forecasts. They exist only from 2024-Q2, and the first map is degenerate (slope 20.8 from 20 rows with 3 HIGH). So calibration instability comes from the **small, regime-dependent calibration sets**, not from the type of data. With 20-55 earlier rows, no calibration map is stable.

## E. Overfitting, stability, bias and generalisation

- **Settings sensitivity** (8 fixed grid configurations, Lead 2):
  - CR-ANC: 0.800-0.846 accuracy, and all 8 pass R1-R7.
  - CR: 0.769-0.831, with 2 of 8 failing.
  - Anchoring makes the price part less sensitive to model complexity. This is reported only: no configuration was chosen.
- **Train / validation / test:** CR-ANC's price-part train Brier is 0.13-0.21 and its out-of-sample Brier 0.07-0.40. The gaps are largest before 2024 (few training quarters).
- **Influential quarters:**
  - Leave-one-quarter-out minimum accuracy: CR-ANC 0.783, CR 0.783.
  - The thirds are uneven: the middle third (2024) is lowest for every candidate.
  - CR-ANC's Brier gain is significant against P0H4-U (p .039) but not corrected for the 14 candidates scored on these rows.
- **Bias:**
  - CR-ANC's errors are 5 misses and 8 false alarms.
  - By province: Rizal 3 (all false alarms; it has no HIGH case), Quezon 3 (2 misses), Laguna 3, Cavite 2, Batangas 2.
  - By period: thirds 0.80 / 0.75 / 0.85.
  - The 2023-Q4 misses are structural (hunger cap).

## F. Trigger groups (research-only ablation of CR-ANC; the final model keeps all 12 families)

ΔBrier is the change in the risk probability when the group is removed; positive means the group helped. p is the Holm-corrected one-sided p across the five groups.

| Group | Lead 1 ΔBrier (Holm p) | Lead 2 ΔBrier (Holm p) | Status |
|---|---|---|---|
| Market and prices (incl. anchored) | +0.072 (.004) | +0.072 (<.001) | **Supported at Leads 1 and 2** |
| Climate stress | +0.002 (.11) | +0.003 (1.0) | Not established |
| Employment and remittances | +0.005 (**.028**) | +0.001 (.13) | **Supported at Lead 1 only** (in CR-ANC); not at Lead 2 |
| Poverty and social vulnerability | +0.003 (.20) | −0.009 (1.0) | Not established. Removal helped at Lead 2 on an uncorrected interval |
| News and NLP | +0.006 (**.015**) | −0.007 (1.0) | **Supported at Lead 1 only** (in CR-ANC); not at Lead 2 |
| Fish production / hunger outlook | ≈ 0 | ≈ 0 | Not established |

These ablations are of a research candidate on development rows. The served dashboard cards describe the P0H4 evidence and were not changed.

## G. Data availability and timing

| Check | Result |
|---|---|
| PSA provincial CPI release dates (18 refreshed months) | **UNKNOWN.** psa.gov.ph, rsso04a.psa.gov.ph and openstat.psa.gov.ph are all blocked (bot verification, not bypassed, or 403); regional page dates are re-postings. Logged in `data/psa_cpi_release_evidence.csv`. |
| Effect if the release was later than day 10 (sensitivity, reported only) | CR-ANC at day 15: Lead 2 0.815, precision 0.67, recall 0.59 (R6 fails), adoption rule passes. **At day 20: Lead 2 0.831, precision 0.69, recall 0.65, Brier 0.130, R1-R7 pass at Leads 1 and 2, and the adoption rule passes.** The outcome flips with the assumption, and the day-20 variant was seen after scoring, so it is **not** adopted. |
| Pre-registered response | `ADDENDUM_ROOT_CAUSE_RELEASE_DATES.md`, committed before any date is known: once the dates are verified, CR-ANC is re-scored once under them, with the frozen rule |
| Target alignment, CPI rule, SWS and news before the issue, no training target after the origin | All pass |
| Sealed outcomes absent from the data | Labels and SWS end at 2026-Q3; CPI at 2026-09 |

## H. Prospective tests

- **CR:** `sealed/cr_prospective.csv` (dd293e2e…). Intact.
- **CR-ANC:** `sealed/cranc_prospective.csv` (07c99e56…), sealed 2026-10-29 before any outcome.
  - Lead 1 2026-Q4: all five LOW.
  - Lead 2 2027-Q1: all five LOW (P 0.14-0.38).
  - Leads 3-4: mostly HIGH.
- Scoring starts once the 2026-Q4 SWS round and the October-December 2026 provincial CPI are published.

## I. What would make the next step possible

1. **Verified PSA release dates** for the 18 provincial CPI months. This decides directly whether CR-ANC's retrospective pass holds (the addendum).
2. **Scored prospective quarters** for CR and CR-ANC.
3. **An inter-round hunger observation** for quarters whose latest SWS reading ties the threshold (the three 2023-Q4 misses).
4. **A repeated provincial food-insecurity outcome**, for province-specific claims.

**Strongest research direction:** CR-ANC, with verified release dates and the sealed prospective record. No further retrospective candidate is justified on these 13 quarters.

## J. Changes and tests

- **New files:**
  - `runner/rootcause_errors.py`, `runner/root_cause.py`, `runner/cr_anc_seal.py`;
  - `out/rootcause_errors.*`, `out/root_cause.*`;
  - `sealed/cranc_prospective.*`;
  - `PROTOCOL_LEAD2_ROOT_CAUSE.md` and its SHA file; `ADDENDUM_ROOT_CAUSE_RELEASE_DATES.md` and its SHA file;
  - this report;
  - `backend/tests/integration/test_lead2_root_cause.py`.
- **Updated:** `data/psa_cpi_release_evidence.csv` (OpenSTAT attempt) and the thesis package (section 24).
- **Unchanged:** served model, rows, evaluation, seal, thresholds, flags, frontend and deployment.
- **Tests:** the root-cause, evidence-gap and CR-resolve tests, 16 passed.

## K. Full test suite

Full backend suite: **973 passed, 18 skipped, 0 failed** (2026-10-29).

## L. PSA release dates collected by the project owner (2026-10-29; `runner/release_dates_review.py`, `out/release_dates_review.json`)

- **Input.** The owner's collection: `data/psa_cpi_release_dates_owner_research_20261029.csv`, kept verbatim (SHA-256 5cb33206…). It covers the 9 priority months: 45 province-month rows, 27 of them with a date.
- **Check.** Every reported date falls **before** its forecast issue date (1-15 days earlier). No refreshed CPI month has been shown unavailable.
- **Later than day 10, but still before the issue:**
  - June 2024, Batangas: 2024-07-22, for the 2024-07-24 issue;
  - April 2026, Laguna and Batangas: 2026-05-11 / 2026-05-12, for the 2026-05-13 issue.

  So the day-10 rule is not a reliable stand-in for the actual dates, although it caused no violation in these rows.
- **Status: reported, not confirmed.**
  - No saved copy was named.
  - It is not yet confirmed that each date is the release date printed on the document rather than a page posting date (some Region IV-A page dates are re-postings).
  - The pages could not be opened from this session (bot verification).
  - Four months (2023-04, 2024-12, 2025-07, 2025-12) rely on a regional report; it still has to be confirmed that it carries the provincial figures of the same CPI series.
- **Erratum to the addendum.**
  - Its rule 2 applies to every Lead-2+ row, training rows included. It therefore needs **36 reference months (180 province-months)**, not the 18 it states.
  - That is 34 months counted by the day-10 rule, plus 2 it excluded that may have been released in time: July 2023 for the 2023-08-03 issue, and October 2025 for the 2025-11-06 issue.
  - The list is in `data/psa_cpi_release_months_needed.csv`. Verified dates can therefore change CR-ANC's inputs in either direction.
- **Decision.** The pre-registered re-score does **not** run yet. 0 of 180 are confirmed and 153 are unknown. The CR-ANC result (day-10 rule: not eligible) and every conclusion above are unchanged.
- **Next step.** Complete and confirm `data/psa_cpi_release_dates_TO_FILL_v2.csv`, which is prefilled with the 27 reported dates.
