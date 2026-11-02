# Objective 3: municipal and city rankings

> "To produce spatially disaggregated municipal and city food insecurity risk rankings from validated province-level
> forecasts, using PSA published poverty incidence and population density as vulnerability weights."
> (Chapter I §1.5.2)

**Status: Partially achieved.**
- The rankings are produced with the approved weights.
- They do not come from a **validated** forecast (no lead passes R1–R7).
- The forecast is **regional, not province-level**.
- No LGU outcome exists to check them against.

## 1. What was produced

File: `out/lgu_rankings_2027Q1.csv`, copied unchanged from `IMPROVE_V2/out/lgu_rankings.csv` (142 rows).
- **Every row is labelled "priority ranking, not a measured food-insecurity rate".**
- Forecast used: the sealed food-insecurity forecast for **2027-Q1** (Lead 2, issue date 2026-10-01), P(Balance Luzon hunger > 11.3%) = **0.860**.
- Method: the backend's approved ranking (`app/quarterly/forecaster_v2.lgu_table` → `app/quarterly/lgu_poverty.rank_lgus`), read-only, exact ranks:
  - risk index = province probability × (0.6 × poverty_norm + 0.4 × density_norm);
  - both terms are min-max normalised within the province, and LGUs are ranked within the province;
  - poverty: PSA 2021 city and municipal Small Area Estimates; density: PSA 2024 POPCEN population ÷ land area.
- Coverage: 142 LGUs (Batangas 34, Cavite 23, Laguna 30, Quezon 41, Rizal 14).
  - 141 use their own PSA municipal poverty estimate.
  - 1 (Lucena City) uses a province-mean substitute, flagged in the file.

**Correction to IMPROVE_V2 RESULTS.md §10.** That file repeats the backend's older note that "many LGUs carry a
province-mean poverty substitute". In the current input table only **1 of 142** does. The IMPROVE_V2 file is not edited;
the correction is recorded here.

### Top three per province, 2027-Q1

| Province | Rank 1 | Rank 2 | Rank 3 |
|---|---|---|---|
| Batangas | Lipa City (0.775) | Bauan (0.645) | San Pascual (0.642) |
| Cavite | Gen. Mariano Alvarez (0.545) | General Emilio Aguinaldo (0.522) | Cavite City (0.516) |
| Laguna | Siniloan (0.529) | San Pedro City (0.401) | Biñan City (0.396) |
| Quezon | Lucena City (0.593; poverty substitute) | San Francisco (0.532) | Macalelon (0.529) |
| Rizal | Taytay (0.860) | Antipolo City (0.565) | Cardona (0.550) |

Index values are relative within a province. They are **not** probabilities or rates for the LGU.

## 2. What the ranking can and cannot say

**The forecast is regional.** All five provinces receive the same probability (0.860), so:
- the order **inside** each province comes from poverty and density alone; the forecast only scales the score;
- comparisons **across** provinces mostly reflect how spread out each province's poverty and density are, not different forecast risk.

**Can be said:** "If Balance Luzon hunger is likely to be high next quarter (P = 0.86), these are the LGUs in each
province where poverty and crowding suggest attention first."

**Cannot be said:**
- "LGU X has a higher food-insecurity rate than LGU Y";
- "the forecast for province A is higher than for province B";
- "the ranking is validated".

## 3. What is missing, and why

| Missing | Category | What would unblock it |
|---|---|---|
| A **validated** forecast | (b) data | Sealed 2027+ forecasts scored as SWS publishes; R1 needs 40 quarters (`OBJ2_METRICS_AND_HORIZON.md`) |
| A **province-level** forecast | (b) data | A provincial food-insecurity outcome (provincial FIES or CBMS) to train and score against |
| An external check of the LGU order | (b) data | **CBMS 2024** LGU food-security results: turned over to LGUs from September 2025 but not public (`FINAL_OBJECTIVE_ACHIEVEMENT/sources/LOCAL_DATA_SEARCH_LOG.md`) |
| H4: consistency with DA evaluators' judgement | (c) people | DA Region IV-A evaluators rank or rate LGUs in the Post-Survey Questionnaire; compare with Spearman ρ per province (`OBJ5_EVALUATION_INSTRUMENT.md`, Part B) |
