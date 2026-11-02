# LEAD2_FOODINSECURITY: results (EXPLORATORY)

**Plan:** `PLAN.md`, sha `23a030ae55f61c92c1a8235272d3c90f9285abaa3d4dcef8a5401b7e125b43ee`, committed in `a5a8bba` before any result.

**Runner:** `runner/run_fi.py`. **Outputs:** `out/results.json` and `out/rows.csv`.

**Label: EXPLORATORY.** These are closed 2023–2026 quarters, so any pass would be a candidate only. Nothing served, sealed or pre-registered was changed.

## Answer

| | Lead 1 | Lead 2 |
|---|---|---|
| Quarters (n) | **14** (2023-Q1..2026-Q3, 70 province rows) | **13** (2023-Q2..2026-Q3, 65 province rows) |
| HIGH quarters | 11 of 14 | 11 of 13 |
| Models passing all of R1–R7 | **none** | **none** |
| Models counted as reliable (R1–R7 + lower Brier than ALWAYS-HIGH and persistence) | **none** | **none** |
| Lower Brier than ALWAYS-HIGH (point estimate) | PIH (−0.125, p 0.121); PERSIST (−0.071, p 0.417) | PIH only (−0.017, p 0.467) |
| Lower than ALWAYS-HIGH at p < 0.10 | none | none |

**No model is reliable at Lead 1 or Lead 2 for the hunger-only target.**
- PIH (the served hunger part) has the lowest Brier at both leads, but it does not beat persistence or ALWAYS-HIGH with confidence.
- LOGIT is worse than ALWAYS-HIGH at both leads.

## Lead 1 (14 quarters)

| Model | TP/FP/FN/TN (rows) | Accuracy | Balanced | Precision | Recall | AUC | Brier | Rules passed | Fails | Brier vs ALWAYS-HIGH | Brier vs persistence | Reliable |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| (a) PERSIST | 45/0/10/15 | 0.857 | 0.909 | 1.000 | 0.818 | 0.909 | 0.1429 | 5/7 | R4, R5 | −0.071 (p 0.417) | (itself) | no |
| (b) PIH | 50/5/5/10 | 0.857 | 0.788 | 0.909 | 0.909 | 0.955 | **0.0895** | 5/7 | R4, R5 | −0.125 (p 0.121) | −0.053 (p 0.237) | no |
| (c) LOGIT | 45/14/10/1 | 0.657 | 0.442 | 0.763 | 0.818 | 0.445 | 0.2716 | 2/7 | R2, R3, R4, R5, R7 | +0.057 | +0.129 | no |
| ALWAYS-HIGH | 55/15/0/0 | 0.786 | 0.500 | 0.786 | 1.000 | – | 0.2143 | 3/7 | R3, R4, R5, R7 | – | +0.071 | no |
| ALWAYS-LOW | 0/0/55/15 | 0.214 | 0.500 | – | 0.000 | – | 0.7857 | 1/7 | R2–R7 | +0.571 | +0.643 | no |
| CLIM | 30/0/25/15 | 0.643 | 0.773 | 1.000 | 0.545 | 0.727 | 0.2847 | 2/7 | R2, R4, R5, R6, R7 | +0.070 | +0.142 | no |

**Why PIH fails:**
- **R4:** its accuracy (0.857) only ties persistence (0.857).
- **R5:** its Brier advantage over persistence (−0.053) has p = 0.237, not < 0.10. It beats CLIM (p < 0.001).

**PERSIST cannot pass R4, R5 or the persistence criterion**, because it is the persistence baseline.

## Lead 2 (13 quarters)

| Model | TP/FP/FN/TN (rows) | Accuracy | Balanced | Precision | Recall | AUC | Brier | Rules passed | Fails | Brier vs ALWAYS-HIGH | Brier vs persistence | Reliable |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| (a) PERSIST | 40/0/15/10 | 0.769 | 0.864 | 1.000 | 0.727 | 0.864 | 0.2308 | 4/7 | R4, R5, R7 | +0.077 (p 0.759) | (itself) | no |
| (b) PIH | 45/5/10/5 | 0.769 | 0.659 | 0.900 | 0.818 | 0.841 | **0.1374** | 3/7 | R3, R4, R5, R7 | −0.017 (p 0.467) | −0.093 (p 0.116) | no |
| (c) LOGIT | 31/10/24/0 | 0.477 | 0.282 | 0.756 | 0.564 | 0.124 | 0.4803 | 1/7 | R2–R7 | +0.327 | +0.250 | no |
| ALWAYS-HIGH | 55/10/0/0 | **0.846** | 0.500 | 0.846 | 1.000 | – | 0.1538 | **5/7** | R3, R5 | – | −0.077 (p 0.397) | no |
| ALWAYS-LOW | 0/0/55/10 | 0.154 | 0.500 | – | 0.000 | – | 0.8462 | 1/7 | R2–R7 | +0.692 | +0.615 | no |
| CLIM | 25/0/30/10 | 0.538 | 0.727 | 1.000 | 0.455 | 0.591 | 0.3240 | 2/7 | R2, R4, R5, R6, R7 | +0.170 | +0.093 | no |

At Lead 2 the no-skill **ALWAYS-HIGH has the highest accuracy (0.846) and passes 5 of 7 rules**. Every model is below it on accuracy, and only PIH is below it on Brier, by 0.017, which is not significant.

## Per quarter

The forecast probability for each target quarter (y = 1 means hunger was above 11.3). For LOGIT the table shows the provinces' mean and how many of the 5 provinces were HIGH.

**Lead 1**

| Target | y | Latest SWS | PERSIST | PIH | LOGIT mean (HIGH provs) | CLIM |
|---|---|---|---|---|---|---|
| 2023-Q1 | 0 | 9.6 | 0 | 0.37 | 0.89 (5) | 0.40 |
| 2023-Q2 | 0 | 11.3 | 0 | 0.50 | 0.77 (4) | 0.33 |
| 2023-Q3 | 0 | 8.7 | 0 | 0.28 | 1.00 (5) | 0.29 |
| 2023-Q4 | 1 | 11.3 | 0 | 0.50 | 1.00 (5) | 0.25 |
| 2024-Q1 | 1 | 10.3 | 0 | 0.41 | 0.53 (3) | 0.22 |
| 2024-Q2 | 1 | 14.3 | 1 | 0.76 | 0.80 (5) | 0.30 |
| 2024-Q3 | 1 | 15.3 | 1 | 0.82 | 0.83 (5) | 0.36 |
| 2024-Q4 | 1 | 19.6 | 1 | 0.97 | 0.73 (4) | 0.42 |
| 2025-Q2 | 1 | 25.3 | 1 | 0.99 | 0.99 (5) | 0.50 |
| 2025-Q3 | 1 | 17.0 | 1 | 0.89 | 0.93 (5) | 0.50 |
| 2025-Q4 | 1 | 16.15 | 1 | 0.78 | 0.60 (3) | 0.53 |
| 2026-Q1 | 1 | 23.8 | 1 | 0.98 | 0.33 (0) | 0.56 |
| 2026-Q2 | 1 | 16.7 | 1 | 0.81 | 1.00 (5) | 0.59 |
| 2026-Q3 | 1 | 22.4 | 1 | 0.96 | 1.00 (5) | 0.61 |

**Lead 2**

| Target | y | Latest SWS | PERSIST | PIH | LOGIT mean (HIGH provs) | CLIM |
|---|---|---|---|---|---|---|
| 2023-Q2 | 0 | 9.6 | 0 | 0.30 | 1.00 (5) | 0.40 |
| 2023-Q3 | 0 | 11.3 | 0 | 0.50 | 0.98 (5) | 0.33 |
| 2023-Q4 | 1 | 8.7 | 0 | 0.22 | 0.00 (0) | 0.29 |
| 2024-Q1 | 1 | 11.3 | 0 | 0.50 | 0.00 (0) | 0.25 |
| 2024-Q2 | 1 | 10.3 | 0 | 0.40 | 0.02 (0) | 0.22 |
| 2024-Q3 | 1 | 14.3 | 1 | 0.78 | 0.93 (5) | 0.30 |
| 2024-Q4 | 1 | 15.3 | 1 | 0.85 | 0.91 (5) | 0.36 |
| 2025-Q2 | 1 | 18.1 | 1 | 0.87 | 0.99 (5) | 0.46 |
| 2025-Q3 | 1 | 25.3 | 1 | 0.98 | 1.00 (5) | 0.50 |
| 2025-Q4 | 1 | 17.0 | 1 | 0.82 | 0.99 (5) | 0.50 |
| 2026-Q1 | 1 | 16.15 | 1 | 0.75 | 0.20 (1) | 0.53 |
| 2026-Q2 | 1 | 23.8 | 1 | 0.96 | 0.21 (0) | 0.56 |
| 2026-Q3 | 1 | 16.7 | 1 | 0.78 | 0.92 (5) | 0.59 |

## What the results show

1. **The hunger-only target is mostly persistence.**
   - Hunger stayed above 11.3% in every quarter from 2023-Q4 on.
   - Every error by PERSIST and PIH is in the 2023 rise: 2023-Q2/Q3 and 2023-Q4 to 2024-Q2. At those origins the latest published reading was still at or below 11.3.
   - No model saw that rise coming.
2. **The served hunger part (PIH) is the best of the three.** It has the lowest Brier at both leads and is well calibrated for the high-hunger period. With 13–14 quarters, though, its advantage over persistence and ALWAYS-HIGH is not significant.
3. **The 12-family logistic model does not work for this target.**
   - It was trained on 4–18 quarters with one region-wide label.
   - It gives confident wrong forecasts in both directions: 0.89–1.00 in the low 2023 quarters, and 0.00–0.02 at the 2023-Q4 to 2024-Q2 rise at Lead 2.
   - Its provinces sometimes disagree on a label that is region-wide: in 4 quarters at Lead 1 and 1 quarter at Lead 2.
4. **ALWAYS-HIGH is hard to beat, and it shows the accuracy rules are lenient for this target.** With 11 of 13 quarters HIGH at Lead 2, a model that never looks at data reaches accuracy 0.846 and passes R1, R2, R4, R6 and R7. That is why the plan's extra Brier criterion against ALWAYS-HIGH matters.

## Caveats

- **n is 14 and 13 quarters.** R1 as written ("≥ 40 rows") is met only because each quarter appears five times, once per province. In quarters (≥ 40 needed) every model fails R1. The bootstrap resamples quarters.
- **The 2023–2026 quarters were seen before** (see the disclosure in PLAN.md). This analysis cannot validate anything; it can only suggest candidates.
- **The window holds one regime change** (the 2023 rise) and then 11 consecutive HIGH quarters. A model that tracks the latest reading looks good here regardless of skill.

## Implication for the thesis

There is **no candidate for a new pre-registration** from this test:
- No model passed R1–R7 at either lead.
- None beat ALWAYS-HIGH with confidence.

Dropping the price condition does not make Lead 2 reliable. It replaces a hard target with an easy, persistent one, where the honest comparison is against persistence and ALWAYS-HIGH, and nothing beats them.
