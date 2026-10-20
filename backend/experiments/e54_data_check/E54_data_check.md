# E54 data check: provincial employment, fish-kill incidents, OFW by province or region

This is a data availability check only. No model was trained, and `backend/app`, `backend/data` and `frontend` are untouched.

- **When:** checked on 2026-10-16 from this machine (scripted HTTP plus web search).
- **Raw downloads:** saved under `raw/<name>/body`, with every request and its HTTP status in `probe_log.tsv`.
- **Scripts:** `scripts/` (`probe.sh` fetches; `list_openstat.py`, `px_meta.py` and `grep_html.py` read the saved files).

**How to read "Source".** "Primary (downloaded)" means the file in `raw/` came from the agency. "Secondary" means the figure was seen only in a news report or a web-search summary of an agency page that returned 403 here. Secondary figures are listed as leads, not as data.

## Access summary

| Site | Status here |
|---|---|
| PSA OpenStat API (openstat.psa.gov.ph) | **200** (works) |
| psa.gov.ph (LFS pages, provincial labor market releases, SOF release PDF, SOF statistical tables) | **403** for every URL tried |
| PSA RSSO IV-A (rsso04a.psa.gov.ph) | **403** |
| BSP (bsp.gov.ph) | **403** |
| foi.gov.ph (PSA OFW-by-LGU request), cpbrd.congress.gov.ph (OFW profile PDF) | **403** |
| BFAR national (bfar.da.gov.ph) | 200; its site search for "fish kill" returns a results page with **no posts** |
| BFAR Region IV-A (region4a.bfar.da.gov.ph) | **no response** (connection failed, http and https) |
| DA (da.gov.ph) | 200 |
| DMW (dmw.gov.ph, /statistics) | 200, but a script-rendered shell with no statistics in the HTML; not verifiable without a browser |

## 1. Provincial unemployment or underemployment

| Item | Finding |
|---|---|
| **Available** | **Partial**: annual only, and only through pages blocked here |
| PSA OpenStat | **No.** All 20 tables in the LFS folder (`DB/1B/LFS`, updated 2026-10-07) are national: their variables are Year × Month × Rate × Sex, with no region or province dimension (`raw/px_lfs_rates_2026`). The search hits for "unemployment" and "province labor force" are national or older (2006–2016). Three listed tables return 404. |
| PSA annual provincial releases | They exist: "2023 / 2024 / 2025 Annual Provincial Labor Market Statistics" ([2025](https://psa.gov.ph/content/2025-annual-provincial-labor-market-statistics-preliminary-results), [2024](https://psa.gov.ph/statistics/labor-force-survey/node/1684077703), [2023](https://psa.gov.ph/statistics/labor-force-survey/node/1684065368)) and RSSO IV-A ["2023 CALABARZON Labor Market Statistics"](https://rsso04a.psa.gov.ph/content/2023-calabarzon-labor-market-statistics-preliminary-results). **All returned 403**, so their tables could not be downloaded. |
| Frequency | **Annual** (preliminary, later final). No quarterly provincial series was found. |
| Years | 2022, 2023, 2024, 2025p are referenced. A 2021 provincial release was not found (the 2021 RSSO release gives the regional rate only). **2026: none** (the annual 2026 figure would be released around March 2027). |
| Values seen (secondary) | **2022:** region 6.4%, Rizal 7.2, Batangas 6.7, Laguna 6.1; Cavite and Quezon not seen. **2023:** Rizal 7.0, Batangas 5.5, Cavite 5.1. **2024:** region 5.6% (highest of all regions). **2025p:** region 5.8% ([BusinessWorld, 2026-03-23](https://bworldonline.com/the-nation/2026/03/23/738165/calabarzon-posts-highest-unemployment-rate-in-2025/), downloaded). Provincial 2024/2025 values were not seen. |
| Release timing | The annual figure for year Y appears around **March of Y+1** (2025p: reported 2026-03-23). This is the only release date seen; the others are unverified. |
| Lag to F−2 without leakage | Yes, but only as "the latest annual figure released before origin F". That is year Y−1 or Y−2 for data quarter F−2 in year Y, a **15–27-month lag**. It cannot vary within a year. |

## 2. Fish-kill incidents in CALABARZON (province × date)

| Item | Finding |
|---|---|
| **Available** | **No** structured incident series |
| BFAR national | No fish-kill bulletin series. The site search returns no posts (`raw/bfar_search_fishkill`). |
| BFAR Region IV-A | The site did not respond. |
| DA / BFAR statements (primary, downloaded) | One event is documented: [DA-BFAR statement, 4 June 2019](https://www.da.gov.ph/da-bfars-official-statement-on-the-fish-kill-in-taal-lake/), Agoncillo, Batangas (Taal Lake), reported May 29. Low dissolved oxygen hit 121 of 6,000 cages. **This is before the 2021 window.** |
| Incidents in 2021–2026 seen (secondary, news) | Only July 2026, Pililla, Rizal (Laguna de Bay): dead fish July 21, PCG and BFAR inspection July 22, cause preliminary ([Inquirer](https://newsinfo.inquirer.net/2268922/pcg-bfar-probe-fish-kill-in-pililla-waters)). The searches mostly surfaced pre-2021 events (Taal 2011, 2019; Laguna de Bay 2012, 2020; Sampaloc Lake, date not confirmed). |
| Frequency and coverage | Event-based and incomplete. There is **no way to tell "no incident" from "not reported"** for a province-quarter. |
| Lag to F−2 | Possible for any dated event, but there is no complete, auditable list to lag. |

## 3. OFW remittances or counts by province or region

| Item | Finding |
|---|---|
| **Available** | **Partial: regional, annual; no provincial data** |
| BSP | Cash remittances are national, monthly, **by country of source**, with no breakdown by region or province of the recipient. The site returns **403**. |
| PSA OpenStat | Only national tables up to 2015 (`DB/3E/GD/MI/0093E3D0910`, OFW counts 2000–2015, `raw/px_ofw_2000_2015`; average remittance per OFW 2000–2015). |
| PSA Survey on Overseas Filipinos (SOF) | Annual (reference April–September). **Regional share of OFWs**: CALABARZON 19.0% (2023), **20.5% (2024)** ([Philstar on the PSA release, downloaded](https://www.philstar.com/business/2025/12/19/2495253/ofws-rise-219-million-2024-psa)), 16.7% (2025 preliminary, secondary). The PSA's [statistical tables](https://psa.gov.ph/statistics/survey/labor-and-employment/survey-overseas-filipinos/stat-tables) and the [2024 special release PDF](https://psa.gov.ph/system/files/iesd/SOF-2024-Special-Release.pdf) returned **403**. Remittances are reported nationally (₱262.2 bn in 2024); **no regional remittance split was found**. |
| SOF release timing | Year Y is released around **December of Y+1** (2024: December 2025). |
| DMW | Not verifiable (script-rendered page). Its published deployment statistics are generally by destination and occupation, not by province of origin; that is **unverified** here. |
| PSA OFWs by city/municipality | An FOI request page exists ([foi.gov.ph](https://www.foi.gov.ph/agencies/psa/migration-ofws-employment-bpos-hospitals-atmsbanks-building-permits-data-by-citymunicipality-2010-to-2025/)) but returned **403**. Whether data was released through it is unknown. |
| Lag to F−2 | Regional annual shares can be lagged (latest SOF released before origin F, i.e. year Y−2 at most dates). They are the same for all five provinces. |

## Summary

| Need | Available | Level | Frequency | Through 2026-Q2? | Downloadable here | Usable without leakage |
|---|---|---|---|---|---|---|
| Provincial unemployment | **Partial** | province | annual | no (latest 2025p) | **no (403)** | yes, lagged 15–27 months |
| Fish-kill incidents | **No** | (event) | event-based, incomplete | – | – | no auditable series |
| OFW by province or region | **Partial** (regional count share only) | region | annual | no (2025 preliminary) | **no (403)** | yes, but identical for all provinces |

## Recommendation (stopping here)

**No E54 experiment is worth running with what can be obtained now.**
- **Fish kill:** there is no auditable series, so there is nothing to test.
- **OFW:** the only sub-national data is one regional share per year. It is the same for all five provinces and adds nothing beyond the national input E53 already has.
- **Provincial unemployment:** this is the only candidate with real provincial variation. But it is annual, lagged 15–27 months, and covers about 4 years (2022–2025p). That gives the model at most 3–4 distinct values per province, essentially a fixed provincial offset. And it cannot be downloaded here (403).

**What E54 would need from you.** Manually download PSA's "Annual Provincial Labor Market Statistics" tables (unemployment and underemployment by province, 2021/2022–2025p, with each release date) from psa.gov.ph or RSSO IV-A in a browser, into `backend/experiments/e54_data_check/manual/`. Then an E54 could be run as follows.

**Input**
- `cond_employment_prov` = the E53 national employment rank × (province rate ÷ CALABARZON rate). The ratio comes from the latest annual release dated before origin F, so there is no leakage.
- It replaces E53's national-only `cond_employment`. Everything else is identical to E53-A1: the walk-forward, the grid, C2 shrinkage, and no forcing.

**Adoption rule (fixed now, before any data)**
- E54 is acceptable only if it is **non-inferior to E53-A1** on the same 65 rows:
  - balanced accuracy ≥ 0.83
  - AUC ≥ 0.84
  - Brier ≤ 0.16
  - LOW caught ≥ 10/12
- Otherwise E53-A1 stays the preview candidate. No further tuning.
- **Reported but not part of the rule:** whether the Employment share differs across provinces at Q4 2026. That is the reason to run E54 at all.
