# Outcome data feasibility: is there a valid food-insecurity outcome for a Lead-2 forecast?

**Branch:** `aiPHeed/forecast-research`. **Date:** 2026-10-27/28. **Register:** `OFFICIAL_OUTCOME_SOURCE_REGISTER.csv` (O1-O15).

**Scope.** Every source below was checked for five things: what it measures, the geography, the years inside the study window (2021-2026), the frequency, and whether the project can actually get it. No value for a quarter after 2026-Q3 was looked up.

## 1. Status of the existing requests (E87 `DATA_REQUESTS.md`)

| Request | Agency and dataset | Status found |
|---|---|---|
| A | PSA CPCD: CBMS 2024 aggregates for the 142 CALABARZON LGUs | **Drafted 2026-10-21, never sent.** No reply exists anywhere in the repository. E112 and the E83/E87 consolidated report also record it as "drafted, not sent". |
| B | DOST-FNRI: provincial FIES for Laguna, Quezon and Rizal, plus 2023/2025 provincial domains and quarter-of-interview tables | **Drafted, never sent** |
| C | SWS Survey Data Library: hunger item for CALABARZON respondents, 2021-2026 | **Drafted, never sent** |

**Nothing was sent in this session.**
- A request is a message on the researchers' behalf and needs their names, signatures, the adviser and the ethics documents.
- The government portals could not be reached today:
  - FNRI eNutrition: "Service Temporarily Unavailable";
  - eFOI: "Maintenance";
  - PSA regional sites: a bot-verification wall, which I did not try to get past.
- **No direct agency confirmation exists yet.** Every PSA fact below marked "record" comes from PSA's own pages as indexed by a search engine, not from reading the page itself.

## 2. What each candidate dataset can and cannot do

### 2.1 PSA CBMS 2024 (O8): the strongest candidate, but one cross-section

| Item | Finding | Basis |
|---|---|---|
| Indicator | **SDG 2.1.2.p1, "Prevalence of moderate or severe food insecurity among households, based on the Food Insecurity Experience Scale (FIES)"**: the 8 FAO items, from "worried you would not have enough food" to "went without eating for a whole day" | PSA CBMS slides, PSAI 2024 annual conference (read 2026-10-28; SHA-256 1e343f2e) |
| Reference period | 12 months: 1 July 2023 - 30 June 2024 | Record: PSA RSSO Caraga 2024 CBMS highlights for Cabadbaran City |
| Geography | Barangay and city/municipality. It is a census of households, so all 142 CALABARZON LGUs if released. | CBMS Act (RA 11315); PSA slides |
| Release in CALABARZON | Preliminary results presented to LGUs (e.g. San Andres, Quezon, 2025-09-10; Batangas LGUs). Data turned over to Laguna municipalities in April 2026. | Records of PSA RSSO IV-A pages |
| Researcher access | LGUs get their own data (RA 11315 §8). The PSA privacy notice says aggregate statistics will be "readily accessible to public users and researchers", but no published aggregate table for CALABARZON was found. PSA's FOI replies send CBMS requests to CPCD. | Records of the PSA CBMS privacy notice and the eFOI pages |
| Frequency | One round with a 12-month recall. No later round is scheduled in any source found. | — |

**What it can support.** One measured outcome per LGU and per province for July 2023-June 2024. It can test whether the province class, or the LGU priority ranking, matches measured household food insecurity in that window.

**What it cannot support.** Any quarterly Lead-2 evaluation. A single 12-month window is one observation per unit, not a series. Turning it into quarterly labels would mean interpolating or repeating the value, which this mission forbids.

### 2.2 DOST-FNRI ENNS / NNS (O3-O7)

| Round | CALABARZON coverage | Value |
|---|---|---|
| ENNS 2018, 2019 (rolling) | 1 province (2018), 2 provinces (2019) | Before 2021: outside the study window |
| ENNS 2021 | **2 provinces + 1 HUC**: Batangas, Cavite, City of Lucena (design slide "Total number of provinces and HUCs covered in 2021") | Batangas 29.7%, Cavite 31.7%, Lucena 26.2% moderate-or-severe (90% CIs overlap); FIES 8 items, 12-month recall |
| ENNS 2022 | 20 provinces/HUCs nationwide, July-December 2022 (PSA clearance record). Whether Laguna, Quezon or Rizal are among them is **unverified** (FNRI site down). | — |
| NNS 2023 | Region only (n = 1,752 households) | 19.1% [16.9, 21.3] |
| 2025 Updating Survey | Region only, population basis | 22.6% |

**Read directly from the original FNRI documents** held locally from E87 (2026-10-28): the FIES method (8 items, 12-month recall, household level; Rasch model in 2025), the 2021 provincial coverage, the 2023 regional sample, and the 2025 value. I confirmed the 2025 CALABARZON value against the chart's text order.

**What it can support.** At most one provincial cross-section, and only for the provinces each rolling round covered, in different years. Annual regional values for 2023 and 2025. **No quarterly series exists.** A quarter-of-interview breakdown would need FNRI microdata (request B), and with about 1,500 households per domain it would give a few noisy semi-annual points at best.

### 2.3 SWS involuntary hunger (O1, O2): the only quarterly direct measure

**What it measures.** Experienced hunger with a 3-month recall, an access-dimension measure that agrees in direction with FNRI's FIES (FORECAST_RESEARCH_II §2.4).

**Its limits.**
- It is published for **Balance Luzon only**, the whole of Luzon outside NCR. It is not CALABARZON, and not a province.
- It comes from a private survey organisation, not a government agency.
- It has 20 in-window quarters with readings, each with a standard error of 1.3-2.3 points.

**Microdata (request C)** could give a CALABARZON series. By my estimate (from SWS's published Balance Luzon margins of error and CALABARZON's population share), that would be about 100-230 CALABARZON respondents per round and only about 20-75 per province. Provincial readings would carry standard errors of roughly 4-8 points, too noisy to label HIGH/LOW.

### 2.4 Other official sources

| Source | Why it does not qualify |
|---|---|
| **PSA APIS hunger item (O10)** | It asks whether the family experienced hunger with nothing to eat in the past 3 months (record of PSA's APIS definition). But the survey is annual (one July round), designed for national and regional estimates, and its microdata on PSADA run to 2022. It cannot give provincial or quarterly outcomes. |
| **PSA subsistence incidence (O11)** | An official provincial measure of food poverty (income below the food threshold) for 2021 and 2023. It measures income, not experienced food insecurity, and has only two time points. It is useful as a cross-sectional access comparator. Record: in 2023, Rizal had CALABARZON's highest subsistence incidence, while Rizal is never HIGH under T43c. |
| **PSA FIES 2023 (O12)** | The Family Income and Expenditure Survey. It has no food-insecurity items. |
| **OCTA (O13)** | Balance Luzon only, irregular, and agrees with SWS on the HIGH/LOW side in only 3 of 7 rounds |
| **FAO SDG 2.1.2 (O14)** | National 3-year averages only |
| **PSA small-area poverty 2021 (O15)** | Poverty, not food insecurity; it is already an input to the LGU ranking |

## 3. Feasibility verdict

| Requirement for a valid Lead-2 test | Met by any source? |
|---|---|
| Directly measured household food insecurity or hunger | Yes: CBMS 2024, FNRI FIES, SWS, APIS |
| At province level (the forecast's unit) | Only one-off cross-sections: FNRI 2021 for 2 provinces + Lucena (held); CBMS 2024 for all (not held) |
| Repeated at least quarterly, so a 2-quarter-ahead forecast can be scored many times | **Only SWS, and only for Balance Luzon** |
| At least 10 independent target quarters not already used in development | **None.** Every SWS quarter to 2026-Q3 has been examined; untouched quarters start with 2026-Q4 (published about January 2027). |

**There is no quarterly provincial or CALABARZON food-insecurity outcome, held or obtainable, that can test a Lead-2 forecast.**

The closest legitimate outcome is SWS Balance Luzon hunger. It is regional, so all five provinces share each reading and count as one observation per quarter, not five. It can only be tested prospectively, from 2027 onwards.

CBMS 2024 and FNRI provincial FIES can validate the *meaning* of the province class for one period. They cannot validate Lead-2 timing.

## 4. Recommended data actions (for the researchers to send; ready drafts in E87 `DATA_REQUESTS.md`)

1. **Send request A (PSA CBMS 2024) first.** Name the indicator exactly ("SDG 2.1.2.p1, moderate or severe household food insecurity, FIES, reference period 1 July 2023 - 30 June 2024") and ask for city/municipal and provincial aggregates with numbers of households. As a parallel route, ask the five Provincial Statistical Offices of RSSO IV-A, which have already presented the preliminary results to LGUs.
2. **Send request B (FNRI),** adding one question: were Laguna, Quezon or Rizal domains of the 2022 ENNS (July-December 2022)? If yes, ask for their FIES prevalence. The eNutrition site was down on 2026-10-27/28, so retry it before requesting.
3. **Request C (SWS microdata)** is worth sending only to build a CALABARZON regional hunger series. It will not give usable provincial labels.
