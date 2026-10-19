# E58 target and data validity

## 1. What Chapter I asks for

- **Target.** "a composite food stress label combining SWS (Social Weather Stations) quarterly hunger data and PSA province-level food CPI deviation, anchored to the FAO SDG 2.1.2 baseline established by the DOST-FNRI ENNS" (§1.2).
- **Scope.** "SWS quarterly hunger data and PSA food price data will be used to determine food insecurity risk" (§1.7).
- **Data contribution.** "derives a validated forecast target from publicly available CPI data" (§1.1).

## 2. What E58 actually predicts

**T43.** A province-quarter is HIGH when both hold:
- **(a)** Balance Luzon SWS hunger > 11.3%. This is the 60th percentile of the 2021–2022 rounds; it is not an FNRI ENNS/FIES anchor.
- **(b)** The province's PSA food YoY, **or** food-minus-headline YoY, is above its own 2021–2022 60th percentile.

**Two outputs** (E58-EW):
- **P(HIGH)** = P(regional hunger stays above 11.3%) × P(provincial food-price pressure);
- **P_price**: the price part alone. It drives the EMERGING level.

| Concept | What E58 provides | Status |
|---|---|---|
| 1. Food-insecurity risk | P(T43 HIGH), a **risk indicator** built from one regional hunger series and provincial prices | a proxy, not a measured provincial food-insecurity outcome |
| 2. Food-price pressure | P_price and the PS label (CPI only) | directly predicted |
| 3. Rising food stress | ONSET = HIGH at the target while the latest known label was LOW; direction = rising / steady / easing | defined from the proxy labels |
| 4. Confirmed hunger | none at provincial level; SWS hunger is regional (Balance Luzon, which extends beyond CALABARZON) | **not predicted at provincial level** |
| 5. Future-quarter forecast | two quarters ahead of the predictor quarter (issue day 1 of t+1, target t+2) | provided |
| 6. Relative prioritization | 142 LGU ranking = province probability × (0.6 poverty + 0.4 density) | a weighting, not a municipal forecast |

**The decisive fact about the evaluation:**
- On **every** evaluated row (50/50, 2024-Q2..2026-Q3) the hunger condition (a) was met: H was 15.3–25.3%. So **T43 equals the price-pressure label PS** on all evaluation rows (checked in `a1_reproduce.py`).
- **Every E58 accuracy figure therefore measures the forecasting of provincial food-price pressure during a period of elevated regional hunger.**
- In the test window, food-insecurity risk and food-price pressure cannot be told apart. Neither the hunger part nor provincial differences in hunger is tested.

**EMERGING ≠ hunger.**
- An EMERGING warning states that price pressure is likely while the latest hunger reading does not confirm elevated hunger.
- In 2021–2023, 24 of the 29 province-quarters with price pressure were **not** T43 HIGH, because hunger was at or below 11.3% (E58 `results.json`).

**Face validity against direct measures** (descriptive; n = 5 provinces, no inference):
- Ranked by E56's mean forecast, the provinces order Quezon > Cavite > Laguna > Batangas > Rizal. This almost matches the 2021 SAE poverty ordering (Quezon 20.3, Cavite 11.1, Batangas 8.6, Laguna 7.9, Rizal 6.9).
- It does not match PSA 2023 subsistence incidence (Rizal 2.6, Batangas 1.4, Laguna 1.3, Quezon 0.9, Cavite 0.8).
- FNRI FIES is regional only: CALABARZON 19.1% in 2023, the lowest in the country. It cannot validate provincial forecasts.

**What would validate the target:**
- a provincial or municipal food-insecurity outcome with quarterly or at least annual frequency (CBMS FIES; provincial FIES/NNS);
- or a provincial hunger series.

Until then, E58 predicts a **food-insecurity risk proxy** whose evaluated part is price pressure.

## 3. Forecast timing and data availability (`runner/a2_timing.py` → `out/timing_by_origin.csv`, `out/timing.json`)

**Convention.** With the latest completed quarter 2026-Q3, the current quarter is 2026-Q4 and the target is 2027-Q1. The forecast was issued 2026-10-01. It stays **pending**: no outcome exists. The record and the frozen file `E56_TUNED_PROSPECTIVE_2027Q1.json` (sha 044499b2…) both say so.

**Truncation test at all 10 evaluated origins.** Every input was truncated to what was published before the issue date:
- CPI months through month 2 of t;
- SWS rounds posted before the origin;
- production, rice and remittances through t−1;
- LFS months of t−1;
- typhoons and news through t;
- policy orders announced before the origin.

Features were then rebuilt from the truncated data and E56 re-run. **Forecasts equal the sealed ones at every origin** (max diff 5e-13; same configuration).

**Latest inputs at each issue date** (from `timing_by_origin.csv`):

| Issue | CPI to | SWS used (posted) | Next SWS posted | Production / LFS | Remittances | Lead to observable outcome |
|---|---|---|---|---|---|---|
| 2024-01-01 | 2023-11 | 2023-Q3 (2023-11-20) | **2024-01-22** | 2023-Q3 / 2023-09 | 2023-Q3 | 6.7 months |
| 2024-04-01 | 2024-02 | 2023-Q4 (2024-01-22) | 2024-04-30 | 2023-Q4 / 2023-12 | 2023-Q4 | 6.5 |
| 2024-07-01 | 2024-05 | 2024-Q1 | 2024-07-23 | 2024-Q1 | 2024-Q1 | 6.5 |
| 2024-10-01 | 2024-08 | 2024-Q2 | 2024-10-17 | 2024-Q2 | 2024-Q2 | 6.3 |
| 2025-01-01 | 2024-11 | 2024-Q3 | 2025-01-14 | 2024-Q3 | 2024-Q3 | 7.4 |
| 2025-04-01 | 2025-02 | 2025-Q1 (2025-03-29) | 2025-06-27* | 2024-Q4 | 2024-Q4 | 7.2 |
| 2025-07-01 | 2025-05 | 2025-Q1 | 2025-08-15* | 2025-Q1 | 2025-Q1 | 6.5 |
| 2025-10-01 | 2025-08 | 2025-Q1 | 2025-11-05* | 2025-Q2 | 2025-Q2 | 7.3 |
| 2026-01-01 | 2025-11 | 2025-Q1 | 2026-01-14 | 2025-Q3 | 2025-Q3 | 7.7 |
| 2026-04-01 | 2026-02 | 2025-Q4 (2026-01-14) | 2026-05-12 | 2025-Q4 | 2025-Q4 | 6.4 |

\* Supplementary SWS rounds (`definition_A` False). They are used for labels, but not by the hunger gate. So from 2025-07-01 to 2026-01-01 the gate read 2025-Q1 hunger, 2–3 quarters old. Using all rounds changes **no** decision (sensitivity S2).

**Findings on timing:**

| Finding | Result |
|---|---|
| Future-data leakage | **None found.** The truncation test passes at all origins, and every SWS round used was posted before the issue date. |
| Lag rules | Conservative: CPI month 3 of t and the next SWS round are excluded. |
| Data backfilling | CPI is the 2018-base OpenSTAT series. Its 2021 values were re-published under the 2018 base in 2022, before every evaluated origin (≥ 2024-01-01), so this is not leakage. The news corpus was collected retrospectively in 2026 from article archives. Article dates precede each origin, but the corpus completeness at the time differs from what a live system would have seen. This is a limitation, not outcome leakage. |
| Design-level dependence (not data leakage) | T43's thresholds (E40, P60 of 2021–22) were chosen after inspecting the HIGH share of development quarters 2023-Q1..2025-Q1, which overlap the evaluation window. E43–E58 were all designed while examining these same quarters, and the EW rule was designed from E56's 2024-Q2 errors. **The evaluation is internal development evidence, not an untouched test.** |
| Missing data | BSP remittances end at 2025-Q4, so they are missing only at the 2026-Q2/Q3 issue dates (not evaluated). They are shown as "limited data". LightGBM routes NaN natively; nothing is imputed with future values. |

**Verdict:** forecast timing and absence of identified leakage are **Supported**. Target validity as a measure of food-insecurity risk is **Partially supported** (Chapter I-consistent composite, but evaluated only as price pressure; no provincial outcome; no FNRI anchoring).
