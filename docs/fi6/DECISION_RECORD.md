# FI6 decision record (written before the FI6 evaluation was run)

## 1. Outcome sources considered

| Candidate | Direct FI measure? | Observed or modelled | CALABARZON | Province | Frequency | Usable obs. | Consistent definition | Sampling error known | Verdict |
|---|---|---|---|---|---|---|---|---|---|
| SWS involuntary hunger | yes (experience of going hungry, ≈ severe end of FIES) | observed survey | via Balance Luzon area | no | quarterly (gaps) | 98 labelled quarters, 1999–2026 | question unchanged; respondent base and mode changes in 2020–21 disclosed | yes (published ±3–6 pp) | **selected** |
| DOST-FNRI ENNS/NNS FIES | yes (FIES) | observed survey | yes | only 2018–19 pooled (some provinces), 2021 (Batangas, Cavite, Lucena) | irregular | ≤ 3 per province | yes | yes | too few points to forecast; validation reference only |
| FAO FIES / PoU (FAOSTAT) | FIES yes / PoU modelled | FIES survey (national) / PoU modelled | no | no | annual, 3-year averages | ~10 national | yes | yes | national only; cannot represent CALABARZON quarters |
| WFP HungerMap LIVE (FCS/rCSI) | consumption/coping | nowcast model where survey data are missing | modelled | no | daily | — | — | — | modelled, not ground truth (Martini et al. 2022) |
| WFP FCS / rCSI surveys | yes | observed | no regular CALABARZON series | no | ad hoc | — | — | — | not available |
| IPC classifications | yes (phase) | expert convergence of evidence | not produced for CALABARZON quarters | — | — | 0 | — | — | not available; no labels fabricated |
| PSA FIES (Family Income and Expenditure) | no (income/expenditure; no FI items) | observed | yes | yes | triennial | 3 | — | yes | vulnerability input, not outcome |
| PSA APIS hunger item | yes | observed | region | no | about annual (July) | few, microdata on request | — | yes | not obtainable in this work; listed as data request |

## 2. Target constructions compared (SWS Balance Luzon, evaluated quarters 2010–2026, n = 62)

`app.fi6.target.candidates()`. P(flip) is the probability that sampling error alone puts a quarter on the wrong
side of the threshold.

| Target | HIGH share | Mean P(flip) | Labels with P(flip) > 0.2 | Oracle ceiling |
|---|---|---|---|---|
| FI5: above five-year average | 0.45 | 0.142 | 34 % | 0.86 |
| **FI6: above five-year average by more than the margin of error** | 0.18 | **0.067** | **11 %** | 0.93 |
| above five-year average by more than 1 SE | 0.27 | 0.110 | 24 % | 0.89 |
| absolute ≥ 20 % of families | 0.21 | 0.074 | 13 % | 0.93 |
| absolute ≥ 15 % | 0.45 | 0.160 | 35 % | 0.84 |
| rise vs previous reading | 0.48 | 0.178 | 43 % | 0.82 |

**Decision:** HIGH = hunger significantly above normal. The threshold is not tuned. It is the survey's own published
95 % margin, which is the standard SWS and other survey producers use to call a change real. Its meaning is the same
"worse than normal" early-warning idea as FEWS NET's five-year-average comparisons, minus the part that sampling
error alone could produce.

**Rejected:**
* The absolute 20 % line has similar reliability, but no framework anchors that number to the SWS question. The IPC
  20 % rule applies to Household Hunger Scale phases, which this question does not measure.
* "Rise vs previous reading" is the noisiest candidate.
* The 1-SE threshold keeps a quarter of the labels unreliable.

**What it does not claim:** it is not a provincial or municipal measurement, not undernourishment, and not poverty.

**Cost of the choice:** HIGH is rare (11 of 62 evaluated quarters, 16 of 98 overall). A classifier trained on about
10 positives would memorise them. The proposed LightGBM therefore forecasts the **continuous change in hunger**,
using all 98 quarters' information, and turns it into P(HIGH) with its out-of-sample error spread. This is the same
continuous-then-threshold logic that FEWS NET projections and the v13 forensic audit both favour.

## 3. Indicators (each one has to earn its place)

| Feature | Domain | Link to food insecurity | Source | Level | Freq. | From | Release lag used | Expected sign | Decision |
|---|---|---|---|---|---|---|---|---|---|
| hunger_last, its anomaly, its age | outcome history | hunger persists | SWS | Balance Luzon | quarterly | 1998 | published date | 0 / − (mean reversion) / 0 | include |
| food CPI YoY | market | access: food affordability | PSA CPI | Region IV-A | monthly | 1995 | +10 d | + | include |
| rice CPI YoY | market | staple affordability | PSA CPI | Region IV-A | monthly | 1995 | +10 d | + | include |
| palay production YoY | market | availability | PSA | Region IV-A | quarterly | 1988 | +45 d | − | include |
| food − all-items, food acceleration | market | derived from the CPI series above | PSA | — | — | — | — | — | **exclude** (redundant) |
| rainfall anomaly (3 m) | climate | crop and access shocks; sign depends on flood vs drought | NASA POWER | 5-province mean | monthly | 1982 | +30 d | 0 | include |
| storms within 200 km (quarter) | climate | typhoon damage | IBTrACS | CALABARZON | event | 1884 | real time | + | include |
| storms last 4 quarters | climate | overlaps the quarter count and the latest hunger reading | IBTrACS | — | — | — | — | — | **exclude** |
| ONI | climate | El Niño drought risk; lag uncertain | NOAA | Niño 3.4 | monthly | 1950 | +10 d | 0 | include |
| Tmax anomaly | climate | no established quarterly link in the reviewed studies | NASA | — | — | — | — | — | **exclude** |
| unemployment rate, YoY change | employment | income loss | PSA LFS | Philippines (no regional series before 2021) | quarterly/monthly | 2005 | +45 d | + | include; national level disclosed |
| remittances YoY | remittance | household income support | BSP via WB WDI | Philippines | annual | 1991 | 15 Feb | − | include; national level disclosed |
| poverty incidence | poverty | vulnerability (not FI itself) | PSA | Region IV-A | triennial | 2006 | Y+2 / documented | + | include **with + constraint**: FI5 showed an unconstrained model reading the record-low 2025 poverty rate as raising risk |
| news_market | market news | shortage / supply / food-price stress news | GDELT 2017+, FSSI 2021+ | PH / CALABARZON | quarterly | 2017 | quarter end | + | include |
| news_climate | climate news | weather damage stress | FSSI | CALABARZON | quarterly | 2021 | quarter end | + | include |
| news_employment | employment news | job-loss news | GDELT 2017+, FSSI | — | quarterly | 2017 | quarter end | + | include |
| news_remittance | remittance news | OFW/remittance stress | FSSI | — | quarterly | 2021 | quarter end | + | include (thin: 83 relevant headlines) |
| news_poverty | poverty news | aid-need and hardship news, actual hunger reports | GDELT 2017+, FSSI | — | quarterly | 2017 | quarter end | + | include |
| BERTopic topic shares | — | coverage volume, not direction | corpus | — | — | 2021 | — | — | **not a model input**; kept as Objective 1 output |
| population density | poverty | exposure | POPCEN | LGU | static | 2024 | — | — | LGU ranking only (no time variation) |

## 4. News integration: is the idea valid?

Putting news inside the domain it describes is sound. It keeps the explanatory structure interpretable, and it is
how Balashankar et al. (2023) used news (as signals of specific drivers, not as one sentiment score). It is only
useful if three conditions hold:
* the news arrives before the official statistic;
* it covers the period being forecast;
* it is not just a repeat of the official release.

**Risks here:**
* Local news covers only 2021+ and was collected retrospectively.
* Two-thirds of headlines have no province.
* Many headlines restate PSA/DA releases.

**Mitigations:**
* Event deduplication.
* Per-domain composites.
* Monotone + constraints.
* A ±0 test: full vs government-only vs news-only vs minus each news domain, on identical origins.

News stays in the final model only as a stated supplementary signal unless that test shows a gain.

## 5. Reliability rules (unchanged from FI5, fixed before the run)

A lead is reliable only if all of these hold:
* accuracy ≥ 0.75;
* recall ≥ 0.50 and precision ≥ 0.50 (so "always LOW", which scores 0.82 here, cannot pass);
* AUC ≥ 0.70;
* Brier skill > 0 vs climatology;
* accuracy ≥ 0.60 in every era.

The furthest reliable lead is the largest L for which every lead from 1 to L passes.
