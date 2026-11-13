# aiPHeed FINAL (RATE + MIND): Standalone Acceptance Report

**Date and protocol.** 2026-11-13. `PROTOCOL_SA.md` (sha `15202d27`) and `PROTOCOL_SA_PARTB.md` (sha `112ca651`). Both were locked before the model they govern was scored.

**What was scored.**
- **FINAL:** the existing forecasts, re-scored under the new rules.
- **FINAL-SA:** one pre-registered improvement candidate, scored once.

All metrics are **retrospective on the 72 reused province-rounds**, not independent validation.

**Untouched.** E196, its artifacts, the seals, the earlier reports and the original seven-rule records are unchanged. Nothing was committed or deployed. All work is in this research folder (isolated from every branch).

## Verdict

**REJECT both as reliable standalone forecasters (6 of 7 rules each). Keep FINAL for research use and prospective sealing.**

| Rule | FINAL | FINAL-SA (candidate) |
|---|---|---|
| 1 Data integrity | PASS | PASS |
| 2 Forecast validity | PASS | PASS |
| 3 Overall performance | PASS | PASS |
| 4 HIGH detection | PASS (exactly at 0.80) | PASS |
| 5 HIGH reliability | PASS | PASS (0.64, narrowly) |
| 6 Probability reliability (protocol form for n = 72) | PASS | **FAIL** |
| 6 as originally proposed (reported) | FAIL | FAIL |
| 7 Stability and reproducibility | **FAIL** | PASS |
| **Rules passed** | **6 of 7** | **6 of 7** |

**Each model fails a different rule, and the two failures are linked:**
- **FINAL** is well calibrated but unstable. It finds only 1 of the 4 HIGH provinces in the 2021 round.
- **FINAL-SA** stops FINAL from projecting change beyond the intervals it was trained on. That fixes the instability: 2021 recovers to 2 of 4, 2019 to 13 of 13, and overall HIGH recall reaches 0.92. But its probabilities then run too high on average, and the calibration test rejects them.

Under the pre-registered rule, nothing further was tuned on these rows. Even a 7 of 7 here would only have earned **CONDITIONALLY ACCEPT**: the rows are reused, and no independent provincial round exists.

---

## 1. Architecture and data flow (FINAL)

1. **Inputs.** 77 candidate inputs (four feature sets) from PSA prices and production, PSA poverty and census, NASA POWER, IBTrACS, NOAA ONI, PSA LFS and regional accounts, and DA-validated news indices. All are read as of the forecast origin. Source register: `evidence/R1_source_register.md`.
2. **Anchor.** The province's latest *released* HFIAS survey (FNRI 2013 or 2015 at the evaluated origins), on the logit scale. Three anchor variants (H, OH, RSS) are chosen per fit by inner error.
3. **RATE.** LightGBM (monotone constraints, 25 inputs selected per fit, 16-setting grid) learns the change *per quarter* since the anchor. Forecast = anchor + (gap ÷ mean training gap) × predicted rate.
4. **MIND.** Gaps in an input are filled with the training median, plus a "was missing" flag for inputs that are gappy in training.
5. **Probability.** Φ(forecast ÷ spread). The spread comes from training out-of-fold residuals and grows with the gap. Raw, linear or Platt calibration is chosen by inner Brier against the survey-uncertainty labels; "raw" was chosen in every fit. Balanced class weights. HIGH at ≥ 0.50. Five seeds averaged.
6. **Target.** HIGH means FNRI HFIAS moderate+severe prevalence ≥ 50 % in the survey round. This is a **relative-risk class**, not a prevalence forecast.

## 2. Current performance of FINAL (Lead 1 = one quarter ahead; 95 % bootstrap intervals over province-rounds)

| Measure | Value | 95 % interval |
|---|---|---|
| Balanced accuracy | 0.847 | 0.748–0.933 |
| AUROC | 0.898 | 0.813–0.963 |
| Accuracy | 0.861 | 0.778–0.931 |
| Precision (HIGH) | 0.800 | 0.630–0.952 |
| Recall (HIGH) | 0.800 (20/25) | 0.632–0.950 |
| Recall (LOW) | 0.894 | 0.800–0.977 |
| F1 | 0.800 | 0.653–0.909 |
| Confusion (TP / FP / FN / TN) | 20 / 5 / 5 / 42 | |
| Brier | 0.123 | 0.084–0.166 |
| Brier skill vs the training HIGH rate | 0.578 | 0.427–0.707 |
| ECE (10 bins) | 0.080 | 0.075–0.188 |
| Calibration in the large (mean p − observed rate) | +0.046 | −0.033 to +0.124 |
| Calibration slope | 1.25 | 0.82–2.38 |
| Calibration intercept (logit, offset) | −0.33 | −0.94 to +0.24 |
| Cox test (intercept 0, slope 1) | p = 0.41 | |

Leads 2 and 3 (reported only): balanced accuracy 0.836 / 0.806; HIGH recall 0.80 / 0.76; precision 0.77 / 0.73.

## 3. Root causes of the failed rules

**FINAL, Rule 7 (2021 HIGH recall 1 of 4): long-gap double extrapolation.** The evidence is outcome-free or training-only (`D1`–`D3`).

- **Every fold forecasts beyond the intervals it was trained on.**

  | Fold | Test gap (quarters) | Training gaps |
  |---|---|---|
  | 2018 | 12 | 8 |
  | 2019 | 16 | 8 |
  | 2021 | 24 | up to 20 |

  Live CALABARZON forecasts would need 22–34 quarters, against at most 24 in training.
- **Change is not proportional to the gap in training rows.** Per-quarter logit change was −0.011 (8 quarters), −0.035 (12), −0.016 (16) and −0.019 (20). National trends differ by period; they do not accumulate linearly.
- **At the 2021 origin, FINAL projected a −23.6-point fall for provinces starting at 60 % or more.**
  - About −12 points come from the anchor's own built-in trend shift (every anchor variant does this).
  - About −12 more come from RATE multiplying the per-quarter rate by 24 ÷ the mean training gap.
  - Training provinces with such anchors fell only −9.4 points, and 77 % stayed HIGH.
  - The trend is counted twice at the long gap. In 2018 and 2019 the two parts total only about −6 points, consistent with training.

**FINAL, Rule 6 as originally proposed: sample size, not the model.** With 72 forecasts, a *perfectly* calibrated forecaster:
- meets ECE ≤ 0.05 only 0.7 % of the time (median 0.11);
- has slope in 0.80–1.20 only 47 % of the time;
- has logit intercept within ±0.10 only 29 % of the time.

These limits become meaningful at about 600–1,000 forecasts (`P0_*.json`). Hence the protocol's consistency tests, which FINAL passes. FINAL's 0.080 ECE is within the range expected by chance (95th percentile 0.153 for its own probabilities).

**FINAL-SA, Rule 6: capping removes a bias the calibration had learned to absorb.**
- The cap raises forecasts at long gaps: mean probability exceeds the HIGH rate by 0.097, and the slope is 1.52.
- The inner calibration never sees capped extrapolations, because training rows lie within the training gaps. So it cannot correct the shift.
- Fixing this needs training rows at long gaps, which only accumulate with new survey rounds. A recalibration chosen now would be tuned on the test rows.

## 4. Data availability and quality

- **Outcomes.** All 72 outcomes and 72 anchors reproduce exactly from published FNRI files (`R1_label_trace_L1.csv`).
- **2021 standard errors.** FNRI published no provincial 2021 SEs, so the pipeline assumes 3.0 points. This affects weights and the survey-uncertainty labels only, not the HIGH class.
- **Survey noise.** Expected wrongly-classed labels from survey noise: **3.6 of 72** (Lead 1). Accuracy above about 95 % is not measurable. 38 of 72 anchors are within 1.96 SE of the 50 % line.
- **Dashboard groups versus model inputs:**
  - **OFW remittances:** no input among FINAL's 77.
  - **Employment:** national or regional only, with one value for every province in the 2018 and 2019 training rows.
  - **Climate and employment:** removing either group changes **no forecast** (0 class flips; probability change ≤ 0.001). They do not inform FINAL's predictions.
  - The forecasts rest on poverty and social vulnerability (13 flips when removed), then agriculture and fish production, then market (`R7e_*`).
- **Inputs carrying nothing.** `ag_dev3y` and `ag_pc` are entirely missing in the 2018 and 2019 training rows; `unemp_region` in all of them.
- **MIND.** Mean missing share is 9.3 % in training and 7.4 % in test rows. No input is missing in test rows but never in training, so MIND's handling is appropriate.
- **Class weights** (12 November evidence, not rerun). Balanced weights count a LOW row about 2.25 times a HIGH row in the 2018 and 2019 folds. Training rows never select balanced weights there. Removing them raised recall but broke calibration, so no change was made.
- **Displacement (Marawi) data:** not compiled, and **not added**. It was identified from test provinces.
- **Five-group mismatch.** Your brief lists the five groups as market, climate, employment, OFW remittances and poverty and social vulnerability. The served dashboard shows Fish Production as the fifth, and the thesis names fish kill. I changed nothing; this needs your decision.

## 5. Improvement implemented: FINAL-SA (pre-registered, `PROTOCOL_SA_PARTB.md`)

1. **No time extrapolation beyond training support.**
   - The RATE multiplier is capped at the longest training gap of each fit.
   - The predictive spread still grows with the true gap, so uncertainty is not understated.
   - Justification: training data show change is not proportional to the gap, and FINAL's long-gap projections double-count the trend.
2. **Decision threshold chosen on training rows only.**
   - The engine's existing balanced-accuracy threshold on inner out-of-fold probabilities (0.424 in the 2018 and 2019 folds, 0.454 in 2021).
   - Probabilities are unchanged. This handles class imbalance without distorting probabilities.

Not done, on purpose:
- class-weight or recalibration changes chosen on these rows;
- province-specific corrections;
- displacement or new features;
- any second candidate.

## 6. Evaluation method and leakage safeguards

- Thresholds were assessed and locked before scoring. One adjustment (Rule 6) is justified by simulation with no model output. Both forms are reported.
- Rule 2 checks pass on every row:
  - target quarter = origin + lead = the survey quarter;
  - anchor released (reference quarter + 6) on or before the origin;
  - every training outcome released on or before the fold origin;
  - RATE and MIND use no outcome (code check and existing test).
- The pipeline's as-of, leakage and reproduction tests were re-run: **26 passed** (`test_e151`, `test_e152`, `test_e175_target_scaling`, `test_hcw_engine`, `test_hcw_final_engine`).
- The candidate's definition used training-only or outcome-free evidence.
- The candidate was scored once. Its two components are reported as ineligible diagnostics. Nothing was selected after scoring.

**Evidence classes.**

| Class | What it covers |
|---|---|
| Locked earlier results | Unchanged |
| This study | Retrospective on reused rows |
| Independent | None exists |

## 7. Final metrics with intervals (Lead 1)

| Measure | FINAL | FINAL-SA |
|---|---|---|
| Balanced accuracy | 0.847 [0.75, 0.93] | 0.822 [0.73, 0.90] |
| AUROC | 0.898 [0.81, 0.96] | 0.908 [0.82, 0.97] |
| Accuracy | 0.861 | 0.792 |
| Precision | 0.80 [0.63, 0.95] | 0.64 [0.47, 0.80] |
| HIGH recall | 0.80 [0.63, 0.95] | 0.92 [0.79, 1.00] |
| F1 | 0.80 | 0.75 |
| TP / FP / FN / TN | 20 / 5 / 5 / 42 | 23 / 13 / 2 / 34 |
| Brier (skill) | 0.123 (0.58) | 0.132 (0.55) |

Ineligible diagnostics:
- **Cap only (0.50 cut-off):** balanced accuracy 0.834, recall 0.88, precision 0.69, 2021 recall still 1 of 4.
- **Threshold only:** recall 0.80, precision 0.69 (2018 false alarms rise from 3 to 6; 2021 recall still 1 of 4).

Each change alone fails Rule 7. The pre-registered combination passes Rule 7 but fails Rule 6.

## 8. HIGH-risk detection

| | FINAL | FINAL-SA |
|---|---|---|
| Lead 1 / 2 / 3 found (of 25) | 20 / 20 / 19 | 23 / 22 / 23 |
| 2018 (8 HIGH) | 8 | 8 |
| 2019 (13 HIGH) | 11 | 13 |
| 2021 (4 HIGH) | **1** | 2 |
| Missed at Lead 1 | Lanao del Norte 0.32, Misamis Oriental 0.38 (2019); Masbate 0.15, Occidental Mindoro 0.21, Agusan del Sur 0.41 (2021) | Masbate 0.19, Occidental Mindoro 0.25 (2021) |
| False alarms at Lead 1 | 5: Camarines Norte, Iloilo, Sorsogon (2018); Quirino, Southern Leyte (2019) | 13 (adds Cagayan, Camiguin, Isabela, Oriental Mindoro, Ilocos Norte, Misamis Occidental, Pangasinan, Sarangani) |

**Leave one round out, FINAL.** HIGH recall drops to 0.71 without 2018 and to 0.75 without 2019. Its recall depends on the 2018 round, where all 8 HIGH provinces are found.

**What wrong HIGH calls mean.** FINAL-SA's 13 false alarms out of 36 HIGH calls would send DA attention to provinces that were not HIGH: one in three alerts. FINAL's misses would leave Masbate and Occidental Mindoro (both above 56 %) unflagged.

## 9. Probability calibration

| Measure | FINAL | FINAL-SA |
|---|---|---|
| ECE (95th percentile under perfect calibration) | 0.080 (0.153) | 0.142 (0.162) |
| Mean p − observed rate | +0.046 | +0.097 |
| Calibration slope | 1.25 | 1.52 |
| Logit intercept | −0.33 | −0.63 |
| Cox p | **0.41** | **0.036** |

- Reliability diagrams: `E_FINAL_reliability_L1.png`, `E_FINALSA_thr_reliability_L1.png`.
- FINAL's mid-range bins (about 0.45 and 0.63) deviate most. They hold few rows each.
- Confident wrong calls (|p − 0.5| ≥ 0.2), FINAL: Masbate 0.15, Occidental Mindoro 0.21, Quirino 0.84, Sorsogon 0.79.

## 10. Stability and reproducibility

| Check | FINAL | FINAL-SA |
|---|---|---|
| 7a Reproduction | All 45 stored fits re-run identically (max difference 0.0); sealed forecast file sha `4ad9267f` unchanged | Deterministic (difference 1e-16) |
| 7b Worst seed balanced accuracy | 0.827 | 0.790 |
| 7c Rounds (balanced accuracy ≥ 0.60 and recall ≥ 0.50) | **2021 recall 0.25: severe** | 0.75 / 0.79 / 0.73; recall 1.0 / 1.0 / 0.50: pass |
| 7e Group missing (largest change in balanced accuracy) | −0.081 (poverty): pass | −0.032 (poverty): pass |
| 7f Operational gap | Live gaps 22–34 > 24 trained: extrapolates | Mean change capped at the training gap; spread still grows |

## 11. Seven-rule PASS/FAIL with evidence

| Rule | FINAL | FINAL-SA | Evidence |
|---|---|---|---|
| 1 | PASS | PASS | `R1_R2_integrity.json`: 10 of 10 checks; labels trace 72/72; no synthetic data; no duplicates; missing-data rates; source register |
| 2 | PASS | PASS | Same file: alignment, release dates and RATE/MIND code checks on every row; 26 pipeline tests pass |
| 3 | PASS (0.847 / 0.898) | PASS (0.822 / 0.908) | `E_*_summary.json` |
| 4 | PASS (0.80 = threshold) | PASS (0.92) | Same |
| 5 | PASS (0.80) | PASS (0.64) | Same |
| 6 | PASS (6a–6d) | FAIL (Cox p = 0.036; 6b +0.097 is within the limit but marginal) | Same; `P0_*.json` |
| 7 | FAIL (7c: 2021 recall 0.25) | PASS (7a–7e) | `R7a_*`, `R7e_*`, `E_*_summary.json` |

## 12. Remaining limitations and what independent validation needs

**Limitations**
- **No independent data.** Every number here comes from 72 reused province-rounds, with 25 HIGH. The interval on HIGH recall is about ±0.15. There is no independent provincial HFIAS round on hand: ENNS 2022 is not obtainable, and the 2023 NNS used FIES.
- **Inputs.**
  - Climate and employment do not move FINAL's forecasts.
  - Remittances are absent.
  - Employment has no provincial variation.
  - The cause of the 2021 Masbate and Occidental Mindoro misses is not established.
- **Operational use.** The live gaps (22–34 quarters) exceed every training gap. Long-gap forecasts are the least supported.

**Exact requirements for independent validation**
1. **An unseen provincial HFIAS round with forecasts sealed beforehand.** FINAL and the other candidates are already sealed (`4ad9267f`). FINAL-SA can be sealed the same way on your approval.
   - At least 25 provinces including about 10 HIGH. With 10 HIGH, one miss moves recall by 0.10.
   - The lower 95 % bound of balanced accuracy must be ≥ 0.60.
2. **The original Rule 6 limits** (ECE ≤ 0.05, slope 0.80–1.20) need about **600–1,000** province-forecasts.
3. **Instrument decision.** If FNRI fields no further provincial HFIAS rounds, these rules cannot be re-tested. A FIES bridge would then be needed (your decision).
4. **Input gaps to close before the next round** (prospective, with your approval):
   - a provincial employment series;
   - a remittance input;
   - checking why the climate inputs carry no weight;
   - compiled displacement data.

## 13. Recommendation

**REJECT** FINAL and FINAL-SA as reliable standalone forecasters for deployment.

| Model | Rules passed | Strength | Failure |
|---|---|---|---|
| FINAL | 6 of 7 | Reliable probabilities | Misses 3 of 4 HIGH provinces after a 24-quarter interval |
| FINAL-SA | 6 of 7 | Detects HIGH provinces consistently (0.92), stable across rounds | Systematically overstates risk and raises a false alarm in one of three HIGH calls |

Both are reproducible, leak-free and genuine-data only. Keep FINAL as the research model with its sealed forecasts. Seal FINAL-SA prospectively if you approve, and decide between them on the next independent round. E196 remains production.

## Files (all new, in `research_notes/aiPHeed_final_standalone_20261113/`)

- `PROTOCOL_SA.md`, `PROTOCOL_SA.sha256`, `PROTOCOL_SA_PARTB.md`, `PROTOCOL_SA_PARTB.sha256`
- `scripts/`: `calib.py`, `ece_null.py`, `ece_null2.py`, `evaluate.py`, `integrity.py`, `diag_rate.py`, `diag_pred.py`, `diag_anchor.py`, `rerun_final.py`, `run_sa.py`, `stability.py`, `stability_sa.py`
- `parts_rerun/` (45 FINAL fits plus perturbations), `parts_sa/` (45 FINAL-SA fits)
- `evidence/`: `P0_*`, `R1_*`, `R7a_*`, `R7e_*`, `D1_*`–`D3_*`, `E_FINAL*`, `E_FINALSA*`, `E_FINALR_thr*`, reliability PNGs, run logs
