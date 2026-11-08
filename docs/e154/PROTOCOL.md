# E154 protocol: small meaningful inputs, very simple trees

The owner asked for better results and for inputs that are meaningful, with regional income for employment. This is the one option left that adds new information and removes capacity, instead of tuning. **E151 to E153 stand.**

## Evidence status

Fifth look at the same 72 rows, with their errors studied. **Retrospective, whatever the result.** Only sealed forecasts are clean. These choices were made knowing what earlier runs showed: too much model capacity, and little input signal.

## The inputs, each with a reason, fixed here

| Group | Input | Meaning | Scope |
|---|---|---|---|
| Market | `cpi_since` | Food price rise since the last survey | Province |
| Market | `cpi_food_rel_nat` | Local food inflation against national | Province |
| Climate | `soil_since`, `rain_since` | Moisture stress since the last survey | Province |
| Climate | `agri_since` | Farm output change since the last survey | Province |
| Climate | `tc_rate_since` | Cyclone exposure since the last survey | Province |
| Employment | `unemp_chg_since` | Job market change since the last survey | **National** |
| Employment | `income_growth` | Regional real household consumption per person, yearly growth since the last survey | **Regional, new** |
| Remittances | `remit_since` | Remittance growth since the last survey | **National** |
| Poverty | `p_poverty` | Province poverty relative to all provinces | Province |
| Poverty | `income_rel` | Regional real consumption per person against the regional average | **Regional, new** |

**Left out:** news, because it failed its tests; repeated versions of the same quantity.

**Regional labor rates are not included.** They sit in PSA release spreadsheets and PSA blocks automated page fetches, which I do not bypass. Household consumption is a stand-in for income, not a labor measure, and the report says so.

**Data limits:** consumption is at constant 2018 prices from today's PSA table, so earlier values may include later revisions. A year is assumed public from Q3 of the next year; **past release dates are not held.**

## The model, with nothing tuned

Same anchor. LightGBM with one split per tree, 200 trees, learning rate 0.02, at least 20 rows per leaf, L2 penalty 20, monotone signs, 10 seeds, full weight on the adjustment.

## Target, classes and comparators

HFIAS moderate plus severe, HIGH at 50, LOW below, not scaled. Lead 1 is the main result; Leads 2 to 4 are reported. Compared with the E151 required model, persistence, and **LEVEL: the anchor plus only the mean training error,** which tests whether the inputs add anything beyond a level correction.

## Adoption rule, fixed now

E154 replaces the E151 required model **only if,** at Lead 1 on the pool: accuracy is at least 0.75, Brier is no worse than E151's, and accuracy is above the 95th percentile of 100 shuffled-input runs. Release gates decide production separately. **R8 and R9 are not addressed here, so production stays unchanged.**

## One run

The code checks hashes and refuses a second run.
