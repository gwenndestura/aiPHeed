# E41 protocol: Lead-2 audit and a two-layer forecast (frozen before any E41 score)

**Written:** 2026-10-15, on branch `e41-lead2-audit` (cut from `label-v3-e40` @ 371b64e).
**Freeze:** the SHA-256 of this file (LF-normalized) is in `runner/PROTOCOL_SHA256.txt`. It is committed before any runner computes an E41 score. The runner refuses to run if this file changes.
**Run once:** `runner/e41_evaluate.py` is run once. A byte-identical repeat may follow. No setting is changed after results are seen. Any deviation is recorded in `DEVIATIONS.md` and labelled as such.

## 1. What is already known (Phase 1; reproduced before this protocol)

- **The ≥75% "Lead-2" figure** is P45 (the 45-candidate LightGBM, E25 `PROPOSED_lgbm_combined`) at lead 2 on target T1_A. It scored 31/35 = 0.886, but those rows were 33 HIGH and 2 LOW, and P45 got TN = 0. Always-HIGH scored 0.943 on the same rows (`2026-10-14_Model_Selection_45_vs_12/MODEL_SELECTION_REPORT.md`, per-lead table).
- **The served Lead-2 model** (E38-LGBM-NQ) scores 39/55 = 0.709 at lead 2, against persistence 0.800 and always-HIGH 0.891. This was reproduced byte-identically on 2026-10-15 (predictions sha prefix `8fdfd027c8677867`; `runs/e38_repro_20261015T095020Z`).
- **The target behind both:** T1_A/S1 (`H + 2D > τ`, τ = trailing median). It is HIGH in 89% of the E38 outer rows. Neither model beats persistence.

E41 does **not** re-score T1_A with any new model: every T1_A development date has been examined at least four times.

## 2. Targets (meaning first; no threshold is chosen from results)

| ID | Target | Level | Definition | Status |
|---|---|---|---|---|
| **T-P (primary)** | **Food price pressure** | Province | `FPP = 1[F > 4.0]`. F = the quarter mean of PSA's three **published** monthly year-on-year rates for 01.1 Food (OpenStat 0012M4ACP23). 4.0 is the ceiling of the BSP 3 ± 1% headline target. | E39 label A, frozen 2026-10-15 by E39. It is a **price-pressure** outcome, **not** food insecurity or hunger. |
| T-F | Food inflation level | Province | F (continuous, percent) | Same source |
| T-H | Hunger level | Region (Balance Luzon) | SWS involuntary hunger H, mean of the quarter's approved (definition_A) rounds; no value where no approved round exists | One value for all five provinces; it is never presented as provincial |
| T-E40 | Researcher's binary food-stress label | Province | E40 rule, frozen (`E40_SWS_CPI_Tiers/label_spec.json`, P60, sustain-2) | Scored **only** on E40 development quarters 2023-Q1..2025-Q1 (see `CONTAMINATION_LOG.md` C-1) |

## 3. Timing (Lead 2)

- **Origin** `O(t)` = 00:00 PHT on the first day of quarter t+1 (the system's quarter-start issue rule, E37/E38).
- **Lead 2** = target quarter t+2, the next calendar quarter after the one under way at the origin. This is the dashboard's forecast target. Example: O = 2026-10-01 → target 2027-Q1.
- **Information allowed at O(t)** (anything published on or after O(t) is excluded):

| Source | Allowed at O(t) | Basis |
|---|---|---|
| PSA CPI, monthly index (ACP22) and published YoY (ACP23) | months up to month 2 of quarter t | PSA national release about the 5th–7th of the next month (2026 release log); the provincial release can follow up to about 6 days later. Month 3 of t is released after O(t). |
| SWS approved rounds | `published < O(t)` (posted date in `sws_rounds.csv`) | verified posted dates |
| PSA palay and corn production; PSA fisheries production (quarterly, provincial) | quarters ≤ t−1 | quarterly reports are released about 45–60 days after the quarter ends |
| PSA LFS unemployment and underemployment rates (monthly, national) | months of quarters ≤ t−1 | LFS is released about 5–6 weeks after the reference month |
| News (E31 Google News store, province-attributed titles; E40 trigger counts) | articles of quarters ≤ t | E31 forecast rule |
| Outcomes for training or calibration | T-P/T-F of quarters ≤ t−1 (all three months published before O(t)); T-H of quarters whose approved rounds were all posted before O(t) | – |

No value dated before January 2021 is read anywhere. This is asserted at load time.

## 4. Methods (all fixed now; nothing is tuned)

### 4.1 Point forecasts of F(t+2) and the FPP decision (`1[F̂ > 4.0]`)

- **B0 majority:** the majority FPP class among the training labels published before O(t), all provinces pooled. Probability = the training HIGH rate with a Laplace correction.
- **B1 persistence:** F̂ = F(t−1), the latest complete published quarter. Probability = the hard 0/1 label.
- **B2 latest-month persistence:** F̂ = the mean of the published YoY rates for months 1–2 of t. Probability = hard 0/1.
- **B3 seasonal naive:** the label of quarter t−2, which is four quarters before the target. Probability = hard 0/1.
- **M1 base-effect projection (PRIMARY, designated now):**
  - Let m0 = month 2 of t (the latest month allowed) and I = the province's food CPI index (2018 = 100).
  - Projected `ln I(m) = ln I(m0) + g·(m − m0)` for the three target months m = m0+5, m0+6, m0+7.
  - g = the mean monthly log change of I over the latest 12 months up to m0, using only months ≥ 2021-01; at least 6 changes are required.
  - `YoŶ(m) = 100·(Î(m)/I(m−12) − 1)`, where I(m−12) is always already published. F̂ = the mean of the three.
  - The year-ago base is known exactly at the origin. Only future month-on-month price changes are unknown.
- **M1z (sensitivity):** M1 with g = 0, i.e. pure base effect with the price level held flat.
- **M2 logistic regression:** inputs F̂_M1, F(t−1), F_now, gap_now, H_last; standardized; L2 penalty with C = 1.0. Fitted at each origin on training pairs `(X(t'), FPP(t'+2))` with `t'+2 ≤ t−1`.
- **M3 LightGBM with the P45 configuration on in-window trigger features:**
  - P45's own hyperparameters (`governing_model.json`: objective binary, LightGBM defaults, `scale_pos_weight = (1−p)/p`, seed 42, deterministic, one thread).
  - P45's original 45-column matrix cannot be used: `features_fused.parquet` contains 2020 rows, and the study-window rule forbids loading it. M3 instead uses the features in §5, rebuilt from in-window official sources.
  - Same training pairs as M2.
- **M2/M3 withholding:** no forecast at an origin whose training pairs cover fewer than 8 distinct target quarters or lack either class.

### 4.2 Probabilities for M1

- M1 under a random walk with drift has the predictive distribution F(t+2) ~ Normal(F̂, s).
- `s = max(s_theory, s_track)`:
  - `s_theory = 100·σ·sqrt(50/9)`, where σ is the SD of the demeaned monthly log changes used for g. The variance of the mean of the 5-, 6- and 7-month-ahead errors is (50/9)σ².
  - `s_track` = the RMS of M1's own earlier lead-2 errors (all provinces) whose outcomes were published before O(t). It is used only once at least 4 such target quarters exist.
- `P(FPP) = 1 − Φ((4.0 − F̂)/s)`. The decision uses F̂ > 4.0, which is equivalent to P > 0.5.
- **Calibration rule:** no recalibrator is fitted. The track-record floor is the only adaptive part, and it uses earlier errors only.

### 4.3 Hunger layer (T-H)

- **H-persist:** Ĥ(t+2) = the latest approved H posted before O(t).
- **H-mean:** Ĥ = the mean of all approved H posted before O(t).
- Reported as MAE only. No classification.

### 4.4 E40 label (T-E40): component simulation

Simulate 20,000 paths at O(t), per province:
- **Food and headline log indices:** random walk with drift from m0 to m0+7. Innovations are bivariate normal with the drift and covariance of the latest 12 in-window monthly changes (at least 6).
- **Quarter YoY means:** for t+1 (m0+2..m0+4) and t+2 (m0+5..m0+7).
- **H:** H(t+1) and H(t+2) are drawn as `H_last + N(0, h·σ_H²)`, where h is the number of quarters from the last approved quarter and σ_H is the RMS of the per-quarter-scaled changes between consecutive approved quarters posted before O(t). At least 4 changes are needed; otherwise no forecast.
- **H and CPI paths are independent** (stated as an assumption).
- **The frozen E40 rule** is applied to (t+1, t+2) using the frozen thresholds.
- P = the share of HIGH paths; the decision is P ≥ 0.5. The seed is 41.
- **Baselines:** E40-label persistence (the latest E40 label available at O(t)) and always-LOW.
- **Scored targets:** 2023-Q1..2025-Q1 only.

## 5. Feature-to-trigger map (M3; also the trigger audit)

| Trigger | Features (as of O(t)) | Official source | Level | Role |
|---|---|---|---|---|
| Market / Prices | F_last, F_now, HL_now, gap_now, mom3 (food index log change, last 3 months), F̂_M1, D_now (F_now minus the five-province mean) | PSA CPI ACP22/ACP23 | Province | Contributing condition / the T-P outcome's own history |
| Hunger (SWS) | H_last, H_chg, H_age | SWS Balance Luzon | Region | Outcome-type evidence, regional only |
| Climate Stress (supply proxy) | palay_yoy, corn_yoy (quarter t−1 vs t−5) | PSA Palay and Corn production 0012E4EVCP0 | Province | Supply proxy. PAGASA climate series are not obtainable in-window here. |
| Fish Kill (supply proxy) | fish_yoy (total), aqua_yoy (aquaculture), quarter t−1 vs t−5 | PSA Fisheries production 0132E4GVFP1 | Province | Supply proxy. No official fish-kill event series (BFAR) is obtainable in-window. |
| Employment | ur_last (mean national unemployment rate of t−1), ur_yoy, under_last | PSA LFS 0021B3FKEI2 | National | Contributing condition; no provincial differentiation |
| OFW Remittance | none | BSP remittance data were not obtainable from an official in-window source in this run. P45's `ofw_remit_yoy` lives in a file with 2020 rows. | – | **Not implemented**; reported as missing, never zero-filled |
| News (all five triggers) | n_articles, hit share per trigger (climate, employment, ofw_remittance, fish_kill, market) | E31 store; E40 trigger counts | Province | Weak signal (E38: 192 of 2,820 titles match any trigger) |

**Missing values stay missing:**
- LightGBM receives NaN, never 0.
- YoY features are NaN where the year-ago quarter is before 2021-Q1.

**Trigger diagnostics (M3; secondary, not used to choose anything):**
- grouped mean |SHAP| at each origin;
- leave-one-group-out ablation on the same rows;
- single-group models;
- the correlation matrix of features on training rows.

## 6. Evaluation

- **Set S-P (primary, M1 and B0–B3):** every target quarter from 2022-Q1 to 2026-Q3 where M1 and the four baselines all forecast. Expected: 19 dates × 5 provinces = 95 rows.
- **Set S-ML (secondary):** target quarters where M2 and M3 also forecast. Expected: 2024-Q3..2026-Q3.
- **Metrics:**
  - accuracy;
  - balanced accuracy;
  - precision, recall, F1 and specificity;
  - confusion matrix;
  - ROC-AUC and PR-AUC with prevalence (probabilistic methods);
  - Brier and log loss (probabilities clipped to [0.001, 0.999] for log loss only);
  - calibration-in-the-large and slope;
  - reliability in the bands of §7;
  - per province, per year and per lead-quarter;
  - MAE and RMSE of F̂.
- **Dependence:** the five provinces of a date share a period. All CIs are date-cluster bootstrap (B = 2000, seed 41). Paired tests are per date (sign-flip, exact when there are ≤ 20 dates, otherwise 20,000 draws), with Holm correction across the four baselines.
- **Lead 1** (target t+1, the quarter under way) is reported as context with the same methods; it is not the primary horizon.

## 7. Gates for M1 (all must pass for "suitable for decision-support testing")

| Gate | Rule on S-P |
|---|---|
| G0 validity | The leakage tests pass: changing any value published on or after O(t) leaves every M1, M2 and M3 forecast at O(t) unchanged; no pre-2021 value is read. |
| G1 accuracy | Accuracy ≥ 0.75 (the lower CI bound is reported). |
| G2 not degenerate | Balanced accuracy ≥ 0.70, and HIGH recall and LOW recall both ≥ 0.60 |
| G3 beats baselines | (a) Accuracy and Brier both better than each of B0–B3 as point estimates; and (b) the per-date Brier gain over B1 persistence has Holm-adjusted one-sided p < 0.05 |
| G4 calibration | The 95% CI of calibration-in-the-large contains 0 |

**Verdicts:**
- All gates pass → **"suitable for decision-support testing (development evidence; prospective confirmation pending)"**.
- Otherwise → **"experimental"**, with the failed gates named.

Any verdict is development evidence: the CPI data of S-P have been read by earlier experiments, and E39 scored FPP at lead 2 on 7 of these dates with other models. The first blind tests are 2026-Q4 (lead 1) and 2027-Q1 (lead 2).

## 8. Operational outputs (documented rule; not tuned)

- **Price-pressure band** from P(FPP at t+2):
  - Low (P < 0.33);
  - Watch (0.33 ≤ P < 0.67);
  - High (P ≥ 0.67).
- **Hunger evidence** (regional): the latest approved H, its quarter and age, and whether H > 11.3 (the E40 frozen P60).
- **Early-warning alert candidate:** the price-pressure band is High **and** the latest approved H is above 11.3. These are two independent official signals, mirroring the E40 rule. The candidate is staged for administrator confirmation as today.
- **Data-sufficiency flags:**
  - SWS latest round older than 2 quarters;
  - M1 drift computed from fewer than 12 months;
  - production data missing;
  - fewer than 5 attributed articles.
- **Municipal level:** no municipal probability is produced. LGU rankings stay contextual (PSA SAE poverty, POPCEN), labelled as prioritization, not forecasts.

## 9. Serving rule

- E41 outputs are added to the backend **behind** `AIPHEED_LEAD2_MODEL=e41`. The default stays `e38`, so the served dashboard is unchanged.
- A separate read-only endpoint exposes the two-layer outputs with explicit score types.
- No approved frontend file is changed.
- Making E41 the default, or changing dashboard wording, needs the user's decision even if every gate passes. It changes what the dashboard's main number means (from the v1 food-stress label to price pressure).
