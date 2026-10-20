# E71 protocol: dimensional food-insecurity risk framework (frozen before any E71 computation)

**Frozen:** 2026-10-20. sha256 (LF) in `runner/PROTOCOL_SHA256.txt`.
**Branch:** `e71-food-insecurity-dimensions`, cut from `e70-objectives-completion` @ ce338e7.
**Library:** the same clean `git archive 089bdf2` export as E70 (`AIPHEED_EXP`), plus the three E70 `inputs/` parquet files.

**Evidence class.** Every quarter from 2021 to 2026-Q3 has been examined before. **No E71 historical result is held-out evidence.** E71 changes the target, so its rules are fixed here, before any E71 label, score or forecast is computed. Only the sealed 2026-Q4 and 2027-Q1 forecasts (§9) can be unseen evidence.

## 1. Conceptual basis (summary; full text in FOOD_INSECURITY_DIMENSIONAL_FRAMEWORK_AND_REDESIGN.md)

**Definition.** Food security exists when all people at all times have physical and economic access to sufficient, safe and nutritious food (World Food Summit 1996).

**Structure.**
- Four dimensions: availability, access, utilization and stability (FAO 2006).
- Following the IPC (Manual 3.1), **contributing-factor evidence** (the dimensions, vulnerability and hazards) is kept apart from **outcome evidence** (experienced hunger or food insecurity, consumption, nutrition).
- A risk index built from contributing factors is **not** an outcome. It must be validated against outcomes measured at their own geographic level.

## 2. Layers

| Layer | Content | Role |
|---|---|---|
| L1 Outcome | SWS hunger (regional, quarterly); FNRI FIES 2025 (regional, one value); PSA subsistence incidence 2021/2023 (provincial, 2 values each) | **Validation only.** Never an input to the E71 index, so the index cannot validate itself. |
| L2 Dimensions | ACCESS, AVAILABILITY, STABILITY (§3); UTILIZATION = **not observed** | Index inputs |
| L3 Vulnerability | 2021 SAE poverty (province mean), known from 2025-01-01 | Reported beside the index and used for LGU prioritization (unchanged). **Not** in the class rule, because it is static and was released after most origins. |
| L4 Integrated estimate | FIR71 = mean of the three dimension scores, plus the dimension profile | Exploratory proxy risk index |
| L5 Forecast | Lead-1/2/3 models (§7) | Forecasts of the FIR71 class |
| L6 Validation | V1–V4 (§6) | Tests whether FIR71 tracks outcomes |

## 3. Indicators

Every indicator is converted to a mid-rank percentile against the **2021-Q1 … 2022-Q4 reference rows**, pooled across provinces, with the **adverse direction** set here. This continues the E40 reference-window convention.

| Dimension | Indicator | Level | Adverse direction | Source |
|---|---|---|---|---|
| ACCESS | a1: food CPI YoY, quarter mean (3 months required) | province | higher | PSA CPI |
| ACCESS | a2: mean of unemployment rate and underemployment rate, quarter mean (≥ 2 months) | national | higher | PSA LFS |
| ACCESS | a3: OFW cash remittances YoY | national | lower | BSP |
| AVAILABILITY | v1: palay + corn production YoY (quarter tonnage vs the same quarter a year earlier) | province | lower | PSA crops |
| AVAILABILITY | v2: fish + aquaculture production YoY | province | lower | PSA fisheries |
| STABILITY | s1: tropical cyclones affecting the province in the quarter | province | higher | PAGASA |
| STABILITY | s2: PAGASA drought alert in the quarter (0/1, used as the value itself) | province | higher | PAGASA |

**Indicator rules.**
- Food-minus-headline YoY is **excluded** from the index: it re-measures the same price movement as a1. It is kept as a sensitivity variant (§8).
- A dimension score is the mean of its observed indicator percentiles. It is missing when no indicator is observed.
- **Missing values are never set to zero or to "no risk".**
- UTILIZATION has no quarterly provincial indicator in the data, so it is reported as **not observed**.

## 4. Index and class (the E71 target "FIR71")

- **FIR71(p, q)** = mean of ACCESS, AVAILABILITY and STABILITY. It is defined only when all three dimension scores exist.
- **HIGH** iff FIR71 > the 60th percentile of FIR71 over the reference rows that have all three dimensions. The 60th percentile is the E40 convention, not a choice made on any evaluation result.
- The profile is reported with each value: the three dimension scores and the dimensions above 0.75.

## 5. As-of rules

- **Training labels at origin t:** quarters q ≤ t − 1 only. Their PSA, BSP and PAGASA inputs for q ≤ t − 1 are published within quarter t, before the issue date O(t).
- **Features:** the E63 as-of feature frame, plus dimension scores from quarters ≤ t − 1.
- **SWS** is never used by the index or the models. In validation, a round counts only with its published date.

## 6. Validation (computed after the labels; criteria fixed now)

| Test | Criterion |
|---|---|
| V1 regional outcome | Spearman ρ between the quarter mean of FIR71 and the SWS hunger quarter mean (all rounds), over quarters with both. **Supported** if the quarter-bootstrap 95% CI lower bound is > 0. Also reported: sign agreement of quarter-to-quarter changes. |
| V2 provincial cross-section | Province mean FIR71 over 2023 vs PSA subsistence incidence 2023; 2022 vs 2021. Face validity only (5 units). |
| V3 collapse | Share of labelled rows where the FIR71 class equals the T43 price condition PS. Share of HIGH rows whose largest dimension is ACCESS. Leave-one-dimension-out class agreement. Report "price-collapsed" if the class equals PS on ≥ 90% of rows. |
| V4 scenarios | Synthetic unit tests, clearly marked as synthetic: the profile must distinguish the six situations of the brief. |

## 7. Forecast models (Lead h ∈ {1, 2, 3}; E63 eligible origins; targets with a FIR71 label)

| Arm | Definition |
|---|---|
| PERSIST | The last known class (q ≤ t − 1) |
| PROVCLIM | The province's share of HIGH among known labels |
| MAJ | The majority class of known labels |
| DIMFUSE | Project each indicator to t + h, then score and combine (§3–4): a1 by the base-effect CPI projection (E63 `bases_h`, m = 1.0); a2, a3, v1, v2, s2 by their last known value; s1 by the province's mean for that calendar quarter over known years. P(HIGH) comes from a logistic regression of the training labels on the projected FIR71. When the training labels have one class or fewer than 10 rows, P is the rule's 0/1. |
| LGBM (Objective 2 model) | LightGBM classifier, fixed configuration (num_leaves 4, max_depth 2, n_estimators 50, learning_rate 0.05, min_child_samples 5, reg_lambda 10, deterministic). Features: the projected and last-known dimension scores, the E63 market group, and the E63 news group. |
| LGBM−news | The same without the news features (NLP ablation) |
| LR | L2 logistic regression (C = 1, standardised on training rows) on the LGBM features |
| PSA-only LR | LR on the official-statistics features only (projected and last-known indicators, market group) |
| NLP-only LR | LR on the news features only |

**Selection rule.** The Objective 2 model is LGBM, unless DIMFUSE beats it on Lead-2 Brier (quarter-bootstrap CI upper < 0). In that case the simpler DIMFUSE is reported as the better model.

**The 80% statement (pre-specified).** It counts only if all of the following hold for the selected model at Lead 2:
- accuracy ≥ 0.80, HIGH recall ≥ 0.50 and balanced accuracy ≥ 0.70;
- Δ Brier vs PERSIST with CI upper < 0, because accuracy against a persistent proxy can come from persistence alone.

Even then it is **proxy-prediction accuracy on development quarters, not food-insecurity accuracy**, unless V1 is supported. It is never "validated" before prospective outcomes are scored.

**Statistics.** The E70 metric helpers: Wilson and quarter-cluster CIs, paired Brier bootstrap, two-sided sign test, McNemar, Holm over the four Objective 4 baselines (PERSIST, PSA-only LR, NLP-only LR, LR), ICC and effective n.

## 8. Sensitivity (reported, never used to choose)

- Thresholds P50 and P75.
- Gap instead of a1.
- Leave-one-dimension-out.
- Empirical weights from a regression of SWS hunger on the regional dimension means (exploratory, in-sample).

## 9. Prospective seal

LGBM, DIMFUSE, PERSIST and LR forecasts are sealed for 2026-Q4 (Lead 2 from 2026-Q2; Lead 1 from 2026-Q3) and 2027-Q1 (Lead 2 from 2026-Q3) before any outcome exists.
