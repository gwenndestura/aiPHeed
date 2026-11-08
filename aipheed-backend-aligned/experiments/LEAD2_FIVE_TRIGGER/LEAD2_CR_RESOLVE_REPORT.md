# LEAD2_CR_RESOLVE: can CR make Lead 2 reliable? (2026-10-29)

**Branch:** `aiPHeed/lead2-lgbm-tuning` (local).

- **Protocol:** `PROTOCOL_LEAD2_CR_RESOLVE.md`, committed in 9a64352 before scoring (SHA-256 c7dd86c3…).
- **Runner:** `runner/cr_resolve.py`.
- **Results:** `out/cr_resolve.json`, `out/cr_resolve_rows.csv`.
- **Tests:** `backend/tests/integration/test_lead2_cr_resolve.py`.

**Status of the evidence.** Every 2021-2026 quarter has been examined in earlier experiments, so all results here are **retrospective development evidence**. Prospective validation has not happened yet. The sealed forecasts (`sealed/cr_prospective.csv`, dd293e2e) are the independent test, and none of their outcomes exists yet.

## Verdict: UNRESOLVED — DATA OR TARGET LIMITATION

CR remains **research-only**. P0H4 stays served, with its seal unchanged. **The maximum reliable horizon is Lead 1.**

- CR meets R1-R7 at Lead 2 retrospectively.
- It fails the frozen adoption rule (3 new false alarms vs 2 new hits).
- Its pass rests on one row, a narrow cut window, one of eight model settings families and an unverified CPI release assumption.
- The one defensible correction (CR-CAL) made Lead 2 worse.
- The binding limits are in the data and the target:
  - a regional hunger component that caps three HIGH cases;
  - no provincial food-insecurity outcome;
  - unrecorded PSA release dates;
  - 13 independent quarters.

  A different model cannot remove any of these.

## 1. Reproduced baselines

All three were reproduced from the committed stack and inputs, not taken from earlier reports:
- P0H4-U and CR refits: max |Δ| 4.9e-7 over 250 rows.
- P0H4: the committed replay. The served export's 70 retrospective rows equal it exactly.

| Lead 2 (65 rows, 13 quarters, 17 HIGH) | Accuracy (90% CI) | Balanced | Precision | Recall | F1 | TP FP FN TN | Brier | Failed |
|---|---|---|---|---|---|---|---|---|
| P0H4 (served) | 0.769 (0.65-0.88) | 0.635 | 0.60 | 0.35 | 0.44 | 6 4 11 44 | 0.194 | R3, R5, R6 |
| P0H4-U | 0.800 (0.71-0.89) | 0.732 | 0.63 | 0.59 | 0.61 | 10 6 7 42 | 0.167 | R6 |
| CR | 0.800 (0.71-0.89) | 0.751 | 0.61 | 0.65 | 0.63 | 11 7 6 41 | 0.147 | none |
| Always LOW | 0.738 | 0.50 | — | 0 | 0 | 0 0 17 48 | — | — |
| Persistence | 0.723 | — | — | — | — | — | 0.277 | — |

Every figure you listed for CR is confirmed:
- accuracy 0.800, balanced accuracy 0.751, recall 0.65, Brier 0.147;
- 11/7/6/41;
- 3 new false alarms vs 2 new hits;
- Brier −0.020 vs P0H4-U, with exact sign-flip p = .13 (block bootstrap p = .11).

## 2. Root causes, ranked by evidence

**Confirmed (measured on the code and data):**

1. **Hunger cap (target structure).** The three 2023-Q4 HIGH cases have π_H = 0.5 exactly, so P < 0.5 whatever the price part is. They are 3 of CR's 6 misses, and the recall ceiling is 14/17 (§17.2).
2. **Target content.** The hunger part is regional:
   - it is identical for the five provinces in every quarter and met in 11 of 13;
   - in those quarters the label equals the province food-price condition;
   - all provincial variation is price pressure;
   - no provincial food-insecurity outcome exists in the data (§21.3).
3. **Price moves after the issue.** CR's other errors are concentrated in a few quarters:
   - misses: 2024-Q4 ×2, 2025-Q3;
   - false alarms: 2024-Q2, 2024-Q3 ×2, 2025-Q2 ×2, 2026-Q2 ×2.

   The refreshed CPI moves the whole region the same way, so hits and false alarms arrive together (§20.3).
4. **Fragility of CR's pass:**
   - one lost hit or one extra false alarm breaks R6;
   - R6 passes only for cuts 0.475-0.50;
   - R1-R7 pass in 9 of 13 leave-one-quarter-out subsets;
   - with each grid setting fixed, Lead-2 accuracy ranges 0.769-0.831 and 2 of 8 settings fail R1-R7. This is reported only; choosing among them would be selection on the evaluation rows;
   - 59% of the Brier gain comes from 2024-Q4.
5. **CPI timing assumption.**
   - Every refreshed CPI month satisfies the day-10 rule before its issue date, and the margins go down to 2 days.
   - PSA's actual release dates for the provincial table are **not recorded**.
   - At day 15 CR fails R6 (§20.4).
6. **Sample size.** 13 independent quarters (7 with HIGH). Detecting a Brier gain of CR's size needs about 58.

**Possible explanations (supported, not established):**

7. **Probability scale is not learnable from training folds.** The training-only Platt maps vary from slope −1.2 to 2.9 across origins.
8. **Poverty and news add noise at Lead 2 under CR.** Removing either improves Lead-2 Brier on uncorrected intervals; see section 7.
9. **Distribution shift between 2023-24 and 2025-26.** CR's later-block over-forecast is +0.20.

**Checked and ruled out:**
- **Leakage:**
  - target quarter = origin + lead for all rows;
  - CPI months follow the day-10 rule;
  - SWS and news were published before the issue date (1,575 dated news rows);
  - no training target after the origin;
  - selection uses inner training folds only.
- **Serving mismatch:** province score = served probability; region = mean of provinces.
- **Class weighting:** lowers recall in 180/180 pairs (§16).

## 3. Experiments performed (all recorded)

| ID | Experiment | Why | Result |
|---|---|---|---|
| X0 | Reproduce P0H4, P0H4-U, CR | Prerequisite | Reproduced (4.9e-7) |
| X1 | **CR-CAL**: Platt recalibration of CR's price part, fitted on inner training folds only | CR mis-scaled (slope 1.50; later over-forecast +0.20) | Brier improved; classification worse; **not adopted** |
| D1 | Settings sensitivity, 8 fixed grid configs | Overfitting and stability | 0.769-0.831; 2 of 8 fail |
| D2 | SHAP stability by origin | Importance stability | A1 has the top share at 13 of 15 origins (mean 0.56); rank correlation between consecutive origins 0.42-0.88 |
| D3 | Train / validation / test gap | Overfitting | Train Brier 0.13-0.22 vs inner validation 0.12-0.31; the gap is large before 2024 (e.g. 0.143 vs 0.310) and small after |
| D4 | Five-group ablation of CR | Trigger contribution | Section 7 |
| D5 | Errors by province, quarter, class; leave-one-quarter-out | Bias and generalisation | Section 6 |
| D6 | Timing and serving checks | Correctness | All pass; release dates unresolved |
| (§20) | Release-day sensitivity 10/15/20 | Timing robustness | R6 lost at 15 and 20 |

**Not run, with the reason (protocol §5):**
- class weighting;
- own-history, persistence and lagged-label features (no gain in LEAD2_TUNING N2, E95, E61);
- larger grids (360 configurations, no gain);
- news variants;
- any threshold change;
- alternative release-day candidates (that would be selection on known results).

## 4. Before and after (identical rows)

| Candidate | Lead 1 accuracy / Brier / failed | Lead 2 accuracy | Lead 2 balanced | Lead 2 precision / recall | Lead 2 F1 | Lead 2 TP FP FN TN | Lead 2 Brier (Δ vs P0H4-U, p) | Lead 2 calibration slope / in-the-large | 2023-24 / 2025-26 accuracy | Lead 3 accuracy | Status |
|---|---|---|---|---|---|---|---|---|---|---|---|
| P0H4 | 0.843 / 0.132 / none | 0.769 | 0.635 | 0.60 / 0.35 | 0.44 | 6 4 11 44 | 0.194 (+0.027) | 0.47 / +0.03 | 0.686 / 0.867 | 0.717 | served |
| P0H4-U | 0.843 / 0.132 / none | 0.800 | 0.732 | 0.63 / 0.59 | 0.61 | 10 6 7 42 | 0.167 | 1.04 / +0.07 | 0.771 / 0.833 | 0.633 | research baseline |
| CR | 0.871 / 0.123 / none | 0.800 | 0.751 | 0.61 / 0.65 | 0.63 | 11 7 6 41 | 0.147 (−0.020, p .11) | 1.50 / +0.09 | 0.771 / 0.833 | 0.533 | research-only |
| CR-CAL | 0.871 / 0.110 / none | 0.769 | 0.711 | 0.56 / 0.59 | 0.57 | 10 8 7 40 | 0.144 (−0.023, p .09) | 1.29 / +0.07 | 0.771 / 0.767 | 0.600 | **not adopted** |

## 5. Frozen criteria (`fr_lib.evaluate` R1-R7, `final.adoption_rule` vs P0H4-U; unchanged)

| Criterion | P0H4 | P0H4-U | CR | CR-CAL |
|---|---|---|---|---|
| R1 ≥ 10 quarters, ≥ 40 rows | pass | pass | pass | pass |
| R2 accuracy ≥ 0.75 | pass | pass | pass | pass |
| R3 balanced ≥ 0.70 | **fail** | pass | pass | pass |
| R4 beats always-LOW and persistence | pass | pass | pass | pass |
| R5 Brier < persistence and climatology, p < .10 | **fail** | pass | pass | pass |
| R6 precision and recall ≥ 0.60 | **fail** | **fail** | pass | **fail** |
| R7 thirds ≥ 0.60, leave-one-quarter-out ≥ 0.70 | pass | pass | pass | pass |
| Adoption: Lead-2 DEV Brier gain ≥ 0.005 | — | — | pass | pass |
| Adoption: Lead-1 DEV Brier not worse by > 0.005 | — | — | pass | pass |
| Adoption: Lead-2 DEV balanced not lower | — | — | pass | pass |
| Adoption: accuracy / balanced / precision / recall within 0.02 | — | — | pass | **fail** (accuracy, balanced, precision) |
| Adoption: new false alarms ≤ new hits | — | — | **fail (3 vs 2)** | **fail (4 vs 2)** |
| Adoption: Lead-2 later-block accuracy not lower | — | — | pass | **fail** |
| Adoption: Lead 1 passes R1-R7 | — | — | pass | pass |

## 6. Overfitting, bias, calibration, generalisation

- **Overfitting.**
  - The train–validation gap is large at the early origins and closes after 2024.
  - Results depend on model settings (D1) and on single rows and quarters (section 2, item 4).
  - Feature importance is stable in its top family: A1 dominates.
- **Bias.** Errors lean toward missed HIGH cases for P0H4 (11 of 15 errors). For CR they are balanced (6 misses, 7 false alarms).
  - **By province:** Laguna has the most CR errors (3 misses, 2 false alarms out of 5 HIGH). Rizal has 2 false alarms and no HIGH case.
  - **By period:** misses cluster in 2023-Q4 (the hunger cap) and 2024-Q4.
  - No province is free of errors; overall accuracy alone says nothing about fairness.
- **Calibration.**
  - P0H4 is overconfident (slope 0.47).
  - CR is under-confident overall (1.50) but over-forecasts in 2025-26.
  - Training-only recalibration does not fix this stably (X1).
- **Generalisation.**
  - DEV accuracy 0.771 and later-block 0.833 for both P0H4-U and CR; thirds 0.84 / 0.65 / 0.90.
  - Leave-one-quarter-out: CR passes all criteria in 9 of 13 subsets, CR-CAL in 0.
  - Overlapping forecast windows are not treated as independent: the unit is the target quarter.

## 7. Trigger groups (research-only ablation of CR; the final model keeps all 12 families)

ΔBrier of the risk probability when the group is removed. Positive means the group helped. 90% quarter-block CI; one-sided p (removal hurts), Holm-corrected across the five groups. SHAP shares are influence, not evidence.

| Group | Lead 1 ΔBrier (CI; Holm p) | Lead 2 ΔBrier (CI; Holm p) | Lead-2 calls changed | SHAP share (Lead 2) | Status |
|---|---|---|---|---|---|
| Market and prices | +0.062 (+0.028, +0.099; .001) | +0.056 (+0.026, +0.090; .003) | 15 | 0.66 (A1, A2, A3 and world prices, incl. urea) | **Supported at Leads 1 and 2** |
| Climate stress | +0.001 (−0.001, +0.004; .47) | +0.002 (−0.001, +0.007; .44) | 0 | 0.05 (C1-C3) | Not established |
| Employment and remittances | +0.008 (+0.000, +0.021; .14) | +0.002 (+0.000, +0.005; .09) | 0 | 0.02 | Observed, not confirmed after correction |
| Poverty and social vulnerability | −0.005 (−0.014, +0.004; .82) | −0.017 (−0.031, −0.005; 1.0) | 5 | 0.13 | Not established. Removal helped at Lead 2 on an uncorrected interval; no corrected test exists for that direction. |
| News and NLP | +0.007 (−0.004, +0.018; .47) | −0.008 (−0.017, −0.000; 1.0) | 8 | 0.07 | Not established; the same caveat at Lead 2 |
| Fish production (separate) | −0.000 | −0.000 | 2 | 0.04 | Not established |
| Regional hunger outlook H1 (separate) | −0.001 | +0.002 | 0 | 0.02 | Not established |

**Data quality:**
- News FSSI (N1) is missing in 79% of rows. All dated news was published before the issue date.
- Employment (E1) and remittances (E2) are national series; E1 tracks the calendar trend.
- Poverty (V1) is a fixed provincial profile, so it can separate provinces but cannot anticipate change.

Removing poverty or news to improve Lead 2 would violate the 12-indicator requirement, and would be selection on the evaluation rows.

## 8. Timing and leakage audit

| Check | Result |
|---|---|
| Target quarter = origin + lead (Lead 1 and Lead 2) | pass, all stack rows |
| CPI refresh month = newest month under the day-10 rule at the schedule-B date | pass, 1,610 rows |
| PSA month, SWS round and news published before the issue date | pass (input audit; 1,575 dated news rows) |
| No training target after the origin; selection on training folds only | pass |
| Future-perturbation of CPI (later months set to 999) | no refreshed value changes |
| Served predictions = evaluated P0H4 (70 retrospective rows) | exact |
| Dashboard province score = served probability; region = mean of 5 provinces | pass (Lead 1 2026-Q4, Lead 2 2027-Q1) |
| **Actual PSA provincial CPI release dates** | **UNKNOWN for all 18 refreshed months** (section 13.1: official sites behind bot verification, regional page dates are re-postings). The day-10 rule is an assumption; CR fails R6 if the release is after day 15 |

## 9. Changes and files

No served file, model, threshold, flag or deployment setting was changed.

| File | Change |
|---|---|
| `PROTOCOL_LEAD2_CR_RESOLVE.md`, `runner/CR_RESOLVE_SHA256.txt` | Frozen protocol (9a64352) |
| `runner/cr_resolve.py` | Reproduction, CR-CAL, diagnostics |
| `out/cr_resolve.json`, `out/cr_resolve_rows.csv` | Machine-readable results, including seed 2027, grid, columns, input-file hashes and the evaluation window 2023-Q1..2026-Q3 (Lead 2: 2023-Q2..2026-Q3) |
| `LEAD2_CR_RESOLVE_REPORT.md` | This report |
| `backend/tests/integration/test_lead2_cr_resolve.py` | 6 tests |
| `LEAD2_THESIS_PACKAGE.md` | Section 22 (summary and link) |

## 10. Tests and reproducibility

- **CR / Lead-2 test files:** 29 passed.
- **Full backend suite:** **963 passed, 18 skipped, 0 failed**.
- **Reproduction:**
  - refits match committed rows to 4.9e-7;
  - the served export matches exactly;
  - `cr_resolve.json` records the input hashes.

## 11. Remaining blockers and the evidence that would resolve them

1. **PSA's recorded release dates of the provincial CPI table, 2022-2026.** They would confirm or refute the day-10 rule on which CR's R6 pass depends.
2. **Scored prospective quarters** from the sealed CR forecasts (2026-Q4 to 2027-Q3), the only untouched test.
3. **A repeated provincial food-insecurity outcome** (CBMS or FNRI FIES). It would replace the price condition as the provincial part of the target.
4. **An inter-round hunger observation** for the three quarters capped at 11.3%.
5. **More quarters.** About 58 are needed to separate candidates of this size.

## 12. Adoption

**CR stays research-only.** It fails the frozen adoption rule, and the investigation found no defensible correction that passes. Under the existing rules, adopting it would require the prospective evidence in item 2, together with item 1.

## 13. Evidence-gap follow-up (2026-10-29; `runner/evidence_gaps.py`, `out/evidence_gaps.json`, `data/psa_cpi_release_evidence.csv`)

No model candidate was run. The served model, criteria, target, labels and seals are unchanged.

### 13.1 PSA CPI release timing: **UNRESOLVED (all dates UNKNOWN)**

- **Series.** PSA OpenSTAT 0012M4ACP22: CPI for all income households by province and commodity group (2018=100), food and all items, monthly, for Batangas, Cavite, Laguna, Quezon and Rizal.
- **Repository copy.** One undated download (`E41_Lead2_Audit/data_acquired/cpi_index_ACP22.csv`), with values through 2026-09 and no release-date metadata.
- **Months to verify.** CR refreshes 18 reference months across its 13 Lead-2 issue dates. Nine of them are within 14 days of the issue under the assumed day-10 rule:
  - 2022-12, 2023-04, 2023-10, 2023-12, 2024-06, 2024-12, 2025-07, 2025-12, 2026-04;
  - the margins run down to 2 days (2023-04 at 2023-05-12) and 3 days (2026-04 at 2026-05-13).
- **What was tried** (all logged with URLs and the retrieval date):
  - **psa.gov.ph** (national Summary Inflation Reports) and **rsso04a.psa.gov.ph** (Region IV-A provincial reports): both are behind bot verification, which was not bypassed.
  - **PIA:** HTTP 403. **PNA:** the article has moved (404).
  - **Regional page dates are not release dates.** A search result shows the Batangas December 2024 report carrying a page date of 27 August 2025.
- **Result.** 0 of 18 dates verified; 18 marked UNKNOWN. The day-10 rule stays an assumption and is not recorded as evidence.
- **No recalculation.** No evidence shows the rule was violated, so the CR results stand as computed. The sensitivity stays the reference: CR loses R6 if the provincial release falls after day 15.
- **What would verify the dates:** the PSA Advance Release Calendar, or the PSA RSSO IV-A release log with the original release dates of the provincial CPI tables for those 18 months. A person can also read the releases after completing the sites' bot check.
- **Exposure check.** The search summaries quoted April and June 2026 CALABARZON figures. Those quarters are not sealed, and those CPI months are already in the data. No value for 2026-Q4 or later was seen (`data/psa_cpi_release_exposure_note.md`).

### 13.2 What the target measures

**Formula** (rebuilt from source with 0 mismatches, FORECAST_RESEARCH_II `target_audit.py`):

y(p, q) = 1[H_BL(q) > 11.3] × 1[m_food(p, q) > 0 or m_gap(p, q) > 0]

- H_BL is the mean of the SWS Balance Luzon involuntary-hunger rounds in quarter q.
- m_food is the quarterly mean of published food CPI YoY minus the province's 2021-Q1..2022-Q4 60th percentile.
- m_gap is food YoY minus all-items YoY, minus that window's 60th percentile.

| Part | Observed? | Measures food insecurity? | Geography |
|---|---|---|---|
| SWS involuntary hunger > 11.3% | Yes (survey; sampling SE 1.3-2.3 pp) | **Yes**: experienced hunger | Balance Luzon (all of Luzon outside Metro Manila), not CALABARZON or a province |
| Food-price pressure (m_food, m_gap) | Yes (PSA CPI) | **No**: an affordability proxy relative to the province's own 2021-22 level | Province |
| V1 poverty/density, E1, E2, C1-C4, A2, A3, news, H1, world prices | Predictors only | Not outcomes | Mixed (several national) |

**Findings:**
- The hunger part is identical for all five provinces in every quarter. It is met in 11 of the 13 Lead-2 quarters and in every quarter since 2023-Q4.
- In those quarters the label equals the price condition: 100% of rows since 2023-Q4, 76% overall.
- Province price pressure does not track the hunger level (ρ ≈ −0.38, not significant). Provincial FIES points exist for only three geographies in 2021 and the region in 2023 and 2025, too few to validate a provincial ranking over time.

**Implication.** The label supports a claim about *provincial food-price pressure while regional hunger is high*. It does **not** support province-specific food-insecurity claims (which province's households are more food-insecure). That needs a repeated provincial food-insecurity outcome (CBMS or FNRI FIES), which the data does not contain. The target was not changed and no observation was relabelled.

### 13.3 The prospective test

| Item | Status |
|---|---|
| File | `sealed/cr_prospective.csv`: 20 rows (5 provinces × Leads 1-4), targets 2026-Q4, 2027-Q1, 2027-Q2, 2027-Q3 |
| Seal | SHA-256 dd293e2e… recorded 2026-10-28 15:06 UTC (commit 80bbe98); **intact** |
| Issue dates | Lead 1 2026-10-01; Leads 2-4 2026-10-15 (re-issue after the 2026-10-14 SWS release) |
| Reproduction | Re-run from the committed snapshot without writing: max \|Δ\| 4.8e-7; issue dates equal |
| Input snapshot | SHA-256 of `stack_l2.csv`, `known_price_l2.csv`, `cpi_refresh.csv`, `sws_rounds_primary.csv` and `cpi_index_ACP22.csv` recorded in `out/evidence_gaps.json` |
| Model configuration | U2 unified LightGBM refit at origin 2026-Q3 (21 columns, 12 families, 8-configuration grid, seed 2027, monotone A1/A_mom, day-10 CPI rule, S-AB hunger term, cut 0.50) |
| No sealed outcome in the data | Labels and SWS end at 2026-Q3; CPI ends at 2026-09 |
| Outcomes required before scoring | For each target quarter: every SWS Balance Luzon round of the quarter; PSA provincial food and all-items CPI for all three months, for the five provinces |
| Scoring rule | The frozen T43c rule with the 2021-22 thresholds. Each quarter's five calls and probabilities are scored descriptively (TP/FP/FN/TN, Brier). R1 needs at least 10 quarters and 40 rows before R1-R7 can be applied. Nothing is refitted, re-thresholded or re-sealed. |
| Earliest possible scoring | 2026-Q4 (Lead 1 only), once the Q4 SWS round and the December 2026 CPI are published. The first Lead-2 target (2027-Q1) follows a quarter later. |

### 13.4 Verdict of the follow-up

- **Verified:**
  - the CPI series and its snapshot;
  - the label formula and its decomposition;
  - the seal's integrity and its reproduction;
  - the absence of any sealed outcome in the data.
- **Unknown:** PSA's actual provincial CPI release dates for all 18 refreshed months.
- **No new evidence changes the Lead-2 conclusion.** CR stays research-only, P0H4 stays served, and the maximum reliable horizon is Lead 1.
- **Reconsidering CR needs all three:**
  1. verified release dates showing the refreshed months were public before each issue date (and, if any was not, a re-scored CR under the verified dates, with the original kept);
  2. scored prospective quarters;
  3. a provincial food-insecurity outcome before any province-specific food-insecurity claim.

### 13.5 Tests (2026-10-29)

- `backend/tests/integration/test_lead2_evidence_gaps.py` (4 tests), run with the CR test files: **22 passed**.
- Full backend suite: **967 passed, 18 skipped, 0 failed**.
