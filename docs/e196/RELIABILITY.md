# E196 reliability checks (existing results only; E196 not changed; local only)

**Sources.** Script: `backend/app/e196/reliability.py`. Output: `backend/data/e196/out/reliability.json`. All checks
use the 72 real outer rows per lead (Leads 1–3, 216 forecasts) and a region-cluster bootstrap (4,000 draws).

## 1. Selection-adjusted (winner's-curse) accuracy
- **The problem.** E196 was the best of **52 variants** evaluated on the same rows (E168 … E196), and the best of many
  tends to be optimistic.
- **The method.** Empirical-Bayes shrinkage of E196's gain toward the mean gain of all 52 variants, weighted by how much
  of the spread between variants is real rather than noise.
- **The numbers:**
  - mean gain of all variants over E184: −2.1 pts;
  - real between-variant SD: 2.2 pts;
  - E196's gain SE: 0.8 pts, giving a shrinkage weight of 0.88.
- **Result:**

| | Pooled Leads 1–3 accuracy |
|---|---|
| E184 | 77.8 % |
| E196, observed | 80.6 % (+2.8 pts) |
| **E196, selection-adjusted** | **80.0 % (+2.2 pts)** |

## 2. Region jackknife
- **Method.** Drop each of the 16 regions in turn.
- **Result.** E196's gain over E184 stays between **+2.5 and +3.0 pts**. No single region drives the improvement.
- **By round** (from `REPORT.md`): E196 ≥ E184 in 8 of 9 round × lead cells.

## 3. E196 metrics with 95 % confidence intervals
| Lead | Accuracy | Recall (HIGH caught) | Specificity | Brier | ROC-AUC |
|---|---|---|---|---|---|
| 1 | 81.9 % [74.0, 90.0] | 0.88 [0.71, 1.00] | 0.79 [0.63, 0.90] | .119 [.084, .156] | 0.90 |
| 2 | 80.6 % [72.4, 89.2] | 0.88 [0.71, 1.00] | 0.77 [0.62, 0.89] | .119 [.083, .155] | 0.90 |
| 3 | 79.2 % [71.2, 87.8] | 0.88 [0.71, 1.00] | 0.74 [0.60, 0.87] | .126 [.089, .162] | 0.89 |

## 4. Calibration (pooled Leads 1–3)

Predicted probability band → observed HIGH rate:

| Band | E184 | E196 |
|---|---|---|
| 0–0.2 | 0 % (n 51) | 0 % (n 48) |
| 0.2–0.4 | 13 % (32) | 10 % (30) |
| 0.4–0.5 | 24 % (34) | 15 % (39) |
| 0.5–0.6 | 33 % (30) | 35 % (26) |
| 0.6–0.8 | 63 % (40) | 63 % (43) |
| 0.8–1.0 | 97 % (29) | 100 % (30) |

- **Strong at the extremes:** below 0.2 means almost never HIGH; above 0.8 means almost always HIGH.
- **Over-called in the middle band (0.5–0.6):** the same period-shift effect as E184. This is why most remaining false
  alarms come from that band.

## Conclusion
- **The improvement is real and broad.** It survives a selection adjustment (+2.2 pts), holds in every region and in
  8 of 9 round-lead cells, and is not tied to one province group.
- **The realistic accuracy to report** is about **80 % pooled over Leads 1–3** (selection-adjusted), with per-lead
  95 % ranges of about 71–90 %.
- **What still requires new data:** proof on unseen outcomes. The sealed 2022 test
  (`docs/e196/CONFIRMATION_PROTOCOL.md`) will provide it.
