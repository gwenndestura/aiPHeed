# LEAD2_POST_SWS_PRICE: results

**Decision: (C).** Lead 2 issued after the SWS release, with the price term's CPI cutoff also moved to that date (M2), does **not** pass. It fails three of the seven reliability criteria:

- **R3**, balanced accuracy 0.681 (0.70 needed);
- **R4**, its accuracy only ties persistence at 0.754;
- **R6**, precision and recall both 0.529 (0.60 needed).

It is worse on classification than M0, the same issue date with the old CPI cutoff, which failed only R6. M2 improves the probabilities (Brier 0.153 against 0.167; AUC 0.827 against 0.760), but no more high-risk rows cross 0.50.

**This was the final pre-registered Lead-2 test on the 2023–2026 rows. No further variant will be tested on these quarters.** Lead 2 stays experimental. The only remaining route to confirming any Lead-2 variant is sealed prospective forecasts (see `SEALING_PLAN.md`).

| Item | Value |
|---|---|
| Protocol | `PROTOCOL.md`, sha `b547e0ab…`, frozen 2026-10-31T12:42:44Z |
| Amendment 1 | Parity tolerance at the stored precision; written before any model run. `PROTOCOL_AMENDMENT_1.md`, sha `d80c568a…`, frozen 12:46:21Z |
| Runs | `runner/price_refit.py served` (203 s, exit 0); `runner/price_refit.py post` (331 s, exit 0); `runner/score_price.py` (exit 0). There were no failed runs. Logs are in `out/` |

## 1. What was changed

**M2 = H4(O'(t)) × P0_price'(t).** P0_price' is the served P0 arm refitted walk-forward with the CPI cutoff of every origin, training and test, set to the newest month available at O'(t). It is implemented as an in-memory, parameterised replacement for `e41_lib.m0_of`; no file was edited. The World Bank columns, news, climate and all other inputs stay as served.

**The cutoff moved at 13 of 23 origins.** On the 13 official test origins it moved by one month at 6:

| Origins | CPI cutoff |
|---|---|
| 2023-Q1, 2023-Q2, 2023-Q3, 2024-Q1, 2025-Q2, 2026-Q1 | +1 month |
| 2022-Q4, 2023-Q4, 2024-Q2, 2024-Q4, 2025-Q1, 2025-Q3, 2025-Q4 | unchanged: the SWS round came out in the first month of the next quarter, so the month-plus-2 rule allows no newer CPI |
| Training-only origins (2021-Q1, Q3, Q4, 2022-Q1, Q2, 2025-Q3 lead-1 rows and later) | moved; several 2021–2022 origins by +2 months, at the 67-day cap |

Because the training cutoffs moved, P0_price' differs from P0_price at **every** origin, even where the test cutoff did not move.

## 2. Checks before scoring (all passed)

| Check | Result |
|---|---|
| Reproduction | P0H4 Lead 2 **6/4/11/44**, Lead 1 **11/5/6/48**, M0 **10/6/7/42**: all equal |
| Parity (a): served-cutoff copy vs stored `P0_price` | 65/65 Lead-2 rows equal at 6 significant digits, max abs. diff 4.9e-7; 70/70 Lead-1 rows equal; configuration equal on every row |
| Parity (b): copy vs the original `l2_lib.forecast_origin` | At 2022-Q4, 2024-Q2 and 2026-Q1: max abs. diff **0.0**, 75/75 rows each, same configuration. LightGBM is deterministic with the same seeds |
| Leakage, all 23 origins (training included) | Every CPI cutoff available at its O' (first day of M+2 ≤ O'). `Data.cut` never holds a later month, and holds exactly the cutoff month at every origin. Issue dates are non-decreasing, so training origins never see more than the test origin |
| Leakage, H4 | The newest SWS round was published before O' on all 13 test origins (O' = publication + 1 day, or the cap) |
| Perturbation, 2023-Q4 origin | 340 CPI index and 340 YoY values after 2023-11 replaced by random numbers: P0_price' unchanged (max diff **0.0**), and equal to the main run |
| Training rows | Every training row has origin < t and target ≤ t−1 |

## 3. Official 65 Lead-2 rows (13 quarters, T43c, threshold 0.50)

95% quarter-cluster bootstrap CIs (B = 2000, seed 2036).

| Model | Acc | Bal. acc | Precision | Recall | Specificity | AUC | Brier | TP/FP/FN/TN | Onsets |
|---|---|---|---|---|---|---|---|---|---|
| P0H4, original issue O(t) | 0.769 (0.63–0.89) | 0.635 (0.48–0.81) | 0.600 (0.00–0.80) | 0.353 (0.00–0.75) | 0.917 (0.83–0.98) | 0.625 (0.45–0.81) | 0.194 (0.12–0.27) | 6/4/11/44 | 0/10 |
| M0, post-SWS issue | 0.800 (0.69–0.89) | 0.732 (0.55–0.87) | 0.625 (0.33–0.78) | 0.588 (0.17–0.90) | 0.875 (0.75–0.96) | 0.760 (0.59–0.91) | 0.167 (0.11–0.23) | 10/6/7/42 | 4/10 |
| **M2, post-SWS issue + CPI** | **0.754** (0.63–0.88) | **0.681** (0.52–0.81) | **0.529** (0.25–0.71) | **0.529** (0.17–0.80) | **0.833** (0.66–0.96) | **0.827** (0.71–0.93) | **0.153** (0.10–0.21) | **9/8/8/40** | **3/10** |
| Persistence at O' | 0.754 (0.63–0.88) | 0.719 (0.53–0.86) | 0.524 (0.20–0.76) | 0.647 (0.22–0.93) | 0.792 (0.63–0.93) | 0.719 (0.53–0.86) | 0.246 (0.12–0.37) | 11/10/6/38 | 6/10 |
| Climatology at O' | 0.738 (0.58–0.88) | 0.500 | – | 0.000 | 1.000 | 0.356 (0.17–0.62) | 0.229 (0.11–0.36) | 0/0/17/48 | 0/10 |
| Always-LOW | 0.738 (0.58–0.88) | 0.500 | – | 0.000 | 1.000 | 0.500 | 0.262 (0.12–0.42) | 0/0/17/48 | 0/10 |

### R1–R7

| Rule | P0H4 original | M0 | **M2** |
|---|---|---|---|
| R1 coverage | pass (13 q, 65 rows) | pass | pass |
| R2 accuracy ≥ 0.75 | pass 0.769 | pass 0.800 | pass 0.754 |
| R3 balanced ≥ 0.70 | **fail** 0.635 | pass 0.732 | **fail 0.681** |
| R4 beats always-LOW and persistence | pass 0.769 vs 0.738/0.677 | pass 0.800 vs 0.738/0.754 | **fail 0.754 vs 0.738/0.754 (tie)** |
| R5 Brier better than persistence and climatology | **fail** (−0.129, p 0.027; −0.033, p 0.146) | pass (−0.079, p 0.052; −0.062, p 0.067) | pass (−0.093, p 0.014; −0.076, p 0.027) |
| R6 precision and recall ≥ 0.60 | **fail** 0.600/0.353 | **fail** 0.625/0.588 | **fail 0.529/0.529** |
| R7 stability | pass (thirds 0.72/0.70/0.90; LOQO min 0.750) | pass (0.84/0.65/0.90; 0.783) | pass (0.80/0.65/0.80; 0.733) |
| **Failed** | R3, R5, R6 | R6 | **R3, R4, R6** |

### By third

| Third | M0 acc / recall / Brier | M2 acc / recall / Brier |
|---|---|---|
| 2023-Q2..2024-Q2 | 0.84 / 0.571 / 0.133 | 0.80 / 0.429 / 0.133 |
| 2024-Q3..2025-Q3 | 0.65 / 0.667 / 0.255 | 0.65 / 0.667 / 0.216 |
| 2025-Q4..2026-Q3 | 0.90 / – (0 HIGH caught) / 0.122 | 0.80 / – / 0.115 |

## 4. M2 against M0, row by row

**M2 catches none of M0's 7 misses.** The price term rose for 5 of them, but no product reached 0.50:

| Target | Province | P0_price → P0_price' | M0 → M2 |
|---|---|---|---|
| 2023-Q4 | Laguna | 0.495 → 0.515 | 0.247 → 0.258 |
| 2023-Q4 | Quezon | 0.495 → 0.467 | 0.247 → 0.233 |
| 2023-Q4 | Batangas | 0.495 → 0.534 | 0.247 → 0.267 |
| 2024-Q3 | Quezon | 0.432 → 0.601 | 0.355 → **0.494** (just below 0.50) |
| 2024-Q4 | Cavite | 0.166 → 0.212 | 0.161 → 0.205 |
| 2024-Q4 | Laguna | 0.173 → 0.469 | 0.167 → 0.454 |
| 2026-Q2 | Cavite | 0.345 → 0.468 | 0.278 → 0.377 |

**Why the misses stay.** In 2023-Q4 the hunger term itself is only 0.50. Elsewhere the hunger term (about 0.82–0.97) times a price term near 0.5 stays under 0.50. A refreshed price term alone cannot lift these rows.

**M2 adds 4 false alarms:** 2025-Q3 Batangas (0.589), 2025-Q4 Quezon (0.522), 2026-Q2 Laguna (0.526), 2026-Q2 Quezon (0.508).

**M2 drops 3 of M0's alarms:**

- 1 hit lost: 2024-Q2 Quezon, HIGH, 0.488;
- 2 false alarms removed: 2024-Q3 Laguna, 2026-Q3 Quezon.

**Net effect:** TP 10 → 9, FP 6 → 8.

## 5. The price half

**Independent check (pre-2021): not evaluable.** As stated in the protocol, the served P0 features cannot be built before 2021:

- the E41 loader raises `WindowViolation` on CPI before 2021-01;
- the news composites, PSA LGU vulnerability and Pink Sheet columns exist only from 2021.

Y12's pre-2021 provincial CPI covers the CPI family only. No substitute model was run. So, even had R1–R7 passed, the decision would have been capped at a development pass.

**Development diagnostic only** (the same 65 rows, scored against the price condition, not T43c; this is not the independent gate):

| Price term | TP/FP/FN/TN | Brier | Bal. acc |
|---|---|---|---|
| P0_price (served cutoff) | 14/14/12/25 | 0.227 | 0.590 |
| P0_price' (O' cutoff) | 18/15/8/24 | 0.206 | 0.654 |
| Price persistence at O' | 22/17/4/22 | 0.323 | 0.705 |

The newer CPI improves the price term, but it still separates the classes less well than simply carrying the newest price condition forward. Under the gate's two conditions, this development comparison would pass on Brier and fail on balanced accuracy.

## 6. Robustness

Exactly as in `LEAD2_POST_SWS_ISSUE` §8. The borderline quarters are 2023-Q2 (BL 11.3) and 2023-Q3 (BL 10.3).

| | M0 | M2 |
|---|---|---|
| Observed (R2/R3/R4/R6/R7) | pass/pass/pass/fail/pass | pass/**fail/fail/fail**/pass |
| Flip 2023-Q2 | R2, R3 fail | R2, R3, R4, R6, R7 all fail |
| Flip 2023-Q3 | R2, R3 fail | all fail |
| Flip both | R2, R3, R7 fail | all fail |
| Monte Carlo pass rate R2 / R3 / R4 / R6 / R7 (2000 draws) | 0.412 / 0.380 / 0.999 / 0.059 / 0.820 | 0.329 / 0.054 / **0.000** / **0.000** / 0.407 |
| **Monte Carlo, all rules together** | 0.059 | **0.000** |

## 7. What this means

- Moving the CPI cutoff to the post-SWS date made the Lead-2 probabilities better calibrated and better ranked: the best Brier and AUC of any Lead-2 variant on these rows.
- It did **not** make the 0.50 classifications more reliable. It caught none of the remaining missed high-risk rows, added false alarms, and lost the R3 and R4 passes that M0 had.
- The remaining Lead-2 misses are therefore not just stale CPI. They come from a hunger probability near 0.5 multiplied by a price probability near 0.5, a structural limit of the product form at a 0.50 threshold. Changing that form or the threshold would be a new variant on the same quarters, which this protocol rules out.

**This result must never be reported as the original Lead 2 passing.** Neither M0 nor M2 passes R1–R7. The original Lead 2 (issued at O(t)) fails R3, R5 and R6. Lead 1, the served system, the seals (a498b5ef, e2bef0b2, Y16 208b5754), R1–R7, the 0.50 threshold and the dashboard's "experimental" label for Lead 2 are unchanged.

## 8. Files

| Path | Contents |
|---|---|
| `runner/price_refit.py` | Parameterised P0 refit, leakage audit, parity, perturbation |
| `runner/score_price.py` | Scoring, rules, row comparison, robustness, decision |
| `out/p0_price_served.csv`, `out/p0_price_post.csv` | P0 price for every origin and lead |
| `out/refit_served.json`, `out/refit_post.json` | Fits, leakage rows, parity, perturbation |
| `out/results.json`, `out/eval_rows.csv` | All scores and the 65 rows |
| `out/log_*.txt`, `out/run_stdout_*.txt` | Logs of every run |
