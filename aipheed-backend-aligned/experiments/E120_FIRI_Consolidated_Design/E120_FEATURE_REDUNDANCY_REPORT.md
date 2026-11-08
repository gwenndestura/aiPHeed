# E120 feature redundancy and double-counting report

**Sources:**
- raw-series correlations: E119-R2 `out/pairwise_correlations.csv`;
- E120 scored-feature correlations: `out/within_indicator_feature_correlation.csv`;
- indicator-score correlations: `out/indicator_score_correlation_*.csv`.

## 1. Removed before scoring (same phenomenon, counted once)

| Kept (scored) | Not scored (alternative) | Evidence |
|---|---|---|
| CPI food YoY | CPI bottom-30% food YoY | r 0.94 |
| Wholesale rice YoY (provincial) | Retail rice YoY; farmgate palay YoY | r 0.86; 0.79 (same quarter) |
| Farmgate palay YoY (regional rice series) | — | The only rice series with a Region IV-A row |
| Fisheries total YoY | Aquaculture YoY | Aquaculture is a part of the total (30–65%) |
| Cyclones within 100 km | Cyclones within 300 km (C2) | Equal across the five provinces in 64% of quarters; r 0.68 with rainfall total |
| Absolute rainfall departure | Rainfall total | The departure is derived from the total |
| GDELT shortage share | GDELT agri-supply share | r 0.93 |
| National unemployment change | Unemployment level | The change is the FIRI concept (E1) |
| Poverty (SAE 2021) | V1 composite | V1 = 0.6 poverty + 0.4 density, with fixed weights |

## 2. Kept together in one component (complementary, averaged inside the component)

| Component | Features | Correlation among scored features | Why averaged, not added |
|---|---|---|---|
| Protein prices (FMA) | Chicken, pork, tilapia | Chicken–tilapia 0.41; others below 0.4 | Different commodities, one concept: one component vote |
| Cereals (AFP) | Palay, corn | Raw YoY r 0.40 | One crop group |
| Poultry and livestock (AFP) | Chicken, livestock | Raw YoY r −0.08 | One group; both from 2024 only |
| Employment (EHS, provincial) | Unemployment, underemployment (annual ranks) | 0.47 | Two aspects of the labour market |

## 3. Kept as separate components (different concepts)

| Pair | Correlation | Reading |
|---|---|---|
| CPI food vs headline | 0.74 (scores) | Related; headline adds non-food cost pressure. **Disclosed overlap:** about half of FMA's components are CPI-based. Merging them into one component is a reasonable sensitivity, recommended for E121. |
| CPI food vs wholesale rice | 0.20 (raw) | Complementary |
| Wholesale rice vs tilapia | −0.41 (scores) | Shared timing (rice rise, fish fall), not one phenomenon |
| Vegetables vs root crops production | −0.04 (raw) | Independent |
| Regional production groups | 0.43–0.91 (scores, **n = 9**) | Too few regional quarters to judge. Kept separate, as at provincial level, where they are independent. |

## 4. Between indicators

| Scope | Spearman between indicator scores |
|---|---|
| Provincial (pairs with ≥ 25 rows) | −0.11 to 0.29 |
| Provincial pairs with PSV or FIS (8–15 rows) | −0.54 to 0.26 (not interpretable) |
| Regional (10 quarters) | −0.26 to 0.53 (FMA–AFP 0.53) |

**Reading.** No two indicators measure the same thing, so **no indicator double-counts another**.
- The first principal component explains 32% of provincial indicator variance.
- Redundancy-adjusted weights differ from equal weights by 0.012 on average.

## 5. Double counting across indicators by construction

**Avoided** by assigning each dataset to exactly one indicator:
- structural affordability (subsistence, FIES food share) to PSV, not FMA;
- remittances to EHS, not FIS;
- realized production losses to AFP and hazards to CEC.

**Hunger is counted nowhere.** SWS is outside the FIRI.
