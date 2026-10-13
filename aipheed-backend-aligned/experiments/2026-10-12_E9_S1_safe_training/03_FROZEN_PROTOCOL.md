# E9 Frozen Protocol: S1 Targets, Guarded Inputs, Walk-Forward Comparison

**Frozen 2026-10-12, before any E9 model was fitted.** The runner refuses to start unless this file exists, and records its SHA-256 in the run manifest. Any later change is a recorded deviation.

## 1. Scoring formula (S1, unchanged)

Source: `app/ml/features/risk_score_v2.py`, adopted in E6 (`REVISED_SCORING_REPORT.md` §C) and kept in E7.

**stress(p, t) = SWS_t + 2 × (food_cpi_yoy(p, t) − mean over the five provinces of food_cpi_yoy(t))**

- SWS_t: mean of the quarter's definition-A Balance-Luzon rounds.
- Missing input → NaN (never 0).
- Regional mean only when all five provinces are present.
- Only complete quarters are labels.

**Event: HIGH if stress > τ0** (strict).

**τ0** = median stress of the complete quarters whose labels were published before **2023-10-01**, the first test origin (`reference_threshold`, ≥ 8 quarters). The run stops if τ0 differs from the recorded 10.843 by more than 0.001. **The approved 14.345 uses labels through 2025-Q4, so it is leakage-affected on these test quarters and is not used for evaluation.**

## 2. Data (guard-enforced; `runner/guard.py`)

**Allowlist (SHA-256 pinned; the run stops on any mismatch):**

- aligned `labels.parquet` (used only to cross-check targets);
- `psa_indicators.parquet`;
- `features_fused.parquet` (columns: unemployment, poverty, headline CPI, food-minus-headline only);
- the 2025 SWS supplementary CSV;
- the CPI release-date CSV;
- the feature-eligibility CSV;
- `config/governing_model.json` (read at import).

**How the parquet files are read:** column-projected, with the read-time row filter `quarter <= 2025-Q4`. **No row after 2025-Q4 is ever returned.** Pre-2021 rows are dropped (study window). All other project data, production files, databases, models, transcripts and memory are blocked, as are `sqlite3` and `subprocess`.

**Excluded inputs:**

| Input | Reason |
|---|---|
| News | Carrier files; E7 news sufficiency 0/100 |
| Rice price | 3 residual forward-filled cells |
| `food_cpi` index level | No approved 2026 source, so a model needing it could not be used prospectively |
| Fuel, FX, remittances, typhoons, rain, ENSO | Their zero-fill correction needs blocked source tables |

An exact 0.0 in unemployment, headline CPI or poverty is treated as missing, because it is an impossible value. Counts are recorded.

**S1 targets** are computed from components:

- SWS values come from the code registry (`sws_rounds`, definition-A rounds, quarter ≤ 2025-Q4);
- provincial food CPI YoY comes from `psa_indicators`.

Cross-check against `labels.parquet` `stress_score`: the run stops if the maximum absolute difference exceeds 0.001.

## 3. Timing (development protocol; the reused helpers read only allowlisted CSVs)

**Origin** = start of the target quarter T.

| Input | Value at origin | Date status |
|---|---|---|
| SWS | Latest round published before the origin | Verified or verified-single |
| `sws_change` | Last round minus the previous round | Same |
| `sws_age` | Quarters between T and the SWS round | — |
| Provincial CPI features | Reference quarter T−2. Available only if the final-month release date (national + 14 d) is before the origin. `cpi_rel` requires all five provinces. `cpi_dev` = YoY(T−2) − mean YoY(T−3…T−6), with at least 2 quarters. | Proxy (unverified), except 2024-Q4 |
| Headline CPI, food-minus-headline | T−2 and T−3, by the national release date | Verified or schedule |
| Unemployment | T−2, available at the quarter end + 45 days | Schedule (unverified) |
| Poverty | Survey vintage released before the origin: 2021 survey on 2022-08-15; 2023 survey on 2024-08-15. The 2018 survey is stored in pre-2021 rows, so it is unavailable (NaN). | Documented release |
| `last_published_stress` | Latest complete label quarter < T published before the origin (Rule L1) | Proxy (via CPI) |
| Training labels | Quarters < T whose labels were published before T's origin | Enforced by the label vault |

## 4. Test design

- **Test quarters:** labelled quarters with **≥ 8** eligible training quarters (expected: 2023-Q4, 2024-Q1–Q4, 2025-Q1, 2025-Q4).
- **Selection period:** test quarters ≤ 2024-Q4. **Final period:** 2025 test quarters. The final period is never used for selection.
- **Reuse:** all these quarters were already evaluated in E1–E7. **Results are exploratory**, not an independent confirmation.

## 5. Arms (fixed; no search)

**LightGBM settings for M1–M3 (classifier and regressor):**

- `num_leaves=4`, `min_child_samples=5`, `n_estimators=100`, `learning_rate=0.05`, `random_state=42`;
- monotone +1 on `last_published_stress` and `sws_hunger`;
- no class weights; NaN kept;
- training-only filter: drop a feature more than 50% missing or constant in the fold's training rows.

| Arm | Output | Definition |
|---|---|---|
| B1 carry-forward | Stress | `last_published_stress` |
| B2 regional | Stress | `sws_hunger` (latest published round) |
| B3 Eq.3 origin rule | Stress | `sws_hunger` + 2 × `cpi_rel` (T−2) |
| B4 majority | Class only | Majority class of the fold's training labels |
| M1 core | Probability + stress | `last_published_stress`, `sws_hunger`, `sws_change` |
| M2 compact | Probability + stress | M1 + `cpi_rel`, `cpi_rel_lag1`, `food_cpi_yoy`, `food_cpi_yoy_lag1`, `cpi_dev` |
| M3 expanded | Probability + stress | M2 + `poverty_incidence`, `headline_cpi`, `food_minus_headline_yoy`, `food_minus_headline_yoy_lag1`, `unemployment_rate` |

**Classification:**

- Probability arms: HIGH if p ≥ 0.50, LOW if p < 0.50 (`final_classification`).
- Stress arms: HIGH if predicted stress > τ0 (S1 `classify`).

**INSUFFICIENT_DATA** applies, identically for every arm, when:

- a required input is missing (`last_published_stress`, `sws_hunger`, `cpi_rel`, `food_cpi_yoy`); or
- `sws_age` > 3; or
- there are fewer than 8 training quarters; or
- the training labels contain one class (probability arms only).

**Calibration (E6 rule):** Platt scaling only if a training-only inner walk-forward yields ≥ 8 out-of-fold quarters and ≥ 10 rows per class. Otherwise probabilities are **uncalibrated** and labelled so.

**Label vault:** a fold can read only labels permitted by Rule L1. Test-quarter outcomes are revealed only after `predictions.csv` is written and hashed.

## 6. Metrics (common evaluable rows)

| Output | Metrics |
|---|---|
| Event (all arms) | Accuracy; balanced accuracy (undefined if a true class is absent); per-class precision, recall and F1; confusion matrix; true and predicted class distributions |
| Probabilities only | Brier. ROC-AUC and PR-AUC only if each true class has ≥ 5 rows. |
| Stress arms | MAE; RMSE; regional-level error; within-quarter concordant pairs and Spearman (ranking by **predicted stress**); predicted vs true spread |

**Breakdowns:** by quarter and by province.

**Uncertainty:** quarter-cluster bootstrap (2,000 draws, seed 42) of per-quarter differences vs B1. Counts of independent quarters and of HIGH and LOW cases are reported.

## 7. Selection rule (on the selection period only)

1. Order by simplicity: B1 → B2 → B3 → M1 → M2 → M3 (stress outputs).
2. Start from B1. Move to the next arm only if its MAE is ≤ 0.90 × the current arm's MAE **and** it beats the current arm in ≥ 3 of the 5 selection quarters.
3. The event classification is reported but not used for selection: the true LOW class is expected to be rare.
4. The final period is reported for every arm without re-selection.

## 8. Diagnostics

- Label distribution by year.
- Regional-only agreement.
- Variance from the regional vs provincial component.
- **α sensitivity** (descriptive): α ∈ {0, 1, 2, 2.74, 4}, with τ recomputed as of 2023-10-01.
- Predicted vs true HIGH share.
- Feature-filter drops.
- Importance stability.
- In-sample vs out-of-sample error.
- INSUFFICIENT_DATA reasons.
- Province spread.

## 9. Stop rules

The run stops on any of:

- a hash mismatch;
- a guard denial;
- τ0 mismatch;
- target cross-check mismatch;
- a quarter after 2025-Q4 appearing anywhere;
- non-deterministic predictions across two runs.

## 10. Not claimed

- A validated food-insecurity probability.
- Province-level or municipal food-insecurity truth.
- Blind-test performance.
- That 75% accuracy is meaningful when one class dominates.
