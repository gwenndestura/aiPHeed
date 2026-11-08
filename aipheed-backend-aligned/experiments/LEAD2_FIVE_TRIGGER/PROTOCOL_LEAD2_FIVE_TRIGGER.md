# LEAD2_FIVE_TRIGGER protocol (frozen before any candidate or ablation is scored)

**Branch:** `aiPHeed/forecast-research`. **Written:** 2026-10-28. The SHA-256 of this file goes in `runner/PROTOCOL_SHA256.txt` and is committed before scoring. The served model (P0H4, seal a498b5ef), the candidates P0H4-U (bd6572e1) and Z0-U (b7162a63), and every frozen artifact stay unchanged.

**Honesty note.** Every 2021-2026 quarter has been inspected by earlier work, so every result here is development evidence. Selection uses the DEV block only (targets ≤ 2024-Q4). The CONF block (targets 2025-Q2 to 2026-Q3) is reported, but it has also been seen before.

## 1. What was established before scoring (`out/input_audit.json`)

- **The served unified LightGBM is reproduced exactly from code.** P0 refits on the served model's own stack (`snapshot_l2.py`, leads 1-15 trained together) match the served P0_price to within 5e-7 on all 250 evaluation rows. The served dashboard rows match the refit to within 5e-7.
- **All 21 columns reach the model:** 13 E107 columns, A_mom, the 2 GDELT news columns, lead, and 5 world-price columns.
- **No duplicates or misalignment.** There are no duplicate rows. The PSA month, the SWS publication date and the news publication date all precede every issue date.
- **One input defect:** N1 (XLM-R FSSI-v3) is missing in 79% of evaluation rows. Most province-quarters have 0-4 admitted headlines, against a minimum of 5.
- **Class balance (binary T43c; the Chapter I definition has no MODERATE class):**

  | Lead | LOW | HIGH | Quarters | Quarters with any HIGH |
  |---|---|---|---|---|
  | 1 | 53 | 17 | 14 | 7 |
  | 2 | 48 | 17 | 13 | 7 |

## 2. Five trigger groups (the user's definition, 2026-10-28)

| Group | Model columns |
|---|---|
| Market and food prices | A1_food, A1_gap, A_mom (A1), A2, A3, W_rice_yoy, W_rice_mom, W_cereal_yoy, W_crude_yoy |
| Climate stress | C1, C2, C3, C4, W_urea_yoy |
| Employment and remittances | E1, E2 |
| News and NLP | N1 (XLM-R FSSI-v3), G_pri_yoy, NG_gap_price (GDELT) |
| Poverty and social vulnerability | V1 |

- **H1** (regional SWS hunger outlook) is the hunger condition of the Chapter I target. It stays in the model, is reported separately, and is not a trigger.
- **`lead`** is the horizon.

## 3. Cause tests (each with a confirm/reject rule)

| ID | Suspected cause | Test | Confirmed if |
|---|---|---|---|
| CT1 | P0H4-U misses HIGH because of the price part | Classify each Lead-2 false negative (S-AB) by π_H < 0.5, π_P < 0.5, or both | ≥ 4 of the misses have π_P < 0.5 with π_H ≥ 0.5 |
| CT2 | News/NLP is under-used because of the N1 coverage defect | Candidate C1 vs C0 (§4); news-group ablation (§6) | C1 lowers Lead-2 DEV Brier by ≥ 0.005 |
| CT3 | Changes in risk between quarters are poorly represented | Candidate C2 vs C0 | C2 lowers Lead-2 DEV Brier by ≥ 0.005 |
| CT4 | Class imbalance suppresses HIGH recall | Candidate C4 (class weight forced to balanced) vs C0 | C4 raises Lead-2 recall by ≥ 2/17 without lowering Lead-2 DEV Brier |
| CT5 | Probabilities are miscalibrated | Candidate C5 (Platt scaling fitted on inner-fold predictions only) vs C0 | C5 lowers Lead-2 DEV Brier by ≥ 0.005 |
| CT6 | Too little predictive information two quarters ahead | Price-term AUC and Brier at Leads 1-2; R5 Brier gaps | Reported: confirmed if Lead-2 price-term AUC < 0.80 and the Lead-2 R5 p-value vs climatology > 0.10 for C0 and the selected candidate |
| CT7 | A trigger group is excluded or broken | §6 ablation and permutation; input audit | A group whose removal changes no prediction, or whose columns are constant |
| CT8 | The dashboard does not show the evaluated forecasts | Input audit (dashboard vs refit) | max \|Δ\| > 1e-4 |
| CT9 | Z0-U does not beat climatology because of power | Cited from FORECAST_RESEARCH_II §8 (MDE 0.05-0.07) | — |

## 4. Candidates

All are one unified LightGBM across leads (the UNI-FINAL U2 recipe, monotone A1/A_mom, grid and inner chronological selection unchanged), on all 12 indicator families, × π_H on the S-AB schedule (Lead 1 at quarter start; Leads ≥ 2 re-issued after the SWS release).

| ID | Change |
|---|---|
| **C0** | P0 as served (P0H4-U) |
| **C1** | C0 + `N1_reg`: a regional pooled XLM-R news index. It is the mean intensity of every province-attributed admitted headline of quarter t published before O(t) (`FINAL_SYSTEM_SELECTION/annotation/model_inputs/fssi_articles.csv`), when there are at least 5 such headlines; otherwise NaN. N1 itself is unchanged. |
| **C2** | C0 + risk-history and transition columns, all known at O(t): |
| | - `PC_now` = 1 if F_ex > 0 or G_ex > 0 (the price condition on the newest 3 CPI months); |
| | - `PC_hist4` = the share of the province's last 4 known quarters with the price condition met; |
| | - `dF_ex`, `dG_ex` = the change in F_ex and G_ex since the previous origin. |
| **C3** | C1 + C2 |
| **C4** | C0 with class_weight = balanced in every grid configuration |
| **C5** | C0 + Platt scaling. A logistic regression on logit(π_P) is fitted on the out-of-fold predictions of the last 4 training origins (inner folds) and applied at the origin. |

**Selection rule (DEV only).**
- Choose the candidate with the lowest Lead-2 DEV T43c Brier, subject to its Lead-1 DEV Brier not exceeding C0's by more than 0.005.
- It replaces C0 only if its Lead-2 DEV Brier is at least **0.005** lower than C0's. Otherwise **C0 is kept**, because it is the simplest.
- The selected candidate is called **FINAL**.

## 5. Evaluation (rules unchanged)

**Rows.** The FR evaluation rows, Leads 1-4 (70/65/60/55).

**Metrics**
- Accuracy, balanced accuracy;
- per-class precision, recall and F1 (HIGH and LOW);
- HIGH recall and the list of missed HIGH cases;
- Brier score, log loss, calibration;
- vs persistence (same information, S-AB), climatology and always-LOW;
- by target quarter and by lead;
- n_eff and quarter-block 90% CIs.

**Pass criteria (fixed, unchanged).** R1-R7 of FORECAST_RESEARCH §6. The maximum reliable lead is the longest k with Leads 1..k all passing. A lead that fails any criterion is **not reliable**, whatever its accuracy.

**Before/after.** FINAL vs C0 on identical rows, with the bootstrap Brier difference and its CI.

## 6. Five-group contribution (on FINAL)

1. **Leave-one-group-out refit**, the same walk-forward for each of the 5 groups. Report ΔBrier (T43c S-AB and price term) by Lead 1-4, with a 90% quarter-block CI and one-sided p, Holm-corrected across the 5 groups.
2. **No-trigger refit:** only H1 and lead remain. This tests whether the triggers collectively add information.
3. **Group permutation:** the model is fixed; each group's columns are replaced by the same province and lead's values from a random other evaluation origin, 20 draws.
4. **SHAP:** the mean |SHAP| share per group by lead. Reported as model influence, not as a contribution.
5. **Classification per group:**
   - *predictive*: the leave-one-out CI excludes 0 (removal hurts) at some lead, and the permutation Δ > 0 there;
   - *weak*: point estimate > 0 but the CI includes 0;
   - *no demonstrated value*: otherwise.

   For any group that is not predictive, the cause is checked: coverage, national-only variation, redundancy (correlated columns), or too few observations.

## 7. Dashboard (backend only; no frontend design change)

- The bars show the five groups of §2 using the existing keys: market, climate, employment, news, poverty. For each group:
  - its indicators;
  - its data status at the issue date;
  - its relative model influence (SHAP);
  - its measured held-out contribution class (§6);
  - a plain explanation.
- No direction is stated where the evidence does not support one.
- Lead-2 forecasts keep the "experimental, not validated" status text.

## 8. Not allowed

- Changing the target, thresholds, evaluation rows or R1-R7.
- Fitting anything on evaluation outcomes.
- Choosing a probability threshold other than 0.50.
- Pre-2021 data, or new data collection.
- Changing served artifacts or seals.
- Pushing or deploying.
