# LEAD2_FINAL protocol: food-price composition and breadth (frozen before scoring)

**Branch:** `aiPHeed/forecast-research`, continuing from `ffdd8bf`. **Written:** 2026-10-28. The SHA-256 of this file goes in `runner/FINAL_SHA256.txt`. Both are committed before `runner/final.py` scores anything.

**Unchanged:** the T43c target, the S-AB hunger term, the evaluation rows (Leads 1-4: 70/65/60/55), R1-R7, the 0.50 cut, the served P0H4 (seal a498b5ef) and P0H4-U (bd6572e1).

## 1. Step 1 finding (diagnostic run before this protocol; `runner/limits.py`, `out/limits.json`)

| Check (Lead 2, P0H4-U) | Result |
|---|---|
| Perfect price knowledge × model hunger term | accuracy 0.938, recall 1.00 |
| Perfect hunger knowledge × model price term | accuracy 0.677, recall 0.59 |
| Price-term AUC on the 55 rows where hunger is HIGH (the rows where price decides the label) | model 0.731, flat projection 0.741 |
| Same, Lead 1 | model 0.743, flat projection 0.949 |

Primary category of the 13 Lead-2 errors (precedence rule in `limits.py`; `out/limits_errors.csv`):

| Category | FN | FP |
|---|---|---|
| Sudden: hunger information absent at the cut-off (SWS 11.3 tie) | 3 | 0 |
| Uncertain label (realised margin within ±0.10) | 1 | 1 |
| Model behaviour (projection on the realised side, model not) | 1 | 1 |
| Price surprise that the 10 nearest training analogs voted for (indicators could plausibly anticipate it) | 2 | 1 |
| Price surprise that the analogs voted against (sudden; the data cannot anticipate it) | 0 | 3 |

**Reading.**
- The hunger misses are not recoverable: the deciding reading was published after the issue date. Earlier hunger-forecasting work (E90, E109-E113) found nothing that beats the latest reading.
- The two rounding-level labels cannot be improved honestly.
- **The realistic opportunity is the price part:** the 8 price-related errors, 2 of them model behaviour and 3 with analog support. Every error the price part could fix is a question of whether the current price pressure **persists or reverts** over the next quarter.
- At Lead 2 the LightGBM already uses the aggregate price information about as well as the flat projection does (AUC 0.731 vs 0.741). A gain therefore needs information that the aggregate food index does not hold.

## 2. Candidate signal (genuinely new)

| Item | Statement |
|---|---|
| Signal | **Composition and breadth of food inflation at the cut-off**, from the PSA provincial CPI by food subgroup |
| Theory | Supply shocks to **fresh food** (fish, fruits, vegetables) reverse with the next harvest or catch. Pressure in **storable or processed food** (rice, corn, meat, oils, sugar) is persistent. This is the reason official "core excluding fresh food" indices exist. **Breadth** (the share of items accelerating) is a standard diffusion measure: broad acceleration signals generalised pressure that continues, while a rise driven by one item tends to fade. The signal therefore targets exactly what decides the price errors: an above-threshold reading that will revert (FP) versus a below-threshold reading that is broadening (FN). |
| Columns | `K_core`: weighted non-fresh food y/y over the newest 3 months minus the province's frozen food threshold. `K_fresh_gap`: weighted fresh y/y minus non-fresh y/y. `K_diff`: weight share of the 8 subgroups whose y/y in the newest month exceeds their y/y 3 months earlier. Built by `runner/features_v4.py`; no outcome is read. |
| Data | PSA OpenStat 0012M4ACP22, 5 provinces × 8 subgroups, 2021-01..2026-09, no missing values. PSA 2018 weights. Its food index equals the model's food CPI exactly (max difference 0.0). |
| Coverage | First value at origin 2022-Q2 (y/y plus 3 months needs 15 months of 2021+ data). 100% of evaluation origins (2022-Q4 onward). Training rows before 2022-Q2 are blank and are left blank (LightGBM missing-value handling), never imputed with zero. |
| Availability | Released in the same PSA CPI release as the food index (about the 5th of the following month). Each row reads only months ≤ its `psa_newest_month`, the cut-off month the A1 columns already use; this is asserted in code. |
| Why it is different | Every tested price feature uses the **aggregate** food or headline index: flat, anchored, structural and random-walk projections, momentum, acceleration, volatility, recency weighting and transitions. The only earlier use of subgroups (E84 S-COMP) simulated each subgroup **forward** as a structural projection outside the LightGBM. Composition and breadth at the cut-off have never been inputs to any model. Correlation on evaluation origins: K_core with A1_food 0.54; K_diff with accel 0.51; K_fresh_gap with A1_food 0.10. |
| Monotone directions (theory, fixed now) | K_core +1, K_diff +1, K_fresh_gap −1, plus the existing A1_food, A1_gap, A_mom +1 |

## 3. The one experiment

- **B0** = P0H4-U: the U2 recipe as in `lt_lib.py`, refitted at every origin; it must reproduce C0 within 1e-5.
- **K1** = B0 + `K_core`, `K_fresh_gap`, `K_diff`.

Everything else is the same: one unified LightGBM over all leads, all 12 indicator families, the same grid and inner chronological selection (last 4 training origins, log loss), the same seed, the same training rows (outcomes known at the origin), the same S-AB hunger term (P = π_H × π_P), and the same origins and evaluation rows. There is no tuning on evaluation outcomes and no second variant.

## 4. Metrics reported (K1 and B0, Leads 1-4)

- Accuracy and its 90% quarter-block CI, balanced accuracy, HIGH precision, recall and F1, TP/FP/FN/TN, false alarms, missed HIGH cases.
- Brier, and the bootstrap Brier difference vs B0 (90% CI, one-sided p).
- R1-R7 with every failed criterion.
- DEV (targets ≤ 2024-Q4) and CONF (2025-Q2..2026-Q3) blocks; accuracy by thirds, leave-one-quarter-out, accuracy by target year.
- Which of B0's 13 Lead-2 errors K1 fixes, and which new errors it makes.
- Mechanism (diagnostic, not selection): standardised HIGH-minus-LOW mean difference of each K column on the training rows known at the final origin, overall and among rows whose flat projection was already above threshold (does K separate pressure that stayed from pressure that reverted?). Also the mean |SHAP| share of the K columns at Lead 2.

## 5. Adoption rule (frozen)

K1 replaces B0 as the research candidate **only if all of the following hold:**

1. **Existing selection rule** (as in LEAD2_IMPROVE):
   - Lead-2 DEV Brier at least 0.005 lower than B0;
   - Lead-1 DEV Brier not more than 0.005 higher;
   - Lead-2 DEV balanced accuracy not lower.
2. **No concealed regression** (all 65 Lead-2 rows):
   - accuracy, balanced accuracy, HIGH precision and HIGH recall each no more than 0.02 below B0;
   - new false alarms ≤ new hits;
   - Lead-2 CONF accuracy not below B0.
3. **Lead 1 still passes R1-R7.**

**Lead 2 is called reliable only if K1 (if adopted) or B0 passes all of R1-R7 at Lead 2.** Lead-1 and Lead-2 results are reported separately. If K1 is not adopted, B0 = P0H4-U is retained.

## 6. Not allowed

- Changing the target, thresholds, evaluation rows, R1-R7 or this rule after scoring.
- A second candidate, re-tuned monotone directions, or a different subgroup split after scoring.
- Pre-2021 data, new data collection, changing served artifacts or seals, pushing or deploying.

All 2021-2026 quarters have been examined by earlier work, so the results are **development evidence**. The sealed prospective forecasts remain the independent test.
