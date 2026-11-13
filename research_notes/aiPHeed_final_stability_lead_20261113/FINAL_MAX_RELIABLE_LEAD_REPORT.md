# FINAL: maximum reliable forecast lead (walk-forward, expanding window)

**Protocol:** `FINAL_IMPROVEMENT_PROTOCOL.md` section 3 (sha `c5e76bd5`), locked before any Lead 4–8 FINAL result was scored. Acceptance rules are PROTOCOL_SA (sha `15202d27`), unchanged.

**Data:** 110 FINAL fits (22 fold-leads × 5 seeds) plus FINAL-ET. Script `scripts/lead_eval.py`; evidence in `evidence/LEAD_*`.

**Evidence class:** retrospective. The 72 province-rounds were reused in earlier development; Leads 4–8 of FINAL had never been scored before.

## Answer

**No reliable forecast lead is established, for FINAL or for FINAL-ET.**
- **FINAL** fails at Lead 1 on stability: the 2021 round finds 1 of 4 HIGH provinces.
- **FINAL-ET** fails at Lead 1 on calibration.

FINAL-ET passes every criterion at Leads 4 and 5. The locked rule requires every lead from 1 up to pass, so isolated passes at longer leads are **not** a reliable horizon.

## Design (as run)

**What a fold is.**
- Each fold is one ENNS round: the target is its reference quarter (2018-Q3, 2019-Q3, 2021-Q3).
- For lead L, the origin is the target minus L quarters.
- Training contains only outcomes released (reference + 6 quarters) by the origin; every input is as of the origin.
- Preprocessing, the 25-input selection, anchor and feature-set choice, hyperparameters, calibration and threshold are all refitted inside the fold. Five seeds are averaged.
- The same future outcome never trains an earlier forecast (release rule; `R1_R2_integrity.json`).

**Which leads the data support.** 2018: Leads 1–6; 2019: Leads 1–8; 2021: Leads 1–8. So:
- Leads 1–6: 72 province-rounds from 3 rounds, 72 distinct provinces, 25 HIGH / 47 LOW.
- Leads 7–8: 50 province-rounds from 2 rounds, 17 HIGH / 33 LOW.

Beyond Lead 8 there is no cached fold, and training would contain only the 2013→2015 transition.

**Survey-anchor gap versus lead.**
- The gap (own survey → target) is fixed by the round: 12, 16 and 24 quarters, whatever the lead.
- What changes with lead is the **training set**:
  - 2021 Leads 1–2 train on 2015, 2018 and 2019 outcomes (532 rows; gaps 8–20);
  - 2021 Leads 3–6 train on 2015 and 2018 (332 rows);
  - 2021 Leads 7–8 train on 2015 only (156 rows; gap 8).
- The gap effect cannot be separated from the round effect: each round has one gap.
- The anchor-staleness effect (gap ≠ time since the latest round) exists only in 2021 Leads 1–6; it is the subject of FINAL-ET.

## Results by lead: FINAL (5-seed mean; 95 % interval on balanced accuracy)

| Lead | n (H/L) | Rounds | BA [95 % CI] | AUROC | Precision | Recall | F1 | Brier | TP/FP/FN/TN | Cox p | Mean p − rate | Worst-seed BA | Recall 2018/2019/2021 | Failed | Reliable |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 72 (25/47) | 3 | 0.847 [0.76, 0.93] | 0.898 | 0.80 | 0.80 | 0.80 | 0.123 | 20/5/5/42 | 0.41 | +0.05 | 0.83 | 1.00/0.85/**0.25** | 7c | No |
| 2 | 72 | 3 | 0.836 [0.73, 0.92] | 0.899 | 0.77 | 0.80 | 0.78 | 0.123 | 20/6/5/41 | 0.57 | +0.04 | 0.83 | 1.00/0.85/**0.25** | 7c | No |
| 3 | 72 | 3 | 0.806 [0.70, 0.90] | 0.883 | 0.73 | **0.76** | 0.75 | 0.133 | 19/7/6/40 | 0.52 | +0.04 | 0.78 | 0.88/0.77/0.50 | 4 | No |
| 4 | 72 | 3 | 0.815 [0.71, 0.91] | 0.885 | 0.71 | 0.80 | 0.75 | 0.135 | 20/8/5/39 | 0.32 | +0.05 | 0.81 | 1.00/0.85/**0.25** | 7c | No |
| 5 | 72 | 3 | 0.784 [0.68, 0.88] | 0.874 | 0.68 | **0.76** | 0.72 | 0.138 | 19/9/6/38 | 0.47 | +0.04 | 0.74 | 1.00/0.77/**0.25** | 4, 7c | No |
| 6 | 72 | 3 | 0.734 [0.62, 0.84] | 0.866 | 0.63 | **0.68** | 0.65 | 0.146 | 17/10/8/37 | 0.54 | +0.04 | 0.73 | 0.88/0.69/**0.25** | 4, 7c | No |
| 7 | 50 (17/33) | 2 | 0.701 [0.56, 0.84] | 0.815 | **0.55** | **0.71** | 0.62 | 0.180 | 12/10/5/23 | 0.13 | **+0.11** | 0.70 | —/0.62/1.00 | 4, 5, 6 | No |
| 8 | 50 | 2 | 0.760 [0.63, 0.87] | 0.818 | **0.58** | 0.82 | 0.68 | 0.175 | 14/10/3/23 | 0.13 | **+0.11** | 0.72 | —/0.77/1.00 | 5, 6 | No |

FINAL-ET is identical to FINAL at Leads 7–8 and in the 2018 and 2019 rows:

| Lead | BA | Precision | Recall | Cox p | Mean p − rate | 2021 recall | Failed |
|---|---|---|---|---|---|---|---|
| 1 | 0.824 | 0.70 | 0.84 | **0.031** | **+0.103** | 0.50 | 6 |
| 2 | 0.814 | 0.68 | 0.84 | **0.032** | **+0.103** | 0.50 | 6 |
| 3 | 0.806 | 0.73 | **0.76** | 0.28 | +0.06 | 0.50 | 4 |
| 4 | 0.835 | 0.72 | 0.84 | 0.16 | +0.08 | 0.50 | — (passes all) |
| 5 | 0.804 | 0.69 | 0.80 | 0.22 | +0.07 | 0.50 | — (passes all) |
| 6 | 0.754 | 0.64 | **0.72** | 0.35 | +0.06 | 0.50 | 4 |

Province-by-lead probabilities: `evidence/LEAD_province_by_lead.csv`.

## Does performance deteriorate with lead?

Yes, for FINAL over Leads 1–6, on the same 72 rows:

| Measure | Lead 1 → Lead 6 |
|---|---|
| Balanced accuracy | 0.85 → 0.73 |
| HIGH recall | 0.80 → 0.68 |
| Precision | 0.80 → 0.63 |
| Brier | 0.123 → 0.146 |

The decline comes mainly from the 2019 round (recall 0.85 → 0.69) and 2018 false alarms (3 → 6), as training shrinks with earlier origins. Calibration stays acceptable to Lead 6 (Cox p ≥ 0.32).

At Leads 7–8 (2019 and 2021 only, trained on 2015 alone), 2021 flips to recall 1.00 with 8 false alarms. Precision falls below 0.60 and probabilities run 0.11 too high.

## Baselines (same rows; paired Brier, 95 % interval; `evidence/LEAD_baselines_paired.csv`)

| Lead | Persistence (latest survey): BA / Brier | FINAL Brier − baseline | Others (GNT, PSA-only, LR, LR + news, news-only) | Climatology / always-LOW BA |
|---|---|---|---|---|
| 1 | 0.70 / 0.253 (recall 0.96, precision 0.48) | −0.130 [−0.19, −0.06] | FINAL lower Brier against all 5; significant against all | 0.50 / 0.50 |
| 2–6 | 0.70 / 0.253 | −0.13 to −0.11, all significant | Significant except GNT at L2, LR at L4, news-only at L5–L6 (lower but not significant) | 0.50 |
| 7–8 | 0.71 / 0.251 | −0.07 / −0.08, significant | All significant | 0.50 |

FINAL is better than every required baseline at every lead on Brier, significantly in 43 of 48 comparisons. **Beating the baselines is not the acceptance rule.** The standalone rules fail on HIGH detection in the newest round, on recall at longer leads, and on calibration beyond Lead 6.

## Maximum reliable lead decision

| Model | Leads passing every criterion | First failure | Maximum reliable lead |
|---|---|---|---|
| FINAL | none | Lead 1: 7c (2021 recall 1 of 4) | **None established** |
| FINAL-ET | 4, 5 | Lead 1: Rule 6 (Cox p 0.031; mean p − rate +0.103) | **None established** |

The 2021 round, which decides 7c, has only 4 HIGH provinces. Training perturbation moves its recall between 0.25 and 1.00 (`R7_et_sensitivity.json`). **The data cannot support a firm multi-lead conclusion either way.**

## What would establish a reliable lead
1. **At least one more provincial HFIAS round**, forecast from sealed origins at Leads 1–8, with about 25 provinces and 10 HIGH:
   - Rule 7c (≥ 0.50 recall per round) then rests on ≥ 5 HIGH per round instead of 4;
   - pooled HIGH n reaches about 35 at Leads 1–6.
2. **A round whose provinces' own surveys are older than the latest national round**, as in 2021, inside the *training* data. Then how RATE should treat a stale anchor can be learned rather than assumed.
3. **About 600–1,000 forecasts in total** before the originally proposed calibration limits (ECE ≤ 0.05, slope 0.80–1.20) can be tested.
