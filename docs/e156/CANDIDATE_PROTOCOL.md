# E156 candidate: training-internal calibration of the E151 model

Written before the run. **One run; `app/e156/candidate.py` refuses a second.**

**Failure addressed.** Lead 1 fails C4: the calibration slope interval [0.52, 0.97] excludes 1, so forecasts are spread wider than the truth. This is the one failure a principled change can target without new data. C1 needs about 78 % accuracy at the effective sample size, which calibration alone is not expected to reach; that is stated now.

**Change.** For each round and lead, the E151 model's own out-of-fold training forecasts (anchor + cross-validated LightGBM adjustment) are regressed on the training survey values, weighted by survey precision: y = a + b·m. The test forecast becomes a + b·m. Nothing outside the round's training rows is used. This differs from E151's earlier calibrators, which were fitted on previous rounds' test forecasts and chosen on one round.

**Kept the same:** all five groups and news, the target, the 50 line, the rows, every lead.

**Read-out:** the reliability criteria C1 to C6 at every lead, against the uncalibrated E151. **The candidate is adopted only if it passes at least as many criteria as E151 at Lead 1, and its Lead 1 Brier is no worse.** Otherwise E151 stays.
