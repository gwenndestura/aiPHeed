# Maximum reliable lead time

**Answer: no lead is reliable.**
- Under the frozen rule (`FINAL_PROTOCOL.md` §6, R1–R8), Lead 1 fails, so the maximum reliable lead is **none** (`out/results_primary.json` → `max_reliable_lead = 0`).
- The secondary long-history arm gives the same answer on 70 untouched quarters per lead.

## 1. What a "lead" means here

Every prediction records its timing (columns in `out/predictions_primary.csv`):
- the issue date;
- the newest SWS quarter known, with its fieldwork end and publication date;
- the newest PSA CPI month;
- the newest news item;
- the target quarter;
- days from issue to the target;
- the true horizon;
- the age of the newest reading.

| Lead | Rows | Target quarters | Days from issue to the end of the target quarter (median) | True horizon (target − newest known SWS quarter) | Age of the newest SWS reading at issue (days) |
|---|---|---|---|---|---|
| 1 | 44 | 2023-Q4 … 2026-Q3 (11) | 92 | **2** (40 rows); 1 (4 rows) | 64–122, median 93 |
| 2 | 40 | 2024-Q1 … 2026-Q3 (10) | 183 | 3 (36); 2 (4) | 64–122 |
| 3 | 36 | 2024-Q2 … 2026-Q3 (9) | 274 | 4 (32); 3 (4) | 64–112 |
| 4 | 32 | 2024-Q3 … 2026-Q3 (8) | 365 | 5 (28); 4 (4) | 64–104 |

**Two different quantities**
- **Lead:** the distance from the issue date to the target.
- **Age of the newest observation:** how stale the starting point is.

They are not the same. Because SWS publishes 17–99 days after fieldwork, a Lead-1 forecast issued on 1 October is anchored on the April–June survey: it has a true horizon of 2 quarters. The four rows with true horizon 1 are the 2025-07-01 issue, when the April 2025 round had been published on 27 June.

**Example timing records** (latest SWS round, newest PSA month, newest news item)

| Issue date | Newest SWS quarter (published) | PSA month | Newest news |
|---|---|---|---|
| 2023-10-01 | 2023-Q2 (2023-08-02) | 2023-08 | 2023-09-29 |
| 2024-10-01 | 2024-Q2 (2024-07-23) | 2024-08 | 2024-09-30 |
| 2025-07-01 | 2025-Q2 (2025-06-27) | 2025-05 | 2025-06-30 |
| 2026-07-01 | 2026-Q1 (2026-05-12) | 2026-05 | 2026-06-30 |

## 2. Results by lead (the same frozen criteria at every lead)

| Lead | R1 evidence | R2 accuracy ≥ 0.75 | R3 balanced accuracy | R4 Brier | R5 precision / recall | R6 thirds | R7 BL | R8 MAE | Reliable? |
|---|---|---|---|---|---|---|---|---|---|
| 1 | ✓ (11 quarters) | ✗ 0.318 | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | **No** |
| 2 | ✓ (10) | ✗ 0.400 | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | No |
| 3 | ✗ (9) | ✗ 0.444 | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | No |
| 4 | ✗ (8) | ✗ 0.500 | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | No |

**Secondary arm, FIL-LONG on untouched 2003–2020** (280 rows and 70 quarters per lead)

| Lead | Accuracy | Criteria passed | Reliable? |
|---|---|---|---|
| 1 | 0.504 | R1, R8 | No |
| 2 | 0.518 | R1, R8 | No |
| 3 | 0.554 | R1, R8 | No |
| 4 | 0.536 | R1, R8 | No |

## 3. Why no lead can qualify (cause)

The Bayes ceiling (Addendum 1) is the accuracy of a forecaster that knows the hunger process exactly:

| Lead | 1 | 2 | 3 | 4 |
|---|---|---|---|---|
| Random-walk level | 0.58 | 0.54 | 0.53 | 0.50 |
| Mean-reverting level (optimistic) | 0.64 | 0.63 | 0.60 | 0.53 |

Every value is below the 0.75 required by R2. Removing survey noise entirely raises the Lead-1 ceiling only to 0.63.

**Consequence.** No model, and no amount of tuning, can make any lead reliable for this outcome and this rule. That is why the rule was not relaxed or redefined after the results.

## 4. What *can* be said about horizons (supporting, not a reliability claim)

**Level forecasts (MAE, percentage points)**
- On untouched 2003–2020 data, FIL-LONG beats the latest reading at Leads 1–2: 4.22 vs 4.57 (p = .031) and 4.52 vs 4.87 (p = .009).
- A two-reading average does better still: 4.14 and 4.34.
- The level outlook's error grows from about 4.1–4.6 points at Lead 1 to 4.5–5.1 points at Lead 4.

**Calibrated ranges.** E113 found that the persistence band is calibrated at Lead 1 only.

**Economic access (PSA food-price squeeze, province level).** Persistence predicts the sign 70% of the time at Lead 1 and 63% at Lead 2, and is at chance after that. This is an economic-access horizon, **not** a hunger horizon.

**Prospective confirmation.** The forecasts are sealed in `out/sealed_prospective.csv` (SHA-256 `c73a0709…`):
- issued 2026-10-01;
- targets 2026-Q4 … 2027-Q3;
- models FIL, FIL-LONG and FIL-LONG-S, plus persistence.

They are scored with `runner/score_prospective.py` as SWS publishes.
