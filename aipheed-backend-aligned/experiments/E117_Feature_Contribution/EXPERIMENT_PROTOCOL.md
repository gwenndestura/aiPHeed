# E117: pre-registered feature-contribution experiment (frozen 2026-10-31, before any fit)

**Hash.** This file's SHA-256 goes in `runner/PROTOCOL_SHA256.txt`; both are committed before `runner/run_e117.py` runs.

**Branch.** `aiPHeed/corrected-data-pipeline`, from baf691a. Local only.

**Unchanged.** The served model, the dashboard, the API, map colours, the corrected pipeline and raw data. Nothing is deployed.

## 1. Data (frozen)

- **Dataset.** The corrected pipeline's regional forecasting panel (`CORRECTED_PIPELINE/out/regional_forecast_panel.csv`), rebuilt by the same builder (`E116_FIRI_Domains/runner/run_e116.rows()`).
- **Hashes.** The SHA-256 of the panel and of every input is recorded at run time. The run stops if the panel differs from the committed one.
- **Rows.** 872: 4 SWS areas × origins 1999-Q1 to 2026-Q3 × Leads 1-2.

## 2. Target

**Primary: SWS Total Hunger level by area** (NCR, Balance Luzon, Visayas, Mindanao).
- It is regional experienced hunger: the strongest independently observed food-insecurity outcome over time.
- It is not provincial food insecurity, and no provincial forecasting is claimed. The provincial vulnerability profile is not a forecasting target.

**Event (secondary): "above usual".** The target reading exceeds the median of that area's readings published before the issue. The 11.3% line is not used.

## 3. Timing modes

### PRIMARY (strict)
- **Allowed:** only features whose timing status is *verified* in the corrected pipeline:
  - hunger history;
  - news N-SUP / N-AST (dated articles, 2018+);
  - typhoon change C-TC (real-time track observations).
- **One declared exception:** pre-2021 SWS release dates follow the month-end + 60-day rule (E114's +100-day sensitivity held).
- **Masked to NaN in strict mode:** CPI (day-10 rule; back-cast before 2018), fisheries, palay, ONI and unemployment. All are `rule_unverified`.
- **Not testable in strict mode:** market, fish, employment and OFW.

### PROVISIONAL
- All features, including `rule_unverified` ones.
- Results are labelled provisional.

## 4. Variants (one unified LightGBM recipe for all)

**Recipe.** E114/E116, unchanged:
- target = change from the latest reading;
- grid depth {1, 2} × trees {100, 300}; lr 0.03; min_child 20; λ 5; seed 114;
- configuration chosen per origin by the last 4 inner chronological folds (nested selection).

**Provisional variants.**

| Code | Features |
|---|---|
| A | base: h_last, MR, d_last, staleness, lead, area |
| B | A + market (AF_food, AF_gap, AF_dfood, P-RICE) |
| C | A + fish (F_yoy, F_dyoy) |
| D | A + climate (C-ONI, C_nino, C-TC, PAL_yoy) |
| E | A + employment (P-UNEMP) |
| F | A + OFW remittances: **not testable** (no series before 2021; BSP blocks download); recorded |
| G | A + news (N-SUP, N-AST) |
| H | A + all testable domains (B ∪ C ∪ D ∪ E) |
| I | H + news ("full"; V1 has no dated series, so it is not representable) |

**Individual indicators** (A + one indicator):
- IA1 (AF_food, AF_dfood)
- IA2 (AF_gap)
- IA3 (P-RICE)
- IC1 (C-ONI, C_nino)
- IC2 (C-TC)
- IC3 (PAL_yoy)
- IC4 (F_yoy, F_dyoy)
- IE1 (P-UNEMP)
- IN1 (N-SUP, N-AST)

E2 and V1 are not testable.

**Interactions** (A + both domains + the product, against the same without the product):

| Code | Interaction |
|---|---|
| X1 | food prices × employment |
| X2 | fish × climate |
| X3 | climate × food prices |

Prices × remittances and poverty × market are not testable: the data do not exist over time.

**Strict variants.**

| Code | Features |
|---|---|
| S_A | base |
| S_G | base + news |
| S_C2 | base + C-TC |
| S_ALL | base + news + C-TC |

**Comparators.**
- RW (latest reading, persistence);
- MEAN (climatology of known readings);
- DAMP (mean reversion, E114);
- AR1 (E114);
- RIDGE: linear model on the I features, fitted per origin like E114.

## 5. Evaluation

**Periods.** All historical periods have been inspected before, so **none is called untouched**.

| Period | Targets | Status |
|---|---|---|
| P1 | 2003-12 | inspected |
| P2 | 2013-20 | inspected (E114/E116) |
| P3 | 2021-26 | inspected |
| Pooled | 2003-26 | inspected |

**Untouched evaluation = prospective.** The forecasts of every variant and comparator for targets not yet published are sealed in this run:
- origin 2026-Q3: Lead 1 → 2026-Q4; Lead 2 → 2027-Q1;
- origin 2026-Q2: Lead 2 → 2026-Q4.

They are scored when SWS publishes those rounds.

**Dependence.** The four areas share national inputs and quarters, so differences are averaged by target quarter before the quarter-block bootstrap (4000 draws, seed 2031) and the Diebold-Mariano test (Newey-West, lag = lead).

**Measures:**
- **Level forecasts:** MSE, MAE and RMSE, pooled and by area.
- **"Above usual" event:** accuracy, balanced accuracy, precision, recall, F1 and Brier. The probability comes from N(ŷ, σ), with σ the model's own earlier out-of-sample RMSE (at least 8 errors), as in E114.
- **Calibration:** slope and calibration-in-the-large.
- **Overfitting:** train vs test MSE.
- **Contribution stability:** the sign of Δ by period.

**Decision rule (development evidence), per domain and indicator, per lead and mode.**

| Reading | Condition |
|---|---|
| improves | pooled Δ MSE vs base < 0, with 90% CI upper bound < 0, Holm-corrected p < 0.10 (across the testable domains of that mode), and Δ < 0 in at least 2 of the 3 periods |
| conditional | Δ < 0 with CI upper bound < 0 in exactly one period |
| possible noise | pooled CI lower bound > 0 |
| no measurable value | otherwise |

**Complementarity:** H vs the best single domain; X1-X3 vs their no-product versions.

**SHAP is not used as evidence.**

## 6. Claims

- Any contribution found here is **development evidence on inspected data**. Only the sealed prospective forecasts can confirm it.
- No production integration is requested before those results.
