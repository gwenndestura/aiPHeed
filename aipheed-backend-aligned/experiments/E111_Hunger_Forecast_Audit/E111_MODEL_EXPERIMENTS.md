# E111 Model experiments

**Protocol:** `PROTOCOL.md` sha `7086aeb1…`, frozen 09:28 UTC before scoring. **Addendum 1:** a corrected DM test, applied after the first scoring; both scorings are kept.

**Status of the evidence.** All quarters had been examined before (E107–E110). **Every result here is exploratory development evidence**, especially ASYM, which was motivated by E110's surge finding on the same quarters.

**Rows.** The panel has 4 SWS areas, with inference clustered by quarter. The rule for an origin to be scored is the same for every method.

| Lead | Quarters | Area-rows | Range | True horizons |
|---|---|---|---|---|
| 1 | 13 | 52 | 2023-Q2..2026-Q3 | 2 (48 rows), 1 (4) |
| 2 | 12 | 48 | 2023-Q3.. | 3 (44), 2 (4) |
| 3 | 11 | 44 | 2023-Q4.. | 4 (40), 3 (4) |
| 4 | 10 | 40 | 2024-Q1.. | 5 (36), 4 (4) |
| 5 | 9 | 36 | 2024-Q2.. | 6 (32), 5 (4) |
| 6 | 8 | 32 | 2024-Q3.. | 7 (32) |

## Experiments

| ID | Hypothesis | Change | Result |
|---|---|---|---|
| DT | momentum anticipates surges | H_last + φ̂ · slope · horizon, φ̂ pooled over 4 areas | φ̂ is estimated at about 0 at every origin, so DT ≈ RW. **No momentum** is detectable in 2021+ data. |
| BRK | the 2025 respondent change breaks the series | LLR restarted at 2025-Q2 | Same as LLR where it applies. Lead 2 gains, but fails the BL accuracy bound (P2). |
| ASYM | asymmetric cost: never forecast below the latest reading | max(RW, LLR) | **Best Lead-1 method** (details below). Fails P3 only, because by design it is worse when hunger falls. |
| LLR | survey-noise filtering (E110) | — | Lead 2: better than RW in every check except the absolute BL bound (P2) |
| LGBM12 (required) | the 12 FIRI families add information | E109 LightGBM, BL | Lead 1: MAE 4.04 vs RW 3.72 (9 quarters), not reliable. Leads 2–4: insufficient evidence. |
| FAM-*f* (×12) | a single family adds information | RW + ridge on one family | **No family is significant** after Holm correction at Leads 1–2. |

## Continuous results (panel MAE in points; block 95% CI)

| Lead | RW | MA2 | LLR | DT | BRK | **ASYM** |
|---|---|---|---|---|---|---|
| 1 | 4.84 (3.69–6.04) | 4.88 | 4.71 | 4.84 | 4.79 | **4.44** (3.23–5.69) |
| 2 | 5.53 (3.54–7.92) | 5.04 | **4.83** (2.79–7.82) | 5.53 | 4.90 | 5.07 |
| 3 | 5.98 | 5.63 | **5.41** | 5.98 | 5.57 | 5.47 |
| 4 | 6.37 | 6.24 | 6.23 | 6.37 | 6.31 | **5.62** |
| 5 | 7.41 | 7.46 | 7.32 | 7.41 | 7.34 | **6.72** |
| 6 | 8.38 | 8.51 | 8.33 | 8.38 | 8.33 | **7.59** |

**Balance Luzon** (rows within the panel):

| Lead | RW | MA2 | LLR | BRK | ASYM |
|---|---|---|---|---|---|
| 1 | 3.32 | 3.85 | 3.89 | 4.01 | **3.19** |
| 2 | 4.76 | 4.32 | 4.50 | 4.46 | **4.31** |

**Paired tests vs RW** (mean quarter differential; one-sided DM with Newey–West variance):

| Lead | ASYM | LLR | BRK |
|---|---|---|---|
| 1 | −0.40 (**p = 0.002**) | −0.12 (p = 0.39) | p = 0.46 |
| 2 | −0.47 (**p = 0.014**) | −0.70 (**p = 0.058**) | −0.63 (p = 0.073) |
| 3 | −0.51 (p = 0.073) | p = 0.12 | — |
| 4 | −0.76 (p = 0.096) | — | — |

## Surge cost and uncertainty

**Surge cost.** Underprediction on sharp increases, i.e. rows where the outcome exceeds the latest reading by more than its margin. Mean underprediction in points (number of such rows):

| Lead | RW | LLR | ASYM |
|---|---|---|---|
| 1 | 10.18 (11) | 10.31 | **8.71** |
| 2 | 10.60 (13) | 9.91 | **9.23** |
| 3 | 10.93 (15) | 9.73 | **9.25** |

**Every method misses most sharp increases.** The miss rate is 0.8–1.0: no method forecast the 2024 surge or the 2025–26 jumps.

**Interval coverage** (nominal 80%) at Leads 1–2: RW 0.67 / 0.67, ASYM 0.71 / 0.71, LLR 0.71 / 0.73. Every method under-covers; none reaches 80%.

## 12-indicator LightGBM and family screen (Balance Luzon, Lead 1, 9 quarters)

- **LGBM12:** MAE 4.04 vs RW 3.72.
- **Single-family ridge vs RW** (mean quarter differential):

| Family | Differential |
|---|---|
| H1 | +0.72 |
| A2 | +0.17 |
| C3 | +0.18 |
| A1 | +0.13 |
| C1 | +0.11 |
| C2 | +0.02 |
| C4 | +0.01 |
| A3 | −0.03 |
| N1 | −0.05 |
| E2 | −0.05 |
| V1 | −0.07 |
| E1 | −0.09 |

- **Holm-adjusted p = 1.0 for every family.**
- **Lead 2:** every family is worse than RW (+0.4 to +1.8).
- **Sensitivity S-ALL** (including the commissioned round): LGBM12 4.31 vs RW 3.81.
- **Sensitivity S-HH:** too few quarters (3).

## Sensitivities (panel)

| | ASYM Lead 1 | LLR Lead 2 |
|---|---|---|
| Primary | 4.44 | 4.83 |
| S-NOINF | 4.51 | 4.85 |
| S-VOTERS | 4.44 | 4.85 |

The conclusions are unchanged.
