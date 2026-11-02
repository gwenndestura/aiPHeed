# Direct food-insecurity labels for CALABARZON: acquisition, reconstruction and assessment (2026-11-03)

Only public online sources were used. No data were requested.

* **Originals:** unchanged in `backend/data/fi_labels/raw/`, listed with sha256 in `raw/MANIFEST.csv`.
* **Derived tables:** `backend/data/fi_labels/clean/`.
* **Code:** `backend/app/fi_labels/`. **Tests:** `backend/tests/unit/test_fi_labels.py` (17 pass).

## 1. Public dataset inventory and download record

| Source | What it contains | Status |
|---|---|---|
| FNRI 2015 Food Security Survey report (PDF, 116 pp.) | HFIAS food-security categories by region **and province**, with n, SE, 95 % CI and CV (Appendices 1–4) | **acquired** |
| FNRI 2023 NNS regional estimates (PDF, 58 pp.) | regional ranking of household food insecurity (p. 55) | **acquired** |
| FNRI 2023 NNS "Household and Food Security" release (PDF, 2 pp.) | moderate-to-severe household food insecurity by region with 95 % CI | **acquired** |
| PSA OpenSTAT SDG 2.1.2.p1 (CSV via the PXWeb API) | FIES-based household moderate-or-severe food insecurity: national 2019 / 2021 / 2023, regions 2023 | **acquired** |
| FNRI ENNS 2018, 2019, 2021 Food Security Survey public-use file (`puf-dataset.php?xx=2018747`) | household HFIAS/FIES microdata | **not acquired**: the FNRI site firewall returned "Web Page Blocked! … Attack ID 20000007" to this network address in curl *and* in a real browser, later for the whole site. It was not bypassed |
| FNRI NNS 2015 public-use file (`xx=2015480`) | household HFIAS microdata | **not acquired** (same block) |
| FAO Philippines FIES microdata (catalogue 783) | Gallup World Poll 2015, national | **not acquired**: access is by contacting FAO (a data request). It is national only, and FAO discourages sub-national estimates |
| 2023 NNS household public-use file | — | **not verified** (catalogue unreachable). Only the published regional results were used |

Exact filenames, URLs, download date, bytes and sha256 are in `backend/data/fi_labels/raw/MANIFEST.csv`.

## 2. Labels (official method) and the reconstruction script

`app/fi_labels/hfias.py`:
* HFIAS score = the sum of nine frequency codes (0 never, 1 rarely, 2 sometimes, 3 often; past 30 days), ranging
  0–27.
* Categories follow the HFIAS Indicator Guide v3 (Coates, Swindale & Bilinsky, 2007), which the FNRI 2015 report
  cites as its method (pp. 6–7, Tables 2–3).
* An incomplete household gets no label. Nothing is imputed.
* `weighted_prevalence()` gives the weighted prevalence, a linearised standard error that allows for strata and
  PSUs, a 95 % CI and the Kish effective sample size.
* It is ready to run on the FNRI public-use files once they can be downloaded (see §8). **No household-level
  dataset could be built today**, because the microdata were blocked.

## 3. Province-by-wave summary (published, weighted, official)

`clean/published_hfias_2015_calabarzon.csv`: 2015, HFIAS, % of households (SE).

| Geography | n | Food secure | Mild | Moderate | Severe | Moderate + severe |
|---|---|---|---|---|---|---|
| CALABARZON | 4,328 | 44.4 (1.3) | 12.6 (0.7) | 24.0 (1.0) | 19.0 (0.8) | 43.0 |
| Batangas | 793 | 43.7 (2.8) | 12.9 (1.2) | 24.4 (2.3) | 19.1 (2.2) | 43.5 |
| Cavite | 1,076 | 44.0 (2.9) | 14.1 (1.3) | 24.5 (2.0) | 17.3 (1.5) | 41.8 |
| Laguna | 989 | 46.8 (2.9) | 11.9 (1.5) | 23.5 (2.0) | 17.9 (1.6) | 41.4 |
| Quezon | 735 | 40.3 (3.3) | 10.9 (1.4) | 27.7 (2.8) | 21.1 (2.4) | 48.8 |
| Rizal | 735 | 46.3 (3.1) | 12.3 (1.8) | 20.3 (2.0) | 21.0 (1.9) | 41.3 |

**Sample adequacy:** all five provinces have 735–1,076 households. CVs are 6–12 % for the secure, moderate and
severe categories and up to 14 % for mild, so every cell is adequate by the CV ≤ 20 % rule. Provincial 95 % CIs are
±4–6 points. The provinces' CIs overlap heavily, so 2015 does not distinguish the provinces statistically, except
for marginal differences such as Quezon's moderate category.

**2018–2021 waves:** whether the rolling ENNS supports province-by-year estimates (which provinces were surveyed
in which year, and their weights, PSUs and replicates) could not be checked, because the public-use files are
blocked. They are not assumed to form a balanced provincial panel.

## 4. 2023 CALABARZON benchmark record

| Field | Value |
|---|---|
| Indicator | Prevalence of moderate-to-severe household food insecurity (FIES; PSA SDG 2.1.2.p1) |
| Geography | Region IV-A (CALABARZON), regional only; **not assigned to provinces** |
| Year / reference period | 2023 NNS; past 12 months (the FIES reference period) |
| Estimate | **19.1 %** (95 % CI 17.0–21.1) |
| National | 31.4 % (2023); 33.4 % (2021); 44.2 % (2019) |
| Sources | PSA OpenSTAT SDG 2.1.2.p1 for the value; FNRI 2023 "Household and Food Security" release for the CI |
| Check | The FNRI summary lists CALABARZON among the five lowest regions; PSA confirms 19.1 |

## 5. HFIAS / FIES comparability

| | HFIAS (2015) | FIES (2019, 2021, 2023) |
|---|---|---|
| Items | 9 occurrence + frequency questions | 8 yes/no items |
| Reference period | past 30 days | past 12 months |
| Scoring | sum 0–27 and a rule-based category | Rasch scale with global moderate/severe thresholds |
| CALABARZON moderate + severe | 43.0 % (2015) | 19.1 % (2023) |

**They are different instruments, reference periods and scoring methods, and they are not harmonised.** The fall
from 43.0 % to 19.1 % must not be read as a trend. No pooled series was built.

## 6. Other sources

* **PSA SDG 2.1.2** is the FIES series above. Its regional values exist only for 2023.
* **FAO microdata** are national (Gallup), not usable for CALABARZON.
* **PSA FIES (Family Income and Expenditure Survey)** is an income and expenditure survey, not the Food Insecurity
  Experience Scale. It is used only for socioeconomic predictors and vulnerability, never as a hunger label.

## 7. What these labels can support

| Use | Supported? | Why |
|---|---|---|
| A. Household-level food-insecurity classification | **Not now** | Needs the household public-use files, which are blocked. Even then, a household classifier says nothing about quarterly provincial forecasting |
| B. Province-level estimation at survey periods | **Yes, for 2015 (HFIAS)** | Official provincial estimates with SE/CI for all five provinces. 2018–2021 is unknown (files blocked). There are no provincial FIES estimates |
| C. Regional external validation | **Yes, as point benchmarks** | CALABARZON FIES 2023 (19.1 %, CI 17.0–21.1) and HFIAS 2015 (43.0 % moderate + severe), each on its own instrument. One point per instrument cannot validate a time series |
| D. Quarterly provincial forecasting | **No** | There is one provincial time point (2015, HFIAS) and one regional FIES point (2023), on different instruments and periods. No valid province-by-time training panel exists, and none may be built by interpolation |

**Conclusion.**
* The new labels do **not** provide a foundation for training or validating aiPHeed's quarterly forecasts.
* They do provide official provincial and regional benchmarks. These will be displayed as *measured food-insecurity
  prevalence at survey dates*, separate from the Balance Luzon outlook and from the vulnerability priority.
* The labelled dataset is kept as a separate research asset.

## 8. Remaining step (no data request involved)

The FNRI public-use-file pages are public, but this network address is blocked by the site's firewall. Two ways to
obtain them:
1. Retry later, in case the block is temporary.
2. Open the same page from another network and save the files into
   `backend/data/fi_labels/raw/fnri/puf/` (any registration the site asks for must be done by you).

Then `app/fi_labels/hfias.py` reconstructs the household labels and weighted provincial summaries for 2015 and
2018–2021. The variable mapping is set once the files' dictionaries can be read.

## Data dictionary (clean tables)

| Column | Meaning |
|---|---|
| survey, instrument, reference_period | source survey, HFIAS or FIES, and recall period |
| year, geography, level | survey year; CALABARZON, a province, PHILIPPINES or a region; region / province / national |
| category | food_secure / mildly / moderately / severely food insecure (HFIAS) or moderate_or_severe_food_insecurity (FIES) |
| n_households, percent, se, ci95_low, ci95_high, cv_percent | as published |
| source | file and page or table |

## 9. Owner-supplied workbook (2026-11-03)

`aiPHeed_CALABARZON_Labeled_Provincial_Data.xlsx` is kept unchanged in `raw/owner_supplied/` (sha256 in MANIFEST), with
sheet exports alongside. `python -m app.fi_labels.workbook verify` checks every record against the primary sources:
* **40 of 50 verified exactly:**
  * FNRI 2015 food secure and severe, all 5 provinces;
  * PSA subsistence incidence among families and population, 2018/2021/2023.
* **10 unverified:** the ENNS provincial records come from a secondary DEPDev document, and the FNRI tables are blocked
  from this network.

Results are in `clean/owner_workbook_records_verified.csv` and `clean/owner_workbook_regional_benchmarks_verified.csv`.
The records are not a quarterly or comparable provincial series (see docs/fi9/LABEL_COMPARABILITY_REPORT.md), so
§7's conclusion is unchanged.
