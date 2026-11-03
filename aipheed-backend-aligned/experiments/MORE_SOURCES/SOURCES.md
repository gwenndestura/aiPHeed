# MORE_SOURCES: public data that could improve aiPHeed's food-insecurity forecast for CALABARZON (report only)

**Written:** 2026-11-03, from web searches and the repository's own data folders. No data was added to any model and
nothing was retrained.

**How to read it.** "Verified" means the fact was seen in an official page or release during this search. "To verify"
means it was only inferred or reported second hand. Licences are summarized and must be checked before use.

## 1. The data limits a new source would have to fix

| Code | Limit (from AUDIT.md, RELIABLE_L12, RELIABLE_NEWINFO) |
|---|---|
| **L1** | **Label noise.** SWS Balance Luzon (BL) hunger is measured on about 300 respondents (±5.7–6 points at 95%). 8 of the 9 errors in the failing 2015–2020 third are readings within that margin of 11.3% (R7). |
| **L2** | **No provincial or LGU outcome.** The target is regional, so Objective 3 / RQ4 / H4 (LGU rankings) cannot be checked against any measured outcome. |
| **L3** | **News only from 2021.** The news inputs are empty before 2021, so news says nothing about 2015–2020, and it carries 2.8% of SHAP influence. |
| **L4** | **Missing drivers.** Employment and OFW remittances are "not an input" on the dashboard cards. |
| **L5** | **Little provincial variation in the inputs.** Only the P0H4 price band and static poverty differ by province. |
| **L6** | **Short prospective record.** R1 needs 40 labelled quarters per lead, about 2037. |

## 2. Ranked table

Rank = expected value for these limits × how honestly and cheaply it can be used. "In repo" = already held.

| Rank | Source | What it measures | Level | Frequency, years | Publication delay | Access, licence | Limits it could fix | Notes |
|---|---|---|---|---|---|---|---|---|
| **1** | **OCTA Research, *Tugon ng Masa*: self-rated / involuntary hunger** | Families with "nothing to eat at least once in the last three months", the SWS wording | National, with **Balance Luzon** reported | Quarterly, **about 2022–present** (Q2 2026: fieldwork July 4–11, n = 1,200, ±3%) | About 3–6 weeks (Q2 2026 released August 2026) | Press-release PDFs ([octaresearch.com](https://octaresearch.com/wp-content/uploads/2026/08/PR-26-TNM-Q2-2026-SURVEY-RESULTS-ON-Poverty-Hunger.pdf)); copyrighted releases, citation needed; microdata not public | **L1 (prospective only)**: a second, independent measurement of the same quantity. Averaging or comparing SWS and OCTA BL readings reduces sampling noise from 2022 on | **Cannot help 2015–2020.** Its wording has shifted over time ("self-rated" vs involuntary); its BL figure and sample size per area need verifying per release. Using it in the label would need a new protocol, not an edit of PROSPECTIVE_PLAN.md |
| **2** | **PSA Community-Based Monitoring System (CBMS) 2024** | Household census items, including **food insecurity experience** | **Barangay / municipality** | One round (2024); earlier rounds for some LGUs (2022) | Preliminary results presented to LGUs **July–October 2025**; final release to be confirmed | PSA regional offices / LGUs; data-sharing agreement likely; PSA terms | **L2**: the only measured LGU-level food-insecurity outcome. It could test the Objective 3 rankings (RQ4/H4) once, cross-sectionally | Preliminary and "subject to validation". It is a one-off, so it validates rankings but does not forecast. CALABARZON release status is to verify |
| **3** | **DOST-FNRI National Nutrition Survey / ENNS food-insecurity module** | Household moderate or severe food insecurity (FIES; HFIAS in older rounds) | Regional; some **provincial** outputs (2019 ENNS disseminated for 39 provinces/HUCs) | 2018–2019 (pooled), 2021, 2022(?), **2023 (in repo: CALABARZON 19.1%, CI 17.0–21.1)** | Months to a year | FNRI publications and eNutrition; microdata on request (FOI listings) | **L2** (provincial, for some years) and face validity (Objective 5) | Sparse and irregular; pooled years. In-repo: `backend/data/e22/nns_fies_verified.json`, `E87_Outcome_Gap/data_acquired/fnri_fies_observations.csv` |
| **4** | **GDELT GKG 2.1 back-fill, February 2015–2020** (and GDELT 1.0 events from 1979) | Themed, geolocated news counts and tone (the E85 features) | Region and province (by place name) | Daily, **GKG from 2015-02**; events 1.0 from 1979 (no themes) | Minutes | BigQuery (scan cost; E85's scan was capped at 1.2 TB); GDELT is free to use with citation | **L3**: the only way to give the news inputs history over the failing 2015–2020 period | Prior expectation **low**: E85 found no predictive news value in 2021–2026. Coverage of Philippine outlets before 2017 is to verify. E85's code can be reused unchanged |
| **5** | **BSP OFW cash remittances** | US$ cash remittances through banks | National | Monthly, **about 1990–present** (in repo only 2021-Q1..2026-Q2) | About 6–7 weeks (e.g. June 2026 data on 2026-08-17) | BSP statistics pages / media releases; public statistics | **L4**: turns the dashboard's "OFW Remittance: not an input" into a measured driver | National and smooth, so it cannot follow BL quarter-to-quarter swings. Needs the 1998–2020 file (you offered to place it in `data/raw/`) |
| **6** | **PSA Labor Force Survey, provincial annual estimates** | Unemployment, underemployment, LFPR | **Province** (and HUC) | Annual, **2021–2023 seen** (2023 preliminary: Rizal 7.0%, Batangas 5.5%, Cavite 5.1%); quarterly regional | About 1 year for annual provincial figures | PSA RSSO IV-A releases ([rsso04a.psa.gov.ph](https://rsso04a.psa.gov.ph/sites/default/files/attachment-dir/SR09_2023%20CALABARZON%20Labor%20Market%20Statistics.pdf)); PSA open data | **L4, L5**: a provincial employment driver | Annual and recent only; regional quarterly LFS is already in the repo (`cov_lfs.csv`) |
| **7** | **PAGASA Drought and Dry Spell Assessments** | Provinces under dry condition / dry spell / drought | **Province** | Monthly PDFs (2015–2016 and 2023–2026 seen; full archive range to verify) | About 1 week after the month | `pubfiles.pagasa.dost.gov.ph/.../dryspelldrought/`; PAGASA terms (CADS-07) | **L5**: provincial climate stress | PDF parsing needed. It overlaps ONI, CHIRPS (tried in RELIABLE_NEWINFO: no call changed) and crop production |
| **8** | **PSA provincial retail and farmgate prices** | Retail prices of selected commodities (provincial capitals); palay farmgate | **Province** | Monthly (retail table 0042M4ARN04; farmgate from 1970 per the PhilRice mirror) | About 35 days for farmgate | PSA OpenSTAT; PSA open data | **L5**: provincial price variation beside the regional CPI | Palay farmgate is already in repo (`LEAD2_RELIABILITY_RESEARCH/y12_domestic_rice_supply/`). The retail table's year range is to verify |
| 9 | **PSA monthly rice stocks inventory (household, commercial, NFA)** | Rice stocks, days of cover | National | Monthly | About 1 month | PSA releases; NFA statements | L4 (supply shocks such as 2018) | OpenSTAT series and years to verify. One national series; 2018 is a single episode |
| 10 | **NDRRMC situation reports** | Agricultural and infrastructure damage per event, by region | Region / province | Per event (PDF sitreps) | Days | NDRRMC website; public | L5 (event shocks) | Irregular, event-based, PDF; overlaps the typhoon counts already used |
| 11 | **PSA FIES (SDG 2.1.2) regional prevalence** | Moderate or severe food insecurity | Region | Every few years (in repo: national 2019 44.2%, 2021 33.4%, 2023 31.4%; regional 2023) | About 1 year | PSA OpenSTAT (in repo) | Face validity only | Too sparse for a quarterly model. Already held |
| 12 | **PSA APIS hunger question** | Families that experienced hunger for lack of money, past 3 months | **Region** | APIS years (2011 verified with a regional table; other years to verify) | About 1 year | PSA APIS publications | L2 (regional, CALABARZON-specific outcome) | **If** asked in 2014–2020 APIS rounds, it would be the only CALABARZON-specific hunger outcome in the failing period. Not confirmed: to verify before any use |
| 13 | **DOE retail pump prices** | Gasoline, diesel, LPG prices | **Metro Manila only** | Weekly PDFs; monthly 1990–2021 via the PhilRice RDAC catalog | Days | DOE legacy site; RDAC | — | NCR only; overlaps the Pink Sheet crude price already used |
| 14 | **Google Trends** (e.g. "gutom", "ayuda", rice price) | Relative search interest | Region (PH regions in the web interface) | Weekly or monthly, 2004+ (web); the API is alpha with a 5-year window | Days | Google ToS; values are sampled and change between downloads | — | Not reproducible (sampling), not sealable. Not recommended |
| 15 | **WFP HungerMap LIVE; FAO FIES (Gallup)** | Modelled food consumption; national FIES (3-year averages) | National / modelled | Daily (modelled) 2020+; annual | — | Public | — | Modelled, not measured, or national only. Not recommended |
| 16 | **Rice import / tariff policy dates** (RA 11203, effective 2019-03-05; EO 62, 2024) | Policy events | National | 2–3 events | — | Public | — | Too few events, chosen after seeing the failure. Not recommended (Step 0) |
| 17 | **DSWD 4Ps coverage** | Beneficiary households | Region | Scattered annual figures; no dated series found | Unclear | DSWD | — | Not a usable series (Step 0) |
| 18 | **Common Crawl CC-News; Media Cloud** | Full-text news | — | CC-News from **2016-08**; Media Cloud from 2008 (PH coverage to verify) | — | Common Crawl terms; Media Cloud research access | L3 (partly) | GDELT GKG (rank 4) covers the same need with existing code; these are the fall-backs |

## 3. Recommendation

1. **No source fixes the main limit (L1) for 2015–2020.** That period's failure is survey noise around a fixed line in
   a 300-respondent area, and no public measurement of BL hunger for those quarters exists besides SWS. **Do not
   expect a new input to make the model pass R1–R7 on the development window.**
2. **Most useful for the thesis objectives:**
   - **CBMS 2024 (rank 2)** for a measured LGU-level check of the Objective 3 rankings (RQ4/H4). This is the one place
     new data can turn an untestable objective into a tested one.
   - **FNRI provincial outputs (rank 3)** as a second, sparser check.
3. **Most useful for the forecast going forward: OCTA BL hunger (rank 1).**
   - It gives a second, independent quarterly measurement from 2022.
   - Recorded beside SWS, it shows how much of a quarter's HIGH/LOW label is sampling noise.
   - Using it inside the label or the scoring would need a new protocol, decided before outcomes, not a change to
     PROSPECTIVE_PLAN.md.
4. **If one input experiment is still wanted:** the **GDELT GKG 2015–2020 back-fill (rank 4)**.
   - It is the only way news can cover the failing period, with E85's code unchanged.
   - Expectation is low, and it would need its own sealed plan and your approval for the BigQuery scan.
5. **For the dashboard's "not an input" cards (L4):** BSP remittances (rank 5, your file) and provincial LFS (rank 6).
   - They make the drivers honest rather than the forecast better.
6. **Not recommended:** Google Trends, HungerMap LIVE, national FAO FIES, policy-date dummies, 4Ps (ranks 14–17).
7. **To verify before any decision:**
   - whether APIS asked its hunger question in the 2014–2020 rounds (rank 12; if yes, it moves near the top);
   - OCTA's Balance Luzon sample size and wording per release;
   - CBMS 2024 release status for CALABARZON;
   - GKG coverage of Philippine outlets in 2015–2016.

## 4. Sources consulted

- OCTA: [Q2 2026 release](https://octaresearch.com/wp-content/uploads/2026/08/PR-26-TNM-Q2-2026-SURVEY-RESULTS-ON-Poverty-Hunger.pdf), [GMA Q2 2026](https://www.gmanetwork.com/news/topstories/nation/999186/octa-self-rated-poverty-hunger-rise-in-q2-2026/story/), [GMA 2023](https://gmanetwork.com/news/topstories/nation/895459/octa-poll-self-rated-hunger-among-pinoys-rises-to-14-or-3-7m-families/story), [Manila Bulletin Q2 2023](https://mb.com.ph/2023/9/19/octa-13-2-m-filipino-families-consider-themselves-poor-in-q2-2023)
- CBMS 2024: [PSA Oriental Mindoro (Baco)](https://rssomimaropa.psa.gov.ph/system/files/attachment-dir/PSA%20Oriental%20Mindoro%20Presents%202024%20CBMS%20Preliminary%20Results%20for%20Baco%2C%20Oriental%20Mindoro.pdf), [PSA CAR (Kiangan)](https://rssocar.psa.gov.ph/content/kiangan-lgu-acquires-crucial-insights-2024-cbms-preliminary-results), [Cagayan de Oro](https://cagayandeoro.gov.ph/index.php/news-and-article/item/3267-psa-misor-office-presents-community-system-findings-to-city-hall.html), [PSA Region VIII](https://rsso08.psa.gov.ph/system/files/attachment-dir/PR-202507-0864-21.pdf)
- FNRI: [2019 ENNS provincial dissemination](https://www.fnri.dost.gov.ph/index.php/programs-and-projects/news-and-announcement/797-dost-fnri-conducts-online-provincial-dissemination-of-2019-enns-results), [ENNS overview](https://fnri.dost.gov.ph/index.php/programs-and-projects/news-and-announcement/763-2018-expanded-national-nutrition-survey), [FOI listings](https://foi.gov.ph/agencies/fnri/SUCCESSFUL), [GHDx ENNS 2018–2020](https://ghdx.healthdata.org/print/521510)
- PSA: [Region IV-A poverty](https://rsso04a.psa.gov.ph/node/1684057525), [CALABARZON labour 2023](https://rsso04a.psa.gov.ph/sites/default/files/attachment-dir/SR09_2023%20CALABARZON%20Labor%20Market%20Statistics.pdf), [Rizal labour 2023](https://rsso04a.psa.gov.ph/sites/default/files/attachment-dir/2023%20Annual%20Labor%20Market%20Statistics%20in%20Rizal.vaa_.pdf), [OpenSTAT retail prices](https://openstat.psa.gov.ph/PXWeb/pxweb/en/DB/DB__2M__NRP/0042M4ARN04.px), [farmgate palay](https://psa.gov.ph/farmgate-prices-palay), [APIS 2011 hunger](https://psa.gov.ph/statistics/income-expenditure/apis/node/41305)
- FIES / FAO / WFP: [FAO FIES microdata](https://microdata.fao.org/index.php/catalog/775/pdf-documentation), [World Bank microdata 5042](https://microdata.worldbank.org/catalog/5042), [Inquirer FAO 2017–19](https://newsinfo.inquirer.net/1307485/59m-filipinos-went-hungry-in-2017-19-says-fao/amp), [WFP Philippines monitoring](https://www.wfp.org/publications/wfp-philippines-food-security-monitoring-oct-2022-march-2023)
- Inputs:
  - [PAGASA May 2026 drought assessment](https://pubfiles.pagasa.dost.gov.ph/pagasaweb/files/climate/dryspelldrought/31May2026_Drought%20and%20Dry%20Spell%20Assessment.pdf)
  - [PAGASA April 2024 drought assessment](https://pubfiles.pagasa.dost.gov.ph/pagasaweb/files/climate/dryspelldrought/April2024_Drought%20and%20Dry%20Spell%20Assessment_asof06May2024.pdf)
  - [ABS-CBN drought definitions](https://www.abs-cbn.com/news/2024/2/6/14-provinces-already-experiencing-drought-pagasa-2249)
  - [RDAC DOE pump prices](https://ricelytics.philrice.gov.ph/data_catalog/dataset/62155c36-11af-4ac6-aebc-e5afc0584467)
  - [DOE legacy price pages](https://legacy.doe.gov.ph/taxonomy/term/95?page=339)
  - [NDRRMC agri damage, GMA](https://gmanetwork.com/news/topstories/nation/878046/agri-damage-due-to-habagat-egay-falcon-hits-p2-9-billion-ndrrmc/story)
  - [NFA buffer stock, Inquirer](https://business.inquirer.net/264763/nfa-rice-buffer-stock-enough-for-78-days)
  - [Google Trends API](https://developers.google.com/search/blog/2025/07/trends-api?hl=ar)
  - [Google Trends sampling](https://www.mzes.uni-mannheim.de/en/publications/details/default-1b90339871013c563d9e0770aa21fed2-44)
  - BSP and PAGASA/CHIRPS sources as cited in `../RELIABLE_NEWINFO/STEP0_SOURCES.md`
- News archives: [GDELT (Wikipedia)](https://wikipedia.com/wiki/GDELT_Project), [MongoDB GDELT intro](https://mongodb.com/developer/how-to/introduction-to-gdelt-data), [CC-News](https://ml.paperswithcode.com/dataset/cc-news), [Media Cloud](https://ojs.aaai.org/index.php/ICWSM/article/view/18127)
