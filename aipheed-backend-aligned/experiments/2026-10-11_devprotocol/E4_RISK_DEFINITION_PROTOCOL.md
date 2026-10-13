# E4 Protocol: Comparing HIGH/LOW Risk Definitions

**Status:** fixed before any E4 code was written or run.

**What E4 is:**

- An isolated experiment only.
- It does **not** change the thesis target, production, or the dashboard.

**Purpose:** test whether a consistently defined HIGH/LOW label on the approved Equation 3 stress score can (a) keep a fixed meaning over time and (b) distinguish provinces, and whether LightGBM can predict it.

**Why the current method produces mostly HIGH** (details in `RISK_CLASSIFICATION_REPORT.md`):

- Equation 3 is stress = SWS Balance-Luzon hunger (%) + 2 × (provincial food CPI YoY − five-province mean, in percentage points).
- Its quarter mean equals the regional SWS value, so all five provinces move together.
- Balance-Luzon hunger rose from 8.7–15.4% (2021–2023) to 14.3–25.3% (2023-Q4 to 2025).
- So any threshold derived from earlier data labels nearly every 2024–2025 row HIGH.

## 1. Evidence for an official threshold

**None was found.**

| Source checked | Result |
|---|---|
| Thesis (Chapter III) | Defines HIGH as "above the global median", a sample-relative rule |
| Project documents and code | No DA or government cutoff for SWS hunger or for the stress score |
| SWS | No cutoff for its hunger series in the stored evidence. No new SWS material was retrieved. |
| IPC / FIES phase thresholds | Belong to other instruments; not applicable to SWS hunger |

**Consequence:** every definition below is **empirical**. None is an official DA or government risk classification.

## 2. Candidate definitions (all keep the Equation 3 stress formula)

**τ0** = the median of all Equation 3 stress scores whose labels were **published before the first evaluation origin** (2023-10-01; 8 quarters, 40 rows). It is computed once, then **held fixed**.

This is the thesis's own statistic (the median), but frozen at the start of evaluation, so that HIGH means the same absolute level in every fold. The same rule applied at the prospective 2026-Q3 origin gives the approved 14.345.

| ID | Rule | Threshold source | Fixed meaning over time? | Leakage-free on 2023–2025? | Can distinguish provinces within a quarter? |
|---|---|---|---|---|---|
| **D-A** (approved, as implemented) | stress > 14.345 | Median of all 80 labelled 2021–2025 rows (Equation 3 "global median") | Yes | **No.** Uses the test quarters. | Only when SWS is near 14.345 |
| **D-B** (E1/E3 primary) | stress > τ_T | Median of each fold's eligible training rows | **No.** Drifts from 10.8 to 14.1. | Yes | Only when SWS is near τ_T |
| **D-C** (absolute, frozen reference) | stress > τ0 | Median of the labels published before 2023-10-01 | Yes | Yes | Only when SWS is near τ0 |
| **D-D** (frozen reference + provincial priority) | stress > **max(τ0, SWS_t)**, i.e. stress > τ0 **and** the province's food-price deviation > 0 | τ0 as in D-C; 0 is the regional mean by definition | Yes | Yes | **Yes.** Within a quarter, only provinces above the regional food-price mean can be HIGH. |

**Equivalence used for D-D:** since mean_p(stress_p,t) = SWS_t, the condition "deviation > 0" is exactly "stress_p,t > quarter mean of stress". Ties count as LOW.

**Selection criteria (fixed now, applied to definitions, not to model results):**

1. The Equation 3 formula is preserved.
2. Meaning is fixed over time.
3. The threshold is leakage-free.
4. Provinces can be distinguished within a quarter.

**Applying the criteria a priori:**

- D-C meets criteria 1–3.
- D-D meets all four.
- D-A fails criterion 3 on retrospective data. It meets it prospectively.
- D-B fails criterion 2.

**Model results do not change this assessment.** A definition is never chosen because LightGBM scores better on it.

**D-D's limitation:**

- Its province component is **relative food-price pressure**: the only province-specific part of Equation 3.
- It is not a province-level hunger measure. No province hunger outcome exists.

## 3. Evaluation (one run per definition; nothing tuned)

**Model and folds:**

| Item | Value |
|---|---|
| Folds | The 7 E1/E3 test quarters (2023-Q4 to 2025-Q4), with Rule L training eligibility (≥ 8 quarters) |
| Model | The **E3 LightGBM configuration, unchanged:** 7 inputs; `num_leaves=4`, `min_child_samples=5`, `n_estimators=100`, `learning_rate=0.05`, seed 42; `scale_pos_weight` from fold training labels; monotone +1 on `last_published_stress` and `sws_hunger` only |
| Training labels per fold | Computed with the same definition and threshold as the test labels: 14.345 (D-A), τ_T (D-B), τ0 (D-C), or τ0 plus each training quarter's own quarter mean (D-D) |

**Baselines:**

| Baseline | Rule | AUC score |
|---|---|---|
| Carry-forward | The province's latest published label under the same definition | Margin `last_stress − τ` for D-A/B/C. **AUC not computed for D-D**, a two-condition rule with no natural single score. |
| Equation 3 rule | Origin-known s = SWS input + 2·`cpi_rel` > τ. For D-D: s > τ0 **and** `cpi_rel` > 0. | Margin `s − τ` for D-A/B/C. **AUC not computed for D-D.** |
| Always-HIGH and always-LOW | References only | Undefined |

**Metrics, per definition and predictor:**

- label counts: all 80 labelled rows, the 35 test rows, and per quarter;
- accuracy and balanced accuracy;
- HIGH precision, HIGH recall and LOW recall;
- ROC-AUC where meaningful;
- confusion matrix;
- per-quarter and per-province results;
- the number of test quarters with mixed actual labels, and with mixed predicted labels;
- a quarter-bootstrap paired balanced-accuracy difference against carry-forward and Equation 3 (10,000 draws, seed 42).

**Decision rule per definition** (the same as E3; exploratory):

| Verdict | Condition |
|---|---|
| Improvement | Balanced-accuracy gain over the better baseline ≥ 0.10, the CI excludes 0, and accuracy is not below carry-forward |
| Non-inferiority | Balanced accuracy ≥ better baseline − 0.05 |
| No demonstrated improvement | Otherwise |

## 4. Disclosures

- **E4 is the fourth analysis on these reused quarters.** Results are exploratory; n_eff is about 7 quarters.
- **D-A and D-B labels on these quarters were already seen in E1 and E3.**
- **Protected 2026 data:** not used. The production `backend/` data already contains 2026-Q3/Q4 food CPI rows (found during the trace; not used here; reported).

**Safeguards (reused from E1 and E3):**

- the label vault: training access only to quarters before the target; test labels revealed after that fold's predictions are written;
- the protected-file hash guard, now also covering the E1, E2 and E3 run folders;
- production isolation;
- a fresh `runs/<UTC>_E4/` folder.
