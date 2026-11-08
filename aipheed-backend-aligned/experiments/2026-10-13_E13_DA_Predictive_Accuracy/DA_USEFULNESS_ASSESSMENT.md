# DA Usefulness Assessment (E13; updated with Amendment 1)

**Status of the evidence:**

- All results are retrospective, on quarters examined before.
- Provincial price results are also **exploratory (timing)**.
- The v1 version of this file is in commit `5f7765f`.

**Detailed reports:**

- `REGIONAL_HUNGER_FORECAST_REPORT.md`
- `PROVINCIAL_PRICE_FORECAST_REPORT.md`
- `OFFICIAL_OUTCOME_COMPARISON.md`

## 1. Answers to the DA questions

| Question | Answer | Evidence |
|---|---|---|
| **Can the model identify changes in regional hunger earlier than a simple baseline?** | **No.** No method beat the latest published value (MAE 4.8 points). Hunger rose against that value in 8 of 9 test quarters. No method's rise calls are informative with one negative case. | Task A |
| **Can it identify provinces with increasing food-price pressure?** | **Partly, and mostly by regression to the mean.** "D will move back toward 0" gets rising and falling pressure right with balanced accuracy of about 0.69, against 0.50 for carry-forward. Absolute food inflation rising (14 of 55 cases) is not predicted better than baselines. | Task B |
| **Can it separate price-pressure changes from the common regional hunger signal?** | **Yes, by construction.** D sums to 0 in every quarter (max \|ΣD\| = 6e-15), so it carries no regional level. Regional food inflation is **negatively** correlated with hunger in 2021–2025 (r ≈ −0.48), so price pressure and hunger are distinct signals here. | §9 of Amendment 1 |
| **Are rankings and warnings stable across periods?** | **Moderately.** Realized D rankings agree with the previous quarter at Kendall τ 0.54. The best arm differs between the two halves of the test period for F. For D, the shrinkage arms beat carry-forward in both halves, but not the "no difference" baseline from 2023-Q4 onward. The 2024-Q2 ranking reversal (Quezon from lowest to highest) was not anticipated by any method. | Stability tables |
| **Does it add information beyond official indicators?** | **Little beyond the latest official values.** The best forecasts are the latest value, or that value shrunk toward the average. The real gain is **timeliness**: a forecast at the start of a quarter, about 3.5 months before that quarter's provincial CPI and 1–6 months before the SWS release. | Task A and B |
| **What would DA need before treating any output as an absolute food-insecurity classification?** | (1) An independent, repeated provincial food-insecurity outcome (FIES or HFIAS type, or a CBMS food-shortage item); (2) thresholds chosen on training data only; (3) validation on new quarters; (4) verified release dates. **None exists yet.** | `OUTCOME_DATA_AUDIT.md`, E15 `DATA_GAP_INVENTORY.md` |

## 2. How each result should be described

| Result | Allowed description | Not allowed |
|---|---|---|
| D shrinkage beat carry-forward | "Better relative food-price-pressure forecasting than carry-forward, on 2023–2025 data (exploratory)" | "Improved food-insecurity prediction" |
| No gain for F | "Provincial food inflation is best forecast by its latest value" | — |
| No gain for H | "Regional hunger forecasts did not improve on the latest published value" | Any provincial difference in hunger |
| Subsistence comparison | "Limited, mixed descriptive consistency" | "Validated against PSA data" |

## 3. Research-only dashboard recommendation (no production change)

| Layer | What it shows | Label | Condition |
|---|---|---|---|
| **Regional hunger context** | SWS Balance-Luzon level, change, publication date, data age. Shown once. | "Regional hunger (Balance Luzon)" | Always, with its scope |
| **Provincial relative food-price pressure** | F, D (with its size), and the rank when all five provinces are present | "Relative food-price pressure", **not risk** | No D or rank when any province is missing |
| **Household vulnerability indicators** | Subsistence and poverty incidence with CIs and survey year | "Vulnerability context (survey year, CV)" | Values with CV ≥ 30% flagged as unreliable |
| **Actual food-insecurity level** | **Nothing.** The panel reads "insufficient evidence". | — | Only once an independent outcome, training-only thresholds and validation on new quarters exist |
| **Insufficient evidence** | An explicit state | "Insufficient evidence" | Wherever data are missing or unvalidated |

**Rules for the display:**

- **A rank is not a food-insecurity level.** A top-ranked province exists even when the differences are small, so the D values must be shown.
- **No LOW labels are generated to avoid an all-HIGH display.**
- **Implementation:** E15's development prototype (`TWO_LAYER_SCHEMA.json`) implements this layout. It is not connected to the dashboard.
