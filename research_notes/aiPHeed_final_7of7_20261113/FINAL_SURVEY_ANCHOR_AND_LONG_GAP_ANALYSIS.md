# FINAL: survey anchors and long gaps

**Evidence** (all training-only or outcome-free unless marked "evaluation"):
- `../aiPHeed_final_standalone_20261113/evidence/D1_*`, `D3_*`
- `../aiPHeed_final_stability_lead_20261113/evidence/D4_*`, `D5_*`
- `evidence/C1_round_calibration_by_arm.csv` (evaluation, descriptive)

## Anchor construction (code)
- **H, OH and RSS all share the same national part** (`app/e160/arms.py`, `app/e163/model.py`): `last_n`, the national level of the **latest released** round, carried flat. To that each adds the province's deviation, differently:
  - **H:** hierarchical prediction;
  - **OH:** reliability-weighted own history;
  - **RSS:** Kalman state-space deviation whose variance grows with elapsed years.
- **Which anchor is chosen:** per fit, by inner out-of-fold error. OH in every 2018 and 2019 fit; RSS in every 2021 fit.
- **Refresh:** when a new round is released, the national part of every province's anchor jumps to the new level, including provinces that new round did not survey.

## Findings

| Question | Answer | Evidence |
|---|---|---|
| Double counting? | **Yes, only where the anchor is stale:** the province's own survey is older than the latest round (ENNS 2021 test rows at Leads 1–6). The anchor already moves those provinces about −12 points; RATE adds about −12 more from the own-survey gap (24 quarters) | D3, D4 |
| Constant per-quarter rate? | **No.** Training transitions give −0.011, −0.035, −0.016 and −0.019 logit per quarter for gaps of 8, 12, 16 and 20 | D1 |
| Elapsed time represented correctly? | **Ambiguous by construction.** RATE uses the own-survey gap g; the anchor's national part is s quarters old (s ≤ g). In every training row s = g, so training cannot tell which is right | D4 |
| Long gaps outside training support? | **Yes, in every fold:** test gap 12 vs 8; 16 vs 8; 24 vs at most 20. Live CALABARZON gaps are 22–34 vs at most 24. The sealed 2022 forecasts have gap 28 for 31 of 78 provinces | D4; `evidence/sealed_enns2022_final_mix.json` |
| Does the refresh cause discontinuities? | **Yes, by design.** Each released round shifts every anchor's national part, so a province's forecast can jump at a release without new provincial information | Code |
| Does uncertainty grow with survey age? | **No, in the evaluated folds.** The implied spread is 0.46 / 0.53 / 0.45 at gaps 12 / 16 / 24. The gap-variance regression is fitted on at most 20-quarter training gaps and flattens; RSS widens only the anchor's own variance, which the probability does not use | D5 |
| Are H / OH / RSS defensible? | **As anchors, yes:** each is a standard shrinkage estimator using released rounds only. **The defect is the interaction with RATE when s < g, not the anchors themselves** | Code, D3 |
| Rounds with different trends? | **Yes.** The national fall 2015→2018 (−10 points over 12 quarters) was much faster than 2013→2015 (−1.8 over 8). The 2018 fold sees only the slow period, so every variant over-predicts 2018 (mean p − rate +0.19) | D1; C1 (evaluation) |

## Why FINAL, FINAL-SA and FINAL-ET differ (evaluation, descriptive; `C1`)

| | 2018 mean p − rate | 2019 | 2021 | 2021 recall | Pooled Rule 6 | Rule 7c |
|---|---|---|---|---|---|---|
| FINAL (gap g) | +0.19 | −0.03 | **−0.01** | 1/4 | Pass | **Fail** |
| FINAL-SA (multiplier capped at the training gap) | +0.23 | +0.05 | +0.03 | 1/4 (2/4 with training threshold) | Fail | Pass (with threshold) |
| FINAL-ET (time since the latest round, s) | +0.19 | −0.03 | **+0.16** | 2/4 | **Fail** | Pass |

1. **Every variant over-predicts 2018 by about +0.2.** That uses most of the pooled ±0.10 calibration tolerance.
2. **FINAL passes calibration only because 2021 is under-forecast for its HIGH provinces.** Its mean is right, but the HIGH provinces are confidently low.
3. **Any change that lifts the 2021 HIGH provinces also lifts its LOW provinces.** Within-2021 AUROC is only 0.86–0.88, so 2021 over-predicts and pooled calibration fails.

The conflict is therefore **a round-specific national trend (2018) plus weak within-round ranking (2021)**, not the elapsed-time formula alone.

## Treatments examined

| Treatment | Justified without the evaluation outcomes? | Result |
|---|---|---|
| Cap at the training gap (FINAL-SA) | Partly: no extrapolation beyond support. But it also cuts the consistent s = g case in 2018 and 2019 | Fails Rule 6 |
| Time since the latest round (FINAL-ET) | Yes: matches the anchor construction | Fails Rule 6 (2021 over-predicts) |
| **Equal mixture of g and s (FINAL-ETMIX)** | **Yes: equal-prior averaging because training cannot identify the right elapsed time; it widens uncertainty exactly where they disagree** | Retrospective 7/7 at Lead 1, **inadmissible**: designed knowing both components' behaviour on these rows. Sealed for ENNS 2022 |
| Learned damping or weights | **No:** not identifiable from training (no stale-anchor training rows) | Not run |
| Uncertainty growing with anchor age | Desirable; cannot be estimated beyond the 20-quarter training support | Partly provided by the mixture |
| Trend information at the origin (SWS regional hunger) | Tested 11-11 on these rows: no gain | Not repeated |

## What resolves it
- **Training rows that contain stale anchors.** A future provincial round surveying provinces whose own survey is older than the latest national round (the 2022 seal has 53 such provinces) lets the elapsed-time weight be learned, not assumed.
- **A period-trend signal available at the origin** that predicts round-to-round national change. None has been verified so far.
