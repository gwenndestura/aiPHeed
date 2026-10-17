# E52 protocol: Chapter 1 acceptance tests for the food-price-pressure candidate (frozen before any E52 score)

**Written:** 2026-10-17 on branch `e46-lead2-policy`, from 6fc1a4f.
**Freeze:** SHA-256 (LF) in `runner/PROTOCOL_SHA256.txt`, committed before the baseline comparison runs. Run once, then a byte-identical repeat.

## 0. Evidence status

**The candidate's historical score was seen in E51.**
- E46's price component scored 0.760 accuracy and 0.752 balanced accuracy on the PS rows. It was designed in E46/E47 while examining those quarters.
- So E52's historical comparison is **confirmation against the complete Objective 4 baseline set, not independent validation.**
- **The independent test is prospective:** the frozen 2027-Q1..Q4 forecasts (section 6).

## 1. Target (exploratory; requires adviser approval)

**PS**, provincial food-price pressure:
- **HIGH** if the province's PSA food CPI YoY (quarter mean) > its 2021–2022 60th percentile, **or** food minus headline YoY > its 2021–2022 60th percentile.
- **Data:** observed from PSA CPI only, available for every quarter, 2025-Q2/Q3 included.
- **Not hunger or food insecurity.** SWS hunger is reported separately as a regional observed indicator.
- **Why:** E51 found PS and RQ to be the only targets meeting all score-free criteria. The thesis label is saturated in 2024–2026 by the SWS level shift.

## 2. Candidate (fixed; no retuning)

**E52-PS** = E46 I7's price component, P(price signal at t+2), exactly as committed in `E46/runs/i7_20261017T000111Z/predictions_i7.csv` (`I7_p_price`).
- **Model:** base-effect food and gap projections from PSA CPI + ridge residuals on the five trigger groups, news and policy (embargoed forward-chaining selection); bivariate-normal probability; decision ≥ 0.5.
- **Issue time:** 00:00 day 1 of quarter t+1 (E47 cutoff audit).

## 3. Baselines (Chapter 1 Objective 4 and Hypothesis 3, on identical rows)

| Baseline | Specification |
|---|---|
| **B1 naive persistence** | the latest PS label available at the origin |
| **B2 PSA-only indicators (logistic)** | E36 `lr_predict` on GOV inputs (`y_last` = PS persistence) |
| **B3 PSA-only indicators (LightGBM)** | E36 `lgbm_predict`, GOV, G1 |
| **B4 NLP-only sentiment (logistic)** | `lr_predict` on NLP inputs |
| **B5 NLP-only sentiment (LightGBM)** | `lgbm_predict`, NLP, G1 |
| **B6 logistic regression, combined** | `lr_predict` on COMB |
| **B7 E38 LightGBM procedure on PS** | nested selection, prior shift, inner threshold (E51 D-1 guard) |
| **Naive** | always-LOW, always-HIGH, climatology (training prevalence) |

- **Decisions:** 0.5 for all logistic and LightGBM baselines; B7 uses its inner threshold.
- **Training rows:** E38's posting rule. **Labels:** PS of each training target.
- **Rows:** every PS target quarter where the candidate and all baselines exist; expected 2024-Q2..2026-Q3, 10 quarters, 50 rows.

## 4. Acceptance criteria (Chapter 1 Objectives 2 and 4)

The candidate is **accepted for development** only if all hold on the identical rows:

| ID | Criterion |
|---|---|
| A1 | accuracy ≥ 0.75 |
| A2 | balanced accuracy ≥ 0.70, HIGH recall ≥ 0.60, LOW recall ≥ 0.60 |
| A3 | Brier score lower than every baseline's |
| A4 | balanced accuracy higher than every baseline's |
| A5 | minimum leave-one-quarter-out accuracy ≥ 0.70 |

**Also reported** (not gates): precision, F1, AUC, confusion matrix, per-quarter accuracy, calibration-in-the-large.

## 5. Explanations (Objective 2 and section 6 of the task)

**Method:** grouped attribution of the served probability P(price signal), the E50 method.
- Each trigger group's inputs are moved to their training mean, all else fixed.
- Market includes the base-effect food and gap projections built from PSA CPI.
- The result is the log-odds change, signed.

**Status rule (E47):**
- **contributes:** the group moves food YoY or the gap by ≥ 0.1 points;
- **no_effect:** below that;
- **insufficient_data:** no input of the group has a value at the issue date.

**Checks:**
- the ridge contributions plus the base deviation reconcile with the model's F̂ and Ĝ, to machine precision;
- the direction is checked against a controlled ±1 SD change of the group's residual inputs.

**Dashboard:** the top two or three contributing groups, each with its direction, its evidence (indicator and period) and its data status, plus one plain-language sentence. The text says these are model attributions, not causes.

## 6. Prospective freeze

- **What:** E52-PS 2027-Q1 probabilities, taken from the already frozen I7 file (`E46_I7_PROSPECTIVE_2027Q1.json`, `I7_p_price`, sha `5592d53e…`), recorded in `frozen/E52_PS_PROSPECTIVE_2027Q1.json`.
- **Acceptance:** criteria A1, A2 and A3 (against persistence and always-LOW/HIGH) on 2027-Q1..Q4 PS outcomes (20 province-quarters).
- **Nothing is reselected.**

## 7. Serving

- **Where:** behind `AIPHEED_LEAD2_MODEL=e52` (experimental, "food-price pressure, not food insecurity").
- **Unchanged:** production E38 and every other flag.
