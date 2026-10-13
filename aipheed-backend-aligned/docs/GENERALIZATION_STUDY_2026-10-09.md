# Generalization Study: Can aiPHeed Reach 75% on Unseen Quarters? (2026-10-09)

**Scope:** a supplementary experiment. Production (MODEL-A, the API and the dashboard), Chapter III, the approved target and all earlier evidence are unchanged. Nothing was committed or deployed.

**Files:**

- **Experiment directory:** `experiments/2026-10-09_generalization/`
  - `PREREGISTRATION.json`: written before any model in this study was run. SHA-256 `3183c423…c453`; the script refuses to run if the file changes.
  - `results.json`
  - `P_nested_predictions.csv`
  - `fixed_config_predictions.csv`
  - `FROZEN_PROSPECTIVE_CONFIG.json`
  - `PROSPECTIVE_EVALUATION_PLAN.md`
- **Script:** `scripts/supplementary/generalization_study.py`
- **Tests:** `tests/unit/test_generalization_protocol.py`
- **Provenance:** git HEAD `eee269b`. The `aipheed-backend-aligned/` tree is untracked, so provenance rests on the SHA-256 of the config, the script and six data files, all recorded in `results.json → provenance`.

---

## Answer

**No candidate credibly meets the 75% requirement on unseen quarters.**

The pre-registered primary estimate is the nested procedure. Inside every fold it chooses a model from a fixed pool of 54 configurations using training quarters only. It scores **74.5% (41/55)** and fails all four within-period criteria.

The data cannot show that any model exceeds 75% with confidence:

- With 55 rows, a confident claim (exact one-sided 95% bound ≥ 0.75) needs **at least 47 correct (85.5%)**. Even if the true accuracy were 85%, the chance of observing that would be only 0.55.
- The five provinces in a quarter share most of their information. The effective sample is therefore about 11 quarters, which makes the requirement harder still.

**Prospective performance cannot be evaluated yet:** no labelled quarter after 2025-Q4 exists. A frozen configuration and a scoring plan are ready for when it does.

**The binding limitations, in order:**

1. **Sample size.**
2. **Label construction.** 66% of label variance lies between quarters, driven by one regional SWS figure per quarter.
3. **Feature validity.** FSSI is forward-filled in 77 of 120 cells. The commodity series after 2021 carry no province-specific information.
4. **Model performance.**

## 1. Verified baseline results

| Claim from earlier audits | Verified? | Evidence |
|---|---|---|
| MODEL-B2: 45/55 = 81.8% | Yes | `results.json → named_comparisons`; identical to the frozen predictions |
| MODEL-A and MODEL-B2 configurations differ | Yes | `training_results.json`: 12 features, MRLT 0, holdout accuracy 0.30. MODEL-B2: 47 inputs. On the strict-timing protocol, the MODEL-A configuration scores 38/55 = 69.1%. |
| Quarter-number-only model: 78.2% | Yes | 43/55, AUC 0.886, Brier 0.153 |
| Timing-valid persistence: 76.4% | Yes | 42/55 |
| 11 test quarters; the 5 provinces of a quarter share information | Yes | 19 of 47 inputs are identical across provinces in every quarter, and the label's SWS term is one regional value per quarter |
| Post-2021 commodity prices are CPI-derived | Yes, **with a correction**. The CPI used is the **Region IV-A figure copied to every province** (`cpi_full` source note). After 2021, each series is therefore a fixed province anchor × one regional factor per quarter (the within-quarter SD of the ratio is ≤ 4e-5). The earlier reports described it as a province-level CPI; it is regional. | `data_audit.cpi_full`, `commodity_post2021_ratio…` |
| Training-only label median lowers accuracy to 70.9% | Yes (MODEL-B2: 70.9%). Under the nested procedure P it gives 72.7%. | `P_with_training_median_labels` |
| No labelled quarter after 2025-Q4 | Yes | The latest SWS round on file is 2025-Q4 |
| Algorithm 4 has not met its AUC criterion | Yes (not re-run here) | `evidence/2026-10-08_optimization/algorithm4_diagnostic.json` |
| Production serves MODEL-A | Yes | `models/lgbm_best.pkl`; consistency check 39/39 |

## 2. Data leakage and feature-timing findings

| # | Potential issue | Evidence | Impact | Recommended action |
|---|---|---|---|---|
| D1 | Government series available at the forecast origin | `frame_t2` uses quarter t−1 for every government series and news from quarter t. CPI is published early in the following month. | No leakage under strict timing | Keep |
| D2 | SWS aligned to actual publication | For each of the 11 outer quarters, the SWS value used is the latest round released before the quarter began (`sws_alignment_outer`). The target quarter's round is never used. Example: 2025-Q1 uses 2024-Q2 (19.6), because 2024-Q3/Q4 were released on 2025-01-14. | Correct. Hunger shifts reach the model 1–2 rounds late. | Keep. Confirm the 4 manually entered release dates against SWS. |
| D3 | Label threshold uses the evaluation period | The global median 14.6 is computed over all 95 labelled rows, **55 of them from the outer test period** | The class boundary is informed by the test period. A training-only median gives 70.9% (MODEL-B2) and 72.7% (P). | Disclose. A change needs adviser approval (it alters the approved Eq. 3). |
| D4 | Target information encoded in features | No feature contains SWS or CPI of t+1. The largest absolute correlation of any input with the label is 0.485 (no near-copy). | No direct encoding | Keep |
| D5 | Label is mostly a quarter-level quantity | 65.8% of stress-score variance lies between quarters. SWS has one value per quarter (Balance Luzon). "SWS > 14.6" alone reproduces 82% of the labels. 7 of 19 labelled quarters are single-class. | Accuracy mostly rewards guessing the quarter's regime. Province ranking depends only on the CPI-deviation term. | Disclose. Report within-quarter AUC separately. |
| D6 | Commodity series independent? | 992/992 rows after 2021 reconstruct exactly as the 2021-Q4 price × (1 + **regional** food CPI YoY). Within a quarter the provinces differ only by a fixed 2021-Q4 anchor. | No independent price information after 2021. In MODEL-B2 they act as a constant province marker (36.5% of gain). | Keep in the governing set (removal is a methodology decision). Disclose. The ablation is in Section 6. |
| D7 | Revised or estimated values unavailable at the time | CPI is the 2018=100 series fetched in 2026 (current vintage, including rebasing and revisions). NASA POWER rainfall is a corrected reanalysis fetched in 2026. Real-time vintages were not recorded. | Training rows from before rebasing may differ from what was available then. Size unknown, probably small for YoY rates. | Limitation. For prospective quarters, archive the values as released (see the plan). |
| D8 | Forward-filled news signal | FSSI is **forward-filled in 77 of 120 cells** and zero-filled in 10 (`feature_provenance.json`). The trigger features are forward-filled in 4 cells each. | The NLP layer is stale in most province-quarters. Forward fill uses past values only, so there is no leakage, but the signal is weak. | Data-quality priority: more geocoded articles per province-quarter. |
| D9 | Leading zero-fills | 2020 values are zero for fx, fuel, Brent, typhoon, rainfall, drought and **ENSO** (20 cells each), and OFW is zero for 2020–21 (40 cells). Zero means "neutral" for ENSO and is a fake price for fuel and FX. | Training rows only (outer tests start 2022-Q4). Zeros can act as an "early period" marker. Measured rainfall exists for 2020 but is dropped by the PAGASA merge. | Implementation fix candidate: use missing values, not 0. Not applied, because it is a production pipeline change. |
| D10 | Rice series break | 2020 retail RMR; wholesale from 2021 | Training rows only | Disclose |
| D11 | In-fold fitting of preprocessing and weights | Scaling sits inside an sklearn Pipeline. `scale_pos_weight` and `class_weight` are computed from the training labels. No imputation statistics are fitted. Unit tests check all three. | No leakage | Keep |
| D12 | Repeated use of the 55 outer rows | MODEL-A, MODEL-B, E0–E7, the robustness and overfitting audits all used these rows | Any configuration picked after those runs is selection-optimistic | This study's primary estimate is the pre-registered nested procedure. Unbiased confirmation needs future quarters. |

## 3. Experimental protocol and exact configurations

Every element below was **fixed in `PREREGISTRATION.json` before running**:

- **Frame:** strict-timing `frame_t2`. **Target:** Eq. 3, threshold 14.6, unchanged. **Horizon:** k = 1.
- **Outer folds:** expanding window, at least 8 target quarters, 11 outer quarters (2022-Q4 to 2025-Q4, 55 rows). Provinces are always kept together by quarter.
- **Inner folds:** walk-forward inside each outer training set, at least 5 inner target quarters. Score is mean inner quarter accuracy. Seed 42; cut-off 0.50.
- **Pool:** 54 configurations, listed simplest first: feature set (12 → 42 → 47) × family (logistic → tree → LightGBM) × complexity × weighting.

| Feature sets | Families and settings |
|---|---|
| `eq5_12` (Equation 5, MODEL-A's set) | L2 logistic regression, standardised inside the fold: C ∈ {0.01, 0.1, 1, 10} × class_weight ∈ {none, balanced} |
| `gov47_no_commodity` (42) | Decision tree: depth ∈ {1, 2, 3}, min leaf 5 × class_weight ∈ {none, balanced} |
| `gov47` (MODEL-B2's set) | LightGBM: defaults, or small (4 leaves, min child 10, 100 trees, lr 0.05) × {none, `scale_pos_weight`} |

- **Primary estimand:** outer accuracy of **P**, which picks the top inner-validation configuration in each fold. Exact ties go to the earliest configuration in the pool order.
- **Pre-registered acceptance rule:**

| Criterion | Requirement |
|---|---|
| C1 Observed | P's mean quarter accuracy ≥ 0.75 |
| C2 Statistical | One-sided 95% lower bound ≥ 0.75, by **both** the quarter-cluster bootstrap and exact Clopper–Pearson |
| C3 Beats baselines | Better than timing-valid persistence **and** clock-only (mean quarter difference > 0, bootstrap 5th percentile > 0) |
| C4 Stability | Leave-one-year-out accuracy ≥ 0.75 for every year |
| C5 Prospective | Accuracy on quarters after 2025-Q4 with the frozen configuration (not evaluable now) |

- **Verdicts:**
  - MEETS_WITHIN_PERIOD = C1–C4 all pass.
  - OBJECTIVE_ACHIEVED = MEETS_WITHIN_PERIOD plus C5.
- **Feasibility, computed before running:** at least 47/55 correct is needed for C2b. The chance of reaching it is 0.20, 0.55 and 0.91 if the true accuracy is 0.80, 0.85 and 0.90 (optimistic, since it assumes independent rows).

## 4. Candidate comparison

### 4.1 Primary result (the nested procedure P)

| | Correct | Accuracy | Precision (w) | Recall (w) | F1 (w) | ROC-AUC | Brier | Within-quarter AUC | Confusion [[TN, FP], [FN, TP]] |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| **P (nested, 54 configurations)** | **41** | **0.745** | 0.798 | 0.745 | 0.746 | 0.788 | 0.200 | 0.56 | [[20, 2], [12, 21]] |
| P restricted to logistic | 40 | 0.727 | | | | 0.814 | | 0.71 | |
| P restricted to tree | 37 | 0.673 | | | | 0.789 | | 0.19 | |
| P restricted to LightGBM | 43 | 0.782 | | | | 0.820 | | 0.57 | |

**What P chose:**

| Outer folds | Configuration chosen | Inner ties at the top |
|---|---|---|
| 2022-Q4 to 2023-Q3 | 12-feature logistic, C = 0.01 | 8–13 configurations tied; broken by pool order |
| 2023-Q4, 2024-Q1, 2024-Q2, 2025-Q4 | 47-feature LightGBM with `scale_pos_weight` (MODEL-B2) | Unique winner |
| 2024-Q3, 2024-Q4, 2025-Q1 | 42-feature logistic, balanced | 2–3 tied |

The LightGBM-only procedure (78.2%) is shown for description only. Choosing it now would select on outer results.

### 4.2 Named comparisons (same 55 rows)

| Model | Correct | Accuracy | F1 | AUC | Brier | Within-quarter AUC | 2022 / 2023 / 2024 / 2025 |
|---|---:|---:|---:|---:|---:|---:|---|
| MODEL-A configuration (12, LightGBM default) | 38 | 0.691 | 0.688 | 0.758 | 0.222 | **0.79** | 0.80 / 0.75 / 0.55 / 0.80 |
| MODEL-B2 (47, LightGBM `scale_pos_weight`) | 45 | 0.818 | 0.820 | 0.828 | 0.167 | 0.63 | 0.80 / 0.90 / 0.70 / 0.90 |
| Clock only | 43 | 0.782 | 0.784 | 0.886 | **0.153** | n/a | 0.80 / 0.75 / 0.75 / 0.90 |
| Timing-valid persistence | 42 | 0.764 | 0.766 | n/a | n/a | n/a | 0.80 / 0.80 / 0.65 / 0.90 |
| Training-majority class | 22 | 0.400 | 0.229 | n/a | 0.277 | n/a | 0.80 / 0.75 / 0.10 / 0.10 |

### 4.3 All 54 configurations at fixed settings (descriptive; `fixed_config_predictions.csv`)

- 12 of 54 reach 0.75 or higher. The median is **0.691** and the range is 0.436–0.818.
- Two configurations tie at the top with 45/55:
  - 42-feature logistic, C = 0.1, balanced: AUC **0.899**, within-quarter AUC **0.79**;
  - MODEL-B2.

**Picking either one now would be selection on the outer test set**, which is the forking-paths problem the pre-registration exists to prevent. The logistic model is recorded as a **hypothesis for prospective testing**, not as a result.

## 5. Fold-by-fold and quarter-level results (primary P)

| Quarter | 22-Q4 | 23-Q1 | 23-Q2 | 23-Q3 | 23-Q4 | 24-Q1 | 24-Q2 | 24-Q3 | 24-Q4 | 25-Q1 | 25-Q4 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| HIGH (of 5) | 1 | 0 | 1 | 1 | 3 | 4 | 5 | 4 | 5 | 5 | 4 |
| P accuracy | 0.8 | 1.0 | 0.8 | 0.8 | 0.8 | 0.6 | **0.4** | 0.8 | 0.6 | 0.8 | 0.8 |
| MODEL-B2 | 0.8 | 1.0 | 0.8 | 1.0 | 0.8 | 0.6 | 0.4 | 0.8 | 1.0 | 1.0 | 0.8 |
| Timing-valid persistence | per `outer_test_rows_55.csv`; 0.80 / 0.80 / 0.65 / 0.90 by year | | | | | | | | | | |

- P's accuracy by year: 0.80 / 0.85 / 0.60 / 0.80.
- Leave-one-year-out: 0.74 (without 2022), 0.69 (without 2023), 0.83 (without 2024), 0.73 (without 2025).
- **Effective sample: 11 quarters.** Rows within a quarter share SWS, ENSO, fuel, FX, unemployment and OFW inputs, plus the label's SWS term.

## 6. Feature ablation (descriptive, same protocol)

| Feature set | n | LightGBM `spw` correct | AUC | Within-quarter AUC | Logistic (C = 0.1) correct | AUC | Within-quarter AUC |
|---|---:|---:|---:|---:|---:|---:|---:|
| gov47 | 47 | 45 | 0.828 | 0.63 | 38 | 0.877 | 0.64 |
| gov47 without commodity | 42 | 40 | 0.782 | 0.60 | 42 | 0.887 | **0.79** |
| Without price levels | 33 | 33 | 0.618 | 0.63 | 44 | 0.880 | 0.68 |
| Without any price feature | 24 | 42 | 0.784 | **0.82** | 44 | 0.888 | 0.71 |
| Quarter-common features only (20) | 20 | 36 | 0.720 | n/a | 38 | 0.815 | 0.38 |
| Province-varying features only | 27 | 40 | 0.774 | 0.60 | 31 | 0.741 | 0.71 |
| eq5_12 | 12 | 41 | 0.789 | **0.82** | 31 | 0.707 | 0.68 |

**What this shows:**

- **Removing the CPI-derived commodity series** costs LightGBM 5 rows. It does not hurt the logistic model, which improves its within-quarter ranking.
- **MODEL-B2's commodity dependence is model-specific.** It reflects the trees using the fixed province anchors, not real price information.
- **Province-specific information exists but is weak and model-dependent.** Within-quarter AUC ranges from 0.60 to 0.82 across reasonable feature sets.
- **The models that rank provinces best within a quarter are not the most accurate overall.** These are the 12-feature LightGBM (MODEL-A's set) and LightGBM without price features (both 0.82). For DA's use (which provinces first), within-quarter AUC is the more relevant measure.

## 7. Comparison against persistence and the quarter-only baseline

Paired comparison, with a 10,000-draw quarter-cluster bootstrap over 11 quarters:

| Comparison | Mean quarter difference | 95% CI | Rows model-only / reference-only right | McNemar p | C3 pass? |
|---|---:|---|---|---:|---|
| P vs timing-valid persistence | −0.018 | [−0.146, +0.091] | 5 / 6 | 1.00 | No |
| P vs clock only | −0.036 | [−0.200, +0.127] | 4 / 6 | 0.75 | No |
| MODEL-B2 vs timing-valid persistence (descriptive) | +0.055 | 5th percentile −0.018 | 6 / 3 | 0.51 | No |
| MODEL-B2 vs clock only (descriptive) | +0.036 | 5th percentile −0.091 | 5 / 3 | 0.73 | No |

No model is shown to beat persistence or the quarter-only reference. A non-significant difference does not show equivalence: the data cannot separate them.

## 8. Uncertainty and limitations

**Primary procedure P (41/55):**

- Quarter-bootstrap one-sided 95% lower bound: **0.673**.
- Exact one-sided 95% lower bound: **0.631**.

**MODEL-B2, for reference (45/55, descriptive):** lower bounds 0.727 and 0.711. Even the best observed configuration fails C2.

**Limitations:**

- 11 effective temporal units.
- 7 of 19 labelled quarters are single-class.
- The label threshold is fitted on the full period.
- FSSI is mostly forward-filled.
- Commodity series are CPI-derived and regional.
- CPI and rainfall are current vintages, not as-released values.
- The 55 rows were reused across many earlier analyses.
- Inner validation in early folds has 3–5 quarters, producing many exact ties. Those ties were broken by the pre-declared order; another order could change the early folds. That alternative was not tried, because trying it would be selection.

## 9. Does any candidate meet the predefined acceptance rule?

| Criterion | P (primary) | MODEL-B2 (descriptive only) |
|---|---|---|
| C1 Observed ≥ 0.75 | **FAIL** (0.745) | pass (0.818) |
| C2 Lower bound ≥ 0.75 | **FAIL** (0.673 / 0.631) | fail (0.727 / 0.711) |
| C3 Beats persistence and clock | **FAIL** | fail |
| C4 Every leave-one-year-out ≥ 0.75 | **FAIL** (0.69–0.83) | pass (0.77–0.89) |
| C5 Prospective | not evaluable | not evaluable |
| **Verdict** | **FAILS** | OBSERVED_ONLY |

**The objective is not achieved.** The strongest defensible candidate is **MODEL-B2 for prospective testing**:

- The pre-registered procedure, run on all data through 2025-Q4, selects MODEL-B2's exact configuration as its unique top choice (inner score 0.814). That choice is frozen in `FROZEN_PROSPECTIVE_CONFIG.json` (SHA-256 `4a33609b0e79…`).
- Its 81.8% is an observed, selection-optimistic figure. It is not statistically above 75% and does not beat the simple references.

**Main limitations, ranked:**

1. Sample size (11 quarters; feasibility power 0.20–0.55).
2. Label construction (quarter-dominated SWS term; full-period threshold).
3. Feature validity (stale FSSI; CPI-derived commodity; zero-filled leading quarters).
4. Model choice (secondary; many models perform similarly).

## 10. Next steps and decisions for the adviser

**Next steps (none applied):**

1. **Prospective evaluation (the only route to C5).** Follow `experiments/2026-10-09_generalization/PROSPECTIVE_EVALUATION_PLAN.md`: score the frozen configuration on 2026-Q1 onward as SWS publishes each round, with values archived as released. At about 5 rows per quarter, **roughly 8–12 additional quarters** would be needed before C2 becomes realistic.
2. **Pre-register the hypotheses this study generated** for prospective comparison against the frozen model, not for selection now:
   - logistic regression without commodity (42 features, C = 0.1, balanced);
   - LightGBM without price features.
3. **Data-quality fixes**, each a production pipeline change that needs authorization:
   - missing values instead of leading zeros (ENSO, fuel, FX, rainfall);
   - restore measured 2020 rainfall;
   - more geocoded articles per province-quarter to reduce FSSI forward-fill.

**Decisions that need adviser approval:**

| # | Decision |
|---|---|
| A1 | How the 75% requirement is assessed. A point estimate on 55 reused rows (MODEL-B2 81.8%; P 74.5%) is different from demonstrating > 75% with confidence; the data support neither the confident claim nor superiority over persistence. |
| A2 | Whether to keep the full-period global-median threshold (Eq. 3), or adopt a training-only threshold. Adopting it would change the target. |
| A3 | Whether the CPI-derived commodity series (region-level CPI × fixed province anchor) may remain as "commodity price" features. |
| A4 | Whether to report within-quarter (province-ranking) AUC as a separate performance measure for the DA use case. |
| A5 | Whether to authorize prospective evaluation and the pipeline extension beyond 2025-Q4. That extension changes the approved 2020–2025 window. |
| A6 | Earlier, still open: the 45-vs-12 wording (R1–R5), `scale_pos_weight` vs "default LightGBM" (R6), Algorithm 4 / Section 3.4.4 (R8), and H3 (R9). |
