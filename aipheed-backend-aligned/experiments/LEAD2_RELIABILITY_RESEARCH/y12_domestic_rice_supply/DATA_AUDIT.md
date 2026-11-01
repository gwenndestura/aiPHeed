# Y12 data audit: domestic rice supply and provincial CPI

**Acquired:** 2026-10-29, between 12:48:53Z and 12:49:09Z.

**Source:** PSA OpenSTAT PXWeb API, `https://openstat.psa.gov.ph/PXWeb/api/v1/en/DB/`. Queries were made with `runner/acquire.py`, parsed with `runner/tidy.py` and checked with `runner/audit_checks.py`.

**Provenance:** every raw response is saved as served in `data_acquired/`. `data_acquired/manifest.json` gives each file's API path, the exact POST query, the UTC fetch time and its SHA-256.

## 1. Series obtained

| # | Series | OpenSTAT table | File (SHA-256 prefix) | Coverage obtained | Frequency, geography | Missing |
|---|---|---|---|---|---|---|
| 1 | **Rice stocks inventory** by sector: total, household, commercial, NFA | 2E/CS/0032E4ECNV0 "Rice and Corn: Monthly Total Stocks Inventory by Sector" | `stocks_national_monthly.csv` (aaa6073c) | 1980-01 .. 2026-09 | Monthly; **national only**. Stock as of the 1st of the month. | None |
| 1b | Rice stocks by region | 2E/CS/0048E4ECNV1 | `stocks_regional_monthly.csv` (f887eb3c) | **2026 only** (Jan–Sep) | Monthly; regions incl. IV-A | **No regional history**, so it cannot be used |
| 2 | **Farmgate palay**, old series (fancy and other variety) | 2M/FG/0032M4AFP01 | `farmgate_palay_old.csv` (d4bda7b2) | 1990-01 .. 2020-12 | Monthly; PH, IV-A, 5 provinces | Other variety: Batangas 367/372 months, Cavite 370, Laguna 362, Quezon 344, **Rizal 226**. Fancy is mostly absent. |
| 2b | **Farmgate palay**, new series | 2M/NFG/0032M4AFN01 | `farmgate_palay_new.csv` (db8642d6) | 2010-01 .. 2026-09 | Monthly; PH, IV-A, 5 provinces | Other variety: 197–201 of 201 months |
| | Old vs new, 2010–2020 overlap | – | – | 1,014 province-months | – | Mean abs. difference ₱0.14/kg, r = 0.991. Spliced: old ≤ 2009-12, new ≥ 2010-01. |
| 3 | **Provincial CPI YoY, 2012 = 100**: all items, food, rice | 2M/PI/CPI/2012/0012M4ACPI6 (1995–2011) and 0012M4ACPI2 (2012–2021) | `cpi2012_yoy_1995_2011.csv` (f06a943a), `cpi2012_yoy_2012_2021.csv` (fca48969) | 1995-01 .. 2021-12 | Monthly; PH, IV-A, Cavite, Laguna, Quezon, Rizal, Batangas | None (324/324 months each) |
| 3b | Provincial CPI index, 2012 = 100 | 0012M4ACPI4, 0012M4ACPI1 | `cpi2012_idx_*` (22e0b79f, 3e3bf564) | 1994-01 .. 2021-12 | Monthly | Downloaded; not used by the models |
| 4 | **Rice imports**, gross kilo, all countries | 2L/IMT/PMG/0022L4DNDM0 "Imports by Major Type of Goods", group "Rice" | `imports_rice_monthly_2015_2026.csv` (3b1465d2) | **2015-01 .. 2026-08** | Monthly; national | Not used in models (section 3) |

**Province codes.** The project's codes are not in PSGC order: PH040100000 = Cavite, PH040200000 = Laguna, PH040300000 = Quezon, PH040400000 = Rizal, PH040500000 = Batangas (backend mapping). `tidy.py` uses this mapping. The first parse used PSGC-style codes and matched nothing; it was caught by the overlap check and corrected before the plan was frozen.

## 2. Publication dates and revisions

| Series | Verified release dates (source) | Lag from reference to release | Pre-2021 dates |
|---|---|---|---|
| Rice stocks inventory | PSA releases found by search: <br>Jun 2022 → 27 Jul 2022 <br>Jan 2023 → **3 Apr 2023** <br>Aug 2023 → 17 Oct 2023 <br>Dec 2023 → 19 Jan 2024 <br>Apr 2024 → 8 May 2024 <br>May 2024 → 14 Jun 2024 <br>Mar 2026 → 1 Apr 2026 <br>May 2026 → 3 Jun 2026 <br>Jul 2026 → 4 Aug 2026 | 31–92 days after the reference date (1st of the month) | **Not verified.** psa.gov.ph returns HTTP 403 to scripted and fetch access; the Internet Archive returned 429 and was not reachable. Older release pages exist (e.g. "Rice and Corn Stocks Inventory, November 2003"), but their dates could not be read. |
| Farmgate palay | September 2026 tables → 13 Oct 2026; December 2023 → 24 Jan 2024 (PSA farmgate page) | About 13–24 days after month end | **Not verified** (same obstacle) |
| Provincial CPI | PSA monthly CPI release, about the 5th of the next month (the project's E41 rule) | About 5 days | The 2012-based series was introduced with the 2012 rebasing. **1994–2011 values are PSA backcasts**, and 2012–2017 values come from the rebased series, not the vintages published at the time. |
| Rice imports | Not checked (not used in models) | – | – |

**How the plan handles unverified dates.** No historical release date was invented. The plan uses availability **bounds** that are longer than the longest verified lag:

- **Stocks:** the stock date must be at least 4 months before the issue (verified maximum 92 days).
- **Farmgate:** the reference month must have ended at least 2 months before the issue (verified maximum about 24 days).

A mandatory sensitivity run adds 3 more months to each. The result is labelled as resting on these bounds.

**Revisions.** OpenSTAT serves one current vintage only. Stocks and farmgate figures are revised at later releases, so the downloaded values may differ from the first published values. This is not quantifiable with the data available.

## 3. Series not obtainable, or not usable

| Requested | Obstacle |
|---|---|
| NFA and commercial stocks by **region or province** before 2026 | The regional table contains 2026 only. The national series was used. |
| **Rice import arrivals / shipment timing** before 2015 | OpenSTAT monthly commodity-level import tables (gross kilo by commodity and country, 1991–2026) do not publish their commodity-code list in the API metadata. Wildcard queries return one unrelated code (e.g. 20060000014). The only monthly series with an explicit "Rice" line starts in 2015, which gives about 18 development quarters before 2021: too short. BOC/BPI arrival data (shipments, import permits) was not found as a public historical series. |
| Rice imports 2015–2026 | Obtained, but excluded from the models by the plan. |
| Real-time vintages of CPI, stocks and farmgate | Not published by PSA in a downloadable form. |

## 4. Checks done before freezing the plan (no forecasting)

**2012-based vs official 2018-based provincial price condition, 2021 overlap** (`out/audit_checks.json`):

| Province | Food YoY mean abs. difference (pts) | Gap mean abs. difference | Condition agreement |
|---|---|---|---|
| Cavite | 2.58 | 1.88 | 2/4 |
| Laguna | 1.93 | 1.88 | 2/4 |
| Quezon | 1.28 | 0.66 | 3/4 |
| Rizal | 1.38 | 0.81 | 3/4 |
| Batangas | 1.86 | 1.03 | 4/4 |

**The 2012-based condition is an analogue of the official one, not a copy of it: 14/20 agree.** Development results describe this analogue. Transfer to the official condition is uncertain even before any forecasting question arises.

**Price-condition prevalence (2012-based):**

| Province | 1995–2001 | 2002–2011 (backcast) | 2012–2020 |
|---|---|---|---|
| Cavite | 0.46 | 0.42 | 0.50 |
| Laguna | 0.43 | 0.55 | 0.56 |
| Quezon | 0.39 | 0.80 | 0.64 |
| Rizal | 0.43 | 0.40 | 0.33 |
| Batangas | 0.39 | 0.60 | 0.36 |

## 5. Sources

- PSA OpenSTAT API: https://openstat.psa.gov.ph/PXWeb/api/v1/en/DB/ (tables listed above)
- [PSA Rice and Corn Stocks Inventory (listing)](https://psa.gov.ph/statistics/crops/rice-corn-stocks-inventory)
- [June 2022](https://psa.gov.ph/content/rice-and-corn-stocks-inventory-june-2022)
- [January 2023](https://psa.gov.ph/content/rice-and-corn-stocks-inventory-january-2023)
- [August 2023](https://psa.gov.ph/statistics/crops/rice-corn-stocks-inventory/node/1684061354)
- [December 2023 (via Public)](https://www.publicnow.com/view/A4B7291DA6E7EFFA66231D462AC2A6A81733A4D2)
- [April 2024](https://psa.gov.ph/content/rice-and-corn-stocks-inventory-april-2024)
- [May 2024](https://psa.gov.ph/content/rice-and-corn-stocks-inventory-may-2024)
- [March 2026](https://psa.gov.ph/content/rice-and-corn-stocks-inventory-march-2026)
- [May 2026](https://psa.gov.ph/content/rice-and-corn-stocks-inventory-may-2026)
- [July 2026](https://psa.gov.ph/content/rice-and-corn-stocks-inventory-july-2026)
- [PSA Farmgate Prices of Palay](https://psa.gov.ph/farmgate-prices-palay)
- [December 2023 farmgate tables](https://psa.gov.ph/farmgate-prices-palay/node/1684061966)

Release dates were taken from PSA page metadata surfaced by web search on 2026-10-29. The PSA pages themselves returned HTTP 403 to direct fetches.
