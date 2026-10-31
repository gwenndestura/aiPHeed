# E120 consolidated FIRI framework (proposal for review)

**Scope.** Design and offline analysis only. `firi.py`, the served FIRI v2, the API, the dashboard and the model are unchanged. No model was trained. Nothing was pushed.

**Rerun:**

```
cd runner
python e120.py
python reports.py
python validate.py
```

## 1. Is the six-indicator structure defensible?

**Yes, with two changes to the proposed sixth indicator.**

1. **SWS hunger is not a FIRI input.** It is the regional forecasting target. A FIRI that contains it would partly *be* the outcome it is later checked against, and would carry target information into any model that uses the FIRI. SWS is shown beside the FIRI as "observed regional hunger".
2. **OFW remittances move to Indicator 4.** A fall in remittances is a household income shock, the same concept as job loss.

What remains in Indicator 6 is the news-based early-warning evidence. It is named **Food Insecurity Early-Warning Signals**.

**This is the E119-R2 seven-indicator structure, minus the outcome indicator.** The outcome stays outside the index, so the FIRI measures risk evidence and SWS measures realized hunger.

**Statistical check.** The six indicator scores are nearly independent:
- provincial Spearman |ρ| ≤ 0.29 for every pair with at least 25 rows (pairs involving PSV or FIS have only 8–15 rows: ρ −0.31 to −0.54, too few to judge);
- the first principal component explains only 32% of the variation.

So the six are distinct dimensions, not one signal counted six times.

## 2. Three levels

| Level | What it is | Where defined |
|---|---|---|
| 1. Features | Measured variables, as of the issue date, from 2021+ observations | `E120_FEATURE_DICTIONARY.csv` (34 scored, 19 profile/context/alternative) |
| 2. Indicator scores | Mean of component scores. A component is a group of features about one thing (e.g. protein prices); each component counts once. | `E120_INDICATOR_SCORE_METHODOLOGY.md` |
| 3. FIRI | Equal-weighted mean of the available indicator scores, 0–1, with 0.5 = the 2021+ usual level, banded by chance variation | `E120_FIRI_AGGREGATION_METHODOLOGY.md` |

## 3. The six indicators

| # | Indicator | Operational definition | FAO dimensions | Components (scored features) |
|---|---|---|---|---|
| 1 | **FMA · Food Market Accessibility and Affordability** | Price pressure on what households can buy: year-on-year change in food and headline consumer prices and in staple and protein food prices | Access; Stability | food inflation (CPI food); cost of living (CPI headline); rice price (wholesale; regional: farmgate palay); protein prices (chicken, pork, tilapia) |
| 2 | **AFP · Agricultural and Fisheries Production** | Fall in local food output: year-on-year production change of each commodity group, sign reversed so that a drop raises risk | Availability; Stability; Access (producer income) | cereals (palay, corn); vegetables; root crops; fisheries; poultry and livestock (from 2024) |
| 3 | **CEC · Climate and Environmental Conditions** | Immediate weather exposure that disrupts farming, fishing and livelihoods: rainfall departures in either direction, heat, and nearby tropical cyclones | Stability; Availability | rainfall (absolute departure); temperature (anomaly); cyclones (within 100 km; regional: in PAR) |
| 4 | **EHS · Employment and Household Economic Stability** | Households' income position: provincial annual unemployment and underemployment; nationally, the unemployment change and the remittance decline | Access; Stability | employment (provincial annual rates; national change); remittances (national, regional FIRI only) |
| 5 | **PSV · Household Poverty and Social Vulnerability** | Structural deprivation that worsens the effect of any shock: poverty incidence | Access; Utilization (indirect) | poverty (SAE 2021, population-weighted). Profile only: subsistence incidence, FIES food share, density. |
| 6 | **FIS · Food Insecurity Early-Warning Signals** | News-reported food stress: provincial FSSI-v3 and national shortage-news share | Stability (early warning) | local news (FSSI-v3); national news (GDELT shortage share) |

**Affordability vs. price change.** The task asks which features measure affordability and which measure price changes.
- **FMA** holds the *dynamic price pressure*.
- The *structural affordability* measures sit in **PSV**, so the same deprivation is never counted twice: food poverty, subsistence, food expenditure share.
- PSV is scored on poverty only. Subsistence is too imprecise (9 of 10 provincial CVs > 20%). The FIES food share has no publication date that can be placed before an issue.

**Climate measures.**
- **Immediate exposure:** rainfall departures, heat, cyclones. This is what CEC scores.
- **Agricultural disruption:** recorded in AFP, the realized production loss.
- **Longer-term ENSO stress:** context only (direction ambiguous; about no effect in E65).

## 4. Two scopes, never mixed

| | Provincial FIRI | Regional FIRI |
|---|---|---|
| Units | Cavite, Laguna, Batangas, Rizal, Quezon | CALABARZON |
| Inputs | Provincial observations only | Region IV-A / CALABARZON / national series |
| Indicators | 6 (FMA, AFP, CEC, EHS, PSV, FIS) | 5 (no regional poverty series acquired) |
| National data | Never copied into a province. Shown as context beside the provincial FIRI. | Used, labelled national |
| Computable | 75 of 115 province-quarters (from 2023-Q1); mostly 4 indicators (54 rows), 5 (13), 6 (8) | 10 of 23 quarters (from 2024-Q2) |
| Use | Provincial vulnerability profiling (no provincial label exists) | Regional context; candidate summary predictor for the SWS model |

**Why the provincial FIRI usually rests on four indicators.**
- **PSV** becomes available only from 2025-Q3: the SAE 2021 poverty release is dated 2025-07-01 under the V1 rule.
- **FIS** needs at least 5 local articles, which happened in only 14 province-quarters.

This is reported, not filled.

## 5. FIRI vs. machine learning

**The FIRI is a transparent summary of risk evidence at the issue date** (a nowcast of conditions). **The ML model forecasts SWS Balance Luzon hunger.** They stay separate:

**FIRI:**
- contains no SWS value and no weights learned from SWS;
- every score uses only observations available before the issue and earlier values for its scale.

**The regional model may use:**
- the regional features;
- the regional indicator scores, or the regional FIRI, as one summary predictor (not alongside its own components);
- lagged SWS readings, which are a model input, not a FIRI input.

**Provincial features, scores and the provincial FIRI** are for vulnerability profiling only. There is no provincial label.

**The served FIRI v2 is not eligible as a predictor.** It contains H1 (regional hunger) and SWS-derived weights.

See `E120_MODEL_FEATURE_ELIGIBILITY.csv`.
