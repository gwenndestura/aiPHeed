# E152 protocol

One locked experiment, requested by the owner, after the E151 error diagnosis. **E151 and its D5 attempt stand unchanged. Nothing here reaches production or the dashboard unless every gate passes.**

## Status of evidence, stated first

* Every test row has been read by earlier work.
* **I also studied these rows' errors (`app/e151/diagnose.py`) before this design,** so the design is informed by the test rows. **This result is retrospective and weaker than E151's, and no result here can be called validated.**
* Only the sealed forecasts give blind evidence.

## What is held fixed

Target HFIAS moderate plus severe. HIGH at score >= 50, LOW below. Rounds 2018, 2019, 2021 at Lead 1, 72 rows. The score is not scaled, shifted or capped. All five groups stay as inputs. **Gates R1 to R9 of the E151 protocol apply as written, on the pool and on 2021.**

## What is new

1. **Local prices (PSA OpenSTAT, all provinces, monthly):** palay farmgate and wholesale rice, as year-on-year change, level relative to all provinces in that quarter, and farmgate against wholesale.
2. **Complete rainfall (NASA POWER, province centroids):** 3 and 6 month anomalies against 2000-2009.
3. **Regional means** of those inputs, and **since-survey means.**
4. **SWS change** in the province's area from the anchor quarter to the last reading published before the issue date.
5. **Regional drift:** the mean as-of Lead 1 error of provinces in the same region in released rounds newer than the province's own last survey, shrunk by n / (n + 3), added to the anchor. The 3 is fixed here and not tuned. **It cannot be learned from training rows, because earlier targets had no newer round.** It affects only 2021 and live forecasts.
6. **Weight on the LightGBM adjustment:** 1 or 0.5, chosen inside each round's training rows by cross-validation across regions, lowest soft Brier.

## Release assumption

A price or rainfall month is used only if at least 3 full months before the issue date. **Past PSA release dates are not held, so this delay is an assumption.** A shorter real delay would lose information. A longer one would be leakage, and that cannot be ruled out for every month.

## Data that was sought and not used

| Data | Why not |
|---|---|
| HDX CHIRPS rainfall, NDVI, WFP prices | The HDX download answered automated requests with an empty 202 response, which looks like bot protection, and it was not bypassed. The owner can download them by hand for later work |
| Fish wholesale prices | 76 % missing from 2016, excluded on coverage before scoring |
| Retail prices | End in 2021, so no live use |
| Provincial labour statistics 2018-2020 | Released January 2022, after all three test issue dates. Using them would be leakage |
| Regional labour series before 2021 | Not found in OpenSTAT at regional level |
| Per capita GRDP by region | Table seen ends 2016 |
| Family income by province | Tables seen carry no year, so they cannot be placed in time |

**So fix 2 of the plan (regional labour and income) is not achieved.** Regional means of prices and rainfall are the only new regional inputs.

## Arms, same rows

| Arm | Inputs | Drift |
|---|---|---|
| **E152, the model tested** | E151 required + new | Yes |
| no_drift | E151 required + new | No |
| no_new_inputs | E151 required | Yes |
| E151_inputs_cv | E151 required | No |

The other three are for attribution only and **cannot replace E152 afterwards.** Comparators: E151 required model and persistence, read from `prov_oof.csv`.

## One run

`app/e152/model.py` checks the hashes of itself, the panel code, the panel file and this protocol, and refuses a second run. A live forecast is sealed after the run. **No third attempt will be made on these rows, whatever the result.**

## Deviations

None yet.
