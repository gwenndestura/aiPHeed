# FINAL vs FINAL-ET: results (scored once under PROTOCOL_SA, sha 15202d27; candidate protocol sha c5e76bd5)

**Evidence class:** retrospective on the 72 reused province-rounds. FINAL-ET differs from FINAL only in the 25 ENNS 2021 rows at Leads 1–6. Primary: Lead 1. 95 % intervals resample province-rounds.

## Answer

**FINAL-ET passes stability across rounds (Rule 7) but fails probability reliability (Rule 6): 6 of 7. Not accepted.**

Removing the double-counted trend lifts all 2021 forecasts:
- one more HIGH province is found (Agusan del Sur);
- four new false alarms appear in 2021;
- the pooled mean probability now exceeds the HIGH rate by 0.1025, and the Cox calibration test rejects (p = 0.031).

FINAL stays 6 of 7, failing Rule 7c.

## Seven rules (Lead 1)

| Rule | FINAL | FINAL-ET | Evidence |
|---|---|---|---|
| 1 Data integrity | PASS | PASS | `../aiPHeed_final_standalone_20261113/evidence/R1_R2_integrity.json` (10/10). FINAL-ET reads the same rows and inputs. The elapsed time uses the pipeline's release rule only |
| 2 Forecast validity | PASS | PASS | Same file. Origin = target − lead and anchor release checks on every row. The staleness definition uses only rounds released by the origin |
| 3 Balanced accuracy / AUROC ≥ 0.70 | PASS: 0.847 [0.75, 0.93] / 0.898 [0.81, 0.96] | PASS: 0.824 [0.72, 0.91] / 0.904 [0.83, 0.96] | `evidence/E_FINALET_summary.json`; standalone `E_FINAL_summary.json` |
| 4 HIGH recall ≥ 0.80 | PASS: 0.80 (20/25) [0.64, 0.95] | PASS: 0.84 (21/25) [0.68, 0.96] | Same |
| 5 Precision ≥ 0.60 | PASS: 0.80 [0.63, 0.95] | PASS: 0.70 [0.52, 0.86] | Same |
| 6 Probability reliability (n < 600 form) | PASS: ECE 0.080 ≤ 0.152; mean p − rate +0.046; Cox p 0.41; BSS 0.58 | **FAIL**: ECE 0.128 ≤ 0.164 (pass); **mean p − rate +0.1025 > 0.10; Cox p 0.031 < 0.05**; BSS 0.53 | Same; `evidence/E_FINALET_reliability_L1.png` |
| 6 as originally proposed (reported) | FAIL (ECE 0.080; slope 1.25; logit intercept −0.33) | FAIL (ECE 0.128; slope 1.52; intercept −0.65) | Same |
| 7 Stability and reproducibility | **FAIL** (7c: 2021 recall 0.25) | PASS (7a, 7b, 7c, 7e) | Below |
| **Rules passed** | **6 of 7** | **6 of 7** | |

## Rule 7 detail

| Item | FINAL | FINAL-ET |
|---|---|---|
| Balanced accuracy by round (2018 / 2019 / 2021) | 0.893 / 0.840 / 0.625 | 0.893 / 0.840 / 0.655 |
| HIGH recall by round | 8/8 / 11/13 / **1/4** | 8/8 / 11/13 / **2/4** |
| Precision by round | 0.73 / 0.85 / 1.00 | 0.73 / 0.85 / **0.33** |
| Severe deterioration (7c: balanced accuracy < 0.60 or recall < 0.50) | Yes (2021 recall) | No; 2021 sits **exactly** at the recall floor |
| Seeds, balanced accuracy (7b ≥ 0.70) | 0.827–0.847 | 0.804–0.824 |
| Reproduction (7a) | 45/45 stored fits identical (0.0). 110 all-lead fits re-run Leads 1–3 identically | Same fitted models (750 rows, 0.0); predictions deterministic |
| Missing groups (7e; worst change in balanced accuracy) | −0.081 (poverty) | −0.081 (poverty); climate, employment and news 0.000 |
| **Training perturbation (7g, reported only):** three 90 % training-province subsamples | Balanced accuracy 0.806–0.844; **2021 recall 0.25–0.50** | Balanced accuracy 0.815–0.874; **2021 recall 0.50–1.00** |

**The 2021 verdict hangs on one province.** The round has 4 HIGH provinces. Small training perturbations move FINAL's 2021 recall between 0.25 and 0.50, and FINAL-ET's between 0.50 and 1.00. A PASS or FAIL on 7c is therefore decided by one province and is not robust either way.

## What changed in 2021 (Lead 1 probabilities)

| Province (truth) | FINAL | FINAL-ET |
|---|---|---|
| Tawi-Tawi (HIGH) | 0.86 | 0.97 |
| Agusan del Sur (HIGH) | 0.41 | **0.67 (found)** |
| Occidental Mindoro (HIGH) | 0.21 | 0.39 (still missed, less confident) |
| Masbate (HIGH) | 0.15 | 0.37 (still missed, less confident) |
| Sarangani (LOW) | 0.44 | **0.66 (false alarm)** |
| Surigao del Norte (LOW) | 0.17 | **0.59 (false alarm)** |
| North Cotabato (LOW) | 0.21 | **0.58 (false alarm)** |
| Leyte (LOW) | 0.30 | **0.57 (false alarm)** |

- The 2021 AUROC rises from 0.857 to 0.881: the ranking is slightly better.
- But the level overshoots. With the double count removed, the model projects too *little* national improvement between the 2019 and 2021 rounds, and the 2021 Brier worsens from 0.090 to 0.129.
- The truth lies between the two treatments. **Training data cannot say where**, because no training row has a refreshed national level with an older own survey.

## Why neither candidate can pass

| | FINAL | FINAL-SA (13 Nov) | FINAL-ET |
|---|---|---|---|
| 2021 projected fall | Too large (double count) | Too small everywhere (cap also in 2018/19) | Too small in 2021 only |
| Rule 6 | Pass | Fail | Fail |
| Rule 7 | Fail | Pass | Pass |

Each legitimate fix of the long-gap mean moves calibration and stability in opposite directions. The pass or fail of each hangs on 1–2 provinces of a 4-HIGH round.

**Fixing both at once needs one of:**
- training rows that contain the stale-anchor condition (a future round surveying provinces whose own survey is older than the latest national round);
- an input that separates the 2021 high-anchor provinces that fell from those that did not. No such genuine input is identified; see the trigger audit and the 12–13 November information reports.

**Not done:**
- no further variant was scored;
- no threshold, weight or calibration change was made after seeing these results.

## Files
- `FINAL_IMPROVEMENT_PROTOCOL.md` (+ `.sha256`) and `candidate_config.json`
- Scripts: `scripts/run_et.py`, `scripts/assemble_et.py`, `scripts/stability_et.py`
- Forecasts: `parts_et/`, `parts_et_L13/`
- Evidence: `evidence/E_FINALET_*`, `evidence/R7_et_sensitivity.json`, `evidence/ET_same_model_check.json`
- `HASHES.sha256`: every protocol, script and prediction file of this study (315 files; manifest sha `9797f123`)
