# E50: fixing the overfitting of the served model (lead 1)

Experiment only. The live system, `backend/data/`, the default record (e49) and the frontend are untouched.

- **Run:** `20261016T045812Z` (`E50_results.json`, `runs/20261016T045812Z/predictions.csv`, `runner/e50_run.py`).
- **Protocol:** E36 walk-forward, nested rule (tie 0.002 → simpler), seed 36, threshold 0.5, current trailing-median labels, the same 65 test rows (13 dates × 5 provinces; 53 HIGH / 12 LOW).
- **Shrinkage:** E49-C2 shrinkage was offered to R0, R1, R2 and R4, fitted on earlier eligible dates only. a = 1 (no shrinkage) whenever shrinking does not lower that Brier.
- **Consistency:** R0 reproduces the served walk-forward exactly (max |Δp| = 0). R3 reproduces E36's B3_LR_GOV (max |Δp| = 7e-18).

| Arm | Model |
|---|---|
| R0 | E49-C2 as served (E48-A1 pool + C2) |
| R1 | COMB_T5, regularised LightGBM: num_leaves {2,4} × min_data_in_leaf {15,10} × λ₂ {5,1}, monotone +1 on Dnow, D_last, H_last, y_last; nested rule (Q4 pick: 4 leaves, min_data 10, λ₂ 5) |
| R2 | R1 without trig_market, trig_employment, trig_ofw_remittance, trig_fish_kill |
| R3 | B3 government logistic regression |
| R4 | 0.4·R1 + 0.4·B3 + 0.2·LR(trig_climate, trig_fish_kill); trig_ofw_remittance was dropped as constant at every origin |

**R2 is identical to R1** at every row. LightGBM's `feature_pre_filter` already discards inputs that cannot satisfy min_data_in_leaf ≥ 10. The four inert inputs have at most 4 non-zero training rows, so R1 never sees them either.

## Performance (65 test rows)

| Arm | Acc. | Bal. acc. | AUC | Brier | Log loss | Max p | p ≥ 0.95 | p ≤ 0.05 | p ≥ 0.99 | Train acc. / log loss (Q4 origin) | SHAP baseline (p) vs label rate 0.733 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **R0** | **0.846** | **0.841** | 0.855 | 0.1509 | 0.48906 | 0.945 | 0 | 6 | 0 | **1.000** / 0.153 (raw 1.000 / 0.030) | **2.67 (0.935)** |
| R1 | 0.754 | 0.785 | 0.802 | 0.1887 | 0.567 | 0.860 | 0 | 0 | 0 | 0.960 / 0.330 (raw 0.947 / 0.163) | 1.61 (0.833) |
| R2 | = R1 | | | | | | | | | | |
| R3 | 0.846 | 0.809 | 0.866 | **0.1019** | 0.420 | **1.000** | 31 | 6 | **21** | 0.907 / 0.248 | 1.92 (0.872) |
| **R4** | 0.846 | 0.809 | **0.868** | 0.1248 | **0.410** | 0.937 | 0 | 0 | 0 | 0.947 / 0.248 | 1.62 (0.835, weighted) |

- **Raw R1:** acc 0.677, Brier 0.189. Shrinkage (a = 0.25–0.5) helped R1.
- **R4:** shrinkage chose a = 1 at every date, so no shrinkage was applied.
- **Errors (TP / FN / TN / FP):**
  - R0: 45 / 8 / 10 / 2
  - R1: 39 / 14 / 10 / 2
  - R3 and R4: 46 / 7 / 9 / 3
- **Paired per-date Brier vs R0** (bootstrap 95% CI):
  - R1: +0.038 [−0.005, +0.089]
  - R3: −0.049 [−0.099, +0.001]
  - R4: −0.026 [−0.067, +0.015]
  - None is significant.

## Adoption (rule fixed before the run)

| Arm | AUC ≥ 0.80 | Bal. acc. ≥ 0.83 | Brier ≤ 0.151 | Log loss ≤ 0.489 | Train acc. ≤ 0.95 | No test p ≥ 0.99 | Result |
|---|---|---|---|---|---|---|---|
| R0 | ✓ | ✓ | ✓ | ✗ (0.48906) | ✗ (1.000) | ✓ | not acceptable |
| R1 / R2 | ✓ | ✗ | ✗ | ✗ | ✗ (0.960) | ✓ | not acceptable |
| R3 | ✓ | ✗ (0.809) | ✓ | ✓ | ✓ | ✗ (21 rows) | not acceptable |
| R4 | ✓ | ✗ (0.809) | ✓ | ✓ | ✓ | ✓ | not acceptable (fails only balanced accuracy) |

**No arm passes, so E49-C2 stays served.**

## The 10 disagreements of R0

R0's 10 disagreements:

| Quarter | Province |
|---|---|
| 2023-Q1 | Rizal |
| 2023-Q4 | Laguna |
| 2024-Q1 | Cavite |
| 2024-Q1 | Laguna |
| 2024-Q2 | Cavite |
| 2024-Q2 | Quezon |
| 2024-Q3 | Laguna |
| 2024-Q4 | Cavite |
| 2025-Q4 | Batangas |
| 2026-Q2 | Batangas |

| Arm | Fixed | Newly wrong | Batangas 2025-Q4 (LOW) | Batangas 2026-Q2 (LOW) |
|---|---|---|---|---|
| R0 | – | – | 0.906 ✗ | 0.810 ✗ |
| R1 / R2 | 2024-Q2 Cavite, Quezon; 2024-Q4 Cavite | 9: 2023-Q2/Q3/Q4 × Batangas, Cavite, Rizal | 0.774 ✗ | 0.659 ✗ |
| R3 | 2023-Q1 Rizal; 2024-Q2 Cavite; 2024-Q3 Laguna; 2024-Q4 Cavite; 2026-Q2 Batangas | 2023-Q1 Batangas, Cavite; 2023-Q3 Batangas, Cavite; 2026-Q2 Cavite | 1.000 ✗ | **0.084 ✓** |
| R4 | 2023-Q1 Rizal; 2024-Q3 Laguna; 2024-Q4 Cavite; 2026-Q2 Batangas | 2023-Q1 Batangas, Cavite; 2023-Q3 Batangas, Cavite | 0.922 ✗ | **0.398 ✓** |

No arm fixes Batangas 2025-Q4.

## Index per quarter (CALABARZON)

| Quarter | R0 | R1/R2 | R3 | R4 |
|---|---|---|---|---|
| 2023-Q1 | 0.400 | 0.400 | 0.544 | 0.461 |
| 2023-Q2 | 0.586 | 0.467 | 0.590 | 0.513 |
| 2023-Q3 | 0.356 | 0.400 | 0.301 | 0.364 |
| 2023-Q4 | 0.534 | 0.440 | 0.619 | 0.523 |
| 2024-Q1 | 0.389 | 0.410 | 0.455 | 0.463 |
| 2024-Q2 | 0.604 | 0.514 | 0.748 | 0.644 |
| 2024-Q3 | 0.559 | 0.543 | 0.848 | 0.653 |
| 2024-Q4 | 0.599 | 0.603 | 0.996 | 0.724 |
| 2025-Q1 | 0.812 | 0.656 | 0.964 | 0.783 |
| 2025-Q4 | 0.907 | 0.775 | 1.000 | 0.923 |
| 2026-Q1 | 0.907 | 0.773 | 1.000 | 0.921 |
| 2026-Q2 | 0.873 | 0.749 | 0.543 | 0.701 |
| 2026-Q3 | 0.912 | 0.811 | 0.986 | 0.920 |
| **2026-Q4** | **0.778** | **0.767** | **0.747** | **0.774** |

## Q4 2026 per province

| Arm | Cavite | Laguna | Quezon | Rizal | Batangas |
|---|---|---|---|---|---|
| R0 (served) | 0.888 | 0.877 | 0.914 | 0.877 | 0.335 |
| R1/R2 | 0.824 | 0.823 | 0.849 | 0.839 | 0.501 |
| R3 | 0.757 | 0.980 | 0.923 | 0.870 | 0.204 |
| R4 | 0.816 | 0.928 | 0.903 | 0.889 | 0.336 |

## Driver shares at Q4 2026 (live panel method)

- **(a)** Market / Climate / Fish Kill / Employment / OFW, normalised over the five drivers.
- **(b)** The same five plus Other in the denominator.

| Arm | CALABARZON (a) | CALABARZON (b) |
|---|---|---|
| R0 | 65 / 33 / 2 / 0 / 0 | 33 / 16 / 1 / 0 / 0 / Other 50 |
| R1/R2 | 81 / 19 / 0 / 0 / 0 | 38 / 9 / 0 / 0 / 0 / Other 53 |
| R3 | 100 / 0 / 0 / 0 / 0 | 33 / 0 / 0 / 0 / 0 / Other 67 |
| R4 | 83 / 11 / 6 / 0 / 0 | 32 / 5 / 2 / 0 / 0 / Other 61 |

**How the attributions were computed:**
- **LightGBM arms:** TreeSHAP.
- **R3:** linear SHAP, coef·z.
- **R4:** the 0.4 / 0.4 / 0.2-weighted component attributions in each component's log-odds. This is approximate: a probability blend has no exact additive log-odds decomposition.

**What the shares show:**
- **R1:** regularisation shrinks trig_climate from −1.6 to about −0.34 log-odds.
- **R4:** its Fish Kill share comes from the 0.2 trigger LR, so it is a direct contribution, not a news allocation.
- **Employment and OFW:** 0 in every arm. There is no data signal: 1 and 0 non-zero training rows respectively.

## Verdict
**No arm meets the adoption rule; keep E49-C2.**
- **Regularisation alone (R1/R2) removes the overfit but loses skill.** Balanced accuracy is 0.785 and Brier 0.189, and nine LOW-predicted 2023 rows become wrong.
- **The paper blend (R4) is closest.** It is not overfit (train accuracy 0.947, SHAP baseline 0.835 vs 0.935), and nothing exceeds 0.95. Brier is 0.125, log loss 0.410 and AUC 0.868, all better than R0, and accuracy ties at 0.846. It fails only balanced accuracy: 0.809 against the 0.83 cut, because it adds one false HIGH among the 12 LOW rows.
- **R0 itself also fails the rule** (training accuracy 1.000, log loss 0.48906 > 0.489).
