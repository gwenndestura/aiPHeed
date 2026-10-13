# LightGBM Improvement Plan (2026-10-11)

**LightGBM stays the primary model.** Carry-forward and the Equation 3 rule stay as comparison baselines.

**Not done:** nothing was trained, tuned or scored. The thesis target, labels, production model and dashboard are unchanged. No 2026 outcome data was accessed.

**Basis:**

- E1 run `20261011T111651Z` and its diagnosis (`MODEL_DIAGNOSIS_AND_NEXT_EXPERIMENT.md`);
- E2 run `20261011T113409Z_E2`;
- read-only checks today on prediction granularity, training/test ranges, and feature availability.

---

## 1. Why LightGBM underperforms

### Confirmed by existing artifacts

| # | Finding | Evidence |
|---|---|---|
| C1 | **The target is dominated by one regional value.** The quarter mean of Equation 3 stress equals SWS Balance-Luzon exactly; 65% of stress variance is between quarters. | Diagnosis §1.0 |
| C2 | **Temporal shift.** Training sets are balanced at τ_T, but the 2023-Q4 to 2025 test quarters are 91% HIGH (A-origin) and 86% HIGH (A-global). | E1 run |
| C3 | **The model did not use the regional level it was given.** In 2025-Q1 the SWS input was 18.1 against τ 13.2, yet MODEL-B2's mean p was 0.32. The quarters 2023-Q4, 2024-Q4 and 2025-Q1 account for 11 of its 15 errors. | E1 diagnosis |
| C4 | **Model complexity is effectively near-constant.** LightGBM defaults are `min_child_samples=20`, `num_leaves=31` and 100 trees. With 40–75 training rows, each tree has at most 2–3 leaves. | See granularity below |
| C5 | **Test values lie outside the training range.** Trees cannot extrapolate. | See ranges below |
| C6 | **Missingness differs between training and test.** 19–30% of the 44 inputs are missing in training rows, against 5–8% in test rows. | E1 diagnosis |
| C7 | **The thesis's news feature is nearly absent.** FSSI exists for only 0–5 of the 5 provinces in each quarter (63% missing in test rows, 69% in training rows); FSSI_accel is 89–92% missing. | Read-only check today |
| C8 | **The 44 inputs carried no usable signal beyond carry-forward at this horizon.** | E1: B2 is below carry-forward and Equation 3. E2: the B2 inputs did not rank provincial food-price deviations better than carry-forward (ρ 0.20 vs 0.38). |

**C4 granularity evidence:**

- In 2023-Q4, MODEL-B2 produced only **2 distinct probabilities** across the 5 provinces, and MODEL-A produced **1**.
- MODEL-A was also constant within 2024-Q1.
- The E2 regressor produced only 3 distinct values in 2023-Q4 and in 2024-Q1.

**C5 range evidence:**

| Fold | Training value range | Test value |
|---|---|---|
| 2024-Q2 (regional stress) | Training maximum 18.7 | 19.6 |
| 2024-Q4 (SWS input) | Training maximum 15.0 | 19.6 |
| 2025-Q1 (SWS input) | Training maximum 15.3 | 18.1 |

### Hypotheses that need testing

| # | Hypothesis | How it would be tested |
|---|---|---|
| H1 | With complexity sized to the sample and fewer inputs, LightGBM uses the level signal (SWS, last published stress) instead of noise | E3 (§3) |
| H2 | The training/test missingness mismatch itself caused wrong splits, rather than merely accompanying them | E3 uses inputs with ≤ 20% training missingness and 0% test missingness. Exceptions: `last_published_stress` is missing for 3 of the 8–15 training quarters (the earliest labels have no published predecessor), and FSSI, which is disclosed. |
| H3 | Monotone constraints on the level inputs prevent the inverted behaviour seen in 2025-Q1 | E3 |

**What cannot be fixed by modelling:**

- the regime shift (C2);
- the 3–5 LOW test rows;
- n_eff ≈ 7.

These limit any evaluation on the 2021–2025 data, whatever model is used.

## 2. Formulation options (assessed, not run)

**1. A smaller feature set: recommended.**

- 44 inputs for 40–75 rows (8–15 quarters, with 5 rows sharing most values) is far too many. A set of about 7 inputs is proportionate.
- The set should be chosen **a priori** from:
  - the structure of Equation 3: a regional hunger level plus a provincial food-price deviation;
  - thesis hypothesis H1: FSSI and the food CPI deviation;
  - timeliness at the origin.
- No feature importances were saved in E1 or E2, so the set below is not derived from test-set results.
- Earlier 10-08/09 studies ran ablations on the same quarters. That exposure is disclosed.

**2. The binary target.**

- The Equation 3 binary label is the approved thesis target, so it stays the primary target.
- Its weakness for DA: the median threshold changes meaning under A-origin (10.8 → 14.1) and is leaky under A-global. In this period it makes almost every quarter HIGH.
- Any change to the threshold needs **adviser approval**. E3 keeps both pre-specified analyses (A-origin primary pending approval; A-global secondary).

**3. LightGBM regression: kept as a later, separately documented alternative, not E3's primary.**

- Regressing Equation 3 stress would keep more information. But regression trees cannot predict above the training maximum (C5).
- Residualizing on carry-forward would fix that, but needs a published anchor for each training row. Under Rule L and WD5 that leaves only **4 evaluable folds** (2024-Q3 onward) at the 8-quarter minimum.
- The E2 relative-price target is **not** food insecurity and is not carried forward.

**4. Time-valid features with information beyond carry-forward.**

| Feature | Available at the origin | Note |
|---|---|---|
| Latest published SWS (`sws_hunger`) and its change (`sws_change`) | Yes | Includes the supplementary 2025 rounds |
| Latest provincial deviation (`cpi_rel`) and level (`food_cpi_yoy`) | Yes | WD1 proxy dates |
| Rice price acceleration | Yes | Development protocol |
| Unemployment | Yes | — |
| FSSI | **Mostly missing** (C7) | News from quarter T−1, the most timely input |

FSSI's coverage is a **data problem to fix before it can be tested** (see §5).

**5. Regularization and class weights: assessable with training data only.**

- **Class weights:** set from training labels, as before. Under A-origin they are about 1 already, because training is balanced. **They cannot correct the test-period shift.**
- **Regularization:** fixed a priori from sample size (below). Any selection must use inner walk-forward folds inside the training quarters. With 8–15 training quarters those inner folds are 3–10 quarters, so selection is noisy. **E3 therefore fixes complexity by rule, not by search.**

## 3. Recommended experiment E3: compact, constrained LightGBM classifier (NOT executed)

**Research question:**

> When sized to the available sample and constrained by Equation 3's structure, does LightGBM stop underperforming carry-forward and Equation 3 on the thesis target, and does it add value beyond them?

**Target:** the approved Equation 3 binary label, unchanged.

- **A-origin** (fold-specific training median τ_T) is primary, pending adviser approval.
- **A-global** (14.345, leaky) is secondary.
- Both are reported, as in protocol v4.

**Model:** LightGBM only. One configuration, fixed a priori:

| Setting | Value |
|---|---|
| `objective` | `binary` |
| `num_leaves` | 4 |
| `min_child_samples` | 5 (one quarter's rows) |
| `n_estimators` | 100 |
| `learning_rate` | 0.05 |
| `subsample`, `colsample_bytree` | 1.0 |
| `random_state` | 42 |
| `scale_pos_weight` | From the fold's training labels |
| Monotone constraints | **+1** on `last_published_stress` and `sws_hunger` (Equation 3: higher hunger level means higher risk); 0 elsewhere |
| Cut-off | 0.50 |

**Inputs (7, a priori):**

1. `last_published_stress`: the province's latest **published** Equation 3 stress, built from the carry-forward anchor;
2. `sws_hunger`;
3. `sws_change`;
4. `cpi_rel`;
5. `food_cpi_yoy`;
6. `rice_price_regular_accel`;
7. `unemployment_rate`.

**Missing data:** NaN is kept; LightGBM handles it natively.

**Pre-declared sensitivity (one only):** + FSSI, the thesis H1 predictor, with its 63–69% missingness disclosed.

**Evaluation design:**

- **Folds:** the same 7 time-ordered folds as E1 (2023-Q4 to 2025-Q4). Training data are the Rule L-eligible labels published before each origin, with at least 8 quarters.
- **Everything is fixed before execution:** thresholds, class weights, complexity, inputs and the cut-off. **Nothing is chosen using test quarters.**
- **Label vault, hash guard and production isolation:** reused from the E1 runner.

**Baselines:**

- carry-forward and the Equation 3 rule;
- always-HIGH and always-LOW, as references only;
- **E1 MODEL-B2 results, for the before/after comparison; not refitted.**

**Metrics, per quarter and pooled:**

- balanced accuracy (headline);
- weighted precision, recall and F1;
- HIGH recall and LOW recall;
- ROC-AUC, **computed for the baselines as well, using their score margins** (Equation 3: s − τ; carry-forward: last stress − τ);
- confusion matrices;
- test-set class counts;
- quarter-cluster bootstrap intervals for the paired differences against carry-forward and Equation 3.

**Decision rule (fixed now).** E3 **adds value** only if all three hold on the 7-quarter A-origin primary:

1. Balanced accuracy ≥ max(carry-forward, Equation 3) + 0.10.
2. The quarter-bootstrap 95% CI of the balanced-accuracy difference against the better baseline excludes 0.
3. Mean-quarter accuracy is not below carry-forward.

**Non-inferiority (a weaker, separately labelled result):** E3's balanced accuracy is within 0.05 of the better baseline, and HIGH recall is not below it. This would show that the reformulation fixed E1's underperformance, **not** that LightGBM adds value.

**What happens next under each outcome:**

- If E3 is non-inferior or better, **freeze** its configuration (hash it) for the protected 2026-Q3/Q4 prospective forecasts. There, 14.345 is leakage-free and equal to τ.
- If it is not, report that, and stop modelling on 2021–2025 data.

**How reused quarters and sample size are treated:**

- E3 is the **third** design evaluated on these quarters, so any result is exploratory and subject to forking-path bias.
- **LOW-class evidence:** 3 rows (A-origin) or 5 rows (A-global).
- **Effective sample:** n_eff ≈ 7.
- **Expected outcome:** with the current data, rule 2 is unlikely to be met unless the effect is large. A "no" is an informative outcome.

## 4. The > 75% requirement

The requirement remains, but **no LightGBM configuration can be guaranteed to meet it.**

**Evidence that does not count:**

- Always-HIGH reaches 91.4% and MODEL-A 77.1% only because 32/35 test rows are HIGH. Both have balanced accuracy ≤ 0.50.
- **Raw accuracy on an imbalanced test set is not evidence of forecasting skill.**

**Evidence a credible claim would need, all of it:**

1. **Independent temporal validation.** Forecasts frozen and hashed **before** the outcomes exist, on quarters never used in design.
2. **Enough independent units.** Rows within a quarter share the SWS outcome. At the quarter level, a 95% lower bound above 0.75 needs about **13 consecutive correct quarters** (0.025^(1/13) ≈ 0.753). Even treating rows as independent needs ≥ 32/35. The protected 2026-Q3/Q4 set (10 rows, 2 quarters) **cannot** establish it.
3. **Balanced performance.** Balanced accuracy and LOW recall are reported, not raw accuracy alone.
4. **Improvement over baselines.** It must exceed carry-forward and Equation 3, with an interval excluding 0.
5. **Verified inputs.** Publication dates verified (not proxied) and point-in-time vintages used.

**Within the approved 2021–2026 window:** the thesis can credibly report a pre-registered point estimate with an interval and a baseline comparison, **not** a demonstrated > 75%.

## 5. Data limitations and the minimum additional data

1. **Outcome units.** One regional SWS value per quarter (16 labelled quarters) is the binding limit. The most valuable addition is **province-level outcome data within 2021–2026**: it multiplies independent units by about 5. Candidates (none retrieved):
   - SWS province-level estimates, by request;
   - NNC/DOH OPT Plus provincial malnutrition, annual;
   - CBMS provincial indicators;
   - DSWD provincial caseloads.
2. **FSSI coverage.** This is a data-pipeline fix, not new outcomes. It needs investigation of the corpus coverage and the data-sufficiency threshold that leaves most province-quarters empty. FSSI cannot be tested as the thesis's predictor until then.
3. **Verified publication dates.** The 19 RSSO IV-A provincial CPI dates, for any strict or real-time claim.
4. **No fabricated or back-filled labels.** No pre-2021 data, per the approved window.

## 6. Evidence required before the next training run

| # | Requirement |
|---|---|
| 1 | Your authorization of E3 as specified in §3, with no changes after any result |
| 2 | A written E3 protocol file and a runner with tests (label vault, hash guard, production isolation, monotone and complexity settings asserted, the 7 inputs asserted), passing in the full suite |
| 3 | Disclosure, in the protocol, that E3 is the third design on these quarters and that earlier ablations exist |
| 4 | Adviser position on A-origin vs A-global as primary. Not blocking: both are reported, and the fallback is fixed. |
| 5 | Optional but recommended: the FSSI coverage investigation, before any FSSI-based claim |
