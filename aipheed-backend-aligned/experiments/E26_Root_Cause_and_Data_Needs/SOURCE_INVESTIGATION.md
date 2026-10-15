# Source investigation: outcome data and signals beyond the authorized files

**Date:** 2026-10-14, about 01:10–01:15 UTC.

**Method.** Web searches and fetches were limited to **methodology and older-year design documents**. No data file was downloaded for analysis. Nothing found here enters any computation; every source needs your authorization first (`MISSING_OBSERVATIONS_SPEC.md`).

**Exposure.** One search exposed protected H2-2026 price information (`docs/CONTAMINATION_LOG.md`). A later rule breach is logged in `docs/CONTAMINATION_LOG_ADDENDUM.md`.

**Verification levels used below:**

| Level | Meaning |
|---|---|
| **READ** | I obtained and read the document's own text: a fetched page, or PDF text extracted locally with pdfminer under `python -I` in an isolated scratch folder |
| **SUMMARY** | Known only from a search engine's summary of the page. **Unverified**: it must be checked against the official document before use. |
| **BLOCKED** | The official page refused automated access (HTTP 403) or was image-only. **Not bypassed.** |

## Summary table

| # | Source (producer) | Measures | Role | Geography | In-window periods | Publication timing | Access | Verification |
|---|---|---|---|---|---|---|---|---|
| S1 | SWS quarterly hunger survey (Social Weather Stations) | % of families with involuntary hunger in the past 3 months | **Current outcome (H)** | NCR, Balance Luzon, Visayas, Mindanao | Quarterly; 20 production rounds 2021-Q1…2026-Q2 authorized | About 1 month after fieldwork (single example, SUMMARY); 2026 dates are upper bounds only | Releases public. Raw datasets "open to academic researchers" (READ). | Method READ; sample sizes SUMMARY |
| S2 | CBMS 2022 and 2024 (PSA with LGUs, RA 11315) | Household FIES, moderate or severe (SDG 2.1.2); "skipped a meal" items | **Local outcome** | Household → barangay → city/municipality → province | 2022 (participating LGUs); 2024 (POPCEN-CBMS) | 2024 fieldwork 15 Jul–16 Sep 2024 (SUMMARY); turnover to LGUs during 2025 (READ, deck) | Held by the LGUs; PSA RSSO IV-A presents results | Indicator READ; coverage BLOCKED |
| S3 | 2023 NNS (DOST-FNRI) | Household FIES | **Provincial outcome** (if domain estimates are released) | 117 domains: 81 provinces, 33 HUCs, 3 other areas | 2023–2024 fieldwork | National results 2024 (SUMMARY) | Microdata by request or PUF; FOI requests to FNRI exist | Design SUMMARY; overview PDF image-only (BLOCKED) |
| S4 | ENNS 2018/2019/2021 food security component (DOST-FNRI) | Household HFIAS | Provincial outcome, **2021 round only** | Rolling design: 8 of 24 replicates of the 117 domains per year | Only domains in the 2021 round (fieldwork Jul–Dec 2021 and Feb–Jun 2022) | Provincial dissemination fora Nov–Dec 2022 (SUMMARY) | Public-use file on eNutrition, mixed years | Design READ; which year each CALABARZON domain was surveyed: **not established** |
| S5 | PSA Official Poverty Statistics | Subsistence (food-poverty) incidence | **Official food-related outcome** (income-based, not FIES) | Province | 2021, 2023 (and later full-year rounds) | 2023 full year released by RSSO IV-A (date to verify) | Public tables (psa.gov.ph refuses automated access) | SUMMARY |
| S6 | PSA Labor Force Survey | Unemployment rate | Signal | Province (annual) | Annual 2021–2025 | Annual provincial release, preliminary then revised | Public | SUMMARY |
| S7 | DSWD DROMIC / NDRRMC situation reports | Affected families and persons per event | **Signal** (shock exposure) | Region → province → municipality, barangay | Event-based, 2021–2026 | During or right after each event | Public PDFs | SUMMARY |
| S8 | PSA CPI for the bottom 30% of income households | Price index for poor households | Signal | National, regional | Monthly | Monthly release | OpenSTAT | Not used. **Contamination source** (H2-2026 values seen). |
| S9 | PSA provincial food CPI (OpenSTAT) | Food inflation | **Current D input** | Province | Authorized through June 2026 | Monthly | OpenSTAT | Authorized and pinned in E25 |
| S10 | FAO FIES (Gallup World Poll) | Individual FIES | — | National | Annual | SOFI report | FAO catalog | SUMMARY. FAO advises against sub-national disaggregation, so **not useful**. |

## Details and provenance

### S1. SWS hunger: the current outcome, and why its sample size matters

**READ.** Source: PIDS SERP-P record of Mangahas, M. K. and Torres, C. B. (2024), "The SWS surveys of Philippine hunger 1998–2024", *Asian Journal of Agriculture and Development* 21(2): 85–92, <https://serp-p.pids.gov.ph/publication/public/view?slug=the-sws-surveys-of-philippine-hunger-1998-2024>.

- **Measure:** "involuntary hunger—being hungry and not having anything to eat—at least once in the past three months".
- **Consistency:** quarterly surveys whose methodology "has been standard and consistent over time".
- **Areas:** four (NCR, Balance Luzon, Visayas, Mindanao). **No CALABARZON or provincial breakdown.**
- **Raw data:** datasets are "archived without permanent embargo period and are open to academic researchers".

**SUMMARY (unverified).** Search engine summary of SWS media releases.

- The Balance Luzon subsample was **300** respondents in the fourth quarter of 2023 (±5.7% margin) and **600** in the first quarter of 2025 (±4%).
- One example shows a release about one month after fieldwork.

**Why it matters:**

- If the sample size changed inside the window, the survey-noise share of a change lies between 0.29 and 0.58 (`ROOT_CAUSE_ANALYSIS.md`, cause 3).
- PCF currently assumes 600 for every round. The engine now accepts a verified per-round `n_respondents` column (`backend_dev/app/quarterly/pcf_engine.py`); without it, the output states that 600 is assumed.

**Publication timing in the authorized data:**

- 2021–2025 rounds have verified publication dates.
- The March and June 2026 rounds have only an upper bound (2026-09-10).

### S2. CBMS 2022 and 2024: the only source with many local units

**READ.** Text extracted from a PSA presentation at the 2024 PSAI conference (35 slides, dated 2024-09-11), <https://www.events.psai.ph/2024/ac/ppt/PS_1B.1_ppt.pdf>.

- **The CBMS indicator list includes:** "Prevalence of moderate or severe food insecurity among households, based on the Food Insecurity Experience Scale (FIES)" (SDG 2.1.2).
- **The FIES items** refer to the past 12 months ("In the past 12 months did you or any adult household member… (due to lack of resources)").
- **Example tabulations by municipality and barangay** are labelled "Source: 2022 Community-Based Monitoring System, Philippine Statistics Authority and Municipality of Libjo, Dinagat Islands". This shows that LGU and barangay aggregates are produced.
- "The PSA is currently conducting the 2024 POPCEN-CBMS. By 2025, CBMS data will be turned over to our local government units (LGUs)."

**SUMMARY (unverified).**

- **Legal basis:** RA 11315 mandates CBMS every three years, with each LGU as the primary data-collecting authority.
- **Fieldwork:** 2024 POPCEN-CBMS fieldwork ran 15 July–16 September 2024.
- **RSSO IV-A results presentations:**
  - 2024 preliminary results to Malvar, Batangas (17 September 2025);
  - presentations to San Andres and Calauag, Quezon;
  - a 2022 CBMS data turnover to Tayabas City, Quezon.
- **Questionnaire:** the 2024 CBMS household questionnaire's food security section (G01–G08) is known only from a third-party transcript.

**BLOCKED.** The PSA list of LGUs that took part in CBMS 2022 (<https://psa.gov.ph/cbms/list-of-participating-lgu>) returned HTTP 403. Not bypassed.

**Gaps:**

- Which of the 142 CALABARZON LGUs have 2022 and 2024 FIES aggregates.
- The FIES scoring method used (raw-score cut-offs or the Rasch-based FAO method).
- Whether LGUs will release municipal aggregates.

### S3. 2023 National Nutrition Survey (FNRI)

**SUMMARY (unverified).**

- FIES was collected in 117 areas (81 provinces, 33 HUCs, 3 other urban areas) in 2023–2024.
- About 384 households were targeted per area, for national and regional estimates.
- National moderate-or-severe prevalence was 31.4%.
- A news report says CALABARZON had the lowest regional rate.
- PSA SDG Watch attributes indicator 2.1.2 to FNRI-DOST's ENNS/NNS.

**Sources:**

- FNRI summit announcement: <https://fnri.dost.gov.ph/index.php/programs-and-projects/news-and-announcement/880-dost-fnri-presents-the-latest-ph-nutrition-situation>
- 2024 summit deck: <https://enutrition.fnri.dost.gov.ph/uploads/2024%20National%20Nutrition%20Summit_Part%201.pdf>
- SDG Watch Goal 2: <https://psa.gov.ph/system/files/phdsd/Goal%202_as%20of%2028%20Feb%202025.pdf>

**BLOCKED (image-only).** The official overview PDF (<https://enutrition.fnri.dost.gov.ph/images/nns-2023/1.%202023%20NNS%20-%20Overview.pdf>) holds two image pages with no extractable text.

**Gap.** Whether FNRI publishes or releases **province-level** FIES estimates for Batangas, Cavite, Laguna, Quezon, Rizal and Lucena City, and with what standard errors.

**Note on the Chapter I anchor.** Objective 5 names "DOST-FNRI NNS 2019 and 2023 CALABARZON prevalence figures". **NNS 2019 is outside the 2021–2026 study window and is not used** (`ADVISER_APPROVAL_REQUEST.md` R4).

### S4. ENNS food-security public-use file (FNRI)

**READ.**

- **eNutrition PUF page** (<https://enutrition.fnri.dost.gov.ph/puf-preview.php?xx=2018747>): "2018, 2019, & 2021 ENNS - Food Security Survey Component", using the "Household Food Insecurity Access Scale (HFIAS)". Access conditions are not stated on the page.
- **Metadata documentation** (<https://enutrition.fnri.dost.gov.ph/download.php?path=uploads%2F2018-19-21_Metadata_Documentation_CLINICAL.pdf&type=puf>; text extracted with pdfminer):
  - a rolling design: 117 PSA domains in 24 replicates, 8 replicates allocated per year;
  - the 2021 round covered 37 provinces and HUCs, with fieldwork July–December 2021 and February–June 2022;
  - the domain list includes CALABARZON's Batangas, Cavite, Laguna, Quezon Province and Lucena City (and Rizal).

**Gap.** Which CALABARZON domains fall in the 2021 round. Domains surveyed in 2018 or 2019 are **pre-window and must never be used**.

**Rule.** The PUF mixes years, so it may be supplied only as an extract holding **2021-round domains only**. A mixed file is refused, never filtered.

### S5. PSA subsistence incidence by province

**SUMMARY (unverified).** RSSO IV-A release "2023 Full Year Poverty Statistics: CALABARZON" (<https://rsso04a.psa.gov.ph/content/2023-full-year-poverty-statistics-calabarzon>).

- Regional subsistence incidence among the population was 1.4% in 2023, about 237.8 thousand people.
- Rizal had the highest subsistence incidence in the region and Cavite the lowest.
- Quezon improved significantly from 2021 to 2023.

**Gaps.** The provincial values, their coefficients of variation and the release date need the official PSA tables. psa.gov.ph refuses automated access (E24, E25); not bypassed.

**What it measures.** This is **income-based food poverty**, an official food-related outcome. It is not experience-based food insecurity.

### S6–S7. Signals: provincial labor market, and disaster exposure

**SUMMARY (unverified).**

- **LFS:** an annual provincial release exists. CALABARZON unemployment was 5.4% in 2023; Rizal had the highest provincial rate. These are preliminary figures, revised in later releases.
- **DROMIC/NDRRMC:** event reports carry provincial and municipal tables. Examples: the Typhoon Tino report of November 2025 (<https://dromic.dswd.gov.ph/wp-content/uploads/2025/11/DSWD-DROMIC-Report-23-on-the-Effects-of-Typhoon-Tino-as-of-14-November-2025-6PM-.pdf>), Kristine/Leon 2024 and Aghon 2024.

**Role.** Both are **signals**: candidate leading indicators of regional hunger changes. They are never outcomes. E25 found that 2021–2025 government indicators carry no anticipatory signal for H. DROMIC has not been tested.

## What the investigation establishes

1. **There is no official quarterly food-insecurity outcome below the SWS area level.** Every local outcome is annual, biennial or triennial: CBMS 2022/2024, NNS 2023, ENNS 2021 round, and subsistence incidence 2021/2023. So **no source can add quarterly evaluation dates for provinces**. Local outcomes can validate the **cross-sectional ordering** (Objective 3), and, where two waves exist, the **direction of change** per LGU or province.
2. **CBMS is the only source with enough units for a powerful local validation** (142 LGUs; `runs/local_power.json`):

   | Units | Spearman needed for one-sided p < 0.05 | Power at true ρ = 0.5 | Power at true ρ = 0.9 | Smallest ρ with 80% power |
   |---|---|---|---|---|
   | 5 provinces | ≥ 0.90 | 0.17 | 0.60 | none up to 0.9 |
   | 6 FNRI domains | ≥ 0.83 | 0.15 | 0.65 | none up to 0.9 |
   | About 30 LGUs (one province) | — | 0.85 | 1.00 | 0.5 |
   | 75 LGUs | — | 1.00 | 1.00 | 0.3 (power ≈ 0.80) |
   | 142 LGUs | — | 1.00 | 1.00 | **0.3** (power 0.97) |

3. **The SWS sample size per round must be verified.** It changes how much of each observed hunger change is noise. The engine is ready to use it.
4. **SWS microdata** may allow a CALABARZON-only tabulation. Whether region codes exist and how many respondents CALABARZON has per round are **unknown**. A CALABARZON subsample is smaller than Balance Luzon, hence noisier, and using it would change the approved target's H (adviser approval).
