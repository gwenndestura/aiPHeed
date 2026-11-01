# v6 Stage 0: Construct validity (what is "food insecurity" here?)

**Tags:**
- VERIFIED: checked this session (web source fetched or searched, URL given; or repository file read);
- UNVERIFIED-CITATION: not checked this session, so nothing relies on it;
- INFERRED.

**Session note:** no SWS web pages or SWS searches were opened. This follows the standing owner rule (memory "E27: no more SWS web searches"; protected-exposure lesson): a search could reveal 2026-H2 releases, which are sealed confirmation data. SWS facts below come from SWS URLs recorded in `backend/data/forecasting/sws_area_rounds.csv` and E110 documents.

## 1. Candidate measures

### 1.1 FAO FIES / SDG 2.1.2 (moderate or severe food insecurity)

| Property | Value | Source |
|---|---|---|
| What it measures | Experience-based food insecurity: 8 yes/no items over the last 12 months (worry about food; unable to eat healthy food; few kinds of food; skipped a meal; ate less; ran out of food; hungry but did not eat; whole day without eating). Rasch-scaled to a global reference; prevalence of moderate+severe and of severe. | VERIFIED: UN SDG metadata 2.1.2 (custodian FAO), https://unstats.un.org/sdgs/metadata/files/Metadata-02-01-02.pdf ; item list per the World Bank microdata catalogue (https://microdata.worldbank.org/catalog/8582). Exact item wording was not checked against FAO's own questionnaire (summary only). |
| Population, geography, frequency | Individuals or households. National through the Gallup World Poll, or any national survey that fields the FIES module. Annual or irregular. | VERIFIED (same metadata) |
| Philippines / CALABARZON data | DOST-FNRI ENNS fields FIES (region; Batangas and Cavite 2021, per DATA_INVENTORY). PSA FIES 2023 public-use file has **no FIES items** (memory, E129/E130). CBMS 2024 FIES items: provincial/LGU, not held. | INFERRED from repository documents |
| Validity for the thesis construct | **Highest:** the international standard for food insecurity | — |
| Usable as a Lead-2 target? | **No:** no quarterly series exists | — |

### 1.2 SWS involuntary hunger (current target)

| Property | Value | Source |
|---|---|---|
| What it measures | Share of families reporting experienced involuntary hunger ("hunger and nothing to eat") at least once in the past 3 months: an experiential, severe-end food-insecurity item, close to FIES items 7–8 (INFERRED) | SWS release URLs in `sws_area_rounds.csv`. The **exact question wording was not checked this session: UNVERIFIED-CITATION**, not relied on. |
| Population, geography | Families (household heads; respondent base changed to adults in 2025-Q2, recorded in the file). 4 areas: Metro Manila, Balance Luzon (CALABARZON is one of its 7 regions), Visayas, Mindanao. | VERIFIED (repository file) |
| Frequency, history | Quarterly; 23 non-commissioned rounds 2021-Q2 … 2026-Q3; no round in 2022-Q1 or 2025-Q1 | VERIFIED (file) |
| Sample size, margin | 300–1 080 per area; ±3 to ±6 pp. 8 early margins were assumed (v3 Task 1). | VERIFIED (file) / NOT VERIFIED for the 8 rounds |
| Release lag | Median 32 days after quarter end | VERIFIED (DIAGNOSIS Q4) |
| Validity | Direct and experiential, but **severe end only, and regional (Balance Luzon), not CALABARZON or provincial** | INFERRED |
| Claim it supports | "Balance Luzon (and other SWS area) involuntary hunger incidence" | — |

### 1.3 PSA subsistence (food-poverty) incidence

| Property | Value | Source |
|---|---|---|
| What it measures | Share of people or families whose income is below the food threshold, i.e. **cannot afford basic food needs**. Provincial food thresholds are used for provincial estimates. | VERIFIED: PSA 2023 Full-Year Poverty Statistics press release, https://psa.gov.ph/system/files/phdsd/Press%20Release_2023%20Full%20Year%20Poverty%20Statistics.pdf (via search summary) |
| Geography, frequency | National, region, province; triennial (2021, 2023) | VERIFIED (repository file `psa_food_threshold_subsistence_2021_2023.csv`) |
| Precision | CALABARZON provinces CV 24–62 % | VERIFIED (same file) |
| Validity | Income-based food poverty, not experienced food insecurity; a related construct | INFERRED |
| Claim it supports | "Provincial food-poverty incidence in 2021 and 2023" (very imprecise) | — |

### 1.4 IPC / CH acute food insecurity phases

| Property | Value | Source |
|---|---|---|
| What it measures | 5-phase area classification (1 Minimal, 2 Stressed, 3 Crisis, 4 Emergency, 5 Famine). An area is in a phase when ≥ 20 % of its population meets that phase or worse. Manual v3.1 added FIES to the reference table. | VERIFIED: IPC Technical Manual 3.1 (IPC Global Partners 2021), via search summary of https://www.fsinplatform.org/sites/default/files/resources/files/IPC_Technical_Manual_3_Final_0.pdf and https://fews.net/about/integrated-phase-classification |
| Philippines | No IPC acute analysis of CALABARZON is held in the repository (NOT VERIFIED whether one exists) | — |
| Validity | High for crises, but a classification, not a quarterly numerical score | INFERRED |

### 1.5 Predictors and context (never ground truth)

CPI and rice prices, FIRI, P0H4, poverty incidence, LFS, climate, and news (FSSI/GDELT) are **predictors or context only**. Lock and DATA_INVENTORY roles are unchanged.

## 2. Gate 0: construct decision

1. **The thesis construct** is "food insecurity in CALABARZON" (provinces/LGUs), forecast numerically two quarters ahead.
2. **No available measurement represents that construct at that resolution and frequency** (INFERRED from the tables):
   - FIES-based measures (the construct's standard) have no quarterly CALABARZON series;
   - SWS hunger is quarterly but regional (Balance Luzon) and severe-end;
   - PSA subsistence is provincial but triennial and imprecise.
3. **Primary target: SWS involuntary hunger by SWS area.** It is the only quarterly experiential food-insecurity measurement, which a Lead-2 forecast requires.
   - **Claim scope:** "Balance Luzon (containing CALABARZON) involuntary hunger incidence", **never** "CALABARZON provincial food insecurity".
   - The other 3 areas are separate measurements, used to pool dynamics, not as CALABARZON.
4. **Validation tracks** (separate, not targets):
   - FNRI ENNS FIES (region);
   - CBMS 2024 FIES (provincial/LGU, when obtained);
   - PSA subsistence incidence (provincial, triennial).
5. **Ranked alternatives if "CALABARZON food insecurity" must be represented directly:**
   1. CBMS 2024 FIES: provincial/LGU cross-section; no forecasting, but valid ground truth for the geography layer.
   2. FNRI ENNS FIES for Region IV-A: regional, irregular.
   3. PSA subsistence incidence by province: 2 points per province, CV up to 62 %.

   **None supports a quarterly Lead-2 forecast** (INFERRED).

**Gate 0 status: PASSED, with a restricted claim.**
- The Lead-2 numerical objective can be pursued only as SWS area hunger.
- The thesis objectives' provincial wording ("CALABARZON provinces") is **not** representable by any measurement held. This is a decision for the owner and adviser (FINAL_REPORT).
