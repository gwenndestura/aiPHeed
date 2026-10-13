# Rule L Training-Readiness Report (2026-10-09)

**This audit was read-only.**

- **Not done:** no model was trained or run, no dataset was downloaded, no missing SWS value was retrieved, and nothing about September or December 2026 SWS results was searched for or opened. Production code and data, frozen forecasts, thesis chapters and the earlier reports are unchanged.
- **Nothing was committed or deployed.**

**New files:**

- `docs/READINESS_REPORT_2026-10-09.md` (this report)
- `docs/LABEL_DEFINITION_DECISION_NOTE_2026-10-09.md` (Task 2)
- `evidence/2026-10-09_readiness/cpi_final_month_release_dates.csv`
- `evidence/2026-10-09_readiness/sws_rounds_reconciliation.csv`
- `evidence/2026-10-09_readiness/eligibility_timeline_candidate_rule.csv`

It builds on `docs/RULE_L_FINAL_AND_PROTECTED_EVALUATION_PLAN_2026-10-09.md` and `evidence/2026-10-09_data_audit/`.

**Evidence classes:**

| Tag | Meaning |
|---|---|
| **[V]** | Original agency or SWS document, or its archived copy |
| **[N]** | PSA's own notice or release as quoted in the search index (the page itself is behind Cloudflare) |
| **[S]** | Dated news report |
| **[A]** | Assumption |
| **[U]** | Unverified |

No file-modification time, fetch date or reference month is used as a publication date.

**Access limitations:**

- psa.gov.ph and rsso04a.psa.gov.ph show Cloudflare bot checks; not bypassed.
- bsp.gov.ph and doe.gov.ph block programmatic access (recorded in the project's source notes).
- The Wayback CDX index was temporarily offline today.

---

## Verdict: **NOT READY**, close to **READY WITH DOCUMENTED LIMITATIONS**

No critical **leakage** risk remains in the data the project holds: every SWS round in the project now has a documented publication date, and every final-month national CPI release date is documented. **Three adviser decisions** are still needed before a leakage-free experiment can be defined:

1. **D1:** the provincial CPI publication date to use in Rule L.
2. **D2:** acceptance of current-vintage (revised) values.
3. **D3:** the label definition (Task 2).

Once these are decided, a **development** experiment on existing data can run as **READY WITH DOCUMENTED LIMITATIONS**. The **protected 2026 evaluation** also requires authorized data collection and the protection steps.

## Task 1: Publication dates

### 1.1 Final-month CPI for each label (`cpi_final_month_release_dates.csv`)

National CPI release dates are now documented for **all 20 needed months** (June 2021 to June 2026):

| Label quarter | Month | National release | Evidence |
|---|---|---|---|
| 2021-Q2 | Jun 2021 | 2021-07-06 | [N] PSA press release dated 06 Jul 2021; [S] ABS-CBN |
| 2021-Q3 | Sep 2021 | 2021-10-05 | [N] PSA press-conference notice; [S] ABS-CBN |
| 2021-Q4 | Dec 2021 | 2022-01-05 | [N] "Date of Release: 05 January 2022" |
| 2022-Q2 | Jun 2022 | 2022-07-05 | [S] ABS-CBN |
| 2022-Q3 | Sep 2022 | 2022-10-05 | [S] GMA, DZRH, DOF |
| 2022-Q4 | Dec 2022 | 2023-01-05 | [S] Inquirer, DZRH |
| 2023-Q1 | Mar 2023 | 2023-04-05 | [S] PNA, ABS-CBN |
| 2023-Q2 | Jun 2023 | 2023-07-05 | [S] DZRH |
| 2023-Q3 | Sep 2023 | 2023-10-05 | [N] PSA press-conference notice |
| 2023-Q4 | Dec 2023 | 2024-01-05 | [N] PSA press-conference notice |
| 2024-Q1 | Mar 2024 | 2024-04-05 | [S] DZRH, Manila Bulletin |
| 2024-Q2 | Jun 2024 | 2024-07-05 | [S] Manila Bulletin |
| 2024-Q3 | Sep 2024 | 2024-10-04 | [N] PSA notice; [S] Manila Times |
| 2024-Q4 | Dec 2024 | 2025-01-07 | [S] Philstar, DZRH |
| 2025-Q1 | Mar 2025 | 2025-04-04 | [S] Philstar, GMA, DZRH |
| 2025-Q2 | Jun 2025 | 2025-07-04 | [S] Philstar, ABS-CBN |
| 2025-Q3 | Sep 2025 | 2025-10-07 | [S] DZRH, FocusEconomics |
| 2025-Q4 | Dec 2025 | 2026-01-06 | [S] Tribune, Inquirer |
| 2026-Q1 | Mar 2026 | 2026-04-07 | [S] Manila Times via ICE; Trading Economics |
| 2026-Q2 | Jun 2026 | 2026-07-07 | [S] Trading Economics, FocusEconomics |

**Two findings that change how CPI enters Rule L:**

- **Provincial CPI is published later than national [N].** CALABARZON provincial CPI is released by **PSA RSSO IV-A at its own regional press conference**, which in the three cases found came **5–8 days after the national release**:
  - December 2024 provincial rates: 2025-01-13 (national 2025-01-07);
  - February 2025: 2025-03-10;
  - April 2025: 2025-05-13.

  The project's provincial values come from OpenStat `0012M4ACP23`. When OpenStat itself shows a new month is **[U]**. **Per-month provincial release dates remain unverified**, since the RSSO IV-A site is behind Cloudflare.
- **The base year changed in February 2022 [S].** PSA switched to the 2018=100 CPI with the January 2022 release on **2022-02-04** (ABS-CBN, "PSA shifts to 2018 as base year"). The 2018-base values the project uses for **2021 months** were therefore **not public before 2022-02-04**.

### 1.2 SWS rounds (`sws_rounds_reconciliation.csv`)

- **All 19 SWS rounds stored in the project from 2021 to 2025** have documented publication dates: 17 [V] on archived SWS pages or media-release files, and 2 [L] from SWS's own listing (November 2025), plus news.
- **The missing rounds' dates** are established in Section 3.

### 1.3 Other model inputs

These values come from quarter T−2 under strict timing, at least about 92 days before the forecast date.

| Feature | Source used by the project | Release practice documented | Evidence | Margin vs release lag | Point-in-time vintage? |
|---|---|---|---|---|---|
| Provincial food CPI (feature) | OpenStat `0012M4ACP23` | National around the 4th–7th of the next month; provincial at RSSO conference about 1 week later | Section 1.1 [S]/[N] | About 2.5 months spare | Current vintage. **2021 values are 2018-base, published 2022-02-04.** |
| Regional CPI | OpenStat `0012M4ACP22` | Same as national | Section 1.1 | Ample | Current vintage |
| Wholesale RMR | OpenStat `0052M4AWB01` | Monthly, "35 days after the reference month" (PSA dataset metadata via PhilRice data catalog [S]); March 2024 data reported 2024-04-16 [S] | [S] | Ample | Current vintage. Missing province-months: Laguna 2022-Q3, Quezon 2024-H1. |
| Unemployment (LFS, national) | OpenStat LFS | Monthly LFS since 2021; example: July 2024 results released 2024-09-06 (about 37 days) [N] | [N] | Ample | Current vintage (preliminary values revised) |
| OFW remittances | BSP, hand-curated quarterly | Around the 15th of the second month after the reference month; examples 2024-09-16, 2026-05-15, 2026-07-15, 2026-08-17, 2026-09-15 [S] | [S] | Ample | Current vintage |
| Diesel / gasoline | DOE Oil Industry Update, weekly, hand-curated | Weekly bulletins | Project source note; doe.gov.ph blocked | Ample | Curated values. 15 rows have no DOE price. |
| Brent | FRED `DCOILBRENTEU` (EIA) | Daily series | Project source note | Ample | Current vintage |
| FX | ECB reference rate via Frankfurter | Daily, same day | Project source note | Ample | Not revised |
| ENSO | NOAA CPC ONI | Monthly. "ONI values may change up to two months after the initial real-time value", and base periods update every 5 years; CPC now also publishes an ERSST v6 ONI [V: CPC ONI_v5 page] | [V] | Ample for availability | **Revised values; not point-in-time** |
| Typhoons (count, severe flag) | NOAA IBTrACS v04r01 best track | Updated about 3 times a week; recent storms are **provisional** and "may change after further analysis" [V: NCEI IBTrACS v4r01 page] | [V] | Ample for availability | **Final best-track values; not point-in-time** |
| Rainfall | NASA POWER PRECTOTCORR (monthly, plus daily endpoint after 2025-12-31) | MERRA-2 posted about 3 weeks after each month; near-real-time GEOS-IT within about 2 days, later replaced [S: NASA Earthdata/POWER docs] | [S] | Ample | **Revised values; not point-in-time** |
| Poverty incidence | PSA official poverty statistics | **2021 FY: 2022-08-15** [S: Inquirer, ABS-CBN 2022-08-15]. **2023 FY with provincial estimates: 2024-08-15** [N: PSA publication "2023 FY Official Poverty Statistics Publication_15August2024"]; the national preliminary 2024-07-22 had no provincial figures. | [S]/[N] | n/a (the vintage rule already applies) | Fixed releases |
| News (FSSI, triggers) | Project corpus | Article publication timestamps | [V] (`published` field) | Articles from quarter T−1 | n/a |
| SWS input | Section 1.2 | Per-round dates | [V]/[L] | n/a | Fixed releases |

**What this establishes:**

- **Every input family now has documented release practice** showing availability by the forecast date, with at least about 2 months to spare.
- **Exact per-observation dates remain unverified** for provincial CPI, rice, LFS and BSP. They rest on a documented release practice and calendar pattern (L3b), not on a per-value date.
- **ONI, IBTrACS and NASA POWER values are revised vintages**, and most other series are current vintages. That is a point-in-time limitation, not a leakage of future *outcomes*. Accepting it is **adviser decision D2**.

## Task 2: Label definition

See `docs/LABEL_DEFINITION_DECISION_NOTE_2026-10-09.md`. In summary:

- **Two-round quarters:** 2021-Q2 and 2022-Q2 average two rounds each.
- **2025-Q1:** uses only March, from **registered voters**, although January and February 2025 also exist.
- **Changing respondent base:** household heads to December 2024, registered voters January–April 2025, adults from the April 23–28, 2025 survey.
- **Missing labels:** 2025-Q2 and Q3 are unlabelled although their rounds exist.

Five options (A–E) are laid out without a recommendation (**adviser decision D3**).

## Task 3: Missing SWS rounds (`sws_rounds_reconciliation.csv`)

All sources compared: the fetcher's hand-curated table, `docs/provenance/sws_hunger_sources.json`, `data/processed/sws_hunger.parquet`, `data/processed/labels.parquet`, and earlier reports.

| Round (fieldwork) | Label quarter | Published | Evidence | In fetcher table / provenance / parquet / labels | Balance-Luzon value stored? |
|---|---|---|---|---|---|
| January 2025 (Stratbase-SWS) | 2025-Q1 | [U] (cited in the March 2025 release) | n/a | No / No / No / No | **No** |
| February 2025 (Stratbase-SWS) | 2025-Q1 | [U] | n/a | No / No / No / No | **No** |
| April 23–28, 2025 | 2025-Q2 | 2025-06-27 | [V] `ART-20250627174857` | No / No / No / No | **No** |
| June 2025 | 2025-Q2 | 2025-08-15 | [L] | No / No / No / No | **No** |
| September 24–30, 2025 | 2025-Q3 | 2025-11-05 | [L] | No / No / No / No | **No** |
| March 2026 | 2026-Q1 | 2026-05-12 | [V] `pr20260512` | Yes / Yes / No / No | **Yes: exposed outcome** |
| June 2026 | 2026-Q2 | [U] | n/a | Yes / Yes / No / No | **Yes: exposed outcome** |
| September / December 2026 | 2026-Q3/Q4 | Not examined | n/a | No | Not examined (**protected**) |

**Correction to earlier reports:**

- **The fetcher header's claim** that hunger releases were retrieved "from 2019-Q3 to 2025-Q1" omits January and February 2025.
- **Earlier statements that 2025-Q2/Q3 "have no SWS round" are wrong.** Those rounds exist; they were never collected.

These corrections are recorded here; earlier text is preserved.

## Task 4: Training readiness

### 4.1 Status of data

| Category | Items |
|---|---|
| **Verified and usable (dates documented)** | All 19 stored SWS rounds from 2021 to 2025, as labels and inputs. National CPI dates for all label months. News inputs. Poverty vintages (2022-08-15; 2024-08-15). |
| **Exists, but the date is unverified at the per-value level** | Provincial CPI (RSSO IV-A release about 1 week after national; per month [U]). Rice, LFS, BSP and DOE (documented practice, not per value). ONI, IBTrACS and NASA POWER (revised vintages). |
| **Missing** | SWS January, February, April, June and September 2025. 2026 provincial CPI (`psa_indicators` ends 2025-Q4). Rice for Laguna 2022-Q3 and Quezon 2024-H1. DOE for 15 rows. BSP for 15 rows. |
| **Exposed (not usable for blind evaluation)** | 2026-Q1 and Q2 SWS outcomes |
| **Protected** | 2026-Q3 and Q4 outcomes |

### 4.2 Eligible labels per forecast date (`eligibility_timeline_candidate_rule.csv`)

The timeline assumes a **candidate** for decision D1: a label is published on the later of (a) the last SWS round it uses and (b) the **national CPI release + 14 days**, a conservative cover for the about-1-week provincial lag. For **2021 labels**, it is additionally not before **2022-02-04** (the 2018-base publication).

Resulting label publication dates:

- 2021-Q2 and Q3: 2022-02-04.
- 2024-Q3: 2024-10-18; 2024-Q4: 2025-01-21.
- 2025-Q1: 2025-04-18.
- 2025-Q4: 2026-01-20.
- Others: their SWS date.

| Target (origin) | Eligible labels in the project (rows) | Eligible but missing from the project | Latest SWS round available as input | That round's status |
|---|---|---|---|---|
| 2022-Q2 (2022-04-01) | 3 (15) | none | 2021-Q4 | In project |
| 2023-Q3 (2023-07-01) | 7 (35) | none | 2023-Q1 | In project |
| 2023-Q4 | 8 (40) | none | 2023-Q2 | In project |
| 2024-Q1 | 9 (45) | none | 2023-Q3 | In project |
| 2024-Q2 | 10 (50) | none | 2023-Q4 | In project |
| 2024-Q3 | 11 (55) | none | 2024-Q1 | In project |
| 2024-Q4 | 12 (60) | none | 2024-Q2 | In project |
| 2025-Q1 | 13 (65) | none | 2024-Q3 | In project |
| 2025-Q2 | 14 (70) | none | 2025-Q1 | In project |
| 2025-Q3 | 15 (75) | none | 2025-Q2 (April 2025) | **Missing** |
| 2025-Q4 | 15 (75) | 2025-Q2 | 2025-Q2 (June 2025) | **Missing** |
| 2026-Q1 | 15 (75) | 2025-Q2, 2025-Q3 | 2025-Q3 | **Missing** |
| 2026-Q2 | 16 (80) | 2025-Q2, 2025-Q3 | 2025-Q4 | In project |
| 2026-Q3 (2026-07-01) | 16 (80) | 2025-Q2, Q3; plus **2026-Q1 (exposed)** | 2026-Q1 | In project (exposed) |
| 2026-Q4 (2026-10-01) | 16 (80) | Same | 2026-Q1; June 2026 date [U] | In project (exposed) |

**Effect on earlier origins (2021-Q4 and 2022-Q1):** these previously counted 1–2 labels as eligible. Under the 2018-base rule they have **none**, because no 2021 label was public in 2018-base form before 2022-02-04. This affects only early inner folds.

### 4.3 Is there enough data?

- **Development (walk-forward):**
  - Labelled targets 2023-Q3 to 2025-Q4 (8 quarters, 40 rows) have 7–15 eligible training quarters (35–75 rows), the same scale as earlier studies.
  - Two folds (2025-Q4 test; 2025-Q3 had no target) are **under-informed** until the 2025 rounds are collected.
  - This is enough for an **exploratory** chronological evaluation, which has already been reused (see earlier reports). It is not enough for a confident accuracy claim.
- **Protected 2026 evaluation:** still **feasible but not ready**. It needs:
  - 2026 provincial CPI (inputs and the 2026-Q1 training label);
  - the missing 2025 rounds;
  - the June 2026 round's publication date;
  - the protection steps.

  At most 10 rows (2 quarters) result, and they cannot establish true accuracy above 75%.

## Task 5: Go/No-Go

**NOT READY.** The smallest set of actions to reach **READY WITH DOCUMENTED LIMITATIONS**:

**Adviser decisions (no data needed):**

- **D1, provincial CPI timing in Rule L:** accept "national release + 14 days" (or another documented bound) as the provincial publication date, or require a per-month RSSO IV-A date.
- **D2, revised vintages:** accept current-vintage and revised values (ONI, IBTrACS, NASA POWER, LFS, BSP, CPI) as a documented point-in-time limitation, given that every input's release practice predates the forecast date by about 2 months or more.
- **D3, label definition** (decision note options A–E), including the 2025 respondent-population change.
- **D4, 2018-base rule:** confirm that 2021 labels and inputs count as published on 2022-02-04 (or accept 2012-base-era availability as equivalent).

**Additional source evidence (no download; manual or adviser-provided):**

- Per-month RSSO IV-A provincial CPI dates, if D1 requires them. The site is behind Cloudflare, so a person must read them.
- The January and February 2025 SWS release dates, if D3 includes those rounds.
- Confirmation of the [L] dates (June 2025, September 2025, November 2025) on the SWS pages themselves.

**Authorization to collect data (needed for the protected evaluation, and to repair the under-informed folds):**

- SWS Balance-Luzon values for April, June and September 2025 (dates known).
- 2026 provincial food CPI from OpenStat `0012M4ACP23`, January–June 2026.
- The June 2026 SWS publication date only (the value is already exposed).

**Protection actions (immediately, no authorization needed beyond agreement):** freeze the SWS outcome table at (2026, 2), and do not open or search September or December 2026 SWS results (plan in `RULE_L_FINAL_AND_PROTECTED_EVALUATION_PLAN_2026-10-09.md`, Section 5).

**Stopping here for your approval.** No data will be downloaded, no model trained, and no production or thesis change made without it.

---

### Sources (new in this report)

- **CPI national releases:**
  - 2021: [ABS-CBN 2021-07-06](https://www.abs-cbn.com/business/07/06/21/inflation-june-41-percent); [ABS-CBN 2021-10-05](https://www.abs-cbn.com/business/10/05/21/inflation-slows-to-48-percent-in-september); [PSA Dec 2021 release](https://psa.gov.ph/system/files/psd/1-1_Press%252520Release%252520on%252520CPI%252520for%252520All%252520Income%252520Households%252520for%252520Dec%2525202021%252520v2-protected_RRDH_APR-signed1.pdf)
  - 2022: [ABS-CBN 2022-07-05](https://news.abs-cbn.com/business/07/05/22/inflation-rises-again-hits-61-percent-in-june); [GMA Sep 2022](https://gmanetwork.com/news/money/economy/847017/inflation-sped-up-to-6-9-in-september-2022-psa/story); [DZRH Dec 2022](https://dzrh.com.ph/post/psa-december-inflation)
  - 2023: [ABS-CBN 2023-04-05](https://abs-cbn.com/business/04/05/23/inflation-cools-to-76-percent-in-march); [DZRH Jun 2023](https://dzrh.com.ph/post/inflation-declines-for-5th-consecutive-month-psa); [PSA Sep 2023 bottom-30% release](https://psa.gov.ph/system/files/psd/Special%20Release%20CPI%20for%20the%20Bottom%2030%25%20Income%20Households%20for%20September%202023.pdf); [PSA Dec 2023 press-conference notice](https://psa.gov.ph/system/files/psd/Press%20Conference%20December%202023%20Inflation_0.pdf)
  - 2024: [DZRH PSA tag (Mar 2024)](https://dzrh.com.ph/tag/psa); [Manila Bulletin 2024-07-05](https://balita.mb.com.ph/2024/07/05/ph-inflation-bumagal-sa-37-nitong-hunyo-psa/); [PSA Sep 2024 press-conference notice](https://psa.gov.ph/content/press-conference-september-2024-inflation); [Philstar 2025-01-07](https://www.philstar.com/business/2025/01/07/2412479/inflation-hits-29-december-ends-2024-32)
  - 2025–2026: [Philstar 2025-04-04](https://www.philstar.com/business/2025/04/04/2433478/inflation-eases-18-march-2025/amp/); [Philstar 2025-07-04](https://www.philstar.com/business/2025/07/04/2455487/philippines-june-inflation-rises-slightly-14-food-prices-easing); [DZRH Sep 2025](https://www.dzrh.com.ph/post/ph-inflation-rises-to-17percent-in-september-2025-psa); [Tribune 2026-01-06](https://tribune.net.ph/2026/01/06/phl-inflation-averages-17-in-2025-below-target); [Trading Economics Mar 2026](https://tradingeconomics.com/philippines/inflation-cpi/news/539462); [Trading Economics Jun 2026](https://tradingeconomics.com/philippines/inflation-cpi/news/564621)
- **2018 rebasing:** [ABS-CBN 2022-02-04](https://news.abs-cbn.com/business/02/04/22/january-inflation-at-3-percent-psa-shifts-to-2018-as-base-year)
- **RSSO IV-A provincial releases:** [April 2025 press-conference notice](https://rsso04a.psa.gov.ph/sites/default/files/attachment-dir/2025-0400-PR17%20April%202025%20Inflation%20Report%20Press%20Con.pdf); [RSSO IV-A releases list](https://rsso04a.psa.gov.ph/all-releases?page=5) (search-index excerpts; site behind Cloudflare)
- **Poverty:** [ABS-CBN 2022-08-15](https://news.abs-cbn.com/business/08/15/22/1999-million-filipinos-poor-in-2021-as-poverty-incidence-rises-psa); [PSA 2023 FY publication, 15 Aug 2024](https://psa.gov.ph/sites/default/files/phdsd/2023%20FY%20Official%20Poverty%20Statistics%20Publication_15August2024.pdf)
- **Wholesale rice:** [PhilRice Ricelytics data catalog (PSA metadata)](https://ricelytics.philrice.gov.ph/data_catalog/dataset/1d55580a-ac85-47ba-9f7a-10196e5c2f57); [BusinessMirror 2024-04-16](https://www.pressreader.com/philippines/businessmirror/20240416/281694029820883)
- **LFS:** [PSA monthly LFS press release](https://psa.gov.ph/sites/default/files/iesd/2022-12/3_Press%2520Release%2520on%2520monthly%2520LFS_signed.pdf)
- **BSP remittances:** [Tribune 2026-07-15](https://tribune.net.ph/2026/07/15/remittances-slump-to-12-month-low-in-may); [Tribune 2026-08-17](https://tribune.net.ph/2026/08/17/bsp-remittances-reach-half-year-high-in-june); [PNA](https://alpha.pna.gov.ph/articles/1233439)
- **ONI revisions:** [CPC ONI v5 page](https://www.cpc.ncep.noaa.gov/products/analysis_monitoring/ensostuff/ONI_v5.php)
- **IBTrACS provisional data:** [NCEI IBTrACS v4r01](https://www.ncei.noaa.gov/node/1660); [NCEI update notice](https://www.ncei.noaa.gov/news/tropical-cyclone-database-updated-twice-weekly)
- **NASA POWER / MERRA-2 latency:** [POWER data sources](https://power.larc.nasa.gov/docs/methodology/data/sources/); [NASA Earthdata MERRA-2](https://www.earthdata.nasa.gov/data/projects/merra-2)
- **SWS rounds:** archived SWS pages and listings as cited in `evidence/2026-10-09_data_audit/sws_round_publication_dates_v2.csv`
