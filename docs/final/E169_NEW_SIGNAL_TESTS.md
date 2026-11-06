# E169: Tests of the two new-signal routes (2026-11-06)

**Requested:** test (A) a national FIES anchor for the round shift, and (B) provincial food prices.

**Rules applied:**
- Inputs are as-of only: published on or before each forecast origin.
- No gate is changed and no model is refitted on test rows.
- Production is untouched (E158).

## Timing: why the error sits in two rounds
Lead-1 forecast origins are 2 quarters before the survey quarter. HFIAS rounds become usable 6 quarters after fieldwork (`ANCHOR_LAG`).

| Test round | Survey quarter | Lead-1 origin | Newest HFIAS visible at origin | Mean error (E168) |
|---|---|---|---|---|
| ENNS 2018 (22 rows) | 2018-Q3 | 2018-Q1 | **2015 round** (2.5 years old) | **+6.8 points** |
| ENNS 2019 (25 rows) | 2019-Q3 | 2019-Q1 | **2015 round** (3.5 years old) | **+3.9 points** |
| ENNS 2021 (25 rows) | 2021-Q3 | 2021-Q1 | 2018 and 2019 rounds | −1.3 points |

**Every test province's own anchor is the 2015 round** (gap 12, 16 or 24 quarters).
- When a newer national HFIAS reading is visible (2021), the round shift almost disappears.
- When it isn't (2018, 2019), the model has to guess a 3–4-year national change with no HFIAS-type measurement in between.
- **That missing in-between measurement is the round-shift error found in E169-A.**

## A. National FIES as the in-between measurement: NOT USABLE
| Source | Philippine series | Available at the 2018-Q1 and 2019-Q1 origins? |
|---|---|---|
| PSA OpenSTAT SDG 2.1.2 (FNRI) | 2019 44.2, 2021 33.4, 2023 31.4 | **No.** It starts with the 2019 survey |
| FAO via World Bank `SN.ITK.MSFI.ZS` (current vintage, `data/e169/raw/`) | 2018 41.2, 2019 42.7, 2020 40.1, 2021 37.4, 2022 33.2; **null before 2018** | **No.** Its first value is 2018 |

- **For the two rounds that carry the error, no FIES value existed before the origin.** There is nothing to test.
- **For 2021:** the values visible at origin (2018 → 2019: 41.2 → 42.7) **rose**, while provincial HFIAS **fell**. That is the same wrong direction as SWS (`sws_shift_signal.json`). The 2021 round also needs no correction (−1.3 points).
- Running LightGBM with a feature that is empty at 2 of 3 origins cannot change the result, so no model run was made.

## B. Provincial food prices: ALREADY IN THE MODEL (correction to the roadmap)
E168 already uses every PSA provincial price series in the repo:

| Series | Coverage | E168 columns |
|---|---|---|
| PSA CPI food and rice, by province (2012 and 2018 bases, monthly, as-of 2-month lag) | 143 provinces and cities | `cpi_food_yoy`, `cpi_rice_yoy`, `cpi_food_3m`, `cpi_food_accel`, `cpi_food_rel_nat`, `cpi_since` |
| PSA farmgate palay, by province | about 86 % of provinces | `l_fg_yoy`, `l_fg_rel`, `r_fg_yoy` |
| PSA wholesale rice, by province | about 63 % of provinces | `l_rice_yoy`, `l_rice_rel`, `l_terms` |

The roadmap's claim that "market inputs are national/regional" was wrong.
- **The market inputs are provincial.** Shuffling them across provinces does not hurt (E168).
- So the provincial price differences carry no forecast information for HFIAS. Market helps only through its **timing** (national price waves).
- The PSA retail-price-by-province table would duplicate the provincial rice CPI.

## Conclusion
- **Both routes are closed.** Neither adds information the model lacks.
- **The remaining error is structural:** for 2018 and 2019, no public measurement of household food insecurity existed between the 2015 round and the forecast date.
- **No input can supply it, and LightGBM tuning cannot either.**
- **What would make the model reliable:** HFIAS outcomes it has never seen (ENNS 2022 or later provincial rounds), scored against the sealed forecasts. With one more round, the forecasts would also start from a recent anchor, the situation in which the model was already well calibrated (2021: −1.3 points).
