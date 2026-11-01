# E134 leakage and calibration audit

## Feature availability (point in time)

| Feature | Observation | Availability rule used | Revision status | Coverage | Geography |
|---|---|---|---|---|---|
| SWS rounds (target and history) | Fieldwork dates | Publication date per round (`published < issue`) | Not revised | 2021-Q2 … 2026-Q3 | 4 areas |
| Rice CPI q/q (A) | Monthly | Quarter end + 10 days | PSA CPI can be revised; latest vintage used (vintage caveat) | 2021-Q2+ | Regions → areas |
| Bottom-30 % food CPI (A) | Monthly | Quarter end + 10 days | As above | 2021-Q2+ | Regions → areas |
| ONI (C) | Monthly | E119 period rule (one quarter back) | ONI is revised slightly as SST data update; latest vintage | 2021+ | Global |
| Typhoons in PAR (C) | Event | E119 period rule | Final best track | 2021+ | PAR |
| Unemployment change (E) | Quarterly LFS | E119 period rule | Revised at rebenchmarking; latest vintage | 2021+ | National |
| GDELT shortage share (N) | Daily | E119 period rule | Index can change | 2021+ | National |
| Poverty (V) | Survey years | E131 release dates | Revised 2021 values; latest | 2021, 2023, 2025 | Regions |
| **Area rainfall deficit aR (new)** | Daily | Quarter end + 10 days. The same-quarter climatology uses only quarters available at the issue (≥ 2). | NASA POWER updates IMERG-based values; latest vintage | 2021-Q1 … 2026-Q3 | 18 regional points → areas |
| **Area palay drop aP (new)** | Quarterly | Quarter end + **75 days** (conservative). YoY only from 2022 (no pre-2021 base). | PSA revises palay estimates; latest vintage | 2022-Q1 … 2026-Q3 | Regions → areas |

**Leakage controls (verified by code and tests):**
- Standardization of every driver is in-fold, over values available at the issue.
- Variances and β are refitted at every issue on prior rounds only.
- Seasonal and design effects come from post-break innovations available at the issue.
- The break date is documented, not fitted.
- No target-derived feature: drivers are exogenous; the history enters only through the state.
- Missing values become neutral 0; no imputation from the future.
- Assertions check that no loaded row precedes 2021.
- Tests check that every driver quarter used at an issue was published by it (`test_e134_information.py`).

**Residual risk.** Vintage: the latest revised values are used for CPI, palay, LFS and NASA POWER, not the real-time vintages. This can only overstate skill slightly. It is not material to a negative result.

## Calibration (80 % intervals, P-DASH, S-U)

| Model | L1 | L2 | L3 | L4 |
|---|---|---|---|---|
| HFM-X | 0.70 | 0.75 | 0.69 | 0.75 |
| E134-AREA-T | 0.66 | 0.72 | 0.61 | 0.69 |
| E134-ONI | 0.68 | 0.82 | 0.75 | 0.78 |
| E134-ENS | 0.70 | 0.80 | 0.72 | 0.81 |
| SEAS-LLM | 0.66 | 0.55 | 0.67 | 0.59 |
| PERSIST | 0.66 | 0.70 | 0.64 | 0.69 |

**HFM-X detail:**
- **Interval width (mean, full):** 10.8 / 11.9 / 12.8 / 13.4 points at Leads 1–4.
- **Coverage by area (Lead 1–4 pooled):**

  | Area | Coverage |
  |---|---|
  | Metro Manila | 0.97 |
  | Balance Luzon | 0.71 |
  | Visayas | 0.61 |
  | Mindanao | 0.61 |

- **Coverage during sharp increases:** 0.46 for HFM-X, against 0.31 for SEAS-LLM.

**Conclusion.**
- HFM-X meets N7 (0.70–0.90) at Leads 1, 2 and 4.
- The intervals are wide: about ±6 points at Lead 2 against a tolerance of about ±3.2.
- Coverage is too low in Visayas and Mindanao and during surges. The intervals under-state escalation risk.
