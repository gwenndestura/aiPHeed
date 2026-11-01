# Lead-2 reliability research, Phase 2: experiment plan

**Status:** this plan is frozen (SHA-256 in `common/PLAN2_SHA256.txt`) before Y2, Y3, Y4 or Y5 is run.

**Relation to Phase 1:** `EXPERIMENT_PLAN.md` (Phase 1, X1–X4) stays frozen and unchanged.

**Already run before freezing (diagnostics, not candidates):**

- **Y0 scoring audit.** It needs no outcome-dependent choice.
- **The component error breakdown** of P0H4 at Lead 2. Of the 11 false negatives, 7 come from a low hunger term (π_H 0.22–0.40) and 4 from a low price term. This repeats `LEAD2_OPTIMIZATION/LEAD2_ERROR_ANALYSIS.md`.

## 1. Fixed

| Item | Value |
|---|---|
| Rules R1–R7 | Protocol section 7, as implemented in `P0H4_LEAD12_REVIEW/runner/reproduce.py`. They are applied unchanged through `common/p2lib.official_rules`. |
| Lead-2 test rows | The 65 official P0H4 rows: 13 target quarters × 5 CALABARZON provinces. Target T43c = BL hunger > 11.3 AND the provincial price condition. |
| Threshold | 0.50 for every candidate |
| Information | Only data published before the issue date (first day of quarter t+1). See the availability rules in section 3. |
| Bootstrap | Quarter clusters, B = 5000, seed 2036 |

Nothing in this plan alters R1–R7, the test rows, the threshold or the labels.

## 2. Hypotheses

| ID | Hypothesis | Why it might overcome the Lead-2 limit | Kind |
|---|---|---|---|
| **Y2** | A latent-state (Kalman) AR(1) model of hunger. SWS sampling error per round is known from the margin of error, and missing or late rounds are handled by the filter. | RW treats the last reading as the truth. With ±4–6 point sampling error, a noise-aware filter can separate signal from noise and give properly widened predictive probabilities at horizon 3. | hunger term |
| **Y3a** | The H3b logistic hunger-crossing model, which uses rice and food CPI from Region IV-A. It is re-run unchanged (`a3.h3(t, k, "b")`) on **2005–2020 BL origins**. | It is the only hunger term that lifted P0H4 Lead 2 (sample b), but it was never tested on independent years. Rice shocks in 2008 and 2014 coincided with rising BL hunger. | hunger term |
| **Y3b** | A pooled four-area, L2-regularised logistic model of crossing. Features: distance of the last reading to 11.3, deviation from the area mean, true horizon h, rice CPI YoY, 3-month change in rice YoY, food CPI YoY, ONI latest, ONI 6-month max, typhoons in PAR last complete quarter, palay production YoY, unemployment change. The penalty is chosen by inner chronological validation on the last 25% of training pairs. | Several earlier-published drivers (prices, El Niño, typhoons, harvests, jobs) may anticipate a crossing 3 quarters ahead. Pooling four areas gives about 4× the training pairs. | hunger term |
| **Y3c** | A continuous-change model. It forecasts Δ = H(target) − last reading by ridge regression on the Y3b features (penalty chosen the same way). The probability comes from a Gaussian predictive distribution with σ = training residual RMSE. | A continuous target uses the full level information rather than 0/1. Crossing is then derived from it, so the original target is kept. | hunger term |
| **Y4** | Lead-specific stacking of the two P0H4 terms. A logistic model on [logit π_H, logit π_P] is refitted at each origin, only on earlier rows whose T43c label was published before the issue. It is run with P0 and with P4. | The product rule assumes the hunger and price conditions are independent and that each is calibrated. A fitted combination can correct a systematic under-forecast. | combination. **Exploratory only:** it can be fitted only on 2021+ rows, the same quarters as the test. |

Y5 is the confirmation step (section 5). Y6 is a desk search for earlier hunger signals; it is evidence, not a model. Y1 (label sensitivity) and Y7 (oracle headroom) are diagnostics.

## 3. Availability at issue date O(t) = first day of quarter t+1

Each indicator uses only values released before O(t), as follows:

| Indicator | Newest value used |
|---|---|
| SWS rounds | Published before O(t). Pre-2021 release dates use the E114 rule: label month end + 60 days. |
| CPI (PSA, released about the 5th of the next month) | Month 2 of quarter t (m0) |
| ONI (NOAA CPC, early next month) | The 3-month season ending month 1 of quarter t |
| Typhoons in PAR (IBTrACS; occurrence known in real time) | Quarter t−1 (conservative) |
| Palay production (PSA, about 6 weeks after quarter end) | Quarter t−1 |
| LFS unemployment (quarterly rounds before 2021) | The newest round with month ≤ m0(t) − 2 |

For training pairs (reading at q0 → outcome at q0 + h), the features are taken at the pseudo-issue O(q0) under the same rules. A pair is used only if both its reading and its outcome were published before O(t).

## 4. Development and gate: 2005–2020, independent of the test

- **Data:** origins whose targets fall in 2005-Q1..2020-Q4, at Lead 2. True horizons are as observed (mostly 3).
- **Areas:** pooled-fit models are scored on all four areas. BL is also scored with an area-held-out fit (Y2, Y3b, Y3c). Y3a is BL-only by construction.
- **Comparator:** RW (persistence with the empirical horizon-h RMSE), as in X2.

**Gate.** A hunger candidate proceeds to Y5 only if all three hold, at Lead 2:

| | Condition |
|---|---|
| G1 | Brier lower than RW, one-sided quarter-cluster p < 0.10, on the candidate's natural scoring set (all areas for pooled models; BL for Y3a). |
| G2 | BL Brier lower than RW. Use area-held-out where defined, else BL pooled. |
| G3 | BL balanced accuracy at 0.50 is higher than RW's, so the gain reaches the 11.3 crossing. |

## 5. Y5 confirmation on the official 2021–2026 rows

**Single confirmatory candidate.** Among gate-passing candidates, the one with the lowest BL Lead-2 Brier over 2005–2020 is the confirmatory candidate. Its hunger probability replaces π_H4 at Lead 2 (and at Lead 1, as a check):

- with P0 (served price term): **primary**;
- with P4 (structural-prior price term): secondary.

R1–R7 are scored once. Other gate-passers are reported as secondary.

**If no candidate passes the gate,** Y5 still scores every Y2/Y3 candidate × P0 on the official rows, as a descriptive result only. It cannot be called confirmatory.

**Honesty clause.** The 2021–2026 quarters were already used by about 20 earlier configurations, and by me (component breakdown). A pass in Y5 is therefore labelled "passes on the historical test; reliability requires the prospective seal". It is never called reliable without sealed prospective quarters.

## 6. Reporting

For every candidate, the report gives:

- n, quarters and prevalence;
- confusion matrix, accuracy, balanced accuracy, precision, recall, specificity, F1, AUC and Brier;
- quarter-cluster 90% CIs;
- each of R1–R7 individually;
- the design effect and effective n.

All failures are reported.
