# aiPHeed final model report: food-insecurity risk forecasting for CALABARZON provinces

2026-11-06. Branch `aiPHeed/e158-thesis-model`.

**Companion documents (this folder):**
- FINAL_FAILURE_AUDIT
- TARGET_VALIDITY_AUDIT
- DATA_AVAILABILITY_AND_PROVENANCE
- CALIBRATION_AUDIT
- MODEL_OPTIMIZATION_REPORT
- MODEL_COMPARISON_REPORT
- MAX_RELIABLE_LEAD_REPORT

**Reproduction:**
- `backend/app/final_audit/run.py`
- tests: `backend/tests/unit/test_final_audit.py`, 12 passed
- experiment log: `docs/EXPERIMENT_REGISTRY.md`

## Recommendation: **RETAIN E158**
- **E166 is the strongest trustworthy candidate, but the evidence is insufficient to accept it.**
- **No model has a reliable forecast lead** (maximum reliable lead = 0).

## Objective-aligned results (Lead 1, one quarter ahead, 72 out-of-sample provincial forecasts)
| Model | Accuracy | Precision (HIGH) | Recall (HIGH) | F1 (HIGH) | Macro F1 |
|---|---|---|---|---|---|
| Persistence | 62.5 % | 0.48 | 0.96 | 0.64 | 0.62 |
| **E158 (production)** | **73.6 %** | 0.58 | 0.84 | 0.69 | 0.73 |
| **E166 (best candidate)** | **76.4 %** | 0.61 | **0.92** | **0.70** | **0.76** |

At Lead 2, E166 reaches **79.2 %**.

## Answers to the review questions
| # | Question | Answer |
|---|---|---|
| 1 | What was wrong with previous models? | Upward bias on LOW provinces in 2018/2019; failed calibration (C4); C1 short at Lead 1; E164's inputs were test-selected; E167 was unstable; employment and remittances have no provincial signal; news adds no out-of-sample value |
| 2 | Verified root causes | The national HFIAS fall after 2015 was unseen by the 2018/2019 origins (one training round); round-specific, sign-changing errors; about 46 effective observations; national-only employment and remittance data |
| 3 | Corrected | Test-selected features removed (E165); source choice moved into training-only selection (E166); provincial ordering improved (0.60 → 0.75); LGU multiplier removed; the C4 definitional inconsistency resolved and documented; a maximum-lead tool for every model |
| 4 | Calibration method selected | **None.** Platt, linear and prior/intercept recalibration, fitted on training data only, never beat the uncalibrated baseline. Isotonic is unsupported at this sample size |
| 5 | Did calibration improve on the baseline? | **No.** A chronological recalibration from 2018/2019 made 2021 worse (bias −2.0 → −7.9) |
| 6 | Accuracy, precision, recall, F1 | E166 improved all of them over E158 (76.4 % vs 73.6 %; recall 0.92 vs 0.84; macro F1 0.76 vs 0.73), **but not significantly** (McNemar p = 0.77; Brier −0.010 [−0.038, +0.020]) |
| 7 | HIGH detection without excessive false alarms? | Yes: E166 misses 2 of 25 HIGH with the same 15 false alarms as E158 (13 at Lead 2) |
| 8 | Real inputs beat shuffled? | **E166: yes**, −0.035 [−0.063, −0.009]. **E165 and E167: no.** The signal is selection-sensitive |
| 9 | Generalised across time and provinces? | **Partly.** Better in 2018 and 2019, worse in 2021. Province order within regions 0.75. One row per province, so provincial generalisation cannot be tested |
| 10 | C1–C6 | Lead 1: C2, C3, C5, C6 pass; **C1 fails by one forecast, C4 fails.** Lead 2: C1 passes, C4 fails |
| 11 | Maximum reliable lead (E156) | **0 quarters.** Skill horizon against persistence: 6 quarters (E166), 5 (E158) |
| 12 | Better than E158? | Better on point estimates, **not statistically**. It fails the bias (+3.25 vs a ±3 limit), 2021-round and calibration gates |
| 13 | Suitable for production? | **No.** E158 remains. The production dashboard and API were not changed. *Per the 2026-11-04 compliance audit, live `main` serves an earlier model (FIRI v2), not E158; wiring E158 needs the owner's go-ahead* |
| 14 | Data needed | (a) **ENNS 2022 provincial HFIAS** (20 provinces; frozen forecasts already sealed 49e514d2) or a later provincial HFIAS round; or the FNRI public-use microdata, which needs a request; (b) PSA regional HFCE **2025**; (c) provincial LFS and SOF / regional remittances; (d) prospective scoring of the 2027 seals |

## CALABARZON
- **Forecast status:** all five provinces are **LOW** for 2027-Q1 (E158, sealed f69e7a02):

| Province | Score |
|---|---|
| Batangas | 26.6 |
| Cavite | 32.1 |
| Laguna | 29.8 |
| Quezon | 31.6 |
| Rizal | 35.5 |

  Each has a 90 % range of about ±15 points. **They are shown unranked.**
- **Consistent with:**
  - FNRI HFIAS: every reading below 50 since 2013;
  - PSA FIES 2023: Region IV-A at 19.1 %, the lowest of 17 regions.
- **Back-test:** 5 of 5 classes are right, but **no HIGH case has ever been observed in CALABARZON**, so high-risk detection there is untested.
- **Quezon is closest to the line:** 48.9 (2013), 48.8 (2015), 44.0 (2019).

## Statement for Chapter IV
> "aiPHeed forecasts food-insecurity risk for the five CALABARZON provinces. The production model achieved 73.6 % one-quarter-ahead accuracy (precision 0.58, recall 0.84, F1 0.69), significantly better than persistence. A training-only automated selection with regional household consumption reached 76.4 % (recall 0.92, F1 0.70) and 79.2 % at two quarters, but the gain was not statistically significant and the model did not meet the predefined bias, round-stability and calibration criteria. No forecast lead met all six reliability criteria; calibration could not be established because forecast errors shifted direction between the three available survey rounds. Additional provincial HFIAS rounds are required."
