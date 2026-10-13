# Origin-Information Study: What the Model Can Know at Forecast Time (2026-10-09)

**Scope:**

- Approved period 2021–2026; nothing from before 2021 is used.
- K1–K4 and window rule W are kept.
- Production, `data/processed/`, the models, existing reports and evidence, the v3 frozen forecasts and the thesis chapters are unchanged.
- Nothing was downloaded, committed or deployed.
- Checks: 159 tests pass; the production consistency check passes 39/39.

**Files:**

| Item | Location |
|---|---|
| Pre-registration (before any v4 run) | `experiments/2026-10-09_origin_info/PREREGISTRATION_v4.json`, SHA-256 `4ac66c03…896d` |
| Amendment, rule L (written before any v4 run) | `PREREGISTRATION_v4_AMENDMENT_L.json`, SHA-256 `c1c5c2ae…53c8` |
| Script | `scripts/supplementary/origin_info_study.py` |
| Tests | `tests/unit/test_origin_info.py` (5 tests) |
| Outputs | `stageA_results.json`, `stageA_predictions.csv`, `news_regeocode_candidates.csv`, `FROZEN_2026_N2.csv`, `FROZEN_2026_RULE_L.csv` (SHA-256 `9da199ba…269d`), `run.log` |

---

## Answer

**The 75% target is not achieved, and this study found that earlier scores were inflated by a timing leak.**

**Training-label leakage (new finding):**

- In 7 of the 8 outer folds, every earlier study trained on the label of the quarter just before the test quarter. That label's SWS round had **not yet been published at the forecast date**. In the 2025-Q1 fold, two such labels were used.
- Rule L removes the leak: a model may train only on labels released before its forecast date.

| Model | Without rule L (as reported earlier) | **With rule L (timing-valid)** |
|---|---:|---:|
| MODEL-B2 configuration (`gov_c`, `spw`) | 32/40 = 80.0% | **29/40 = 72.5%** |
| `gov_c` logistic (the earlier hypothesis) | 34/40 = 85.0% | **31/40 = 77.5%** |
| Clock only | 30/40 = 75.0% | **25/40 = 62.5%** |
| Nested procedure P4 | 29/40 = 72.5% | **25/40 = 62.5%** |
| Eq. 3 rule (nothing fitted) | 29/40 = 72.5% | 29/40 = 72.5% (unaffected) |
| Timing-valid persistence | 29/40 = 72.5% | 29/40 = 72.5% (unaffected) |

**Under fully timing-valid evaluation, no pre-specified trained model beats carrying forward the last released label (72.5%).**

- **The only result above 75%** is the logistic configuration at 77.5%. It was singled out in the v3 study *after* seeing these 40 rows, so it is a hypothesis, not evidence.
- **The pre-registered primary candidate N2** (an SWS nowcast plus Eq. 3) scores **65.0%** and fails. Its SWS estimates were **worse** than simply using the latest released SWS (mean absolute error 4.98 vs 4.39 points).

**Two things limit accuracy:**

1. **SWS can't be estimated better than its last released value from the quarterly data in the project.** About 15 usable training quarters are too few to learn more.
2. **Rule L costs 1–2 more training quarters per fold.** Each forecast effectively has to look about 3 quarters past the last label it can learn from.

**Monthly CPI and rice data are the next justified step.** They are not in the project and need your authorization to download (Section 2).

## 1. Leakage, timing and missing-value tests

| Test (`tests/unit/`) | What it checks |
|---|---|
| `test_origin_info.py::test_rule_l_excludes_unreleased_training_labels` | No training label in any outer fold was released on or after the forecast date |
| `…::test_without_rule_l_the_previous_quarter_leaks` | Documents the earlier defect: exactly 7 of 8 folds leak without rule L |
| `…::test_nowcast_uses_training_quarters_only` | Changing the test quarter's outcome does not change N2's forecast |
| `…::test_frozen_rule_l_forecasts_trained_on_released_labels_only` | The new frozen 2026 forecasts use only labels released before each forecast date (latest: 2025-Q1, released 2025-03-29) |
| `test_window2021.py` (7) | No pre-2021 values; SWS rounds released before the target quarter; missing values, not zeros, at the window edge |
| `test_improvement_corrections.py` (9) | K1–K4; the strict-timing shift does not zero-fill |
| `test_generalization_protocol.py` (6) | Inner and outer splits keep provinces together by quarter; scaling and class weights are fitted in-fold |

**Label-timing audit by fold:**

| Test quarter | Training quarters (old) | With rule L | Unreleased labels the old protocol used |
|---|---:|---:|---|
| 2023-Q3 | 8 | 7 | 2023-Q2 |
| 2023-Q4 | 9 | 8 | 2023-Q3 |
| 2024-Q1 | 10 | 9 | 2023-Q4 |
| 2024-Q2 | 11 | 10 | 2024-Q1 |
| 2024-Q3 | 12 | 11 | 2024-Q2 |
| 2024-Q4 | 13 | 12 | 2024-Q3 |
| 2025-Q1 | 14 | 12 | 2024-Q3, 2024-Q4 |
| 2025-Q4 | 15 | 15 | none |

**What this affects:**

- **Every trained-model result in the earlier reports**: MODEL-B2 81.8%, the nested 74.5% / 70.9% / 72.5%, and the clock-only 78.2% / 75%. These scores include this leak.
- **Not affected:** the persistence and Eq. 3 results, which already respected release dates.
- **The v3 frozen 2026 forecasts** (`experiments/2026-10-09_window2021/FROZEN_2026_FORECASTS.csv`) were trained with the 2025-Q4 label, released 2026-05-12, which is after both forecast dates. They are **preserved unchanged** but are **not timing-valid**. Rule-L versions are in `FROZEN_2026_RULE_L.csv`.

## 2. Monthly CPI and rice prices: verified need, collection plan (not executed)

**The project holds no monthly series.** The fetchers query monthly data but store only quarterly means:

- `openstat_fetcher._merge_to_quarterly`;
- `psa_rice_fetcher` (averages per quarter);
- `cpi_full_fetcher`.

Under strict timing the model therefore sees quarter t−1 in full. The first two months of quarter t, typically published before quarter t+1 begins, are discarded.

**Sources to collect (all within 2021-01 to the latest 2026 month):**

| Variable | Source table (PSA OpenStat PXWeb) | Geography | Units | Already referenced in |
|---|---|---|---|---|
| Food & non-alcoholic beverages CPI, monthly, 2018=100 | `DB/2M/PI/CPI/2018NEW/0012M4ACP22.px` | **Province** (the 5 CALABARZON provinces) | Index | `openstat_fetcher.py` l.199 |
| Food CPI year-on-year rate, monthly | `DB/2M/PI/CPI/2018NEW/0012M4ACP23.px` | Province | % | `openstat_fetcher.py` l.275 |
| Regular-milled rice, wholesale, monthly | `DB/2M/NWSNEW/0052M4AWB01.px` | Province | PHP/kg | `psa_rice_fetcher.py` l.57 |

**Release dates.** OpenStat tables carry no release dates, so each one must be verified separately:

- **CPI:** the release date of PSA's monthly *Summary Inflation Report CPI (2018=100)* for each reference month (psa.gov.ph price-indices pages and the PSA Advance Release Calendar). Provincial tables must be confirmed to appear on the same day as the national release.
- **Wholesale rice:** the release date of PSA's monthly wholesale-price publication for each reference month.
- **Revisions:** keep the value as first published where PSA's release archive allows. Otherwise record that the current vintage is used.

**Collection steps for authorization:**

1. Re-run the three PXWeb queries (2021-01 to 2026-latest) and save the **monthly** rows unaggregated to `data/supplementary/monthly_origin/`, with `fetched_at`. This is about 3 tables × 5 provinces × about 69 months, roughly 1,000 rows, a few hundred KB.
2. Build a release-date ledger (`release_calendar.csv`: series, reference month, release date, source URL) from the PSA release pages.
3. Build an origin-availability table: for each forecast quarter T, the latest month of each series released before T starts.
4. Run Stage B exactly as pre-registered (B1–B4; primary B4) under rule L.

**I have not downloaded anything.** Please confirm steps 1–2. Fetching from psa.gov.ph and openstat.psa.gov.ph is an external download.

## 3. News: can more articles be assigned to provinces?

- **The pool:** 2021+ articles that pass the approved 0.30 threshold. Of these, **48 already have a province and 46 do not**. All 3,773 unscored articles also lack a province, so they cannot enter a province FSSI.
- **The test:** the documented 142-LGU / barangay geocoder (`location_geocoder.py`), run on the 46 unassigned articles.
- **The result:** it assigns 6, and checking each one by hand shows **5 are false matches**:

| Article | Assigned to | Why it is wrong |
|---|---|---|
| "USTR … Greenhills market" | San Juan, Batangas | Greenhills is in San Juan, Metro Manila |
| "Mayors, MMDA to monitor market prices" | San Juan, Batangas | MMDA is Metro Manila |
| "Food security … quarantine" | Lopez, Quezon | "Lopez" is a surname |
| "DSWD: giving cash…" | Lopez, Quezon | "Lopez" is a surname |
| "33 grocery items" | Lopez, Quezon | "Lopez" is a surname |

The sixth, a Calatagan (Batangas) mural article, is geographically correct but not about food insecurity.

**Conclusion (pre-registered rule: fewer than 10 genuine, so no data change).** Under the approved threshold and documented geocoding rules, province news coverage cannot be meaningfully expanded with the existing corpus. The remaining retained articles are national stories. More province news needs new province-specific collection, not re-tagging. The `Lopez` and `San Juan` false positives are a geocoder precision issue worth fixing before any future re-tag.

## 4. Candidate comparison (timing-valid, rule L)

Same 40 rows (2023-Q3 to 2025-Q4), threshold 14.345.

| Model | Correct | Acc | F1 (w) | ROC-AUC | Brier | Within-quarter AUC | HIGH recall | Missed / false HIGH | Confusion [[TN, FP], [FN, TP]] |
|---|---:|---:|---:|---:|---:|---:|---:|---|---|
| **N2: SWS nowcast + Eq. 3 (pre-registered primary)** | 26 | **0.650** | 0.679 | 0.742 | 0.284 | 0.78 | 0.61 | 12 / 2 | [[7, 2], [12, 19]] |
| N1: SWS shrinkage + Eq. 3 | 18 | 0.450 | 0.464 | 0.724 | 0.341 | 0.78 | 0.32 | 21 / 1 | [[8, 1], [21, 10]] |
| MODEL-B2 configuration | 29 | 0.725 | 0.746 | 0.796 | 0.186 | 0.75 | 0.71 | 9 / 2 | [[7, 2], [9, 22]] |
| `gov_c` logistic (hypothesis, post hoc) | 31 | 0.775 | 0.790 | 0.860 | 0.165 | 0.80 | 0.77 | 7 / 2 | [[7, 2], [7, 24]] |
| P4 nested | 25 | 0.625 | 0.654 | 0.703 | 0.303 | 0.78 | 0.55 | 14 / 1 | [[8, 1], [14, 17]] |
| Eq. 3 rule | 29 | 0.725 | 0.746 | 0.814 | 0.203 | 0.78 | 0.71 | 9 / 2 | [[7, 2], [9, 22]] |
| Timing-valid persistence | 29 | 0.725 | 0.746 | n/a | n/a | n/a | 0.71 | 9 / 2 | [[7, 2], [9, 22]] |
| Clock only | 25 | 0.625 | 0.656 | 0.760 | 0.198 | n/a | 0.58 | 13 / 2 | [[7, 2], [13, 18]] |

**N2 pre-registered acceptance:**

| Criterion | Result |
|---|---|
| C1 accuracy ≥ 0.75 | 0.650 (fail) |
| C2 lower bounds ≥ 0.75 | 0.50 / 0.51 (fail) |
| C3 beats baselines | vs persistence −0.075; vs clock +0.025, CI includes 0 (fail) |
| C4 leave-one-year-out ≥ 0.75 | 0.60–0.70 (fail) |

## 5. Fold-by-fold results (rule L)

| Quarter | HIGH / 5 | N2 | MODEL-B2 configuration | Logistic (hypothesis) | P4 nested | Eq. 3 rule / persistence | Clock |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2023-Q3 | 1 | 1.0 | 0.8 | 0.8 | 0.8 | 0.8 | 0.8 |
| 2023-Q4 | 3 | 0.6 | 0.4 | 0.6 | 0.6 | 0.6 | 0.4 |
| 2024-Q1 | 4 | 0.8 | 0.6 | 0.6 | 0.4 | 0.4 | 0.2 |
| 2024-Q2 | 5 | 0.4 | 0.4 | 0.8 | 0.2 | 0.6 | 0.0 |
| 2024-Q3 | 4 | 0.8 | 0.8 | 0.8 | 0.2 | 0.6 | 0.8 |
| 2024-Q4 | 5 | 0.6 | 1.0 | 0.8 | 1.0 | 1.0 | 1.0 |
| 2025-Q1 | 5 | **0.2** | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 |
| 2025-Q4 | 4 | 0.8 | 0.8 | 0.8 | 0.8 | 0.8 | 0.8 |

**Why the SWS nowcast failed:**

| Quarter | Nowcast | Actual | Latest released SWS |
|---|---:|---:|---:|
| 2024-Q2 | 13.3 | 19.6 | 14.3 |
| 2024-Q4 | 15.9 | 25.3 | 19.6 |
| 2025-Q1 | 10.5 | 24.0 | 19.6 |

- The ridge model, trained on 9–12 quarters, pulled back toward the historical mean exactly when hunger surged.
- Its 2026-Q2 nowcast (32.2) is an extrapolation and should not be trusted.

## 6. Regional vs province-specific prediction

| Model | Within-quarter AUC |
|---|---:|
| `gov_c` logistic | 0.80 |
| Eq. 3 province term (N2, N1, rule) | 0.78 |
| MODEL-B2 configuration | 0.75 |

- **Within-quarter ranking holds up after the timing correction.** It barely moved, because the province term (`cpi_rel`) does not depend on training labels.
- **Rule L hurts the quarter-level component.** Overall accuracy fell, while province ranking stayed the same.
- **The bottleneck is the regional SWS regime, not province discrimination**, consistent with every earlier study.

## 7. Strongest defensible configuration

**Under timing-valid evaluation, the defensible choice is the Eq. 3 rule** (latest released SWS + 2 × `cpi_rel`, threshold 14.345):

- It needs no training labels, so rule L cannot inflate or deflate it.
- It ties the best pre-specified trained model (72.5%).
- It has better AUC (0.81 vs 0.80) and within-quarter AUC (0.78 vs 0.75) than the MODEL-B2 configuration.
- It is fully explainable from Eq. 3.

**The MODEL-B2 configuration remains the governing thesis model.** Its timing-valid figure is 72.5%, not 80% or 81.8%.

**The logistic configuration (77.5%)** is the only result above 75%, but it was chosen after seeing these rows. It is frozen for prospective testing (`FROZEN_2026_RULE_L.csv`) and is not a result.

## 8. Is the 75% target achieved?

**No.**

| Evidence | Result |
|---|---|
| Score on the reused 40 rows, timing-valid | 72.5% for the best pre-specified models; 65.0% for the pre-registered primary |
| Chronological validation | Inner scores 0.71–0.90 under rule L |
| Against simple baselines | No model beats timing-valid persistence |
| Prospective | Pending (no 2026 labels) |

## 9. 2026 prospective evaluation

**Preserved unchanged:**

- `experiments/2026-10-09_window2021/FROZEN_2026_FORECASTS.*` (v3). Marked **not timing-valid**: training included the 2025-Q4 label, released 2026-05-12.
- `experiments/2026-10-09_generalization/FROZEN_PROSPECTIVE_CONFIG.json`.

**New, rule-L compliant, label-blind:**

| File | Contents | 2026-Q1 HIGH calls | 2026-Q2 HIGH calls |
|---|---|---:|---:|
| `FROZEN_2026_N2.csv` | N2 | 5 / 5 | 5 / 5 |
| `FROZEN_2026_RULE_L.csv` | MODEL-B2 configuration | 5 / 5 | 5 / 5 |
| `FROZEN_2026_RULE_L.csv` | Eq. 3 rule | 5 / 5 | 5 / 5 |
| `FROZEN_2026_RULE_L.csv` | Logistic hypothesis | 5 / 5 | 4 / 5 |

All were trained on labels through 2025-Q1, the latest released before both forecast dates.

**These are retrospective simulations, not real-time forecasts.** Every input table was fetched between 2026-09-04 and 2026-09-23, after the forecast dates (`stageA_results.json → frozen_2026_provenance`). The values are current vintages, not as originally released. They are label-blind: no 2026 SWS round is in the project.

**Plan for the remaining 2026 quarters:**

1. **When SWS publishes the 2026-Q1 and Q2 rounds**, add them with their release dates and compute Eq. 3 labels at 14.345. Score every frozen file as is: report all quarters, with no refitting beforehand, against persistence and clock-only.
2. **For 2026-Q3 and Q4 (needs authorization):** collect provincial food CPI for 2026-Q1 and Q2 (`psa_indicators` ends 2025-Q4) and, if approved, the monthly series (Section 2). Then issue forecasts **before** each forecast date where still possible. 2026-Q4's forecast date has passed, so its forecast will also be retrospective.
3. Apply C1–C4 cumulatively once at least 4 prospective quarters exist, and report the interval every time.

## 10. Decisions that need adviser approval

| # | Decision |
|---|---|
| E1 | **Restate earlier reported accuracies under rule L.** MODEL-B2 is 72.5% (not 80% / 81.8%), and the earlier nested and clock figures fall too. This affects every trained-model number in the earlier reports. |
| E2 | Treat the Eq. 3 rule as the reference forecaster alongside the governing MODEL-B2 configuration |
| E3 | Authorize collection of monthly provincial CPI and wholesale rice (2021–2026) plus the release-date ledger (Section 2) |
| E4 | Authorize collection of 2026 provincial CPI and the 2026 SWS rounds for prospective scoring |
| E5 | Still open: the window (2021–2026 vs Chapter III's 2020–2025), the threshold (14.345 vs 14.6), production adoption, how the 75% requirement is judged, Chapter III wording, Algorithm 4, H3 |
