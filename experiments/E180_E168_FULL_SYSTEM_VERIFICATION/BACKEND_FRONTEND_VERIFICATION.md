# E180: backend ↔ frontend consistency (local default env, uncommitted fixes included)

| Item | Backend | Frontend | Status |
|---|---|---|---|
| Province probabilities | E168 history (2027-Q1: Quezon 0.075, Rizal 0.070, Laguna 0.039, Cavite 0.031, Batangas 0.029) | displayed from `/provinces` | VERIFIED consistent |
| Indicator name | `e168_high_food_insecurity_probability` | risk card label hard-coded **"Price-pressure risk"** | **INCORRECT (HIGH, I02)** |
| Thresholds | `/config`: display 0.50, alert 0.60, limited < 5 articles | uses `/config` | VERIFIED |
| Driver percentages | five groups normalised to 100 among themselves; `otherPct` not in `ExplainabilityResponse` | shows the five bars only | **INCORRECT vs required method (HIGH, I04)** |
| Driver labels | `fish_kill` group = fisheries production | "Fish Kill" | INCORRECT label (MEDIUM, I09) |
| LGU ranking | 142 rows, Algorithm 5 | 142 polygons, name-key join | VERIFIED |
| Article counts | feed count and the LIMITED flag consistent (uncommitted fix) | displayed | VERIFIED locally; differs from the model's news-panel count (MEDIUM, I10) |
| Model description | E168 (`/config`, `/thesis/*`, PDF after the uncommitted fixes) | Landing / About describe the retired SWS + price target and seal a498b5ef | **INCORRECT (HIGH, I03)** |
| Mock data | none served | 4 unused components import `mockData`; Admin `SidebarPeek` uses it | LOW (I16) |
| "Data could not be loaded" | CORS allows localhost:5173 only by default | any other port fails | LOW (I17) |
| Production | serves the Chapter I system (I01) | would show Chapter I values | **CRITICAL** |

Dashboard values match the backend for the served numbers; labels, descriptions and the driver-share method do not match the model.

## Additional checks for this verification (2026-11-07)
| Item | Backend | Display | Status |
|---|---|---|---|
| History chart | `/forecast/timeseries`: 17 E168 quarters, scoreType e168 | 2023-Q1..2026-Q3 flagged `isForecast: false`, quarter state "actual" | **INCORRECT (F11)**: back-forecasts shown as observed |
| Map colours | riskLevel from riskScore with cutoff 0.50 / alert 0.60 (`/config`) | colours by riskLevel | VERIFIED (2027-Q1: all low; Quezon limited signal) |
| Active / confirmed alerts | `/alerts`: 0 rows; staged by the quarterly cycle | Admin queue | VERIFIED empty; **not E168-based (F12)**; no E168 P(HIGH) >= 0.60 exists |
| Model version indicator | `/config` indicator `e168_high_food_insecurity_probability`; `servingModel` null | risk card says "Price-pressure risk" | INCORRECT label (F03) |
| Forecast Index Score / probability | riskScore = E168 P(HIGH) | displayed | VERIFIED |
