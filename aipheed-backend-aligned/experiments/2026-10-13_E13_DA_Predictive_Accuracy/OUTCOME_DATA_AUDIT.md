# Outcome Data Audit (E13, 2026-10-13)

**Purpose.** This audit lists every official outcome that could show whether aiPHeed predicts food insecurity in Cavite, Laguna, Batangas, Rizal and Quezon. It was completed **before** the experiment protocol was frozen and before any model or baseline was compared.

**Sources used for this audit:**

1. **Allowlisted project files,** read through the E13 guard. The structure and values are in `runs/inspect_20261013T022045Z/input_inventory.json`.
2. **Project code and documents** (read as text):
   - `app/ml/corpus/enns_fetcher.py`
   - `app/ml/corpus/psa_subsistence_fetcher.py`
   - `app/ml/corpus/lgu_poverty_fetcher.py`
   - `app/ml/features/label_generator.py`
   - `docs/DATA_AVAILABILITY.md`
   - the E9 data-eligibility document
3. **Two web searches restricted to the DOST-FNRI domains,** about ENNS provincial estimates. No PSA, SWS or RSSO page was searched or opened. Search summaries are **not verified against the primary tables.**

## 1. Summary

| # | Source and measure | Five-province coverage | Level in the project | Period in window | Frequency | Independent observations, 2021–2025 | Independent of predictors and S1? | Suitability |
|---|---|---|---|---|---|---|---|---|
| 1 | **SWS** involuntary hunger (total), Balance Luzon | All five fall inside Balance Luzon, but there is **no provincial value** | Survey stratum wider than CALABARZON | 2021-Q2 to 2025-Q4 (none in 2021-Q1, 2022-Q1) | Quarterly rounds | **18 quarterly values** (21 rounds), shared by all five provinces | Independent of provincial CPI. **Not independent of S1** (it is S1's H term). | **Regional** training and validation. Provincial context only. |
| 2 | **DOST-FNRI NNS/ENNS FIES**, moderate or severe household food insecurity | Region only. The project file **copies the regional value into five provincial rows** (`geographic_level = region_inherited`) | Region IV-A | 2025 only (2021 and 2023 removed as unverifiable on 2026-09-01) | Irregular (2018, 2019, 2021 rolling ENNS; 2023, 2025 NNS) | **1 regional value** (22.6%) | Yes | **Context only** |
| 3 | **PSA subsistence incidence** among families (income below the food threshold) | **Yes:** all five provinces and the region | Province, region | 2021, 2023 (2018 exists but is outside the window and was not loaded) | Triennial (2018, 2021, 2023; 2025 released 2026-08-21, **not in the project files**) | **10 provincial values** (5 × 2) and 2 regional | Yes (income survey) | **Descriptive external comparison only.** Provincial CV is 17.3–53.3%. |
| 4 | **PSA 2021 small-area poverty estimates** (municipal or city) | All five provinces, 142 LGUs | LGU, but only **3–5 distinct values per province**; many rows are province-mean fallbacks | 2021 | One-off | 1 cross-section (effectively about 5 provincial values) | Yes | **Context only** (household vulnerability, not food insecurity) |
| 5 | **PSA provincial food CPI**, year-on-year (F) | **Yes:** all five, complete | Province | 2021-Q1 to 2025-Q4 | Monthly, used quarterly | 100 province-quarters (20 × 5). Strongly correlated across provinces and over time, so the effective number is far smaller. | **No.** It is S1's provincial input (D = F − five-province mean). | Training and validation for **food-price pressure only.** **Not a food-insecurity label.** |
| 6 | **S1** = H + 2D (aiPHeed's Equation 3) | All five | Province | 16 labelled quarters | Quarterly | 80 rows, but its HIGH/LOW mainly restates one regional value per quarter | **Constructed from items 1 and 5** | **Not an independent outcome** |
| 7 | **DA:** price monitoring, production, sufficiency | Some provincial series exist outside the project | — | — | — | 0 in the project | — | Possible **predictors**, not food-insecurity outcomes |
| 8 | **DSWD:** Listahanan, 4Ps, Walang Gutom, DROMIC | Administrative; not in the project | — | — | — | 0 | Driven by programme decisions | **Not a prevalence outcome** without access and definitions |
| 9 | **PSA CBMS** household food-shortage items | Municipal or barangay rollout from 2022; CALABARZON coverage **not verified** | — | — | Irregular | 0 in the project | Yes | **Candidate future outcome** (needs acquisition) |
| 10 | **NNC Operation Timbang Plus** (child undernutrition) | Provincial and municipal, annual; not in the project | — | — | Annual | 0 | Yes | Nutrition, **not food insecurity**. Supporting at most. |

## 2. Details by source

### 2.1 SWS hunger (Balance Luzon): the only repeated, independently measured hunger outcome

- **What it measures:** the share of families who experienced involuntary hunger at least once in the past three months, as self-reported in a national survey. The value used is for the **Balance Luzon** stratum (Luzon outside Metro Manila).
- **Rounds in the window:** 21 rounds, mapped to 18 fieldwork quarters as E12 assigned them.
  - **18 rounds** come from the production series (`definition_A = True`).
  - **3 rounds** come from the 2026-10-09 supplementary collection: 2025-Q2 (two rounds) and 2025-Q3.
  - `docs/DATA_AVAILABILITY.md` records 2025-Q2 and 2025-Q3 as having **no** published round. The later collection found rounds for both quarters. The two records disagree. E13 treats the supplementary rounds as eligible and adds a sensitivity analysis without them.
- **Publication dates:** all 21 have a publication date. 18 are `verified` and 3 are `verified-single`. Where the fieldwork dates are recorded, a round was published between about 10 days after fieldwork (the March 2025 Stratbase-SWS round) and about 3.5 months after. The last eligible round (2025-Q4) was published on 2026-01-14.
- **Independence:**
  - It is measured separately from the provincial CPI.
  - It is the H term of S1. Any S1-based target therefore contains it.
- **Geography:** one value per quarter. Repeating it five times does **not** create provincial observations.
- **What it supports:** quarterly forecasting of **regional** hunger. It gives no provincial accuracy.

### 2.2 FNRI FIES (NNS 2025): regional, single value, secondary source

- **What it measures:** the FAO Food Insecurity Experience Scale (moderate or severe), household level. This is the SDG 2.1.2 indicator.
- **Value in the project:** CALABARZON 22.6% for 2025. The national value is 32.6% (severe 2.9%).
  - The source is a press report of the regional table (explained.ph). The project note says the data were presented at the 2026 National Nutrition Summit and released on 17 June 2026.
  - The primary FNRI table has not been obtained.
- **The project file is unsafe as a provincial outcome.** `nns_fies.parquet` stores the regional 22.6% five times, once per province, with `geographic_level = region_inherited`. Using these rows as provincial outcomes would turn one regional observation into five. **E13 uses only the single regional value.**
- **Earlier cycles:** the 2021 and 2023 CALABARZON values were removed on 2026-09-01 as unverifiable. FNRI's search results show a national 2021 ENNS value of 33.4% (95% CI 30.1–36.6).
- **Provincial FNRI data (not in the project):**
  - **Design:** the 2018, 2019 and 2021 ENNS used a rolling design over 117 provinces and highly urbanized cities. FNRI's metadata documents provincial sampling weights.
  - **Dissemination:** FNRI held provincial dissemination fora for the 2019 ENNS, including Rizal and Quezon (October 2020).
  - **Coverage:** each province appears **once** across 2018–2021. The 2018–2019 food-insecurity component relied mainly on HFIAS, not FIES.
  - **The 2023 NNS:** it targets national and regional estimates.
  - **Status:** these provincial values would need to be computed from public-use microdata or requested from FNRI. They are mostly **before the 2021–2026 window**. They give at most one cross-section per province, not a time series.

### 2.3 PSA subsistence incidence (provincial, triennial)

The 2018 rows exist in the file but were filtered out at read time.

| Year (release) | Area | Subsistence incidence, % | CV, % | 95% CI | CV < 30? |
|---|---|---|---|---|---|
| 2021 (2022-08-15) | Batangas | 0.6 | 34.8 | 0.2–1.1 | No |
| | Cavite | 1.5 | 31.6 | 0.6–2.5 | No |
| | Laguna | 1.5 | 24.3 | 0.8–2.2 | Yes |
| | Quezon | **4.7** | 17.3 | 3.1–6.3 | Yes |
| | Rizal | 0.6 | 34.2 | 0.2–1.0 | No |
| | Region IV-A | 1.6 | 12.3 | 1.2–2.0 | Yes |
| 2023 (2024-08-15, news-sourced date) | Batangas | 0.8 | 33.9 | 0.3–1.3 | No |
| | Cavite | 0.4 | 53.3 | 0.0–0.8 | No |
| | Laguna | 0.8 | 35.0 | 0.3–1.4 | No |
| | Quezon | 0.5 | 38.5 | 0.1–0.9 | No |
| | Rizal | 1.5 | 24.5 | 0.8–2.3 | Yes |
| | Region IV-A | 0.8 | 15.8 | 0.6–1.0 | Yes |

- **What it measures:** families whose per-capita income is below the cost of a basic food basket. It is **income-based food poverty, not experienced food insecurity.**
- **Reliability:** only 3 of the 10 provincial values have CV below 30%. In 2023 the provincial confidence intervals overlap almost completely. Quezon in 2021 is the only provincial value clearly above the others.
- **Timing:** two observations per province in the window, each published about 8 months after its reference year. **It cannot support quarterly training or validation.**
- **Use in E13:** a descriptive, cross-sectional comparison with each province's food-price pressure in the same year. No inference is drawn.

### 2.4 PSA 2021 municipal poverty (small-area estimates)

- 142 LGU rows, all with reference year 2021 (released 2024).
- Each province has only 3 to 5 distinct values. Source notes mark many rows as **province-mean fallbacks** ("LGU SAE not in table").
- **Provincial medians of the LGU values:**

  | Province | Median, % |
  |---|---|
  | Quezon | 16.8 |
  | Batangas | 7.1 |
  | Cavite | 4.3 |
  | Laguna | 4.2 |
  | Rizal | 3.5 |

- **What it is:** poverty, which is household vulnerability. It is not food insecurity, and it is a single year. **Context only.**

### 2.5 Provincial food CPI (F) and D

- **Coverage:** complete for all five provinces in all 20 quarters, 2021-Q1 to 2025-Q4.
- **Release dates are proxies:** national release + 14 days, unverified except 2024-Q4. Because a quarter's last month ends the day before the next quarter starts, **F for quarter T−1 cannot be published before the origin of T.** F for T−2 was released about 10 weeks before that origin in every case E9 documented.
- **Revisions:** the stored values are the current vintage. Real-time vintages were not reconstructed.
- **What it supports:** forecasting **food-price pressure** (F) and **relative food-price pressure** (D). PSA measures both independently, but **neither is food insecurity.**

### 2.6 DA and DSWD

- **DA:** no DA dataset in the project records measures food insecurity. DA price monitoring and production statistics describe supply and prices. They are candidate **inputs**, not outcomes.
- **DSWD:** registries and programme data (Listahanan, 4Ps, Walang Gutom, DROMIC) record eligibility or programme reach. They depend on programme decisions and coverage. They do not measure prevalence. None are in the project.

## 3. Conclusion

1. **No independent provincial food-insecurity outcome with repeated observations exists in the project data for 2021–2025.**
   - The only provincial FIES-type values found are FNRI's 2018, 2019 and 2021 rolling-ENNS cross-sections. They are not in the project, are mostly pre-window, and give one value per province.
   - The provincial FIES rows in `nns_fies.parquet` are copies of one regional value.
2. **Actual provincial food-insecurity prediction accuracy therefore cannot yet be established.** No re-weighting, re-thresholding or new model can change this, because there is nothing provincial to score against.
3. **What can be evaluated defensibly:**
   - **Target A:** forecasting **regional hunger** (SWS Balance Luzon), with 18 quarterly observations. At most 9 quarters are testable after a minimum training history. These quarters were all examined in earlier experiments.
   - **Targets B1 and B2:** forecasting **provincial food-price pressure** (F) and **relative pressure** (D), with 20 quarters × 5 provinces. This is price pressure, not food insecurity.
   - **Descriptive comparisons** against provincial subsistence incidence (2021, 2023) and the single 2025 regional FIES value.
4. **Minimum data needed to evaluate provincial food-insecurity accuracy:** a provincial food-insecurity measure (FIES or HFIAS type, or a CBMS food-shortage item) for all five provinces, with the following properties:
   - repeated at least yearly, and preferably for at least 5 to 8 periods;
   - documented sampling error;
   - known publication dates;
   - not derived from aiPHeed's own inputs.
