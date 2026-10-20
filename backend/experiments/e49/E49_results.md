# E49: calibrating the E48-A1 probabilities (lead 1)

Experiment only; the systems on 8000/8080 and `e36_record.json` are untouched.

- **Run:** `runs/20261015T215405Z` (`E49_results.json`, `runner/e49_run.py`).
- **Setup:** current trailing-median labels; E48-A1 features (E36's 13 inputs + 5 trigger proportions); E36's walk-forward and nested rule (seed 36); 13 test quarters, 2023-Q1..2026-Q3 (65 rows).

## Arms

| Arm | What it does |
|---|---|
| C0 | raw E48-A1 (operational setting COMB_T5 × G2) |
| C1 | Platt scaling of C0: logistic regression on logit(p), refitted at each date on earlier out-of-fold predictions |
| C2 | shrinkage of C0: p' = a·p + (1−a)·base rate. `a` is chosen from 0..1 (step 0.05) by lowest Brier on earlier dates; the base rate is the Laplace HIGH rate of the training labels at that origin |
| C3 | stronger LightGBM regularisation, no post-calibration: R1 = 2 leaves, min 15 rows per leaf, 60 trees, λ = 5; R2 = 3 leaves, depth 2, min 20 rows per leaf, 60 trees, λ = 10. Same nested rule; operational setting COMB_T5 × R1 |
| C4 | C3 + Platt scaling |

**No future data.** For a test date t, "earlier dates" are the test dates whose **target was posted before t's origin**, which is E36's eligibility rule. A date with fewer than 3 such dates, or with only one class, uses the raw p.
- **Affected dates:** the first **4** test quarters (2023-Q1..2023-Q4) use the raw p in C1, C2 and C4.

## Results (65 rows)

| Arm | Accuracy | Bal. acc. | AUC | Brier | Log loss | ECE (3 bins) | Max p | Mean p | p ≥ 0.99 | Brier vs C0 (95% CI) |
|---|---|---|---|---|---|---|---|---|---|---|
| **C0** raw | 0.815 | 0.822 | 0.839 | 0.1540 | 0.520 | 0.133 | 0.9997 | 0.683 | **17** | — |
| C1 Platt | 0.862 | 0.851 | 0.844 | **0.1282** | **0.791** | 0.094 | 1.0000 | 0.721 | 14 | −0.026 (−0.062, +0.002) |
| **C2 shrinkage** | **0.846** | 0.841 | **0.855** | 0.1509 | **0.489** | 0.166 | **0.9452** | 0.649 | **0** | −0.003 (−0.010, +0.003) |
| C3 regularised | 0.615 | 0.732 | 0.671 | 0.2026 | 0.579 | 0.232 | 0.8923 | 0.584 | 0 | +0.049 (−0.016, +0.112) |
| C4 regularised + Platt | 0.723 | 0.766 | 0.793 | 0.1797 | 0.592 | 0.153 | 0.9995 | 0.662 | 3 | +0.026 (−0.029, +0.085) |
| persistence | 0.877 | 0.860 | 0.860 | 0.1231 | 1.700 | 0.123 | 1.0000 | 0.754 | 49 | |

**Reliability** (5 bins; cells are n / mean predicted p / observed HIGH rate):

| Bin | C0 | C1 | C2 | C3 | C4 |
|---|---|---|---|---|---|
| 0.0–0.2 | 12 / 0.08 / 0.50 | 10 / 0.05 / 0.40 | 11 / 0.07 / 0.45 | 2 / 0.19 / 0.50 | 4 / 0.02 / 0.75 |
| 0.2–0.4 | 1 / 0.32 / 1.00 | 1 / 0.27 / 1.00 | 2 / 0.30 / 1.00 | 12 / 0.33 / 1.00 | 1 / 0.29 / 1.00 |
| 0.4–0.6 | 10 / 0.45 / 0.60 | 8 / 0.43 / 0.50 | 10 / 0.45 / 0.60 | 21 / 0.43 / 0.52 | 26 / 0.45 / 0.65 |
| 0.6–0.8 | 6 / 0.70 / 1.00 | 8 / 0.74 / 1.00 | 6 / 0.69 / 1.00 | 10 / 0.75 / 0.90 | 4 / 0.71 / 0.75 |
| 0.8–1.0 | 36 / 0.96 / 0.94 | 38 / 0.97 / 0.95 | 36 / **0.89** / 0.94 | 20 / 0.85 / 1.00 | 30 / 0.93 / 0.97 |

Every arm's lowest bin is too low: about half of the "≤ 0.2" rows were HIGH. In C2's top bin the predicted 0.89 sits slightly below the observed 0.94 (mildly under-confident), which is why its 3-bin ECE is higher than C0's.

**Confident mistakes.**

| Arm | p ≥ 0.9 but LOW | p ≤ 0.1 but HIGH |
|---|---|---|
| C0 | 2025-Q4 Batangas 0.997 | 2023-Q4 Laguna 0.064; 2024-Q1 Cavite 0.028; 2024-Q1 Laguna 0.080 |
| C1 | 2025-Q4 Batangas 0.999; 2026-Q2 Batangas 0.904 | 2023-Q4 Laguna 0.064; 2024-Q1 Cavite 0.000; 2024-Q1 Laguna 0.000 |
| C2 | 2025-Q4 Batangas **0.906** | the same three as C0 (0.064, 0.028, 0.080; all in the first year, before shrinkage applies or with a = 1) |
| C3 | none | none |
| C4 | 2025-Q4 Batangas 0.915 | 2024-Q1 Laguna 0.031; 2024-Q2 Cavite 0.012; 2024-Q2 Quezon 0.012 |
| persistence | 2023-Q1, 2025-Q4 Batangas (1.0) | 6 rows at 0.0 |

**C2's shrinkage weight.** `a` = 1.0 in 2024-Q1/Q2, then 0.85, 0.75, then 0.65–0.70 from 2025. With a base rate of about 0.72, that caps p at about **0.92** and floors it at about **0.22**.

**Platt (C1).** Its slope is about 0.5 and its intercept about +1.2 to +1.8. It pushes probabilities **up** toward the recent HIGH rate, so it becomes more extreme rather than less, and its log loss rises (0.791).

## Adoption (rule fixed before results)
- **Rule:** the lowest Brier among arms with accuracy ≥ C0 − 0.01 (≥ 0.805) **and** log loss ≤ C0's (0.520).
- **Eligible:** **C2 only.** C1 fails on log loss; C3 and C4 fail on accuracy.
- **Choice:** **C2**, which beats C0 on Brier (0.1509 vs 0.1540). The gain is small and **not significant** (CI −0.010 to +0.003).

## Index history: C0 vs C2 (CALABARZON = mean of the five provinces)

| Quarter | Observed share HIGH | C0 | **C2** |
|---|---|---|---|
| 2023-Q1 | 0.2 | 0.400 | 0.400 |
| 2023-Q2 | 0.6 | 0.586 | 0.586 |
| 2023-Q3 | 0.6 | 0.356 | 0.356 |
| 2023-Q4 | 0.8 | 0.534 | 0.534 |
| 2024-Q1 | 0.8 | 0.389 | 0.389 |
| 2024-Q2 | 1.0 | 0.604 | 0.604 |
| 2024-Q3 | 1.0 | 0.561 | 0.559 |
| 2024-Q4 | 1.0 | 0.600 | 0.599 |
| 2025-Q1 | 1.0 | 0.888 | 0.812 |
| 2025-Q4 | 0.8 | **0.998** | **0.907** |
| 2026-Q1 | 1.0 | **0.998** | **0.907** |
| 2026-Q2 | 0.8 | 0.965 | 0.873 |
| 2026-Q3 | 1.0 | **0.993** | **0.912** |
| **2026-Q4** (forecast) | – | **0.800** | **0.778** |

Province probabilities for every quarter are in `E49_results.json` (`index_history`).

## Q4 2026 (origin 2026-10-01)

| Arm | CALABARZON | Cavite | Laguna | Quezon | Rizal | Batangas |
|---|---|---|---|---|---|---|
| C0 | 0.800 | 0.957 | 0.941 | 0.994 | 0.941 | 0.167 |
| C1 | 0.871 | 0.933 | 0.922 | 0.973 | 0.922 | 0.602 |
| **C2** | **0.778** | 0.888 | 0.877 | 0.914 | 0.877 | 0.335 |
| C3 | 0.818 | 0.916 | 0.916 | 0.916 | 0.916 | 0.427 |
| C4 | 0.917 | 0.959 | 0.959 | 0.959 | 0.959 | 0.749 |

## Verdict
**Adopt C2 (shrinkage toward the base rate) on top of E48-A1.**
- **Results:** it is the only arm that keeps or improves accuracy (0.846 vs 0.815) and log loss (0.489 vs 0.520) while lowering Brier (0.151 vs 0.154). The Brier gain is small and not significant.
- **Overconfidence removed:** no province-quarter reaches 0.99 (C0 had 17), the maximum is 0.945, and the worst confident miss (Batangas 2025-Q4) drops from 0.997 to 0.906.
- **Rejected arms:**
  - Platt scaling (C1) has a lower Brier but makes the probabilities *more* extreme (0.000 / 1.000) and its log loss worse.
  - Stronger regularisation (C3, C4) loses too much accuracy.

**What the dashboard index history would look like with C2.**
- **2023–2024:** unchanged, because shrinkage starts only once enough earlier outcomes exist.
- **From 2025:** the recent quarters fall from 0.97–1.00 to about **0.87–0.91**, with no 1.00.
- **Q4 2026:** CALABARZON reads **0.78** instead of 0.80, with Batangas at 0.34 instead of 0.17.
- **Limit on the range:** at the recent shrinkage weight (a ≈ 0.7, base ≈ 0.72) the index **cannot show values above about 0.92 or below about 0.22**. A HIGH province-quarter shows as about 0.88–0.91 rather than 0.99.
- **What it doesn't change:** the reason the index is high. About 9 in 10 recent province-quarters really are HIGH under the trailing-median label.
