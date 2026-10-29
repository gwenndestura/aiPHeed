# LEAD2_ROOT_CAUSE protocol: corrections of CR justified by the row-level error analysis (frozen before scoring)

**Branch:** `aiPHeed/lead2-lgbm-tuning`. **Written:** 2026-10-29. The SHA-256 goes in `runner/ROOT_CAUSE_SHA256.txt`. Both are committed before `runner/root_cause.py` scores any candidate.

**Status of the rows.** Every 2021-2026 quarter has been examined before, so all results are **development evidence**. The sealed CR forecasts (dd293e2e) remain the only independent test.

**Unchanged:**
- the T43c target and labels;
- the S-AB timing;
- CR's day-10 CPI rule (release dates UNKNOWN, `data/psa_cpi_release_evidence.csv`);
- the 65 Lead-2 evaluation rows; R1-R7; `final.adoption_rule` vs B0 = P0H4-U;
- the 21 CR columns (12 families);
- the U2 grid and its inner selection, seed 2027;
- served artifacts and seals.

## 1. Evidence from the error analysis (`runner/rootcause_errors.py`, run before this protocol)

| Finding | Data | Correctable? |
|---|---|---|
| 3 misses (2023-Q4) are hunger-capped: newest SWS at the re-issue (2023-Q2) = 11.3 exactly, so π_H = 0.5; realised 14.3; no later reading existed by the window cap | `out/rootcause_errors.csv` | No |
| The price part is the binding component: hunger part right on 85% of rows, CR price part on 69%; oracle true-price Lead-2 accuracy 0.938 vs true-hunger 0.769 | `out/rootcause_errors.json` | Partly |
| **6 of CR's 7 false alarms are price reversals**: the projection was above the threshold (+0.43 to +2.33) and the realised margin fell below it (−0.07 to −3.02) | same | Hypothesis: the flat projection carries current pressure forward |
| 3 misses are small price rises after the issue (realised margin +0.19 to +0.69) | same | Borderline labels; not targeted |
| 2 false alarms (2024-Q3) are model behaviour: projection negative, π_P 0.61-0.77, with the rice inputs (A3, world rice) in their top quartile | same | Hypothesis; not targeted (no issue-time rice-policy input exists) |

## 2. Candidates (each scored once)

1. **CR-ANC (price reversals).**
   - CR plus `A1_food_anc` and `A1_gap_anc`: the LEAD2_IMPROVE B1 anchored projections (monthly log index grown at the BSP target midpoint ln 1.03 / 12 instead of held flat), computed at each row's own CPI cut-off (m0r for Lead ≥ 2, as in CR; m0 for Lead 1).
   - Monotone +1, like the other A1 columns. 23 columns: all 12 families kept.
   - **Why:** a projection anchored to the inflation target reduces projected pressure exactly when inflation runs high, the situation of the 6 reversal false alarms. B1 cut the Lead-2 food-inflation RMSE from 2.37 to 1.93 in FR-II, but was only tested with quarter-start CPI.
2. **CR-T (missed HIGH cases; training-only threshold).**
   - CR's probabilities with a decision cut chosen per origin and lead by the ADDENDUM 2 rule (`threshold.py choose`), using only CR's own earlier forecasts whose outcomes were published before the origin:
     - balanced accuracy, over a grid of 0.10-0.50;
     - ties broken toward 0.50;
     - at least 4 quarters, 3 HIGH and 3 LOW, otherwise 0.50.
   - Brier is unaffected. Classification criteria use the calls.
3. **CR-WCAL (unstable calibration).**
   - CR's T43c probability recalibrated per origin and lead by a Platt map (unpenalised logistic regression of y on logit P), fitted on CR's own earlier forecasts with published outcomes (the same eligibility minimum as CR-T), otherwise identity.
   - **Why:** CR-CAL's maps came from 4 inner folds of the price part (slope −1.2 to 2.9). Genuine earlier out-of-sample forecasts of the final probability are the appropriate calibration data.

## 3. Evaluation and decision

- **Metrics for each candidate**, vs P0H4, P0H4-U, CR, CR-CAL, persistence and always-LOW:
  - Leads 1-4: accuracy (90% CI), balanced accuracy, precision, recall, F1, confusion matrix, Brier, calibration slope and in-the-large;
  - DEV and later blocks; by quarter and province; leave-one-quarter-out;
  - R1-R7 and `final.adoption_rule` vs B0.
- **CR-ANC only** (the candidates that refit the model):
  - settings sensitivity (8 fixed grid configurations);
  - five-group ablation (as in LEAD2_CR_RESOLVE);
  - train / validation / test Brier.
- **Eligibility:** `final.adoption_rule` vs B0 passes and R1-R7 pass at Leads 1 and 2.
- **More than one eligible:** the lowest Lead-2 DEV Brier is reported as the research candidate. Three candidates were compared, and this is disclosed.
- **Adoption into serving** needs the researchers' explicit approval in every case.
- **No eligible candidate:** CR stays the research candidate and P0H4 the served model.

## 4. Diagnostics reported, not used

- Target sensitivity on the same rows (each measures something different; no target is replaced):
  - hunger part alone (regional hunger condition);
  - price part alone (provincial price pressure);
  - persistence of each.
- Missingness of N1 and A3 in the error rows.
- News timing (article dates before the issue).
- CPI release status (UNKNOWN unless an official dated source is found).

## 5. Not run, with the reason

- **Class weighting:** lowers recall in 180/180 pairs (§16).
- **Own-history, lagged-label and regime-memory features:** E95 cumF4, LEAD2_TUNING N2, LEAD2_IMPROVE B4.
- **Larger grids:** no gain in §16.
- **Choosing a grid configuration post hoc** (e.g. the one that looked best in LEAD2_CR_RESOLVE D1): that would be selection on evaluation rows.
- **Removing groups.**

## 6. Not allowed

Changing the target, rows, criteria, rule, release rule or grid after scoring; another candidate; moving test quarters into training; pushing, merging, enabling flags or changing served artifacts.
