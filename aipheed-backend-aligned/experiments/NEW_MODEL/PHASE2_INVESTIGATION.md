# NEW_MODEL, Phase 2: multisource investigation and revised methodology (no training)

**Written:** 2026-11-03, after your correction: aiPHeed stays a **multisource** food-insecurity forecasting system;
the target and the predictors are separate questions.

**Status:** **not committed** (no authorization yet).

**Nothing was trained or changed.** The only new computation is `runner/news_diagnostic.py`, a read-only analysis of
stored forecasts, SHAP and the input table (`out/news_diagnostic.json`).

**Supersedes:** Phase 1 §6 item 1. Option C is a statement about the **target** only. The predictor system stays
multisource.

## 1. Multisource data inventory and quality

Kind: **D** = direct food-insecurity measurement, **I** = indicator or predictor, **V** = vulnerability (static), **R** =
reference / face validity.

| # | Source | Kind | What it measures | Level | Frequency | Years usable (in repo unless marked) | Publication delay | Quality and limitations |
|---|---|---|---|---|---|---|---|---|
| 1 | **SWS involuntary hunger** | **D** | Families with nothing to eat at least once in 3 months | **Balance Luzon** (all Luzon outside NCR; CALABARZON is about a third of it), plus NCR, Visayas, Mindanao, national | Quarterly (some quarters skipped: 5 of 67 in 2010–2026) | **1998-Q3 – 2026-Q3** | About 3–8 weeks (60-day rule before 2021, documented) | About 300 respondents per area, **±5.7–6 points**. Mobile-phone mode in 2020-Q2/Q3. **Not CALABARZON-specific, not provincial** |
| 2 | **OCTA *Tugon ng Masa*** | **D** | Hunger in the last 3 months ("self-rated" in recent releases; wording to verify per release) | National, with **Balance Luzon** reported | Quarterly | **About 2022 – present** (not in repo) | About 3–6 weeks | n = 1,200 (±3% national); area samples and wording consistency unverified; press PDFs only |
| 3 | **DOST-FNRI NNS / ENNS (FIES)** | **D / R** | Moderate or severe household food insecurity (FIES; HFIAS in older rounds) | Region (some provincial outputs in 2019) | Every 1–3 years | 2018–19 (pooled), 2021, **2023 (19.1%, CI 17.0–21.1)** | Months to a year | Too sparse for a quarterly label; the paper says face validity only |
| 4 | **PSA FIES (SDG 2.1.2)** | **D / R** | The same FIES scale | Region | About every 2–3 years | 2019, 2021, 2023 (national); regional 2023 (in repo) | About 1 year | Sparse |
| 5 | **PSA APIS hunger question** | D | Family hunger, past 3 months (wording changed in 2019) | Region (microdata) | APIS years | 2011 tabulated; 2016/2017/2019 collected; **no published 2019 table** (`MORE_SOURCES/APIS_CHECK.md`) | About 1 year | Annual at most; would need the PSADA microdata |
| 6 | **PSA CBMS 2024** | **D** | Food-insecurity experience items | **Barangay / LGU** | One round | 2024 (preliminary to LGUs, 2025; not in repo) | — | A cross-section, not a time series |
| 7 | **PSA CPI**: food, all items, rice | I (affordability) | Price levels and inflation | **Province** (ACP22 2018+; ACP28 back-cast 1994+), region, national | Monthly | 1994-01 – 2026-09 | About 5–10 days after the month | Back-cast before 2018; single vintage |
| 8 | PSA wholesale and retail rice prices; palay farmgate | I (affordability, supply) | Commodity prices | Province | Monthly | Rice wholesale 2010+ (partial provinces); farmgate 1970+ (mirror) | About 35 days | Gaps by province |
| 9 | **World Bank Pink Sheet** | I (affordability, import cost) | World rice, cereals, crude, urea | World | Monthly | 1960 – 2026-09 | About 3 days | Global, not local |
| 10 | **PSA crop production** (palay, corn) | I (supply) | Production volume | Province, region | Quarterly | 1987 – 2026-Q2 | About 6–8 weeks | Revised at the next release |
| 11 | **PSA fisheries production** | I (supply) | Production volume | Province, region | Quarterly | 1993 – 2026-Q2 | About 6–8 weeks | Revised |
| 12 | **NOAA ONI** | I (climate) | El Niño / La Niña | Global | Monthly | 1950 – 2026 | About 5–10 days | — |
| 13 | **IBTrACS typhoon tracks** | I (climate shock) | Storms within 300 km | Province | Event → quarter | 1884 – 2026 | Days (best-track revised later) | Vintage caveat |
| 14 | **CHIRPS rainfall** (`RELIABLE_NEWINFO`) | I (climate) | Rainfall anomaly | Box over CALABARZON (gridded) | Monthly | 1981 – 2026-09 | About 3 weeks | Satellite estimate; today's vintage |
| 15 | PAGASA drought / dry-spell assessments | I (climate) | Provinces under drought / dry spell | Province | Monthly PDFs | About 2015+ (to verify; not in repo) | About 1 week | PDF parsing |
| 16 | **PSA LFS** unemployment | I (economic access) | Unemployment, underemployment | National quarterly (repo); **provincial annual 2021+** (not in repo) | Quarterly / annual | 2005-04 – 2026-08 (national) | About 5–6 weeks | Monthly from 2021, with gaps |
| 17 | **BSP OFW remittances** | I (economic access) | Cash remittances | National | Monthly | 2021-Q1+ in repo; about 1990+ published | About 6–7 weeks | Needs acquisition before 2021 |
| 18 | **PSA poverty**: SAE 2021, Table 1/2/2a | V | Poverty incidence | LGU, province, HUC | About every 3 years | 2018 / 2021 / 2023 | About 1 year | Static per round |
| 19 | PSA POPCEN 2024 | V | Population, density | LGU | Census | 2020, 2024 | — | Static |
| 20 | **Project news corpus** (RSS / DOC) → **FSSI-v3** (XLM-RoBERTa), six category shares, **BERTopic** | I (NLP) | Food-stress sentiment and themes in headlines | Region; province where tagged | Continuous → quarterly | **2021-Q1 – 2026-Q4** | Real time | Collected 147–882 a quarter, admitted **2–100**; N1R missing (< 5 items) at 7 of 23 origins; collection grows about 5-fold |
| 21 | **GDELT GKG** (E85 + OLD_NEWS) | I (NLP / events) | Theme-family shares, tone, affected counts | Region, province | Continuous → quarterly | **2015-Q2 – 2026-Q3** | Minutes | GDELT's monitored volume fell about 3-fold after 2020; share features comparable |
| 22 | GDELT DOC price news (`G_pri_yoy`) | I (NLP) | Price-news volume, year on year | Region | Daily | 2017+ | Minutes | — |
| 23 | NDRRMC situation reports | I (shock) | Agricultural damage per event | Region / province | Per event | PDFs (not in repo) | Days | Irregular |
| 24 | DSWD 4Ps, Walang Gutom | V / I | Programme coverage | Region | Annual, irregular | No dated series found | — | Not usable now |

## 2. Target-variable options

The target must be a direct food-insecurity measure, and the only direct measure with a usable quarterly history is
SWS. Prices, production, climate, employment and news stay **predictors**.

| Option | Definition | Food-insecurity alignment | Level | History | Known performance | Main problem |
|---|---|---|---|---|---|---|
| **T1** | SWS BL hunger > 11.3% (current REF target) | **Direct** | Regional (BL) | 62 labelled quarters 2010–2026 (1998+ for training) | Leads 1–2 accuracy 0.79 (REF); R7 fails | Sampling noise near the line; BL ≠ CALABARZON |
| **T2** | **T1, measurement-error aware**: the label is the probability that true BL hunger > 11.3, given the published reading and its SWS sampling error (soft label); or a forecast of the hunger **level** with P(> 11.3) derived from it | Direct, and honest about noise | Regional | Same | **Not tried as a label.** IMPROVE_V2 tried a regression variant (I2) as a model, not this label | R1–R7 score hard labels; a soft label changes how training treats near-threshold quarters, not the scoring. A level-forecast variant exists (I2) |
| **T3** | **Multi-measurement hunger**: SWS and OCTA (where both exist) combined into one BL reading, more respondents and less noise | Direct | Regional (BL) | OCTA only from about 2022, so it cannot train a model; **prospective** | — | Comparability is unproven (wording, mode, sample). It needs a calibration study first |
| T4 | Eq. 3 with an origin-specific median: hunger + 2 × provincial food-CPI deviation | **Mixed: the province part is price only** | Province | 24 quarters (2021+), or longer with the back-cast | 0.30 (Eq. 3 as written, E99) | Makes affordability part of the target |
| T5 | P0H4: hunger condition **and** provincial price condition | Mixed (affordability-conditioned) | Province | 2021+ | Lead 1 passes R1–R7; Lead 2 fails | The province signal is a price forecast |
| — | Any provincial **measured** food-insecurity target | Would be ideal | Province | **Does not exist** (only CBMS 2024 cross-section, FNRI sparse) | — | Cannot be built without fabricating provincial observations |

## 3. Source-to-feature mapping (how each dimension enters the forecast)

The SHAP shares are from the verdict window (62 quarters) of REF+news, `OPTION_1/out/results.json`. "Tested" names the
experiment that measured incremental value.

| Dimension | Sources (§1) | Features (existing) | Level used | Role | SHAP share (REF+news) | Incremental value tested |
|---|---|---|---|---|---|---|
| Hunger history | 1 | `h_last`, `h_change`, `h_mean4`, `true_h`, `pi_H4L` | Regional | Predictor (own history) | 64% | It is the persistence baseline; the strongest signal |
| Affordability: local | 7, 8 | `R_food_yoy`, `R_head_yoy`, `R_rice_yoy`, `R_food_mom` | Regional | Predictor | 6% (food and headline) + 2.5% (rice) | Part of REF |
| Affordability: world | 9 | `W_rice_yoy`, `W_rice_mom`, `W_cereal_yoy`, `W_crude_yoy`, `W_urea_yoy` | World | Predictor | 21% | Part of REF |
| Supply | 10, 11 | `R_C3` (crop drop), `R_C4` (fish drop) | Regional | Predictor | 0.8% / 0.5% | Part of REF |
| Climate | 12, 13, 14 | `ONI_last`, `ONI_max12`, `tc_mean`; CHIRPS `RF_z3`, `RF_z6` | Global / province mean / box | Predictor | 1.9% / 0.1%; CHIRPS 2.0% | **CHIRPS: no call changed** (RELIABLE_NEWINFO) |
| Economic access | 16, 17 | `E1` (unemployment change); remittances (not before 2021) | National | Predictor | — | `E1`: HISTORY_RETRAIN option (c); not in REF |
| NLP / news | 20, 21, 22 | `N1R`, six E112 shares, `G_pri_yoy`; GDELT `g_*` | Regional | Predictor | **4.4% overall, about 16% within the news era** (§5) | REF+news worse than REF; REF+G fails R5 and R7 (OLD_NEWS) |
| Vulnerability | 18, 19 | Poverty, density | LGU / province | **Spatial weighting** (Algorithm 5, province score), not a predictor | — | — |
| Face validity | 3, 4, 5 | — | Region | Reference only | — | — |

**Distinctions kept separate in all reporting:**
- food insecurity: SWS, FNRI and OCTA (measured);
- food affordability: CPI, prices;
- agricultural stress: production, climate;
- socioeconomic vulnerability: poverty, density, employment.

## 4. Geographic and temporal coverage

| Level | Sources with **measured** values at that level | Sources only at a coarser level |
|---|---|---|
| **LGU** | Poverty (SAE 2021), population; CBMS 2024 (one round) | — |
| **Province** | CPI (1994+ back-cast, 2018+ official), crop and fisheries production, typhoon counts, poverty (Table 1), provincial LFS (2021+ annual), GDELT province tags (sparse), corpus province tags (very sparse) | — |
| **Region / BL** | **SWS hunger (BL)**, regional CPI, FNRI / FIES (Region IV-A), CHIRPS box, OCTA BL | Province values of the outcome **do not exist** |
| National / world | LFS (quarterly), remittances, ONI, Pink Sheet, GDELT volume | — |

**Temporal coverage, binding for training:**
- SWS from 1998;
- CPI 1994+;
- production 1987/1993+;
- LFS 2005+;
- GDELT 2015-Q2+;
- the corpus 2021+.

A multisource model trained 1998–2026 therefore sees most sources for the full span, LFS from 2005, GDELT from 2015 and
corpus news from 2021 only.

**Province rule (non-negotiable).** A province forecast is **never** a copied regional observation presented as
provincial ground truth.
- The regional forecast may be **shown** for every province with that statement (the Option C display).
- Provincial **predictors** (prices, production, typhoons, poverty) may describe how provinces differ.
- Neither can be scored as a provincial food-insecurity accuracy.

## 5. Why news is weak, and what to investigate (`out/news_diagnostic.json`)

| Finding | Evidence |
|---|---|
| **The low share is mostly dilution, not disuse.** News exists for only 20 of the 62 verdict quarters (2021+) | News SHAP is 4.4% over all 62 quarters (all 8 news columns; OPTION_1's 2.8% grouped fewer columns as news), but **15.8% (Lead 1) and 16.4% (Lead 2) within the news era** |
| **All of REF+news's loss is in the news era** | Pre-2021 origins: REF+news **identical** to REF (42/42 and 43/43 quarters). News-era origins: accuracy **0.750 vs 0.850** (L1) and **0.737 vs 0.842** (L2); Brier 0.224 vs 0.200 and 0.256 vs 0.207 |
| **The model leans on news it cannot learn well** | News-era training rows: at most about 20 quarters. LightGBM splits on news learned from so few quarters fit noise; their influence (about 16%) is larger than their evidence |
| **Weak univariate signal** | AUC of each news column against the label (news era, Lead 1, n = 14–20): N1R 0.56, price 0.65, shortage 0.41, disaster 0.56, agri 0.52, jobs/income 0.32, assistance 0.59, `G_pri_yoy` 0.18 (inverted) |
| **Sparse, non-stationary corpus** | Admitted 2–100 articles per quarter; N1R missing at 7 of 23 origins; collection grows about 5-fold 2021→2026, so a share or level partly measures collection effort |
| **Geographic mismatch** | The corpus and GDELT are CALABARZON-located, but the target is Balance Luzon (about three times larger) |
| **Timing is not the cause** | Audit B5: no news value is used before its publication; NaN, not 0, before 2021 |
| **Longer history did not help** | GDELT 2015–2026 (OLD_NEWS): one call changed, the wrong way; R5 lost |

**Causes, ranked:**
1. Too few labelled quarters with news (coverage).
2. Feature construction that carries collection drift (levels and shares of a growing corpus).
3. Geographic mismatch with the target.
4. A genuinely weak quarterly signal.

Data quality issues (relevance noise in headlines) add to (4). **Not shown:** that news has no value at all.

**Proposed investigation (Phase 4, each sealed before running, Lead 1 and Lead 2 separately):**
- **N-a. Drift-free construction.** Each news feature as its anomaly against its own trailing 8 quarters (z-score),
  not its level. This removes collection growth.
- **N-b. Low-capacity news.** One pre-specified news summary (e.g. the mean of N-a anomalies over the hunger-related
  families) instead of 8 columns, so 20 quarters fit one parameter, not many splits.
- **N-c. Geography matched to the target.** GDELT records located anywhere in Balance Luzon, not only CALABARZON,
  2015–2026. This needs a new GDELT query, about the same scan size; your approval is required.
- **N-d. News-era-only evaluation.** Report every news variant on the 2021+ quarters separately (where news exists),
  beside the full window, so dilution is never mistaken for value.

## 6. Revised methodology recommendation (for adviser review)

1. **Target: T1 (SWS Balance Luzon hunger > 11.3%) as the reference outcome**, with T2 (the measurement-error-aware
   variant) as the one new label investigation, and T3 (SWS + OCTA) as a **prospective** calibration study.
   - SWS is the direct food-insecurity measure; it is regional, and the reports say so everywhere.
   - FNRI, PSA FIES and APIS are face-validity references; CBMS 2024 is the LGU-level validation reference for
     Objective 3.
2. **Predictors: multisource, by dimension (§3).**
   - Each dimension's **incremental** value is tested by a pre-registered group ablation against the same REF core,
     at Lead 1 and Lead 2 separately: hunger history; local affordability; world prices; supply; climate (including
     CHIRPS); economic access (`E1`, remittances if acquired); NLP (N-a/b/c/d).
   - A source stays in the final model only if its ablation supports it. Every tested source is **reported**, kept
     or not (Objective 1 and master prompt §2).
3. **Province layer (Objective 3), without fabricated ground truth.**
   - The regional forecast is shown for each province, ordered by the poverty-weighted score (Option C).
   - The provincial affordability, supply and climate indicators are shown as **context**, labelled by dimension.
   - LGU rankings follow Algorithm 5 with the vulnerability-weighting disclosure.
   - CBMS 2024 is used once to check whether the LGU ranking agrees with measured LGU food insecurity (RQ4 / H4).
4. **Validation.** Algorithm 3 at k = 1..8, with Lead 1 and Lead 2 reported independently. R1–R7 per lead. The
   six Objective 4 comparators with Holm. Calibration and by-period stability.
   - **Algorithm 4 blind holdout = the first four sealed prospective quarters (2027-Q1..Q4)**, scored once. The old
     2025-Q4..2026-Q3 holdout has been examined and cannot be blind.
   - Development results are labelled as development evidence throughout.
5. **One final model.** The candidates from (1)–(2) are compared once on a pre-registered selection rule. The chosen
   model is sealed prospectively under `SENIOR_REVIEW/PROSPECTIVE_PLAN.md` (or a revision of it, if the model
   changes, approved before any 2027 outcome).
6. **Honest reporting of unmet requirements.**
   - R1–R7 at both leads on development data: not met so far.
   - Holdout AUC ≥ 0.80: not reached by any model.
   - A province-level measured outcome: unavailable.

## 7. Decisions requiring adviser approval

| # | Decision | My recommendation |
|---|---|---|
| A1 | Target: T1 as the reference outcome (regional), with Ch I/III amendments (RQ2, RQ3, H2, H3, Obj 2–3 wording; CH3_AMENDMENT Option C) | Approve T1 |
| A2 | Investigate T2 (measurement-error-aware label) as the one new label variant | Yes |
| A3 | Start a prospective SWS–OCTA comparability study (T3); no use in labels until shown comparable | Yes |
| A4 | Eq. 3 (T4) and P0H4 (T5) retired as targets; prices kept as predictors and province context | Yes |
| A5 | Province forecasts presented as the regional forecast plus provincial context, never as measured provincial accuracy; LGU rankings disclosed as vulnerability-weighted | Yes |
| A6 | Algorithm 4 blind holdout = the first four sealed 2027 quarters (the old holdout is no longer blind) | Yes |
| A7 | Algorithm 4's Optuna 100 trials replaced by the fixed 8-setting grid with chronological selection (already disclosed) | Yes, given 24–62 quarters |
| A8 | R1–R7 kept as the project's stricter rule beside Algorithms 3/4, and named as not from the paper | Yes |
| A9 | The dimension-group ablation design (§6.2) and the NLP investigation N-a..N-d, including **a new GDELT Balance-Luzon query (about 1 TiB, needs your approval)** | Yes for N-a, N-b, N-d; N-c your call |
| A10 | Acquire: BSP remittances 1998+ (your file), provincial LFS 2021+, CBMS 2024 CALABARZON (PSA request), OCTA releases 2022+, PAGASA drought PDFs | Remittances, CBMS and OCTA first |
| A11 | Open paper contradictions: C1, C3, C4, C5, C6, C8, C13, C18, C19 (`PAPER_ALIGNED/STEP0_REQUIREMENTS.md`) | Decide before Chapter III is finalized |
| A12 | FNRI references: NNS 2023 (verified); 2019 noted as a different scale (HFIAS) | As before |

**Stop.** No training until the target (A1–A4) and this methodology are approved.
