# v4 Step A: Target data options

**Tags:** VERIFIED (read from a repository file or computed, path given) / INFERRED / NOT VERIFIED. Nothing was downloaded or requested.

**The binding constraint:** the target is noisy and sparse.
- Lead 2 is a **quarterly** concept: target = dashboard quarter + 1.
- So only a measurement published at least quarterly can be a Lead-2 target.
- Everything else can only be a validation reference or a predictor.

## 1. Candidate measurements

| # | Measurement | What it measures | Geography | Frequency | History held (2021+) | Sample size | Published margin / error | Release lag | Access route | Independent Lead-2 target observations it adds |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | **SWS involuntary hunger** (current target) | % of families that experienced hunger in the past 3 months (experiential food insecurity) | 4 SWS areas; CALABARZON lies in Balance Luzon | Quarterly (no round in 2022-Q1 or 2025-Q1) | 23 rounds, 2021-Q2 … 2026-Q3 (VERIFIED, `backend/data/forecasting/sws_area_rounds.csv`) | 300–1 080 per area per round | ±3 to ±6 pp. 14 rounds recorded from SWS releases; 8 early rounds assumed ±6 (NOT VERIFIED; v3 Task 1) | Median 32 days after quarter end (VERIFIED, DIAGNOSIS Q4) | Public SWS releases (already held) | **4 rows per quarter** (1.17 design effect within a quarter): about 3.4 effective rows per quarter. All 2021–2026-Q3 rows are spent (development). |
| 2 | **PSA subsistence (food-poverty) incidence** | % of population below the food threshold (consumption-based) | Region and 5 provinces | Triennial (2021, 2023; 2025 provincial release NOT VERIFIED) | 2 rounds × 5 provinces (VERIFIED, `E131…/psa_food_threshold_subsistence_2021_2023.csv`) | FIES sample per province (not in the file) | Province CV 24–62 % (VERIFIED, same file): too noisy to rank provinces | About 1–2 years | PSA OpenSTAT (held) | **0:** no quarterly series, so Lead 2 is undefined |
| 3 | **PSA FIES 2023** (public-use file, Tables 7–8) | Income and expenditure; food shares by decile | Province / decile | Triennial | 2023 (DATA_INVENTORY) | National FIES | Not stated in the repo (NOT VERIFIED) | About 2–3 years | PSA microdata (memory: the PUF has **no FIES food-insecurity items**) | 0 |
| 4 | **DOST-FNRI ENNS food insecurity (FIES scale)** | % of households moderately or severely food-insecure (FAO FIES) | Region; Batangas and Cavite 2021 | Irregular (2021, 2023, 2025) | 3 rounds, region (DATA_INVENTORY) | ENNS sample | Not held (NOT VERIFIED) | About 1 year | FNRI reports / data request | 0 at Lead 2; validation reference |
| 5 | **CBMS 2024 FIES items** | Household food insecurity (FIES items), census-type | Province, municipality, barangay (142 LGUs) | One-off (2024; next round not scheduled in the repo) | Not held | Near-census | Small at province level (INFERRED: census-type) | NOT VERIFIED | Formal PSA / LGU request (v3 Task 5) | 0 at Lead 2. **Cross-sectional provincial/LGU truth for 2024**: the only route to a provincial or LGU claim. |
| 6 | **Regional quarterly LFS** (unemployment, underemployment) | Labour market, **not food insecurity** | 17 regions | Quarterly | National/regional series only, through E119 (`unemployment_rate_pct`, `E1_unemployment_change_pp`) | LFS sample | PSA published SEs (not held) | About 1.5 months | PSA OpenSTAT (download needed) | **Predictor only.** It adds no target observations. |
| 7 | OCTA hunger readings | Self-rated hunger | National | Irregular (9 readings; E133 D5) | Held in E133 | About 1 200 | ±3 pp | — | Public | Not an area series; 9 readings cannot support Lead 2 |

## 2. Ranking

**Criteria:**
- **(i) Noise floor:** the oracle bound at Lead 2 under the frozen tolerance.
- **(ii)** Independent test observations gained.
- **(iii)** Validity as actual food insecurity.

| Rank | Measurement | (i) Lead-2 oracle bound | (ii) Independent Lead-2 test observations | (iii) Validity | Role |
|---|---|---|---|---|---|
| 1 | **SWS hunger, 4 areas** | 0.43 (all-data dynamics) / 0.60 (calm regime), frozen tolerance; 0.59 / 0.78 under the published margin (VERIFIED, v3) | About 3.4 effective per future quarter; 0 unseen today | High: experiential hunger, measured | **Target** (the only quarterly food-insecurity measurement) |
| 2 | CBMS 2024 FIES | n/a (not a time series) | 0 at Lead 2; about 142 LGU cross-sections for 2024 | Highest for local food insecurity | Provincial/LGU **ground truth** for the geography layer |
| 3 | DOST-FNRI ENNS FIES | n/a | 0 | High (FAO FIES) | Validation reference |
| 4 | PSA subsistence incidence | n/a | 0 | Medium (food poverty, consumption) | Validation reference (CV 24–62 %) |
| 5 | Regional quarterly LFS | Would change the oracle only through a leading signal. National unemployment change: ρ ≈ 0.1 (DIAGNOSIS Q3). | 0 | Not food insecurity | **Predictor** candidate |
| 6 | PSA FIES 2023 PUF, OCTA | n/a | 0 | Low or partial | Context |

**Conclusion** (INFERRED from the VERIFIED table):
- **No held or obtainable measurement adds Lead-2 target observations faster than SWS does.** The test sample grows only as SWS publishes: about 4 area rows per quarter.
- Provincial measurements (CBMS, FNRI, PSA) can make the geography layer truthful, but they cannot create a Lead-2 test.

## 3. Access checklist (for you to authorise; nothing done)

| # | Item | Purpose | Steps | Needs |
|---|---|---|---|---|
| 1 | **SWS round documentation** (n, margin, design effect, 2021-Q2 … 2026-Q3) | Replace 8 assumed margins; fix the amended tolerance from measurement properties | Open each SWS release (URLs in `sws_area_rounds.csv` `source`) → copy "Survey Background"; ask SWS (Survey Data Library) whether design effects are published | Your authorisation to browse and email |
| 2 | **Regional quarterly LFS** | The only untested leading-signal predictor | PSA OpenSTAT → Labor and Employment → LFS → regional quarterly tables, 2021+ → CSV; record each PSA press-release date as the availability date | Download authorisation |
| 3 | **CBMS 2024 FIES** | Provincial/LGU ground truth | Formal request to the PSA (CBMS Service / RSSO IV-A), adviser-signed, with a data-privacy agreement; or each LGU's CBMS office | Request letter, adviser signature |
| 4 | **FNRI ENNS regional FIES tables** | Validation reference | FNRI ENNS reports, or a data request to DOST-FNRI | Request |
| 5 | **Each new SWS quarterly release** (2026-Q4 onward) | The sealed confirmation set | Append the round, with its URL, publication date, n and margin, to `sws_area_rounds.csv` → run `python -I backend/scripts/v4_score_sealed.py` | Routine; no authorisation beyond adding public data |
