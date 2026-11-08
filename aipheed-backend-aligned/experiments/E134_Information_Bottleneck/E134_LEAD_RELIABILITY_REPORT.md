# E134 Lead 1–4 reliability report

**Definitions** (`backend/app/quarterly/target.py`):
- Lead k targets quarter D − 1 + k. The issue date is the first day of D (P-DASH).
- The information horizon h counts from the latest SWS quarter; it is 3 at Lead 2 in most issues.

**Criteria:**
- N1–N7 exactly as frozen (`e130_lib.numeric_reliability`).
- Validation also requires N2 and N3 on S-E132.

**Sources:** `out/e134_rules.json`, `out/e134_summary.json`, `E134_MODEL_COMPARISON.csv`.

## Selected candidate: HFM-X (P-DASH, S-U)

| Lead | Rows / quarters | Within | MAE | RMSE | Bias | 80 % coverage | Sharp increases within | p vs persistence | Fails (S-U) | Fails (S-E132) |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 44 / 11 | 0.55 | 4.70 | 6.13 | — | 0.70 | — | 0.035 | N2, N5, N6 | N1, N2, N5, N6, N7 |
| 2 | 40 / 10 | 0.50 | 4.87 | 6.42 | −2.53 | 0.75 | 8 / 16 | 0.089 | **N2, N5** | N1, N2, N4, N5, N6 |
| 3 | 36 / 9 | 0.50 | 5.10 | 6.56 | — | 0.69 | — | 0.14 | N1, N2, N4, N5, N6, N7 | N1, N2, N3, N4, N5, N6 |
| 4 | 32 / 8 | 0.31 | 5.51 | 6.80 | — | 0.75 | — | 0.18 | N1, N2, N4, N5, N6 | N1, N2, N3, N4, N5, N6 |

**Lead 2 by area** (within): Metro Manila 0.80, Balance Luzon 0.60, Visayas 0.40, Mindanao 0.20.

**High-hunger tercile bias at Lead 2:** −7.14.

## All candidates, Lead 2, P-DASH

| Model | S-U within | S-U MAE | S-E132 within | S-E132 MAE |
|---|---|---|---|---|
| PERSIST | 0.40 | 5.98 | 0.46 | 5.28 |
| SEAS-LLM | 0.45 | 5.72 | **0.61** | 4.78 |
| HFM-X | **0.50** | 4.87 | 0.43 | 4.96 |
| E134-AREA-T | 0.50 | 5.39 | 0.43 | 5.67 |
| E134-AREA-O | 0.48 | 4.85 | 0.39 | 5.24 |
| E134-ONI (PH2, post-hoc origin) | 0.50 | **4.27** | 0.43 | 4.47 |
| E134-ENS | 0.48 | 4.81 | 0.50 | 4.42 |

**Within tolerance by lead (S-U, P-DASH):**

| Model | L1 | L2 | L3 | L4 |
|---|---|---|---|---|
| HFM-X | 0.55 | 0.50 | 0.50 | 0.31 |
| E134-AREA-T | 0.50 | 0.50 | 0.42 | 0.50 |
| E134-AREA-O | 0.50 | 0.48 | 0.44 | 0.47 |
| E134-ONI | 0.61 | 0.50 | 0.53 | 0.41 |
| E134-ENS | 0.48 | 0.48 | 0.44 | 0.41 |
| SEAS-LLM | 0.39 | 0.45 | 0.33 | 0.44 |

**P-REL** (separate operational design, never selected): the best Lead-2 within is E134-ENS 0.57 (S-U).

## Decision

- **No model passes N1–N7 at any lead, on any set, under any policy.**
- **Maximum reliable lead: none established.**
- **Lead 2 is not reliable.** The best agreement, 0.50, is 20 of 40 rows. 75 % needs 30 of 40, so **10 more rows** must fall within tolerance.
- Leads 3–4 also fail **N1**: there are fewer than 10 evaluable quarters in 2021+ data.
