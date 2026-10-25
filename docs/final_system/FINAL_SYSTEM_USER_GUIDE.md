# aiPHeed user guide (DA Region IV-A)

## Opening the system

**Production:** the Vercel site (frontend) with the Render API.

**Local run:** from the repository root, start two servers.

1. API, in `backend` (port 8000):
   ```bash
   AIPHEED_LEAD2_MODEL=thesis AIPHEED_STRICT_MODEL=1 python -m uvicorn app.main:app --port 8000
   ```
2. Web, in `frontend` (port 8080):
   ```bash
   npm run dev
   ```

Then open `http://localhost:8080/dashboard`.

## The map page

| Part | What it shows | How to read it |
|---|---|---|
| **Regional average priority score** (top left) | The mean priority score of the 5 provinces for the selected quarter, 0–1 | ≥ 0.50 = High priority (red), < 0.50 = Low priority (yellow). It is an **indicator-based priority score**: not a probability, and not the share of hungry families. |
| **What drives this priority score?** | Each driver group's share of the score (SHAP) | A large share means the score leaned on that group. It does not prove that the group causes hunger. |
| **Map** | 5 provinces and 142 cities and municipalities | Province colour = its priority level. A town's position = its rank inside the province by poverty and density. No town or province has a measured hunger rate. |
| **Legend** | Red = High priority, Yellow = Low priority, Grey = no score | Hover for the cutoff |
| **Right panel** | Factors pushing the score up or down, and the news analysed | Each headline carries a chip: **Reported event** or **Possible future risk**. Open a headline for its note. News is context only: it did not improve forecasts. |
| **Timeline and View history** | Past and forecast quarters | See below |

## About & Methodology (bottom left)

**Measured regional hunger (SWS)**
- The latest SWS survey: quarter, fieldwork dates, publication date, and how many days old it is.
- The Balance Luzon hunger rate (CALABARZON is part of Balance Luzon) with its survey margin, and the national rate.
- **Next quarter:** the latest reading carried forward, with the range in which the next reading fell four times in five in the past.
- The LightGBM forecast, with the date it was issued.

**Forecast model and its tested accuracy**
- The LightGBM's accuracy at each horizon, next to the "latest reading" baseline.
- Its average error in percentage points.
- Whether the 75% target was reached (**No**).
- Whether a reliable horizon exists (**Not established**).

## View history

| Table | Content |
|---|---|
| First table | Past priority scores for the region |
| Second table, "Hunger forecasts, Balance Luzon (SWS)" | For each quarter: the LightGBM forecast, the latest SWS reading when it was made, the reading SWS later published, and whether the "above average" call was correct. Rows marked **Sealed** are prospective forecasts kept unchanged until SWS publishes those quarters. |

## Responsible use

**Do**
- Use the latest SWS reading as the regional hunger situation, noting its age.
- Use the priority score and town ranking to decide **where to look first**.
- Use the provincial food-price squeeze (`/api/v1/final/cpi`) as a sign of pressure on food access.
- Use the news panel for situational awareness.

**Do not**
- Report a province's or town's priority score as its hunger rate or as a probability.
- Treat a High-priority colour as proof that families there are hungrier.
- Treat news headlines as a forecast that hunger will rise.
- Claim a reliable forecast horizon: none was established.

## API, for analysts

All routes are read-only and live under `/api/v1/final/`:

| Route | Content |
|---|---|
| `overview` | Latest SWS reading, outlook, LightGBM forecast, CPI, data freshness |
| `evaluation` | Per-lead metrics, baselines, verdicts, news tests, surge results, ceiling verification |
| `families` | The 12 families and their columns, with missingness |
| `contributions` | Driver-group SHAP shares of the LightGBM |
| `archive?kind=retrospective\|prospective&area=BL` | Retrospective and sealed forecasts |
| `news?limit=&category=&kind=future\|reported&before=YYYY-MM-DD` | News events, cut off by date |
| `cpi` | Provincial food-price squeeze |
| `lgus` | All 142 LGUs with priority score, rank, poverty notes and local-evidence status |

## Updating each quarter

1. When SWS publishes a new round, add it, with its publication date, to `aipheed-backend-aligned/experiments/FINAL_FOOD_INSECURITY_LIGHTGBM/data/sws_area_rounds_2021.csv`.
2. Score the seals with `score_prospective.py`, both FINAL's and FIL-OA's.
3. Rerun `run_oa.py all`, then `export_engine.py`, and restart the API.
