# E40 methods note: binary food-stress label (Chapter 3 / DA)

*Exploratory. Indicative, not an official classification. Not a validated measure of food insecurity.*

## Data (2021-Q1 to 2026-Q3 only)

- **PSA provincial CPI.** Published monthly year-on-year rates for All items and 01.1 Food, January 2021 to September 2026, for the five CALABARZON provinces.
  - Source: OpenStat table 0012M4ACP23 (2018 = 100).
  - Quarter values are the mean of three months.
- **SWS hunger.** Balance Luzon involuntary hunger, from approved rounds only. A quarter with two rounds uses their mean.
  - Four quarters have no approved round: 2021-Q1, 2022-Q1, 2025-Q2 and 2025-Q3. They carry no label, and their label is not set to LOW.
- **News.** Titles of province-attributed articles from the E31 Google News store (2,820 of 8,320 articles).
- The code asserts that no CPI month, SWS round, label or article predates January 2021.

## Label

The label uses a frozen reference window, 2021-Q1 to 2022-Q4. Its thresholds are never recomputed. Each signal uses the 60th percentile (P60) of the window:

- `sws_hi`: hunger H is above 11.3%.
- `cpi_hi`: the province's food CPI YoY is above its own window P60.
- `gap_hi`: food minus headline CPI YoY is above the province's own window P60.
- A province-quarter is **HIGH** when `sws_hi` and (`cpi_hi` or `gap_hi`) both hold in that quarter *and* in the previous quarter. Otherwise it is **LOW**. There is no third class.

**How P60 was chosen.** The researcher chose P60 on 2026-10-15, after a P60–P85 grid. The gates were:
- the overall HIGH share of the 9 development quarters (2023-Q1 to 2025-Q1) must be 5–30%;
- the 40% per-year cap applies only to years with at least 3 development quarters.

**Result at P60:**
- 11.1% HIGH overall: 2023 is 0%, 2024 is 10%, 2025 is 60% (one quarter, so exempt from the year cap).
- All five provinces have the same label in 6 of the 9 quarters.

**Variants (reported only):**
- P75 is a sensitivity run.
- The 21.1% SWS cutoff is report-only. It is a pre-2021 statistic supplied by the researcher and not verified here.

The four holdout quarters (2025-Q4 to 2026-Q3) were not read or scored. The label files are frozen by SHA-256 in `frozen/E40_LABEL_FREEZE.json`.

## Model and evaluation

**Timing.** The walk-forward is publication-aware. At origin O(t), the first day of quarter t+1, the model may use only:
- SWS rounds posted before the origin;
- full CPI quarters up to t−1, plus months 1–2 of quarter t;
- news up to quarter t.

A training label is used only once its SWS rounds have been posted. Each fold needs at least 8 training label-quarters. The 2021–2022 labels are used for training only.

**Model.** An equal-weight blend of two parts. The weights were not tuned.
- LightGBM: num_leaves 4, max_depth 3, min_child_samples 10, L1 1, L2 5.
- Logistic regression with C = 0.3.

**Calibration.** Walk-forward Platt scaling, fitted only on earlier out-of-fold scores, then clipped to [0.02, 0.98].

**Display.** The band cutoff comes from out-of-fold scores, with 0.50 as the default. Rank ties are broken by the CPI gap.

**Gate.** Every training fold must contain at least 2 HIGH rows.

**Result: the gate fails on all 6 development folds (2023-Q4 to 2025-Q1).** Their training sets hold 0, 0, 0, 0, 0 and 1 HIGH rows. This is because the first HIGH label is 2024-Q3. So no trained model was fitted or scored on development data:
- not the blend;
- not the blend without CPI-derived features;
- not LR gov-only;
- not LR NLP-only.

The gate was not relaxed. With no out-of-fold scores, there is no calibration, and the cutoff stays at the 0.50 default.

**Baselines on the same 6 folds** (30 province-quarters, 5 HIGH; 95% CIs from a quarter-cluster bootstrap):

| Method | Accuracy | Balanced accuracy | Brier |
|---|---|---|---|
| Persistence (last known label) | 0.867 (0.733–0.967) | 0.600 (0.500–0.667) | 0.133 (0.033–0.267) |
| Always-majority (LOW) | 0.833 | 0.500 | 0.159 (training base rate) |

The majority-class AUC (0.64) means nothing: its score is only the training base rate, which changes from fold to fold.

**Plain statement.** No model can be shown to beat persistence or the majority class on this sample. The system should be presented as a **ranking and monitoring tool** for the observed SWS and CPI signals, not as a classifier.

**Does a model only recover the label?** The no-CPI variant could not be trained, so this was checked with fixed rules on origin-time inputs. These rules are not fitted and not tuned, and this is not a forecast evaluation. Across the 9 development quarters:

| Rule | Balanced accuracy | Uses CPI? |
|---|---|---|
| `sws_last_hi` × `cpi_sig_now` | 0.95 (recall 1.0) | yes |
| `sws_last_hi` alone | 0.81 | no |

So most of the target is already fixed by the inputs that define it. Any skill a model showed would largely be recovering the label, not forecasting.

**Sealed forecasts.** Forecasts for 2025-Q4 to 2026-Q4 were issued from a blend trained on development labels only. They are uncalibrated and not scored, and their hash is recorded in `frozen/E40_HOLDOUT_FORECASTS.json`. All are LOW (scores 0.07–0.42).

## Trigger composition and market regex audit

- **Composition.** Each province-quarter's trigger mix is shrunk toward a regional prior: (hits + 5·prior)/(total + 5), where the prior is the regional mix of quarters up to that quarter.
  - 116 of 120 province-quarters have at least 5 articles. The other 4 are shown as "insufficient news" with a pooled regional mix.
  - 65 province-quarters have no trigger hit at all.
- **Categories per article.** Among province-attributed titles: 2,628 hit 0 categories, 192 hit 1, and none hit 2 or more.
- **Market audit.** The top matched market keyword is "palay" (33 of 87 market titles across the whole corpus). None of the generic terms the researcher listed (price, presyo, bigas, palengke, market) are in the deployed list.
- **Market-v2 rule.** Market-v2 keeps a market title only if it has a non-generic market term and a surge/shortage context word.
  - Market titles drop from 87 to 28 across the whole corpus, and from 10 to 7 among province-attributed titles.
  - The market share of province-attributed trigger hits drops from 5.2% to 3.7%.
  - `trigger_classifier.py` and the NLP model are unchanged.
- **The dashboard's "market = 100%".** This driver split is not a news share. It is the SHAP grouping in `e31_engine.five_trigger_drivers`, where only the market group has model features.

## Face validity

The 11.1% HIGH share is a share of province-quarters marked by a *relative* rule. It is not a household prevalence. For scale, the researcher-supplied references (not re-verified here) are:
- FIES moderate-to-severe food insecurity, national: 31.4% (2023) and 33.4% (2021);
- SWS hunger, national: 23.2% (March 2026) and 22.6% (September 2026);
- PSA poverty, CALABARZON: 7.9% (2023) and 10.2% (2021).

**Chapter I.** It says "44% of households experiencing moderate to severe food insecurity in 2023" (DOST-FNRI, 2024). The 2023 national figure supplied is 31.4%.

Proposed wording, to use after checking the FNRI 2023 NNS FIES table: "with 31.4% of households experiencing moderate to severe food insecurity in 2023 (DOST-FNRI, 2024)". The thesis file was not edited.

## Before / after

| | Before (served v1, E36-LGBM) | After (E40 label, development) |
|---|---|---|
| HIGH share | 70% overall (2023 45%, 2024 65%, 2025 80%, 2026 95%) | 11.1% (2023 0%, 2024 10%, 2025-Q1 60%) |
| Score P10 / P50 / P90 | 0.079 / 0.868 / 0.998 | no calibrated scores; sealed uncalibrated: 0.087 / 0.146 / 0.421 |
| Share of scores > 0.95 | 37.1% | 0% |
| Tied rows | 29 rows in 9 quarters | 0 (CPI-gap tie-break) |
| Market share | dashboard 100% (SHAP artefact); news 5.2% | news 3.7% (market-v2) |
| Metrics | E36 record | no model scored (gate); persistence balanced accuracy 0.60, Brier 0.133 |
