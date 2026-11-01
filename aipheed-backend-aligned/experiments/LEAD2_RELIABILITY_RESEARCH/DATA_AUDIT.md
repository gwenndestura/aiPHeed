# Data audit for Lead-2 reliability

**Date:** 2026-10-29.
**Scope:** every claim below was checked against files in this repository. Items not in the repository are marked
**external, not verified here**. Nothing was downloaded.

## 1. Where Lead 2 fails

Lead 2 fails on the hunger side, not the price side:

- P0H4 Lead 2 caught 0 of 10 onsets, with recall 0.35.
- A perfect price forecast would lift recall only to 0.59 (`LEAD2_OPTIMIZATION/LEAD2_FINAL_REPORT.md`).
- The 2023-Q4 → 2024 hunger surge was published after the Lead-2 issue dates.

**The evidence question is therefore whether Balance Luzon (BL) hunger exceedance can be forecast two to three
quarters ahead, and on how many independent observations.**

## 2. Outcomes (observed, not proxies)

| Source | Measure | File | Coverage | Frequency | Geography | Publication lag | Lead-2 use |
|---|---|---|---|---|---|---|---|
| SWS Social Weather Survey | Involuntary hunger, % families (adults from 2025) | `FINAL_FOOD_INSECURITY_LIGHTGBM/data/long/sws_area_rounds_full.csv`, `E114_Final_Run/data/sws_rounds_1998_2026.csv`, `backend/data/inputs/sws_rounds.csv` (2021+, production) | **1998-Q3 .. 2026-Q3**, about 4 rounds a year, 115 rounds | Quarterly | **Four areas:** NCR, Balance Luzon, Visayas, Mindanao (and national) | 2021+: verified posted dates (8–90 days). Pre-2021: **rule** = label month end + 60 days. 10 spot-checked releases came 8 days early to 43 days after month end, so the rule is conservative (never earlier than the real release). | **Yes.** It is the hunger condition of T43c and the FIRI R target. |
| SWS sampling error | Area margin of error | same file, `area_moe_bl` | All rounds | – | Area | – | ±6 points (n ≈ 300 per area) before 2024; ±4 (n ≈ 600) from 2024 |
| FNRI ENNS/NNS FIES | Moderate or severe household food insecurity | `nns_fies.parquet` (via E13) | 2025 only (regional 22.6%) | Irregular | Region (copied to provinces) | – | **No.** One value. |
| FNRI ENNS 2018–2021 rolling | Provincial food insecurity, HFIAS/FIES | **external, not verified here** (E13 search summaries) | Each province once, 2018–2021 | One cross-section | Province | – | **No time series** |
| PSA subsistence incidence | Families below the food threshold | `backend/data/inputs/psa_subsistence_population_2021_2023.csv` | 2021, 2023 | Triennial | Province | ~8 months | **No** (2 points per province, CV up to 53%) |
| PSA CBMS food-shortage items | Household | **external, not verified here** | 2022+ rollout | Irregular | Barangay/municipal | – | Future candidate |

**Conclusions on outcomes:**

- E13 (`2026-10-13_E13_DA_Predictive_Accuracy/OUTCOME_DATA_AUDIT.md`) found **no repeated provincial food-insecurity
  outcome**. This audit confirms that nothing new is in the repository.
- **The one genuine expansion is SWS itself:**
  - the same question and survey in **four comparable areas**;
  - **1998–2020** history, which gives about 90 quarters × 4 areas of the same measured outcome;
  - **BL alone in 2021–2026** has only 17–20 quarters, against about 360 area-quarters in the full panel.

**Comparability caveats:**

- **Mode:** three 2020 rounds were by mobile phone (COVID).
- **Respondent base:** household heads until 2024, registered voters in early 2025, adults from 2025-Q2.
- **Release dates before 2021** are rule-based.
- **Area samples** are about 300 per area (±6 points) until 2023, which is **large relative to the 11.3 threshold
  distance in most quarters**.

## 3. Predictors with long history

| Source | Field | File | Coverage | Frequency | Geography | Lag | Lead-2 suitable |
|---|---|---|---|---|---|---|---|
| PSA CPI | All items, food, rice (index, YoY) | `long/cov_cpi.csv` | **1994-01 .. 2026** | Monthly | National, Region IV-A | ~5 days after month end (PSA calendar; no stored dates) | Yes (month m0 = 2nd month of the origin quarter) |
| PSA CPI (provincial) | Food, all items | `E41_Lead2_Audit/data_acquired/cpi_index_ACP22.csv` | 2021+ only | Monthly | Province | same | Yes, 2021+ only |
| PSA palay production | Region IV-A | `long/cov_palay.csv` | 1987 .. 2026 | Quarterly | Region | ~6–8 weeks (calendar; no stored dates) | Yes, with a one-quarter lag |
| PSA palay, corn, fisheries | Province | `E41/data_acquired/*production.csv` | 2021+ | Quarterly | Province | **no stored date** (committed 2026-10-20) | 2021+ only |
| PSA LFS | Unemployment | `long/cov_lfs.csv` | 2005 .. 2026 | Quarterly rounds, monthly from 2021 | National | ~5–6 weeks | Yes |
| NOAA ONI | ENSO index | `long/cov_oni.csv` | 1950 .. 2026 | Monthly | Global | ~1 week | Yes |
| IBTrACS | Typhoons in PAR | `long/cov_ibtracs_par.csv` | 1996 .. 2026 | Quarterly | PAR | days | Yes |
| GDELT DOC | News volume, 4 categories | `long/cov_gdelt_doc.csv` | **2017-01 ..** | Daily | National | real time | 2017+ only |
| BSP remittances | OFW cash remittances | E43 inputs (`ofw`) | 2020-Q1+ (curated to 2025-Q4) | Quarterly | National | ~6 weeks | 2021+ only |
| PSA rice wholesale | Province | E43 inputs (`rice`) | 2020+ | Quarterly | Province | fetched 2026-09-09 | 2021+ only |

## 4. Opportunities and limits

| Question | Answer from the data |
|---|---|
| **Monthly instead of quarterly observations?** | **No legitimate gain.** The outcome (SWS hunger) is observed about quarterly. Monthly CPI rows would repeat the same outcome three times and inflate n without new evidence. Monthly predictors are already used, at month m0. |
| **Older history?** | **Yes, for the hunger outcome and for national/regional CPI, palay, ONI and typhoons (1994–2020).** Provincial price and production series start in 2021. Pre-2021 BL history was used before (H2, H3b) but **only scored on the 2021–2026 quarters**. It was never validated out of sample before 2021, and never used for selection away from the test window. |
| **Other regions?** | **Yes, for hunger: NCR, Visayas and Mindanao** use the same SWS question and survey, so their labels are comparable. CPI for those areas is **not** in the project (national CPI only). An area-held-out test (fit on NCR, Visayas and Mindanao; predict BL) is possible for the hunger component. |
| **Provincial or household outcomes?** | **None with repeated observations** (E13). Provincial accuracy cannot be established. |
| **Predictors available at each origin?** | 2021+: audited (perturbation audits at 7 origins, including 2026-Q3). Pre-2021: CPI month ≤ m0 (published before issue on the PSA calendar), SWS by the conservative release rule. |
| **Label noise** | BL hunger is a survey estimate with ±4–6 points of sampling error. In 2021–2026, two LOW quarters are **exactly 11.3** and several others are within 2 points. **Part of the "error" is unmeasurable, not unforecastable.** Quantified in RESULTS.md (X1). |

## 5. Scope note

You decided on 2026-10-27 to keep the 2021+ study window for the served system. Pre-2021 data here are used **for
research and validation only**. Any result that uses them can be adopted only after you formally revise the scope.

---

# Phase 2 additions (2026-10-29)

## 6. Covariates verified for Phase 2 (all read-only from `FINAL_FOOD_INSECURITY_LIGHTGBM/data/long` unless noted)

| Source | Series | Coverage | Geography | Release lag (rule used at issue O(t)) | Revisions / vintage |
|---|---|---|---|---|---|
| PSA CPI (`cov_cpi.csv`) | All items, food, rice. YoY as published. | 1994-01 .. 2026-12 (396 months) | Philippines; Region IV-A | About the 5th of the next month. Newest = month 2 of quarter t. | Rebasings (2006, 2012, 2018 = 100) are spliced in one series. Single vintage. |
| PSA CPI provincial (`E40_SWS_CPI_Tiers/data_acquired`) | Food, all items YoY | **2021-01 onward only** | 5 CALABARZON provinces | Same | No pre-2021 provincial history in the project. |
| NOAA CPC ONI (`cov_oni.csv`) | 3-month ONI | 1950 .. 2026-JAS | Niño 3.4 | Early in the next month. Newest = season ending month 1 of quarter t. | ONI is recomputed with updated ERSST. Minor. |
| IBTrACS (`cov_ibtracs_par.csv`) | Tropical cyclones in PAR per quarter | 1996-Q1 .. 2026-Q4 | PAR | Known in real time. Used: quarter t−1. | Best-track revisions do not change counts much. |
| PSA palay (`cov_palay.csv`) | Quarterly production, YoY | 1987 .. 2026 | Philippines | About 6 weeks. Used: quarter t−1. | Revised at the next release. Single vintage. |
| PSA LFS (`cov_lfs.csv`) | Unemployment rate | 2005-04 onward. Quarterly rounds before 2021, monthly after; 152 non-missing values. | Philippines | About 5–6 weeks. Used: newest round ≤ m0 − 2. | The 2016 weight revision is in the series. |
| **World Bank Pink Sheet** (`y10_world_prices/data_acquired/`, downloaded 2026-10-29, sha `bd89b83e…`) | Rice Thai 5%, crude average, urea, maize, wheat HRW, palm oil (USD) | 1960-01 .. **2024-12** (vintage "Updated on January 03, 2025") | World | About the 2nd–3rd business day of the next month. Used: m0. | One vintage. Monthly averages are rarely revised. **This vintage stops at 2024-12, so a 2021+ confirmation would need a newer vintage. None was needed: no gate passed.** |

## 7. Earlier hunger signals searched (Y6)

| Candidate | Finding | Usable for Lead 2? |
|---|---|---|
| OCTA Research *Tugon ng Masa* (quarterly, n = 1,200, ±3 national) | Q3 2024: fieldwork 28 Aug–2 Sep, published 22 Oct 2024 (GMA News), after the 1 Oct issue. Q4 2023 BL hunger was 11% while SWS December 2023 BL was 14.3%, so the two instruments disagree on the onset. Q2 2026: fieldwork 4–11 Jul, reported about 21 Aug 2026. Series since about 2022. | **No.** It is not published earlier than SWS at the Lead-2 issue, its history is too short to validate, and its BL level differs from SWS. |
| WFP mVAM Philippines (monthly mobile survey) | 3 rounds, Oct 2022–Mar 2023, all 17 regions; food insecurity 10–15% nationally. | **No.** It was discontinued. |
| DSWD / NNC monitoring | No published monthly or quarterly hunger series found. WFP notes that government monitoring focuses on food consumption. | No. |
| PSA FIES / SDG 2.1.2 (FIES) | Triennial or annual, national or regional. | No (frequency). |

Sources:

- [GMA, OCTA Q3 2024](https://www.gmanetwork.com/news/topstories/nation/924475/octa-self-rated-poverty-hunger-decline-in-2024-q3/story)
- [GMA, OCTA Q4 2023](https://gmanetwork.com/news/topstories/nation/895459/octa-poll-self-rated-hunger-among-pinoys-rises-to-14-or-3-7m-families/story)
- [GMA, OCTA Q2 2026](https://www.gmanetwork.com/news/topstories/nation/999186/octa-self-rated-poverty-hunger-rise-in-q2-2026/story/)
- [WFP mVAM Oct 2022–Mar 2023](https://www.wfp.org/publications/wfp-philippines-food-security-monitoring-oct-2022-march-2023)
- [UNDP MPTF document](https://mptf.undp.org/sites/default/files/documents/2023-05/philippines_0.pdf)

## 8. Remaining data gaps (Phase 2)

1. **A hunger observation published within about 1 month of fieldwork, or fielded in month 1 of the issue quarter.** None exists. At a Lead-2 issue, the newest SWS reading is 3 quarters before the target.
2. **Provincial food CPI before 2021.** PSA OpenSTAT publishes provincial CPI under the 2012 base (from 2012). Acquiring it would allow independent validation of the provincial price condition, which Y8 could only approximate at regional level.
3. **Leading information on the domestic food-price path 5–7 months ahead that works in real time.** World prices did not (Y10, Y11). Untested candidates: NFA and private rice stocks, import arrivals and the tariff schedule (EO 62, June 2024), and farmgate palay prices. All are monthly from PSA or BOC/DA, but their release dates and history need verifying.
4. **Prospective sealed quarters.** These are the only route to an untouched evaluation of any Lead-2 claim.

## 9. Data-quality notes found in Phase 2

- `sws_rounds.csv` maps the "First Quarter 2025 Social Weather Survey" (published 2025-06-27) to 2025-Q2. It is the first of two 2025-Q2 rounds. Both 2025-Q2 rounds are HIGH (17.0 and 15.3), so no label depends on this mapping.
