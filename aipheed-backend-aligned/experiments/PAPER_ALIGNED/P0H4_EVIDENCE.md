# P0H4 under the paper's reliability rule, and the Objective 4 / H3 comparison

**Status:** evidence for the team decision "P0H4 as the main model (pending adviser confirmation)", 2026-11-03.

**No model was fitted or changed.**
- Every number comes from the stored P0H4 walk-forward rows (`../LEAD2_OPTIMIZATION/out/predictions_addendum3.csv`,
  column `P0H4_p3`) and the served evaluation (`backend/data/ch1_engine/evaluation.json`).
- `p0h4_alg3.py` recomputes the table and writes `p0h4_alg3.json`, with the SHA-256 of both inputs. The recomputed
  accuracies equal the stored ones at every lead.
- **Development evidence:** every scored quarter (2023-Q1..2026-Q3) was examined while P0H4 was built.

## 1. Algorithm 3 as written

**Rule** (Chapter III pp. 41–43):
- one quarter per fold;
- a lead is reliable when the mean fold accuracy is ≥ 0.75;
- k = 1..8 are tried in order, halting at the first failing lead.

Each quarter holds the five provinces, so mean fold accuracy equals pooled accuracy.

**Maximum Reliable Lead Time = 2 quarters.** Lead 3 is the first failure (0.717).

| Lead | Rows (quarters) | Mean fold accuracy | Algorithm 3 | Always-LOW accuracy | HIGH caught (recall) | R1–R7 failed |
|---|---|---|---|---|---|---|
| 1 | 70 (14) | **0.843** | pass | 0.757 | 11 of 17 (0.647) | none |
| 2 | 65 (13) | **0.769** | pass | 0.738 | **6 of 17 (0.353)** | **R3, R5, R6** |
| 3 | 60 (12) | **0.717** | **fail: stop** | 0.717 | 4 of 17 (0.235) | R2, R3, R4, R6, R7 |
| 4–8 | 55 → 35 | 0.629–0.720 | after the stop | 0.691–0.750 | 0–2 of 9–17 | R2–R7 (Leads 6–8 also R1: fewer than 10 quarters) |

**Under R1–R7 (stricter, frozen before scoring) the Maximum Reliable Lead Time is 1.**

### R1–R7 at Leads 1 and 2

Source: `../P0H4_LEAD12_REVIEW/out/reproduce.json`, which matches the stored evaluation.

| Rule | Lead 1 | Lead 2 |
|---|---|---|
| R1 ≥ 10 quarters, ≥ 40 rows | pass (14 q, 70 rows) | pass (13 q, 65 rows) |
| R2 accuracy ≥ 0.75 | pass (0.843) | pass (0.769) |
| R3 balanced accuracy ≥ 0.70 | pass (0.776) | **fail (0.635)** |
| R4 accuracy > always-LOW and > persistence | pass (0.843 vs 0.757 / 0.743) | pass (0.769 vs 0.738 / 0.677) |
| R5 Brier < persistence and < climatology (p < 0.10) | pass (−0.125, p 0.018; −0.069, p 0.029) | **fail** (−0.129, p 0.027; but vs climatology −0.033, **p 0.146**) |
| R6 precision ≥ 0.60 and recall ≥ 0.60 | pass (0.688 / 0.647) | **fail (0.600 / 0.353)** |
| R7 each third ≥ 0.60, leave-one-quarter-out min ≥ 0.70 | pass (0.88 / 0.76 / 0.90; 0.831) | pass (0.72 / 0.70 / 0.90; 0.750) |

**Plainly:**
- **Lead 2 passes the paper's 75% rule, but by a narrow margin.**
  - Always-LOW would score 0.738, and P0H4 gets 50 of 65 right against always-LOW's 48.
  - The 95% interval of its accuracy is 0.63–0.89.
  - It catches 6 of the 17 HIGH province-quarters.
- **Why the misses happen:** at Lead 2 the binding limit is the hunger part. The 2023-Q4 and 2024-Q2 hunger surges
  were not visible in any SWS reading published before those forecasts, so 7 of the 17 HIGH cases could not be
  reached (evaluation.json, `horizon.why_not_longer`).
- **Rows beyond the stored leads:** none are missing. P0H4 stores walk-forward rows for Leads 1–15, and Algorithm 3
  stops at Lead 3.

## 2. Objective 4 / H3 for P0H4

**What exists.** The six comparators were fitted on the same 70 Lead-1 province-quarters by `FINAL_VERIFICATION`
(`../FINAL_VERIFICATION/out/horizon_predictions_lead{1,2}.csv`). They are tabulated beside P0H4 in
`../DASHBOARD_SELECTION/DASHBOARD_SELECTION_REPORT.md` §3.

### Lead 1 (70 rows, 17 HIGH)

| Model | Paper's name | Accuracy | Recall | Brier |
|---|---|---|---|---|
| **P0H4** | proposed | **0.843** | 11/17 | **0.132** |
| PERSIST-SI | I. naive persistence | 0.743 | 9/17 | 0.257 |
| LR-GOV | II. PSA-only indicator baseline (logistic, government data only) | 0.800 | 8/17 | 0.179 |
| LR-NLP | III. NLP-only sentiment baseline (logistic, news only) | 0.686 | 12/17 | 0.212 |
| LR-COMB | IV. logistic regression baseline (combined) | 0.771 | 6/17 | 0.192 |
| LGBM-NLP | H3: LightGBM, news only | 0.700 | 3/17 | 0.214 |
| LGBM-GOV | H3: LightGBM, government data only | **0.914** | 14/17 | **0.086** |
| always-LOW | reference | 0.757 | 0/17 | 0.243 |

### Lead 2

- P0H4 on all 65 rows: 0.769.
- On the 60 rows where all the comparators exist:

| Model | Accuracy |
|---|---|
| P0H4 | 0.750 |
| always-LOW | 0.717 |
| LGBM-GOV | 0.700 |
| LR-GOV | 0.567 |
| LR-COMB | 0.483 |
| LR-NLP | 0.433 |
| LGBM-NLP | 0.400 |

### Significance tests that exist for P0H4

| Comparison | Result | Source |
|---|---|---|
| P0H4 vs persistence (Brier) | Lead 1: −0.125, p 0.018. Lead 2: −0.129, p 0.027 (one-sided, cluster bootstrap) | R5, `reproduce.json` |
| P0H4 vs climatology (Brier) | Lead 1: −0.069, p 0.029. Lead 2: −0.033, p 0.146 | R5 |
| P0H4 − per-lead CH1/government-only LightGBM (Brier) | **+0.045 [+0.014, +0.079], p 0.027 (P0H4 worse)** | DASHBOARD_SELECTION §3 |

**Missing (not run; would need your approval).** There is no paired, Holm-corrected Brier test of **P0H4** against
LR-GOV, LR-NLP, LR-COMB or LGBM-NLP, at either lead. The "beats all but LGBM-GOV" statements in the selection
reports were tested for the per-lead CH1-LGBM (`../FINAL_THESIS_OBJECTIVES/THESIS_OBJECTIVE_ASSESSMENT.md`), not
for P0H4.

These tests would need **no new model**: the comparators' forecasts are already stored, so they could be scored
against P0H4 on the same rows. I have not run them.

**Reading for H3, from what exists:**
- **H3 is not rejected for P0H4.** The government-only LightGBM is more accurate (0.914 vs 0.843) and has a
  significantly lower Brier score at Lead 1 (p 0.027).
- **Rejecting H3 needs P0H4 to beat all six comparators.** It already fails against one, so the missing tests cannot
  change this verdict. They would only say which of the other five it beats significantly.
