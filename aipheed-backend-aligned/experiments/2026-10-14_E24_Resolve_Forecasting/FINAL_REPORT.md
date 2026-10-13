# E24 Final Report: resolving the forecasting failures and completing the Chapter I objectives

**Date:** 2026-10-14.

**Isolation:** all E24 work is in this folder.

- `backend_dev/` = an isolated copy of the backend code (no data, databases or models).
- `dashboard_dev/` = an isolated frontend copy.
- `backend/`, `frontend/`, E17, E18 and E23 were not modified; verified by git and the hash lists.
- Nothing was committed, pushed, merged or deployed.
- **E23 had left 16 modified tracked files in `aipheed-backend-aligned/`** (uncommitted). E24 preserved them; your keep/revert decision is in `BUG_FIXES.md` §0.

## Unambiguous answers

| Question | Answer |
|---|---|
| **Does accuracy exceed 75%?** | **Yes, numerically, and without skill.** On the approved target at lead 1, the E24 final candidate scores **0.875**. Always-HIGH scores 0.925 on the same 40 rows. |
| **Does the model beat persistence and every other applicable baseline?** | **No.** E24-F **ties** persistence: 0.875 vs 0.875, Brier 0.131 vs 0.125, the same 5 errors, p = 1.0. It beats B6 (LightGBM news-only; Holm-adjusted p = 0.047) but **not** B1, B2, B3, B4 or B5 after Holm adjustment. The proposed combined LightGBM (0.825) loses to persistence. |
| **Does the result generalize to unseen quarters?** | **Not assessable.** No untouched authorized holdout exists: 2026-Q1/Q2 have been viewed and 2026-Q3+ is protected. Development quarters do not count. |
| **Furthest lead time meeting the reliability rule** | **None**, at every lead, for both targets. The rule itself is researcher-declared and awaits adviser approval. |
| **Hypotheses** | **H1, H2, H3: not testable** (the approved target has ≤ 3 LOW test rows at every lead; minimum 5). **H4, H5: awaiting genuine DA Region IV-A responses.** None is supported or rejected. |
| **Are province-specific forecasts defensible?** | **Not as food-insecurity distinctions.** 65.2% of label variance is the regional SWS level, which is identical for the 5 provinces. Provincial differences come only from relative food inflation (D). Even D > 0 (exploratory T2) is forecast no better than persistence (0.655; the final candidate 0.618). |
| **Are all 142 LGU rankings defensible?** | **Partly.** Codes, names, populations and the formula are verified for all 142, and the computation is exact and deterministic. But **126 LGUs lack a PSA municipal poverty estimate** in the authorized data, so their within-province order reflects density only. This is now labelled per LGU. Completing it needs the PSA 2021 SAE workbook. |
| **Is the 2027-Q1 forecast supported by authorized data?** | **No.** The cycle returns INSUFFICIENT_DATA: no authorized 2026-Q4 news; 2026-Q3 government data, CPI and SWS protected; no qualifying model; the cutoff (2026-12-31 23:59:59 PHT) not reached. **Zero articles are shown; nothing substituted.** |

## Results by Chapter I objective, SOP question and hypothesis

| Item | Status | Evidence |
|---|---|---|
| **O1** NLP pipeline (XLM-R zero-shot + BERTopic → bias-corrected FSSI) | **Implemented.** The per-quarter NLP stage is now wired into the quarterly cycle (eligible articles only). BERTopic is not re-run per cycle (needs the unauthorized corpus). | `QUARTERLY_PIPELINE_AUDIT.md` |
| **O2** Accuracy, precision/recall, F1, AUC-ROC, lead times via walk-forward | **Computed** for all models at leads 1–6, on both targets, with balanced accuracy and Brier | `BASELINE_COMPARISON.csv`, `runs/.../results.json` |
| **O2-V** Furthest reliable horizon | **None** | as above |
| **O3** 142 LGU rankings | **Computed and verified.** 126 LGUs carry a labelled substitute; PSA workbook pending. | `LGU_RANKING_VALIDATION.csv` |
| **O4** Comparison with baselines | **Done** on identical rows (six H3 baselines; Objective 4's four map onto B1/B3/B4/B2) | `BASELINE_COMPARISON.csv` |
| **O5** Dashboard, alerts, ISO/IEC 25010, NNS anchor | Dev dashboard works locally (not deployed). Instruments and result-entry workflow ready. NNS 2023 verified (E23); NNS 2019 not verifiable. | `TEST_RESULTS.md`, `instruments/` |
| **SOP Q1–Q5** | Q1 descriptive SHAP only; Q2 none; Q3 not beaten; Q4/Q5 awaiting participants | — |
| **H1–H3** | Not testable | — |
| **H4/H5** | Awaiting genuine responses | — |

## The forecasting goal: criteria C1–C9 (frozen before running; approved target, lead 1)

| Criterion | E24-F result |
|---|---|
| C1 accuracy > 75% | **Met** (0.875) |
| C2 beats the strongest baseline | **Not met** (ties persistence) |
| C3 not explained by HIGH dominance | **Not met** (balanced accuracy 0.779 = persistence's) |
| C4 holds across quarters | **Not met** |
| C5 information beyond persistence | **Not met** (0 of 5 label changes anticipated) |
| C6 reliability rule | **Not met** (lead not evaluable) |
| C7 no leakage | **Met** (assertions pass in every fold) |
| C8 reproducible | **Met** (byte-identical seals) |
| C9 generalizes to unseen quarters | **Not assessable** |

**→ The forecasting goal is NOT met.**

## Why, in one paragraph

Persistence's 5 errors are exactly the 5 rows whose label changed. All 5 are driven by moves in the **target quarter's regional SWS hunger level**, which is unpublished at the forecast origin (see `ROOT_CAUSE_ANALYSIS.md`). No available feature (news, government indicators or label history) anticipated any of them. The persistence-gated candidate therefore correctly fell back to persistence.

To show a model beating persistence with p < 0.05, it would have to fix all 5 errors, one per quarter, without a single new error. Even then, a power simulation shows that a realistic model needs **more than 40 new labelled quarters**. An excellent one (75% of changes anticipated, no false flips) needs about **12–16**. More tuning on the same 8 quarters would only overfit them, so it was not done.

## Modifications implemented in E24

1. **Reproduction.** E23 reproduced exactly, and the required models re-run identically.
2. **Target audit.** Variance decomposition, unanimity, change rows and threshold drift.
3. **Frozen E24 protocol** with predeclared acceptance criteria C1–C9, a persistence-gated final candidate, 15 ablation arms (feature groups G, N, P; LR, nested-C LR, nested LightGBM), and an **exploratory provincial target (T2)** reported separately.
4. **Paired, quarter-level statistics:** sign-flip (accuracy, Brier), AUC permutation, Holm, leave-one-quarter-out.
5. **Minimum-data power analysis.**
6. **Prospective-holdout machinery:** candidates frozen; `seal_prospective.py` refuses until 2026 features are authorized.
7. **LGU v2:**
   - identity validation of all 142 LGUs;
   - honest labelling of substitutes;
   - deterministic tie rule;
   - PSA SAE workbook ingestion with PSGC conversion (bug found by test and fixed: Excel-numeric codes).
8. **Pipeline:** schema/duplicate/conflict validation, NLP stage, model/feature version records.
9. **Dashboard:** criteria C1–C9 and "Goal NOT met" displayed, T1/T2 separated, poverty-value kind shown. PDF from the same sources. jsdom render tests.
10. **Instruments:** a result-entry workflow and a header-only template; the scorer refuses non-Forms exports.

## Post-hoc observations (descriptive only; NOT used to select anything)

**Approved target (T1).** LightGBM on the persistence-history block alone reached 0.925 (2 more correct rows than persistence, p = 0.25). **Not significant.**

**Exploratory provincial target (T2).** Logistic regression on persistence history:

- Brier 0.193 vs persistence 0.345 (p = 0.003 uncorrected; about 0.045 Bonferroni across ~15 arms);
- AUC +0.13 (p = 0.044);
- accuracy 0.727 vs 0.655 (p = 0.125, not significant).

This suggests **mean reversion in provincial relative food inflation** that binary persistence ignores. Both arms are frozen as **prospective** candidates. They can only be validated on future authorized quarters.

## Remaining blocked items (exact dependencies)

See `ADVISER_AND_AUTHORIZATION_CHECKLIST.md` and `DATA_ACQUISITION_REGISTER.md`. In short:

1. Your authorization of 2026 features and news (prospective sealing; 2027-Q1).
2. New labelled quarters (≥ 8 for any claim; ≈ 12–20 for adequate power).
3. The PSA 2021 SAE workbook (manual download; 403 to automation).
4. Adviser decisions B1–B7.
5. The 50 DA Region IV-A evaluators' genuine responses.
6. An independent provincial food-insecurity outcome (FNRI microdata, CBMS, or a DA/LGU FIES module) to validate provincial claims.
7. Deployment approval.
