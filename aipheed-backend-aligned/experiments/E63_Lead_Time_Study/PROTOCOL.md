# E63 protocol: lead-time study of the E56/E58 procedure (frozen before any E63 score is read)

**Written:** 2026-10-19.
**Location:** this folder sits in the session worktree `claude/bold-euclid-f53301` at `aipheed-backend-aligned/experiments/E63_Lead_Time_Study/`. The frozen code and data are read from the main checkout (`C:\Users\admin\aipheed`, branch `e62-final-audit`), which this study does not write to.
**Freeze:** the SHA-256 of this file (LF line endings) is written to `runner/PROTOCOL_SHA256.txt`, with the time in `runner/PROTOCOL_FROZEN_AT.txt`, before `runner/e63_predict.py` runs. The same hash is copied to the session notes folder outside the repository. Nothing is committed without the user's approval.
**Requirement basis:** Chapter I only. Objective 2 V: *"forecast performance across multiple lead times via walk-forward expanding-window cross-validation to empirically determine the furthest horizon at which reliable forecasting is achievable."* No 75% accuracy threshold is used anywhere in this protocol.

## 0. Evidence status

- This is **development evidence**. Every target quarter here (2023-Q4..2026-Q3) was examined in E43–E62.
- **Lead 2 is not new.** E57 scored the same 10 origins (50 rows) before this protocol was written:
  - accuracy 0.72, Brier 0.214;
  - against persistence: 7 quarter wins and 3 losses, paired Brier CI [−0.41, −0.062];
  - against climatology: 5 wins and 5 losses, CI [−0.187, 0.001].
  - So the lead-2 verdict under the section 8 rule can be anticipated from E57. It is disclosed here, not hidden.
- **Leads 1 and 3 have never been scored** for this model.
- **The section 8 rule was set by the requesting session** (the E61 addendum significance rule applied to persistence and climatology). It was not chosen after seeing any lead-1 or lead-3 result.
- **Seen before freezing:**
  - the score-free eligibility check (`tables/eligibility.csv`, `out/eligibility.json`), which reads no label value;
  - the identity check showing that the lead-2 inputs of `e63_lib` equal the E56 inputs exactly.

## 1. Leads, origins and targets

**Origin:** O(t) = 00:00 on day 1 of quarter t+1, as in E41/E56.

**Lead:** lead h means target quarter t+h. Lead 1 is the quarter that begins on the issue date. Lead 2 is the served E56/E58 horizon. Lead 3 and lead 4 are one and two quarters further.

**Walk-forward, expanding window:** each origin refits on every training target t'+h ≤ t−1 that is available at O(t), from the 2021-Q3 feature origin onward. Earlier origins never see later data.

**Eligible origins** (score-free check, 2026-10-19). An origin is eligible when E57's rule holds:
- at least 6 price-training quarters;
- a test projection exists;
- at least 6 regional hunger training pairs;
- a T43 label can be formed for the target (an SWS round exists and the CPI quarter is complete), with the target ≤ 2026-Q3.

| Lead | Origins (issue quarter t) | Targets | Quarters | Rows |
|---|---|---|---|---|
| 1 | 2023-Q3..2026-Q2 | 2023-Q4..2026-Q3 | 12 | 60 |
| 2 | 2023-Q4..2026-Q1 (= E57) | 2024-Q2..2026-Q3 | 10 | 50 |
| 3 | 2023-Q4..2025-Q4 | 2024-Q3..2026-Q3 | 9 | 45 |
| 4 | none | — | 0 | 0 |

**Excluded, with reasons:**

| Case | Reason |
|---|---|
| Earlier origins at leads 1–3 | fewer than 6 price-training quarters or hunger pairs (data begin 2021) |
| Target 2022-Q1 | no SWS round, so no T43 label |
| Targets after 2026-Q3 | outcome not yet observed |
| **Lead 4, every origin** | **The E56 procedure is not computable.** The year-earlier base months of a lead-4 target are the three months of the issue quarter t. Month 3 of t is after the CPI cutoff (month 2 of t). So the base-effect projection (`base_m`, `gbase_m`) and `F_hat_M1` are undefined, and `E.ok` fails at every origin. No substitute procedure is introduced. Lead 4 is reported as "not computable under the pre-registered cutoffs" and cannot meet the section 8 rule. |

**Common-target set** (sensitivity check): targets 2024-Q3..2026-Q3, which are eligible at leads 1, 2 and 3 (9 quarters, 45 rows per lead).

## 2. Information cutoffs (E41/E56 rules, unchanged)

Every forecast at O(t) uses only `Data.cut(t)`, `cut_extra(t)` and policy events announced before O(t):

| Input | Latest information allowed at O(t) |
|---|---|
| CPI index and published YoY (food, all items) | month 2 of quarter t (`m0_of(t)`) |
| SWS hunger (hunger component) | approved rounds **posted** before O(t) |
| T43 labels (training, persistence, climatology) | quarters ≤ t−1 whose SWS rounds were all posted before O(t), with CPI from `d.cut(t)` |
| Palay, corn, fisheries production | quarter t−1 |
| LFS unemployment and underemployment | month 3 of quarter t−1 |
| ENSO phase, OFW remittances, FX, rice wholesale price | quarter t−1 |
| Typhoon counts, news counts | quarter t, which has ended at O(t). This is the E56 rule, kept unchanged; the requesting brief's shorthand "other inputs to t−1" is narrower. |
| Rice-policy events | announced before O(t) |
| Poverty (PSA SAE 2021) | only at origins on or after 2025-01-01 (POV-AS) |

**Training pairs:** only targets t'+h ≤ t−1.

**Data window:** 2021-01 to 2026-10-14. No pre-2021 value (the `WindowViolation` asserts of `e41_lib` stay active). No new data are fetched, and no input file is changed.

## 3. Procedure at lead h (E56-TUNED, read-only)

**Code path:** `E56_LightGBM_Optimization/runner/e56_lib.py`, through `e55_lib`, `e53_lib`, `e46_i7` / `e46_lib`, `e44_components`, `e43_lib` and `e41_lib`. All are imported read-only.

**Generalisation:** in that chain the horizon is a literal 2 in six places. `runner/e63_lib.py` re-implements exactly those six with h as a parameter and changes nothing else:

| ID | Original | Lead-h version |
|---|---|---|
| H1 | `F_hat_M1 = m1_point(d, t, 2, p)` | `m1_point(d, t, h, p)` |
| H2 | policy shares over `target_months(t, 2)` | `target_months(t, h)` |
| H3 | base-effect projections over `target_months(t, 2)` | `target_months(t, h)` |
| H4 | price training pairs t'+2 ≤ t−1 | t'+h ≤ t−1 |
| H5 | hunger training pairs (t', H(t'+2)) | (t', H(t'+h)) |
| H6 | inner-fold embargo 3 (targets ≤ q−3 at inner origin q−2) | h+1 (targets ≤ q−h−1 at inner origin q−h) |

**Unchanged from E56:**
- the 72 configurations (seed 56);
- nested selection by embargoed forward log-loss on training targets only, with the simplicity tie-break;
- P(HIGH) = P_hunger × P_price;
- the decision rule p ≥ 0.5.

**E58-EW at lead h:** warn iff P_price ≥ 0.5. The scored probability is P_price, as in E58. There is no refit.

**No tuning:** nothing is chosen with reference to any evaluation quarter.

## 4. Sealing

`runner/e63_predict.py` runs these steps in order:

1. Checks the hash of this file.
2. Computes the lead-2 forecasts and checks them against the sealed E57 file. `E56_p`, `E56_p_price` and `E56_p_hunger` must agree within 1e-9 on all 50 rows. If they do not, nothing is written.
   - A mismatch is an implementation defect in `e63_lib`. It is corrected without reading any label and logged in `DEVIATIONS.md`.
3. Computes leads 1 and 3, plus the as-of baselines (section 5), at every eligible origin.
4. Writes `sealed/predictions.csv` and `sealed/predictions.csv.sha256`. These are write-once: the script refuses to run if the file exists. The file contains no outcome.

`runner/e63_score.py` refuses to run unless both the protocol hash and the sealed-file hash verify. Only after that does it build the T43 labels.

## 5. Outcome and baselines (same rows, same lead)

**Outcome:** T43 (E55 PROTOCOL section 2). HIGH iff the quarter-mean SWS hunger over all rounds is > 11.3, **and** the provincial food YoY or the food-minus-headline gap is above its province P60 threshold (E40, frozen 2021–2022).

**Baselines** (E57 definitions, as of O(t), so identical across leads for the same origin):

| Baseline | Probability |
|---|---|
| **Persistence** | latest T43 label known at O(t) for the province (`e55_lib.t43_last`), 0 or 1 |
| **Climatology** | share of HIGH among all T43 labels known at O(t) (all provinces) |
| Majority | 1 if that share ≥ 0.5, else 0 (descriptive) |
| Province climatology | the province's own known share of HIGH (descriptive) |

## 6. Metrics (per lead; repeated on the common-target set)

**Counts:**
- rows, quarters, actual HIGH;
- predicted HIGH, correct.

**Decision metrics** (p ≥ 0.5):
- accuracy;
- balanced accuracy;
- HIGH recall and HIGH precision;
- LOW recall.

**Probability metrics:**
- Brier score;
- log loss, with probabilities clipped to [0.001, 0.999] so 0/1 baselines are finite;
- AUC, where both classes occur.

**Calibration:**
- calibration-in-the-large = mean(y) − mean(p);
- logistic calibration slope (unpenalised regression of y on logit p; not reported for 0/1 baselines or when not estimable);
- reliability table with 5 equal-width bins (count, mean p, observed share).

**Uncertainty:**
- quarter-cluster bootstrap: 4000 draws, seed 63, resampling whole target quarters;
- 95% percentile CIs for accuracy, balanced accuracy, HIGH recall, HIGH precision, Brier and log loss.

**Paired comparisons** (model vs persistence and vs climatology):
- mean Brier difference with its cluster CI;
- per-quarter mean-Brier wins and losses, with a two-sided exact sign test (ties excluded).

**Tables:**
- a per-quarter table for each lead;
- the same metrics for every baseline.

## 7. Model arms scored

| Arm | Probability | Decision | Role |
|---|---|---|---|
| **E56** | P(HIGH) = P_hunger × P_price | p ≥ 0.5 | **headline**: the forecasting model |
| E58-EW | P_price | P_price ≥ 0.5 | secondary: the served warning form |

## 8. Working definition of "reliable"

Chapter I does not define "reliable". E63 uses the following rule.

**Reliable at lead h** means **both** of the following hold on that lead's eligible rows:

| Condition | Against | Requirement |
|---|---|---|
| **R-P** | persistence | the quarter-cluster 95% CI of the mean paired Brier difference (model − baseline) lies entirely below 0, **and** the quarter sign test favours the model with two-sided p < 0.05 |
| **R-C** | climatology | the same two requirements |

**Partial results:** if only one of the two requirements holds against a baseline, the result is "suggestive, not established", and the lead is **not** reliable.

**Minimum quarter wins** for p < 0.05, with no ties:

| Lead | Quarters | Wins needed |
|---|---|---|
| 1 | 12 | ≥ 10 of 12 |
| 2 | 10 | ≥ 9 of 10 |
| 3 | 9 | ≥ 8 of 9 |

This limit is stated with each result.

**Furthest reliable lead:**
- the largest h in {1, 2, 3, 4} at which the rule holds;
- the report also states whether the rule holds at every shorter lead;
- if no lead meets the rule, the answer is **"no lead meets the rule"**;
- lead 4 cannot meet the rule (section 1).

**Scope of the rule:**
- **Headline:** the rule applied to E56 P(HIGH) on each lead's full eligible set.
- **Reported, not headline:**
  - the rule applied to E58-EW (P_price);
  - the rule applied on the common-target set.
  - If either gives a different verdict, the report says so.
- Accuracy and the other metrics are **descriptive**. No accuracy threshold is part of the rule.
- No multiplicity correction across leads is applied. A correction could only make the rule stricter.

## 9. Not allowed

- retuning, a different model, changed labels, thresholds or search space;
- dropping or adding quarters after sealing, or imputing outcomes;
- data after 2026-10-14 or before 2021;
- writing into E56–E62 or `backend/data` (checked by the SHA-256 manifest in `runner/e63_guard.py`, before and after);
- serving changes or a production switch (E38 stays the default);
- commits or pushes without the user's approval;
- reading session transcripts.

## 10. Deliverables

- `PROTOCOL.md` and its hash;
- `sealed/predictions.csv` and its hash;
- `tables/lead_metrics.csv`, `tables/per_quarter.csv`, `tables/reliability_bins.csv` and `tables/paired_tests.csv`;
- `out/scores.json`;
- `FINAL_REPORT.md`, with the lead × metric table, the rule verdict per lead, the furthest reliable lead (or none), and a Chapter IV-ready paragraph answering SOP Q2 / Objective 2 V.
