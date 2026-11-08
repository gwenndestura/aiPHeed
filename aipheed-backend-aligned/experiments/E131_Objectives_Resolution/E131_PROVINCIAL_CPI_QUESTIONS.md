# E131: answers to the owner's provincial CPI questions (2026-10-31)

**Owner's point, which E131 confirms.** Quarterly provincial food CPI solves the **predictor** frequency problem, not the **target** problem. E131 tested whether CPI, together with independent PSA and FNRI measurements, can support a valid provincial food-insecurity target or forecasting design.

**The key evidence** is a price-versus-income decomposition of the 2021→2023 change in provincial food deprivation (PFDR = PSA subsistence incidence among the population). It is built from the FIES 2023 public-use microdata and PSA's official food thresholds (`out/x3a_price_income_decomposition.csv`).
- The microdata reproduce PSA's official 2023 provincial values within 0.00–0.25 points, so the decomposition rests on PSA's own numbers.
- **Price effect** = how much the 2021→2023 rise in the official food threshold alone raised 2023 deprivation, at 2023 incomes.
- **Income effect** = the rest of the official change.

| Province | Official change 2021→2023 | Price effect | Income effect | Official threshold growth | Food-CPI growth |
|---|---|---|---|---|---|
| Batangas | +0.4 | +0.69 | −0.29 | +16.4 % | +15.3 % |
| Cavite | −1.6 | +0.12 | −1.72 | +17.3 % | +13.1 % |
| Laguna | −1.1 | +1.33 | −2.43 | +31.1 % | +9.8 % |
| Quezon | −5.7 | +0.31 | −6.01 | +6.9 % | +7.0 % |
| Rizal | +1.7 | +1.73 | −0.03 | +24.2 % | +16.3 % |

Changes and effects are in percentage points.

## 1. Why is provincial food CPI treated only as a predictor?

Because it measures **prices, not people's access to food**.
- CPI says how much the food basket costs relative to a base period. It says nothing about how many households cannot afford it.
- The table shows the gap directly. Food prices rose in **all five** provinces, yet food deprivation **fell** in three: Quezon, Laguna and Cavite. In those three, income gains outweighed prices.
- A target built on CPI would have said deprivation rose everywhere.

The owner's 2026-10-31 role assignment ("food CPI = predictor") is therefore supported by the data, not only by definition.

## 2. Can CPI help build a food-insecurity measurement without circularity?

**Only for the price half, only imperfectly, and not as a target.**
- **Price side.** Updating PSA's food threshold with food CPI reproduces the official 2023 threshold within 1 % for Batangas and Quezon. It misses Rizal by −6.4 % and **Laguna by −16.2 %**. PSA re-prices a provincial food menu; it does not index the threshold by CPI. In incidence terms, the CPI-updated threshold misstates Laguna's 2023 deprivation by −1.33 points and Rizal's by −0.63 points.
- **Income side.** This drove the changes in three of five provinces, by up to −6.0 points in Quezon. **No quarterly provincial income or expenditure measurement exists.** The FIES runs in survey years only, and the provincial LFS is annual and carries no income.
- **Circularity.** A quarterly "constructed food deprivation" would therefore be mostly CPI. Scoring a CPI-using model against it would be circular: the model would score well by reproducing its own input.

CPI belongs **inside the model** as the affordability (price) driver. The validation target must be measured independently.

## 3. Can independent PSA and FNRI measurements establish the target?

**At survey-year resolution, yes. Quarterly, no.**

| Measurement | Provincial? | Rounds 2021+ | What it can do |
|---|---|---|---|
| PSA subsistence incidence (PFDR) | Yes, 5 provinces with CVs | 2021, 2023. The 2025 release has no provincial subsistence table (owner-verified). | Survey-year reference: levels, changes, and the decomposition above |
| PSA poverty incidence | Yes | 2021, 2023, 2025 | A predictor (vulnerability), not food insecurity. Its provincial order is fairly stable: Quezon is highest in every round. |
| FNRI FIES | Batangas and Cavite (2021); regional (2023, 2025) | One provincial round | Construct cross-check only |
| CBMS 2024 FIES | All LGUs | One window | Strongest cross-sectional check; **not held** |

## 4. Can the available measurements support provincial numerical forecasting?

| Resolution | Verdict | Reason |
|---|---|---|
| Survey-year | Yes, but only one round ahead and descriptively | Five provinces per round. The E130 seal forecasts the next round. |
| Quarterly | **No validated forecast is possible** | There is nothing provincial and quarterly to score against |

Any quarterly provincial number has to be **model-based**: a regional measured-hunger forecast scaled by provincial relative deprivation (E131 X3c). Even then:
- **It depends heavily on the deprivation measure chosen.** The subsistence-based relative risk for Quezon is 0.76; the poverty-based one is 2.86. Scaling Balance Luzon's forecast by the poverty-based value gives an implausible 65 % hunger in Quezon.
- **Provincial order is unstable on the food-deprivation measure.** It reversed between 2021 and 2023 (Spearman −0.82; stability test p = 0.022).

## 5. What is the strongest legitimate approach that keeps the thesis objectives?

`E131_SELECTED_SOLUTION.md` sets out a two-layer design:

1. **Quarterly forecasting on measured food insecurity** (SWS hunger, 4 areas including Balance Luzon).
   - Numerical forecasts at the dashboard's leads, scored with the pre-registered measurement tolerance.
   - CPI and the other trigger groups as predictors.
   - Validated prospectively through the E131 seal.
2. **Provincial layer as measured food deprivation at survey years** (PFDR, with the price-versus-income decomposition).
   - It explains *why* provinces move: prices pushed deprivation up in Rizal; income pulled it down in Quezon.
   - Quarterly provincial values are shown only as labelled model-based estimates, never as validated forecasts.

**What would make quarterly provincial food-insecurity forecasting genuinely achievable** is a repeated provincial measurement of the **income side or of food insecurity itself**, for example:
- CBMS FIES rounds;
- a provincial FIES-8 module in an existing quarterly survey;
- provincial earnings from the LFS, if PSA releases them.

CPI is already sufficient on the price side.
