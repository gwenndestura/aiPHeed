# LEAD2_IMPROVE protocol (frozen before any candidate is scored)

**Written:** 2026-10-28. The SHA-256 goes in `runner/IMPROVE_SHA256.txt` and is committed before `improve.py` runs. The target (T43c), the evaluation rows, R1-R7, the lead convention (Lead 1 = current quarter, Lead 2 = next quarter) and the served model all stay unchanged.

## 1. Defects addressed and hypotheses

| ID | Defect (evidence) | Change | Why it should help |
|---|---|---|---|
| B1 | 3 of 7 Lead-2 misses are "price rose after the issue". The flat projection's error has a regime-dependent bias. The BSP-anchored projection cut food-inflation RMSE at Lead 2 from 2.37 to 1.93 (FR-II §5.2) but was never given to the LightGBM. | Add `A1_food_anc` and `A1_gap_anc`: the anchored projections of the food and gap excess. Monotone increasing, like A1. | A better price-level forecast should move borderline price conditions to the right side |
| B2 | The price model is trained on the 2022-23 inflation regime and over-/under-shoots after the regime changes (FR-II FR0-a, Z1 overshoot in 2025) | Recency weighting of training rows: weight 0.5^((t − q)/HL). HL ∈ {none, 8, 4} quarters, chosen per origin by inner-fold log loss (training origins only), together with the configuration grid. | Lets the model follow the current price regime |
| B3 | B1 + B2 | Both | — |
| B4 | The four non-market triggers enter as levels only. Delayed and changing effects are not represented. | Add `dC3`, `dC4`, `dE1`, `dE2` (change since the previous origin), `C2_2q` (typhoons in the last 2 quarters) and `C1_run` (consecutive quarters with an El Niño alert) | Tests whether climate, employment, fish production and remittances carry signal the current features miss |

All candidates are the same unified LightGBM (UNI-FINAL U2 recipe, trained on every lead together, inner chronological selection), with all 21 existing columns (12 families), multiplied by π_H on the S-AB schedule. **B0** = P0H4-U, the reference.

All new columns use only data published before the issue date: the PSA index through month 2 of the origin quarter, and origin-level trigger values already in the stack. The anchored projection was verified to equal the served flat projection when the drift is 0 (Leads 1-3 exact).

## 2. Selection (no final-test data)

- **DEV** = targets ≤ 2024-Q4. **CONF** = targets 2025-Q2 to 2026-Q3. CONF is held out from this selection; it was seen by earlier experiments.
- Among B1-B4, choose the lowest **Lead-2 DEV Brier** (T43c, S-AB), subject to Lead-1 DEV Brier ≤ B0's + 0.005.
- It **replaces B0 only if** its Lead-2 DEV Brier is ≥ 0.005 lower than B0's **and** its Lead-2 DEV balanced accuracy is not lower than B0's.
- Otherwise B0 stays.

## 3. Reporting

For B0-B4 at Leads 1-4:
- accuracy (90% CI), balanced accuracy;
- HIGH precision, recall and F1; TP / FP / FN / TN;
- Brier score, log loss;
- baselines (persistence, climatology, always-LOW);
- R1-R7 pass/fail;
- DEV and CONF separately;
- ΔBrier vs B0 with a quarter-block CI;
- the 7 earlier misses: caught or not;
- new false alarms.

## 4. Error patterns (descriptive)

Every Lead-2 error of B0 and of the selected model is classified as one of:
- hunger part ≤ 0.5;
- projected price margin < 0 ≤ realised margin (price rose after the issue);
- projected ≥ 0 > realised (price fell after the issue);
- model behaviour.

Plus the borderline flag (|realised margin| < 0.5).

For each missed HIGH case, the **early-warning check** lists the indicators whose value at the cut-off lay beyond the 75th percentile of training rows in the direction that the training HIGH rows took (higher or lower mean).

## 5. Acceptance (frozen; unchanged)

R1-R7 per lead, maximum reliable lead as before. The 80% accuracy figure is a goal, not a criterion. A Lead-2 pass is development evidence, not validation.

## 6. Not allowed

- Changing the target, rows, thresholds or criteria.
- Choosing HL or the configuration on evaluation rows.
- Re-running a candidate with new settings after seeing results.
- Replacing the served model or pushing.
