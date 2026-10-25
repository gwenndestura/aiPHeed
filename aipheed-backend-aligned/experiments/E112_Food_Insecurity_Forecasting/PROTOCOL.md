# E112 Pre-registered protocol (frozen before any E112 candidate is scored)

**Base.** Branch `aiPHeed/e112-food-insecurity-forecasting`, from E111 `509781e`.

**Already built before this freeze:**
- the root-cause audit;
- the news indicator tables (`runner/news_indicators.py` → `out/news_quarterly_{corpus,gdelt}.csv`). These read no hunger data.

**Disclosure.** Every SWS quarter through 2026-Q3 was examined in E109–E111, so nothing scored here is unseen. This protocol fixes the E112 candidates, tests and decision rules before their scores exist. Reliability still requires prospective confirmation (P6).

## 1. Outcome, vintages, horizons

- **Outcome:** SWS Total Hunger, Balance Luzon, primary rule (E109 `outcome_rounds.csv`, non-commissioned rounds), continuous percentage.
- **Generalization panel:** the four SWS areas (E110 `sws_area_rounds.csv`).
- **Issue date:** O(t) = first day of quarter t+1 (`e107_lib.issue`).
- **Vintage:** only rounds published before O(t) (E109 Addendum 1).
- **Leads and horizons:** leads k = 1–4 quarters (target quarter t+k). Every row also records its true horizon, t+k − newest observed quarter.
- **Evaluated rows:** every BL target quarter q ≤ 2026-Q3 whose origin q−k has at least 8 training pairs (E109 `MIN_PAIRS`). All BL candidates share the same rows.

## 2. News indicators (fixed; `runner/news_indicators.py`)

| Source | What |
|---|---|
| **C (primary)** | The project RSS corpus (E31 + E60 stores). Every headline is de-duplicated (`pipeline_v3.dedupe`, the same normalised title within 3 days). Each is tagged with six event categories by a fixed title lexicon (English and Filipino): price, shortage, disaster, agri_supply, jobs_income, assistance. |
| **G (cross-check)** | GDELT GKG documents located in CALABARZON (E85 file), the same six categories from fixed GKG theme lists |

**Measures per quarter:**
- **volume:** headline count n;
- **intensity:** category share = category headlines / all headlines, which is coverage-normalised;
- **direction:** year-over-year change of the share (quarter q minus q−4), which removes the typhoon calendar.

**Severity.** XLM-R intensity (FSSI-v3) covers only 379 headlines and stays in family N1 unchanged. No new severity score is created.

**Timing.**
- A forecast issued at O(t) uses the YoY indicators of quarter t: the "gap quarter", complete on the last day before O(t).
- An indicator is set to missing if any headline counted in it was published on or after O(t). This is asserted in code and tested.
- No hunger data enter the indicators.

## 3. Candidates (BL unless marked)

| Id | Definition |
|---|---|
| RW | Latest published reading (reference) |
| MA2, MEAN, SEAS, LL | E109 baselines, unchanged |
| NEWS-C | **News only.** Latest reading + ridge (alpha 10, standardised, median-filled; E110 `_ridge`). Fitted on E109 training pairs, predicting the change from the latest reading from the six corpus YoY indicators. |
| NEWS-G | As NEWS-C with the six GDELT YoY indicators |
| LGBM12 | **The required 12-family LightGBM.** E109 `forecast("LGBM")` unchanged: 13 columns, depth 1, 2 leaves, min_child 3, lr 0.05, L2 5, trees {25, 75} by inner MAE, seed 109. |
| LGBM12N | LGBM12 with the six corpus YoY indicators added (19 columns). Identical settings and tree selection. |
| LGBM12N−f | LGBM12N without family f (each of the 12 families) or without the news group. Leads 1–2. Contribution analysis only. |
| LGBM12N−c | LGBM12N without corpus category c (6). Leads 1–2. Contribution analysis only. |
| NEWS-CP (panel) | 4-area panel. Latest reading of the area + ridge on the six corpus YoY indicators, fitted on the pooled training pairs of all four areas known at O(t). Same rows as E111 `evaluate_panel`. |

No hyperparameter, lexicon or feature is changed after scoring.

## 4. Tests

### 4.1 Concurrent validity of the news indicators (no hunger data)

Spearman, one-sided ρ > 0, quarters 2021-Q1..2026-Q3 where both values exist. Indicator rows come from `e109_lib.regional_features(1)`, the provincial mean.

| News | Comparison |
|---|---|
| price share | A2 at origin q (headline inflation, months 1–2 of q) |
| price YoY | A3 at origin q+1 (rice YoY of quarter q) |
| disaster share | C2 at origin q (typhoon count of q) |
| agri_supply YoY | C3 and C4 at origin q+1 (production drops of q) |
| jobs_income YoY | E1 at origin q+1 (unemployment change of q) |

- **Valid:** a category is "valid" when at least one of its comparisons has p < .05.
- **No external series:** shortage and assistance are reported descriptively.

### 4.2 Advance-warning association (news vs later hunger)

**Test.**
- Spearman between news YoY of quarter s and the BL hunger YoY change D(s+j) = H(s+j) − H(s+j−4), for j = 0, 1, 2.
- Expected sign: + for price, shortage, disaster, agri_supply and jobs_income. Assistance is two-sided.
- Holm within each source over its 18 tests.

**Reading.**
- **Advance warning:** some category at j ≥ 1 has Holm p < .10 with the expected sign.
- **Concurrent only:** significance at j = 0 only.

### 4.3 Forecast tests

Every test uses the E111 Newey–West HLN Diebold–Mariano test (`e111_lib.dm_nw`), one-sided, on per-quarter absolute-error differentials.

| Test | Comparison | Holm correction |
|---|---|---|
| N1 news-only | NEWS-C vs RW and NEWS-G vs RW | over 2 sources × 4 leads |
| N2 ablation | LGBM12N vs LGBM12 | over 4 leads |
| N3 contribution | LGBM12N−news, LGBM12N−c and LGBM12N−f vs LGBM12N (H1: removing it makes forecasts worse) | over the 19 removals per lead (leads 1–2) |

N3 also reports mean |SHAP| share of the news columns in LGBM12N.

**News adds measurable predictive value** if N1 or N2 has Holm p < .10 at any lead. Otherwise the conclusion is "measured, no demonstrated gain".

**A family adds value** if its N3 Holm p < .10 and the gain keeps its sign under the ALL and HH rules (§4.5).

### 4.4 Reliability rule (unchanged from E111 §4, Newey–West DM)

| | Requirement |
|---|---|
| P1 | ≥ 8 quarters and p < .10 vs RW |
| P2 | BL MAE ≤ RW and ≤ 4.0 |
| P3 | Better in every third, in rising and falling rows, and after 2025-Q2 |
| P4 | Leave-one-quarter-out |
| P5 | Last 4 quarters not worse |
| P7 | Surge underprediction ≤ RW |
| P8 | 80% interval coverage ≥ 0.70 (sigma = RMSE of earlier own errors) |
| P6 | Unseen confirmation (always false now) |

**Rows used.** BL candidates use their BL rows for every criterion. NEWS-CP uses the panel rows, with BL for P2.

**Status.**
- **provisional:** everything except P6;
- **insufficient evidence:** fewer than 8 quarters;
- **not reliable:** otherwise.

**Maximum provisional lead:** the largest k such that leads 1..k are all provisional.

### 4.5 Generalization and stress checks (reported for every candidate)

- Thirds, rising and falling rows, post-2025-Q2, leave-one-quarter-out and the last 4 quarters (within P3–P5).
- **Sharp increases** (y − latest reading > the latest round's published margin):
  - count;
  - mean underprediction;
  - miss rate.
- **Warnings and false alarms:**
  - a warning is a forecast ≥ latest reading + 2.0 points (half the ±4 BL margin);
  - hit = a warning followed by a sharp increase;
  - false alarm = a warning not followed by a sharp increase.
- **Missing data:** NaN share of every feature over the evaluated origins.
- **Survey changes:**
  - BL rules ALL (adds commissioned rounds) and HH (household-head rounds only, i.e. before the 2025 respondent-base change), leads 1–2;
  - the true-horizon breakdown.

## 5. Final-method decision rule (fixed)

1. **Adopted forecast.** The adopted research forecast is the first of LGBM12N, LGBM12, NEWS-C, NEWS-G, NEWS-CP whose Lead-1 status is "provisional". Otherwise it is **RW, the latest published SWS reading**, labelled with its true horizon and its empirical error.
2. **Maximum reliable lead.** It is "none established" unless P6 is met. P6 is met only by sealed prospective scoring.
3. **Exploratory candidates.** E111's ASYM (Lead 1) and LLR (Lead 2) stay exploratory and are not re-scored as new claims.
4. **Municipal claims.** No municipal or provincial food-insecurity forecast is claimed (no measured outcome; see the target assessment).

## 6. Seals

- At origin 2026-Q3 (issue 2026-10-01), forecasts of every BL candidate and NEWS-CP for leads 1–4 go to `out/sealed_prospective.csv`, with a SHA-256.
- The E107–E111 seal hashes are recorded and verified unchanged.
- `runner/score_prospective.py` scores any sealed file once newer SWS rounds are entered. It never alters the seals.
