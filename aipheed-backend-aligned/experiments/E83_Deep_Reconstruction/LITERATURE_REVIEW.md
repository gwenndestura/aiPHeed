# E83 literature review: forecasting food insecurity, and how news enters forecasts

Scope:
- methods that can forecast quarterly, multidimensional food-insecurity risk for five provinces;
- methods that turn news into forecasting signals.

Every claim below is attributed. "Reported" means taken from the paper's abstract or summary; the methods sections of
the paywalled papers were not read.

Searches were restricted to methodology and pre-2026 publications. No PSA, BSP or SWS "latest" query was run, because
of the blind-boundary rule.

## 1. Sources consulted

| # | Source | What it contributes to E83 |
|---|---|---|
| 1 | Balashankar, Subramanian & Fraiberger (2023), *Predicting food crises using news streams*, Science Advances 9(9) eabm3449 | 11.2 M articles (1980–2020). News-derived indicators reportedly improve district-level IPC forecasts up to 12 months ahead over models without text. The authors' replication code is public. |
| 2 | Balashankar et al. (2021), *Fine-grained prediction of food insecurity using news streams*, arXiv 2111.15602 | 15 fragile states, district level, up to 3 months ahead. Reports 32% more food crises predicted than existing models. |
| 3 | Andrée, Chamorro, Kraay, Spencer & Wang (2020), *Predicting Food Crises*, World Bank PRWP 9412 | Statistical forecasts for 21 countries (2007–2020). At longer horizons they are reportedly competitive with expert outlooks. Conflict and news-derived event data are inputs. |
| 4 | Westerveld et al. (2021), *Forecasting transitions in the state of food security with machine learning using transferable features*, Sci. Total Environ. 786:147366 | XGBoost on Ethiopian livelihood zones, leads of 1–12 months. Macro-F1 is 0.51 at 3 months and 0.61 at 7 months. The largest gain over baselines is on **deteriorations** (transitions), which is evaluated separately. |
| 5 | Busker et al. (2024), *Predicting food-security crises in the Horn of Africa using machine learning*, Earth's Future 12(8) e2023EF004211 | XGBoost with 20+ datasets. R² > 0.6 to 3 months. It predicts only 20–50% of crisis onsets at 3 months. It is compared with **persistence**, seasonality and FEWS NET outlooks. |
| 6 | Foini, Tizzoni, Martini, Paolotti & Omodei (2023), *On the forecastability of food insecurity*, Sci. Rep. 13:2793 | WFP. Gradient-boosted trees forecast food consumption; satisfactory up to 30 days in only some countries. Forecastability is country-specific and limited. |
| 7 | Martini et al. (2022), *Machine learning can guide food security efforts when primary data are not available*, Nature Food | Nowcasting where surveys are missing. A nowcast is distinct from a forecast. |
| 8 | Machefer et al. (2025), Global Food Security 45:100859 | Potential and limitations of ML for acute food insecurity (title and journal verified; content not read). |
| 9 | IPC Technical Manual v3.1 (2019); FEWS NET scenario development | Food insecurity is multidimensional: availability, access, utilization and stability. Evidence is converged from several indicators. Outlooks are projected scenarios, not point forecasts. |
| 10 | Mueller & Rauh (2018), *Reading between the lines*, APSR | Topic shares from newspaper text forecast within-country changes. Normalisation by total coverage and within-unit variation are essential. |

## 2. What the evidence implies for aiPHeed

### 2.1 Persistence is the benchmark to beat

Persistence and seasonality are the benchmarks to beat, and they are hard to beat at short horizons (sources 4–6).

- Gains appear mainly on **transitions**, so E83 reports "rising" rows separately (PROTOCOL §6).
- Evaluating on all rows lets a model ride persistence.

### 2.2 Forecastability is limited and horizon-dependent

Forecastability is limited and depends on the horizon (sources 5 and 6).

- Published systems with thousands of unit-months reach useful skill at 3 months. Skill falls with lead time.
- aiPHeed has:
  - 13 evaluable target quarters at Lead 2;
  - one independent hunger series (SWS Balance Luzon);
  - five provinces whose label differences come only from prices.

  That is orders of magnitude less information. A claim of > 75% accuracy *with* discrimination at Lead 2 needs
  evidence that this sample can barely provide. E83 therefore reports intervals by date block, not by row.

### 2.3 Text features help when converted into event signals

Text features help when they are turned into causal-event signals and normalised (sources 1, 2 and 10).

- Reported pipeline in source 1 (from the paper's summary):
  1. Seed terms for food-crisis drivers are expanded semantically with word embeddings.
  2. Mentions are counted per district and month.
  3. Counts are normalised by coverage.
  4. Lags enter a tree model.
- The incremental value is measured by ablation against the same model without text.

### 2.4 Mechanism versus mention

Event occurrence versus discussion is handled by phrase-level driver lexicons, not topic words (source 1; also the
E60 lessons). Directionality matters: adverse versus easing versus response.

### 2.5 Media attention

Media attention is controlled by dividing by total coverage per unit-time (sources 1 and 10). In aiPHeed the
collection itself grew over time: E73 found that market news was a corpus-growth artifact.

### 2.6 Leakage

Leakage is prevented by using publication time, not the event or reference time, for every input (sources 3 and 5).
Retrieval time differs from publication time when an archive is collected later. That is a real-time availability
limitation, and it must be disclosed.

## 3. Answers to the directive's seven news questions, as implemented in E83

| Question | E83 implementation (`backend/app/news/events.py`, `lead_extractor.py`) |
|---|---|
| 1. Raw articles to signals | Classifier v2 phrase lexicon decides relevance and driver. The polarity rule gives ADVERSE / IMPROVING / RESPONSE / NEUTRAL. Event clustering uses multilingual MiniLM embeddings. Rates are taken per 100 collected articles. |
| 2. Event versus mention | Relevance requires a mechanism phrase. A further OFF_TOPIC filter removes classroom, medicine and power shortages. Polarity is separate from relevance. When a lead is available, relevance is re-decided on title + lead. |
| 3. Aggregation over space and time | Province-attributed events are shrunk toward the regional value (κ = 5). National events enter only through the regional value. Quarters run up to O(t), with a change against t−1. |
| 4. Delays, duplicates, coverage, attention | Publication time is used. Exact-title syndication is removed (E64). Semantic clusters span 7 days, and salience comes from the outlet count. Division by quarterly corpus volume controls attention. A coverage feature is included. |
| 5. Future information | Only articles with publication time before O(t) are used. Lead text was retrieved on 2026-10-21; this is disclosed (§7 of the protocol). |
| 6. Incremental value | Ablation arms A–F use the same rows and folds. Group-drop and group-only tests run for every driver. |
| 7. Realism for CALABARZON | 695 relevant de-syndicated articles over 23 quarters is about 6 per province-quarter, far below the article volumes in sources 1–2. Lead text can be legally recovered only from the government and WordPress publishers that permit it (see LEAD_TEXT_REPORT.md). Regional shrinkage and a few aggregated event features are the realistic ceiling. |

## 4. Consequences for model choice

- **Sample size.** With 25–65 evaluable rows per lead and 5–13 independent target quarters, tree ensembles with many
  features overfit. That is visible in E83 round 1, where the learners fall to 0.32–0.44 accuracy after the 2025
  regime change.
- **Preferred structures:**
  - structural models with few parameters, whose components follow the target's definition (hunger × price);
  - heavily regularised linear models;
  - in-origin threshold choice.
- LightGBM is retained as a candidate and as the served price-pressure indicator.
