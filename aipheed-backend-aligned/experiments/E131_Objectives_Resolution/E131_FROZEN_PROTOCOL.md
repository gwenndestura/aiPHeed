# E131 frozen protocol: resolving E130 and testing every thesis objective

**Freeze.** This protocol was frozen **before** any E131 result was computed. Its SHA-256 is in `runner/PROTOCOL_SHA256.txt`.

**Scope and starting point.**
- Branch `aiPHeed/corrected-data-pipeline`; starting commit `a0f0c2f`.
- Offline research only. No production, dashboard, FIRI v2 or FIRI3 change. Nothing pushed.

## 0. Why E131 differs from E109–E114, E128 and E130

| Earlier work | What it tested | What E131 adds |
|---|---|---|
| E109–E113 (SWS levels, 4 areas, 2021+) | MAE and Brier against persistence; quarter-start issue | **The owner's numerical-agreement criterion** (≥ 75 % within a measurement-based tolerance), and N1–N7 at the dashboard's operational leads under both issue policies |
| E110 / E111 / E113 smoothers | Local-level and ETS fitted freely | **Measurement-aware** local-level models, with observation noise fixed to each round's published sampling error (not fitted to outcomes) |
| E113 / E128 covariates | CALABARZON CPI only, or regional and national series on the Balance Luzon target | **Area-level CPI** (food, rice, food relative to all items) for all 4 areas, plus the other groups, on a panel large enough for N1 |
| E130 provincial gate | Target availability | **A price-versus-income decomposition** of provincial food deprivation, from FIES 2023 microdata and PSA's official food thresholds (the owner's CPI questions), plus the stability of provincial patterns across PSA rounds |

**Data status.** All SWS 2021–2026 values have been seen in earlier experiments. **The walk-forward results here are therefore development evidence.** The confirmatory test is the prospective seal (§9).

## 1. Target (measured food insecurity)

| Item | Definition |
|---|---|
| y(a, q) | SWS involuntary hunger, % of families, area a ∈ {Metro Manila, Balance Luzon, Visayas, Mindanao}: the mean of the non-commissioned rounds of quarter q, 2021-Q2 … 2026-Q3 (`E110_Hunger_Generalization/data/sws_area_rounds.csv`) |
| Sampling SE of round i | n_i = 0.9604 / (MOE_i / 100)², the simple-random-sample size implied by the published 95 % margin (BL margin for Balance Luzon, the "other areas" margin otherwise; 6 if missing). SE_i = 100 √(p_i (1 − p_i) / n_i), with p_i the round's own estimate. |
| Quarter SE | SE(a, q) = √(Σ SE_i²) / k for k rounds |
| **Tolerance (primary)** | **tol(a, q) = 1.645 × SE(a, q)**, the reference's own 90 % sampling half-width (E130 §4 principle). Uses the observed p, not 0.5, and no design-effect inflation, so it is not generous. |
| Tolerance sensitivity (information only) | 0.5× and 2× tol; and the SE implied by the published margin at p = 0.5 |

## 2. Leads and issue policies

| Item | Definition |
|---|---|
| Operational Lead k | Target = D + k − 1, where D is the dashboard quarter (`backend/app/quarterly/target.py`). Lead 2 = the dashboard target. |
| **P-DASH (primary)** | Issue at 00:00 on the first day of D. Information = rounds published strictly before the issue date. |
| P-REL (secondary) | Issue on the day after the last round of quarter D − 1 is published, if that falls within D; otherwise there is no issue that quarter. Information = rounds published before that day. |
| Partial quarters | Count as observed with the rounds published at the time |
| Evaluation dashboard quarters | Every D from 2021-Q3 to 2026-Q4 whose target has an observed value, with at least 8 observed training target quarters for the model |

## 3. Models

All models are fitted on data available at the issue date only. Training pairs (origin s, target s + k) need the target **published before the issue date**. Rows are pooled across the 4 areas.

| Id | Model | Notes |
|---|---|---|
| PERSIST | Latest available quarter value of the area | Baseline |
| CLIM | Expanding mean of the area's available quarter values | Baseline (climatology) |
| LLM | Local level per area: observation variance = SE(a, q)² (fixed); level-noise variance σ²_η by pooled maximum likelihood on the available data | Forecast = filtered level. Predictive variance = P + h σ²_η + SE²_target, with SE_target the median of the area's past SEs. |
| DLLM | Damped local level: μ_t − m_a = φ(μ_{t−1} − m_a) + η, with m_a the expanding area mean; φ ∈ [0, 1] and σ²_η by pooled maximum likelihood | Forecast = m_a + φʰ (μ̂ − m_a), h = information horizon |
| RIDGE-H / LGBM-H | Ridge / LightGBM on history features (H) | — |
| RIDGE-ALL | Ridge on H + all five groups | Linear baseline (continuous counterpart of logistic regression) |
| **LGBM-ALL** | LightGBM on H + all five groups | **Proposed model** |
| PSA-ONLY | Ridge on H + official-statistics groups (A, C, E, V) | Baseline |
| NLP-ONLY | Ridge on H + news (N) | Baseline |

**Learned models** predict Δ = y(target) − y(latest).
- **H (history):** y_latest; LLM level; area expanding mean; information horizon h; latest change; area code.
- **LightGBM settings:** fixed, with no outcome-based tuning (the data are too few for inner CV). num_leaves 4, max_depth 2, learning_rate 0.05, n_estimators 100, min_child_samples 8, reg_lambda 5, bagging 0.8 every iteration, feature_fraction 0.8, seed 131. Seeds 131–135 for sensitivity.
- **Ridge:** alpha 10 on training-standardized features; training-median imputation.
- **Minimum** 20 training rows; otherwise no forecast is issued.
- **Intervals** for learned models: 80 % interval = prediction ± (the 80 % quantile of absolute out-of-fold training residuals from earlier issues, falling back to in-sample residuals), widened by SE_target in quadrature.

## 4. Trigger groups (point-in-time; availability rule in brackets)

| Group | Features | Geography |
|---|---|---|
| A Market | Area food-CPI YoY; area rice-CPI YoY; area relative food price (food ÷ all-items index), as level and as 4-quarter change. Built from the OpenSTAT `0012M4ACP22` regional index, monthly 2021-01 … 2026-09 [day 10 of m + 1]. YoY only from 2022-01 (no pre-2021 base). | Area = unweighted mean of its regions (stated limitation) |
| C Climate | ONI, El Niño flag, PAR typhoons (E119 regional dataset, as of quarter start) | Global / national |
| E Employment and OFW | Unemployment rate and change; remittance decline (E119 regional dataset) | Regional / national |
| N News | GDELT shares (E119 regional dataset) | National |
| V Poverty | Area poverty incidence among the population, latest PSA round published before the issue date (owner workbook Table 2: 2021/2023 rounds dated 2024-08-15; 2025 round dated 2026-08-24) | Regional, aggregated to areas |

The FIRI v2 families are mapped in the trigger report:

| FIRI v2 families | Used as |
|---|---|
| A1, A2, A3 | A |
| C1, C2 | C |
| C3, C4 | Not area-level (stated) |
| E1, E2 | E |
| N1 | N (GDELT; FSSI is provincial only) |
| V1 | V |
| H1 | H |

## 5. Evaluation

**Metrics,** per model × lead × policy:
- MAE, RMSE and R²;
- **share within tolerance;**
- direction accuracy;
- 80 % coverage;
- per area, per level tercile, and on sharp increases (Δ > 2 SE).

**Reliability:** N1–N7 (E130 `numeric_reliability`). The N3 baselines are PERSIST, CLIM, PSA-ONLY, NLP-ONLY and RIDGE-ALL; a model is never compared with itself.

**Maximum reliable lead:** consecutive leads from Lead 1.

**Ablation:** LGBM-ALL and RIDGE-ALL each without A, C, E, N and V, at Leads 1–2 under P-DASH. Reported as ΔMAE and Δwithin. Groups are never forced to contribute.

**Overfitting checks:**
- training against out-of-sample MAE for learned models;
- seed sensitivity;
- trees with splits.

**Selection rule (fixed here).**
- The **E131 candidate** is the model with the highest Lead-2 share within tolerance under P-DASH among LLM, DLLM, RIDGE-H, LGBM-H, RIDGE-ALL, LGBM-ALL, PSA-ONLY and NLP-ONLY. Ties go to the lower MAE.
- It is "validated" only if it passes N1–N7 at Lead 2.
- Production adoption needs validation **and** owner approval.

## 6. Provincial layer (CPI questions and Objective 5)

**X3a · Price-versus-income decomposition of the 2021→2023 PFDR change.**
- **Inputs:**
  - FIES 2023 public-use file (owner's Downloads; read in place, hashed, never copied). Per-capita income = TOINC / FSIZE; population weight MEM_RFACT; province from W_REGN = 04 and W_PROV, with Quezon excluding the Lucena HUC (via RPROV).
  - PSA's official annual per-capita food thresholds for 2021 and 2023 (OpenSTAT `DB/1F/FY/0071F3DF040.px`, queried for 2021 and 2023 only).
- **Replication:** I23(T23), the 2023 incidence, compared with official 2023 PFDR.
- **Price effect:** I23(T23) − I23(T21).
- **Income effect:** the official change minus the price effect.
- **Also reported:** official threshold growth against provincial food-CPI growth (D5 rule).

**X3b · Stability of provincial patterns.** Spearman correlation and the E130 rank-stability test between rounds:
- PFDR (2021, 2023);
- poverty among the population (2021, 2023, 2025), from owner workbook Table 2.

Descriptive only. The 2025 family poverty values were seen (E130 X2).

**X3c · Provincial model-based estimates** for the seal quarters:
- **Rule:** Balance Luzon forecast (E131 candidate) × provincial relative food deprivation = EB-shrunk PFDR 2023 ÷ the Region IV-A 2023 subsistence value, with propagated uncertainty.
- **Label:** "model-based; provincial dynamics inherited from Balance Luzon; validated only at PSA survey rounds."
- **Sensitivity:** poverty-based relative risk.

## 7. Questions the provincial layer must answer (owner, 2026-10-31)

1. Why is provincial food CPI treated only as a predictor?
2. Can CPI help construct a defensible food-insecurity measurement without circularity?
3. Can independent PSA and FNRI measurements establish the target?
4. Can the available measurements support numerical forecasting at provincial level?
5. What is the strongest legitimate approach that preserves the thesis objectives?

## 8. Integrity rules

- Study window 2021+. Every file loaded must hold only 2021+ rows, except the FIES 2023 public-use file, which is in-window by construction.
- No SWS value copied into province rows as a measurement.
- CPI, poverty, FIRI v2 and FIRI3 are never targets.
- Tolerance, rules and selection are fixed here.
- Any deviation goes to `DEVIATIONS.md`; any exposure to `CONTAMINATION_LOG.md`.
- No "latest", "current" or "release" searches for PSA, BSP or SWS series.
- Local commits only.

## 9. Prospective seal (confirmatory)

| Item | Definition |
|---|---|
| Issued | 2026-10-31, with all information published by then (SWS to 2026-Q3, published 2026-10-14; CPI to 2026-09) |
| Targets | 2026-Q4, 2027-Q1, 2027-Q2 and 2027-Q3 for the 4 areas |
| Content | Every model's point forecast and 80 % interval, plus X3c provincial estimates |
| Integrity | SHA-256 recorded; never re-sealed |
| Scoring | With the §1 tolerance, as SWS publishes each quarter |
