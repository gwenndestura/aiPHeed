# E175: should the FNRI food-insecurity percentages be transformed for the 50 % HIGH/LOW rule?

Investigation only, 2026-11-07. The official FNRI values are read and never modified, and nothing here reaches the dashboard.

**Code:** `backend/app/e175/target_scaling.py`.

**Outputs:** in `backend/data/e175/out/`:
- `results.json`: every metric below.
- `values.csv`: each validation row's original FNRI value, the cut each method implies, and the resulting class.
- `calabarzon_transformed.csv`: the original values beside every transformed value and its parameters.

## 1. The key fact

E168 forecasts the **level**: the share of households that are moderately or severely food insecure (HFIAS), on the logit scale. It classifies HIGH or LOW only afterwards.

Every candidate keeps the provinces in the same order:
- min–max rescaling;
- relative risk against a reference;
- percentile rank;
- calibration to another survey scale.

For any order-preserving transformation T:

> T(x) ≥ 0.5 ⇔ x ≥ T⁻¹(0.5)

So **"transform the values, then keep the 50 % threshold" is exactly the same as "keep the values, and move the threshold to T⁻¹(0.5)".** A transformation cannot make the forecast more accurate. It can only change *which* provinces count as HIGH. The real questions are:
1. Is the implied cut meaningful?
2. Can it be known when the forecast is made (no leakage)?
3. Does the model beat simple baselines under that definition, rather than just benefiting from a different share of HIGH cases?

## 2. Candidates and their justification

| Method | Mathematical form | What "50 %" becomes on the FNRI scale | Justification and fit |
|---|---|---|---|
| **A. Original FNRI share** | x | 50 % | The official measured value (Coates, Swindale & Bilinsky 2007, *HFIAS Indicator Guide*, FANTA). The panel's rule: a majority of households moderately or severely food insecure. |
| **B. Min–max per round** | (x − min)/(max − min) | the midpoint of the round's minimum and maximum (about 47–59 %) | Min–max is for putting *different* indicators on one scale in composite indices (OECD/JRC 2008, *Handbook on Constructing Composite Indicators*). Its result depends on the two most extreme provinces in each round, which changes with which provinces were surveyed. **Unsuitable for a target.** |
| **C. Relative to the reference level** | x / ref; shown as x/(x + ref), so 0.5 means relative risk 1 | the reference (mean) level of the round | Relative risk is standard in epidemiology. It changes the question to "worse than average?", which is not "high". FNRI publishes no national HFIAS for 2013, 2015 or 2021, so the reference must be built from the surveyed provinces. |
| **D. Percentile rank** | share of provinces below x | the round median | Ranking against other provinces; the same issues as B and C. |
| **E. Calibration to FIES (SDG 2.1.2)** | logit F = (logit H − 0.158)/0.917 (E169 bridge) | 53.9 % on the HFIAS scale | Puts HFIAS on the official SDG 2.1.2 scale (Cafiero, Viviani & Nord 2018, *Measurement* 116). But the bridge comes from only 20 provinces in one year (slope 95 % CI 0.64–1.22), and those 2019 households overlap a validation round. |
| **F. Logit** | log(x/(100 − x)) | 50 % (logit 0) | Variance-stabilising for proportions (Warton & Hui 2011, *Ecology* 92). **Already used by E168**, and identical to A for classification. |
| **Sparse-survey treatment** | weighting by 1/SE²; shrinkage toward hierarchical anchors; labels as probabilities | no change of cut | The recognised approach for sparse provincial survey estimates is to model their sampling error, not to rescale them (Fay & Herriot 1979, *JASA* 74; Rao & Molina 2015, *Small Area Estimation*). **E168 already does this:** 1/SE² weights, hierarchical and own-history anchors, and a label probability `q_true` used in the Brier score. |

For B, C and D the parameters (minimum, maximum, mean, median) can come from:
- **the target round itself**: a naive implementation, which uses the outcome being forecast and so is **leakage**; or
- **the latest round published at the forecast origin** ("as-of"), the only leakage-free version.

Both versions were evaluated.

## 3. Original versus transformed CALABARZON values (all FNRI rounds)

| Round | Province | FNRI original | B min–max | C relative risk | D percentile | E FIES scale |
|---|---|---|---|---|---|---|
| NNS 2013 | Quezon | 48.9 % | 0.34 | 0.85 | 0.28 | 44.5 % |
| NNS 2013 | Rizal | 43.8 % | 0.27 | 0.76 | 0.17 | 39.1 % |
| FNRI 2015 | Quezon | 48.8 % | 0.45 | 0.88 | 0.23 | 44.4 % |
| FNRI 2015 | Batangas | 43.5 % | 0.37 | 0.78 | 0.10 | 38.8 % |
| ENNS 2018 | Laguna | 26.2 % | 0.00 | 0.55 | 0.00 | 21.4 % |
| ENNS 2019 | Quezon | 44.0 % | 0.44 | 0.89 | 0.32 | 39.3 % |
| ENNS 2019 | Rizal | 39.1 % | 0.34 | 0.79 | 0.24 | 34.2 % |
| ENNS 2021 | Batangas | 39.9 % | 0.40 | 0.96 | 0.40 | 35.0 % |
| ENNS 2021 | Cavite | 35.5 % | 0.28 | 0.85 | 0.32 | 30.5 % |

All 15 CALABARZON rows are in `calabarzon_transformed.csv`, with each round's minimum, maximum, mean and median.

**What this shows.** CALABARZON is **below the level of the other surveyed provinces under every method**:
- relative risk 0.55–0.96;
- percentile 0–40 %;
- min–max at most 0.45.

None of the transformations makes a CALABARZON province HIGH. The 50 % rule is not "too high for CALABARZON": CALABARZON's measured food insecurity really is below most other provinces'.

## 4. Before and after: E168's frozen forecasts under each definition

These use the same 72 as-of forecasts, with no refit. "Skill" is accuracy minus always predicting the more common class. Persistence means reusing the latest published survey, with the same cut.

**Lead 1:**

| Method | Leakage-free | HIGH share | Accuracy | Always-majority | Skill | κ | Precision | HIGH recall | F1 | AUC | Persistence accuracy | E168 − persistence |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **A original 50 %** | yes | 0.35 | 0.750 | 0.653 | +0.097 | 0.50 | 0.59 | **0.88** | 0.71 | **0.893** | 0.625 | **+0.125** |
| B min–max (target round) | **no** | 0.42 | 0.764 | 0.583 | +0.181 | 0.53 | 0.68 | 0.83 | 0.75 | 0.862 | 0.625 | +0.139 |
| B min–max (as-of) | yes | 0.35 | 0.764 | 0.653 | +0.111 | 0.51 | 0.62 | 0.80 | 0.70 | 0.850 | 0.597 | +0.167 |
| C relative (target round) | **no** | 0.50 | 0.736 | 0.500 | +0.236 | 0.47 | 0.67 | 0.92 | 0.78 | 0.813 | 0.639 | +0.097 |
| C relative (as-of) | yes | 0.26 | 0.750 | 0.736 | +0.014 | 0.42 | 0.52 | 0.68 | 0.59 | 0.869 | 0.667 | +0.083 |
| D percentile (target round) | **no** | 0.51 | 0.736 | 0.514 | +0.222 | 0.47 | 0.70 | 0.86 | 0.77 | 0.806 | 0.639 | +0.097 |
| D percentile (as-of) | yes | 0.25 | 0.792 | 0.750 | +0.042 | 0.49 | 0.56 | 0.72 | 0.63 | 0.867 | 0.722 | +0.069 |
| E FIES-calibrated 50 % | yes* | 0.29 | 0.806 | 0.708 | +0.097 | 0.53 | 0.67 | 0.67 | 0.67 | 0.866 | 0.750 | +0.056 |
| F logit | yes | identical to A | | | | | | | | | | |

*E's cut is a constant, but the bridge was fitted on ENNS 2019 households that overlap a validation round.

**Leads 2 and 3** show the same pattern (`results.json`). A has the highest AUC (0.894, 0.873) and HIGH recall (0.88, 0.84) of all the leakage-free definitions.

## 5. What the comparison shows

1. **The apparent gains are class-share effects, not better forecasting:**
   - The target-round versions of B, C and D push the HIGH share towards 50 %, which lowers the always-majority rate to 0.50–0.58. That makes their skill look large (+0.18 to +0.24).
   - But they use the outcome round to set the cut, which is **leakage**, and their AUC *falls* (0.81–0.86 against 0.893).
   - As-of D and E reach 76–81 % accuracy only because they make HIGH rarer (25–29 %). Always predicting LOW already scores 71–75 % under those definitions. Their skill is +0.04 to +0.10 (A: +0.097), their gain over persistence is smaller (+0.06 to +0.07 against +0.125), and their HIGH recall drops to 0.67–0.72 (A: 0.88).
2. **Nothing improves the model's ranking of provinces.** AUC measures how well the forecast orders provinces, independent of the cut. It is highest for A, at every lead.
3. **Regional bias.** For every leakage-free method, Luzon has 9 % HIGH, as with A. The transformations don't change who is food insecure, only where the line is drawn. The leaky target-round versions inflate Visayas to 93 % HIGH.
4. **Lowering the values is not neutral.** E shifts every value down about 4–5 points, the HFIAS–FIES gap. That produces more LOW classes and higher accuracy, but fewer HIGH provinces detected. This is the "artificially lower the values" outcome the brief warns against.

## 6. Recommendation

- **Keep the original FNRI percentages as the target**, modelled on the logit scale as E168 already does, **and the panel's 50 % rule.** It is:
  - leakage-free;
  - officially measured;
  - stable across rounds;
  - the best at ranking provinces (AUC);
  - the best at catching HIGH provinces (recall 0.88);
  - the furthest ahead of persistence (+0.125).
- **Reject:**
  - **B, C and D in their target-round form**, because they use the outcome being forecast (leakage);
  - **B, C and D as-of**, because their cut depends on which provinces happened to be surveyed in the previous round, they no longer mean "high", and they lower HIGH recall;
  - **E as the classification rule**, because it rests on a 20-province, single-year bridge with a wide slope interval, and its higher accuracy comes from fewer HIGH cases. It can be reported as a sensitivity check.
- **Sparse provincial data** are best handled by modelling sampling error, which E168 already does (1/SE² weights, shrunk anchors, probabilistic labels). No extra transformation is warranted.
- **Thesis:** report this comparison as evidence that the target definition was examined and that the original values are the defensible choice. Do not adopt a transformation.

## 7. How the 50 % threshold should be read

- **HIGH:** a majority of households are forecast moderately or severely food insecure (HFIAS). That is the panel's rule.
- **LOW:** "below that majority line", **not** "low food insecurity". The 2027-Q1 forecasts are 25–36 %, about one in three households in Quezon and Rizal.
- **FNRI's own severity bands** apply to *any* food insecurity (mild, moderate and severe): Very Low < 20 %, Low 20–39.9 %, Medium 40–59.9 %, High 60–79.9 %, Very High ≥ 80 %. For example, Quezon 2019 was 44 % moderate + severe but 61.9 % any-level, which is FNRI "High". The thesis and dashboard should say so, so that LOW is not read as "no problem".

## 8. Backend changes and tests

- **Model:** none. No transformation is adopted, and the dashboard is unchanged by this study.
- **Wording (recommended, separate decision):** show "LOW (below the 50 % HIGH line): X % of households forecast moderately or severely food insecure" wherever the class appears. This uses the existing text fields, with no design change.
- **Test added:** `tests/unit/test_e175_target_scaling.py` checks that:
  - the FNRI source files are unchanged (hash);
  - every target-round method is flagged as leaking;
  - the logit method gives the same classes as the original.
