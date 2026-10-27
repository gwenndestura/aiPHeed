# VALIDATOR_ONLY protocol: PSA food CPI and SWS hunger used only to validate, never as inputs

**Frozen before any scoring (2026-10-27).** The SHA-256 is recorded in `runner/PROTOCOL_SHA256.txt`.

## Decision being tested

The researcher's decision of 2026-10-27 is that **PSA food CPI and SWS hunger are validators, not indicators.** This follows Chapter I:
- §1.4: the independent variables are news-derived signals and government socioeconomic indicators;
- §1.7: SWS hunger and PSA food prices determine the risk.

## Target (unchanged; the validator)

**Label T43c, as served.** A province-quarter is HIGH when:
- SWS Balance Luzon hunger is above 11.3%, AND
- the province's food CPI YoY, or its food-minus-headline gap, is above its 2021-22 60th percentile.

SWS and PSA food CPI appear **only** in this label.

## Inputs removed (computed from PSA food CPI or from SWS)

**From food CPI:**

| Column | What it is |
|---|---|
| `A1_food`, `A1_gap` | Food CPI projection, and its gap against headline |
| `A_mom` | Food CPI momentum |
| `O_food_yoy` | Region IV-A food CPI YoY |
| `O_rice_yoy` | Region IV-A rice CPI YoY, a food CPI sub-index |
| `W_cereal_yoy` | Removed with the rest of family A1 |

**From SWS:**

| Column(s) | What it is |
|---|---|
| `H1`, `h_last`, `h_change`, `h_mean4`, `h_max4`, `h_margin`, `h_run` | Balance Luzon hunger outlook and readings |
| `NCR_*`, `VIS_*`, `MIN_*` | The other SWS areas' readings |
| `true_horizon` | Quarters since the newest SWS round |
| `NG_gap_price` | GDELT price-news share measured from the SWS fieldwork end date |

Also removed: the hunger-condition multiplier (P0H4's π_H) and S3's structural price offset, which is built from the food CPI projection.

## Inputs kept (10 of the 12 families, A1 and H1 removed)

| Column(s) | Family and source |
|---|---|
| `A2` | Headline (all-items) CPI, not food CPI |
| `A3` | PSA wholesale rice prices, a price survey, not the CPI |
| `V1` | Poverty and density |
| `C1`–`C4` | El Niño status, typhoons, rice and corn harvests, fisheries production |
| `E1` | Unemployment |
| `E2` | Remittances |
| `N1`, `G_pri_yoy` | FSSI-v3 news index; GDELT price-news share by calendar quarter |
| `W_rice_yoy`, `W_rice_mom`, `W_crude_yoy`, `W_urea_yoy` | World Bank prices |
| `lead` | The forecast lead |

## Arms

| Arm | Inputs |
|---|---|
| **V0 (primary)** | The kept inputs above |
| **V1 (sensitivity)** | V0 without `A2` and `W_crude_yoy`. Headline CPI enters the label's gap condition, so this arm checks whether the result depends on it. |

## Model and evaluation

The S3 recipe is reused unchanged except for the removed inputs and the removed offset:
- one LightGBM trained on T43c across all leads;
- balanced class weights;
- the S3 grid, chosen by inner walk-forward log-loss over the last 4 origins;
- training rows are labels known before the issue date;
- refitted at every issue date, on the same origins and rows as `FINAL_ARCHITECTURE/out/predictions.csv`.

The decision rule is **HIGH at 0.50.** Reliability uses the same criteria R1–R7 and the same later-block check (`run_one.report`). The maximum reliable lead is the number of consecutive passing leads starting from Lead 1.

**Comparators**, all on the same rows:
- P0H4 (served);
- S3;
- always-LOW;
- naive persistence;
- climatology.

The Brier difference against each is tested with a paired cluster bootstrap by target quarter.

**Pre-stated reading.** If V0 is not reliable at Lead 1, then a model that uses PSA food CPI and SWS only as validators has no reliable forecast horizon on 2021–2026 data. That will be reported as the result. There are no further tuning rounds after scoring.
