# S1 results: C-b + Kalman estimate of true hunger

Pre-registration `S1_PREREGISTRATION.md` (`6a59cccb…4f24`), fixed and hashed before the fit.

Development evidence only: the 14th historical attempt, on 62 previously examined quarters.
Runner `runner/s1_kalman.py`; outputs in `out/s1_*`.

## Pre-checks (all passed)

- The two filter implementations agree at all 113 origins.
- The features are unchanged when every SWS round published on or after O(t) is randomized (5 reps).
- The C-b refit reproduces 904 / 904 rows (max |Δ| 1e-16).
- Median σ_w² = 1.76, i.e. true hunger moves about 1.3 points per quarter.

## Metrics (62 quarters)

| | Accuracy | Balanced | Precision | Recall | F1 | AUC | Brier | ECE | TP/FP/FN/TN | Failed | 2015–20 third |
|---|---|---|---|---|---|---|---|---|---|---|---|
| C-b L1 | 0.790 | 0.717 | 0.812 | 0.907 | 0.857 | 0.702 | 0.1874 | 0.169 | 39/9/4/10 | R7 | 0.571 |
| **S1 L1** | **0.806** | **0.743** | **0.830** | 0.907 | **0.867** | **0.711** | 0.1871 | 0.165 | 39/8/4/11 | **none** | **0.619** |
| C-b L2 | 0.790 | 0.717 | 0.812 | 0.907 | 0.857 | 0.704 | 0.1837 | 0.152 | 39/9/4/10 | R7 | 0.571 |
| **S1 L2** | **0.806** | **0.743** | **0.830** | 0.907 | **0.867** | **0.715** | **0.1805** | 0.166 | 39/8/4/11 | **none** | **0.619** |

- **R7 for S1:** thirds 0.952 / 0.619 / 0.850; leave-one-quarter-out minimum 0.803.
- **Algorithm 3:** MRLT 2.
- **Against C-b:**
  - Lead 1: Brier −0.0004 (95% CI −0.009..0.008), p 0.46.
  - Lead 2: Brier −0.0033 (CI −0.012..0.005), p 0.22.
- **One call changed per lead**, from origin 2018-Q3 (S1 0.496 vs C-b 0.530). It turned a false HIGH into a correct
  LOW.

## 14-test Holm family (S1 × 7 baselines × 2 leads)

| Comparator | Lead 1 diff (Holm p) | Lead 2 diff (Holm p) |
|---|---|---|
| Persistence | −0.152 (**0.005**) ✓ | −0.158 (**0.000**) ✓ |
| PSA-only logistic | −0.021 (0.511) | −0.059 (0.108) |
| Combined logistic | −0.006 (0.511) | −0.054 (0.197) |
| NLP-only logistic | −0.147 (**0.035**) ✓ | −0.219 (0.056) |
| LightGBM gov-only | −0.046 (0.056) | −0.060 (**0.007**) ✓ |
| LightGBM NLP-only | −0.101 (0.056) | −0.095 (0.159) |
| Always-HIGH | −0.119 (0.056) | −0.126 (0.056) |

All 14 differences are negative; 4 of 14 are significant.

## Gates

| G1 all baselines | G2 improves C-b | G3 R1–R7 | G4 MRLT ≥ 2 | G5 R7 fixed | **Adoption (G2 + G4)** |
|---|---|---|---|---|---|
| ✗ | ✗ (p 0.46 / 0.22) | **✓** | ✓ | **✓** | **No** |

## Honest reading

- **S1 is the first model in the project to pass all seven reliability rules at both leads.** It is better than C-b on
  every classification metric and on AUC.
- **But the whole difference is one forecast.** One origin's probability moved from 0.530 to 0.496, across the 0.50
  line. With 21 quarters in the middle third, one quarter decides R7. The Brier improvement is not significant.
- **Under the pre-registered rule, S1 is not adopted, and C-b stays the main model.** The rule needs a Brier
  improvement (G2), not one changed call.
- **What would be defensible:**
  - Report S1 as an exploratory result in the thesis.
  - If the team and adviser want it, add S1 to the sealed prospective registry beside C-b, so new data can decide.
  - Adding it is a new registry entry: it needs your approval, a commit, and a re-hashed ledger before 2027-01-15.
