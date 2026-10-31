# E130 final recommendation

**Outcome: BLOCKED.**

A quarterly provincial food-insecurity risk-score model cannot be trained or validated on the data that exist. The minimum operational objective (Lead 2, at least one completed quarter beyond the dashboard quarter) is **not achieved**. This is not a modelling failure: there is no provincial quarterly measurement to learn from or score against.

E130 delivers four things:
- a frozen, execution-ready provincial protocol;
- the first sealed provincial numerical forecast;
- the resolved lead definition;
- data requirements in numbers.

## 1. Answers to the brief's 26 questions

| # | Question | Answer |
|---|---|---|
| 1 | Which provincial score is the model learning? | None: no model was trained. The defined reference is **PFDR v1**, PSA provincial subsistence incidence among the population (% below the provincial food threshold), per FIES survey year. |
| 2 | Which official measurements support it? | PSA FIES-based poverty statistics: 2021 and 2023 held (vintage 2024-08-15); 2025 published 2026-08-21, not held. FNRI ENNS 2021 FIES (Batangas, Cavite) as a cross-check. |
| 3 | Food insecurity or a proxy? | **Measured food deprivation** (income below a food threshold), an official measurement. Not experienced food insecurity (FIES) and not a constructed index. |
| 4 | Independent provincial target observations? | **10** values (5 provinces × 2 rounds); **5** changes; **0** quarterly |
| 5 | Meaningful variation across provinces and quarters? | Across rounds, yes: the order reversed (Spearman −0.82; stability p = 0.022), with real changes in Quezon (−5.7) and Rizal (+1.7). Across provinces: significant in 2021 (Q p < 0.0001), not in 2023 (p = 0.17). Across quarters: not observed. |
| 6 | Which trigger groups carry useful information? | Not testable on a provincial target. Descriptively, provincial **food prices** ranked the 2021→2023 changes (Spearman 0.90, N = 5, partly mechanical); **employment** did not (0.00). Climate, news and poverty cannot be assessed on 5 changes. On the regional target, E128 found no stable group contribution. |
| 7 | Is the model learning food insecurity rather than food prices? | No model exists. For PFDR, food prices are part of the construct (affordability). A model would also need income-side data to learn more than prices. |
| 8 | Numerical errors of LightGBM? | None: not trained |
| 9 | Share within the approved tolerance? | Not evaluable. Tolerance fixed at 1.645 × reference SE (0.50–1.89 pp). |
| 10 | ≥ 75 % numerical agreement? | **No** (not evaluable) |
| 11 | ≥ 75 % classification accuracy? | **Not valid:** no approved PFDR thresholds |
| 12–15 | Does LightGBM beat persistence, PSA-only, NLP-only, logistic regression? | **Not established** for any baseline |
| 16 | Generalizes across the five provinces? | Not assessable. One change per province; Quezon carries 83 % of the squared change. |
| 17 | Overfitting? | No model. Any model would have 7.8 predictors per independent change. |
| 18 | Geographic or risk-level bias? | Not measurable. Inherited risks: news covers Cavite 4× more than Rizal; 1 high-deprivation value in 10; typhoon counts identical across provinces in 82 % of quarters. |
| 19 | Calibrated? | Not evaluable. The sealed intervals are honest but wide (± 4.4–4.5 pp). |
| 20 | Maximum reliable lead? | **None**, for every model |
| 21 | Does Lead 2 meet the minimum operational requirement? | **No.** Lead 2 status: **failed** (not evaluable). |
| 22 | Does Lead 2 forecast one completed quarter beyond the dashboard quarter? | By definition yes. Lead 2 is the dashboard's forecast target (`backend/app/quarterly/target.py`). No model reaches it reliably. |
| 23 | First unreliable lead? | **Lead 1** (fails N1) |
| 24 | Why does performance fall at longer horizons? | A growing information horizon (SWS: 3 quarters at Lead 2 at the quarter-start issue); predictor publication lags (CPI 2 quarters, production 3, LFS 4–7); provincial price deviations losing memory by 3–4 quarters (autocorrelation 0.29, −0.05); regime shifts (regional hunger 11.2 → 19.6 from 2023 to 2024) |
| 25 | What changes are genuinely necessary? | See §2 |
| 26 | Suitable for production? | **No.** Nothing was trained, and nothing should be integrated. The served system, FIRI v2 and FIRI3 are unchanged. |

## 2. What is genuinely necessary

1. **A repeated provincial food-insecurity measurement.** Nothing else can unblock a provincial *forecast*:
   - **Best:** a quarterly FIES-8 measurement in each province. For example, ≈ 300 households per province per quarter gives SE ≈ 2.6 pp at 30 % prevalence, about the size of real quarter-to-quarter variation.
   - **Duration:** 20–40 quarters before Lead 2 can be confirmed. The planning simulation shows that 10 quarters (the N1 minimum) passes at most 78 % of the time even with excellent predictors.
2. **Predictors that explain ≥ 50 % of the true two-quarter change.** None has shown this. E79's best regional trigger variant explained 6 %, so stronger *provincial* drivers are needed:
   - verified provincial CPI release dates (148 are still rule-based);
   - sub-annual provincial labour data;
   - province-tagged news with enough volume.
3. **The data that exist but are not held:**
   - **PSA 2025 provincial subsistence table.** The owner should download it manually, because the PSA site's bot check blocks automated access. It scores the E130 seal and raises PFDR to 15 values.
   - **CBMS 2024 LGU FIES** (142 LGUs; requests A–C from E87 are unsent).
   - **FNRI 2022 ENNS provincial FIES.**
4. **No pre-2021 data, no SWS copies, no CPI or FIRI target.** None of these would make the provincial objective valid.

## 3. Alternatives for owner approval

None of these claims a validated quarterly provincial forecast.

| Option | What it delivers | What it validates | Effort and timing |
|---|---|---|---|
| **A. Regional forecast plus provincial priorities (recommended for the thesis)** | Keep quarterly forecasting at the regional level (SWS Balance Luzon; label its leads by information horizon). Present provinces as *priorities* (FIRI3, declared as an index) checked against PFDR rounds. | Regional forecasting (E128 rules); provincial ranking against measured deprivation (V-S1/V-S2) | Now; no new data |
| **B. Survey-year provincial forecasting** | One-round-ahead PFDR forecasts, sealed before each PSA release (E130 pattern) | Provincial numerical forecasts, round by round (5 rows per round) | Next score: 2025 round, as soon as the owner supplies the table. Then 2027. |
| **C. LGU cross-section with CBMS 2024** | A numerical model of LGU FIES prevalence (142 LGUs), province-held-out | Whether the system's LGU risk matches measured food insecurity (cross-sectional, not temporal) | Needs the CBMS request |
| **D. Prospective quarterly provincial monitoring** | DA IV-A or LGU FIES-8 rounds each quarter | Quarterly provincial forecasting, Lead 2 | 5–10 years. A recommendation, not a thesis deliverable. |

## 4. Immediate next steps

1. **Owner:** download the PSA "Regional and Provincial Press Release – 2025 Full Year Poverty Statistics" (or the 2025 statistical tables) and place it in `data/owner_supplied/`. E130 then extracts the five provincial values and CVs and runs `runner/score_e130.py`. No new 2025 forecast is allowed (exposures X1 and X2).
2. **Owner decision:** choose among options A–D, and decide whether to approve PFDR category thresholds (needed for any classification claim).
3. **Thesis wording:** state the minimum operational objective (Lead 2) as **not met at provincial level, because no provincial quarterly measurement exists**. Describe the operational lead and the information horizon separately.
