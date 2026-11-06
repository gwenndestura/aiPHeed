# E164 report: nested automatic model selection (AUTO)

- **Protocol:** `PROTOCOL.md` (6a04027e), with gates fixed before results.
- **Code:** `backend/app/e164/auto.py` (`eval`, `live`).
- **Outputs:** `backend/data/e164/out/`.
- **Seal:** `cbfb61dc`.
- **Registry:** `docs/EXPERIMENT_REGISTRY.md`.

## Result
**AUTO passes all eight acceptance gates (A1–A8) and becomes the release candidate. E158 remains the production thesis model until AUTO's sealed forecast is scored.** Nothing is deployed.

AUTO is a procedure, not a hand-picked model. At each forecast issue date it chooses the anchor, learner, features and calibration using only the training rows available then (region-grouped inner folds). The numbers below are therefore **the performance of the whole selection procedure.**

### What AUTO chose (inner validation only)
| Outer round | Lead 1 | Leads 3–4 |
|---|---|---|
| 2018, 2019 (training: 2015 only) | own history (OH) + ElasticNet + official inputs | same |
| 2021 (training: 2015, 2018, 2019) | RSS + ElasticNet + all inputs | RSS + RandomForest + all inputs |
| **Live 2027-Q1** (all rounds) | **RSS + RandomForest + all inputs** | n/a |

## 1, 5, 15. Comparison with the baselines (Lead 1, 72 rows, about 46 effective)
| | Always-LOW | Persistence | Anchor only | RP | C1 (RSS) | **E158** | **AUTO** |
|---|---|---|---|---|---|---|---|
| Accuracy | 65.3 % | 62.5 % | 63.9 % | 69.4 % | 69.4 % | 73.6 % | **79.2 %** |
| Balanced accuracy | 0.50 | 0.703 | 0.714 | 0.757 | 0.757 | 0.760 | **0.812** |
| HIGH precision / recall | n/a / 0 | 0.48 / 0.96 | 0.49 / 0.96 | 0.53 / 0.96 | 0.53 / 0.96 | 0.58 / 0.84 | **0.65 / 0.88** |
| LOW precision / recall | 0.65 / 1 | 0.96 / 0.45 | 0.96 / 0.47 | 0.96 / 0.55 | 0.96 / 0.55 | 0.89 / 0.68 | **0.92 / 0.75** |
| F1 | n/a | 0.640 | 0.649 | 0.686 | 0.686 | 0.689 | **0.746** |
| ROC-AUC / PR-AUC | n/a | 0.83 / 0.71 | 0.86 / 0.80 | 0.86 / 0.76 | **0.93 / 0.88** | 0.86 / 0.81 | 0.90 / 0.86 |
| Brier | 0.254 | 0.213 | 0.173 | 0.171 | 0.152 | 0.134 | **0.122** |
| Calibration slope / intercept | n/a | 0.71 / −0.33 | 0.94 / −0.29 | 0.70 / −0.25 | **0.99** / −0.30 | 0.72 / −0.13 | 0.73 / −0.13 |
| MAE (points) | n/a | 11.2 | 9.4 | 9.0 | 8.6 | 8.2 | **7.8** |
| False alarms / missed HIGH | 0 / 1.00 | 0.55 / 0.04 | 0.53 / 0.04 | 0.45 / 0.04 | 0.45 / 0.04 | 0.32 / 0.16 | **0.26 / 0.12** |
| Within-region concordance | n/a | 0.70 | n/a | 0.70 | 0.675 | 0.60 | **0.725 [0.58, 0.85]** |
| Confusion (TP / FP / FN / TN) | | | | | | 21 / 15 / 4 / 32 | **22 / 12 / 3 / 35** |

- Always-LOW uses its training base rate as the probability (stated in the protocol). Its class is LOW by definition.
- **AUTO − E158 Brier: −0.012 [−0.042, +0.020].** The direction is consistent, but the gain is **not statistically significant** at this sample size.
- **Accuracy is +5.6 points (4 more rows correct).** AUTO fixes more rows than it breaks: 3 fewer false alarms and 1 fewer miss.

## 6–7. Nested and chronological validation, per round
| Round | E158 accuracy / Brier | AUTO accuracy / Brier |
|---|---|---|
| 2018 | 63.6 % / 0.150 | **72.7 %** / **0.134** |
| 2019 | 68.0 % / 0.172 | **76.0 %** / **0.142** |
| 2021 | **88.0 %** / **0.083** | 88.0 % / 0.092 |

AUTO is better or equal in every round on accuracy and better on Brier in 2 of 3 (gate A3).

## 8. Shuffled-input and NLP controls (Lead 1)
| Control | Brier | AUTO − control [95 %] | Accuracy | Meaning |
|---|---|---|---|---|
| AUTO with all five-group and news inputs shuffled across provinces (3 seeds) | 0.160 | **−0.038 [−0.063, −0.012]** | 70.8 % | **The trigger groups carry real province-level information.** This is the first significant result in E151–E164 |
| AUTO with official inputs only, no news | 0.122 | +0.000 [−0.003, +0.005] | 79.2 % | **News adds nothing** beyond the official inputs |
| AUTO with news only, no official inputs | 0.159 | −0.036 [−0.065, −0.012] | 70.8 % | News alone is no better than the shuffled control |

- **Why this differs from E161/E163:** in those experiments a flexible LightGBM residual memorised province-specific noise. Given a choice, AUTO's inner validation picks **regularised linear or shallow-tree learners on a survey-history anchor.** With those learners, the official inputs generalise.
- **Leakage:** corrupting unreleased survey rounds changed AUTO by **0.0**.

## 9. Bias and fairness (signed error, predicted − observed points)
| Group | n | E158 | AUTO |
|---|---|---|---|
| Overall | 72 | +2.9 [0.6, 5.1] | +2.8 [0.7, 4.9] |
| Luzon | 35 | **+5.5 [3.1, 7.8] BIAS** | +3.9 [0.8, 7.4] BIAS |
| Visayas | 15 | −0.6 | +0.8 |
| Mindanao | 22 | +1.1 | +2.5 |
| Observed HIGH | 25 | −1.6 | −0.6 |
| Observed LOW | 47 | +5.3 BIAS | +4.7 BIAS |

- AUTO reduces the Luzon and LOW biases but does not remove them.
- **Fairness cannot be established** for single provinces (one row each), or by data completeness (every row has 2 earlier rounds).

## 10–11. Provincial ranking; Quezon and Batangas
- **Concordance:** 0.725 [0.58, 0.85], the highest of any arm. Per round 0.67 / 0.64 / 0.86. Spearman 2021: 0.62. Top-1 hit: 3/6.
- **CALABARZON back-test errors:**

| Row | E158 | AUTO |
|---|---|---|
| Quezon 2019 | +4.0 | **+1.2** |
| Rizal 2019 | +3.6 | −1.6 |
| Laguna 2018 | +9.3 | +8.9 |
| Batangas 2021 | −13.7 | **−13.1, not fixed** |
| Cavite 2021 | −6.2 | −9.0 |

- **Batangas:** the 2015→2021 rise in its position relative to the national level was invisible to every input at the issue date. AUTO does not fix it. The evidence needed is a more recent Batangas observation or a provincial livelihood indicator.

**2027-Q1, sealed cbfb61dc:**

| Province | Score | 90 % range | P(HIGH) | P(highest) |
|---|---|---|---|---|
| **Quezon** | **28.5** | 17.7–42.4 | 0.013 | **0.36** |
| Rizal | 27.3 | 16.9–41.0 | 0.009 | 0.24 |
| Batangas | 25.9 | 15.9–39.3 | 0.005 | 0.15 |
| Laguna | 25.5 | 15.7–38.8 | 0.005 | 0.13 |
| Cavite | 25.2 | 15.4–38.4 | 0.004 | 0.12 |

- **Quezon is highest without being forced there.** But P(highest) is 0.36 < 0.80, so the order is shown as probabilities, not ranks.
- All are LOW.

## 3, 12. Five groups and NLP (live model, RandomForest importance)
| Group | Importance |
|---|---|
| Poverty & social vulnerability | 0.52 |
| Climate | 0.18 |
| Market | 0.15 |
| Remittances | 0.07 |
| Employment | 0.05 |
| Timing | 0.04 |

- **News columns make up 0.49 of the importance** (distributed inside the groups), but the no-news control shows **they add no out-of-sample value.** Importance is not contribution.
- **Employment and remittances have no provincial official data** (E163 audit), so their share comes from their news columns and national timing. The fix is provincial LFS and BSP data.

## 13. Calibration and uncertainty
- **Slope 0.73 [0.51, 0.88]:** C4 fails. The forecasts are too spread; AUTO's linear recalibration was not selected by inner validation.
- **Reliability table (Lead 1):**

| Probability bin | Rows | Mean predicted | Observed HIGH rate |
|---|---|---|---|
| 0–0.2 | 17 | 0.08 | 0.00 |
| 0.2–0.4 | 9 | 0.26 | 0.22 |
| **0.4–0.6** | 22 | 0.50 | **0.18** |
| 0.6–0.8 | 11 | 0.72 | 0.73 |
| 0.8–1.0 | 13 | 0.91 | 0.85 |

- **The middle bin is over-predicted.** That is the false-alarm zone.

## 14. Forecast horizons
| Lead | AUTO accuracy | E158 accuracy | AUTO − E158 Brier [95 %] | E156 criteria failed |
|---|---|---|---|---|
| 1 | **79.2 %** | 73.6 % | −0.012 [−0.042, +0.020] | **C4 only** |
| 2 | **79.2 %** | 73.6 % | −0.014 [−0.046, +0.023] | C4 |
| 3 | **76.4 %** | 75.0 % | −0.021 [−0.049, +0.009] | C4 |
| 4 | **76.4 %** | 75.0 % | −0.026 [−0.059, +0.003] | C4 |

**Maximum reliable lead: 0.** Only the calibration criterion C4 fails. Lead 1 now passes C1 (accuracy above the majority rule at the effective sample size), which no earlier model did.

## 2. Data audit
- **Target:** 228 survey rows, with no duplicates.
- **Outliers:** two extremes (Lanao del Sur 88.7 % and Bataan 16.5 %, both 2015) are plausible and kept.
- **Feature granularity and missingness:** in `data/e163/out/group_audit.csv`.
- **Definition break to fix at source:** subsistence incidence moves from families (training years) to population (the 2018+ PSA methodology), and the CPI base changes from 2012 to 2018 (E137 notes).

## 16. Release gate
| Item | Decision |
|---|---|
| **AUTO** | **Release candidate.** It passes A1–A8 on retrospective nested validation. **Not deployed:** its Brier gain is not significant, calibration fails C4, and the outer rows were seen when the menu was designed. It goes live only after the sealed 2027 forecast (cbfb61dc) is scored, or after independent review by the adviser |
| E158 | Remains the production thesis model |
| Reportable accuracy | "AUTO, nested selection: 79.2 % at Lead 1 (retrospective), against E158 73.6 %; the Brier improvement is not statistically significant" |
| Maximum reliable lead | 0 (C4) |
| Provincial display | Probabilities of being highest, not ranks. Quezon is most likely (0.36) |
| Production, dashboard, API | Unchanged |

**Limiting factors for further gains:**
1. Calibration of the middle-probability band.
2. No provincial employment or remittance data.
3. No HFIAS round after 2021, which limits both training and any untouched test.
