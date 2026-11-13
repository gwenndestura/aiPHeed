# aiPHeed H_cw: Final Optimisation Report

Date: 2026-11-12. Protocol: `PROTOCOL_FINAL.md`, locked before any arm was run (hash in `PROTOCOL_FINAL.sha256`). All numbers come from `evidence/`. Earlier work this report builds on: studies I and II (46 configurations), the E196 combination test, and `HCW_IMPROVEMENT_REPORT.md`.

## Summary

- **A real, structural weakness was found and tested: H_cw learns change over one interval length and forecasts over a longer one.** In two of the three forecast folds every training row spans 8 quarters between surveys and every test row spans 12 or 16. Teaching LightGBM the change *per quarter* fixes this.
- **On the survey round that had never been used for testing (78 provinces), the fix is large and clear:** accuracy 66.7 → 74.4 % (6 provinces better, none worse), Brier score 0.161 → 0.119, interval entirely below zero.
- **On the forward one-quarter-ahead test the candidate reaches 86.1 %** (H_cw: 81.9 %), with calibration error halved and false alarms halved (10 → 5).
- **It does not pass the locked acceptance rules.** It finds fewer HIGH provinces (20 of 25 instead of 22), and its Brier score against the survey probability is not distinguishable from H_cw's. So it is **not validated as a replacement**. It is a different error trade-off: fewer false alarms, more missed HIGH provinces.
- **85 % is reached as a point estimate, not as a validated result.** The 95 % interval of 86.1 % on 72 provinces is 77.8–94.4 %.
- Nothing was changed in production (E196), the dashboard, or the H_cw branch. The candidates' forecasts for the next survey round are sealed so that round can decide.

---

## A. Existing model diagnosis

**Current performance (H_cw, leak-free, 5-seed mean, 72 province-rounds per lead, rolling origin).**

| Lead | Accuracy | Precision | Recall HIGH | Recall LOW | F1 | Balanced acc. | ROC-AUC | Brier | Calibration slope | TP / FP / FN / TN |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 81.9 % [72.2, 90.3] | 0.69 | 0.88 | 0.79 | 0.77 | 83.4 | 0.911 | 0.135 | 1.78 | 22 / 10 / 3 / 37 |
| 2 | 83.3 % | 0.72 | 0.84 | 0.83 | 0.78 | 83.5 | 0.906 | 0.135 | 1.60 | 21 / 8 / 4 / 39 |
| 3 | 80.6 % | 0.69 | 0.80 | 0.81 | 0.74 | 80.4 | 0.903 | 0.132 | 1.54 | 20 / 9 / 5 / 38 |

The new engine reproduces these exactly (maximum probability difference 0.0 over 1,080 rows). The H_cw engine test on the branch passes (3 of 3).

**Where the 13 Lead 1 errors come from.**

| Diagnostic | Result | Meaning |
|---|---|---|
| Model fitted inside each test round (knows that round's level; leave-one-province-out) | 59 of 72 correct, same as H_cw | With the current inputs, better learning has little room |
| Latest survey value alone, with the round's level known | 53 of 72 | The inputs add about 6 provinces over the survey value |
| Does H_cw predict provincial change? | Yes: correlation of predicted with actual change 0.68, 0.54, 0.62 by round | Skill is real, not only persistence |
| Size of predicted change, 2018 fold | −0.19 logit predicted, −0.42 actual | Change is under-predicted |
| Size of predicted change, 2019 fold | −0.12 predicted, −0.25 actual | Change is under-predicted |
| Survey sampling error | 11 of 13 errors are certain on the other side of 50 % | The errors are not survey noise |
| Missing inputs | Provincial retail prices missing for 17–45 % of provinces | Default handling gives "missing" its own branch |

**Solvable and not solvable.**

- *Solvable (addressed in this study):* the interval mismatch. In the 2018 and 2019 folds the model trains on the 2013 → 2015 transition (8 quarters) and forecasts 2015 → 2018 or 2019 (12 or 16 quarters). A tree cannot extrapolate along an input that never varies in training, so it predicts an 8-quarter change for a 12–16-quarter interval.
- *Not solvable with data on hand:* how each region changed since its last survey. Regional income growth since the anchor is zero for every 2015 training row under the release rules, so the model cannot learn it in those folds. Annual provincial child-nutrition records (OPT Plus) were tested on 11-04 and their change does not track food-insecurity change (correlation 0.03).
- *Fixed limits:* four survey rounds; all in the third quarter; CALABARZON has 5 forward test rows, all LOW.

---

## B. Research and optimisation strategy

Each candidate answers one diagnosed weakness. Nothing from the 46 earlier configurations was repeated.

| Axis | Candidate | What it does | Why |
|---|---|---|---|
| Target | **RATE** | LightGBM learns change per quarter since the anchor survey; forecast = anchor + interval × rate | Makes rows with different interval lengths comparable; removes the extrapolation a tree cannot do (März & Rasul 2024; Shi et al. 2019 on piecewise-constant trees) |
| Target | RATE_SQRT | Same, scaling with the square root of the interval | Diffusion-type alternative |
| Missing values | IMPUTE | training-median fill | Study I candidate, reassessed |
| Missing values | RIMP | fill from the region's published price series, then regional mean | Domain alternative |
| Missing values | **MIND** | median fill plus a "was missing" flag per input | Missing-indicator method (Van Ness et al. 2022; Sisk et al. 2022) |
| Missing values | DROPGAP | drop inputs missing in over 15 % of rows | Simplest alternative |
| New information | COMP | anchor survey's mild and severe shares and two dispersion measures | The only unused genuine survey information on disk |

**Rejected before running, with reason.** Synthetic rows (four studies, all worse or neutral). E196 combination (0.97 correlated, already failed). WATCH band (failed on the held-out round). Direct HIGH/LOW classification objective (dichotomising a measured prevalence discards information). Spatial smoothing of the anchor (anchor sampling error is about 3 points against a between-province spread several times larger). More hyper-parameter search (a 40-setting search returned to the same small trees).

**Validation design, built to avoid choosing on the forward test.**

1. *Held-out round, for choosing.* FNRI 2015 as test, trained on 2018, 2019 and 2021. This is leave-one-round-out, **not a forecast**: training outcomes are later than test outcomes. For RATE it is a mirror test (training intervals 12–24 quarters, test interval 8).
2. *Forward folds, for confirming.* The single composed candidate is confirmed on the chronological folds against seven fixed rules.

The interval mismatch was noticed from forward-fold summaries, so the forward test is not an untouched test of that idea. The held-out round is.

---

## C. Experimental results

### C1. Stage 1: held-out round (78 provinces; not forecast accuracy)

| Arm | Lead 1 accuracy | Recall HIGH | Recall LOW | ROC-AUC | Brier vs survey probability, Leads 1–2 | Difference vs H_cw [95 % CI] | Provinces better / worse |
|---|---|---|---|---|---|---|---|
| H_cw | 66.7 % | 0.65 | 0.71 | 0.793 | 0.161 | | |
| **RATE** | **74.4 %** | 0.76 | 0.71 | 0.796 | 0.126 | −0.035 [−0.053, −0.019] | 6 / 0 |
| RATE_SQRT | 69.2 % | 0.69 | 0.71 | 0.793 | 0.141 | −0.020 [−0.030, −0.011] | 2 / 0 |
| IMPUTE | 66.7 % | 0.65 | 0.71 | 0.806 | 0.157 | −0.005 [−0.010, +0.000] | 0 / 0 |
| RIMP | 66.7 % | 0.65 | 0.71 | 0.802 | 0.160 | −0.001 [−0.006, +0.003] | 0 / 0 |
| **MIND** | 66.7 % | 0.65 | 0.71 | 0.797 | 0.149 | −0.012 [−0.018, −0.008] | 0 / 0 |
| DROPGAP | 66.7 % | 0.65 | 0.71 | 0.793 | 0.163 | +0.002 [−0.000, +0.005] | 0 / 0 |
| COMP | 66.7 % | 0.65 | 0.71 | 0.781 | 0.187 | +0.026 [+0.015, +0.039] | 1 / 1 |

RATE removes most of the level error on this round (mean error −0.19 → −0.05 logit). Latest-survey persistence scores 74.4 % here; RATE matches it on accuracy and beats it on ranking (AUC 0.80 vs 0.70) and Brier.

By the locked rule: target axis → RATE; missing-value axis → MIND; new-information axis → none (COMP is clearly worse). **FINAL = RATE + MIND.** On the held-out round FINAL scores 74.4 %, Brier 0.119, difference −0.042 [−0.061, −0.025].

A prediction of mine was wrong and is recorded: I expected MIND to lose IMPUTE's gain. It did better than IMPUTE on this round.

### C2. Stage 3: forward chronological folds (the forecasting evidence)

Lead 1, 72 province-rounds. Only FINAL is eligible; the single arms are shown for transparency.

| Configuration | Acc. L1 / L2 / L3 % | Precision | Recall HIGH | Recall LOW | F1 | Bal. acc. | ROC-AUC | Brier | Cal. slope | ECE | TP / FP / FN / TN | Worst seed |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Persistence | 62.5 / 62.5 / 62.5 | 0.48 | 0.96 | 0.45 | 0.64 | 70.3 | 0.827 | 0.253 | 1.09 | 0.296 | 24 / 26 / 1 / 21 | |
| E158 | 73.6 / 73.6 / 75.0 | 0.58 | 0.84 | 0.68 | 0.69 | 76.0 | 0.860 | 0.161 | 1.53 | 0.163 | 21 / 15 / 4 / 32 | |
| **H_cw** | **81.9 / 83.3 / 80.6** | 0.69 | 0.88 | 0.79 | 0.77 | 83.4 | 0.911 | 0.135 | 1.78 | 0.135 | 22 / 10 / 3 / 37 | 81.9 |
| **FINAL (RATE + MIND)** | **86.1 / 84.7 / 81.9** | 0.80 | 0.80 | 0.89 | 0.80 | 84.7 | 0.898 | 0.123 | 1.25 | 0.072 | 20 / 5 / 5 / 42 | 84.8 |
| RATE | 83.3 / 86.1 / 84.7 | 0.76 | 0.76 | 0.87 | 0.76 | 81.6 | 0.900 | 0.125 | 1.36 | 0.069 | 19 / 6 / 6 / 41 | 81.8 |
| RATE_SQRT | 83.3 / 83.3 / 83.3 | 0.74 | 0.80 | 0.85 | 0.77 | 82.6 | 0.905 | 0.128 | 1.56 | 0.109 | 20 / 7 / 5 / 40 | 83.1 |
| IMPUTE | 86.1 / 87.5 / 83.3 | 0.76 | 0.88 | 0.85 | 0.81 | 86.6 | 0.915 | 0.130 | 1.87 | 0.129 | 22 / 7 / 3 / 40 | 83.3 |
| MIND | 80.6 / 81.9 / 84.7 | 0.66 | 0.92 | 0.74 | 0.77 | 83.2 | 0.910 | 0.139 | 1.72 | 0.133 | 23 / 12 / 2 / 35 | 80.2 |
| RIMP | 79.2 / 80.6 / 80.6 | 0.64 | 0.92 | 0.72 | 0.75 | 82.2 | 0.923 | 0.143 | 1.93 | 0.171 | 23 / 13 / 2 / 34 | 78.9 |
| DROPGAP | 81.9 / 81.9 / 83.3 | 0.69 | 0.88 | 0.79 | 0.77 | 83.4 | 0.917 | 0.135 | 1.90 | 0.139 | 22 / 10 / 3 / 37 | 81.9 |
| COMP | 83.3 / 84.7 / 80.6 | 0.71 | 0.88 | 0.81 | 0.79 | 84.4 | 0.913 | 0.136 | 1.77 | 0.129 | 22 / 9 / 3 / 38 | 81.9 |

**FINAL against the locked rules.**

| Rule | Result |
|---|---|
| 1. Mean fold accuracy not more than 1.4 points lower at any lead | Pass |
| 2. Brier (vs survey probability) lower at ≥ 2 of 3 leads | Pass (Leads 1 and 2; worse at Lead 3) |
| 3. Pooled Brier difference, interval below 0 | **Fail**: −0.0006 [−0.0155, +0.0156] |
| 4. Recalls not more than 0.04 lower | **Fail** at Lead 1: HIGH recall 0.88 → 0.80. At the limit at Lead 2 (0.84 → 0.80) and Lead 3 (0.80 → 0.76) |
| 5. Worst seed | Pass (84.8 vs 81.9) |
| 6. Balanced accuracy at Lead 1 | Pass (84.7 vs 83.4) |
| 7. No round more than one province worse | Pass |

Provinces changed at Lead 1: 5 better, 2 worse (Lead 2: 3 / 2; Lead 3: 3 / 2).

**By test round, Lead 1.**

| Round | H_cw accuracy | FINAL accuracy | H_cw FP / FN | FINAL FP / FN | H_cw mean error (logit) | FINAL mean error |
|---|---|---|---|---|---|---|
| ENNS 2018 (22) | 81.8 % | 86.4 % | 4 / 0 | 3 / 0 | +0.22 | +0.20 |
| ENNS 2019 (25) | 80.0 % | 84.0 % | 5 / 0 | 2 / 2 | +0.14 | +0.01 |
| ENNS 2021 (25) | 84.0 % | 88.0 % | 1 / 3 | 0 / 3 | −0.09 | −0.26 |

**By island group, Lead 1.** Luzon 77.1 → 85.7 %; Visayas 86.7 → 86.7 %; Mindanao 86.4 → 86.4 % (2 false alarms removed, 2 HIGH provinces lost).

**Provinces that changed class at Lead 1.**

- Corrected (were false alarms): Oriental Mindoro, Ilocos Norte, Pangasinan, Misamis Occidental, Sarangani.
- Broken (were correct HIGH calls): Lanao del Norte and Misamis Oriental, both Northern Mindanao 2019. H_cw had them at 0.52 and 0.53; doubling the predicted decline for the 16-quarter interval pushed them to 0.32 and 0.38.
- Still wrong in both: Sorsogon, Camarines Norte, Iloilo, Quirino, Southern Leyte (false alarms); Masbate, Occidental Mindoro, Agusan del Sur (missed HIGH, 2021).

**CALABARZON (all five test rows are LOW; every configuration calls them LOW).**

| Province (round) | H_cw | FINAL |
|---|---|---|
| Quezon (2019) | 0.27 | 0.11 |
| Rizal (2019) | 0.13 | 0.04 |
| Laguna (2018) | 0.05 | 0.02 |
| Cavite (2021) | 0.04 | 0.01 |
| Batangas (2021) | 0.03 | 0.01 |

The provincial order is kept (Quezon highest). Skill inside the region cannot be measured with five LOW rows.

### C3. What the two sets say together

| | Held-out round | Forward folds |
|---|---|---|
| Accuracy (Lead 1) | +7.7 points, 6 better / 0 worse | +4.2 points, 5 better / 2 worse |
| Brier vs survey probability | −0.042, clear | −0.0006, not distinguishable |
| Brier vs outcome | 0.241 → 0.190 | 0.135 → 0.123 |
| Calibration slope (1 is ideal) | not computed | 1.78 → 1.25 |
| HIGH recall | 0.65 → 0.76 | 0.88 → 0.80 |
| Level error | −0.19 → −0.04 | 2018 and 2019 improved; 2021 worse (−0.09 → −0.26) |

The per-quarter formulation corrects the level where the forecast interval is 8–16 quarters. At 24 quarters (the 2021 fold) a straight-line scaling overshoots: change over six years is not three times the change over two. That is where the two lost HIGH calls and the Lead 3 Brier loss come from.

---

## D. Real and synthetic data assessment

**Selected integration: genuine observations only; synthetic share 0 %.**

Evidence, from five experiments on this model family:

| Study | Synthetic use | Result against genuine-only H_cw |
|---|---|---|
| 11-09 to 11-11 (three studies) | 1:1 and 50:50 augmentation | Worse; accuracy 4–12 points lower |
| Study I (11-12) | SMOTE, Borderline-SMOTE, ADASYN, geography-restricted, sampling-error bootstrap, copula, CTGAN at 10–100 % | All 19 worse on Brier; none realistic |
| Study II (11-12) | Down-weighted rows; synthetic pretraining then genuine fine-tuning | Harm removed, no gain |
| Combination (11-12) | H_cw averaged with E196, which is trained with 20 synthetic draws per fit | Between the two members; no gain |

Why it cannot help here: a generator can only re-express the survey rounds it was fitted on. The model's errors are about how provinces changed *after* those rounds. This study's result fits that picture: the one change with a large independent effect is about how genuine rows are *used* (per-quarter change), not about adding rows.

For generalisation and reliability, the genuine-only choice keeps seed stability (1 province changes class across seeds for FINAL at Lead 1; 10–20 with synthetic rows in study I).

---

## E. Final optimised model

**No configuration is validated as a replacement for H_cw.** The strongest experimentally supported candidate is described so it can be judged, and it is sealed for a prospective test.

**Candidate: H_cw-R (FINAL = RATE + MIND).**

| Element | Setting |
|---|---|
| Algorithm | LightGBM regression, as H_cw |
| Target | (logit prevalence − anchor) ÷ g, with g = quarters since the anchor survey ÷ mean training value; row weight × g²; forecast = anchor + g × predicted rate |
| Missing values | training-median fill plus one 0/1 "was missing" input per input that has gaps |
| Unchanged | inputs, 25-input selection per fold, correlation pruning, monotone constraints, three anchors, four input sets, 16-setting grid, survey-precision × balanced class weights, raw-first calibration, threshold 0.5, five seeds, no synthetic rows |

| Lead 1 | H_cw | H_cw-R |
|---|---|---|
| Accuracy | 81.9 % [72.2, 90.3] | 86.1 % [77.8, 94.4] |
| Precision / Recall HIGH / Recall LOW | 0.69 / 0.88 / 0.79 | 0.80 / 0.80 / 0.89 |
| F1 / Balanced accuracy | 0.77 / 83.4 | 0.80 / 84.7 |
| ROC-AUC | 0.911 | 0.898 |
| Brier / calibration slope / ECE | 0.135 / 1.78 / 0.135 | 0.123 / 1.25 / 0.072 |
| False alarms / missed HIGH | 10 / 3 | 5 / 5 |
| Held-out round accuracy (not a forecast) | 66.7 % | 74.4 % |

**Strengths.** Better calibrated; half the false alarms; higher accuracy at all three leads; level error removed on the held-out round; stable across seeds; chosen on rows other than the forward test.

**Weaknesses.** Misses two more HIGH provinces of 25; slightly worse ranking (AUC); worse at Lead 3 on the Brier score; over-projects decline when the interval since the last survey is long (24 quarters).

**Median imputation (IMPUTE)** remains the other candidate: 86.1 / 87.5 / 83.3 % forward with no loss of HIGH recall, but that forward figure was the best of 37 in study I, and on the held-out round it changes Brier only slightly (−0.005, interval touching zero) and no province.

**For an early-warning system, a missed HIGH province costs more than a false alarm.** On that criterion H_cw (22 of 25 found) and IMPUTE (22 of 25) are safer than H_cw-R (20 of 25). This is why rule 4 exists and why it decides against adoption.

---

## F. Deployment readiness

| Item | Status |
|---|---|
| Validation | H_cw-R: held-out round passed clearly; forward confirmation **failed** rules 3 and 4. Not validated. |
| Reproducibility | Protocol hash `263a9dd7…`; scripts `engine_final.py`, `run_final.py`, `stage1_select.py`, `eval_fwd.py`; 80 + 10 held-out jobs and 405 forward jobs, 0 failed; BASE reproduces H_cw exactly |
| Tests | `tests/unit/test_hcw_engine.py` on the H_cw branch: 3 passed. No project file was modified by this study |
| Project implementation | **Not done, by the protocol's own safeguard**: the candidate did not pass, so nothing was added to `app/hcw` or to serving. The candidate engine lives in the study folder |
| Production | E196 unchanged. Dashboard unchanged. H_cw branch unchanged |
| Prospective test | Forecasts of H_cw, IMPUTE, RATE and H_cw-R for the next survey round are sealed (see section H) |

**Recommendation: do not integrate.** Keep E196 in production and H_cw as the documented research model. Decide between H_cw, IMPUTE and H_cw-R when the next provincial survey round is scored against the seals.

---

## G. Honest achievement assessment

- **How close to 85 %?** The candidate scores 86.1 % at Lead 1 and 84.7 % at Lead 2 on the forward test. The interval on 72 provinces is 77.8–94.4 %, so "about 85 %" is consistent with the data and so is 78 %.
- **Is it supported by independent evidence?** Partly. The idea behind it is strongly supported on the held-out round (6 provinces better, none worse; interval clear). The forward accuracy gain is 5 better and 2 worse, which on its own is not statistically distinguishable from no change, and the gain in probability score against the survey is nil.
- **Is it reliable enough to replace H_cw?** No. It trades missed HIGH provinces for fewer false alarms, and it fails the two rules that guard against that.
- **Is H_cw itself reliable for practical forecasting?** As a screening and ranking tool with stated limits: yes at Leads 1–3 retrospectively (81.9 %, selection-adjusted 77.8 %). The held-out round is a caution: trained on later rounds, H_cw scored 66.7 % there, below persistence, because of the same level problem.
- **What prevents further improvement?**
  1. Four survey rounds, with disjoint provinces in the last three. Every forecast is anchored on 2015.
  2. No input observes how a region changed since its last survey.
  3. Change does not scale simply with elapsed time; with only four rounds the shape of that scaling cannot be estimated.
  4. All outcomes are third-quarter values; CALABARZON has five test rows.
- **What would improve it:** one more provincial HFIAS round. It would add a transition with a new interval length, let the scaling be learned instead of assumed, and score the sealed forecasts.

Not pursued after seeing the forward results, on purpose: RATE with median imputation instead of indicators, or a damped scaling for long intervals. Both are reasonable next candidates. Choosing them now would be choosing on the forward test rows; they belong in the next pre-registered round.

---

## References

Opened or found by search on 2026-11-12:

- März, A., Rasul, K. (2024). Forecasting with Hyper-Trees. arXiv:2405.07836. (Piecewise-constant trees do not forecast beyond the training range; cites Shi et al. 2019 on piecewise-linear trees.)
- Van Ness, M., Bosschieter, T., Halpin-Gregorio, R., Udell, M. (2022). The Missing Indicator Method: From Low to High Dimensions. arXiv:2211.09259.
- Sisk, R., Sperrin, M., Peek, N., van Smeden, M., Martin, G.P. (2022). Imputation and missing indicators for handling missing data in the development and implementation of clinical prediction models. arXiv:2206.12295.
- LightGBM documentation, Advanced Topics: Missing Value Handle. https://lightgbm.readthedocs.io/en/stable/Advanced-Topics.html
- LightGBM documentation, `LGBMModel.fit`. https://lightgbm.readthedocs.io/en/stable/pythonapi/lightgbm.LGBMModel.html

Data sources (already in the repository, no download in this study): DOST-FNRI 8th NNS 2013 Facts and Figures (Appendix 33), FNRI 2015 Updating Survey food-security appendices, ENNS 2018 / 2019 / 2021 provincial results; PSA prices, regional accounts, poverty statistics and crop production; NASA POWER rainfall; IBTrACS. Remaining references on class imbalance, synthetic data and validation are in study I, section E.

## Files

- `PROTOCOL_FINAL.md`, `PROTOCOL_FINAL.sha256`
- `scripts/`: `engine_final.py`, `run_final.py`, `stage1_select.py`, `eval_fwd.py`, `seal_candidates_enns2022.py`
- `parts_rev/` (90 jobs), `parts_fwd/` (405 jobs)
- `evidence/`: `stage1_metrics.csv`, `stage1_paired.csv`, `final_config.json`, `fwd_metrics_by_lead.csv`, `fwd_metrics_by_round.csv`, `fwd_metrics_by_island.csv`, `fwd_calabarzon_rows.csv`, `fwd_rows_L1.csv`, `fwd_decision_table.csv`, `fwd_decision.json`, run logs

---

## H. Sealed forecasts for the next survey round

File: `evidence/sealed_enns2022_candidates.json`, sha256 `4ad9267fdc8256bbc8fb2eaff85a4e63b0fa299744e18176ff9765741c494c3a`. Built with `scripts/seal_candidates_enns2022.py`, the same construction as the existing H_cw seal, before any ENNS 2022 provincial outcome is available on this machine. 78 provinces × Leads 1–2 for each of four configurations; 40 jobs, 0 failed.

| Configuration | HIGH / LOW at Lead 1 | HIGH / LOW at Lead 2 |
|---|---|---|
| H_cw (leak-free) | 15 / 63 | 7 / 71 |
| IMPUTE | 16 / 62 | 9 / 69 |
| RATE | 15 / 63 | 11 / 67 |
| H_cw-R (RATE + MIND) | 10 / 68 | 7 / 71 |

CALABARZON, probability of HIGH at Lead 1: all five provinces are LOW in every configuration (H_cw: Quezon 0.06, Rizal 0.05, Batangas 0.05, Cavite 0.02, Laguna 0.02; H_cw-R: Quezon 0.04, Rizal 0.04, the others 0.01 or below).

Two things to know when these are scored:

- **The H_cw row in this file is not identical to the earlier H_cw seal** (`43662c65…`, sealed 2026-11-11 06:08 UTC). Class agreement is 95.5 % (149 of 156 rows), largest probability difference 0.05. The earlier seal predates the as-of price-centring fix; this one uses the corrected inputs. Both stay on record; neither is to be altered.
- **The seal is itself an extrapolation for the per-quarter candidates.** Training intervals are 8–20 quarters; the sealed targets are 12, 16 and 28 quarters from their anchor. The 28-quarter rows are where straight-line scaling is least trustworthy (section C3).
