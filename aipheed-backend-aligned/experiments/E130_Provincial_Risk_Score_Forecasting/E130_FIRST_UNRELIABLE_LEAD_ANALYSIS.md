# E130 first unreliable lead

## Result

**The first unreliable lead is Lead 1, for every model.** It fails N1 because there are no quarterly provincial reference observations.

Under the frozen rule (protocol §8), the maximum reliable lead is the furthest *consecutive* reliable lead from Lead 1. The run therefore ends at Lead 1, and no later lead can be declared reliable. That holds even though Lead 1 is not itself the operational goal (Lead 2 is).

## Why longer horizons get worse

These mechanisms are documented on today's data and would bind once a provincial target exists:

| Mechanism | Evidence | Effect per extra lead |
|---|---|---|
| **Information horizon** | At the quarter-start issue the newest SWS reading is 3 quarters before the Lead-2 target and 5 before Lead 4 (`E130_ISSUE_DATE_AND_OPERATIONAL_LEAD_MAPPING.csv`) | +1 quarter of unobserved change |
| **Publication lags of provincial predictors** | Food CPI and rainfall: 2 quarters behind the issue quarter. Production: 3. Provincial LFS: annual, 4–7 quarters old at Lead 2. PFDR: 5–13 quarters old. | The newest provincial signal is already 2–3 quarters old at Lead 1 |
| **Persistence of provincial signal** | Province-specific food-CPI deviations have autocorrelation 0.74 / 0.55 / 0.29 / −0.05 at 1–4 quarters (E129). The E130 recompute at 2 quarters is 0.54. | By Lead 4 the provincial price signal carries no information about its own future |
| **Regime shifts** | Regional hunger jumped from 11.2 (2023) to 19.6 (2024). E128: Lead-4 LightGBM 0/6 on the shift. | Longer leads cross more regime changes |
| **Reference noise** | 2023 signal-to-noise is 0.73. Changes are detectable only above 1.4–3.0 pp (80 % power). | Small real changes look like noise at every lead |

## Is the limit the data, the target, the features, the model, or inherent?

| Source | Contribution |
|---|---|
| **Target** (decisive) | No quarterly provincial food-insecurity measurement exists |
| **Data volume** | 10 provincial values and 5 changes. Even a quarterly series would need 20–40 quarters. |
| **Features** | Mostly common across provinces (median common-quarter share 0.71) or stale (annual LFS, static poverty) |
| **Model** | Untestable here. On the regional target (E128), LightGBM beat no baseline. |
| **Inherent** | Two-quarter-ahead hunger change has been near-unpredictable regionally: E79's best trigger variant explained 6 %, and the planning simulation needs ≥ 50 % |
