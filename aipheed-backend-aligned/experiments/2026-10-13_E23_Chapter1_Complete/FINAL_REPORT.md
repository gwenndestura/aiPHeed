# E23 Final Report: Chapter I objectives, hypotheses, quarterly forecasting and the accuracy goal

**Date:** 2026-10-13.

**Scope:** isolated development backend and dashboard copy only. Nothing was committed, pushed, merged or deployed. Production (`backend/`, `frontend/`, served models) was not changed.

**Full tables:** `RESULTS_TABLES.md` (generated from the sealed runs).

## 1. Status by objective, SOP question and hypothesis

| Item | Status | Evidence | Remaining blocker |
|---|---|---|---|
| **O1** NLP pipeline → bias-corrected FSSI, latent patterns | Built; features present for 2021–2025 | `features_fused`; PHT boundary fix F1 | Corpus re-audit and FSSI rebuild need the news corpus (not authorized). FSSI is sparse and largely forward-filled (prior audits). |
| **O2** Metrics I–V, walk-forward lead times | **Computed** at leads 1–6 (7–8 have no origin) | E23 tables | **No lead is evaluable** under the primary target (≤ 3 LOW test rows). Maximum reliable lead: **none**. |
| **O3** 142 LGU rankings | **Verified** (independent = backend, 142/142) | `rankings/` | 2027-Q1 ranking unavailable (no forecast). 126 LGUs use province-mean poverty. |
| **O4** Comparison with baselines | **Done**, all six H3 baselines + PSA-only supplement, identical rows | E23 tables, paired tests | The proposed model does not beat persistence on the primary target |
| **O5** Dashboard, alerts, ISO evaluation, NNS anchor | Dev dashboard works locally; NNS 2023 verified | `DASHBOARD_RANKINGS_AND_QUALITY.md` | Deployment needs your approval. ISO evaluation needs the 50 DA evaluators. NNS 2019 not verifiable. |
| **SOP Q1** strongest predictors | Descriptive SHAP. At lead 1 (primary), price **levels** dominate (`food_cpi` first); FSSI ranks 7th of 44; news block 5.7% of SHAP. | `fold_meta_origin.json` | Not a test (H1 not testable) |
| **SOP Q2** furthest reliable lead | **None** under the frozen rule | E23 | More evaluable quarters with LOW cases |
| **SOP Q3** proposed vs six baselines | See Section 2 | E23 | — |
| **SOP Q4** rankings reflect vulnerability | Awaiting DA evaluators | `instruments/` | Participant data |
| **SOP Q5** ISO/IEC 25010 assessment | Awaiting DA evaluators | `instruments/` | Participant data |
| **H1** | **Not testable** (primary). Sensitivity: not rejected. | E23 | — |
| **H2** | **Not testable** (0 evaluable leads; the rule needs ≥ 2) | E23 | — |
| **H3** | **Not testable** (primary). Sensitivity: not rejected. | E23 | — |
| **H4** | **Awaiting participant data** (50 DA Region IV-A evaluators) | `instruments/DECISION_RULES.md` | Data collection + adviser approval of the rules |
| **H5** | **Awaiting participant data** | same | same |

## 2. Direct answers

**1. Did the proposed model outperform each of the six baselines?** **No.**

On the **primary target** (training-window median threshold), lead 1, 8 origins, 40 rows (37 HIGH / 3 LOW; **not evaluable**):

| Model | Accuracy | AUC | Brier |
|---|---|---|---|
| Proposed | 0.825 | 0.703 | 0.142 |
| Naive persistence | 0.875 | 0.779 | 0.125 |
| LightGBM, government only | 0.850 | 0.649 | 0.131 |
| Logistic regression, news only | 0.600 | 0.802 | — |

So the proposed model is beaten by persistence on all three metrics. On the **sensitivity target** (fixed 14.6; evaluable at lead 1, 35/5):

- the proposed model has the highest AUC, 0.760, with origin-cluster 95% CI 0.41–0.97;
- its Brier is 0.214;
- no AUC difference is significant (all Holm-adjusted p = 1.0);
- the best raw Brier p is 0.094 vs persistence (Holm 0.47);
- government-only LightGBM has higher accuracy (0.775 vs 0.750).

At leads ≥ 2, every model's AUC is unstable or below 0.5, with 1–3 LOW rows.

**2. Consistent across independent origins, or one quarter?** Not consistent. On the sensitivity target, the AUC advantage over B3, B5 and B6 **changes sign** when single origins are left out. Persistence's errors are spread one per origin (Section 3).

**3. Furthest lead time meeting the frozen reliability rule:** **none**, under both targets.

**4. Null hypotheses:**

| Hypothesis | Decision |
|---|---|
| H1, H2, H3 | **Not testable** under the primary target |
| H1, H3 (sensitivity target) | Not rejected |
| H2 (sensitivity target) | Not testable (only one evaluable lead) |
| H4, H5 | Awaiting participant data |

**None was rejected.**

**5. Was the 2027-Q1 forecast produced using only eligible, authorized information at the declared cutoff?** **No forecast was produced.** The cycle ran and correctly returned `INSUFFICIENT_DATA` (record `f0c27087…`). The cutoff (2026-12-31 23:59:59 PHT) has not passed, and the required inputs are missing or unauthorized.

**6. Does it use only eligible Q4 2026 news, with future news excluded everywhere?** No Q4 2026 news is authorized, so **zero** articles are shown. The exclusion rules (publication time in PHT, cutoff, quarantine of undated articles, duplicates) are enforced in the backend, the API record, the dashboard and the PDF, and are tested. **Nothing is labelled "Q4 news" that is not.**

**7. Is the data complete for the claims made?** For 2021–2025 back-tests: yes, with the gaps in `DATA_COMPLETENESS_AND_MISSING_REGISTER.md` (M6–M12). **For 2027-Q1: no.** It is missing:

- Q4 2026 news;
- 2026-Q1–Q3 news and government features;
- July–December 2026 CPI;
- the Sept/Dec 2026 SWS rounds;
- a promoted model.

126 of 142 LGUs lack LGU-specific poverty values.

**8. Can the pipeline advance to 2027-Q2 and later?** **Yes, mechanically.**

- `quarterly_update advance` plus configuration-driven periods.
- Tested on the 2027-Q1 → 2027-Q2 transition: target, news window and exclusions advance together, and earlier records stay reproducible.
- It still needs authorized inputs each quarter.

**9. Late, unavailable, unauthorized or revised data:**

| Case | Result |
|---|---|
| Late | `NOT_AVAILABLE_BY_CUTOFF` |
| Unavailable | `MISSING` / `STALE` → INSUFFICIENT_DATA; stale data is never relabelled |
| Unauthorized | `BLOCKED`; content never read |
| Revised | New vintage with a required note; old vintages kept; recomputations labelled retrospective |

**10. Bugs fixed, and did they change a conclusion?**

| Fix | What |
|---|---|
| F1 | Philippine-time quarter boundaries for news |
| F2 | A missing province forecast silently ranked as zero risk |
| F3 | A forecast cycle with cutoff, news window, authorization and vintage control |
| F4 | Withdrawn second-agency references (incl. the admin e-mail default) |
| F5 | Two edge bugs in the new code, caught by its tests |

**No scientific conclusion changed.** F1's impact is unmeasured: the corpus is not authorized and the features were not rebuilt.

**11. What needs your authorization, external providers, participants or deployment approval:**

1. **Data authorization, file by file:**
   - 2026-Q4 news (and 2026-Q1–Q3 news) with verified publication timestamps;
   - 2026-Q3/Q4 government series and provincial CPI;
   - the Sept/Dec 2026 SWS rounds, opened only after forecasts are frozen.
2. **Adviser decisions:**
   - the reliability rule (O2-V/H2);
   - the H4/H5 decision rules (`instruments/DECISION_RULES.md`);
   - the threshold definition (training-window median vs fixed 14.6);
   - whether supplementary SWS rounds may define labels (M6);
   - the Chapter I corrections (44% figure, Objective 4 vs H3, NNS 2019).
3. **Participants:** the 50 DA Region IV-A evaluators (questionnaire, consent, facilitator guide and scorer are ready).
4. **External providers:**
   - PSA RSSO IV-A for LGU poverty estimates and provincial CPI release dates;
   - FNRI for regional or provincial FIES tables.
5. **Deployment and dependency changes:**
   - deploying the dashboard;
   - fixing the 20 npm vulnerabilities in `frontend/`;
   - promoting any model;
   - wiring `/forecast-period` into the production frontend.

## 3. The mandatory forecasting-improvement goal (> 75% accuracy AND beating the strongest baseline)

**What was done:** E23-B, a separately frozen protocol (`IMPROVEMENT_PROTOCOL_E23B.md`, hash `5287b693…`).

- **Candidate features:** lagged published-label features (last S1, margin to threshold, D history, SWS trend, 4-quarter rolling means), all available at the cutoff.
- **Candidate models:** three feature sets (combined, government, compact), 24 regularized LightGBM configurations.
- **Selection:** nested chronological selection with an inner-chosen decision threshold.
- **Comparison rows:** identical to E23 (the sealed baseline predictions were reused).

**Result** (primary target, lead 1, 40 rows):

| Model | Accuracy |
|---|---|
| E23-B selected model | **0.850 (> 0.75)** |
| Naive persistence (strongest baseline) | **0.875** |
| Always-HIGH reference | 0.925 |

- E23-B corrects 1 row persistence missed and misses 2 that persistence got right.
- Sign-flip p = 0.875. **It does not beat the strongest baseline.**
- Inner selection dropped the news block in most origins (feature set FB or FC — no full news block — in 24 of 28 folds; FC keeps only FSSI and FSSI_lag1).
- On the sensitivity target: 0.750 (not > 0.75) vs government-only LightGBM 0.775.

**Why the target cannot be met legitimately on the current data:**

- **Accuracy above 75% is not informative here.** "Always HIGH" scores 92.5% at lead 1, because hunger rose after 2023 and nearly every test row is HIGH.
- **To beat persistence significantly, a model must be near-perfect.**
  - Persistence errs on 5 rows, **one in each of 5 different origins**.
  - The smallest attainable one-sided sign-flip p is 1/2^5 = 0.031.
  - Reaching it requires fixing all five errors while adding **no** new error in any origin.
  - Any further tuning on these same 8 development origins would overfit them.
- **The label is mostly regional.** 68% of its variance is the regional SWS level shared by all provinces, published 1–3 months after fieldwork. Its best predictor is its own last published value, which is persistence.
- **No untouched authorized holdout exists.**
  - 2026-Q1/Q2 outcomes were viewed in E18.
  - 2026-Q3 onward is protected.
  - "Robust on unseen quarters" cannot be assessed yet.

**Completion criteria:**

| Criterion | Status |
|---|---|
| Accuracy > 75% | **Met numerically (0.850), but without skill** (below always-HIGH) |
| Beats the strongest baseline | **Not met** |
| Robust on unseen quarters | **Not assessable** |
| Hypotheses | **None supported** (H1–H3 not testable; H4–H5 awaiting participants) |

**I do not declare the objective achieved.**

**Path to a legitimate test:**

1. Freeze the E23-B procedure (done).
2. Authorize 2026-Q3 features.
3. Seal forecasts for 2026-Q4 onward before their labels publish.
4. Score at ≥ 8 new origins with ≥ 5 LOW rows.

The E10 sealed 2026-Q4 forecast (manifest `a3903086…`) is the first such quarter.
