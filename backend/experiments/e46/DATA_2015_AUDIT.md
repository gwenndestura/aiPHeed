# E46: can the aiPHeed inputs go back to 2015-Q1?

This is a read-only feasibility audit, run on 2026-10-16. Nothing was downloaded into the live system, and no code or data file was changed.

Probe scripts are in `scripts/` and their outputs in `data/`.

**What could be reached:**

| Source | Status |
|---|---|
| PSA OpenStat API | **200** |
| NASA POWER | **200** |
| NOAA (IBTrACS, ONI) | **200** |
| sws.org.ph | **200** (new site; old `swsmain/artcldisppage` links return 404) |
| psa.gov.ph | **403** |
| bsp.gov.ph | **403** |
| Google News RSS | reachable (section 3) |

## 1. Target pieces

**S1 = H + 2D**, where H is SWS Balance Luzon hunger and D is province food inflation minus the five-province mean.

| Input | Source | 2015-Q1..2020-Q4? | Level / frequency | Breaks and how to bridge | Script or by hand | Verdict |
|---|---|---|---|---|---|---|
| **SWS hunger (H), Balance Luzon** | SWS Social Weather Survey media releases (PDF), e.g. [Q4 2017 release](https://www.sws.org.ph/downloads/media_release/pr20180122%20-%20Hunger%20in%20families%20(Media%20release).pdf) | 2015–2019: quarterly rounds exist (SWS gives Balance Luzon annual averages of **12.4% for 2015, 13.6% for 2016, 12.8% for 2017**). 2020: the March round was not held (lockdown); the May–November 2020 rounds were run by **mobile phone** | Area stratum (Balance Luzon), quarterly | **Mode break in 2020** (face-to-face to phone, then back from 2021). Bridge: flag 2020 or leave it out of τ. Publication dates must be collected per round (the label is used only after it was posted) | **By hand**: no API; each figure comes from a release PDF. Nothing before 2021 is in the repo (`sws_rounds.csv` starts at 2021-Q2) | **PARTIAL** |
| **Provincial food CPI (D)** | PSA OpenStat `DB/2M/PI/CPI/2018/0012M4ACP15.px`, **2018=100 backcast, January 1994 – December 2017**; plus `0012M4ACP09.px`, 2018=100, January 2018 – December 2025 | **Yes**, all five provinces and Region IV-A, "01.1 Food" and "01.1.1.12 Rice" | Province, monthly | **None to bridge**: PSA backcast the 2012-based series to 2018=100, so 1994–2026 is on one base. Year-on-year can be computed from the index (YoY tables `ACP10` start in 2019) | **API** | **READY** |
| **Rice retail prices by province** | PSA OpenStat `DB/2M/RP/0042M4ARP01.px` ("Regular Milled Rice (RMR)", 1990–2021) and `DB/2M/2018/0042M4ARA01.px` ("RICE, REGULAR-MILLED, 1 KG", 2018–2025); also `DB/2M/NRP/0042M4ARN01.px` (2012–2021) | **Yes** (old series) | Province, monthly | **Survey/series change in 2018**: different commodity definitions. Bridge using the **2018–2021 overlap** (province-specific ratio or splice) and check the level shift. The served `rice_rel` uses a separate CSV starting in 2021 | **API** | **PARTIAL** (needs a splice) |

## 2. Driver data

| Input | Source | 2015–2020? | Level / frequency | Breaks and how to bridge | Script or by hand | Verdict |
|---|---|---|---|---|---|---|
| **Unemployment (LFS)** | PSA OpenStat `DB/1B/LFS/0021B3FKEI2.px` (April 2005 – August 2026) | **Yes** | **National only** (no regional table on OpenStat), quarterly rounds (Jan/Apr/Jul/Oct) until 2020, monthly from 2021 | Design changes in **2016** (new LFS master sample) and **2021** (monthly LFS, new population-projection weights). PSA's own revision of the earlier years is not confirmed here (psa.gov.ph is 403). Bridge: use the year-on-year change, or add level-break dummies at 2016-Q2 and 2021-Q1. 2020-Q2 is a COVID outlier (lockdown spike) | **API** | **PARTIAL** (series exists; breaks must be handled) |
| **OFW remittances** | BSP "Overseas Filipinos' Cash Remittances" (monthly, by country of source; BSP Statistics → External Accounts) | Exists at BSP (series runs back decades) | National, monthly | Repo values are hand-curated and only cover 2020–2025; their quarterly split already disagrees with BSP's own figures (see `e43/DATA_REFRESH.md`) | **By hand** (bsp.gov.ph returns 403 to scripts) | **PARTIAL** (exists, manual only) |
| **Rainfall** | NASA POWER daily PRECTOTCORR (`power.larc.nasa.gov/api/temporal/daily/point`) | **Yes** (data from 1981) | Province (6 points each), daily → quarter | None: one service end to end (E43 rebuilt 1991–2026-Q3 and checked it) | **API** | **READY** |
| **Tropical cyclones** | NOAA IBTrACS v04r01 Western Pacific CSV | **Yes** (full history) | Province centroid, 300 km radius | None | **Script** (file download) | **READY** |
| **ENSO (ONI)** | NOAA CPC `oni.ascii.txt` | **Yes** (from 1950) | Global, monthly | None | **Script** | **READY** |
| **Fisheries production** | PSA OpenStat `DB/2E/FS/0132E4GVFP1.px` | **Yes** (1980–2026-Q2) | Province × subsector, quarterly | None in the table. Release dates for old quarters are not recorded (only the latest OpenStat update stamp) | **API** | **READY** (proxy) |

## 3. News (Google News RSS, the system's source)

**Test** (`scripts/news_probe.py`, `data/news_probe.csv`): the system's own 16 CALABARZON food queries (`_CALABARZON_FOOD` in `gnews_rss_fetcher.py`), with the same quarterly `after:/before:` window and en-PH locale. All 112 requests returned HTTP 200.

| Quarter | Unique titles | Naming a CALABARZON province | Of those, tagged by the driver classifier | Validated (R1.1) titles in the served store |
|---|---|---|---|---|
| 2015-Q2 | **1** | 0 | 0 | – |
| 2017-Q3 | **3** | 1 (an earthquake shake map) | 0 | – |
| 2019-Q4 | 13 | 5 | 1 | – |
| 2020-Q2 | 25 | 1 (a Quezon *City* item, a false match) | 0 | – |
| 2022-Q3 | 20 | 2 | 0 | 6 |
| 2024-Q3 | 61 | 12 | 1 | 36 |
| 2026-Q2 | 99 | 22 | 1 | 15 |

**Reading it.** Google News RSS today returns almost nothing for 2015–2017 and very little for 2019–2020. Retrieval of old items falls off sharply with age; it is an index limitation, not evidence that no news existed. The pre-2021 news inputs (`news_n`, `news_reg`, `news_direct_share`, FSSI) **could not be rebuilt on the same basis**. A 2015 news feature would be close to zero by construction, which would look like a real signal to the model.

**Options.**
- **(a)** Keep the news inputs and mark 2015–2020 as missing.
- **(b)** Drop the news inputs from a 2015–2026 model.
- **(c)** Use an archive with stable historical coverage (for example GDELT, from 2015, which would need its own relevance and province-attribution validation).

**Verdict: NOT AVAILABLE** (on the current source).

## 4. Extra labelled data and the effect on τ

**Extra labels.**
- **2015–2019:** 20 quarters × 5 provinces = **up to 100 province-quarters**, if each quarter has an approved (definition A) round.
- **2020:** about 3 quarters (May–November, phone mode) = **about 15 more**, if kept.
- **Total:** about 100–115 new labelled province-quarters against the **95** labelled now (2021-Q2..2026-Q3). The training history would roughly double.

**Effect on τ: not computable exactly.** The 2015–2020 quarterly Balance Luzon H values are not in the repo and are not machine-readable (they are PDF releases).

**Bounded estimate.** D averages zero across the five provinces each quarter, so the median of S1 tracks the median of H. Today's τ for the Q4 2026 origin is 14.99, and the median of 2021–2026 H is 14.8.
- **Assumptions:** 2015–2017 use the SWS annual averages (12.4 / 13.6 / 12.8); 2018–2019 and 2020 are swept over plausible ranges.

| 2018–2019 H | 2020 H | Median H (proxy for τ) with 2015–2020 | Now | 2024–2026 quarters above τ |
|---|---|---|---|---|
| 10 | 15 | 12.8 | 14.8 | 100% (unchanged) |
| 12 | 18 | 12.8 | 14.8 | 100% |
| 14 | 21 | 14.0 | 14.8 | 100% |
| 16 | 24 | 14.3 | 14.8 | 100% |

**What this means.**
- **τ would fall, not rise:** by about 0.5–2 points, because 2015–2019 hunger was lower than 2024–2026.
- **The recent labels would not change:** every 2024–2026 quarter stays above τ, so the high index of recent quarters would remain.
- **What would change:** older quarters would be more balanced, giving the model more LOW examples to learn from.

## Verdict summary

| Input | Verdict |
|---|---|
| SWS hunger (Balance Luzon) | **PARTIAL**: exists for 2015–2019; 2020 is phone mode; PDF releases collected by hand, publication dates needed |
| Provincial food CPI | **READY**: 2018=100 backcast from 1994 (API) |
| Rice retail prices by province | **PARTIAL**: series change in 2018; splice using the 2018–2021 overlap |
| LFS unemployment | **PARTIAL**: national only; 2016 and 2021 design breaks |
| BSP OFW remittances | **PARTIAL**: exists, hand curation only (403) |
| NASA POWER rainfall | **READY** |
| NOAA IBTrACS / ONI | **READY** |
| PSA fisheries production | **READY** (proxy; old release dates unknown) |
| News (Google News RSS) | **NOT AVAILABLE**: 1–25 titles per quarter for 2015–2020, near zero before 2019 |

## Recommendation

A 2015–2026 experiment is **worth running only for one purpose**: to give the model about twice the training history and more LOW cases. It would **not** lower the current index.

**What is ready:** the government series (CPI on one 2018 base, rainfall, storms, ONI, fisheries) are ready by API.

**What it depends on:**
1. Collecting about 20–24 SWS Balance Luzon rounds by hand (2015–2020 media-release PDFs), each with its publication date.
2. A decision on the 2020 phone-mode rounds.
3. Handling the LFS breaks (2016 and 2021).
4. Splicing the 2018 change in the rice price series.
5. Hand-curating BSP remittances.
6. **Dropping or masking the news inputs**, which can't be rebuilt for 2015–2020 from Google News. E36's news and FSSI inputs would have to go, or be marked missing before 2021, so the model would not be E36 as served.

**Without SWS H there is no 2015–2020 label at all**, so that collection is the gating step.

**Suggested order:**
1. Collect the SWS rounds.
2. Recompute τ exactly.
3. Run a government-inputs-only 2015–2026 walk-forward against the same baselines. E36's government-only baseline (B5) is already close to E36 on 2021–2026.
