# Locked protocol: final H_cw optimisation — three diagnosed weaknesses, one composed candidate

Written 2026-11-12, before any arm below was run on either evaluation set. Hash in `PROTOCOL_FINAL.sha256`.

## What was looked at before writing this (disclosed)

Diagnostics on the existing H_cw forecasts (forward folds, Lead 1), run today:

1. **Information ceiling.** A model fitted inside each test round (leave-one-province-out, so it knows that round's level and relationships) gets 59 of 72 right with H_cw's inputs; anchor only gets 53. H_cw gets 59. Better learning on the same inputs has little room.
2. **H_cw does predict provincial change** (correlation of predicted with actual change inside a round: 0.68, 0.54, 0.62), **but too little of it in the 2018 and 2019 folds**: mean predicted change −0.19 and −0.12 logit against actual −0.42 and −0.25; spread of predicted change 0.25 and 0.19 against 0.41 and 0.49. In those folds every training row spans 8 quarters (2013 → 2015) and every test row spans 12 or 16 quarters (2015 → 2018 / 2019). A tree cannot extrapolate over an input that is constant in training.
3. **Missing values.** Provincial retail-price inputs are missing for 17–45 % of provinces; LightGBM's default gives "missing" its own branch.
4. **Unused survey information.** The anchor survey publishes four HFIAS categories per province (secure, mild, moderate, severe). H_cw uses only moderate + severe.
5. Already closed, not re-tested: synthetic rows (4 studies, 30+ arms), H_cw + E196 combination, WATCH band, annual child-nutrition records (OPT Plus; change correlation with HFIAS 0.03 in the 11-04 study), income pass-through (regional growth is too small to explain the level change: about 0.05–0.10 logit against 0.25–0.42).

Items 1–2 used forward test outcomes. So forward results for the arms below are **not** an untouched test of the idea in item 2; the held-out round is.

## Axes and arms

Each axis addresses one diagnosed weakness. Everything not named is H_cw unchanged (inputs, 25-input selection, grid, anchors, class weights, raw-first calibration, threshold 0.5, seeds 168/1/2/3/4, no synthetic rows).

**Axis T — target formulation (weakness 2).**

| Arm | Definition |
|---|---|
| RATE | LightGBM learns change **per quarter** since the anchor survey: target (y − anchor) / g, row weight × g², forecast = anchor + g × predicted rate, with g = quarters since anchor ÷ mean training value. When all training rows span the same interval the fit is identical to H_cw and only the forecast is scaled by the interval ratio. |
| RATE_SQRT | Same with g = square root of the interval ratio (diffusion-type scaling). |

**Axis M — missing values (weakness 3).**

| Arm | Definition |
|---|---|
| IMPUTE | training-median fill (study I) |
| RIMP | hierarchical fill: provincial food and rice price change ← the region's published series; any other gap ← mean of the same input over provinces of the same region and origin quarter; remaining gaps ← training median |
| MIND | median fill **plus** a 0/1 "was missing" input per gappy input. Mechanism check: if missingness-as-signal is what hurts, MIND should lose IMPUTE's gain |
| DROPGAP | inputs missing in more than 15 % of training rows are removed; native handling for the rest |

**Axis C — new survey information (weakness 4).**

| Arm | Definition |
|---|---|
| COMP | adds four inputs from the anchor survey's published categories: logit severe share, logit mild share, probit(moderate + severe) − probit(severe), probit(any insecurity) − probit(moderate + severe). As-of by construction (same publication as the anchor). No monotone constraint. |

## Two evaluation sets, two different roles

- **Held-out round (development / selection).** FNRI 2015 as test (78 provinces, Leads 1–2), trained on ENNS 2018, 2019, 2021. Leave-one-round-out, not a forecast; its accuracy is never quoted as forecast accuracy. For RATE it is a mirror test: training intervals 12–24 quarters, test interval 8.
- **Forward chronological folds (confirmation).** Rolling origin, test rounds ENNS 2018, 2019, 2021, 72 province-rounds per lead, Leads 1–3, Lead 1 primary. The only forecasting evidence.

## Procedure

**Stage 1, held-out round.** Run BASE and the seven single arms. On each axis, take the arm with the lowest pooled (Leads 1–2) Brier score against the survey probability, **if** it is lower than BASE and its Lead 1 accuracy is not lower than BASE; otherwise the axis stays at H_cw. Ties: the simpler arm (RATE over RATE_SQRT; IMPUTE over RIMP over DROPGAP over MIND).

**Stage 2, composition.** FINAL = the stage-1 choices combined. If no axis is chosen, FINAL = H_cw and the study ends with "no improvement". FINAL is run on the held-out round (reported) and on the forward folds.

**Stage 3, forward confirmation of FINAL only**, against H_cw (rules of study I):

1. Mean fold accuracy no more than 1.4 points below H_cw at every lead.
2. Brier score lower than H_cw at ≥ 2 of 3 leads.
3. Pooled paired Brier difference (Leads 1–3): 95 % province-round bootstrap interval entirely below 0.
4. HIGH recall and LOW recall no more than 0.04 below H_cw at any lead.
5. Worst-seed mean fold accuracy no more than 1.4 points below H_cw's.
6. Balanced accuracy at Lead 1 not below H_cw.
7. No test round at Lead 1 more than one province worse than H_cw.

Because FINAL is one configuration chosen on other rows, the 95 % level applies. All single arms are also run forward and reported, for transparency only; none of them can be selected from forward results.

**Verdicts.**
- *Validated improvement*: FINAL passes rules 1–7 forward **and** is better than BASE on the held-out round (pooled Brier interval below 0).
- *Supported improvement*: FINAL is better on both sets in point terms, with no rule-4/6/7 damage, but an interval includes 0.
- *No improvement*: otherwise. H_cw stays.

**Accuracy target.** About 85 % at Lead 1 is the owner's aspiration. It is reported, not used as a pass rule, and nothing is tuned to reach it.

## Safeguards

- No test outcome enters training, selection, imputation values, or input construction. RIMP region means use inputs only.
- Synthetic rows: none.
- Production (E196), the dashboard and the `aipheed_hcw` branch are not modified. Implementation of a passing candidate is added as an opt-in research module only; serving it needs owner approval.
- Stated limits that no arm can remove: every outcome is a third-quarter measurement; CALABARZON has 5 forward test rows, all LOW; four survey rounds in total.
