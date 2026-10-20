# E68 target-validity report

**Sources:**
- `runner/r2_diagnostics.py` produces `tables/r2_target_by_year.csv`, `r2_target_by_province.csv`, `r2_target_by_quarter.csv`, `r2_labels_all.csv`, `r2_face_validity_subsistence.csv` and `out/r2_diagnostics.json`.
- The label code is in E55 `e55_lib.t43_labels`, using the E40 `label_spec.json` thresholds and E41 `quarter_F`.

## 1. How the approved target T43 is generated

| Step | Exact rule | Source data | Resolution | Released |
|---|---|---|---|---|
| Hunger | quarter mean of every SWS round in the quarter (`sws_rounds.csv`, all rounds) | SWS Balance Luzon hunger | **region** (one value for all 5 provinces) | rounds posted 3–8 weeks after fieldwork |
| Food price | quarter-mean PSA food CPI YoY | PSA OpenSTAT 0012M4ACP22/23 | province | about 5 days after each month |
| Gap | food YoY − headline (all-items) YoY | same | province | same |
| PS | food YoY > province P60 **or** gap > province P60 | thresholds frozen in E40 over 2021-Q1..2022-Q4 | province | — |
| T43 | hunger > 11.3% **and** PS = 1 | H = 11.3 is the E40 P60 of the 6 window quarters with an approved round | province-quarter | — |
| Missing SWS | no label; never zero-filled | — | — | — |

**Threshold rationale (E40 `label_spec.json`).** The thresholds are P60 of the 2021–22 window. P60 was chosen by the researcher on 2026-10-15 from a P60–P85 grid, with gates on label prevalence: 5–30% HIGH share and a 40% per-year cap.
- They were set **from label prevalence, not from model predictions**.
- They have never been recomputed.
- E68 reproduces the food P60 exactly with `numpy.percentile` (asserted in `r1_arms.py` and in a test).

## 2. What the label actually varies with (measured)

| Fact | Value |
|---|---|
| Province-quarters with a label (2021-Q1..2026-Q3) | 105 (21 quarters) |
| Lead-2 evaluation rows / independent quarters | 50 / **10** |
| Evaluation rows where T43 = PS | **50 / 50** |
| Quarters with hunger above 11.3% | 14 of 21 (all of 2024, 2025, 2026) |
| Rows with hunger above the line but T43 LOW | 47 |
| Quarters where all five provinces share one T43 label | 12 of 21 |

**HIGH rate by year** (`r2_target_by_year.csv`):

| Year | T43 | PS | T-AFF | Hunger above line |
|---|---|---|---|---|
| 2021 | 0.13 | 0.40 | 0.20 | 0.33 |
| 2022 | 0.00 | 0.40 | 0.13 | 0.33 |
| 2023 | 0.15 | **0.85** | 0.00 | 0.25 |
| 2024 | 0.40 | 0.40 | 0.15 | 1.00 |
| 2025 | 0.45 | 0.45 | 0.05 | 1.00 |
| 2026 (Q1–Q3) | 0.07 | 0.07 | **0.53** | 1.00 |

**HIGH rate by province** (T43): Quezon 0.38, Laguna 0.29, Batangas 0.24, Cavite 0.19, **Rizal 0.00** (never HIGH).

**Reading.**
- **2021–2023:** hunger decides. In 2023 price pressure was HIGH in 85% of rows, but hunger was below the line in 3 of 4 quarters.
- **2024–2026:** hunger is always above the line, so T43 is the price condition.
- **Consequence:** on everything evaluated at Lead-2, T43 is provincial food-price pressure.

## 3. Can T43 represent what the thesis intends?

| Intended dimension | Represented? | Evidence |
|---|---|---|
| Elevated hunger | Only regionally and as an on/off gate | one Balance Luzon series; above the line in every evaluated quarter |
| Food-price pressure | Yes | PS by province |
| Household affordability | **Partly, and inverted for non-food inflation** | the gap clause counts faster non-food inflation as relief. 2026-Q3: hunger 23.6%, headline 4.8–7.3%, T43 LOW everywhere |
| Climate-related production stress | Only once it shows in food CPI | no production, rainfall or drought term in the label |
| Household vulnerability | No | poverty enters only the LGU ranking (Objective 3) |
| Household food insecurity | **No** | no provincial food-insecurity outcome exists in the data |

## 4. Candidate revised target T-AFF (exploratory, pre-registered in PROTOCOL §3)

**Definition:** T-AFF = hunger > 11.3% AND (food YoY > food P60 OR **headline** YoY > headline P60). The headline P60 values come from the same frozen 2021–22 window and method:

| Province | Headline P60 |
|---|---|
| Cavite | 5.01 |
| Laguna | 4.65 |
| Quezon | 5.06 |
| Rizal | 6.07 |
| Batangas | 5.55 |

**Disclosure:** it is hindsight-informed, motivated in part by the observed 2026-Q3 case.

**What it changes** (`r2_*`, `out/r2_diagnostics.json`):
- On the 50 evaluation rows T-AFF disagrees with T43 on **20** rows: 13 T43-HIGH become LOW, and 7 T43-LOW become HIGH. It has 12 HIGH, against 18 for T43.
- It moves HIGH toward 2026 (0.53), when headline inflation outran food.
- It labels 2024–25 mostly LOW (0.15 / 0.05), because food inflation then exceeded headline.

**Forecastability** (`tables/r3_taff_arms.csv`, same 50 rows):

| Reading | Accuracy | Balanced accuracy | HIGH recall | What it amounts to |
|---|---|---|---|---|
| TAFF-LGBM (E56-TUNED on T-AFF) | 0.76 | 0.50 | **0** | identical to always-LOW |
| TAFF-RULE | 0.74 | 0.57 | 0.25 | worse than always-LOW on accuracy (0.76) |

The 2026-Q2/Q3 headline-driven HIGHs were missed: 1–2 of 5 correct in each quarter.

**Verdict.** T-AFF is a more faithful affordability description of 2026, but it is **not forecastable two quarters ahead** with the available inputs. It is not adopted; adoption needs adviser approval in any case. Its forward forecasts are sealed in `sealed/prospective.csv`. TAFF-RULE gives 0.49–0.87 for 2027-Q1, so 2026-Q4 and 2027-Q1 will be informative.

**What the dashboard does instead (e68).** It shows the observed affordability fact as an observation, not a forecast: for example, "headline inflation in Laguna (6.9%) is above its usual 2021–2022 level (4.7%) … a peso buys less".

## 5. Independent provincial outcomes

| Source | In the system? | Usable as an outcome? |
|---|---|---|
| PSA subsistence (food-poverty) incidence 2021, 2023, by province | yes (E27 `acquisition/validated/`) | **Face validity only.** Two years × 5 provinces; CVs 17–62% (PSA: CV > 30% is unfit for ranking); income-based food poverty, not FIES |
| DOST-FNRI NNS FIES 2023 | regional figure only (CALABARZON 19.1%) | No (region, survey years) |
| CBMS food-security items | not in the system | Would be the key outcome (city/municipal), if released for 2021–2026 |
| Provincial FIES (PSA) | not published by province in the files available | — |
| DSWD/LGU feeding or assistance caseloads | not in the system | possible proxy; needs a data request |

**Face-validity result** (`r2_face_validity_subsistence.csv`): Spearman correlations between province annual HIGH rates and subsistence incidence, n = 5 per year.

| Year | T43 | PS | T-AFF |
|---|---|---|---|
| 2021 | 0.30 | 0.14 | 0.89 |
| 2023 | 0.00 | 0.29 | undefined (no variation) |

With five points and CVs up to 62%, these correlations neither confirm nor reject the label; 0.89 on five points is not evidence.

## 6. Conclusion and required future data

- **Supported claim:** "an exploratory provincial food-stress score: provincial food-price pressure under elevated regional hunger". On all evaluated quarters it reduced to provincial food-price pressure.
- **Not supported:** "validated provincial food-insecurity forecast".
- **E68 wording:** in e68 mode the dashboard event text is "the exploratory food-stress score (… not a measure of household food insecurity)".
- **Required to resolve:**
  1. A provincial or municipal food-insecurity outcome for 2021–2026: CBMS, provincial FIES, or DSWD/LGU caseloads, at least annual.
  2. Provincial hunger (SWS publishes only regional series).
  3. An adviser decision on the price clause (gap vs headline vs both), taken before seeing 2026-Q4 outcomes.
