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
