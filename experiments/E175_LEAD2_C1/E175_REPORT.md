# E175: LightGBM Lead-2 C1 (2026-11-07)

**Outcome: no defensible candidate. No new model was run, so Lead 2 does not pass C1 and E168 is unchanged.**

## 1. C1, verified (`app/e156/leads.py`, unchanged)
`C1 = accuracy > majority AND low_bound > majority`, strict comparisons, rounding only in printed output.
majority = 47/72 = 0.652778; n_eff = 72 / (1 + (1.8 - 1) x 0.726) = 45.5466; low_bound = acc - 1.96 sqrt(acc (1 - acc) / n_eff).

| Correct | Accuracy | Low bound | C1 |
|---|---|---|---|
| 55 (E168 Lead 2, reproduced) | 0.763889 | 0.640550 | fail |
| 56 (minimum to pass) | 0.777778 | 0.657038 | pass |

## 2. Lead-2 errors (`lead2_error_analysis.csv`)
17 errors: 15 false HIGH, 2 false LOW; 9 within 0.05 of P(HIGH) = 0.5. ENNS 2018 13/22, ENNS 2019 21/25, ENNS 2021 21/25.
The survey anchor alone over-forecasts by +0.36 / +0.29 / +0.25 logit (2018 / 2019 / 2021); E168 leaves +0.19 / +0.11 / -0.02.
ENNS 2018 and 2019 forecasts train on one survey transition (NNS 2013 -> FNRI 2015); 2021 forecasts on three.

## 3. Why no candidate was run (`candidate_registry.csv`)
Every LightGBM direction in the E175 brief was already evaluated on these 72 rows: lower complexity, regularization, depth and
leaves, training-only feature selection, lead-exact training, seed bagging and round-aware selection (E171, E172, E173). The
training-only selection over all of them (E172, pre-declared) gave 53/72. SIMPLE (59/72) is a post-hoc subset whose result is known.
The one untested direction, class weighting against false HIGHs, comes straight from the Lead-2 error analysis. E175's acceptance
rule requires selection without the held-out Lead-2 outcomes. That is not possible for any of these candidates any more, so
running one would be another try on the same rows, which the brief forbids ("do not continue tuning against the same evaluation set").

## 4. Comparison (Lead 2, existing results only; `evaluation_comparison.csv`)
| Model | Correct | Low bound | C1 | C2-C6 | Brier | ROC-AUC | Status |
|---|---|---|---|---|---|---|---|
| E168 (served) | 55 | 0.641 | fail | pass | 0.137 | 0.887 | pre-registered |
| E171 | 53 | 0.608 | fail | pass | 0.140 | 0.883 | pre-declared |
| E172 (LightGBM) | 53 | 0.608 | fail | pass | 0.145 | 0.869 | pre-declared |
| SIMPLE (LightGBM) | 59 | 0.708 | pass | pass | 0.144 | 0.874 | post-hoc; frozen in E173 |
| 5-seed bagging (LightGBM) | 54 | 0.624 | fail | pass | 0.136 | 0.891 | diagnostic |
| E166 (not LightGBM) | 57 | 0.674 | pass | pass | 0.139 | 0.894 | reference |

## 5. Answers
1. Did Lead 2 pass C1? **No.** No new candidate was evaluated; E168 stays at 55/72.
2. All C1-C6? **No** (C2-C6 pass, C1 fails).
3. Change in predictive performance? **None.** Nothing was refitted.
4. Brier or ROC-AUC worse? **Not applicable.** For reference, SIMPLE's 59/72 comes with a worse Brier (0.144 vs 0.137) and ROC-AUC (0.874 vs 0.887).
5. Selected without the held-out outcomes? **No candidate could be.** That is why none was run.
6. Protected artifacts modified? **No** (`PROTECTED_ARTIFACTS_CHECK.md`).

## 6. What would make a genuine Lead-2 pass possible
Independent provincial HFIAS rows after 2021, with standard errors, from at least 40 provinces. The frozen E168 and SIMPLE would
then be compared once on them (`backend/app/e174/evaluate_future.py`). Until then the defensible statement is: Lead 2 meets the
study's 75 % reliability rule (76.4 %) and five of six strict criteria; C1 is one province-year short at n_eff = 45.5.
