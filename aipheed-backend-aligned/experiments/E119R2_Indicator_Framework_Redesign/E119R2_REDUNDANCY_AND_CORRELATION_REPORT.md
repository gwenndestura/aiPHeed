# E119-R2 redundancy and correlation report

**Source.** `runner/analyze.py`. Full tables:
- `out/pairwise_correlations.csv`: every pair, with n, Pearson and Spearman;
- `out/effective_components.csv`;
- `out/annual_rank_correlation.csv`.

**Data.** 2021+ observations only, built with the E119 rules: quarters need all 3 published months, and year-on-year changes need a 2021+ base, so they start in 2022.

**No target correlations.** Correlations with SWS hunger were deliberately **not** computed. Choosing datasets by how well they track the target would be selection on the evaluation data. Redundancy is judged only among the predictors.

## 1. How redundancy was judged

| Question | Method |
|---|---|
| Do two series measure the same thing? | Pearson and Spearman on comparable observations: the same unit and the same observation quarter, pooled over the 5 provinces. |
| How many genuinely different signals sit in an indicator? | **Effective number of independent components** = (Σλ)² / Σλ², from the eigenvalues λ of the Spearman correlation matrix (complete rows only). It equals the number of series when they are unrelated, and 1 when they are copies of each other. |
| Conceptual overlap | Does one series contain the other (aquaculture is part of fisheries; headline CPI contains food)? Is one derived from the other (anomaly from total)? |
| Coverage and timing | Missing share, first and last quarter, release-date status (`E119R2_GEOGRAPHIC_AND_TEMPORAL_COVERAGE.csv`) |

**Threshold.** |r| ≥ 0.8 with a shared concept means "one signal, keep one as primary". 0.5–0.8 means "related; keep both only if the concepts differ". Below 0.5 means "complementary".

## 2. Effective independent components per indicator

| Indicator | Series used | Effective components | Complete rows | Reading |
|---|---|---|---|---|
| FP Food Prices and Affordability | 14 | **4.58** | 59 | 14 price series carry about 4–5 distinct signals. Averaging them would hide that; treating them as 14 votes would count the same evidence several times. |
| PS Local Food Production and Supply | 6 | **5.03** | 90 | Commodity groups are nearly independent. Keep them as separate components. |
| CH Climate and Weather Hazards | 5 | **3.20** | 80 | Rainfall total, anomaly and the 300 km cyclone count overlap. Temperature and local cyclones add separate information. |
| NS national news (GDELT) | 4 | **2.54** | 23 | Two of the four categories are one signal. |

## 3. Pairs that are redundant (same phenomenon)

| Pair | n | Pearson | Spearman | Decision |
|---|---|---|---|---|
| CPI bottom-30% food vs CPI food | 115 | 0.937 | 0.939 | **Redundant.** Keep CPI food as primary; bottom-30% only as a poor-household sensitivity. |
| Retail rice vs wholesale rice | 89 | 0.857 | 0.812 | **One rice-price component.** Wholesale is primary (the served A3 source); retail is the alternative. |
| Farmgate palay vs wholesale rice | 88 | 0.793 | 0.771 | Same rice component, at the producer side. Farmgate is the regional predictor because only it has a Region IV-A row. |
| Farmgate palay vs retail rice | 94 | 0.704 | 0.677 | As above |
| GDELT agri-supply share vs shortage share | 23 | 0.928 | 0.896 | **Redundant.** Keep one, or their sum, as "supply-shortage news". |
| Rainfall total vs 300 km cyclone count (C2) | 100 | 0.680 | 0.616 | Cyclones bring the rain. C2 is also identical across the five provinces in 64% of quarters, so the **100 km count** is kept as the province-specific cyclone measure and C2 becomes supporting. |
| Rainfall anomaly vs rainfall total | 80 | 0.592 | 0.645 | The anomaly is derived from the total. Use one per model (the total plus season terms, or the anomaly). |

**Correction to E119.** E119 reported r = 0.70 (retail vs wholesale rice) and 0.43 (farmgate vs wholesale) from the *as-of* provincial dataset. There each value can come from a different observation quarter. Aligned on the same quarter, the series are more alike (0.86 and 0.79). The same-quarter figures are the right test of redundancy.

## 4. Pairs that are complementary (keep separately)

| Pair | n | Pearson | Why both stay |
|---|---|---|---|
| CPI food vs headline CPI | 115 | 0.720 | Headline contains food, but non-food costs (fuel, transport, rent) squeeze food budgets separately. Headline stays in the provincial profile. |
| CPI food vs retail chicken / tilapia / tomato / carrot / cassava / cabbage | 79–95 | 0.42 / 0.46 / 0.30 / 0.26 / 0.22 / 0.21 | Single commodities add information that the food CPI averages away |
| CPI food vs retail pork / farmgate hog | 95 / 84 | −0.10 / −0.03 | The pork cycle (African swine fever) is independent of general food inflation |
| Farmgate palay vs retail pork | 94 | −0.733 | Strong but **not conceptual**: the rice price rise (2023–24) and the pork price fall happened at the same time. It is a shared timing, not one phenomenon, so both are kept. |
| Palay vs corn production | 95 | 0.396 | Different crops and seasons; C3 already combines them as the worse of the two |
| Vegetables vs root crops production | 90 | −0.043 | Unrelated; splitting E119's combined series is justified |
| Palay vs fisheries production | 90 | 0.000 | Unrelated; production cannot be one averaged number |
| Aquaculture vs fisheries total | 90 | 0.214 (Spearman 0.562) | Aquaculture is a **part** of the total (30–65%), so it is not independent evidence. It stays a supporting sub-component. |
| 100 km vs 300 km cyclones | 110 | 0.383 | Different exposure radius |
| Retail cassava vs retail carrot | 87 | 0.004 | Root-crop prices do not form one series. A basket would need explicit weights (see §6). |

## 5. National and regional quarterly series (one value per quarter; n 13–23)

| Pair | n | Pearson | Reading |
|---|---|---|---|
| Region IV-A CPI food vs headline | 19 | 0.780 | As at province level |
| Unemployment change vs GDELT jobs-income share | 19 | −0.882 | Both follow the 2022 post-COVID recovery. With n = 19, a shared trend is more likely than duplicate measurement, so both are kept and the overlap is disclosed. |
| Unemployment change vs remittance decline | 18 | 0.341 | Different income channels |
| ONI vs CALABARZON rainfall anomaly | 16 | −0.546 | El Niño means drier conditions, as expected. ONI stays the ENSO predictor and the PAGASA advisory (C1) is its thresholded form. |
| ONI vs Region IV-A CPI food | 19 | −0.079 | No direct link in 2021–26 (consistent with E65) |

These national correlations rest on 13–23 quarters dominated by one recovery cycle. They are reported, not used to drop data.

## 6. Annual provincial profile (5 provinces: rank agreement only)

| | Poverty (SAE 2021) | Subsistence 2021 | Subsistence 2023 | FIES food share (all) | FIES food share (bottom 30%) | Density |
|---|---|---|---|---|---|---|
| Batangas | 8.55 | 1.0 | 1.4 | 35.5 | 44.9 | 961 |
| Cavite | 11.13 | 2.4 | 0.8 | 38.0 | 47.1 | 2,997 |
| Laguna | 7.89 | 2.4 | 1.3 | 39.7 | 50.3 | 1,912 |
| Quezon | 20.30 | 6.6 | 0.9 | 47.3 | 62.0 | 256 |
| Rizal | 6.89 | 0.9 | 2.6 | 38.7 | 50.5 | 2,889 |

**Rank correlations (n = 5).**
- Poverty vs subsistence 2021: 0.82.
- Subsistence 2021 vs 2023: **−0.82**.
- FIES all vs bottom 30%: 0.90.
- Food share vs density: −0.40.

**Reading.**
- **Poverty and 2021 subsistence agree.** Quezon is the most deprived.
- **Subsistence 2023 reverses the 2021 order.** Rizal is highest at 2.6 and Quezon falls to 0.9. With coefficients of variation of 14–88%, the provincial subsistence estimates are too imprecise to rank provinces from one round. Report both rounds with their CVs; never use one round alone.
- **FIES food share** places Quezon clearly highest in both the overall and bottom-30% measures. It is the most stable deprivation signal available.
- **Density** runs opposite to deprivation. It measures urban market dependence, not hunger. In V1 it carries 40% of the weight, which this analysis does not support.

**Composite rule.** No composite is proposed: with five provinces, any weighting is arbitrary. The profile shows each component side by side, with its year and precision.

## 7. Consequences for the framework

1. **Keep the components, do not average them.** Each indicator is a named group of components. A component with several near-duplicate series (rice prices; the GDELT supply and shortage shares) uses **one primary series**, and the others are alternatives.
2. **Evidence counting.** In any score or explanation, an indicator counts once, and inside it each component counts once. Bottom-30% CPI, retail rice, aquaculture, rainfall anomaly and the 300 km cyclone count never add evidence on top of their primary series.
3. **No new weights.** No weighting or composite score is introduced. Any combination needed later should come from a pre-registered, in-sample-only method (for example, the first principal component within the training window). It must not come from judgment.
