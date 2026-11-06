# E161: overfitting and bias audit of E158, RP+R and OH+R. Criteria fixed before results.

Written 2026-11-06. This is an audit only: **nothing is selected or tuned, and the E160 adoption (RP+R) is not changed by these results.**

Data: `backend/data/e160/out/oof_arms.csv` at Lead 1 (72 rows), plus new shuffled-input runs.

## A. Overfitting
1. **Nested selection.** Hold out one round (2018, 2019 or 2021). Using only the other two rounds' rows, choose among {E158, RP_R, OH_R} by lowest Brier, then score the chosen arm on the held-out round. Pool the three held-out rounds.
   - This estimates the accuracy of the **procedure** "pick the best arm", with the optimism of choosing after the fact removed.
   - **Flag OVERFIT-SELECTION** if nested accuracy is more than 5 points below the best single arm's pooled accuracy.
2. **Shuffled-input null.** Refit each residual arm (E158, RP_R, OH_R) with the residual inputs `E158.COLS` permuted across rows within each (survey, lead) group, in both training and test. The anchors are unchanged. Seeds 1, 2 and 3; report the mean.
   - **Flag NO-SIGNAL** for an arm if its real Brier is not better than its shuffled Brier, i.e. the interval of real − shuffled is not entirely below 0. A no-signal flag means the five trigger groups and news add nothing beyond chance structure, so any gain over the anchor is noise.
3. **Round stability.** Accuracy per round for each arm.
   - **Flag UNSTABLE** if the range across rounds exceeds 20 points.

## B. Bias (systematic error towards a group)
For each arm, the mean signed error is predicted % − observed %. Bootstrap 95 % intervals with 2,000 draws, seed 161, resampling region clusters.

Groups:
- overall;
- island (Luzon, Visayas, Mindanao);
- observed class (HIGH, LOW);
- CALABARZON rows.

Also per island: false-alarm rate (predicted HIGH among observed LOW) and miss rate (predicted LOW among observed HIGH).

- **Flag BIAS** for a group when its mean signed error interval excludes 0 and the absolute error exceeds 3 points (the survey's own error).
- **Flag UNEQUAL-ERROR** when an island's false-alarm or miss rate differs from the other islands' pooled rate by more than 25 points.

## Reporting
Every flag is reported as found. No arm, threshold or weight is changed in response.
