# aiPHeed: objectives completion and model validation report (E70)

**Date:** 2026-10-20
**Branch:** `e70-objectives-completion`, cut from `final-system-v2` @ 2c88d9f
**Experiment:** `aipheed-backend-aligned/experiments/E70_Objectives_Completion/` (protocol, runner, seals, tables, tests)
**Starting point:** `FINAL_OBJECTIVES_AND_MODEL_VALIDATION_AUDIT.md` (same date)

## Summary

| Question | Answer |
|---|---|
| **Did Lead-2 accuracy reach 80%?** | **No.** The best defensible Lead-2 result is still **36/50 = 0.720** (Wilson 95% [0.583, 0.825]), with HIGH recall 0.556 and balanced accuracy 0.684. It is development evidence on reused quarters. |
| Does the model forecast food insecurity? | **No, not demonstrably.** The label T43 (SWS hunger AND provincial food-price pressure) equals food-price pressure on **all 155** Lead-1/2/3 rows. Regional hunger was above 11.3% in every evaluated target quarter, and above every threshold anchored on 2021–22. The LightGBM accuracy is food-price-pressure accuracy. |
| Did any change improve the model? | **No.** Three pre-registered candidate changes and 13 ablation and single-group checks were tested. None passed the pre-registered improvement rule. The served model is unchanged. |
| Leakage | **None found.** All post-issue raw values were randomised; every forecast of every arm is unchanged (max \|Δ\| 4.7e-13). |
| Reproducible? | **Yes.** A clean `git archive` re-run gives byte-identical sealed files. |
| Objectives 1–4 | **All PARTIALLY MET** (§10). |
| Production | Unchanged. Nothing was merged, pushed or deployed. The E38 default and the thesis-mode served values are unchanged; only text fields changed. |

---

## 1. Approved objectives (Chapter I §1.5, verbatim)

1. "To design a two-tier pipeline combining zero-shot XLM-RoBERTa Filipino-English sentiment extraction and BERTopic unsupervised topic modeling to produce the bias-corrected Food Stress Sentiment Index and latent food insecurity risk patterns per province-quarter from a Filipino-English news corpus."
2. "To evaluate the performance of the proposed LightGBM forecasting model using the following metrics: I. Accuracy … II. Precision and Recall … III. F1-Score … IV. AUC-ROC … V. Forecast performance across multiple lead times via walk-forward expanding-window cross-validation to empirically determine the furthest horizon at which reliable forecasting is achievable"
3. "To produce spatially disaggregated municipal and city food insecurity risk rankings from validated province-level forecasts, using PSA published poverty incidence and population density as vulnerability weights."
4. "To compare the effectiveness of the proposed LightGBM forecasting model against the following baseline approaches: I. Naive persistence baseline II. PSA-only indicator baseline III. NLP-only sentiment baseline IV. Logistic regression baseline"

Chapter I §1.7: "SWS quarterly hunger data and PSA food price data will be used to determine food insecurity risk."

Chapter I states no accuracy threshold. The ≥ 80% Lead-2 goal comes from this task's brief and is applied as a performance goal, not as a thesis criterion. No objective was reworded.

---

## 2. Audit findings and what was done about each

The full traceability matrix (finding → change → test → criterion) is in `E70/ACTION_PLAN.md`.

| Audit finding | Change in E70 | Evidence | Outcome |
|---|---|---|---|
| T43 = price pressure on all rows | Dominance test with a hunger-threshold sweep (P25–P90 of 2021–22) | `tables/E70_TABLES.md` "Target audit" | Confirmed: price-dominated under every pre-anchored threshold. The label was **not** revised: the only binding threshold (> 14.3) would be chosen from the evaluation period. |
| 8 HIGH missed at Lead 2 | Error decomposition by component | "Lead-2 R0 errors" | 4 misses are the 2024-Q2 surge: P_price was 0.81–0.96, but the regional-hunger component gave 0.21 because the latest hunger known on 2024-01-01 was 10.3%. The other 4 misses and all 6 false alarms are price-component errors. |
| Over-confidence (slope 0.55) | A2 SHRINK: training-only logit shrinkage | Lead-2 slope 0.54 | No effect: at 7 of 10 Lead-2 origins b = 1 (fewer than 10 out-of-fold rows, or a training slope ≥ 1), and at the other 3 b = 0.85–0.91. The over-confidence appears only out of sample. |
| Configuration instability (9 configurations in 10 origins) | A1 STABLE: cumulative-loss configuration | 34/50, Brier +0.005 | Worse |
| How much is price projection alone? | S0 STRUCT (base-effect CPI projection, no trees) | Lead-2 35/50; Lead-1 51/60 with a better Brier (Δ −0.008, CI [−0.016, −0.001]) | Most of the skill comes from the CPI base-effect projection. The trees add no measurable value. |
| Evidence-group value, news value | 7 ablations, 6 single-group models | "Ablations" | No group adds measurable value (§8.2). Removing news gives 37/50 (Δ Brier −0.002, CI includes 0). |
| Obj 4 tests one-sided / unadjusted | Two-sided sign test with Holm over the 4 required baselines | "Objective 4" | Credible advantage only over IV (combined LR). After Holm, PSA-only (II) is no longer credible (Holm p 0.117). |
| Development reuse | Disclosed; new arms sealed prospectively | `sealed/prospective.csv` sha 31f73040… | Awaits 2026-Q4 / 2027-Q1 outcomes |
| No clean reproduction of the model | Re-run from `git archive` | `REPRODUCTION.md` | Byte-identical |
| AI-only news annotation | 300-headline blind, stratified human sample + scorer | `annotation/` | **Not yet labelled.** Human labels must come from the researcher. |
| 142-LGU consistency | `obj3.py` re-run on this branch | `out/obj3_results.json` | 142/142 consistent. The PDF holds all 34 Batangas LGU values at 4 dp. The script's 2-dp string test shows 23/34, a rounding artifact of the check, not a defect. |
| Dashboard all-HIGH and goal text | Text-only additions in existing backend fields (§7) | `test_e70_disclosure.py` | Done; no UI element changed |

---

## 3. Data sources, coverage and availability

All inputs fall within 2021-Q1 … 2026 and were released by the authorized limit of 2026-10-14. The library asserts the window before it loads rows.

| Source | Level | Coverage | Availability rule at issue date O(t) = first day of quarter t+1 |
|---|---|---|---|
| PSA CPI YoY, food and all items (OpenSTAT 0012M4ACP23) | Province | 2021-01 … 2026-09 | Months up to the cut month of t only |
| PSA CPI index (ACP22) | Province | 2021 … 2026 | Same |
| SWS hunger rounds (`sws_rounds.csv`) | Balance Luzon / national, **regional only** | 2021-Q2 … 2026-Q3 (no 2021-Q1, 2022-Q1). 2025-Q2 and 2025-Q3 have non-approved rounds only. | Round `published` date < O(t) |
| PSA palay/corn production; fisheries/aquaculture | Province | 2021 … | Quarters ≤ t−1 |
| PSA LFS unemployment and underemployment | **National** | 2021 … | Months up to the end of t−1 |
| BSP OFW remittances, FX (`bsp_macro.parquet`) | **National** (repeated per province) | 2021-Q1 … 2026-Q3 rows; remittances missing for the 2026 issues | Quarters ≤ t−1 |
| PAGASA tropical cyclones, ENSO (`pagasa_climate.parquet`) | Province / national | 2021-Q1 … 2026-Q3; 2026-Q3 typhoon count incomplete | Cyclones ≤ t, ENSO ≤ t−1 |
| PSA rice prices (`psa_rice_prices.parquet`) | Province | 2021 … 2026 | Quarters ≤ t−1 |
| Rice-policy events | National | 2021 … 2026 | Announcement date < O(t) |
| News corpus (E40 composition for the model; v3 pipeline for FSSI) | Province / national | 9,665 in-window headlines; 695 admitted; titles only | Publication date < O(t). The corpus was collected retrospectively: 687/695 were first seen after their issue date. |
| PSA SAE 2021 poverty; POPCEN 2024 density | LGU | 141/142 poverty (Lucena uses an unverified substitute); 142/142 density | Poverty usable from 2025-01-01 (release date) |

Data vintages are the latest PSA releases, not real-time vintages. Revisions cannot be excluded.

---

## 4. Target definition

| Target | Definition | Class |
|---|---|---|
| **T43** (model label) | HIGH iff SWS hunger quarter mean (all rounds) > 11.3 AND (province food CPI YoY > its 2021–22 P60 OR food-minus-headline YoY > its P60) | **Proxy label**, price-dominated in practice |
| DIRECT-R | Regional SWS hunger > 11.3 at the target quarter | **Direct outcome, regional only** |
| FIRI v2 (served map value) | Evidence-weighted proxy composite of six domains | **Proxy index, not a probability, not validated** |

**Dominance test (Lead 2, 50 rows).**
- T43 = PS on 50/50 rows; the hunger condition never binds.
- Minimum target-quarter hunger: 16.1%.
- HIGH comes from food-minus-headline alone in 13 of 18 cases, food YoY alone in 1, and both in 4.
- Same at Leads 1 and 3. Under thresholds P25 = 9.78 … P90 = 13.57, T43 = PS on every row.

**What this means.** In 2024–2026 the label says "provincial food prices are rising faster than the province's own 2021–22 norm (mostly faster than headline inflation) while regional hunger is high". It does not separate provinces by hunger, and no provincial food-insecurity outcome exists to test it.

**DIRECT-R.** Hunger was above 11.3 in every evaluated quarter (10/10 at Lead 2). The I7 hunger component scores 9/10 and always-above scores 10/10. With no LOW quarter, accuracy cannot show skill on the direct outcome.

The target uses only information available at the issue date for training labels, persistence and as-of baselines (verified, §9).

---

## 5. Final model and why it was kept

**Selected: R0 = E56-TUNED LightGBM** (unchanged):

P(T43 HIGH at t+2) = P(regional hunger > 11.3) × P(provincial price signal)

- The price part is a LightGBM with a structural CPI base-effect offset.
- Its configuration is chosen per origin from 72 by forward log-loss on training quarters only.

**Why it was kept.** By the pre-registered rule (PROTOCOL §6), a change must:
- beat R0 on Lead-2 Brier with a quarter-bootstrap CI below 0 and a Holm-adjusted two-sided sign test p < 0.05;
- keep HIGH recall;
- not be credibly worse at Leads 1 and 3.

Neither candidate met this. The simpler S0 projection model is nearly as good, which is reported as a simplicity finding (§8.2). It was not a candidate under the protocol, so it was not promoted.

---

## 6. Lead-1, Lead-2 and Lead-3 results

All rows use the expanding-window walk-forward design, are identical across arms, and use threshold 0.50. Δ Brier is against R0.

### Lead 2 (primary): 50 rows, 10 quarters 2024-Q2 … 2026-Q3, 18 HIGH, ICC 0.29, effective n ≈ 23

| Arm | Correct | Acc [Wilson] | TP/FP/FN/TN | Prec H | Rec H | F1 H | Rec L | Bal | AUC | Within-q AUC | Brier | Slope |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **R0 E56** | **36/50** | **0.720 [0.583, 0.825]** | 10/6/8/26 | 0.625 | 0.556 | 0.588 | 0.812 | 0.684 | 0.649 | 0.706 | 0.214 | 0.55 |
| A1 STABLE | 34/50 | 0.680 | 11/9/7/23 | 0.550 | 0.611 | 0.579 | 0.719 | 0.665 | 0.679 | 0.676 | 0.219 | 0.59 |
| A2 SHRINK | 36/50 | 0.720 | 10/6/8/26 | 0.625 | 0.556 | 0.588 | 0.812 | 0.684 | 0.644 | 0.706 | 0.217 | 0.54 |
| S0 STRUCT | 35/50 | 0.700 | 9/6/9/26 | 0.600 | 0.500 | 0.545 | 0.812 | 0.656 | 0.648 | 0.618 | 0.222 | 0.49 |
| Persistence | 28/50 | 0.560 | 8/12/10/20 | 0.400 | 0.444 | 0.421 | 0.625 | 0.535 | 0.535 | — | 0.440 | — |
| Majority / climatology | 32/50 | 0.640 | 0/0/18/32 | — | 0 | 0 | 1 | 0.500 | 0.500 / 0.214 | — | 0.360 / 0.304 | — |

- **R0 accuracy, quarter-cluster bootstrap 95% CI:** [0.58, 0.84].
- **Calibration:** ECE 0.226; over-confident.
- **Confusion matrix:** TP 10, FP 6, FN 8, TN 26.
- **Correct per quarter** (of 5): 2024-Q2 1, 2024-Q3 3, 2024-Q4 3, 2025-Q1 4, 2025-Q2 4, 2025-Q3 3, 2025-Q4 5, 2026-Q1 5, 2026-Q2 4, 2026-Q3 4.
- **Per province** (correct of 10; HIGH found): Batangas 7 (1/3), Cavite 4 (1/4), Laguna 7 (3/5), Quezon 8 (5/6), Rizal 10 (no HIGH).

### Lead 1: 60 rows, 12 quarters, 21 HIGH

| Arm | Correct | Acc [Wilson] | Prec H | Rec H | F1 H | Bal | AUC | Brier | Slope |
|---|---|---|---|---|---|---|---|---|---|
| **R0** | 51/60 | 0.850 [0.739, 0.919] | 0.833 | 0.714 | 0.769 | 0.819 | 0.901 | 0.130 | 0.97 |
| A1 | 47/60 | 0.783 | 0.700 | 0.667 | 0.683 | 0.756 | 0.895 | 0.136 | 0.91 |
| A2 | 51/60 | 0.850 | 0.833 | 0.714 | 0.769 | 0.819 | 0.896 | 0.137 | 0.93 |
| S0 | 51/60 | 0.850 | 0.833 | 0.714 | 0.769 | 0.819 | 0.911 | **0.122** | 1.06 |
| Persistence | 41/60 | 0.683 | 0.550 | 0.524 | 0.537 | 0.647 | 0.647 | 0.317 | — |

### Lead 3: 45 rows, 9 quarters, 14 HIGH

R0 28/45 = 0.622, AUC 0.620, Brier 0.251, slope 0.25. This is below always-LOW (31/45 = 0.689). S0 has Brier 0.226; A1 27/45.

### Furthest reliable horizon (E63 §8 criterion, unchanged)

No arm meets it at any lead. **Furthest reliable horizon: none established.** Lead 4 cannot be computed under the CPI cutoff.

---

## 7. The 80% statement

**The Lead-2 accuracy goal of at least 80% was not reached.**

- Selected model: 36 of 50 correct = 0.720, Wilson 95% [0.583, 0.825], quarter-cluster [0.58, 0.84].
- 18 HIGH and 32 LOW; HIGH recall 0.556, balanced accuracy 0.684, Brier 0.214, AUC 0.649, calibration slope 0.55.
- No arm reached 0.80. The highest were two ablations at 37/50 = 0.74, a best-of-16 figure that is not significant.

**What would have been needed, and why it was not done.**
- Four more correct rows would reach 40/50. The four 2024-Q2 misses alone would do it.
- They were caused by a rise in regional hunger that the information on 2024-01-01 did not show. The latest reading, 10.3%, was below the threshold, and no tested method (E69) forecasts hunger two quarters ahead better than the latest reading.
- Adjusting the model to catch that quarter now would be tuning on a known outcome. E58 did exactly that, and its gain was 2024-Q2 timing only.

**What the result is not.** The accuracy is against a label that equals food-price pressure, so it is not food-insecurity accuracy.

---

## 8. Baselines, ablations, uncertainty, calibration

### 8.1 Objective 4: same 45 rows (targets 2024-Q3 … 2026-Q3), 14 HIGH

| Model | Acc | Rec H | AUC | Brier | R0 − baseline Δ Brier [95% CI] | Sign (two-sided / Holm) | Credible |
|---|---|---|---|---|---|---|---|
| **R0 E56** | 0.778 | 0.714 | 0.763 | 0.178 | | | |
| I. Persistence | 0.600 | 0.571 | 0.592 | 0.400 | −0.222 [−0.415, −0.037] | 6/3 (0.508 / 0.508) | No |
| II. PSA-only LR | 0.378 | 0.214 | 0.295 | 0.598 | −0.420 [−0.647, −0.191] | 8/1 (0.039 / 0.117) | No |
| III. NLP-only LR | 0.667 | 0.143 | 0.488 | 0.235 | −0.057 [−0.120, +0.006] | 7/2 (0.180 / 0.359) | No |
| IV. Combined LR | 0.333 | 0.214 | 0.247 | 0.646 | −0.467 [−0.670, −0.272] | 9/0 (0.004 / 0.016) | **Yes** |
| Majority (extra) | 0.689 | 0 | 0.500 | 0.311 | −0.133 [−0.313, +0.022] | 6/3 (0.508) | No |

- R0 has the best Brier of all models on these rows.
- After Holm adjustment, its advantage is credible only over IV. That baseline has AUC below 0.5, so beating it is weak evidence.
- The 45-row accuracy 0.778 is a subset figure, not a separate demonstration.

### 8.2 Ablations and single groups (Lead 2, 50 rows)

| Removed group | Correct | Δ Brier vs R0 [CI] | Rows identical to R0 |
|---|---|---|---|
| climate | 34 | +0.001 [−0.007, +0.010] | 25 |
| fish kill | 36 | +0.001 [+0.000, +0.001] | 40 |
| employment | 36 | +0.001 [−0.000, +0.003] | 30 |
| OFW remittance | 34 | −0.010 [−0.030, +0.007] | 25 |
| news | 37 | −0.002 [−0.006, +0.001] | 40 |
| policy | 36 | +0.000 [+0.000, +0.001] | 45 |
| poverty | 37 | −0.003 [−0.009, +0.001] | 30 |

- **No evidence group adds measurable value.** The rule needs CI lower bound > 0. Fish kill and policy have lower bounds of exactly +0.000 with Δ ≤ 0.001, which is negligible.
- **Single-group models are all worse than R0.** Market only: 31/50, Δ +0.042 [+0.005, +0.081]. Climate only: 26/50. News only: 20/50.
- **The skill is in the CPI projection.** The base-effect projection alone (S0) gets 35/50.
- **Repeated inputs.** National and regional inputs (employment, remittances, ENSO, hunger) are the same for all five provinces. They can only shift a quarter's level, so they cannot separate provinces within a quarter.

### 8.3 Uncertainty and calibration

- Wilson intervals and quarter-cluster bootstraps are shown for every arm. The effective sample is about 23 observations at Lead 2.
- At this sample size, a true 80% accuracy could not be distinguished from 72%.
- Calibration slope: Lead 1 0.97, Lead 2 0.55, Lead 3 0.25. Probabilities beyond Lead 1 are over-confident, and the training-only shrinkage could not detect this in-sample.

---

## 9. Overfitting, leakage, bias, generalization

**Leakage** (`out/leak.json`). At origins 2023-Q4, 2025-Q1 and 2026-Q1:
- every raw value unavailable at the issue date was randomised: CPI after the cut month, SWS rounds published on or after the issue date, production, LFS, news, typhoons, ENSO, remittances, rice, and policy events;
- R0, A1, A2 and S0 were re-run, including A1's corrupted history;
- max |Δ| ≤ 4.7e-13 and every configuration is unchanged. **Pass.**

**Timing tests** (`test_e70.py`):
- target − origin = lead;
- issue date = first day after the origin quarter;
- no duplicate rows;
- prospective targets have no outcome round published before the seal.

**Overfitting.** Insufficient data to determine, with warning signs:
- 9 configurations in 10 origins; the stable-configuration arm did worse, so per-origin selection is not the only source of variance;
- over-confidence from Lead 2 onward;
- accuracy falls with lead (0.85 → 0.72 → 0.62);
- every quarter was reused across about 30 experiments. E70 adds 16 more arms on the same rows, disclosed as best-of-k.

**Bias.**
- Missed HIGH rows concentrate in Cavite (1/4 found) and Batangas (1/3), and in the 2024-Q2 regime change.
- Accuracy depends on the regime: 18/30 in 2024-Q2 … 2025-Q3 (17 HIGH) vs 18/20 in 2025-Q4 … 2026-Q3 (1 HIGH).
- The E40 news composition counts are ≥ 5 for all 50 origin province-quarters, so the model's news inputs cannot show a sufficiency effect.
- In the v3 FSSI pipeline only 20 of 115 province-quarters are SUFFICIENT; Rizal has 0 articles in 17 of 23.

**Generalization.** It can only be shown on unseen quarters. The sealed prospective forecasts are below.

| Target | Lead | R0 (Cavite, Laguna, Quezon, Rizal, Batangas) | FIRI v2 served |
|---|---|---|---|
| 2026-Q4 | 2 (issued 2026-07-01) | 0.024, 0.061, 0.285, 0.005, 0.019 | (sealed in FIRI2) |
| 2027-Q1 | 2 (issued 2026-10-01) | 0.109, 0.070, 0.146, 0.050, 0.043 (all LOW) | 0.76, 0.80, 0.72, 0.72, 0.71 (all HIGH) |

The price-pressure model and the proxy index point in opposite directions for 2027-Q1. The 2027-Q1 outcomes will be the first independent test of which reading is useful.

---

## 10. Objective matrix

| Objective | Status | Evidence | Precise blocker |
|---|---|---|---|
| 1 NLP pipeline, FSSI, BERTopic | **PARTIAL** | Implemented and served (XLM-RoBERTa zero-shot intensity, classifier v2, de-duplication, FSSI-v3, BERTopic). Ablation: news adds no measurable forecasting value (Δ −0.002, CI includes 0). Blind 300-headline human sample drawn. | No human labels yet; bias correction has no reference to validate against; titles only; 7/695 Filipino headlines |
| 2 Metrics and lead time | **PARTIAL** | Full metric set for Leads 1–3, reproduced byte-identically, leakage-tested | Label is price pressure in practice; no reliable horizon under the pre-set criterion; development data only; 80% not reached |
| 3 142-LGU rankings | **PARTIAL** | 142/142 complete, finite, mapped, consistent across API, map and PDF; poverty 0.6 / density 0.4 weights recomputed (max \|Δ\| 5e-5) | The premise "validated province-level forecasts" is unmet; LGU values are relative prioritization |
| 4 Baseline comparison | **PARTIAL** | Same 45 rows, two-sided tests with Holm | Credible only over IV; not over persistence, PSA-only (after Holm) or NLP-only |

---

## 11. Tests and reproduction

| Check | Result |
|---|---|
| Backend `pytest -q` (all) | **546 passed, 18 skipped, 0 failed** (includes 4 new `test_e70_disclosure.py`) |
| E70 tests (`E70/tests/test_e70.py`) | **9/9**: protocol freeze, seals, R0 = E63, timing, prospective blindness, target dominance, decision rule, leakage, blind sample |
| Frontend `vitest run` | **49/49** (no frontend file changed) |
| `vite build` | passed |
| `tsc --noEmit` | not re-run; the 6 pre-existing `mockData.ts` errors from the audit are unaffected |
| API ↔ dashboard / PDF, 142 LGUs | `obj3.py` re-run: all consistent; PDF 34/34 Batangas values at 4 dp |
| Leakage corruption | pass (3 origins × 4 arms) |
| Clean-checkout reproduction | byte-identical `predictions.csv`, `prospective.csv`, `ablations.csv` |
| Browser end-to-end | not re-run in E70; no UI or served value changed since the 10-20 audit's browser check |

**Commands** (see `E70/REPRODUCTION.md`; `AIPHEED_EXP` = clean `git archive 089bdf2` export):

```
python -B runner/e70_predict.py main ; python -B runner/e70_predict.py ablation
python -B runner/e70_score.py ; python -B runner/e70_leak.py ; python -B runner/e70_export.py
python -m pytest -q aipheed-backend-aligned/experiments/E70_Objectives_Completion/tests
cd backend ; python -m pytest -q
```

---

## 12. Remaining limitations and next steps

1. **No provincial or municipal food-insecurity outcome.** Obtain CBMS food-insecurity items or provincial FIES to make T43 or FIRI testable.
2. **The hunger condition never binds in 2024–26.** The label cannot separate hunger from prices until hunger falls below the threshold in some quarter.
3. **No held-out data.** Score the sealed 2026-Q4 and 2027-Q1 forecasts (E70 `prospective.csv` 31f73040…, E68, E69, FIRI2) once the PSA CPI for October 2026 to March 2027 and the SWS 2026-Q4 and 2027-Q1 rounds are published. Keep sealing each quarter before its outcome. About 20 unseen quarters are needed for a credible accuracy claim.
4. **Human annotation.** Label `annotation/HUMAN_ANNOTATION_SAMPLE.csv` (ideally two annotators), then run `e70_annotation.py score`.
5. **News.** Collection is retrospective, titles only, and English-dominated; real-time, full-text Filipino sources are needed.
6. **Smaller items.** Verify the Lucena poverty value; obtain 2026 remittances; use real-time data vintages.
7. **Simplicity decision for the adviser.** S0 (projection only) is as accurate as the LightGBM and better calibrated at Lead 1. If the thesis keeps the LightGBM, report that its trees add no measurable skill.

---

## 13. Changes, branch, commits, production

**Branch:** `e70-objectives-completion` (local; **not pushed**).

**Commits:**
- `19937ab`: protocol frozen before any forecast;
- `7ed1447`: runner and seals;
- `2e01f6f`: scoring, leakage, annotation, backend disclosure;
- the report commit, given in the delivering reply.

**Changed or added files:**
- `aipheed-backend-aligned/experiments/E70_Objectives_Completion/**`: plan, protocol, runner, inputs, sealed, out, tables, annotation, tests, reproduction;
- `backend/app/ml/inference/thesis_system.py`: **text only**. The PDF sentences gain the E70 outcome. The region summary notes when every province is HIGH. The model sentence states that neither 75% nor 80% is demonstrated. The E70 summary is a required artifact, so there is no silent fallback.
- `backend/data/thesis/e70_summary.json`;
- `backend/tests/integration/test_e70_disclosure.py`;
- this report.

**Production.** No served score, class, rank, model, threshold, colour or UI element changed. The production default (E38) and thesis-mode defaults are unchanged. Nothing was merged, pushed or deployed.
