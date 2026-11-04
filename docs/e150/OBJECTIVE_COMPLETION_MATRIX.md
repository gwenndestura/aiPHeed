# Objective completion matrix

**Verdict: E150 does not pass its gates. Promotion is not requested. Production and the dashboard are unchanged.**

Evidence labels: **D** development (2018, 2019), **R** retrospective, including opened 2021, **H** sealed holdout, 12 unopened areas.

## Success gates, Lead 1

| Gate | Requirement | Result | Status |
|---|---|---|---|
| Target | Food-insecurity prevalence at panel threshold | Any-level HFIAS ≥ 50 %. **Panel's measure still unconfirmed** | **PASS, pending confirmation** |
| Lead 1 | Next calendar quarter, as-of inputs | Issue 2026-10-01, target Q1 2027; release rules applied | **PASS** |
| Accuracy | ≥ 75 % out of sample with balanced performance | R 0.847, balanced 0.634; H 0.75, balanced 0.81 | **PARTIAL:** balanced is weak on R |
| Better than baselines | Beats simple rules | Above always-HIGH 0.806 and persistence 0.819 on accuracy; Brier vs persistence −0.013 [−0.046, +0.012]; on 2021, worse (+0.023) | **FAIL** |
| HIGH and LOW detection | Credible both ways | HIGH 0.98; LOW 0.29 (R), 0.63 (H) | **FAIL on R** |
| Calibration | Reliable probabilities | R: ECE 0.034, slope 1.05. H: ECE 0.28, overconfident | **PARTIAL** |
| Intervals | Defensible | R coverage 0.89 | **PASS on R** |
| Provincial differentiation | Genuine | 0 of 10 pairs separated | **FAIL** |
| Trigger groups | Genuine inputs, used | Selected A-H: poverty only. A-G: all five (climate 29 %, remittances 29 %, poverty 21 %, market 6 %, employment 4 %) | **FAIL for selected arm; PASS for A-G, with national limits** |
| News value | Before any claim | Holm fails; placebo 30 % | **FAIL** |
| Quarterly value | Response beats history on held-out SWS area | L1 −0.029 [−0.059, −0.0002]; significant to L3. Survey-fitted loading 0 | **PASS at area level; not carried to provinces** |
| Updating vs frozen | Beats frozen | −0.015 [−0.036, +0.005] | **FAIL** at L1; passes at leads 3 to 8, but partly a comparison artefact |
| Maximum reliable lead | Predefined cumulative | **0 quarters;** L1 fails R4, R8 | **Determined; result fails thesis need** |
| Reproducibility | Locks, seeds, predictions | Lock, 2 deviations logged, seals committed before scoring | **PASS** |
| No leakage | Temporal and geographic | Release rules, as-of fits, cross-fitted levels; E144's defect fixed | **PASS, by construction and tests** |

## Thesis objectives

| Objective | Status | What's done | What's missing |
|---|---|---|---|
| **1. XLM-RoBERTa, BERTopic, FSSI, news features** | **Built; not validated** | Two-tier pipeline; sentence attribution 96 %; bias correction; province-quarter features | Local sentiment accuracy; demonstrated value |
| **2. LightGBM, Lead 1, 75 %, max lead** | **Partial** | LightGBM in the level and residual; Lead 1; 0.847 and 0.75 at surveyed rows | Beating persistence; LOW recall; reliable lead above 0 |
| **3. 142 LGU rankings** | **Built; can't be directly validated** | Rankings, weight sensitivity, rank uncertainty | Municipal outcome; firm provincial forecast |
| **4. Four baselines** | **Done** | Persistence, PSA-only, NLP-only, logistic, plus drift, always-HIGH, always-LOW | None |
| **5. Dashboard, ISO/IEC 25010, face validity** | **Not done** | Face validity in `docs/e148/FINAL_REPORT.md` | Deployment held back by the gates; 50 real DA evaluators |

## Exact reasons for failure

| Failure | Reason | Minimum to resolve | Action |
|---|---|---|---|
| Doesn't beat persistence | Detectable gap about 0.07 with this sample; observed 0.013 | **Many more unseen rows;** about 25 times the evidence at this effect size, so at least several new rounds | Score sealed forecasts as FNRI releases come |
| Low LOW recall | 14 LOW rows of 72 at the 50 % line | More LOW cases, which later rounds may supply | Same; do not change the threshold |
| No provincial separation | Four provinces share nearly the same structural inputs; intervals ±15 to 20 points | CBMS 2024 or FNRI household microdata | Your data decision |
| News | One national-outlet-dominated source, weak attribution, few outcomes | Labelled sample, local sources, more rounds | Your decision on labelling |
| Employment, remittances | National history only | PSA FIES 2015, 2018, 2021 files; LFS microdata | PSA request; your rule currently excludes this |
| Quarterly province validation | No repeated provincial measurement | Provincial survey in at least 2 consecutive quarters | Partnership; no public source found |

## Decision needed: which arm goes forward

| | **A-G (uses all five groups)** | A-H (selected by the locked rule) |
|---|---|---|
| Thesis requirement: five groups as inputs | **Yes** | No |
| LightGBM main role | **Yes, level and residual** | Level only |
| Quarterly movement | **2.4 to 2.8 points, by province** | Almost none beyond trend |
| Accuracy, pool | 0.861 | 0.847 |
| LOW recall, pool | **0.429** | 0.286 |
| Balanced accuracy, pool | **0.697** | 0.634 |
| Brier, pool | 0.124 | **0.119** |
| Prevalence error | 8.23 | **7.09** |
| Calibration slope | 0.71, overconfident | **1.05** |
| Live spread | 37.4 to 50.5 | 34.5 to 39.8 |

**My recommendation: carry A-G forward as the thesis model, stated openly as a requirements-based choice.** It is the only arm that meets your stated requirement, with better classification and province detail. Its costs are overconfident probabilities and larger prevalence error, and these should be disclosed. Fix this choice before the next test. It would not make any gate pass retroactively, and it must not be presented as selected by the locked rule.

## Next step that can produce new evidence

The Q1 2027 forecast is sealed (`f773fbff…`). The next independent evidence is SWS 2027 at area level, and any new FNRI round. **No further model search on these rows will add evidence.** All HFIAS rows through 2021 are now read.
