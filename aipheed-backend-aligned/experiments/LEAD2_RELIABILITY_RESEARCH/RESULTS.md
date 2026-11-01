# Lead-2 reliability research: results

**Plan:** `EXPERIMENT_PLAN.md`, SHA-256 `0c64aebb…`, frozen 2026-10-29T09:51:29Z, before any run.
**Data:** `DATA_AUDIT.md`.

**Reproduce** (from `runner/`, in this order; each script checks the plan hash):

```
python -B x1_label_noise.py   # out/x1_label_noise.json
python -B x2_pre2021.py       # out/x2_results.json, out/x2_rows.csv
python -B x3_confirm.py       # out/x3_results.json, out/x3a_rows.csv, out/x3b_rows.csv
python -B x4_windows.py       # out/x4_windows.json (post hoc, descriptive)
python -B issue_manifest.py --issue YYYY-MM-DD   # Path 1 tool: run ON each issue day, beside the sealed forecasts
```

`issue_manifest.py` writes the SHA-256 of all 36 pipeline input files, the newest SWS round before the issue, the git
HEAD and the UTC write time. A demonstration run for 2026-10-01 correctly records `writtenBeforeIssueEnds: false`.
That is the timing gap this tool closes from 2027-01-01 on.

Logs are in `out/log_x*.txt`.

**Deviation, disclosed.** The first X3 run stopped on a NaN before any metric was computed. The served H4 term is
undefined at the 2022 origins, which have fewer than the minimum number of 2021+ errors. The fix scores H4 on the 15
rows where it exists and reports the count. Nothing else changed.

## Baselines reproduced first (X3 asserts these)

| Baseline | TP/FP/FN/TN | Check |
|---|---|---|
| P0H4 Lead 1 | 11/5/6/48 | exact |
| P0H4 Lead 2 | 6/4/11/44 | exact |
| FIRI v2 Lead 2 vs observed BL hunger | 11/0/1/5 | exact |

The served hunger term H4 was recomputed to 4.7e-7.

## X1: how much of the Lead-2 "error" is measurement noise

SWS area samples carry ±6 points (until 2023) or ±4 (from 2024), 95%. Label reliability is Φ(|H − 11.3| / SE):

| BL quarter | H | Label | P(observed label = true label) |
|---|---|---|---|
| 2022-Q4 | 11.3 | LOW | **0.50** |
| 2023-Q2 | 11.3 | LOW | **0.50** |
| 2022-Q2 | 11.8 | HIGH | 0.59 |
| 2021-Q3, 2023-Q3 | 10.3 | LOW | 0.63 |
| 2022-Q3 | 9.6 | LOW | 0.71 |
| 2023-Q4 (the onset) | 14.3 | HIGH | 0.85 |
| 2024-Q2 .. 2026-Q3 | 16–25 | HIGH | 0.96–1.00 |

Expected accuracy of a forecaster that knew the **true** prevalence exactly, scored against observed labels:

| Target set | Expected accuracy |
|---|---|
| 17 FIRI Lead-2 targets | **0.877** |
| 14 P0H4-period targets (hunger part) | **0.921** |

FIRI's observed 0.941 is above this ceiling, which is consistent with a favourable draw, not with demonstrated skill.
Almost all of the LOW class sits within sampling error of the threshold.

## X2: hunger forecasting on independent data (2005–2020, four SWS areas; no 2021+ outcome used)

248 area-quarters per lead (62 quarters × 4 areas), 205 HIGH / 43 LOW. True horizon at Lead 2 = 3 quarters (295 of 310
rows). Pooled fit, all areas:

| Lead 2 | Accuracy | Balanced | Precision | Recall | Specificity | AUC | Brier | MAE (pts) | Onsets |
|---|---|---|---|---|---|---|---|---|---|
| **RW** (persistence, H4 analogue) | **0.794** | **0.637** | 0.87 | 0.88 | 0.40 | **0.734** | **0.1508** | 4.91 | 17/19 |
| CLIM | 0.665 | 0.430 | 0.80 | 0.79 | 0.07 | 0.275 | 0.2424 | – | 16/19 |
| MR (pooled mean reversion) | 0.718 | 0.471 | 0.82 | 0.85 | 0.09 | 0.624 | 0.1762 | **4.74** | 16/19 |
| MRF (+ national food inflation) | 0.677 | 0.447 | 0.81 | 0.80 | 0.09 | 0.616 | 0.1776 | 4.78 | 17/19 |

MR minus RW Brier: +0.025, one-sided p = 0.99 (62 quarter clusters). MRF: +0.027.

**Balance Luzon only, Lead 2** (62 quarters, 49 HIGH):

| | Accuracy | Balanced | AUC | Brier | MAE |
|---|---|---|---|---|---|
| RW, pooled fit | 0.742 | 0.611 | 0.686 | 0.1838 | 5.11 |
| MR, pooled fit | 0.645 | 0.465 | 0.586 | 0.1979 | **4.36** |
| RW, **area-held-out** (fit on NCR, Visayas, Mindanao) | 0.742 | 0.611 | 0.686 | 0.1840 | 5.11 |
| MR, area-held-out | 0.661 | 0.503 | 0.589 | 0.1971 | 4.36 |

Lead 1 shows the same ordering (all areas: RW Brier 0.156 vs MR 0.165).

**Selection rule (frozen):** MR was chosen over MRF. **Gate failed** on both conditions:

- it did not beat RW on all areas (p = 0.99);
- it did not beat RW on BL area-held-out.

**Findings:**

1. Over 16 years and four areas, **nothing in this set beats persistence** for the hunger condition two quarters ahead.
2. **Persistence itself reaches only about 0.64 balanced accuracy** at Lead 2. That is the level P0H4 shows (0.635).
3. **The other three areas generalise to BL as well as BL's own pairs do.** The dynamics are comparable, but they add
   no skill.
4. Mean reversion lowers the error of the **continuous level** (MAE 4.36 vs 5.11 in BL) but **worsens the classification
   and the probabilities**. The level forecast improves around the mean, not at the 11.3 crossing.

## X3: one confirmation on 2021–2026 (the X2-selected MR, scored once)

**X3a: BL hunger condition, 17 Lead-2 targets 2022-Q3..2026-Q3 (12 HIGH / 5 LOW).**

| Forecast | Rows | Accuracy | Balanced | Precision | Recall | Specificity | AUC | Brier | TP/FP/FN/TN | Rules failed (FIRI protocol application) |
|---|---|---|---|---|---|---|---|---|---|---|
| MR (selected) | 17 | 0.706 | 0.500 | 0.71 | 1.00 | 0.00 | 0.817 | 0.160 | 12/5/0/0 | R1 R2 R3 R4 R5 R7 |
| RW (1998+ four-area σ) | 17 | 0.706 | 0.617 | 0.77 | 0.83 | 0.40 | 0.825 | 0.142 | 10/3/2/2 | R1 R2 R3 R4 R5 R7 |
| H4 (served hunger term) | 15 | 0.733 | 0.583 | 0.83 | 0.83 | 0.33 | 0.819 | 0.138 | 10/2/2/1 | R1 R2 R3 R4 R5 R7 |
| H1 (FIRI's hunger outlook) | 17 | 0.706 | 0.617 | 0.77 | 0.83 | 0.40 | 0.792 | 0.161 | 10/3/2/2 | R1 R2 R3 R4 R5 R7 |
| FIRI v2 | 17 | 0.941 | 0.958 | 1.00 | 0.92 | 1.00 | 0.933 | 0.189 | 11/0/1/5 | R1 R5 |

MR minus H4 Brier: −0.002, p = 0.50. Not a difference.

**X3b: P0H4 with the hunger term replaced by MR** (identical rows, T43c, threshold 0.50, R1–R7 as frozen):

| | Accuracy | Balanced | Precision | Recall | Specificity | F1 | AUC | Brier | TP/FP/FN/TN | Fails |
|---|---|---|---|---|---|---|---|---|---|---|
| Lead 1, MR × P0 | 0.800 | 0.688 | 0.62 | 0.47 | 0.91 | 0.533 | 0.853 | 0.144 | 8/5/9/48 | R3 R6 |
| Lead 1, **P0H4 (served)** | **0.843** | 0.776 | 0.69 | 0.65 | 0.91 | 0.667 | 0.867 | 0.132 | 11/5/6/48 | none |
| Lead 2, MR × P0 | 0.738 | 0.557 | 0.50 | 0.18 | 0.94 | 0.261 | 0.674 | 0.183 | 3/3/14/45 | R2 R3 R4 R5 R6 |
| Lead 2, **P0H4 (served)** | **0.769** | 0.635 | 0.60 | 0.35 | 0.92 | 0.444 | 0.625 | 0.194 | 6/4/11/44 | R3 R5 R6 |

**Not recommended:** worse at both leads, and Lead 1 would lose its pass.

## X4 (post hoc, descriptive): could any hunger-gated forecast pass R2 + R3 at Lead 2?

This takes every 13-quarter window of 2005–2020, the size of the P0H4 Lead-2 test, and scores the best hunger forecast
found (RW) at Lead 2:

| Area | Windows (two-class) | Balanced ≥ 0.70 | Accuracy ≥ 0.75 **and** balanced ≥ 0.70 | Median balanced |
|---|---|---|---|---|
| **BL** | 40 | **2.5%** | **0%** | 0.46 |
| Visayas | 34 | 0% | 0% | 0.46 |
| NCR | 18 | 22% | 22% | 0.62 |
| Mindanao | 19 | 42% | 32% | 0.62 |

With the information available at a Lead-2 issue (the newest SWS round is about 3 quarters before the target), BL
hunger exceedance **never** met R2 and R3 together in 16 years. P0H4 Lead 2 requires that hunger condition, so its
failure of R3 and R6 is **expected from the information set, not a model defect**. That explains why about 20 model
variants could not fix it.

## Answer to the reliability question

**No approach meets R1–R7 at Lead 2 without leakage.**

- **FIRI v2** passes R2–R4, R6 and R7 on 17 regional quarters. It fails R1 as written and R5. Its accuracy exceeds the
  label-noise ceiling and it was selected on those quarters.
- **Every hunger-term alternative** is at or below persistence on 16 years of independent data.

## Investigation C: ranked paths

| Rank | Path | Feasibility | Scientific value | Data needed | Risk to thesis validity |
|---|---|---|---|---|---|
| **1** | **Keep Lead 1 operational and Lead 2 experimental; strengthen prospective validation.** Seal each forecast on its issue day with a manifest of input files and hashes. Score every quarter. | High, now | High: the only route to independent evidence | Time (SWS rounds from Jan 2027) | None |
| **2** | **A hunger signal published earlier than SWS.** For example a monthly or sub-quarterly food-insecurity or hunger observation for Luzon or CALABARZON (DSWD, LGU or NNC monitoring), or SWS's own non-commissioned rounds where released early. | Low–medium (acquisition, verification of history and dates) | **Highest.** X2 and X4 show the limit is that the latest outcome is about 3 quarters old at a Lead-2 issue. Only fresher information can lift it. | At least 8 years of history with release dates | Low if pre-registered |
| 3 | **A continuous target** (BL hunger level). | Medium | Moderate. MR improves MAE but not the crossing. A level forecast does not answer "high risk or not" without a threshold, so the classification problem returns. | None new | **Medium:** it changes the research question unless framed as supplementary |
| 4 | **Comparable regions or finer frequency.** | **Done here** (X2: four areas, 16 years, area-held-out) | Confirmed the limit; no lift. Finer frequency is impossible: the outcome is quarterly, and monthly rows would duplicate it. | – | Inflated n if misused |

## Evidence required before declaring Lead 2 reliable

1. **Pass R1–R7 at Lead 2,** with Lead 1 still passing, on rows **not used in any selection**, that is, prospective
   sealed quarters.
2. **At least 10 prospective quarters (R1), including at least one hunger regime change.** Since 2021, BL has changed
   class once.
3. **A demonstrated hunger-crossing skill above persistence on independent history** (the X2 gate) for any new hunger
   input, before it is used.
4. **For a provincial claim, a provincial food-insecurity outcome with repeated observations,** such as CBMS food-shortage
   items or provincial FIES. None exists today (E13).


---

# Phase 2 (2026-10-29): systematic search for a Lead-2 method

**Plans.** These were frozen before each confirmatory step:

- `EXPERIMENT_PLAN_PHASE2.md` (`af18a7ab…`)
- `EXPERIMENT_PLAN_PHASE2_ADDENDUM_A.md` (`cdc4c6ed…`)
- `EXPERIMENT_PLAN_PHASE2_ADDENDUM_B.md` (`315f4342…`)
- `EXPERIMENT_PLAN_PHASE2_ADDENDUM_C.md` (`5b8f3be3…`)

**Search record:** `SEARCH_LOG.md`. **Data:** `DATA_AUDIT.md` sections 6–9.

**Reproduce** (each script checks its plan hash; run in this order):

```
python -B y0_audit/audit.py                      # Y0 audit
python -B y7_headroom/headroom.py                # Y7 oracle headroom
python -B y2_state_space/run_dev.py              # Y2 dev rows 2005-2020
python -B y3_leading_indicators/run_dev.py       # Y3 dev rows 2005-2020
python -B y3_leading_indicators/diagnose.py      # Y3 leading vs concurrent
python -B y5_confirm/gate_and_confirm.py         # gate, then official rows
python -B y4_stacking/stack.py                   # Y4 exploratory
python -B y8_price_condition/run_dev.py          # Y8 price condition, independent years
python -B y9_joint_independent/joint.py          # Y9 joint, independent years
python -B y10_world_prices/run_dev.py            # Y10 world prices
python -B y11_world_continuous/run_dev.py        # Y11 continuous world-price model
python -B y1_label_sensitivity/sensitivity.py    # Y1 label sensitivity
```

Each folder has `out/` with JSON results, row-level CSVs and logs.

## P2.1 Baseline reproduced and the seven rules, exactly (Y0)

**P0H4** on the 65 official Lead-2 rows (13 quarters × 5 provinces; 17 HIGH, prevalence 0.262). Confusion matrix TP/FP/FN/TN = 6/4/11/44.

| Rule | Lead 1 (70 rows) | Lead 2 (65 rows) |
|---|---|---|
| R1 ≥ 10 quarters and ≥ 40 rows | PASS: 14 q, 70 | PASS: 13 q, 65 |
| R2 accuracy ≥ 0.75 | PASS: 0.843 | PASS: 0.769 |
| R3 balanced accuracy ≥ 0.70 | PASS: 0.776 | **FAIL: 0.635** |
| R4 accuracy > always-LOW and > PERSIST-SI | PASS: 0.843 vs 0.757 / 0.743 | PASS: 0.769 vs 0.738 / 0.677 |
| R5 Brier < PERSIST-SI and < CLIM, one-sided quarter-cluster p < 0.10 | PASS: −0.125 (p 0.018); −0.069 (p 0.029) | **FAIL:** −0.129 (p 0.027); **−0.033 (p 0.146)** |
| R6 precision and recall ≥ 0.60 | PASS: 0.688 / 0.647 | **FAIL: 0.600 / 0.353** |
| R7 each third ≥ 0.60 and leave-one-quarter-out min ≥ 0.70 | PASS: thirds 0.88/0.76/0.90, LOQO 0.831 | PASS: thirds 0.72/0.70/0.90, LOQO 0.750 |

**FIRI v2** at Lead 2 (17 regional targets; 11/0/1/5):

| Rule | Result |
|---|---|
| R1 | **FAIL**: 17 rows |
| R2 | PASS: 0.941 |
| R3 | PASS: 0.958 |
| R4 | PASS: 0.941 vs 0.294 / 0.706 |
| R5 | **FAIL** vs H1: +0.027, p 0.73 |
| R6 | PASS: 1.00 / 0.92 |
| R7 | PASS: LOQO 0.938 |

**Audit verdict: no scoring bug.**

- An independent re-implementation (sklearn confusion matrix with explicit label order, its own bootstrap loop) gives the same seven verdicts as the frozen code and the stored `evaluation.json`.
- Probabilities are oriented correctly (AUC of p > AUC of 1 − p).
- There are no missing values and no probabilities at exactly 0.50. Target = origin + lead.
- P0H4 = π_H4 × P0_price (to within 8e-7). Labels = (BL H > 11.3) AND price.
- Every hunger input was published before its issue date. The 2025-07-01 issue correctly uses the 2025-Q2 round published 2025-06-27.
- PERSIST-SI and CLIM use only issue-time information.
- Two flags were benign:
  - the Brier score differs from the stored value by 5e-8, which is CSV rounding;
  - my own first timing check compared against the later 2025-Q2 round. It was corrected and rerun.

**Effective sample size.** The error indicator is correlated within quarters (intra-class correlation 0.24 at Lead 2), because the 5 provinces share the regional hunger term:

| | Design effect | Effective n | Accuracy 90% CI | Balanced accuracy 90% CI |
|---|---|---|---|---|
| Lead 2 | 1.97 | **≈ 33** of 65 | 0.65–0.88 | 0.50–0.78 |
| Lead 1 | 1.41 | 50 | – | – |

## P2.2 Where the Lead-2 limit sits (Y7 oracle headroom; diagnostic values, not forecasts)

| Lead 2, official rows | Accuracy | Balanced | P / R | Brier | Rules failed |
|---|---|---|---|---|---|
| Observed hunger × P0 | 0.677 | 0.648 | 0.42 / 0.59 | 0.181 | R2 R3 R4 R5 R6 R7 |
| Observed hunger × P4 | 0.738 | 0.709 | 0.50 / 0.65 | 0.174 | R2 R4 R5 R6 |
| Observed hunger × P6 (best of 10 price terms) | 0.785 | 0.740 | 0.58 / 0.65 | 0.170 | R5 R6 |
| Observed hunger × P1, P2, P3, P5, P7, P8, P0c | 0.52–0.71 | 0.47–0.70 | – | – | 4–6 rules each |
| Served π_H4 × observed price | 0.815 | 0.742 | 0.67 / 0.59 | 0.077 | R6 R7 |

**Even a perfect hunger forecast does not pass Lead 2 with any existing price term.** Both halves of T43c bind.

## P2.3 Hunger candidates on independent years (2005–2020, four SWS areas, Lead 2; the frozen gate)

Comparator: RW (persistence). Gate: G1 Brier lower with p < 0.10; G2 BL Brier lower (area-held-out); G3 BL balanced accuracy higher.

| Candidate | Scored rows | Brier (RW) | p (cand. not better) | BL Brier (RW), held-out | BL balanced (RW) | Gate |
|---|---|---|---|---|---|---|
| **Y2** Kalman latent AR(1) with SWS sampling error | 248 | 0.165 (0.151) | 0.91 | 0.187 (0.184) | 0.436 (0.611) | **fail** G1 G2 G3 |
| **Y3a** H3b replica (BL, rice + food CPI) | 62 | 0.212 (0.184) | 0.95 | 0.212 (0.184) | 0.406 (0.611) | **fail** G1 G2 G3 |
| **Y3b** pooled L2 logistic, 8 issue-time indicators | 248 | 0.192 (0.151) | 1.00 | 0.216 (0.184) | 0.426 (0.611) | **fail** G1 G2 G3 |
| **Y3c** ridge, continuous change + Gaussian | 248 | 0.188 (0.151) | 1.00 | 0.210 (0.184) | 0.465 (0.611) | **fail** G1 G2 G3 |

At Lead 1 the Kalman model has a slightly lower Brier than RW (0.151 vs 0.156, p 0.29), but a lower balanced accuracy. No candidate passed, so **no confirmatory candidate exists** (`y5_confirm/out/gate.json`).

**Do the indicators lead or merely co-move?** (`y3_leading_indicators/out/diagnose.json`; 316 pairs, 79 quarters, 1998–2020, horizon 3)

| Indicator | Leading r with hunger change [90% CI] | Concurrent r [90% CI] |
|---|---|---|
| Rice CPI YoY | −0.09 [−0.26, 0.11] | +0.01 [−0.11, 0.14] |
| Rice YoY, 3-month change | +0.02 [−0.14, 0.18] | −0.01 [−0.10, 0.07] |
| Food CPI YoY | +0.02 [−0.12, 0.17] | +0.10 [−0.01, 0.22] |
| ONI latest / 6-month max | −0.04 / −0.11 [−0.22, −0.01] | −0.08 / −0.05 |
| Typhoons, previous quarter | −0.01 | +0.04 |
| Palay YoY | +0.15 [0.08, 0.23] | 0.00 |
| Unemployment, YoY change | −0.08 [−0.19, 0.05] | **+0.32 [0.03, 0.51]** |

- **Onsets.** Of 100 LOW starting points, 40 onsets followed. Rice YoY at issue averaged **0.0%** before onsets and 2.3% before non-onsets.
- **Unemployment** co-moves with hunger (COVID 2020) but does not lead it.
- **Palay**'s weak positive sign has no plausible mechanism.

## P2.4 All candidates on the official rows (Y5; descriptive, because no gate was passed)

These replace π_H4 on the identical 65 Lead-2 and 70 Lead-1 rows, threshold 0.50, rules unchanged.

| Hunger × price | Lead 2: acc / bal / P / R / spec | F1 | AUC | Brier | TP/FP/FN/TN | Lead-2 fails | Lead-1 fails |
|---|---|---|---|---|---|---|---|
| **P0H4 (served, reference)** | 0.769 / 0.635 / 0.60 / 0.35 / 0.92 | 0.444 | 0.625 | 0.194 | 6/4/11/44 | R3 R5 R6 | none |
| P4H4 (reference) | 0.769 / 0.654 / 0.58 / 0.41 / 0.90 | 0.483 | 0.618 | 0.203 | 7/5/10/43 | R3 R5 R6 | none |
| KAL × P0 | 0.754 / 0.586 / 0.57 / 0.24 / 0.94 | 0.333 | 0.667 | 0.184 | 4/3/13/45 | R3 R5 R6 | R3 R6 |
| KAL × P4 | 0.631 / 0.541 / 0.32 / 0.35 / 0.73 | 0.333 | 0.620 | 0.213 | 6/13/11/35 | R2–R7 | R2 R4 R5 R6 R7 |
| H3B × P0 | 0.800 / 0.694 / 0.67 / 0.47 / 0.92 | 0.552 | 0.737 | 0.166 | 8/4/9/44 | R3 R6 | R3 R6 |
| **H3B × P4** | 0.800 / 0.751 / 0.61 / 0.65 / 0.85 | 0.629 | 0.714 | 0.187 | 11/7/6/41 | **R5 only** | R6 |
| LOG × P0 | 0.800 / 0.694 / 0.67 / 0.47 / 0.92 | 0.552 | 0.713 | 0.178 | 8/4/9/44 | R3 R5 R6 | R3 R5 R6 |
| LOG × P4 | 0.662 / 0.657 / 0.41 / 0.65 / 0.67 | 0.500 | 0.630 | 0.219 | 11/16/6/32 | R2–R7 | R2 R4 R5 R6 R7 |
| RDG × P0 | 0.800 / 0.656 / 0.75 / 0.35 / 0.96 | 0.480 | 0.702 | 0.177 | 6/2/11/46 | R3 R5 R6 | R5 R6 |
| RDG × P4 | 0.646 / 0.589 / 0.36 / 0.47 / 0.71 | 0.410 | 0.625 | 0.224 | 8/14/9/34 | R2–R7 | R2 R4 R5 R6 R7 |

**H3B × P4 is not a pass, and should not be adopted**, for four reasons:

1. It fails R5.
2. It fails R6 at Lead 1.
3. Its hunger term is **worse than persistence on 16 independent years** (Y3a).
4. Its classification passes depend on one label: 2023-Q2, BL hunger exactly 11.3 (P2.7).

## P2.4b Y4: stacking instead of the product (exploratory; fitted and scored on 2021–2026 only)

Logistic on [logit π_H4, logit π_P], refitted at every origin on earlier rows whose T43c label was published before the issue. It falls back to the product when there are too few rows.

| Variant | Fallback rows (L1 / L2) | Lead 1: acc / bal / R; fails | Lead 2: acc / bal / P / R | Lead-2 Brier | Lead-2 fails |
|---|---|---|---|---|---|
| P0, same lead | 25 / 30 | 0.786 / 0.679 / 0.47; R3 R6 | 0.723 / 0.490 / 0.00 / 0.00 | 0.231 | R2–R7 |
| P0, leads 1–3 pooled | 25 / 25 | 0.814 / 0.698 / 0.47; R3 R6 | 0.708 / 0.574 / 0.42 / 0.29 | 0.225 | R2–R7 |
| P4, same lead | 25 / 30 | 0.714 / 0.612 / 0.41; R2–R7 | 0.708 / 0.498 / 0.25 / 0.06 | 0.270 | R2–R7 |
| P4, leads 1–3 pooled | 25 / 25 | 0.757 / 0.620 / 0.35; R3–R7 | 0.646 / 0.570 / 0.35 / 0.41 | 0.256 | R2–R7 |

**Worse than the product at both leads.** The fit sees only 10–40 earlier rows, most from before the 2023-Q4 onset, when T43c was rare. It learns to say LOW. A fitted combination needs many more labelled quarters than exist.

## P2.5 The price condition on independent years (Y8, Y10, Y11; Region IV-A CPI; targets 2002-Q1..2020-Q4; 76 quarters; prevalence 0.50)

Lead-2 information: the target quarter is CPI months m0+5..m0+7. Gate: Brier lower than PERS-PROB with p < 0.10, and balanced accuracy no lower.

| Model | Acc | Bal | P / R | AUC | Brier | vs PERS-PROB: diff (p iid / p block-4) | Gate |
|---|---|---|---|---|---|---|---|
| PERS-BIN (newest 3 months, 0/1) | 0.658 | 0.658 | 0.69 / 0.58 | 0.658 | 0.342 | – | comparator |
| **PERS-PROB** (logistic on the persistence distances) | 0.605 | 0.605 | 0.62 / 0.55 | 0.683 | **0.235** | – | comparator |
| Y8 AR (ridge on F and G, Gaussian) | 0.605 | 0.605 | 0.61 / 0.61 | 0.557 | 0.295 | +0.060 (1.00 / 1.00) | fail |
| Y8 LOGX (L2 logistic, 11 domestic indicators) | 0.539 | 0.539 | 0.59 / 0.26 | 0.557 | 0.306 | +0.072 (1.00 / 0.99) | fail |
| Y10 LOGW (+ world rice, crude, urea changes) | 0.487 | 0.487 | 0.48 / 0.32 | 0.541 | 0.289 | +0.055 (1.00 / 0.98) | fail |
| Y10 LOGW2 (+ maize, wheat, palm) | 0.566 | 0.566 | 0.59 / 0.42 | 0.593 | 0.292 | +0.057 (0.98 / 0.89) | fail |
| Y11 WAR (OLS, top-3 world features chosen in-fold) | 0.539 | 0.539 | 0.55 / 0.42 | 0.617 | 0.275 | +0.040 (0.93 / 0.80) | fail |
| Y11 WAR0 (same, no world features; ablation) | 0.592 | 0.592 | 0.62 / 0.47 | 0.637 | 0.251 | +0.016 | – |

**The world features make the out-of-sample forecast worse:** WAR − WAR0 = +0.024, p = 0.99.

- Over the whole period, 6-month world price changes correlate with the coming change in food inflation: palm 0.46, wheat 0.42, crude 0.39.
- That relationship comes from the 2007–08 and 2010–11 commodity spikes. An expanding-window model cannot learn it before it happens.
- **This is a retrospective correlation, not a forecast.**

## P2.6 The joint target on independent years (Y9; post hoc, descriptive)

Regional analogue of T43c, 2005–2020: BL hunger > 11.3 AND the Region IV-A price condition. 62 quarters, prevalence 0.42.

| Forecast | Acc | Bal | P / R | AUC | Brier | 13-quarter windows passing R2 + R3 + R6 |
|---|---|---|---|---|---|---|
| RW hunger × PERS-PROB price (best validated on each side) | 0.677 | 0.647 | 0.67 / 0.46 | 0.698 | 0.219 | **0%** (49 windows); R4 never |
| Observed hunger × PERS-PROB | 0.694 | 0.683 | 0.64 / 0.62 | 0.801 | 0.178 | 10% |
| RW hunger × observed price | 0.887 | 0.887 | 0.85 / 0.88 | 0.949 | 0.083 | **90%** |
| PERSIST-SI analogue (0/1) | 0.726 | 0.710 | 0.70 / 0.62 | 0.710 | 0.274 | – |

When hunger stays HIGH, as in 2005–2020 and since 2023-Q4, **the binding constraint is the price condition 5–7 months ahead.** No validated method forecasts it better than persistence.

## P2.7 Label sensitivity (Y1)

Two analyses:

- **Flip test:** BL test quarters within 1 point of 11.3 (2023-Q2 = 11.3, 2023-Q3 = 10.3; FIRI also 2022-Q4 = 11.3) have their hunger label flipped.
- **Monte Carlo:** 2000 draws of the true level from N(observed, SE²).

| Forecast, Lead 2 | Observed verdict | Flip 2023-Q2 alone | MC pass rate R2 / R3 / R6 / R7 | MC: all classification rules pass |
|---|---|---|---|---|
| P0H4 | R2 pass; R3, R6 fail | R2 and R7 then fail | 0.38 / 0.00 / 0.00 / 0.41 | 0.00 |
| H3B × P4 | R2, R3, R6, R7 pass | **R2, R3, R6 fail** | 0.56 / 0.55 / 0.41 / 0.84 | 0.41 |
| FIRI v2 | R2, R3, R6, R7 pass | still pass | 0.93 / 0.98 / 1.00 / 0.44 | 0.44 |

With 13 Lead-2 quarters, two of them on the threshold, **a single sampling-error flip decides R2, R3 and R6.** No pass or fail on this test period is robust.

## P2.8 Answer

**No method passes all seven Lead-2 rules without leakage.** Phase 2 tested 4 hunger families, 5 price families and 1 combination family (4 variants), on independent 2002–2020 data wherever the data allow. **None beat persistence on independent years**, on either half of the target. The one configuration that comes close on the test period (H3B × P4) fails R5, breaks Lead 1, loses to persistence on 16 independent years, and depends on one borderline label.

**What improved over persistence, and where:**

| Model | Gain over persistence |
|---|---|
| Kalman (Y2), **Lead 1 only** | Brier 0.151 vs 0.156 on 2005–2020 (p 0.29, not significant), with lower balanced accuracy |
| Mean reversion (Phase 1 X2), continuous BL level | MAE 4.36 vs 5.11 |
| Candidates on the official rows (descriptive) | H3B × P0 (0.166), RDG × P0 (0.177), LOG × P0 (0.178) and KAL × P0 (0.184) all have lower Lead-2 Brier than served P0H4 (0.194). None is supported on independent years, and all fail R3 and R6. |

No model improved on persistence for the threshold crossing on independent data.

**The limit, stated exactly.** At a Lead-2 issue, aiPHeed knows:

- the newest SWS reading, 3 quarters before the target;
- CPI up to 5–7 months before the target months.

On 16–19 independent years, persistence of each is the best available forecast. It reaches balanced accuracy of about 0.61–0.66 for each half separately and about 0.65 for the joint target. The product of two such forecasts cannot reach balanced accuracy ≥ 0.70 together with recall ≥ 0.60 except by chance (0 of 49 windows).

To pass, the system needs **information that is not in any series now available to it**:

1. a hunger observation fresher than SWS at the issue date;
2. a real-time leading signal for provincial food inflation 5–7 months ahead.

**Strongest remaining hypothesis.** Domestic rice supply information leads CALABARZON food inflation 5–7 months ahead in real time, where world prices did not. Candidate sources:

- NFA and commercial rice stock inventories (PSA, monthly);
- rice import arrivals and licences (BPI/DA, monthly);
- farmgate palay prices (PSA, monthly).

Supply is the channel between world prices and domestic retail prices that Y10 and Y11 could not see.

**Exact data needed to test it:**

- monthly stocks, imports and farmgate prices from at least 2002, with publication dates;
- provincial food CPI under the 2012 base, 2012–2020, from PSA OpenSTAT, to validate at provincial level;
- the same Addendum-A gate against PERS-PROB.

On the hunger side, the hypothesis is a hunger reading fielded in month 1–2 of the issue quarter and published before the issue date. No such source exists; the only route would be commissioning one.
