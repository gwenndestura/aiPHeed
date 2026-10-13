# DRAFT v3 Pre-registration: aiPHeed Exploratory Development Experiment

**Status: DRAFT v3. NOT frozen, NOT hashed, NOT authorized to run.**

| Item | Value |
|---|---|
| Prepared | 2026-10-11 |
| Supersedes | `PREREGISTRATION_DRAFT_v2.md` (preserved, unchanged) |
| Decision report | `docs/FINAL_METHODOLOGY_AUDIT_2026-10-11.md` |
| Code | `scripts/supplementary/devprotocol_rule_l.py` (SHA-256 `c126ca68953f6ba354293b2772c8caeff2d22541033e85a512d2c3d5c83841ec`, unchanged) |
| Tests | `tests/unit/test_devprotocol_rule_l.py` (16) |

**How to read the markers:**

- **[ADVISER]** marks an item that needs adviser approval before freezing.
- **[RESEARCHER]** marks an item that needs the researcher's decision.

**This draft does not claim any adviser approval.**

**Every result of this experiment is EXPLORATORY.**

- Every evaluated quarter (2023-Q4 to 2025-Q4) was used in earlier studies.
- The development protocol relies on a provincial-CPI date proxy (WD1) and revised climate data (WD2).
- No result here is a final or independent evaluation.
- No result here can establish 75% accuracy.

---

## 1. Target

### 1.1 Stress score (unchanged)

The stress score is Equation 3, definition A, with nothing rebuilt or added:

- stress(p, t) = SWS Balance-Luzon hunger(t) + 2 × (provincial food CPI YoY(p, t) − five-province mean food CPI YoY(t)).
- There are 80 labelled rows: 2021-Q2 to 2025-Q4, excluding 2022-Q1, 2025-Q2 and 2025-Q3.

### 1.2 Threshold: two pre-specified analyses, both always reported

| Analysis | Threshold for quarter *T* | Meaning of "HIGH" | Leakage on reused quarters |
|---|---|---|---|
| **Primary: "A-origin"** [ADVISER] | τ_T = median stress over the training rows eligible under Rule L at *T*'s origin | Stress above the median of all stress levels published by the forecast date | None |
| **Secondary: "A-global"** (mandatory) | 14.345 = median of the 80 labelled 2021–2025 rows | Stress above the 2021–2025 median (the approved definition as implemented) | **Yes.** The threshold is computed partly from the evaluated quarters and later ones (C1). |

**Rules that apply to both analyses:**

- One threshold per analysis per fold is applied to:
  - the training labels;
  - the test labels;
  - the Equation 3 rule;
  - the carry-forward baseline;
  - `scale_pos_weight`.
- A hybrid design is not permitted: training at τ_T while scoring at 14.345, or the reverse.

**If the adviser does not approve A-origin as primary:**

- A-global becomes primary.
- Every A-global result must then carry the label "uses the full-period threshold: not leakage-free".
- A-origin is reported as the leakage-free sensitivity analysis.

**This choice must be recorded before freezing and cannot change after any result.**

### 1.3 Protected 2026-Q3/Q4 evaluation (not part of this experiment)

The two analyses coincide here: τ = 14.345 at both origins, with all 16 labelled quarters eligible.

- The approved threshold was fixed from data published before 2026-07-01.
- It is therefore **leakage-free for the protected quarters, with its approved meaning unchanged**.
- **This holds only if no 2026 label enters the threshold or the training data.** The 2026-Q1/Q2 outcomes are exposed and are never labelled.

## 2. Horizon and origin

| Item | Specification |
|---|---|
| Horizon | One quarter ahead (k = 1) |
| Forecast for *T* | Issued at its origin, 00:00 on the first day of *T* |
| Unit | Province × quarter: five provinces. Balance-Luzon SWS is shared across them. |
| Inputs | Only values published before the origin under the development protocol (Section 6) |

## 3. Chronological training and evaluation procedure

For each exploratory target quarter *T*, in calendar order:

1. **Training quarters.** E(T) = labelled quarters *q < T* whose label was published before *T*'s origin. A label is published at the later of:
   - the last contributing SWS round's publication date;
   - the final-month provincial CPI release, which is the WD1 proxy (national release + 14 days) unless verified, and never before 2022-02-04 (WD5).

   E(T) is computed by `devprotocol_rule_l.eligible_training_quarters(T, "development")`.
2. **Threshold τ.** τ = τ_T (A-origin) or 14.345 (A-global). For τ_T, use all five provinces' rows of E(T) only, and **assert that no row of *T* or of any later quarter enters it.**
3. **Training labels** are `stress > τ` on the rows of E(T).
4. **Class weight:** `scale_pos_weight = (1 − p)/p`, with *p* = the HIGH share of the step-3 labels. If *p* is 0 or 1, the fold is reported as degenerate and not refitted.
5. **Input matrix** for the training rows and the *T* rows: `devprotocol_rule_l.development_frame()`, restricted to the fold's feature set (Section 4).
6. **Fit** the two fitted configurations on the training rows. Then predict the five *T* rows and record the probability and the class at a cut-off of 0.50.
7. **Non-fitted baselines** for the *T* rows, using the same τ (Section 4).
8. **Test labels** are `stress(T) > τ`. They are read **only after** the forecasts in steps 6–7 have been written to a fold record.
9. **Fold record:** τ, |E(T)|, training HIGH share, predictions, then labels.

**Exploratory test quarters (fixed now):**

- **2023-Q4, 2024-Q1, 2024-Q2, 2024-Q3, 2024-Q4, 2025-Q1, 2025-Q4**: 7 quarters, 35 rows.
- **2023-Q3 is excluded** [RESEARCHER, ADVISER note]. It has 7 eligible training quarters, below the minimum (Section 3.1).

**Excluded quarters:**

| Quarter | Reason |
|---|---|
| 2025-Q2, 2025-Q3 | No definition-A label |
| 2026-Q1, 2026-Q2 | Exposed outcomes: disclosed checks only |
| 2026-Q3, 2026-Q4 | Separate protected protocol |

**No inner validation:** nothing is selected from data.

### 3.1 Minimum training history

**Rule:** at least **8 eligible labelled quarters** (40 rows) in E(T).

This follows Chapter III Algorithm 3: "a minimum training window of 8 quarters" and "minimum 8 training quarters". The count is made after Rule L.

**Interpretation note [ADVISER]:**

- The Algorithm 3 architecture list says "8 **consecutive** quarters".
- No eligible set in the 2021–2026 window is consecutive, because 2022-Q1 has no label.
- Read literally, the first qualifying fold is 2024-Q3: eight consecutive eligible quarters, 2022-Q2 to 2024-Q1.
- That reading is pre-registered as sensitivity S6. It is not the primary rule.

| Target | Eligible quarters (development) | Longest consecutive run | Primary rule | S6 (consecutive) |
|---|---:|---:|---|---|
| 2023-Q3 | 7 | 4 | excluded | excluded |
| 2023-Q4 | 8 | 5 | included | excluded |
| 2024-Q1 | 9 | 6 | included | excluded |
| 2024-Q2 | 10 | 7 | included | excluded |
| 2024-Q3 | 11 | 8 | included | included |
| 2024-Q4 | 12 | 9 | included | included |
| 2025-Q1 | 13 | 10 | included | included |
| 2025-Q4 | 15 | 12 | included | included |

## 4. Fixed models, seed and comparators

**Settings for every model:**

- Seed 42 for every stochastic component. One seed, never selected.
- Library defaults; no tuning and no search.
- Cut-off 0.50.
- No data-driven feature selection.
- Reproducibility check: the primary run is executed twice and must give identical predictions.

| Role | Specification | Inputs |
|---|---|---|
| **Primary** | MODEL-B2 configuration: LightGBM `objective="binary"`, `random_state=42`, `scale_pos_weight` per Section 3 step 4 | `gov_c` ∩ development mask: 44 inputs |
| **Comparator: MODEL-A** | MODEL-A configuration **refitted per fold**: LightGBM defaults, `random_state=42` | The 12 Equation 5 inputs |
| **Comparator: Equation 3 rule** | HIGH if (latest SWS published before the origin + 2 × `cpi_rel` available at the origin) > τ | 2 inputs; no fitting |
| **Comparator: carry-forward** | HIGH if the province's latest **published** stress score (latest quarter in E(T)) > τ | none |
| Reference only (not comparators) | Always-HIGH and always-LOW | none |

**MODEL-A notes:**

- The served artifact (`models/lgbm_best.pkl`) is **not** scored, because it was trained on rows that include the evaluated quarters.
- The `backend/` served model is out of scope.

**The reference rows** make the test-set class balance visible. Under A-origin, the test HIGH share is not guaranteed to be 50%.

## 5. Leakage-free determination of every data-dependent quantity

| Quantity | Determined from | Never uses |
|---|---|---|
| Threshold τ_T (A-origin) | Stress of rows in E(T) | *T* or any later quarter |
| Threshold 14.345 (A-global) | All 80 labelled rows | Nothing excluded: **leaky by construction**, so disclosed |
| Training labels | τ and the stress of E(T) | Test labels |
| `scale_pos_weight` | Training labels | Test labels |
| Feature engineering | Fixed formulas on data published before the origin: `cpi_dev` uses the province's prior 4 quarters; the regional mean is a same-quarter cross-section of published inputs | Any statistic pooled across folds |
| Scaling or normalization | None (tree models; rules are threshold comparisons) | — |
| Missing values | NaN, kept as NaN; LightGBM native handling; nothing imputed, nothing fitted | Zero-fill, or means from any period |
| Baselines | τ and inputs published before the origin | Test labels |
| Cut-off | Fixed at 0.50 | Any result |

## 6. Data-availability rules

| Input or rule | Treatment |
|---|---|
| SWS input | Latest round with a known publication date before the origin, selected per round. Includes the three supplementary 2025 rounds **as inputs only**. Unknown-date rounds are excluded (Rule L4). |
| Provincial CPI | WD1 proxy: national release + 14 days, except the verified 2024-Q4 date (2025-01-13). Not before 2022-02-04 (WD5). |
| Regional CPI | National release date |
| Other series | Documented schedules (WD3) |
| Revised climate inputs | ONI, drought, IBTrACS and NASA POWER (WD2). Development only. |
| Retail rice | Excluded: unresolved 2022–2025 provenance |
| Unavailable values | NaN |

**Development mask:** 49 of 51 inputs.

## 7. Metrics

**Reported for every configuration × analysis (A-origin, A-global) × sensitivity:**

- mean-quarter accuracy, plus correct and incorrect counts;
- **balanced accuracy**;
- weighted precision, recall and F1;
- HIGH recall, plus missed-HIGH rows and quarters;
- ROC-AUC and Brier score (fitted models);
- within-quarter province AUC;
- confusion matrix;
- per-quarter and per-province results;
- **test-set HIGH share**;
- τ for every fold, with |E(T)| and the training HIGH share.

## 8. Uncertainty and quarter dependence

**Two-stage uncertainty:**

- **Quarter-cluster bootstrap:** 10,000 draws over the 7 quarters, seed 42. This is the headline interval.
- **Clopper–Pearson exact interval:** over the 35 rows, labelled "assumes independent rows: optimistic".
- **Paired comparisons:** primary vs each comparator, using an exact McNemar test (also labelled optimistic) and a quarter-bootstrap interval of the accuracy difference.

**Limitations that must accompany every result:**

1. The five provinces in a quarter share the SWS component and most national inputs. The effective sample is closer to 7 quarters than to 35 rows.
2. With 7 clusters, the bootstrap distribution is coarse and tends to understate tail uncertainty.
3. Even under the optimistic independence assumption, 35 rows would need **at least 32 correct** for the 95% Clopper–Pearson lower bound to exceed 0.75. Ten rows (the protected 2026-Q3/Q4 set) can never reach it: 10/10 gives a lower bound of 0.69.

## 9. Treatment of reused quarters

- All 7 test quarters, and every earlier fold, were used in earlier studies (WD6).
- Results are labelled "**exploratory development estimate on 7 reused quarters**" and are never called a final, independent or held-out evaluation.
- They may inform whether to proceed to the protected 2026-Q3/Q4 evaluation. They may not be pooled with it.

## 10. Sensitivity analyses (reported alongside, never substituted for the primary)

| ID | Change |
|---|---|
| S1 | Drop the revised inputs (ONI, drought, IBTrACS, NASA POWER) |
| S2 | Strict-protocol input mask (22 inputs); same proxied labels |
| S4 | Drop the three supplementary 2025 SWS inputs (pre-collection information set) |
| S5 | Add 2023-Q3 as an extra fold (7 training quarters), reported separately |
| S6 | Literal "8 consecutive quarters": test quarters 2024-Q3, 2024-Q4, 2025-Q1 and 2025-Q4 only (4 quarters, 20 rows) |

**Not included:** alternative label definitions (formerly S3) need separate authorization.

## 11. Leakage checks

**Before and after the run:**

- `tests/unit/test_devprotocol_rule_l.py` must pass.
- The full suite must pass.

**Runtime assertions:**

1. Every quarter in E(T) is earlier than *T* and published before *T*'s origin.
2. Every input is published before the origin.
3. τ_T is computed only from rows of E(T).
4. Test labels are read only after the fold's predictions have been written.
5. No 2026 quarter appears as a label anywhere.
6. The hashes of `data/processed/*`, `models/*` and `app/ml/corpus/sws_hunger_fetcher.py` are unchanged.
7. The primary run gives identical predictions twice.

## 12. Reporting rule

1. Report every configuration, analysis, fold, metric and sensitivity, including failures and degenerate folds.
2. **No change after results:** a change requires a new, separately labelled pre-registration.
3. **Comparability:** A-origin results are not comparable with any earlier accuracy (all earlier studies used 14.345) (C10). A-global results are comparable, but leaky.
4. **No 75% claim:** no statement may say or imply that the 75% requirement is met.

## 13. Invalidating conditions

### 13.1 For this exploratory experiment

The run is void, and must be redone under a new pre-registration, if:

- any assertion in Section 11 fails;
- any setting is changed after any result is seen;
- the C1 analysis designation (primary or secondary) is changed after any result is seen;
- a manually confirmed [V-single] SWS value or date differs from the value used (C6).

### 13.2 For any final accuracy claim

No result may be presented as a final accuracy estimate if any of the following holds:

- the evaluated quarters were used before (true for 2022-Q4 to 2025-Q4);
- any input or label relies on a proxy date (WD1) or revised vintage (WD2) without verification;
- the threshold was computed using the evaluated quarters (A-global on 2021–2025 quarters);
- the outcomes were seen before the forecasts were frozen (2026-Q1/Q2);
- the respondent-population issue (C4/D3) is unresolved for the quarters involved;
- the test set is too small (Section 8.3);
- the served model or data change mid-evaluation without the change being recorded (C9).

## 14. Thesis statements affected if A-origin becomes primary

These would need revision or a stated deviation, but only with adviser approval. Chapter III line numbers refer to the extracted text. **Nothing has been edited.**

1. **"Forecast Target Label" paragraph (§3.4.2):** "The global median threshold across all 120 province-quarter pairs will guarantee a balanced class split."
2. **Equation 3 legend:** "global_median(stress): median stress score across all 120 province-quarter pairs; guarantees a 50/50 class balance."
3. **Chapter III summary of the model section:** "composite food stress label thresholded at the global median to yield a balanced binary HIGH/LOW target."
4. **Algorithms 3 and 4 inputs:** "120 rows spanning 5 provinces across 24 quarters" (already inconsistent with 80 labelled rows), and the "consecutive" wording of the minimum window.
5. **§3.4.4 Reliability Threshold:** the 75% / F1 ≥ 0.75 / AUC ≥ 0.80 targets would be assessed on the origin-relative target in the exploratory analysis.
6. **Every Chapter IV or results statement** that reports accuracy, class balance or labels at 14.345 or "the global median" would need to say which analysis it reports.

**Statements that hold under either analysis:** wording about identifying "high-risk provinces" for anticipatory planning (Chapters I–II) does not need revision. "High" would mean "high relative to the stress levels observed up to the forecast date".

## 15. Open decisions before freezing

| # | Decision | Who |
|---|---|---|
| C1 | A-origin primary (recommended) or A-global primary | Adviser |
| C3 | Drop 2023-Q3 (recommended); "8 eligible" vs "8 consecutive" reading | Researcher, with an adviser note |
| C4 / D3 | 2025 respondent-population composition | Adviser |
| C6 | Manual confirmation of the June, September and November 2025 SWS rounds | Researcher |
| C9 | `SCHEDULER_ENABLED` before 2026-10-15 02:00 Asia/Manila | Researcher |
| — | Freezing and hashing this draft, then authorizing the run | Researcher |
