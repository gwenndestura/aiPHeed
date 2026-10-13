# Model Diagnosis and Next Experiment (run 20261011T111651Z)

**Sources:**

- The completed run: `RUN_REPORT_20261011T111651Z.md`, `metrics.json`, `scored_rows.csv`, `config.json` and the prediction files;
- `app/ml/features/label_generator.py` and `data/processed/labels.parquet`;
- the development frame, rebuilt read-only.

**Supporting tables and the script:** `diagnosis_20261011T111651Z/`

- `quarter_decomposition.csv`
- `test_quarter_level.csv`
- `missingness.csv`
- `within_quarter_spearman.csv`
- `errors_primary.csv`
- `diagnose.py`

**Not done:** no model was trained, refitted or tuned. The completed run, production, the served model, frozen forecasts, the scheduler, the scheduled tasks and the thesis are untouched. No 2026 outcome data was accessed.

**Disclosure:** this diagnosis read the stress scores of the already-reused 2023–2025 test quarters (§1.5). That further exposes those quarters, and is a further reason they can only ever support exploratory claims.

---

## 1. Diagnosis

### 1.0 The decisive structural fact (established)

Equation 3 is: stress(p, t) = SWS(t) + 2 × (CPI(p, t) − mean over the 5 provinces of CPI(t)). The deviation term sums to zero across the five provinces, so:

- **The quarter mean of stress equals the regional SWS value exactly.** Every test quarter confirms it: 14.3, 15.3, 19.6, 18.1, 25.3, 24.0, 16.7.
- **Over the 80 labelled rows, 65% of the stress variance is between quarters (the single regional SWS value).** Only **35%** is within a quarter, and that part comes entirely from provincial food-CPI deviations.

**So the binary target has two parts:**

1. **A regional call:** is Balance-Luzon hunger above the threshold? There is one value per quarter.
2. **A within-quarter ranking:** the provincial food-price deviation, which only matters in quarters where the regional level is near the threshold.

### 1.1 Why MODEL-B2 is worse than carry-forward and the Equation 3 rule

**Established:**

- **The regional level drives the outcome.** Under A-origin, the regional level exceeded τ_T in **all 7** test quarters, by +2.6 to +12.8 points.
- **The simple rules start from the right level.** Carry-forward and the Equation 3 rule begin from the last published stress or SWS value. That value was already above τ_T in most folds, and hunger stayed high: consecutive labelled quarters keep the same label 77% of the time.
- **MODEL-B2 did not use the information it had.** Its mean predicted probability was 0.32 in **2025-Q1**, even though its own SWS input at the origin (18.1) was far above τ_T (13.22). It predicted only 1 HIGH out of 5 when all 5 were HIGH. It also gave only 2/5 HIGH in 2024-Q4 (input 19.6 against τ 12.5).
- **Where its errors come from:**

  | Quarter | MODEL-B2 errors out of 5 | Situation |
  |---|---:|---|
  | 2023-Q4 | 4 | SWS input 11.3, just above τ 10.84; hunger then rose to 14.3; B2 predicted 0 HIGH |
  | 2025-Q1 | 4 | Described above |
  | 2024-Q4 | 3 | Described above |

  These three quarters account for **11 of its 15 errors**.

**Hypotheses that still need testing:**

- **H1: the defaults leave almost no room for model structure.** LightGBM's defaults are `min_child_samples=20`, `num_leaves=31` and `n_estimators=100`. With 40–75 training rows, a tree can have at most 2–3 leaves. The model therefore becomes a sum of stumps over 44 mostly regional features, and it does not anchor on the SWS level. The default settings are a fact; their effect is a hypothesis, because no importances were saved and nothing was refitted.
- **H2: the training data have a missingness pattern the test data lack.**

  | | Training rows | Test rows |
  |---|---:|---:|
  | Share of MODEL-B2 inputs that are NaN | 19–30% | 5–8% |

  The missing values in training come from early quarters (WD5 CPI cutoff and short news history). The trees can split on missingness patterns that never occur at test time. MODEL-A shows the same pattern: 30–35% missing in training against 18–28% in test.
- **H3: the test levels lie outside the training range.** The test-period SWS inputs (14.3–19.6) are at or beyond the top of most training folds (2021–2023 levels were 8.7–15.4). Trees cannot extrapolate.

### 1.2 Why MODEL-A has high accuracy but poor balanced accuracy

**Established:**

- **It behaves almost like always-HIGH.** It predicted HIGH in 30 of 35 rows, so its accuracy is mostly the base rate (32/35 HIGH).
- **It missed every LOW row:** 0/3, giving a confusion matrix of [[0, 3], [5, 27]].
- **In 2025-Q1 it predicted all LOW,** so all 5 rows there were wrong.
- **In 2023-Q4 and 2024-Q1 its predictions were identical for all five provinces,** so it made no within-quarter distinction at all.
- **Where it did vary within a quarter, it ranked provinces backwards:** mean within-quarter Spearman ρ against actual stress is −0.31.

Balanced accuracy is 0.42, below chance.

### 1.3 Where the errors are

**MODEL-B2, A-origin, errors out of 7:**

| Province | Errors |
|---|---:|
| Batangas | 4 |
| Laguna | 4 |
| Rizal | 3 |
| Cavite | 2 |
| Quezon | 2 |

**By quarter:** 2023-Q4 (4 errors), 2025-Q1 (4) and 2024-Q4 (3).

**This is not a province-specific failure.** The errors come from whole-quarter misses of the regional level; per-province counts mostly reflect those quarters.

**The rules' few errors were spread out:** Laguna 2, Quezon 2, Batangas 1, Rizal 1, Cavite 0. They fall in the mixed quarters, where one province was LOW.

### 1.4 Features, missing values, threshold shifts or class distribution?

| Candidate cause | Status | Evidence |
|---|---|---|
| **Change in the HIGH/LOW distribution (threshold drift)** | **Established; the dominant cause** | τ_T is the median of a mostly 2021–2023 low-hunger history (10.8–14.1). The 2023-Q4 to 2025 period sits at 14.3–25.3. Training sets are balanced (HIGH share 0.49–0.50), but the test set is 91% HIGH. This is a shift between training and test, not imbalance in the training data. |
| Missing values | **Hypothesis (H2)** | The NaN share differs sharply between training and test (§1.1). The Equation 3 rule needed no fallback, so missing data did not affect the rules. |
| Specific features | **Untested** | Answering this requires refitting to obtain importances, which this task did not allow |
| Small-sample configuration | **Hypothesis (H1)** | — |

### 1.5 Does the model distinguish provinces, or only the regional level?

**Within-quarter Spearman ρ between each model's score and actual stress (5 provinces per quarter; established):**

| Model | Mean ρ | Per-quarter range |
|---|---:|---|
| Carry-forward | 0.29 | −0.4 to 0.9 |
| Equation 3 rule | 0.29 | −0.4 to 0.9 |
| MODEL-B2 | 0.21 | −0.36 to 0.82 |
| MODEL-A | −0.31 | — |

- Carry-forward and the Equation 3 rule rank provinces identically, because both rank by the last published CPI deviation.
- **None of the models differentiates provinces reliably.** With 5 provinces per quarter, |ρ| < 0.9 is not distinguishable from chance in any single quarter.
- **MODEL-B2 mostly tracks the regional level,** and does that badly.

### 1.6 Are the current metrics meaningful?

**Only partly.**

- **Accuracy over 35 rows mixes two different things:**
  - about 7 regional decisions, which dominate the result;
  - a weak within-quarter ranking signal.
- **Under A-origin, 4 of the 7 test quarters have all five provinces HIGH.** The whole LOW class is 3 rows from 3 quarters, so balanced accuracy and ROC-AUC rest on 3 rows.
- **Row-level intervals overstate precision** (n_eff ≈ 7).

**Meaningful reporting separates the two parts:**

1. A **regional-level** result at the quarter level: 7 units, compared with persistence.
2. A **within-quarter province ranking** result: Spearman ρ, or top-province hit rate.

## 2. Target and class-imbalance audit

### 2.1 How the label is built

`label_generator.py` builds the label as follows:

1. Compute stress = SWS + 2 × (provincial food CPI YoY − five-province mean of the same quarter).
2. Set the threshold to `median(stress)` over **all labelled rows** (l.222–226).

### 2.2 The two thresholds compared

| | Approved global median (14.345) | Training-only median τ_T |
|---|---|---|
| Comparable over time | **Yes.** HIGH always means stress > 14.345. | **No.** The same stress of 14.0 is HIGH at the 2025-Q1 origin (τ 13.22) but LOW at the 2025-Q4 origin (τ 14.11). |
| Leakage in retrospective evaluation | **Yes.** The threshold uses the test quarters. | None |
| Contrast in the 2023-Q4 to 2025 test period | 30/35 HIGH | 32/35 HIGH |
| Meaning for DA planning | "Hunger and food-price stress above the 2021–2025 typical level": an interpretable absolute level, fixed after the fact | "Above what has been typical so far": a drifting reference. It flags almost everything once a high-hunger regime begins. |

**Consequences:**

- **Neither binary threshold gives useful contrast in this test period**, because the regional level was persistently high.
- The approved threshold is better for interpreting results over time.
- The training-only threshold is the honest way to evaluate on reused quarters, but its labels are hard to compare from quarter to quarter.
- **For the protected 2026-Q3/Q4 evaluation, both thresholds equal 14.345** (all 80 labels are published before those origins). That evaluation keeps the approved meaning without leakage.

**Adviser decisions required** (nothing has been changed):

1. Which threshold governs the reported exploratory analysis. The protocol fixed A-origin as primary, pending approval.
2. Whether a fixed, externally justified planning threshold would serve DA better than a median. Any such threshold must be set **without** looking at test outcomes.
3. Whether results may be reported as two parts (regional level and within-quarter province ranking) alongside the Equation 3 binary label.
4. Whether any research-alternative target (§3.3) may be reported alongside the thesis target, and with what status.

## 3. Next steps, in the requested order

### 3.1 Improve the evaluation and the baseline comparison

**Do this first; it needs no training.**

- Carry-forward and the Equation 3 rule are the bars any model must clear. **Today, MODEL-B2 adds no value beyond them** (established).
- Future reports should use the two-part split in §1.6, with quarter-level intervals.

### 3.2 Class weighting and threshold selection

- **Training labels are already balanced** under A-origin: `scale_pos_weight` ≈ 1.
- The imbalance is in the **test period**, caused by a regime shift that cannot be seen at the origin. Class weights or a probability cut-off tuned on training data cannot anticipate a shift whose direction is unknown.
- Training-only selection is possible: nested walk-forward inside the 8–15 training quarters. But the inner folds would have 3–10 quarters, so the selection would be very noisy. The earlier nested result was 62.5%.
- **Not recommended as the next step.**

### 3.3 A continuous target (separately documented research alternative)

Predicting continuous stress removes both the threshold drift and the imbalance. The regional part is a single series of about 16 quarterly values within the approved 2021–2026 window, which persistence already forecasts reasonably:

- correlation between the regional level and the SWS input at the origin: 0.81;
- correlation of their quarter-to-quarter changes: 0.53.

**No credible machine-learning improvement on the regional level can be shown with 16 points.** That part should stay a persistence/Equation 3 component.

**The provincial deviation is where a model could add value,** and where more data exist:

- provincial food CPI covers **20 quarters**, 2021-Q1 to 2025-Q4, all five provinces;
- that includes 2022-Q1, 2025-Q2 and 2025-Q3, which have no SWS round.

### 3.4 Province-level risk differentiation

**What the current target can support:**

- The shared regional target supports province claims **only** about relative food-price stress: the CPI deviation.
- It does **not** support claims about province-level hunger. No province-specific hunger outcome exists in the project, and none may be invented.

### 3.5 Data limitations

**The provincial outcome data that would materially help (within 2021–2026; none retrieved):**

| Source | What it would add |
|---|---|
| Province-level SWS hunger estimates (request to SWS; not public) | Province hunger outcomes |
| NNC/DOH OPT Plus provincial malnutrition prevalence | Annual provincial outcome |
| CBMS province and LGU indicators | Provincial welfare indicators |
| DSWD program caseloads by province | Provincial need |
| PSA provincial poverty estimates | Triennial provincial measure |
| The missing 2025 SWS rounds (January and February Stratbase, April 11–15) | Inputs only; they do not add labels |

## 4. Proposed next experiment (E2): NOT executed; needs your authorization

**Research question:**

> At each forecast origin, does the MODEL-B2 input set rank the five provinces' next-quarter food-price stress better than carry-forward of the latest published deviation?

This tests the one component where a model can add province-level value for DA prioritization.

**Target (a research alternative; it does not replace Equation 3):**

- d(p, T) = provincial food CPI YoY(p, T) − five-province mean(T).
- This is the provincial component of Equation 3: stress = SWS + 2d.
- It is computed with the same `label_generator` CPI construction, read-only, into the experiment folder.
- Building it requires your authorization (C2).

**Training and test periods:**

- **Training data for T:** quarters q < T whose final-month provincial CPI was published before T's origin (WD1 proxy; never before 2022-02-04). No SWS is involved.
- **Folds:** each fold needs at least 8 eligible quarters (2023-Q4 has 10).
- **Test quarters, fixed now:** **2023-Q4 through 2025-Q4**, all 9 quarters (45 rows).
  - **2025-Q2 and 2025-Q3 have never been evaluation targets.**
  - The other 7 were reused, and their deviations were exposed by this diagnosis.
- **Excluded:**
  - 2026-Q1 and 2026-Q2: CPI seen at collection.
  - 2026-Q3 and 2026-Q4: protected. Because this target needs **no SWS**, it offers a clean prospective path later: freeze forecasts, then collect July–December 2026 provincial CPI under a separately authorized procedure.

**Features at each origin:** the same `development_frame()` inputs as the first run. The MODEL-B2 set is used unchanged (44 inputs); no selection.

**Model (one only; no search):**

- `LGBMRegressor(objective="regression", random_state=42, verbosity=-1)` with library defaults.
- The H1 limitation is disclosed. It is not tuned away.

**Baselines:**

| Baseline | Definition |
|---|---|
| CF-dev (carry-forward) | The latest published deviation, i.e. `cpi_rel` at the origin |
| Province-mean | Each province's mean d over its training quarters |
| Zero | No differentiation (all provinces equal); for MAE only |

**Metrics, per quarter and pooled:**

- within-quarter Spearman ρ, giving a mean ρ and per-quarter values;
- top-province hit rate: was the most-stressed province identified?;
- MAE of d;
- **sign classification (d > 0, i.e. above the regional mean):**
  - balanced accuracy, per-quarter accuracy and confusion matrix;
  - the threshold is fixed at 0 by construction, so it needs no training threshold or class weights; classes are near 50/50 every quarter;
- quarter-cluster bootstrap 95% intervals (10,000 draws, seed 42) for the differences from CF-dev;
- for continuity only: the Equation 3 binary implied by carry-forward SWS + 2 × predicted d, at τ_T and at 14.345.

**Thresholds and class weights:** none are learned. The regression is threshold-free, and the sign threshold is 0 by definition.

**How it avoids leakage:**

- Every training target and input is published before the origin.
- The regional mean is a same-quarter cross-section; it uses no future quarters.
- Test-quarter values are revealed only after the predictions are written (the label-vault pattern from the first runner).
- The quarters, model, features, baselines and metrics are all fixed in this document before any E2 output exists.
- The runner's protected-file hash guard is reused.

**Improvement criterion (pre-specified).** E2 counts as adding value only if all three hold:

1. The mean within-quarter ρ exceeds CF-dev by at least 0.20.
2. The quarter-bootstrap 95% interval of that difference excludes 0.
3. The MAE is not worse than CF-dev.

**Interpreting the outcome:**

- **Anything else means "no demonstrated value beyond carry-forward."**
- With 9 quarters of 5 provinces, only a large effect can pass. A failure would be informative, not a reason to try other models.
- Whatever the result, it is an **exploratory** claim about relative food-price stress, **not** about province hunger, and not a 75% accuracy claim.

## 5. Supported findings vs hypotheses

**Supported by existing results:**

- The binary target is dominated by the single regional SWS value (65% of variance).
- Under the training-only threshold, the test period is 91% HIGH because of regime drift, not imbalance in the training data.
- MODEL-B2's errors are whole-quarter misses of the regional level. It underpredicted HIGH in 2023-Q4, 2024-Q4 and 2025-Q1, even with high SWS inputs.
- MODEL-A acts as a near-always-HIGH classifier and has negative within-quarter ranking.
- No model differentiates provinces reliably (mean ρ ≤ 0.29).
- MODEL-B2 adds no value beyond carry-forward or the Equation 3 rule.

**Hypotheses needing tests:**

- H1: LightGBM defaults are too coarse for 40–75 rows.
- H2: the training/test missingness mismatch misleads the trees.
- H3: the trees cannot extrapolate beyond the training levels.
- Whether province-varying inputs predict the CPI deviation better than carry-forward. This is E2.
