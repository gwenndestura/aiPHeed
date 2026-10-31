# E131 experimental results

**Status of the evidence.**
- Development evidence only: every SWS value from 2021 to 2026 had already been seen in earlier experiments.
- The protocol was frozen beforehand (`88b270c`).
- The confirmatory test is the prospective seal.

**Rerun:** `runner/e131_x1.py`, `e131_univariate.py`, `e131_provincial.py <PUF>`, `e131_summary.py`.

## X1 · Measured hunger, 4 areas, walk-forward

**Target.** SWS hunger by area. The tolerance is 1.645 × each quarter's sampling SE: median SE 1.95 points, so a median tolerance of 3.21 points.

### Shared rows (every model forecasts)

| Issue policy | Lead 1 | Lead 2 | Lead 3 | Lead 4 |
|---|---|---|---|---|
| P-DASH (dashboard) | 36 rows / 9 quarters | 28 / 7 | 24 / 6 | 20 / 5 |
| P-REL (release-anchored) | 36 / 9 | 28 / 7 | 20 / 5 | 20 / 5 |

### Share within tolerance, P-DASH (pass needs ≥ 0.75)

| Model | Lead 1 | Lead 2 | Lead 3 | Lead 4 |
|---|---|---|---|---|
| PERSIST | 0.44 | 0.46 | 0.54 | 0.50 |
| CLIM | 0.14 | 0.18 | 0.21 | 0.20 |
| **LLM** | 0.42 | **0.50** | 0.50 | 0.55 |
| DLLM | 0.33 | 0.36 | 0.33 | 0.35 |
| RIDGE-H | 0.36 | 0.32 | 0.17 | 0.10 |
| LGBM-H | 0.28 | 0.46 | 0.42 | 0.50 |
| RIDGE-ALL | 0.36 | 0.32 | 0.46 | 0.15 |
| **LGBM-ALL (proposed)** | 0.31 | 0.39 | 0.46 | 0.15 |
| PSA-ONLY | 0.36 | 0.36 | 0.46 | 0.40 |
| NLP-ONLY | 0.33 | 0.39 | 0.67 | 0.30 |

### MAE in percentage points, P-DASH

| Model | Lead 1 | Lead 2 | Lead 3 | Lead 4 |
|---|---|---|---|---|
| PERSIST | 5.38 | 5.28 | 4.04 | 3.77 |
| LLM | 5.44 | 4.70 | 3.72 | 3.52 |
| LGBM-ALL | 6.12 | 6.13 | 5.05 | 6.35 |
| PSA-ONLY | 6.01 | 7.26 | 4.61 | 5.15 |
| NLP-ONLY | 5.51 | 5.46 | 3.24 | 17.19 |
| RIDGE-ALL | 6.04 | 6.51 | 5.05 | 8.34 |

### Other results

**P-REL at Lead 2.** RIDGE-ALL 0.57, PERSIST 0.54, LLM 0.50. Still far below 0.75.

**Univariate set** (each model judged where it has ≥ 8 past quarters; Lead 2 has 40 rows over 10 quarters, 2024-Q1 to 2026-Q3):

| Model | Within, P-DASH | MAE, P-DASH | Within, P-REL | MAE, P-REL |
|---|---|---|---|---|
| LLM | 0.38 | 5.67 | 0.45 | 5.03 |
| PERSIST | 0.40 | 5.98 | 0.50 | 5.04 |

**Reliability rules.** **No model passes N1–N7 at any lead under either policy** (`out/x1_rules.json`, `out/x1_univariate_rules.json`). The maximum reliable lead is none for every model.

**Information only** (not pass/fail): with 2× the tolerance, LLM at Lead 2 reaches 0.79 and PERSIST 0.75. R² is negative everywhere because of the level shift.

## X3 · Provincial layer

**X3a · Price versus income (FIES 2023 microdata and official thresholds).**
- Replication gap against official 2023 PFDR: 0.00–0.25 points.

| Province | Price effect (points) | Income effect (points) |
|---|---|---|
| Batangas | +0.69 | −0.29 |
| Cavite | +0.12 | −1.72 |
| Laguna | +1.33 | −2.43 |
| Quezon | +0.31 | −6.01 |
| Rizal | +1.73 | −0.03 |

- CPI-updated threshold error: −16.2 % in Laguna and −6.4 % in Rizal.

**X3b · Pattern stability.**
- PFDR order between 2021 and 2023: Spearman −0.82, stability test p = 0.022 (genuine reordering).
- Poverty order: Spearman 0.3 (2021→2023), 0.8 (2023→2025), 0.7 (2021→2025). Quezon is highest in every round.

**X3c · Provincial relative food deprivation** (EB-shrunk PFDR 2023 ÷ Region IV-A 2023):

| Province | Relative risk | Poverty-based (sensitivity) |
|---|---|---|
| Batangas | 1.00 | 0.33 |
| Cavite | 0.78 | 0.48 |
| Laguna | 0.96 | 1.19 |
| Quezon | 0.76 | 2.86 |
| Rizal | 1.34 | 0.95 |

## Seal (prospective, frozen 2026-10-31)

| Seal | File | sha256 |
|---|---|---|
| 4 areas × Leads 1–4 × 10 models | `sealed/E131_PROSPECTIVE_SEAL.csv` | `92b5535f…` |
| Provincial model-based estimates | `sealed/E131_PROVINCIAL_MODEL_BASED_SEAL.csv` | `ed8393e9…` |

Balance Luzon, LLM: **2027-Q1 (Lead 2) 22.8 % [80 % interval 15.8–29.8]**.
