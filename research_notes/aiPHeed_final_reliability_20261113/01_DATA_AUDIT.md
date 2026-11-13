# 01 — Ground-truth data audit (FNRI provincial HFIAS, 2013–2021)

Script: `scripts/gt_audit.py`. Evidence: `evidence/GT_rounds.csv`, `GT_evaluation_labels.csv`, `GT_excluded_areas.csv`.

## 1. What the label is
- **Measure:** FNRI HFIAS (9 items, 30-day recall, FNRI scoring after Coates et al. 2007). It is the same instrument in all five rounds.
- **Target:** share of households that are moderately or severely food insecure, by province.
- **HIGH:** that share is at least 50 %.
- **No quarterly label exists.** A row exists only where a survey measured the province. Nothing is interpolated or synthesised.

## 2. Rounds

| Round | Provinces with a mod+sev value | HIGH | Median % | Where the standard error comes from | Median SE (pp) | Labels within 1.96 SE of 50 % | Expected wrong-side labels | Role in FINAL |
|---|---|---|---|---|---|---|---|---|
| NNS 2013 | 78 | 54 | 58.7 | **Not printed.** Approximated as sqrt(deff 3.17 · p(1−p)/n) | 4.59 | 32 | 6.0 | Anchor history only |
| FNRI 2015 | 78 | 54 | 55.5 | Derived from the printed category SEs (design effect) | 3.89 | 39 | 10.0 | Training only |
| ENNS 2018 | 22 | 8 | 46.4 | Printed 90 % CIs; conservative sum | 2.11 | 4 | 1.2 | Test fold 1 (trained on 2015) |
| ENNS 2019 | 25 | 13 | 51.6 | Printed 90 % CIs; conservative sum | 2.82 | 8 | 1.2 | Test fold 2 (trained on 2015 only; 2018 was not yet released at the 2019 origin) |
| ENNS 2021 | 25 | 4 | 41.4 | **Not published.** 3.0 pp assumed for every province | 3.00 | 5 | 1.2 | Test fold 3 (trained on 2015 + 2018 + 2019) |

"Expected wrong-side labels" is the sum over provinces of P(the true value is on the other side of 50 % | the published value and its SE). Across the three test rounds, about **3.5 of the 72 evaluation labels** are expected to be on the wrong side of the HIGH line because of sampling error alone.

## 3. Excluded observations (every one is listed in `GT_excluded_areas.csv`)

| Round | Excluded | Reason |
|---|---|---|
| ENNS 2018 | 17 | City, HUC or NCR domain: there are no provincial predictors for it |
| ENNS 2018 | 1 | Davao Occidental: not in the FNRI 2015 appendix, so it has no region, anchor or inputs |
| ENNS 2019 | 8 | City, HUC or NCR domain |
| ENNS 2019 | 5 | Camarines Sur, Cebu, Davao Oriental, Pampanga, Zamboanga del Sur: the FNRI deck used for the panel prints only the any-level headline, with no moderate/severe split. The Heat Map split was never reconciled, so the row was left out |
| ENNS 2019 | 1 | Dinagat Islands: not in the FNRI 2015 appendix |
| ENNS 2021 | 11 | City, HUC or NCR domain |
| ENNS 2021 | 1 | Batanes: not in the FNRI 2015 appendix |

The five 2019 headline-only rows could be recovered from the FNRI Heat Map. That would add 5 evaluation rows, but adding them now would mean re-scoring the model after seeing results, so they were **not** added.

## 4. Requirements in brief §1

| Requirement | Status | Evidence |
|---|---|---|
| Retrieve and audit 2013, 2015, 2018, 2019 and 2021 provincial HFIAS | **Done** (published provincial estimates) | Table §2 |
| Use actual household responses and sampling weights | **NOT MET — unavailable.** No FNRI HFIAS public-use microdata could be obtained from this network: the FNRI PUF pages return "Web Page Blocked", and microdata need a data-sharing agreement. The published estimates are FNRI's own design-weighted estimates, but their weighting **cannot be re-verified** | memory `fi-labels-public`; completion audit `FINAL_SURVEY_DATA_AVAILABILITY_REPORT.md` |
| Verify harmonisation | **Partly.** The instrument, recall period and scoring are the same across rounds. The ENNS is a rolling survey with a different province subset each year. Round-level shifts are real (the 2019 subset is poorer than 2018) and are a known error source | `E137 OUTCOME_AUDIT` |
| Sampling design and coverage | **Partly.** 2015 and 2013 cover 78 provinces. The ENNS covers 22–25 provinces per round, chosen by FNRI's rolling design and not at random with respect to risk | Table §2 |
| Estimate uncertainty | **Partly.** 2013 is approximated and 2021 is assumed (3.0 pp). The label-noise consequence is quantified above | §2 |
| Never manufacture quarterly labels | **Met** | No such rows exist in `oof.csv` |
| Document every exclusion | **Met** | §3 |

**Remains unproven:** whether the FNRI-published provincial percentages reproduce from the household responses with the correct weights, and what the real 2021 provincial standard errors are.
