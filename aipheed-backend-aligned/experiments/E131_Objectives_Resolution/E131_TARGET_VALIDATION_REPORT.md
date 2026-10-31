# E131 target validation: does the model learn food insecurity?

## The targets are measured food insecurity or food deprivation, never their drivers

| Target | What it measures | Independent of the predictors? | Coverage | Numerical? |
|---|---|---|---|---|
| **SWS involuntary hunger** (quarterly layer) | Families who experienced involuntary hunger in the past 3 months: an experience-based food-insecurity indicator | **Yes.** A household survey answer, not built from prices, jobs or news. | 4 areas × 20 quarters, 2021–2026 | Yes, %, with per-round sampling error |
| **PFDR, PSA subsistence incidence** (provincial layer) | Share of the population whose income is below the provincial food threshold: food deprivation | **Partly.** The threshold is priced at provincial food prices; income is measured. Overlap quantified in X3a. | 5 provinces × 2 survey rounds | Yes, %, with CVs |

**Rejected as targets:** CPI, poverty, FIRI v2 and FIRI3 are drivers or indices built from drivers. So is any quarterly measure built from CPI (`E131_PROVINCIAL_CPI_QUESTIONS.md`).

## Evidence that the target is not just food prices

1. **In the provinces, food deprivation fell where prices rose.** Food prices rose 7–16 % from 2021 to 2023 in all five provinces, yet PFDR fell in Quezon, Laguna and Cavite. Income effects (−6.0, −2.4, −1.7 points) outweighed the price effects (X3a).
2. **On the hunger series, price features do not help.**
   - In ridge, removing the market group *lowered* Lead-2 MAE by 2.25 points.
   - In LightGBM it changed MAE by +0.17 points.
   - Earlier work found the same: regional hunger and food inflation correlate at r = −0.61 (E83), and untouched 2013–2020 data showed no market skill (E114).
3. **The 2024 hunger surge** (Balance Luzon 11 → 25) came *after* food inflation peaked in 2023. A price-trained model would not anticipate it, and none did (0 of 7 sharp increases within tolerance).

## What the models actually learn

| Model | What it learns | Evidence |
|---|---|---|
| **LLM (selected)** | The **level of hunger itself**, separating real movement from survey noise using each round's published sampling error | Its forecast is a filtered hunger level, not a function of prices |
| Learned models (LightGBM, ridge) | Hunger history mainly, plus noise from the trigger features | Training MAE 2.1 against out-of-sample 6.1; ablation effects unstable in sign |

## Measurement limitations carried into every result

- SWS is regional (4 areas), not provincial.
- The respondent base changed in 2025 (household heads → adults).
- Area values are means of 1–2 rounds.
- PFDR is biennial and noisy: CVs of 17–62 %, and the 2023 provinces cannot be distinguished statistically (Cochran's Q p = 0.17).
