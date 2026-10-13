# DRAFT v2 Pre-registration: aiPHeed Exploratory Development Experiment

**Status: DRAFT v2, NOT frozen and NOT hashed.**

| Item | Value |
|---|---|
| Supersedes | `PREREGISTRATION_DRAFT.md` (v1, preserved) for the items listed in `docs/PREREGISTRATION_CONFLICT_RESOLUTION_2026-10-11.md` |
| Code | `scripts/supplementary/devprotocol_rule_l.py` (SHA-256 `c126ca68…`) |
| Tests | `tests/unit/test_devprotocol_rule_l.py` |

**Items marked [DECISION] need researcher or adviser confirmation before freezing.**

**All results of this experiment are EXPLORATORY:**

- the quarters were used in earlier studies;
- the provincial CPI publication proxy (WD1) and revised climate inputs (WD2) are in use.

It is not a final or independent evaluation, and it cannot establish 75% accuracy.

---

## 1. Primary target and horizon

- **Target concept:** Equation 3 stress = SWS Balance-Luzon hunger + 2 × (provincial food CPI YoY − five-province mean of the same quarter); HIGH if stress exceeds the median threshold. Definition A rounds, unchanged; no label rebuilt or added.
- **Operational threshold:**

  | Analysis | Threshold | Status |
  |---|---|---|
  | **Primary: "A-origin"** | τ_T, the median of stress over the training rows eligible at *T*'s origin, applied to training labels, test labels and every baseline | [DECISION C1] |
  | **Secondary: "A-global"** | The approved 14.345 (global 2021–2025 median) everywhere | Labelled as using the full-period threshold, so comparable with earlier studies but leaky |

- **Horizon:** one quarter. Forecast for *T* is issued at 00:00 on the first day of *T*.
- **Unit:** province × quarter (5 provinces; Balance-Luzon SWS shared across them).

## 2. Chronological train/test rules

- **Training set for *T*:** labelled quarters *q < T* whose label was **published** before *T*'s origin. Published means the later of the last contributing SWS round and the final-month provincial CPI release (WD1 proxy: national + 14 days unless verified; 2021 values not before 2022-02-04).
- **Minimum training history:** **at least 8 eligible labelled quarters**, following Chapter III Algorithm 3's minimum training window of 8 quarters, counted after Rule L.
- **Exploratory test quarters:** 2023-Q4, 2024-Q1, 2024-Q2, 2024-Q3, 2024-Q4, 2025-Q1, 2025-Q4. That is 7 quarters, 35 rows, with 8–15 training quarters. **2023-Q3 is excluded** (7 eligible quarters) [DECISION C3].
- **No inner validation:** nothing is selected from data.
- **2026 quarters are excluded:** 2026-Q1/Q2 are disclosed checks; 2026-Q3/Q4 belong to the separate protected protocol.

## 3. Fixed model configurations

**Seed 42; library defaults; no tuning; cut-off 0.50.**

| Role | Configuration | Inputs |
|---|---|---|
| **Primary** | MODEL-B2: LightGBM `objective=binary`, `random_state=42`, `scale_pos_weight=(1−p)/p` with *p* = HIGH share of the fold's training labels at τ_T (A-origin) or 14.345 (A-global) | `gov_c` ∩ development mask: 44 inputs |
| Comparator | MODEL-A configuration: LightGBM defaults, `random_state=42` | The 12 Equation 5 inputs |
| Comparator | Equation 3 rule | HIGH if known SWS + 2 × `cpi_rel` > threshold (τ_T or 14.345) |
| Comparator | Latest-published-label carry-forward | HIGH if the province's latest **published** stress > threshold |

## 4. Missing-data and feature-eligibility rules

- **Inputs:** from `devprotocol_rule_l.development_frame()`, the corrected window frame (K1–K4, rule W, strict timing).
- **SWS inputs:** the latest round with a known publication date before the origin, per round, including the three supplementary 2025 rounds as **inputs only**. Unknown-date rounds are excluded.
- **CPI inputs:** WD1 proxy for provincial CPI; national release date for regional CPI; WD5 cut-off.
- **Other inputs:** documented schedules (WD3).
- **Missing values stay NaN.** LightGBM uses native missing handling; nothing is imputed with zero.
- **Excluded inputs:** retail rice (unresolved provenance) and anything outside the development mask.
- **Feature selection:** none from data. Feature sets are fixed above.

## 5. Metrics and uncertainty

**Over the 7 exploratory quarters, for each configuration and for each threshold analysis (A-origin, A-global):**

- mean-quarter accuracy, plus correct and incorrect counts;
- weighted precision, recall and F1;
- HIGH recall, plus missed-HIGH rows and quarters;
- ROC-AUC and Brier score (fitted models);
- within-quarter province AUC;
- confusion matrix;
- per-quarter and per-province results;
- τ_T for every fold.

**Uncertainty:**

- quarter-cluster bootstrap (10,000 draws over the 7 quarters) and exact Clopper–Pearson intervals;
- paired comparison of the primary model with each comparator (exact McNemar test and a quarter-bootstrap interval of the difference);
- reported as an "exploratory estimate on 7 reused quarters (35 rows; 5 provinces share most inputs)".

## 6. Sensitivity analyses (reported alongside, never substituted)

| Sensitivity | Change |
|---|---|
| S1 | Drop revised inputs (ONI, drought, IBTrACS, NASA POWER) |
| S2 | Strict-protocol input mask (22 inputs), same proxied labels |
| S4 | Drop the supplementary 2025 SWS inputs |
| S5 | Include 2023-Q3 (7 training quarters) as an additional fold, reported separately |

**Alternative label definitions (formerly S3) are removed**; they need separate authorization (C2).

## 7. Leakage checks

- **Before and after the run:** `tests/unit/test_devprotocol_rule_l.py` must pass.
- **Runtime assertions:**
  - every training quarter < *T* and published before *T*'s origin;
  - every input published before the origin;
  - τ_T computed only from training rows (assert that no test-quarter row enters the median);
  - no 2026-Q3/Q4 outcome present;
  - `data/processed/*` hashes unchanged.

## 8. Reporting rule

1. **Report everything:** every configuration, threshold analysis, fold, metric and sensitivity, including failures. Nothing is re-run with changed settings.
2. **No changes after results:** a change requires a new, separately labelled pre-registration.
3. **Comparability:** A-origin results are not comparable with earlier reported accuracies (C10). A-global results are, but they carry the C1 leak.
4. **No 75% claim:** no statement may say or imply that the 75% requirement is met.

## 9. Conditions that would invalidate a final accuracy claim

Any one of the following means no result from this experiment, or any later one, may be presented as a **final** accuracy estimate:

- the evaluated quarters were used before (true for all 2022-Q4 to 2025-Q4 quarters);
- any input or training label is used before its documented publication date, or a proxy date (WD1) or revised vintage (WD2) is relied on without verification;
- a threshold, configuration, feature set, cut-off or test period is chosen or changed after seeing any result on the evaluated quarters;
- the test set is too small to separate performance from simple baselines. For example, 2 quarters / 10 rows cannot establish accuracy above 75%, because the 5 provinces in a quarter share most inputs;
- outcome values for the evaluated quarters were seen before the forecasts were frozen (2026-Q1/Q2 are already exposed);
- the [V-single] SWS inputs are later found to differ from their sources;
- the served model or data change mid-evaluation (for example, through the `backend/` scheduler) without the change being recorded.

## 10. Open decisions before freezing

C1 primary design; C3; C4/D3; C6; C9. See `docs/PREREGISTRATION_CONFLICT_RESOLUTION_2026-10-11.md`.
