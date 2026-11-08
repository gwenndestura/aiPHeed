# LEAD2_OPTIMIZATION Addendum 3: hunger-onset term and final evaluation rules (hashed before the Addendum-2 results were seen)

**When.** 2026-10-27. The Addendum-2 leakage audit was running and no Addendum-2 metric existed.

**Known when this was written:**
- Addendum-1 results (`out/results_addendum1.json`);
- the component analysis and oracle ceilings (`out/component_analysis.txt`);
- the error analysis.

Everything is **development evidence**.

## 1. Why (`out/component_analysis.txt`)

**False negatives by component, Lead 2 (65 rows, 17 HIGH):**

| Arm | Hunger only | Price only | Both | Total |
|---|---|---|---|---|
| P0H0 | 4 | 4 | 3 | 11 |
| P4H0 | 4 | 3 | 3 | 10 |

**The hunger term is binding.** With the served π_H, **no** price model passes at 0.50; even the oracle price gives recall 0.59. With the oracle hunger condition, P4's price term reaches accuracy 0.738 and recall 0.65 at 0.50.

**Within 2021+ data, no hunger onset can be learned before the 2024-Q2 forecast.** The 2023-Q4 surge reading (14.3) was published 2024-01-22, after the issue date 2024-01-01. No onset precedes it in the 2021+ training labels.

**Group-B misses are hunger-term misses** (2024-Q2: price flagged, π_P 0.68–0.80). Over 1998–2020, Region IV-A rice-price shocks (2008, 2014) coincided with rising BL hunger. A hunger-crossing term that uses issue-time price signals is the one justified candidate.

## 2. Hunger candidates

| Id | Definition | Data | Adoptable |
|---|---|---|---|
| H0 | Served π_H (latest reading, 2021+ error σ) | 2021+ | yes (incumbent) |
| **H4** | H0 with σ from the latest-reading errors of **all four SWS areas** pooled, at the same true horizon. Uses quarters with rounds published before O(t), 2021+ only; fewer than 8 pooled errors → H0. | 2021+ | yes |
| **H3a** | Logistic hunger-crossing model, L2 penalty (C = 1), standardised features. See below. | 2021+ | yes |
| **H3b** | H3a on BL 1998+ (pre-2021 releases dated by the E114 rule) with Region IV-A CPI from 1994 | 1998+ | **no: sample b**, sensitivity only, unless you formally revise the scope |

**H3a in detail:**
- **Features:** latest BL reading, true horizon h, Region IV-A rice CPI YoY and food CPI YoY at the pseudo-origin month m0′.
- **Training pairs:** every pair (q0, q0+h), h = 1…6, of BL quarters published before O(t). Features are taken as at the pseudo-origin t′ = q0+1 (m0′ = month 2 of t′); the label is H(q0+h) > 11.3.
- **Eligibility:** at least 20 pairs with ≥ 5 per class, otherwise H0.
- **Prediction:** latest BL reading at O(t), true horizon of (t, k), CPI at m0.

## 3. Combinations, selection and serving

**Price arms combined with each hunger candidate:**
- P0 (served);
- P4 (structural prior, Addendum 1);
- the Addendum-2 final price arm, if different.

**Selection.** Among the sample-a combinations, the lowest **Lead-2 development Brier** (targets ≤ 2024-Q4) is adopted. Ties within 0.0005 go to the incumbent order (H0 before H4 before H3a; P0 before P4 before the Addendum-2 arm).

**Serving.** The PROTOCOL_LEAD2 §4 rule applies, with the PROTOCOL_LEAD2 serving conditions unchanged.

## 4. Final evaluation rules (frozen now; apply to Addenda 2 and 3)

| Item | Rule |
|---|---|
| Primary Lead-2 population | The 65 UNI-FINAL Lead-2 rows: origins 2022-Q4..2026-Q1, targets 2023-Q2..2026-Q3, 13 quarters × 5 provinces. Identical for every candidate; a candidate missing any row is reported as failing. |
| Target | T43c exactly as verified (`out/target_verification.txt`) |
| Baselines | ALWAYS-LOW, PERSIST-SI, CLIM on the same rows |
| Validation | Expanding-window rolling origin; development = targets ≤ 2024-Q4; later block = 2025-Q2..2026-Q3 (seen before; not untouched) |
| Acceptance | R1–R7 at 0.50 + the Addendum-2 later-block check |
| Threshold | **0.50** (dashboard rule). The research τ of Addendum 2 F2 (development-selected) is reported only. |
| Final confirmation (untouched) | The sealed prospective forecasts (seal `fcc4130d`, and a new seal for any adopted candidate before its first unseen outcome), scored on SWS 2026-Q4 onward |
| Verdicts | Addendum 2 §3: no "Reliable" verdict is possible before untouched outcomes exist |

**Effective sample size.** The hunger condition is one regional observation per quarter: 13 independent hunger outcomes at Lead 2, not 65. All CIs use cluster bootstrap by quarter.
