# HISTORY_RETRAIN — Step 1: data inventory (EXPLORATORY)

**Date:** 2026-11-02. **Status:** inventory only. No model was fitted and no result was computed. No served,
sealed, preregistered or dashboard file was changed.

**How each row was checked:**

- **[repo]**: first and last non-missing value counted directly from the file named.
- **[PSA live]**: PSA OpenSTAT PXWeb API, queried on 2026-11-02 for table metadata and a few sampled cells. The
  sampled cells were printed to the console only. **Nothing was downloaded into the repository.**
- **[ext]**: external and **not verified here**. These are taken from earlier audits or general knowledge and must be
  checked before use.

No value was invented, interpolated or filled.

## 1. The outcome: SWS involuntary hunger

| Item | Finding |
|---|---|
| File | `FINAL_FOOD_INSECURITY_LIGHTGBM/data/long/sws_area_rounds_full.csv` (same as `E114_Final_Run/data/`, `LEAD2_OPTIMIZATION/data/SOURCES.md`) [repo] |
| Source | SWS media release of 14 Oct 2026, Tables 1–6 (the full 1998–2026 series), plus verified releases from 2021 onward |
| Rounds | 115 rounds, 0 commissioned: 92 before 2021 and 23 from 2021 |
| First / last quarter | **1998-Q3 / 2026-Q3** |
| Quarters with a Balance Luzon (BL) reading | 106 of 113 |
| Quarters with no round | 1999-Q3, 2001-Q2, 2016-Q1, 2020-Q1, 2021-Q1, 2022-Q1, 2025-Q1 (the only 2025-Q1 round was commissioned and is excluded) |
| Share of quarters with BL above 11.3% | 1998–2020: 0.663 (86 quarters). 2021–2026: 0.650 (20 quarters). 2021-Q1..2023-Q3 alone: about 0.22 (LEAD2 protocol §1, M2) |
| Areas | NCR, Balance Luzon, Visayas and Mindanao, all on the same question, plus national |

**Definition and comparability changes:**

- **Respondent base.** Household heads until 2024. Adults from 2025-Q2. The file labels 108 rounds "household heads"
  and 7 rounds "adults".
- **Mode.** Three 2020 rounds were by mobile phone (COVID). The other 112 were face-to-face.
- **Sample size.** About 300 per area until 2023 (margin of error about ±6 points). About 600 for BL from 2024
  (about ±4 points).
- **Release dates.** From 2021, these are verified posting dates. **Before 2021 they come from a rule:** label month
  end + 60 days (`sws_release_date_evidence.csv`). Ten spot checks found real releases between 8 days earlier and
  43 days later than month end, so the rule never makes a reading available earlier than it really was.
- **Pre-2021 use.** These values were used only as a sensitivity arm (H2, sample b) and were never adopted, as the
  2026-10-27 scope decision required.

## 2. Inputs to the current P0H4 model

P0H4 has two parts:

- the **price part** π_P: one LightGBM model on the 12 FIRI v2 families, `lead`, and Pink Sheet world prices;
- the **hunger part** π_H: the latest BL reading, with σ taken from the latest-reading errors of all four SWS areas
  from 2021 onward.

The table below gives, for each input, what is in the repository today and what is published.

| Family / input | What P0H4 uses | Geography | In repo: first – last | Published: earliest | Gaps / definition changes |
|---|---|---|---|---|---|
| **A1, A2** food and headline CPI (and the T1 price condition) | PSA 0012M4ACP22, 2018=100, food 01.1 and all items | province ×5 | **2021-01 – 2026-09** (E41 `cpi_index_ACP22.csv`) [repo] | **2018-01** in ACP22 [PSA live]. **1994-01 – 2017-12** in ACP28, "2018=100 back-casted", with all five provinces and item 01.1 FOOD; cells for 1994, 2000, 2005, 2010 and 2017 checked filled for every province [PSA live] | **Back-cast caveat:** pre-2018 provincial values are PSA's later reconstruction on the 2018 basket. They are **not** the figures published at the time, which used the 1994, 2000, 2006 and 2012 bases. A 2012=100 provincial table (ACPI1/ACPI4, 1994–2021) also exists; its food item and fill were not checked. Provincial YoY can start in 1995-01. |
| Regional / national CPI (incl. Region IV-A rice CPI, P1 features) | ACP28 + ACP22, 2018=100 | PH, Region IV-A | **1994-01 – 2026-09**, 393 months, YoY from 1995-01 (`long/cov_cpi.csv`) [repo] | same | The same back-cast caveat applies before 2018. No stored release dates; the rule is day 10 of month m+1 (E114). |
| **A3** wholesale rice price | PSA 0052M4AWB01, regular-milled rice | province ×5 | **2021-Q1 – 2026-Q3** (E107 `psa_rice_prices.parquet`, 112 rows) [repo] | **2010-01**, new series; cells for 2010, 2012, 2015 and 2020 filled for Batangas, Quezon and Rizal [PSA live] | Old series 0012M4AWP01 (1990–2021) lists **only Batangas and Quezon** among the five provinces; its fill was not checked. |
| **V1** poverty and density | 2021 SAE and POPCEN 2024 | LGU → province | static | — | Static by design. It gives no time variation, so history length does not matter. |
| **C1** PAGASA El Niño alert or advisory | `enso_context.PAGASA_ENSO` items | national | **2023-03-24 – 2026-09-23** (20 items) [repo] | PAGASA has issued ENSO advisories for decades [ext] | **Not in the repo before 2023.** NOAA ONI is held for **1950-DJF – 2026-JAS** (`long/cov_oni.csv`) [repo], but switching to ONI would change C1's definition. |
| **C2** typhoons within 300 km of the province centroid | IBTrACS v04r01, recomputed | province ×5 | counts **2021-Q1 – 2026-Q3** (`pagasa_climate.parquet`) [repo] | The raw IBTrACS WP file is held for **seasons 1884–2026** (`E114_Final_Run/data/raw/ibtracs.WP.list.v04r01.csv`) [repo]. A PAR-box count exists for 1996-Q1 – 2026-Q4 (108 quarters that had storms) [repo] | The provincial 300 km counts would need recomputing for earlier years with `FIRI_V2_DATA_AUDIT/runner/typhoons.py`. The source is the same, so this is computation, not invention. |
| **C3** palay and corn production drop | PSA 0012E4EVCP0 | province ×5 | **2021-Q1 – 2026-Q2** [repo]. National palay **1987-Q1 – 2026-Q2** (`long/cov_palay.csv`) [repo] | **1987-Q1**, provincial; palay and corn cells for 1987, 1995 and 2005 filled [PSA live] | Quarterly figures are revised at the next release. Single vintage. |
| **C4** fisheries production drop | PSA 0132E4GVFP1 | province ×5 | **2021-Q1 – 2026-Q2** [repo] | Table lists 1980, but provincial cells are **empty for 1980–1992**. First filled quarter: **1993-Q1** [PSA live] | — |
| **E1** unemployment change | PSA 0021B3FKEI2 | national | **2005-04 – 2026-08**, 131 values (`long/cov_lfs.csv`) [repo] | **2005-04**; the table starts there [PSA live] | Quarterly rounds (Jan/Apr/Jul/Oct) until 2020; monthly from 2021, with some months not surveyed. The table starts at the April 2005 unemployment definition. An earlier audit reports a 2016 weight revision in the series [ext]. |
| **E2** remittance decline | BSP OFW cash remittances, rebuilt from cited releases | national | **2021-Q1 – 2026-Q2**, 22 quarters (`FIRI_V2_DATA_AUDIT/data/bsp_cash_remittances_quarterly.csv`) [repo] | BSP has published monthly series since about 1990 [ext] | **Not in the repo before 2021.** Would need acquiring from BSP. |
| **N1** news: FSSI-v3, GDELT GKG, GDELT price-news | RSS corpus, GKG, DOC | region | FSSI-v3 topics **2021-Q1 – 2026-Q4** (9,667 headlines). GKG **2021-01-01 – 2026-10-14** (58,634 documents). GDELT DOC **2017-01-01 – 2026-10-01** [repo] | GDELT DOC timelines start 2017. GKG 2.0 starts about 2015-02 [ext]. **The RSS corpus cannot be rebuilt for past years.** | **News exists only recently:** at most 2017+ (DOC) or 2015+ (GKG), and FSSI-v3 only from 2021. Before that, news would be structurally missing. |
| **Pink Sheet** world rice, cereals, oil, urea | World Bank CMO monthly | world | **1960-01 – 2026-09** in the raw xlsx (801 months). The parsed CSV keeps 2018-01+ [repo] | 1960 | One vintage, downloaded 2026-10-26. |
| **H1 / π_H** latest BL reading and its error σ | SWS (§1) | BL, plus four areas for σ | 1998-Q3 – 2026-Q3 [repo] | 1998-Q3 | See §1. |

## 3. What this means for history length

Earliest quarter with real published data, by what each target needs:

| Requirement | Earliest start | Binding input |
|---|---|---|
| **T2 label** (BL hunger > 11.3), region-wide | **1998-Q3** label. First Lead-1 target is 1998-Q4 (the 1998-Q3 reading was published 1998-09-29 by the rule) | SWS |
| **T1 label** (hunger AND provincial price condition, 2021–22 P60 thresholds unchanged) | **1998-Q3**, but **only after acquiring the PSA provincial back-cast** (ACP28, 1994–2017) and the 2018–2020 part of ACP22. **Neither is in the repo today.** With current repo data, T1 starts at **2021-Q1**. | provincial CPI |
| Persistence and logistic regression on hunger, CPI, ONI, typhoons and palay | **1998-Q4** with repo data only (regional and national CPI, ONI, PAR typhoons, national palay, Pink Sheet) | SWS |
| P0H4 LightGBM with **all 12 families present** | **2021-Q1** in the repo. With acquisition: E2 from BSP and C1 from PAGASA [ext], so roughly 2005-Q2 at best (E1), and **N1 is always missing before 2015–2017** | E2, C1, N1 (then E1, A3) |

**Plain summary:**

- **Hunger.** The SWS record gives about 5× more quarters (106 vs 20).
- **Provincial food prices.** These *are* published back to 1994, but only as a back-cast.
- **The full 12-family LightGBM.** It cannot see its full feature set before 2021 without new acquisition. Even
  with acquisition, the news families stay missing before about 2015–2017, the remittance family before about 1990,
  and LFS before 2005.

## 4. Decisions needed before Step 2 (PLAN.md)

1. **Acquire the PSA provincial CPI back-cast** (ACP28 1994–2017, plus ACP22 2018–2020)?
   - **Without it,** T1 cannot be extended at all. Only T2 gets a longer history.
   - **With it,** the plan must disclose that pre-2018 values are a later reconstruction, not real-time figures.
2. **How should "the existing LightGBM setup on the longer history" handle families that do not exist early?**
   - **(a) Native NaN.** LightGBM's default. The model then learns "missing = early era", a confound.
   - **(b) Long-history subset.** Restrict the retrained LightGBM to the families with long history: CPI, rice CPI,
     palay and corn, fisheries, ONI in place of C1, typhoons, Pink Sheet, SWS. This changes C1's definition and
     drops E2 and N1.
   - **(c) Start where all inputs exist.** Begin training at about 2005 (E1) after acquiring E2 and A3, with N1 as
     NaN.

   The plan must fix one choice before any result.
3. **Acquire E2 (BSP remittances) and A3 (2010+ provincial rice), and recompute C2 from the held IBTrACS raw file?**
   All three come from real published sources. They need acquisition or computation, which Step 1 did not do.
4. **The test block 2023–2026 is not unseen.** Every quarter through 2026-Q3 has been examined by earlier
   experiments (LEAD2 protocol, "Evidence status"). Holding it out here prevents tuning *in this experiment*, but its
   score is still development evidence. Only 2027+ quarters are untouched.
5. **Small samples.** In the test block, T2 has about 13–14 region-wide quarters per lead (LEAD2_FOODINSECURITY
   found 14 and 13). R1 needs at least 10 target quarters and at least 40 rows. In quarters, T2 cannot reach 40 rows
   at either lead. **The plan must say how R1's row clause applies to T2** before any result. Two options:
   - read it as R1 failing automatically;
   - state R1 as quarters only.

   The rules themselves would not change.
