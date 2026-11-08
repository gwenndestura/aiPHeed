# LEAD2_CR_RESOLVE protocol: root causes of CR's Lead-2 failure and one justified correction (frozen before scoring)

**Branch:** `aiPHeed/lead2-lgbm-tuning`. **Written:** 2026-10-29. The SHA-256 goes in `runner/CR_RESOLVE_SHA256.txt`. Both are committed before `runner/cr_resolve.py` scores the candidate.

**Status of the rows.** Every 2021-2026 quarter has been examined in earlier experiments (§§11-21), so everything below is **development evidence**. The sealed prospective forecasts (`sealed/cr_prospective.csv`, dd293e2e) remain the only independent test.

**Unchanged:**
- the T43c target and labels;
- the S-AB timing (Lead 1 at quarter start; Leads ≥ 2 re-issued after the SWS release, at the latest day 1 of month 3);
- the day-10 CPI rule of CR;
- the 65 Lead-2 evaluation rows; R1-R7; the 0.50 cut; `final.adoption_rule` (compared with B0 = P0H4-U);
- the 21 model columns (12 indicator families);
- the U2 LightGBM recipe (8-configuration grid, inner chronological selection on the last 4 training origins, seed 2027, monotone A1/A_mom);
- served artifacts and seals.

## 1. Reproduction (prerequisite)

Refit P0H4-U (B0) and CR from the committed stack and `data/cpi_refresh.csv`. Both must match the committed rows (`out/cpi_refresh_rows.csv`) within 1e-5. P0H4 comes from the committed replay (`out/candidates.csv`); the served export's retrospective rows must equal it exactly. If reproduction fails, nothing else is scored.

## 2. Root causes already established (no new scoring needed; cited)

| Cause | Evidence | Fixable with the available data? |
|---|---|---|
| Hunger cap | 3 of the 17 Lead-2 HIGH cases (2023-Q4) have π_H = 0.5 exactly, so P < 0.5 for any price part (§17.2) | No |
| Price moves after the issue | Most remaining misses and false alarms are price moves after the cut-off (§15.1, §17.3) | Partly: CR's refresh |
| Target content | The hunger part is regional and met in 11 of 13 quarters, so provincial variation is price pressure only (§21.3) | No (needs a provincial outcome) |
| CR's R6 rests on one row, cuts 0.475-0.50 and the day-10 rule | §20.4 | No |
| Sample size | 13 quarters; about 58 needed (§20.5) | No |

## 3. The one candidate: CR-CAL (training-only recalibration of CR's price part)

- **Hypothesis.** CR's probabilities are mis-scaled. Diagnostics computed on evaluation rows motivated the test; they are disclosed as such and are not used to fit anything:
  - overall calibration slope 1.50 (under-confident);
  - calibration-in-the-large +0.20 in 2025-26 (over-forecasts).

  The price part is a LightGBM with strong L2 regularisation and monotone constraints on 300-900 training rows, which typically compresses probabilities.

  A recalibration fitted **only on training data** could:
  - sharpen the ordering already present (CR AUC 0.85 vs P0H4-U 0.76);
  - reduce over-forecasting.

  Neither the cut nor the ordering within a quarter is chosen on evaluation rows.
- **Method.** At each origin t, with the configuration CR's inner selection picked:
  1. For each of the last 4 training origins o (the same folds as `lt_lib.select`), fit on training rows with target ≤ o − 1 and predict rows at o. This gives out-of-fold price-part predictions with their price labels, all known at t.
  2. Fit a Platt map: logistic regression of the price label on logit(π_P), unpenalised.
  3. If the folds have fewer than 30 rows or a single class, use the identity map.
  4. Apply the map to the test rows' π_P.
- **Prediction.** P = π_H (S-AB) × calibrated π_P, HIGH at 0.50.
- **Adoption.** CR-CAL becomes the research candidate only if both hold:
  1. `final.adoption_rule` vs B0 passes exactly;
  2. R1-R7 pass at Leads 1 and 2.

  CR is re-scored under the same unchanged rule. No second candidate is scored after this one.

## 4. Diagnostics (reported, never used to choose anything)

1. **Settings sensitivity:** CR with each of the 8 grid configurations fixed at every origin. Lead-2 accuracy, recall, Brier and R1-R7.
2. **Feature-importance stability:** CR's mean |SHAP| share per indicator family at Lead 2, by origin.
3. **Train / validation / test gap:**
   - training-row price-part Brier;
   - inner-fold (validation) Brier;
   - out-of-sample Brier, by origin.
4. **Five-group ablation of CR** (research-only refits; the final model keeps all 12 families). Groups, as the request names them:
   - market and prices: A1, A_mom, A2, A3, world rice, cereal and crude prices;
   - climate stress: C1, C2, C3, world urea;
   - employment and remittances: E1, E2;
   - poverty and social vulnerability: V1;
   - news and NLP: N1, G_pri_yoy, NG_gap_price.

   Fish production (C4) and the regional hunger outlook (H1) are reported separately.

   Measure: ΔBrier of the T43c probability when the group is removed, with a 90% quarter-block CI, a one-sided p (removal hurts) and Holm correction across the five groups.
5. **Errors** by province, target quarter, class and period; leave-one-quarter-out R1-R7.
6. **Timing:**
   - verify that every input was published before its issue date (CPI rule, SWS, news);
   - verify that target quarter = origin + lead;
   - day-15/day-20 release sensitivity (from §20).
7. **Serving consistency:**
   - the served export's predictions, model and target equal the evaluated P0H4;
   - the regional forecast equals the documented mean of province scores.

## 5. Not run, with the reason

- **Class weighting:** lowers recall in 180/180 pairs (§16).
- **Own-history, persistence or lagged-label features:** no gain in LEAD2_TUNING N2, E95 cumF4 and E61.
- **Larger grids:** 360-configuration search, no gain (§16).
- **News variants:** the existing ablation shows no Lead-2 gain (§6).
- **Threshold changes:** prohibited.
- **Alternative release-day candidates:** already scored as a sensitivity (§20.4); choosing one now would be selection on known results.

## 6. Not allowed

Changing the target, rows, cut, criteria, rule, release rule, columns or grid after scoring; a second candidate; moving test quarters into training; pushing, merging, enabling flags or changing served artifacts.
