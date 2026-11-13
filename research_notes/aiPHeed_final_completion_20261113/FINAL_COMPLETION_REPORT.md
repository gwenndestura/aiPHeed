# aiPHeed final model: completion report (2026-11-13)

**Selected final model: FINAL (RATE + MIND) LightGBM, unchanged.**
- Every new candidate built today was evaluated under protocols locked before fitting:
  - 3 change-since-survey and trajectory arms;
  - long-gap training pairs;
  - 3 national-relative models;
  - a Bayesian structural model and 2 hybrids;
  - 5 tuned LightGBM arms (randomized hyperparameter search, class-weight selection, training-chosen threshold, structural anchor, everything combined);
  - DSWD DROMIC disaster/assistance data (6 features; one confirmed and tested in LightGBM).
- On your eight thresholds, no candidate beats FINAL.
- **FINAL passes all eight thresholds in ENNS 2018, ENNS 2019 and pooled. It fails three in ENNS 2021: recall, F1 and balanced accuracy.** The cause is that the three missed 2021 HIGH provinces cannot be ranked above similar LOW provinces with any public information available at the 2021 forecast date.
- Not deployed, nothing overwritten, dashboard unchanged.

---

## 1. Final model and architecture

| Item | Value |
|---|---|
| Model | FINAL (RATE + MIND), `app.hcw.final_engine.fit_predict` in `C:\Users\admin\aipheed_hcw\backend` |
| Target | HFIAS moderate+severe share of households ≥ 50 % = HIGH (thesis definition, unchanged) |
| Structure | Survey anchor (H / OH / RSS, chosen by inner CV) + LightGBM on the change per unit of elapsed time since the anchor survey (RATE) + median fill with missing-value flags (MIND). Probability = Φ(μ / σ) |
| Selection inside each fit | 25-input selection + correlation pruning; input set (GOV / FULL / GOV+cons / FULL+cons); 16-setting grid; all by region-grouped inner CV on training rows only |
| Forecast | One quarter ahead (Lead 1), validated chronologically; sealed issue 2026-Q4 for 2027-Q1..2028-Q1 (sha `80b20aed…`) |
| Seeds | 168, 1, 2, 3, 4 (mean probability); threshold 0.50 |

**Optimised hyperparameters (chosen by inner CV in each fold; modal setting):**

| Fold | Anchor | Input set | num_leaves | max_depth | learning_rate | n_estimators | min_child_samples | feature_fraction | bagging_fraction | L1 | L2 | Class weights | Calibration |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2018 | OH | GOV+cons | 3 | −1 | 0.02 | 150 | 40 | 0.8 | 0.8 | 0 | 20 | balanced × survey precision | raw |
| 2019 | OH | GOV+cons | 3 | −1 | 0.02 | 150 | 40 | 0.8 | 0.8 | 0 | 20 | balanced × survey precision | raw |
| 2021 | RSS | FULL | 3 | −1 | 0.02 | 150 | 40 | 0.8 | 0.8 | 0 | 20 (one seed: 5) | balanced × survey precision | raw |

A 40-configuration randomized search (num_leaves up to 15, depth 2–4, learning rate 0.01–0.1, up to 700 trees, L1 up to 5, L2 up to 50) was also run. Its choices did not improve on these settings (§4, arm A1).

## 2. Inputs and sources

**FINAL's inputs:**
- Provincial poverty, subsistence and poverty gap (PSA small-area estimates).
- Regional GRDP relative and growth (PSA).
- Local and national food and rice CPI (PSA).
- Palay and corn production (PSA OpenSTAT).
- Fish production.
- Rainfall, soil-moisture and drought anomalies.
- Typhoon exposure (NOAA IBTrACS).
- Regional unemployment.
- News-derived indices.

Every input is taken as of the forecast quarter (as-of panels; 6-quarter survey release lag). Inputs actually selected in 2021 include `cpi_food_3m`, `cpi_food_rel_nat`, `vu_tc_strong`, `l_rice_rel`, `cpi_since` and news indices; in 2018/2019 `hh_grdp_rel`, `p_poverty`, `p_subsistence`, `ag_palay_yoy` and others.

**New indicators investigated today:**

| Indicator | Source | Coverage | Available at forecast date | Contribution | Decision |
|---|---|---|---|---|---|
| DROMIC hydro-met displaced persons per 1,000 since last survey (D3) | DSWD DROMIC terminal/numbered reports (Word; 2016–17 Google Docs), 6,537 province values | 2016–2021; 2013–2015 absent (Yolanda not in DROMIC); about 21 events per window return HTTP 410 | Yes (report date < cut-off; test-verified) | **Confirmed** on the 2015→2018 and 2015→2019 changes (Holm p 0.048). In LightGBM (LG-D) it is selected in every fit, but 2021 stays 1/0/3/21 | Not added: no improvement |
| DROMIC affected persons, damaged houses, assistance per capita and per affected person, conflict displacement | Same | Same | Yes | Not confirmed (sign flips; assistance not associated with recovery in non-2021 data) | Not added |
| SAP 2020 coverage | Press summaries only; no provincial dataset; FOI request only | 2020 only | — | Unverified; no historical counterpart, so it cannot be learned | Not used |
| Structural income/poverty attractor | PSA (already in FINAL's inputs) | 2009– | Yes | Confirmed on non-2021 changes; reliable for "above national" (ATTR); worse on the ≥ 50 % label | Not added to the absolute model; ATTR sealed separately |

Source details: `../aiPHeed_final_dromic_20261113/evidence/SOURCES.md`.

## 3. Final status against the required thresholds (FINAL, Lead 1, 5-seed mean, historical test rounds)

| Survey round | Recall | Precision | F1 | Balanced Accuracy | Brier | Accuracy | ROC-AUC | PR-AUC (prevalence) | Status |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 2018 | 1.000 PASS | 0.727 PASS | 0.842 PASS | 0.893 PASS | 0.130 PASS | 0.864 PASS | 0.964 PASS | 0.950 > 0.364 PASS | **PASS (8/8)** |
| 2019 | 0.846 PASS | 0.846 PASS | 0.846 PASS | 0.840 PASS | 0.151 PASS | 0.840 PASS | 0.853 PASS | 0.841 > 0.520 PASS | **PASS (8/8)** |
| 2021 | **0.250 FAIL** | 1.000 PASS | **0.400 FAIL** | **0.625 FAIL** | 0.090 PASS | 0.880 PASS | 0.857 PASS | 0.610 > 0.160 PASS | **FAIL (5/8)** |
| Pooled | 0.800 PASS | 0.800 PASS | 0.800 PASS | 0.847 PASS | 0.123 PASS | 0.861 PASS | 0.898 PASS | 0.846 > 0.347 PASS | **PASS (8/8)** |

**Confusion matrices** (TP/FP/FN/TN; HIGH = positive):

| Round | TP/FP/FN/TN | HIGH recall | HIGH precision | LOW recall | LOW precision | False alarms | Missed HIGH |
|---|---|---|---|---|---|---|---|
| 2018 (8 HIGH / 14 LOW) | 8/3/0/11 | 1.00 | 0.73 | 0.79 | 1.00 | 3 | 0 |
| 2019 (13 / 12) | 11/2/2/10 | 0.85 | 0.85 | 0.83 | 0.83 | 2 | 2 |
| 2021 (4 / 21) | 1/0/3/21 | 0.25 | 1.00 | 1.00 | 0.88 | 0 | 3 (Masbate, Occidental Mindoro, Agusan del Sur) |
| Pooled (25 / 47) | 20/5/5/42 | 0.80 | 0.80 | 0.89 | 0.89 | 5 | 5 |

## 4. Comparison of all candidates (Lead 1, 5-seed mean, threshold 0.50 unless stated)

| Model | 2018 (TP/FP/FN/TN, all 8) | 2019 | 2021 HIGH recall | 2021 precision | 2021 F1 | Pooled Brier | Stability (2021) |
|---|---|---|---|---|---|---|---|
| **FINAL (selected)** | 8/3/0/11 ✓ | 11/2/2/10 ✓ | 1/4 | 1.00 | 0.40 | **0.123** | All seeds 1/0/3/21. Training-round drops: 1/4–3/4 |
| FINAL-LG (long-gap pairs) | 8/3/0/11 ✓ | 11/2/2/10 ✓ | 1/4 | 0.50 | 0.33 | 0.123 | All seeds 1/1/3/20. Drops: 3/2, 2/4, 2/3 (TP/FP) |
| A1 LightGBM, 40-config randomized search | 7/2/1/12 ✓ | 10/2/3/10 ✓ | 1/4 | 1.00 | 0.40 | 0.125 | Seeds 1/0 or 1/1 |
| A2 class-weight selection (inner Brier) | 8/4/0/10 ✗ | 11/2/2/10 ✓ | 1/4 | 0.50 | 0.33 | 0.125 | — |
| A3 training-chosen threshold (≈ 0.43) | 8/6/0/8 ✗ | 11/3/2/9 ✓ | 2/4 | 0.67 | 0.57 | 0.123 | — |
| A4 structural anchor added | = FINAL-LG (never chosen by inner CV) | = | 1/4 | 0.50 | 0.33 | 0.123 | — |
| A5 everything combined (training-chosen) | 8/9/0/5 ✗ | 13/3/0/9 ✓ | 2/4 | 0.67 | 0.57 | 0.134 | Seeds 1/1 or 2/1. Drops: 2/2, 1/1, 2/3 |
| LG-D (FINAL-LG + DROMIC displacement) | = FINAL-LG ✓ | = ✓ | 1/4 | 1.00 | 0.40 | 0.123 | Seeds 1/0. Drops: 2/1, 2/4, 2/2 |
| HYB (FINAL-LG level + structural ranking) | 8/5/0/9 ✗ | 8/2/5/10 ✗ | 1/4 | 0.33 | 0.29 | 0.152 | — |
| ATTR scored on the absolute label | 8/12/0/2 ✗ | 12/8/1/4 ✗ | 4/4 | 0.33 | 0.50 | 0.236 | — |
| Persistence (baseline) | 8/9/0/5 ✗ | 12/5/1/7 ✓ | 4/4 | 0.25 | 0.40 | 0.253 | — |

✓ = all 8 thresholds met in that round.

**Earlier candidates.** DELTA, TRAJ, DELTA_TRAJ, ET, SA, ETMIX, CF, STACK, RATE_SQRT, BASE, IMPUTE, MIND, RIMP, DROPGAP, COMP, CAP, VAR, CONV and the anchor-shrinkage arms are in `../aiPHeed_final_model_optimization_20261113/evidence/OPT_per_round_L1.csv`. None passes 2021.

**Why FINAL is selected**
- **Rolling-origin selection:** chosen only from 2018 + 2019 out-of-sample forecasts, it prefers FINAL-LG / FINAL over every tuned arm (log loss 0.434 vs 0.435–0.465). FINAL-LG and FINAL are identical in 2018/2019.
- **2021 tie-break:** where they differ (2021 only), FINAL has one fewer false alarm and is better on your listed priorities (F1, precision, balanced accuracy, accuracy).
- **What FINAL-LG does better:** prevalence estimates (pooled error −0.38 pp, significant). It stays a sealed challenger.

**Why the arms that find 2 of 4 in 2021 are not selected.** A3 and A5 lower the threshold or reweight classes using training data only, but they break 2018 precision (6 and 9 false alarms). That is exactly the trade-off the brief forbids.

## 5. Why 2021 cannot meet recall, F1 and balanced accuracy (evidence, not assumption)

1. **Ranking, not threshold.** Even a threshold tuned on the 2021 answers fails for every model, including persistence. Among the eight provinces that started 2015 at 64 % or more, every model separates HIGH from LOW at about chance (AUC 0.47–0.63).
2. **The distinguishing 2021 pattern cannot be learned from history.**
   - Masbate and Occidental Mindoro stayed HIGH after the 2019–2020 typhoons. In every earlier transition, typhoon exposure went with relative improvement.
   - Sarangani and North Cotabato, the poorest of the group, improved most, against the confirmed poverty rule.
   - DROMIC displacement and assistance do not separate them either: the LOW neighbours had similar displacement.
3. **Four positives.** A model with FINAL's true pooled skill passes the 2021 count thresholds 27 % of the time, and all three rounds 14 %. Observed 2021 recall of 1/4 has a 95 % interval of [0.006, 0.81].

## 6. Stability, reproducibility and leakage

| Check | Result |
|---|---|
| Seeds | FINAL: all five seeds give 2021 1/0/3/21; pooled accuracy 0.847–0.861 |
| Training-round removal | 2021 recall 1/4–3/4. Not stable, because 4 positives make each province decisive |
| Reproduction | An independent rerun of FINAL's live pipeline reproduces all 25 official sealed probabilities (max \|Δ\| 5e-5; `../aiPHeed_final_seals_20261113/evidence/REPRO_official_FINAL.json`). FINAL-LG refit reproduces the stored FINAL-LG exactly (Δ 0.0) |
| Leakage | 110 FINAL fits: every training round released ≥ 6 quarters before the forecast; test round never in training (0 violations). Every DROMIC value comes from a report dated before its cut-off (test-checked). Tuning choices inside training data only; cross-arm selection uses only 2018/2019 for the 2021 fold |
| Synthetic data | None |
| Evaluation status | 2018/2019/2021 are **historical test** rounds, viewed many times during development. These results are **retrospective, not independent validation**. Independent validation = scoring the sealed forecasts on the next FNRI provincial round |

## 7. Backend implementation, artifacts and tests

**Model code:** `C:\Users\admin\aipheed_hcw\backend\app\hcw\final_engine.py`, with live rows via `app/hcw/serve.py` and inputs via `app/hcw/inputs.py`.
- Unit tests `tests/unit/test_hcw_final_engine.py`: **5/5 pass** (this session).
- `app/hcw` is untracked in git; committing it needs approval.

**Completion tests:** `tests/test_final_completion.py`, **12/12 pass**. They cover:
- official seal hash;
- independent reproduction;
- experimental seal hashes;
- FINAL's confusion matrices and pooled Brier / AUC / PR-AUC recomputed from stored predictions;
- release-lag leakage record;
- DROMIC publication dates before every cut-off.

**Seals** (none served):

| Seal | sha256 | Content |
|---|---|---|
| FINAL (official) | `80b20aed…` | 25 province-quarters, all LOW |
| FINAL-LG (experimental) | `1b341560…` | 25 rows, all LOW, p ≤ 0.053; projected share 22–35 % |
| ATTR (experimental, above-national label) | `f4d73ef3…` | All five provinces not above national, p 0.19–0.34 |

**Study folders** (11-13; each has a locked protocol and a HASHES manifest):
- `aiPHeed_final_model_optimization_20261113`
- `aiPHeed_final_reformulation_20261113`
- `aiPHeed_final_detection_20261113`
- `aiPHeed_final_dromic_20261113`
- `aiPHeed_final_tuning_20261113`
- `aiPHeed_final_seals_20261113`
- this folder.

Raw DROMIC downloads are kept in the session scratchpad (untrusted data), not in the repository.

## 8. Decision

| Question | Answer |
|---|---|
| Strongest completed model | FINAL (unchanged): 8/8 in 2018, 2019 and pooled; 5/8 in 2021 |
| All thresholds met in every round? | **No.** 2021 recall 0.25, F1 0.40, BA 0.63 are below threshold, and no defensible method changed that |
| Better than FINAL-LG? | On classification thresholds, yes (2021 precision 1.00 vs 0.50). FINAL-LG estimates prevalence better. Both are sealed |
| Ready for production replacement? | Nothing replaces FINAL. FINAL remains the official model; deployment and any commit or push of these artifacts need owner authorization |
| What would fix 2021 | A new FNRI provincial HFIAS round to score the seals, and provincial post-2019 shock data with a historical counterpart. That rules out SAP; DROMIC needs a pre-2016 provincial assistance series, which is not published |
