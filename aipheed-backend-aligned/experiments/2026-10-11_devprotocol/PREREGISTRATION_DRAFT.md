# DRAFT Pre-registration: aiPHeed Exploratory Development Experiment (Development Protocol)

**Status: DRAFT, not yet frozen.** It becomes binding only when the researcher authorizes it and its SHA-256 is recorded. Until then nothing may be trained or scored.

| Item | Value |
|---|---|
| Prepared | 2026-10-11 |
| Code | `scripts/supplementary/devprotocol_rule_l.py` (SHA-256 `c126ca68953f6ba354293b2772c8caeff2d22541033e85a512d2c3d5c83841ec`) |
| Tests | `tests/unit/test_devprotocol_rule_l.py` (16) |
| Basis | `docs/WORKING_DECISIONS_AND_TRAINING_READINESS_2026-10-11.md` (WD1–WD6) |

**Every result of this experiment is EXPLORATORY.** The evaluated quarters (2023-Q3 to 2025-Q4) have been used in earlier comparisons, and the development protocol relies on a provincial-CPI date proxy (WD1) and revised climate data (WD2). Nothing here is a final or independent evaluation. No result here can establish 75% accuracy.

---

## 1. Prediction target

- **Label:** `label_stress` from Eq. 3, **definition A, unchanged** (`window2021_study.window_labels(14.345)`).
  - stress = SWS Balance-Luzon hunger + 2 × (provincial food CPI YoY − five-province mean); HIGH if stress > 14.345.
  - 14.345 is the Eq. 3 global median over the 80 labelled 2021–2025 rows.
- **Unit:** province × quarter (5 provinces). Labelled quarters: 2021-Q2 to 2025-Q4, excluding 2022-Q1, 2025-Q2 and 2025-Q3 (16 quarters).
- **No label is rebuilt.** Alternative definitions are sensitivity analyses that need separate authorization to build (Section 8).

## 2. Forecast horizon and origin

- **Horizon:** one quarter ahead. The forecast of target quarter *T* is issued at its origin, 00:00 on the first day of *T*.
- **Inputs:** only values available before the origin under the development protocol:
  - SWS: the latest round with a known publication date, per round (Rule L2/L4), including the three supplementary 2025 rounds;
  - provincial CPI: the national release + 14 days **proxy** (WD1);
  - regional CPI: the national release date;
  - 2018-base CPI: not before 2022-02-04 (WD5);
  - other series: documented schedules (WD3);
  - news: articles from quarter *T−1*.
- **Missing inputs stay missing (NaN).**

## 3. Chronological splits

- **Exploratory outer test quarters (fixed now):** 2023-Q3, 2023-Q4, 2024-Q1, 2024-Q2, 2024-Q3, 2024-Q4, 2025-Q1, 2025-Q4. That is 8 quarters, 40 rows, already reused.
- **Training set for target *T*:** all labelled quarters *q < T* whose label was **published before *T*'s origin** (Rule L1: the later of the last SWS round in the label and the final-month provincial CPI date, proxied). This gives 7, 8, 9, 10, 11, 12, 13 and 15 training quarters respectively (`eligibility_snapshot.csv`).
- **No inner selection is needed:** no hyperparameters or features are chosen from data (Sections 5–6).
- **2026 quarters are not part of this experiment:**
  - 2026-Q1/Q2 are disclosed checks only.
  - 2026-Q3/Q4 belong to the separate protected-evaluation protocol (`docs/RULE_L_FINAL_AND_PROTECTED_EVALUATION_PLAN_2026-10-09.md`). They need their own freeze-then-collect authorization.

## 4. Models (fixed now; nothing added after results)

| Role | Model | Inputs |
|---|---|---|
| **Primary** | MODEL-B2 configuration: LightGBM, library defaults, `random_state=42`, `scale_pos_weight = (1−p)/p` from the fold's training rows | `gov_c` ∩ development mask (44 inputs) |
| Comparator | MODEL-A configuration: LightGBM, library defaults, `random_state=42` | The 12 Equation 5 inputs |
| Comparator | Equation 3 rule: HIGH if (latest published SWS + 2 × `cpi_rel`) > 14.345 | 2 inputs; no fitting |
| Comparator | Carry-forward of the latest **published** label: the province's label from the most recent quarter whose label was published before the origin | none |

**Decision cut-off:** 0.50 for the fitted models; no threshold tuning.

## 5. Feature selection

**None from data.** Feature sets are fixed above. Exclusions are by rule only:

- retail rice (unresolved provenance);
- anything not in the development mask (`evidence/2026-10-11_working_decisions/feature_eligibility_by_protocol.csv`).

## 6. Hyperparameters and seed

- **Library defaults; no tuning, no search.**
- **Seed 42** for every stochastic component. One seed, with no seed selection.

## 7. Metrics and comparisons (all reported)

**Per configuration, over the 8 exploratory quarters:**

- mean-quarter accuracy, plus correct and incorrect counts;
- weighted precision, recall and F1;
- HIGH-class recall, plus missed-HIGH rows and quarters;
- ROC-AUC (fitted models) and Brier score;
- within-quarter province AUC;
- confusion matrix;
- results by quarter and by province.

**Uncertainty and comparisons:**

- quarter-cluster bootstrap (10,000 draws over the 8 quarters) and the exact Clopper–Pearson interval;
- paired comparison of the primary model against each comparator: exact McNemar test and a quarter-bootstrap interval of the difference.

**Reporting language:** "exploratory development estimate on 8 reused quarters (40 rows; 5 provinces per quarter share most inputs)".

## 8. Pre-declared sensitivity analyses (reported alongside, never substituted for the primary)

| Sensitivity | Change | Status |
|---|---|---|
| S1 | Remove revised inputs (ONI, drought, IBTrACS, NASA POWER) | Ready |
| S2 | Strict-protocol input mask (22 inputs) with the same proxied labels | Ready |
| S3 | Label definitions A-adult, C and D | **Need separate authorization to build labels** |
| S4 | MODEL-B2 configuration without the supplementary 2025 SWS inputs (the pre-collection information set) | Ready |

## 9. Leakage checks (must pass before and after the run)

- `tests/unit/test_devprotocol_rule_l.py` (16 tests): training labels published before the origin; SWS inputs published before the origin; unknown-date rounds excluded; two-round labels wait for the second round; 2021 labels not before 2022-02-04; proxy vs verified dates distinguishable; NaN, not zero; revised inputs development-only; retail rice excluded; no protected 2026 outcome present; no production file changed.
- **Runtime assertions:**
  - no feature row with an origin later than its target's start;
  - no training quarter ≥ the target;
  - the hashes of `data/processed/*` are unchanged after the run.

## 10. Reporting rule

1. **Report every configuration, every quarter, every metric and every sensitivity, including failures.** No result is dropped or re-run with changed settings.
2. **No change to models, inputs, cut-offs or definitions after any result is seen.** A change requires a new, separately labelled pre-registration.
3. **All results are labelled exploratory.** No statement may say or imply that the thesis meets the 75% requirement on this evidence, or that a small test set establishes reliability.
4. The protected 2026-Q3/Q4 evaluation, if later authorized, is reported separately under its own protocol (at most 10 rows; a point estimate with an interval).

## 11. Unresolved methodological conflicts (not silently resolved)

| # | Conflict | Current handling in this draft | Decision needed |
|---|---|---|---|
| C1 | The global-median threshold (14.345) uses all labelled rows, including the evaluated quarters (as Eq. 3 specifies) | Kept as approved | Whether to keep it, or use a training-only threshold (a target change) |
| C2 | Label definitions A-adult or D would change the global median; should sensitivity labels reuse 14.345 or recompute? | Not built yet | Adviser/team choice before S3 |
| C3 | The earlier protocol required at least 8 training quarters; under Rule L the first exploratory origin (2023-Q3) has 7 | The 8 outer quarters are kept as fixed above | Accept 7, or drop 2023-Q3 (must be decided **before** running) |
| C4 | Definition A's 2025-Q1 label comes from a registered-voter round; the earlier series is household heads | Kept (definition A); S3-D drops it | Adviser (D3) |
| C5 | WD1 proxy, WD2 revised inputs | Development only; disclosed | Strict protocol needs 19 provincial dates and vintages |
| C6 | SWS rounds used as inputs with [V-single] evidence (June, September and November 2025) | Used, flagged | Manual confirmation |
| C7 | The March 2026 SWS value is an exposed outcome (2026-Q1) but a legitimate input for 2026-Q3/Q4 forecasts | Not used here (2026 not in this experiment) | Disclosure in any protected evaluation |
| C8 | June 2026 SWS publication date unknown, so it is excluded as an input for the 2026-Q4 origin | Not relevant here | Verify before any 2026-Q4 forecast |
| C9 | `backend/` scheduler (2026-10-15) could replace the thesis-documented served model | Outside this experiment; not touched | `SCHEDULER_ENABLED` decision (researcher) |
