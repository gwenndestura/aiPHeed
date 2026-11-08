# E157: root causes, data feasibility, and what can be fixed

Starts from E156 (`3ae914e4`). No model was retrained, no production code or dashboard was changed. Diagnostics use the same 72 Lead-1 rows, which have been read before.

## Summary

| Category | Items |
|---|---|
| **Fixed or settled** | Cause of the two 100 %-missing inputs found; anchor bias measured (it runs high, not low); every news category tested one at a time; excluded survey rows audited; public sources located for regional labour, OFW and remittance history |
| **Tested, did not work** | Dropping or isolating any news category (no gain); city survey rows as extra training data (no usable history); E152 to E156 changes (prices, rainfall, regional drift, tuning, calibration) |
| **Blocked by data** | Provincial employment and remittance history before 2018 does not exist publicly. Regional series exist but **PSA and BSP refuse automated downloads** (HTTP 403), so they need a manual download or the in-app browser, with your permission |
| **Not claimable** | 75 % at Lead 1. A demonstrably improved candidate needs new information; tuning on these rows would be overfitting |

## 1. Employment and remittances

**Why two inputs are 100 % missing in training**

| Input | Source on disk | Coverage | First usable issue quarter | Training targets end |
|---|---|---|---|---|
| `unemp_region` | `data/pfi/raw/psa_sdg_unemployment_region.csv` | Annual 2021 to 2025 | 2022-Q2 | 2021 |
| `remit_q_yoy` | `CORRECTED_PIPELINE/out/remittances_quarterly_corrected.csv` | Quarterly from 2021-Q1 | 2022-Q3 | 2021 |

So both were built only from 2021 onward, and no training row can use them. The remaining employment and remittance inputs are national, with 14 distinct values in training, all explained by the issue quarter.

**Public historical sources found**

| Data | Geography | Coverage | Frequency | Status |
|---|---|---|---|---|
| PSA Labor Force Survey, regional tables | 17 regions | From 2005 rounds; method change April 2016 | Quarterly rounds | In release spreadsheets and the Regional Social and Economic Trends tables; **psa.gov.ph returns 403 to scripts** |
| PSA OpenSTAT LFS (`1B/LFS`) | National | April 2005 to 2026 | Quarterly | Accessible, national only |
| PSA Survey on Overseas Filipinos | 17 regions | Annual tables from 2012 (regional OFW distribution) | Annual | Release spreadsheets; **403 to scripts** |
| BSP cash remittances | National, by source country | Monthly from 1989 | Monthly | **bsp.gov.ph returns 403 to scripts** |
| PSA FIES family income | Region, province, HUC | Survey years (2015, 2018, 2021, 2023) | Triennial | OpenSTAT tables seen carry no year; release reports needed |
| Provincial labour statistics | Province | 2018 to 2020 (released 2022) and 2021 onward | Annual | **Leak** for past tests; usable live only |

**What can make these groups meaningful**

* **Employment:** regional quarterly unemployment and underemployment from LFS rounds, 2013 to 2021. That gives 17 regional values per quarter instead of one national value. It is a direct measurement at regional scope, not provincial, and must be labelled so.
* **Remittances:** each region's OFW share (SOF) multiplied by national remittance growth (BSP) is a **regional exposure proxy**, varying by region and over time. It is a proxy, not a measurement, and must be tested before use.
* **No provincial history for either exists publicly.** That limitation stays in the thesis.

## 2. Survey anchor

| Lead 1, mean error in points (forecast minus survey) | 2018 | 2019 | 2021 | All | Calibration slope |
|---|---|---|---|---|---|
| Anchor alone | +8.7 | +6.8 | +5.9 | **+7.1** | 0.94 |
| E151 (anchor + LightGBM) | +4.7 | +5.1 | −0.2 | **+3.1** | 0.79 |
| Old survey (persistence) | +10.2 | +5.6 | +12.9 | **+9.5** | 0.71 |

* **The anchor runs too high, not too low,** in every test round, because food insecurity fell between surveys. LightGBM removes most of that bias. The live forecasts sitting below the latest surveys follow the same pattern, so they are not evidence of a downward bias.
* **Overconfidence is real:** slope 0.79. The E156 calibration candidate fixed it, but lost accuracy and Brier.
* **Uncertainty does not grow with survey age** in the fitted model (variance per quarter = 0 at the live fit). This should be fixed for the report's ranges, not for accuracy.
* **Hierarchical alternatives** (Fay-Herriot, state-space) were tested in E151 and scored lower.

## 3. Additional survey observations

46 FNRI Heat Map rows in 2018, 2019 and 2021 are not in the model.

| Reason | Rows |
|---|---|
| Highly urbanised and other cities, with no 2013 or 2015 HFIAS history in the data held, and no city-level inputs | 37 |
| New or split provinces with no earlier history (Davao Occidental, Dinagat Islands, Samar, Batanes) | 4 |
| Headline-only rows with no moderate-or-severe figure (2019: Camarines Sur, Cebu, Davao Oriental, Pampanga, Zamboanga del Sur) | 5 |

**None can be added legitimately** without inventing a history or using province inputs as if they were city measurements. FNRI's 2023 NNS uses FIES, which is a different instrument; it is not pooled.

## 4. NLP

| Lead 1, news removed | Correct of 72 | Brier |
|---|---|---|
| Full model | 52 | 0.1375 |
| All news removed | 53 | 0.1374 |
| Without market news | 52 | 0.1386 |
| Without climate news | 51 | 0.1374 |
| Without employment news | 51 | 0.1378 |
| Without remittance news | 51 | 0.1379 |
| Without poverty news | 51 | 0.1376 |
| Without response news | 51 | 0.1374 |
| Without hunger and net stress | 50 | 0.1395 |
| Without topic shares | 51 | 0.1381 |
| Without province sentences | 51 | 0.1372 |

Every change is within one or two rows and 0.002 Brier, which is noise at about 46 effective rows. **No news category carries measurable information beyond official data.** The cause is not processing: labels agree 69 %, timing is enforced, duplicates are removed. It is thin provincial coverage (2 to 4 stories per quarter), overlap with monthly CPI, and too few labelled outcomes. News does lead quarterly labour and farm data during shocks (E155).

## 5. Maximum reliable lead

Unchanged from E156: **0.** Lead 1 fails C1 (accuracy not clearly above always-LOW at about 46 effective rows) and C4 (overconfidence).

## 6. Recommended changes

1. **Disclose and remove the two 100 %-missing inputs from the reported input list,** or rebuild them from historical sources (step 3).
2. **Make interval width grow with survey age,** so ranges are honest for stale provinces.
3. **Add regional employment and a regional remittance exposure proxy** from LFS, SOF and BSP history, then run **one locked experiment (E158)**: E151 with and without them.
4. Keep news in the model as required, and report its role as early warning, not accuracy.

## 7. Implementation plan for E158

1. Obtain, with your permission: LFS regional tables for 2013 to 2021 rounds; SOF regional OFW distribution for 2012 to 2021; BSP monthly cash remittances from 2010. Record each file's source, date and checksum.
2. Build regional quarterly unemployment, underemployment and labour-force participation, each usable about 6 weeks after its round. Build the exposure proxy as region OFW share (previous year's SOF) × national remittance growth (BSP, previous quarter).
3. Unit-test the release dates: no value used before its publication.
4. Write the protocol and hash it. One run, Lead 1 to 8, same rows, same reliability criteria as E156.
5. Adopt only if Lead-1 Brier improves with a 95 % interval below 0 and accuracy does not fall.

## 8. Is 75 % at Lead 1 attainable?

* **Effective sample:** about 46 independent rows. For the lower end of a 95 % interval to clear always-LOW (65.3 %), observed accuracy needs to be about **78 %**, six more correct rows than now.
* **Gap:** 72.2 % now. Every change tried in E151 to E156 moved it by at most two rows, and the shuffled-input test shows inputs add about one row beyond a level correction.
* **Room:** survey noise allows about 95 %, and perfect regional knowledge about 92 %, so the ceiling is not the limit. **The limit is information that separates provinces within a round.**
* **Verdict:** 75 % at Lead 1 is **not realistically attainable with the data now held.** Regional labour and remittance history is the most promising addition, but it varies by region, not province, so a gain of six rows is unlikely. It is worth one locked test. A new provincial HFIAS round would matter most, and none exists after 2021.
