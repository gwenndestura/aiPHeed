# E58 trigger implementation audit

**Chapter I** mentions "trigger composition scores" (§1.2) but does **not** enumerate five trigger groups. The five groups audited here are the implementation's: `e44_components.PRICE_GROUPS` and `HUNGER_GROUPS`, the E46 `POLICY` block, and the news `trigger_classifier.py`. They match the list in the audit brief.

**Sources:**
- `runner/a4_triggers.py` → `out/trigger_use_by_origin.csv`, `out/triggers.json`;
- the E55 `tables/feature_audit.csv` (sources, geography, missingness).

**How the trace was done:** at each of the 12 issue dates (10 evaluated + 2026-Q4 + 2027-Q1), the configuration E56 selected was refitted. It reproduces the served E58 record to the 4-decimal rounding of stored values. Then the inputs the LightGBM trees actually split on were counted.

## 1. Path from data to dashboard

**Data → features:**
- `e41_lib.load` (CPI, SWS, production, LFS, news composition);
- `e43_lib.load_extra` (typhoons/ENSO, BSP/FX, rice prices, FSSI);
- `e46_lib` (policy orders);
- each origin uses only data published before it.

**Features → model.** The E56 price part is LightGBM.
- Its starting score (offset) is the base-effect projection of provincial food inflation from PSA CPI.
- Its trees use the selected feature set. At each origin this is "market" (Market group + policy) or "all" (five groups + news + optional poverty).

**Hunger part:** the I7 ridge on regional means of F_now, ENSO (current and lagged), typhoon counts (current and lagged), palay, fish, unemployment, underemployment, remittances in PHP, FX and news volume. It is **not** LightGBM and **not** in the TreeSHAP bars.

**Model → explanation:**
- TreeSHAP (`pred_contrib`) of the price part, grouped into the five groups; the offset is counted as Market.
- Group status: contributes / no_effect / insufficient_data.

**Explanation → API → dashboard:**
- `/explainability` returns five trigger cards (`pct`, direction, status, evidence note) and the plain summary, which carries the E58 warning text.
- The approved left/right panels render them.

**E58-EW rule:** it uses only P_price and P(HIGH) and adds **no input of its own**.

## 2. Use by group (12 issue dates)

| Group | Data (geography, latest) | Offered to the trees | **Used in tree splits** (origins / splits) | Served "contributes" (of 60 entries) | In hunger part |
|---|---|---|---|---|---|
| **Market / food prices** | PSA provincial food and headline CPI (to 2026-08 at the last issue); PSA wholesale rice (provincial, t−1); 4 national rice-policy features; news_market | 12 / 12 | **10 / 550**: gap_now, rice_whsl_yoy, F_now, D_now, F_hat_M1, plus the CPI offset at every origin. The policy features were never used in a split. | **58** | F_now |
| **Climate / weather** | IBTrACS typhoons (provincial 300 km, quarter t); NOAA ONI (national, t−1); PSA palay and corn (provincial, t−1); 2 interactions; news_climate | 6 / 12 | **6 / 205**: palay, corn, typhoon lag, interactions; news_climate once | 20 | ENSO, typhoons, palay |
| **Fish kill / fisheries** | PSA fisheries and aquaculture production (provincial, t−1). **No official fish-kill event series exists.** news_fish_kill nonzero in 7 of 105 province-quarters. | 6 / 12 | **2 / 12** | **0** | fish_yoy |
| **Employment / livelihood** | PSA LFS unemployment and underemployment (**national**, t−1); news_employment nonzero in 1 of 105 | 6 / 12 | **5 / 52**: ur_yoy, under_yoy | 15 | ur_yoy, under_yoy |
| **OFW remittances** | BSP cash remittances (**national**, t−1, **ends 2025-Q4**, missing at the 2026-Q2/Q3 issue dates); ECB USD/PHP; news_ofw_remittance **always 0** (105/105) | 6 / 12 | **6 / 89**: remit_php, remit_usd, fx | 25 | remit_php_yoy, fx_yoy |
| News volume (NLP) | article count per province-quarter | 6 / 12 | 1 / 29 | (other) | news_n |
| Poverty (candidate) | PSA 2021 SAE, province mean (as-of from 2025) | 5 / 12 | 1 / 1 | (other) | – |

**When each group is used.** At the first five evaluated origins (2023-Q4..2024-Q4) the selected feature set was **Market only**, so the non-market triggers entered the trees only from 2025-Q1 onward. The 2024-Q2 early warning (EMERGING) came from Market inputs and the CPI offset alone.

**The NLP trigger signal.** The five news trigger shares are almost always zero in the model data:

| News share | Nonzero province-quarters (of 105) |
|---|---|
| OFW | 0 |
| Employment | 1 |
| Market | 6 |
| Fish kill | 7 |
| Climate | 44 |

Only news_climate (once) and news volume (once) reached a tree split. **The NLP component contributes almost nothing to E56/E58 forecasts.**

## 3. Verdict

**What can be claimed:**
- E58 uses **food prices** genuinely and predominantly.
- **Climate, employment and OFW** are used intermittently (from 2025-Q1), with small effects.
- **Fisheries** is used only marginally and never counts as a contributing factor.
- No **fish-kill** event data exist.
- The **news-derived** trigger shares are essentially empty.
- **Rice-policy features**, although provided, were never split on.
- The dashboard shows all five groups at every quarter, with their status.

**What cannot be claimed:** that E58 "uses all five triggers as predictors". The dashboard's five cards are faithful attributions (zero or no-effect where unused), not evidence that each trigger drives the forecast.

**Classification: Partially supported.** All five are implemented as inputs and displayed, but only Market / Prices is materially used; fish-kill and NLP triggers are effectively absent.
