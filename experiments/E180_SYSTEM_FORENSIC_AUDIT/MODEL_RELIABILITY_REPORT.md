# E180: model reliability

All figures recomputed independently (`recompute.py`, scikit-learn and a written-out C1 formula) from saved forecasts
(`data/e172/out/oof.csv`, which re-ran E168 in the same jobs with max difference 0.0 from its locked output).
Evidence type: historical held-out rows (ENNS 2018/2019/2021), **previously inspected** in about 29 experiments.

## E168 vs SIMPLE (verified)
| Metric | E168 L1 | E168 L2 | SIMPLE L1 | SIMPLE L2 |
|---|---|---|---|---|
| Confusion (tp/fp/tn/fn) | 23/14/33/2 | 23/15/32/2 | 22/13/34/3 | 22/10/37/3 |
| Accuracy | 0.7778 | 0.7639 | 0.7778 | 0.8194 |
| C1 low bound (vs 0.6528) | 0.6570 pass | 0.6405 **fail** | 0.6570 pass | 0.7077 pass |
| C2-C6 | pass | pass | pass | pass |
| F1 | 0.742 | 0.730 | 0.733 | 0.772 |
| Balanced accuracy | 0.811 | 0.800 | 0.802 | 0.834 |
| ROC-AUC | 0.895 | 0.887 | 0.864 | 0.874 |
| Brier | 0.1394 | 0.1373 | 0.1453 | 0.1437 |
| Seed stability (156 untainted training rows) | 3 of 156 class flips (E168 settings) | | 8 of 156 | |
| Calibration slope (95 %) | 1.05 [0.64, 1.33] | 0.99 [0.60, 1.29] | 0.96 | 0.90 [0.54, 1.18] |

## SIMPLE vs E168: what the Lead-2 difference is
- **Mechanism:** 6 ENNS 2018 rows move by 0.001-0.013 across P = 0.5 (5 become correct, Aklan becomes wrong); 66 of 72 classes are
  identical. The gain is threshold-margin movement, concentrated in one survey round.
- **Selection:** SIMPLE is one of five diagnostic subsets examined after E172 ran: post hoc.
- **Probability quality:** worse Brier and ROC-AUC, entirely from ENNS 2021 (lambda 0.97, over-confident).
- **Stability:** SIMPLE flips more classes across seeds than E168's settings; a 5-seed average (E178) reduces this.
- **Generalisation:** unknown. In the sealed 2027 forecasts (E173) SIMPLE and E168 give identical classes for all 78 provinces.
- **Verdict:** E168 is better supported (pre-registered, locked, more stable, better probabilities). SIMPLE's accuracy edge is not
  demonstrated to generalise.

## Overfitting and selection bias
- Every LightGBM option explored after E168 (E169-E179) was scored on the same 72 rows. Any best-of-N result on them is optimistic;
  only the pre-registered E168 result (and each experiment's pre-declared selection) is held-out evidence.
- Temporal generalisation: the ENNS 2018/2019 forecasts train on one survey transition; forward validation over rounds is impossible
  before 2021 (E177/E178).

## Other candidate (E179)
See E179_REPORT.md once complete; E179 is explicitly exploratory and test-informed.
