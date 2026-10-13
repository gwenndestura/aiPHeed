# Data Completeness Audit: Monthly CPI and Wholesale Rice (2026-10-09)

**This audit was read-only.**

- **Not touched:** no dataset, fetcher, production file, frozen forecast, thesis chapter or methodology was modified. No data values were downloaded. Nothing was committed or deployed.
- **The only external requests** were HTTP GETs for **table metadata** (dimension lists and table titles) from the PSA OpenStat PXWeb API, plus one attempt to open psa.gov.ph.
- **Saved:** the metadata response, as `evidence/2026-10-09_data_audit/openstat_metadata_snapshot_2026-10-09.json` (SHA-256 `1bb12d06…`).

Every statement below is tagged:

- **[V]** verified from a file or the metadata;
- **[A]** an assumption;
- **[U]** unresolved.

---

## 1. Existing project data

| Search | Result |
|---|---|
| All `.parquet` and `.csv` files under `backend/`, `aipheed-backend-aligned/`, `aipheed-lean/` and `Claude outputs/` (189 data files), checked for a price/CPI column **and** a month-like column | **0 files** [V] |
| `backend/data/raw/psa/` | Empty [V] |
| `aipheed.db` (both copies) | Only application tables (forecasts, SHAP, alerts, users); no price data [V] |
| `data/supplementary/`, `data/reference/` | No monthly price series. `_price_commodities.csv` and `_price_crosswalk.json` are commodity mappings [V]. |

**How the existing fetchers discard the monthly values:**

| Fetcher | What it queries | What it stores |
|---|---|---|
| `openstat_fetcher.py` | Monthly provincial food CPI from `0012M4ACP22` / `0012M4ACP23` | Quarterly means in `psa_indicators.parquet`; no fetch timestamp column [V] |
| `psa_rice_fetcher.py` | Monthly provincial wholesale RMR from `0052M4AWB01` | Quarterly means in `psa_rice_prices.parquet` (l.187–193) [V] |
| `cpi_full_fetcher.py` | Table `0012M4ACP22`, but **Region IV-A only** | Its source note says "Region IV-A inherited to provinces" [V] |

The provincial CPI the model and label use comes from `0012M4ACP23` through `openstat_fetcher` [V].

**Conclusion: no monthly observations exist anywhere in the project.** The monthly values were fetched in the past but aggregated before storage, so they are not recoverable from what is stored.

## 2. The proposed official sources (metadata only)

Endpoint pattern: `https://openstat.psa.gov.ph/PXWeb/api/v1/en/<table path>`. GET returned HTTP 200 for all three tables on 2026-10-09.

| Item | `0012M4ACP22` (CPI index) | `0012M4ACP23` (CPI YoY %) | `0052M4AWB01` (wholesale cereals) |
|---|---|---|---|
| Path | `DB/2M/PI/CPI/2018NEW/0012M4ACP22.px` | `DB/2M/PI/CPI/2018NEW/0012M4ACP23.px` | `DB/2M/NWSNEW/0052M4AWB01.px` |
| Title [V] | "Consumer Price Index for All Income Households by Commodity Group (2018=100): January 2018 – September 2026" | "Year-on-Year Changes of the Consumer Price Index in Percent by Commodity Group (2018=100): January 2019 – September 2026" | "Cereals: Wholesale Selling Prices of Agricultural Commodities" |
| Folder "updated" timestamp [V] | 2026-10-06 09:22 | 2026-10-06 09:22 | 2026-10-07 08:51 |
| Years [V] | 2018–2026 | 2019–2026 | 2010–2026 |
| Periods [V] | Jan–Dec + "Ave" | Jan–Dec + "Ave" | January–December + "Annual" |
| Five provinces present [V] | Yes: codes 33 Batangas, 34 Cavite, 35 Laguna, 36 Quezon, 37 Rizal; region at 32. These match `openstat_fetcher.CALABARZON_OPENSTAT`. | Yes, same codes | Yes: 28 Batangas, 29 Cavite, 30 Laguna, 31 Quezon, 32 Rizal; region at 27. `psa_rice_fetcher` matches by name. |
| Required category [V] | `2` = "01.1 – FOOD" (the series behind the label); also "01 – Food and non-alcoholic beverages", "01.1.1.12 – Rice" | Same | "Regular Milled Rice (RMR)"; also "Well Milled Rice (WMR)" |
| Geography note [V] | **"City of Lucena (Capital)" is listed separately (code 38).** The "Quezon" series very likely excludes Lucena [A]. The label is built from the same "Quezon" series, so the definitions are internally consistent. | Same | No separate Lucena |
| Last month available | September 2026 (title) [V] | September 2026 (title) [V] | **[U]**: the title gives no end month. The stored quarterly file reaches 2026-Q3 (fetched 2026-09-09), so at least one 2026-Q3 month exists [V]. |
| Missing or suppressed cells | **[U]**: cell completeness cannot be seen in metadata | **[U]** | **Known gaps [V]:** `psa_rice_prices.parquet` has **no value at all** for Laguna 2022-Q3, Quezon 2024-Q1 and Quezon 2024-Q2, so every month of those quarters was suppressed or empty. Partial-month gaps in other quarters are **[U]**. |
| Classification changes over time | **[U]**: a PX table shows only its current structure | **[U]** | **[U]** |
| Observation vs estimate; revisions | **[A]** CPI cells are compiled index values (the "observations"); PSA rarely revises published CPI except at rebasing. Earlier vintages cannot be seen in OpenStat. | Same | **[A]** Surveyed wholesale prices; revision practice unknown **[U]** |
| Publication date per observation | **Not in the table [V].** The only timing evidence is the 2026-10-06 update, consistent with September 2026 being released about 6 days after month-end. | Same | **Not in the table [V].** The 2026-10-07 update suggests a monthly cadence; which month it added is **[U]**. |

**Historical release dates could not be checked automatically.**

- psa.gov.ph returned **HTTP 403** to automated requests.
- In the built-in browser it showed a **bot-verification (Cloudflare) page**, which I did not attempt to bypass.
- The CPI release calendar (Summary Inflation Reports) and the wholesale-price release dates are therefore **[U]**. They need to be read by a person, or obtained from PSA's Advance Release Calendar.

## 3. Completeness report

Window: January 2021 to the latest month available, and only the 5 provinces. Under window rule W, nothing before January 2021 enters, including through lags or rolling windows.

### `0012M4ACP23`: provincial CPI year-on-year % (01.1 Food)

| Audit item | Finding |
|---|---|
| Expected coverage | 69 months (2021-01 to 2026-09) × 5 provinces = **345 values** |
| Actual coverage | Table covers the range and provinces [V]. Values verifiably in the project: **0 monthly**; 100 quarterly means for 2021–2025 with no missing values [V]. |
| Missing observations | Monthly: all 345 missing from the project [V]. In the source: unknown [U]. |
| Duplicates | None in the stored quarterly data [V]. Monthly: n/a. |
| Data quality | Units are % YoY [V]. The Lucena / Quezon definition is noted. No invalid values in the stored quarterly means [V]. |
| Publication timing | Not in the source. One data point (Sept 2026 → about 6 Oct 2026). The history is unverified [U]. |
| Project overlap | Quarterly means 2020-Q1 to 2025-Q4 in `psa_indicators`. No 2026 values [V]. |
| Usable leakage-free? | **Only with a verified per-month release date, or an approved conservative availability rule** (Section 4) |

### `0012M4ACP22`: provincial CPI index (2018=100)

| Audit item | Finding |
|---|---|
| Expected coverage | 69 × 5 = 345 values (01.1 Food) |
| Actual coverage | Table covers the range and provinces [V]. Province values in the project: **0 monthly** [V]. `cpi_full` holds the **region only**, quarterly to 2026-Q2 [V]. |
| Missing, duplicates, quality | As ACP23. Index units are 2018=100 [V]. |
| Publication timing | Same as ACP23 [U] |
| Need | **Not required.** The pre-registered monthly CPI features (latest-month YoY, 2-month change, province minus five-province mean) come from ACP23 alone. ACP22 would only add month-on-month index change. |

### `0052M4AWB01`: wholesale Regular Milled Rice, PHP/kg

| Audit item | Finding |
|---|---|
| Expected coverage | 2021-01 to the latest 2026 month (at least about 67 months; exact end [U]) × 5 provinces = **about 335–345 values** |
| Actual coverage | Table covers 2010–2026, all 5 provinces, and RMR [V]. Values in the project: **0 monthly**; 112 of 115 quarterly means, 2021-Q1 to 2026-Q3 [V]. |
| Missing observations | **At least 9 province-months [V]:** Laguna 2022-07/08/09, and Quezon 2024-01 to 2024-06. Partial gaps elsewhere [U]. |
| Duplicates | 0 in the quarterly data [V] |
| Data quality | Prices 29.0–49.9 PHP/kg, none ≤ 0 [V]. Wholesale, not retail. A retail-to-wholesale break exists only against 2020 data, which is excluded by W. |
| Publication timing | Not in the source; history unverified [U] |
| Project overlap | Quarterly means only |
| Usable leakage-free? | Same condition as CPI. The Quezon 2024 gap falls in the outer test period, so it must stay **missing**, not interpolated. |

## 4. Can the experiment be run?

| Question | Answer |
|---|---|
| Monthly observations expected vs available now | About 690 needed (345 CPI YoY + about 345 RMR); **0 available in the project** |
| Five-province coverage 2021–2026 | CPI: full per metadata (cell-level [U]). Rice: gaps for Laguna 2022-Q3 and Quezon 2024-H1 [V]; others [U]. |
| Usable without post-forecast information? | **Not yet.** No source table records release dates. Two options: **(a)** a per-month release-date ledger read by a person from PSA's release pages; or **(b)** a conservative availability rule approved in advance. For example, "a month is usable for quarter T only if it ended at least 45 days before T starts", which admits month 1 of quarter t but not months 2–3. Option (b) gives up some of the benefit but needs no release dates. |
| Missing months without unsupported interpolation | Yes. Leave missing; the existing in-fold handling (LightGBM native NaN; in-fold median imputation with missing indicators) applies. No interpolation across the Quezon 2024 gap. |
| Fair comparison with the quarterly model and baselines | Yes, once data exist. Same 40 outer rows, rule L, and the B1–B4 candidates and baselines pre-registered in `PREREGISTRATION_v4.json` |
| Data through 2026 | CPI through September 2026 [V]; rice at least into 2026-Q3 [V]. Provincial CPI for 2026 would also allow the 2026-Q3/Q4 forecasts once SWS labels exist. **No 2026 SWS round is in the project**, so no 2026 labels [V]. |
| Window rule W | Respected by fetching only 2021-01 onward. ACP23's 2021 YoY values are published 2021 statistics, allowed under the v3 reference-base note. |

**Expected benefit (from earlier evidence, not an assumption about the new data).**

- **The province term isn't the bottleneck.** In the window study, an oracle that knew the *true* next-quarter province CPI term but only the released SWS reached just **65%**. An oracle with the true next-quarter SWS reached **82.5%** (`experiments/2026-10-09_window2021/results.json → diagnostics`).
- **So monthly CPI mainly improves the province term, which is not what limits accuracy.** It could help only if fresher food inflation helps predict the regional SWS jump.
- **The earlier attempt with quarterly CPI didn't help:** the N2 nowcast was worse than the latest released SWS.

Monthly data are therefore **unlikely by themselves to lift accuracy to 75%**. They may improve within-quarter province ranking.

## 5. News: the 46 retained articles without a province

The geocoder assigned 6 of the 46 (`experiments/2026-10-09_origin_info/news_regeocode_candidates.csv`). I checked each against its text:

| Article (quarter) | Assigned to | Text evidence | Verdict |
|---|---|---|---|
| USTR … Greenhills (2023-Q2) | San Juan, Batangas | "Greenhills Shopping Center in **San Juan City**" | **False**: San Juan City is in Metro Manila |
| Mayors, MMDA … market prices (2023-Q1) | San Juan, Batangas | "MMDA … Metro Manila Council … the **San Juan city government**" | **False**: Metro Manila |
| Food security … quarantine (2021-Q1) | Lopez, Quezon | "Trade Secretary Ramon **Lopez**" | **False**: surname |
| DSWD: giving cash … (2024-Q1) | Lopez, Quezon | "Assistant Secretary … Romel **Lopez**" | **False**: surname |
| 33 grocery items (2022-Q1) | Lopez, Quezon | "Trade Secretary Ramon M. **Lopez**" | **False**: surname |
| Calatagan artist mural (2026-Q2) | Calatagan, Batangas | "**Calatagan** artist …" | Geography **correct**; topic is art, not food insecurity |

**Root causes** in `app/ml/corpus/location_geocoder.py`:

1. **`lopez` is in neither `_NATIONALLY_AMBIGUOUS_LGU` nor `_LGU_SURNAME_OR_WORD`.** Because Lopez is unique within Region IV-A, `_resolve_lgu` step 1 accepts it on any mention.
2. **`san juan` is in the ambiguous set, but "city" counts as a locality cue.** In `_cue_province` the cue is `_LOCALITY_KW`, which includes `city`. "San Juan **City**" therefore corroborates San Juan, Batangas, which the gazetteer lists as a **municipality** (`lgu_type`). Metro Manila cues are also absent from `_OTHER_LOC`.

**Minimal correction (tested in memory only; no code or data changed):**

- add `"lopez"` to `_LGU_SURNAME_OR_WORD`;
- in `_cue_province`, do not let "city / cities / lungsod" immediately after the name corroborate an LGU whose gazetteer `lgu_type` is `municipality`.

**Simulated effect:**

- All 5 false matches are removed and the correct Calatagan location is kept.
- Re-geocoding 400 of the 484 existing LGU-tagged corpus rows changed **0** tags because of the fix. One pre-existing difference, "All Home …" stored as Bacoor and re-geocoded as Antipolo, occurs with or without the fix.

**The conclusion on news coverage stands:** no genuine CALABARZON food-insecurity articles are recoverable from the 46. Applying the fix is a code change to the pipeline and needs your approval.

## 6. Findings and approval gate

### Source-by-source summary

| Source | Finding | Basis |
|---|---|---|
| `0012M4ACP23` (provincial CPI YoY) | **UNVERIFIED** | The table exists, is accessible, and covers 2021-01 to 2026-09 for all 5 provinces with the required category [V]. **0 monthly values in the project.** Cell completeness and **per-month publication dates** are not established. |
| `0012M4ACP22` (provincial CPI index) | **UNVERIFIED** (and **not required**) | Same as ACP23. The pre-registered features do not need it. |
| `0052M4AWB01` (provincial wholesale RMR) | **INCOMPLETE** for the outer test period, and **UNVERIFIED** for timing | At least 9 province-months are missing in the source [V]: Laguna 2022-07 to 09 and Quezon 2024-01 to 06. The Quezon gap overlaps outer test quarters 2024-Q2 and Q3. The end month and release dates are [U]. The gaps can be left as missing, so they reduce rather than block the experiment. |

### Exact missing data

| Item | Gap |
|---|---|
| Monthly values in the project | All of them: about 345 CPI YoY + about 345 RMR cells |
| Rice cells known to be absent at the source | Laguna 2022-07, 2022-08, 2022-09; Quezon 2024-01 to 2024-06 |
| Release dates | All about 69 CPI release dates (2021-01 to 2026-09) and all wholesale-rice release dates |
| Labels | Every 2026 SWS round (prospective labels) |

### Access and publication-date limits

- OpenStat metadata is accessible.
- psa.gov.ph blocks automated access with a bot check. Release dates must be collected by a person, or replaced by an approved conservative availability rule.

### Is the experiment ready without downloading?

**No.** The project holds no monthly observations.

### Smallest additional collection

1. **`0012M4ACP23`:** commodity `2` (01.1 Food); geography codes 33–37; 2021-01 to 2026-09. **345 values.**
2. **`0052M4AWB01`:** Regular Milled Rice; geography codes 28–32; 2021-01 to the latest month. **At most about 345 values.**
3. **Availability timing**, either:
   - **(a)** a release-date ledger read by hand from PSA's Summary Inflation Reports and wholesale-price releases (about 69 + about 69 dates); or
   - **(b)** adviser approval of a conservative rule (for example, a month is usable only if it ended at least 45 days before the forecast quarter starts).

Both downloads are small (well under 1 MB). Store them unaggregated, with `fetched_at`, under a new `data/supplementary/monthly_origin/`; no existing file is touched.

### Recommendation

**Downloading is justified only as a small, low-cost test, and only after the timing question is settled.** Without (a) or (b) the monthly features cannot be used without risking leakage.

- **Set expectations:** earlier oracle results suggest monthly CPI and rice will mainly sharpen province ranking. They are unlikely to raise overall accuracy to 75%, which is limited by the regional SWS lag.
- **Recommended order:**
  1. Decide (a) or (b).
  2. Approve items 1 and 2 (ACP22 not needed).
  3. Run the pre-registered Stage B under rule L.

**Stopping here, as you asked.** No download and no new experiment will start without your explicit approval.
