# FORECAST_RESEARCH protocol (frozen before scoring)

**Branch:** `aiPHeed/forecast-research`, cut from `aiPHeed/system-fixes` at 2fb7c8b. Written 2026-10-27, and its SHA-256 is recorded in `runner/PROTOCOL_SHA256.txt` before any arm is scored. The served model (P0H4, seal a498b5ef) and every frozen artifact stay untouched.

**Honesty note on test data.** Every 2021-2026 evaluation quarter has already been inspected by earlier experiments (E1-E114, FINAL_*, LEAD2_*, VALIDATOR_ONLY). Two diagnostics that motivated this protocol also looked at those quarters:
- **FR0-a.** The flat price projection has mean errors of +1.1, +2.2, +3.2 and +4.3 points at Leads 1-4.
- **FR0-b.** Recombining the existing Lead-1 hunger term with Lead-2 price parts raised Lead-2 accuracy.

So no 2021-2026 result here is a clean test. The only clean test is prospective: the forecasts sealed in §8 against outcomes published after today. The development/confirmation split in §6 is kept for selection discipline, not as proof.

## 1. Questions

| ID | Question | Comparison |
|---|---|---|
| FR1 | What limits each lead: the hunger term, the price term, or both? | 2x2 oracle table (true vs forecast hunger x true vs forecast price), Leads 1-4 |
| FR2 | Does a continuous model of the price-projection error beat the flat projection? Do the 12 families add anything to it? | Z0 / Z1 / Z2 / Z3 below, on continuous error (RMSE) and on the price condition and T43c (Brier) |
| FR3 | How much does the SWS publication lag cost? Does an issue made right after the SWS release make a longer warning reliable? | Issue schedule A vs B (§3), identical price parts and identical evaluation rows |
| FR4 | Which input families add held-out value to the selected model, at which leads, and how stable is that? | Refit ablation of each family, grouped ablation, permutation, SHAP by period (§7) |
| FR5 | Are the probabilities credible? | Reliability bins, calibration-in-the-large, calibration slope, ECE (diagnostic only, never fitted on evaluation outcomes) |

## 2. Target (unchanged)

The target is T43c: province p is HIGH in quarter q when **both** hold:
- SWS Balance Luzon involuntary hunger exceeds 11.3 (mean of the quarter's non-commissioned rounds);
- the province's food CPI YoY exceeds its frozen 2021-22 P60, **or** food minus headline YoY exceeds its gap P60 (`E40 label_spec.json`).

It is a composite proxy:
- the hunger term is an experienced-hunger measure (access dimension) at the regional level;
- the price term is a provincial affordability pressure, not observed food insecurity (SOURCES S1-S3).

No target is changed. The two components are also scored separately (FR1) so that DA can see which part carries a warning.

## 3. Issue schedules

**A (current).**
- Issue date: O(t) = day 1 of quarter t+1.
- Inputs: exactly the served cut-offs (CPI through month 2 of quarter t, SWS rounds published before O(t), and so on).
- Lead k targets quarter t+k. Warning before the target quarter starts = 3(k-1) months.

**B (SWS-update issue).**
- Issue date: I_B(t) = the day after the last non-commissioned Balance Luzon round of quarter t is published. If that has not happened by day 1 of month 3 of quarter t+1, then I_B(t) is that day.
- Inputs: the only change from A is that the hunger term uses the SWS rounds (all four areas) published before I_B(t). Every other input stays at its O(t) cut-off. That information is older than allowed, so it is strictly leakage-safe.
- Lead k targets quarter t+k. Each row records its warning in days: (start of target quarter) - I_B(t).
- The same-information persistence baseline uses the B hunger reading.
- Climatology uses the labels known before O(t). The CPI for quarter t is not complete under B either.

B is evaluated as an *additional* scheduled update. It does not replace A.

## 4. Hunger term (both schedules)

π_H(t,k) is the served H4 rule, with the issue date of the schedule:

> π_H = Φ((h_last − 11.3) / σ_h)
> - h_last = the newest published BL quarter mean (vintage mean of the published rounds);
> - h = (t+k) − (quarter of h_last);
> - σ_h = RMSE of h-quarter-ahead latest-reading errors, pooled over NCR, BL, Visayas and Mindanao, using readings published before the issue date. Fewer than 4 errors → 4.0; floor 0.5.

**Audit:** under A it must reproduce `pi_H4` of FINAL_ARCHITECTURE to within 1e-6.

## 5. Price term arms (π_P)

Notation:
- e_f = (F − θ_f) − A1_food;
- e_g = (F − HL − θ_g) − A1_gap;
- F, HL = the realised quarter-mean food and headline YoY;
- A1 = the flat (no-change) base-effect projection known at O(t).

**Training rows at origin t:** every (t' < t, lead 1-4, province) whose target quarter is ≤ t−1 and has a complete CPI quarter. This includes quarters without an SWS round, since the continuous error does not need SWS.

**From error to probability:**

> π_P = 1 − (1 − Φ((A1_food + ê_f)/σ_f,k)) · (1 − Φ((A1_gap + ê_g)/σ_g,k))

| Arm | ê | σ | Notes |
|---|---|---|---|
| **Z0** | 0 | RMSE of e by lead on the training rows | Reproduces P5 (audit: to within 1e-6) |
| **Z1** (bias-corrected projection) | Training mean of e by lead | SD of e by lead | |
| **Z2** (ridge) | Ridge regression of e on the feature set F12 below | RMSE of the inner out-of-fold residuals by lead | Standardised; training-median imputation; α ∈ {1, 10, 100, 1000} chosen by inner-fold MSE |
| **Z3** (unified LightGBM, the primary thesis candidate) | One LightGBM regressor per error type (food, gap), shared across leads 1-4, on F12 + lead | As Z2 | Grid: depth ∈ {1, 2}, trees ∈ {50, 150}, min_child ∈ {10, 20}; learning rate 0.05, λ_L2 5, colsample 0.8, deterministic, seed 2031. Selected by inner-fold MSE. |

For Z2 and Z3, a lead with fewer than 8 inner residuals uses the Z1 σ for that lead. Every σ has a floor of 0.25.

**Inner folds:** the last 4 training origins o. Each fold is fitted on rows with t' < o and target ≤ o−1, and predicts the rows of origin o.

**Feature set F12** (all 12 families eligible; nothing is forced to contribute):

| Family | Columns |
|---|---|
| A1 food CPI | A1_food, A1_gap, A_mom, F_ex, G_ex, mom1, mom6, accel, vol6, O_food_yoy, W_cereal_yoy |
| A2 headline | A2, W_crude_yoy |
| A3 rice | A3, R_rice_yoy, R_rice_mom3, O_rice_yoy, W_rice_yoy, W_rice_mom |
| V1 | V1 |
| C1 | C1, ONI_last, ONI_max12 |
| C2 | C2 |
| C3 | C3, W_urea_yoy |
| C4 | C4 |
| E1 | E1 |
| E2 | E2 |
| N1 | N1, G_pri_yoy |
| H1 | h_last |
| Lead | lead |

**Combined forecast:** p = π_H × π_P, the served product ("AND") rule.

## 6. Evaluation

**Rows.** The FINAL_ARCHITECTURE evaluation rows: origins 2022-Q4 to 2026-Q3, Leads 1-4, labelled targets. They are identical for every arm and schedule.

**Development / confirmation split.**
- DEV = targets ≤ 2024-Q4.
- CONF = targets 2025-Q2 to 2026-Q3.
- All reported results are reported over all rows, as well as by block.

**Metrics:**
- accuracy at 0.50, with a 90% quarter-block bootstrap CI;
- balanced accuracy;
- HIGH precision and recall, and the confusion matrix;
- Brier score, log loss, AUC;
- price-term Brier and AUC, and continuous RMSE of ê vs realised e;
- effective sample size (quarter ICC design effect).

**Baselines:**
- always-LOW;
- same-information persistence (per schedule);
- climatology;
- P0H4 (served);
- S3.

**Reliability rule at a lead** (the R1-R7 of CH1, unchanged):
- R1: ≥ 10 quarters and ≥ 40 rows;
- R2: accuracy ≥ 0.75;
- R3: balanced accuracy ≥ 0.70;
- R4: accuracy > always-LOW and > persistence;
- R5: Brier below persistence and below climatology, one-sided bootstrap p < 0.10 for both;
- R6: precision ≥ 0.60 and recall ≥ 0.60;
- R7: accuracy ≥ 0.60 in each chronological third, and minimum leave-one-quarter-out accuracy ≥ 0.70.

**Maximum reliable lead:** the largest k such that Leads 1..k are all reliable.

**Selection** (per schedule, made before reading CONF results):
- Choose the arm with the lowest DEV T43c Brier averaged over Leads 1-3.
- Z3 is chosen whenever it is within 0.002 of the best, because the thesis requires a LightGBM model.
- If Z3 is more than 0.002 worse, the report must say that LightGBM adds no development value over the chosen arm. Z3 is then still reported as the thesis candidate, with that disclosure, and the serving recommendation follows the evidence.

**Superiority claims:** Brier differences with a one-sided quarter-block bootstrap; Holm correction across the baselines of a lead. Not claimed when p ≥ 0.05.

## 7. Input contributions (FR4), selected arm only, both schedules

Each item is a full rolling refit on the same rows. Δ = ablated minus full, so positive = the family helped.
1. **Family refit ablation.** Remove one family's columns from F12, for each of the 12. Report ΔBrier (T43c and price term) at Leads 1-3, with a 90% block-bootstrap CI and p, plus Δ continuous RMSE.
   - H1 removal = π_H replaced by the hunger climatology (the share of known quarters above 11.3).
   - A1 removal = the base projection is also removed: ê predicts the realised excess directly.
2. **Grouped ablation.** Price block (A1 columns except the base, A2, A3, world prices); climate (C1-C4); household economy (E1, E2); news (N1).
3. **Permutation.** Each family's columns are permuted across origins within the evaluation rows, 20 times; report the mean ΔBrier (model fixed).
4. **SHAP.** Mean |SHAP| per family of the Z3 food-error model, by chronological third of origins; rank stability across thirds.

**Classification of each family:**
- **predictive:** refit ΔBrier CI excludes 0 at some lead, and the permutation Δ is positive;
- **weak:** point estimate > 0 but the CI includes 0;
- **no demonstrated value:** otherwise.

A family with no value is checked for coverage (share missing) and timing (publication lag) before any recommendation is made.

## 8. Prospective seal

The selected arm's forecasts are written and hashed from the newest origins, for every target quarter after 2026-Q3:
- schedule A: issue 2026-10-01;
- schedule B: issue = the day after the 2026-Q3 SWS publication.

The hash goes in `out/PROSPECTIVE_SEAL.json`. They are scored only when the outcomes are published, by a later session.

## 9. Not allowed

- Changing the target, thresholds or evaluation rows after seeing results.
- Fitting any calibrator on evaluation outcomes.
- Pre-2021 data.
- Web queries for current PSA, BSP or SWS values.
- Replacing served artifacts or seals.
- Pushing or deploying without the user's approval.
