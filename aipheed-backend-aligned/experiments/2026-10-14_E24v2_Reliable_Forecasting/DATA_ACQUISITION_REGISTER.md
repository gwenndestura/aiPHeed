# Data acquisition register (E24v2)

**Status values:**

| Status | Meaning |
|---|---|
| ACQUIRED (E24v2) | Fetched in this experiment from an official public source; years ≤ 2025 only; raw response, query, hash and retrieval time stored |
| AUTHORIZED | On the hash-pinned allowlist used since E17/E18 |
| PUBLIC – BLOCKED | Published, but the site returns HTTP 403 to non-browser requests (never bypassed) |
| PUBLIC – NOT OPENED | Published, but opening it here risks exposing protected 2026 outcomes |
| PROTECTED / PENDING | Protected, or not yet published |
| UNAVAILABLE | Not published at the needed geography |

**Authorization basis for ACQUIRED rows:**

- they are official public statistics;
- they fall within Chapter I §1.7's data scope ("publicly available data from PSA …");
- they are outside every protected category (2026 outcomes, 2026 news, restricted survey rounds);
- no year ≥ 2026 was requested, and the script asserts this on every response.

**Please confirm this basis** (checklist A6).

## Acquired in E24v2 (`acquisition/ACQUISITION_MANIFEST.json`)

| Data | Source (PSA OpenSTAT PXWeb API) | Coverage | Rows | Use | Validation |
|---|---|---|---|---|---|
| Provincial CPI, 2018=100, **back-cast** (All items, 01.1 Food, Rice) | `DB/2M/PI/CPI/2018NEW/0012M4ACP28.px` | 1994-01 to 2017-12; Batangas, Cavite, Laguna, Quezon (excl. Lucena), Rizal | 4,320 | D history 1995–2017 (back-cast test, D model training) | Same 2018 base and geographic codes as the current table. The 2018 YoY values join the two tables. PSA's published provincial YoY starts in 2019, so **the join itself cannot be checked against a published rate**. Gate (ii) checks 2019–2020 instead. |
| Provincial CPI, 2018=100 | `0012M4ACP22.px` | 2018-01 to 2020-12; 2021–2025 (comparability check only) | 540 + 900 | D 2018–2020; gate (i) | Gate (i): index-derived D vs the approved E12 D for 2021–2025, max \|ΔD\| = **0.039 pp**, sign agreement **100%** |
| Published provincial YoY | `0012M4ACP23.px` | 2019–2020 | 360 | Gate (ii) only | Median \|Δ\| = 0.023 pp (max 0.050) |
| Subsistence incidence among population, with SE, CV and CI | `DB/1F/FY/0081F3DF04A.px` | 2018, 2021, 2023; region, 5 provinces, Lucena | 162 | Measured provincial food-poverty anchor (descriptive; dashboard) | Official precision measures shown |
| Poverty incidence among population, with SE, CV and CI | `DB/1F/FY/0041F3DF02A.px` | same | 162 | as above | as above |

## Prioritized register of what would improve the forecasts

| P | Variable (geography) | Years needed | Source & access | Status | Contribution | History adequate? |
|---|---|---|---|---|---|---|
| **1** | **SWS involuntary hunger, Balance Luzon, every round with fieldwork and publication dates** | **1998–2020** | SWS Social Weather Reports (sws.org.ph) | **PUBLIC – NOT OPENED.** SWS pages can display the protected 2026 rounds. **You** can download the historical table or the releases in a browser and supply a CSV restricted to ≤ 2020 (format in `runner/run_bx_t1.py`). | **The only near-term route to evidence that the approved composite forecast generalizes (C9)**, through the pre-registered T1 back-cast (amendment A2). It also gives the H model ~90 rounds instead of 20. | Yes: about 80 quarters, combined with the D back-cast that is already acquired |
| **2** | 2026-Q3 onward outcomes: Sept/Dec 2026 SWS rounds, July–December 2026 provincial CPI | 2026-Q3+ | SWS; PSA OpenSTAT | PROTECTED | Scores the **two blind prospective seals** already made (`runs/SEAL_*`); C9 needs ≥ 8 scored origins | Accumulates one origin per quarter |
| **3** | **Municipal poverty incidence, PSA 2021 SAE** (with SE/CV) | 2021 (2023 if released) | psa.gov.ph/statistics/poverty-sae/stat-tables, `2018 - 2021 SAE_with PSGC_noHUC.xlsx` | **PUBLIC – BLOCKED** (HTTP 403 from Cloudflare on 2026-10-14; not bypassed). Not on OpenSTAT, which holds province and HUC tables only. | Replaces the density-only order for 126 LGUs (Objective 3, H4). `runner/lgu_rankings_v2.py --sae` and `backend_dev/app/quarterly/lgu_poverty.py` are ready and tested. | Static weight |
| **4** | Exact provincial CPI release dates (RSSO IV-A) | 1995–2026 | rsso04a.psa.gov.ph | PUBLIC – NOT ACQUIRED (Cloudflare) | Replaces the +14-day proxy behind Dnow's timing. **The current proxy is conservative.** | n/a |
| **5** | Publication dates of the March and June 2026 SWS rounds | 2026 | SWS releases | PUBLIC – NOT OPENED | With verified dates, the 2026-Q1/Q2 rounds could enter the H model at the 2026-07-01 origin. They are excluded for now (conservative). | n/a |
| **6** | Provincial food-insecurity outcome (FIES moderate+severe by province) | any | DOST-FNRI NNS microdata request; PSA CBMS; a DA/LGU FIES module | UNAVAILABLE as published tables | **The only way to validate provincial *food-insecurity* claims.** The current label's provincial part is relative food inflation. | 1–2 points per province; validation only |
| **7** | Regional leading indicators for H (rice retail prices, regional LFS unemployment, typhoon damage) | 1998–2025 | PSA OpenSTAT, PAGASA, NDRRMC | Public, acquirable | **Only useful once item 1 exists**, because testing whether they anticipate hunger needs the long SWS series. Not acquired, to avoid fitting candidates that cannot be tested. | Yes, with item 1 |
| — | 2026 news (any quarter) | 2026 | Project corpus | PROTECTED | Display context only. The E24v2 forecaster does not use news (no measured predictive value). | — |

## What you need to do (in order)

1. **SWS history (item 1).**
   1. Prepare a CSV with columns `quarter,H,published,source`, with every round 1998-Q1…2020-Q4 and no later row.
   2. Hash it and add it to an authorization JSON.
   3. Run `python -B runner/run_bx_t1.py --sws <csv> --authorization <json>`.
2. **PSA SAE workbook (item 3).** Download it in a browser, then run `python -B runner/lgu_rankings_v2.py --sae "<path>" --sae-year 2021`.
3. **When 2026-Q3/Q4 outcomes are authorized (item 2).** Run `python -B runner/score_prospective.py --outcomes <csv> --authorization <json>`.
