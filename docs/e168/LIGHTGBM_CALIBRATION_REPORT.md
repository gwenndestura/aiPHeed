# LightGBM calibration report (E168)

Each layer was fitted on inner out-of-fold LightGBM forecasts from training rows only. The primary layer was chosen by inner Brier. All three are also reported on the outer rows.

| Lead 1 layer | Inner Brier (2018/19; 2021) | Outer accuracy | Outer Brier | **Official C4 slope [95 %]** | Probability-slope 95 % CI | Bias (points) |
|---|---|---|---|---|---|---|
| **Raw (chosen)** | 0.080; 0.114 | 75.0 % | **0.1230** | 0.76 [0.55, 0.90]: fail | [1.08, 3.39] | +2.97 |
| Linear (intercept + slope) | 0.086; 0.122 | 76.4 % | 0.1263 | **0.84 [0.61, 0.99]:** closest, still fails | [1.22, 3.77] | +3.45 |
| Platt (soft, L2) | 0.087; 0.126 | 68.1 % | 0.1423 | 0.76 [0.55, 0.90]: fail | [1.20, 3.87] | +2.97 |

**Reliability, raw layer, Lead 1:**

| Probability band | Rows | Observed HIGH rate |
|---|---|---|
| 0–0.2 | 16 | 0.00 |
| 0.2–0.4 | 9 | 0.11 |
| **0.4–0.6** | **24** | **0.29** |
| 0.6–0.8 | 12 | 0.58 |
| 0.8–1.0 | 11 | 0.91 |

- **The middle band is over-predicted**, again by 2018/2019 near-threshold LOW provinces.
- **The probability-slope intervals lie above 1:** P(HIGH) is compressed toward 0.5 (under-confident). The official logit-level slope is below 1 (prevalence levels over-spread). Both come from the round-level shift.

**Not run:**
- **Isotonic:** 1–3 training rounds and about 46 effective rows.
- **Hierarchical by round or province:** round effects cannot be estimated from 1 training round (2018/2019 origins), and there is one row per province.

**Verdict:**
- Inner validation correctly preferred the raw layer: it gave the lowest outer Brier.
- The linear layer moves the C4 slope from 0.76 to 0.84, but the interval still excludes 1, and it raises bias.
- **No calibration layer passes C4 honestly.** The cause is the round-level shift documented in `docs/e166/C1_C4_ANALYSIS.md`.
