# 06 — HIGH-risk detection and false-negative analysis (deliverable 7)

Script: `scripts/false_negatives.py`. Evidence: `evidence/FN_high_rows_L1to5.csv`, `FN_by_round_lead.csv`, `GT_se2021_sensitivity.csv`.

**Method:** every forecast is decomposed exactly, using the stored fits (5 seeds, TreeSHAP) and no refit:

> forecast logit = survey anchor + factor contributions + elapsed-time term (RATE intercept × gap)

## 1. The five Lead-1 misses

| Round | Province | Observed % | Label z vs 50 % | Last survey % | Forecast % | Predicted change | Observed change | Gap (q) | p(HIGH) | Persistence p | Time term (logit) | Classified cause |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2019 | Lanao del Norte | 59.0 | 3.7 | 55.6 | 43.7 | −11.9 | +3.4 | 16 | 0.32 | 0.69 | −0.25 | **Feature insufficiency:** Marawi displacement (~139,700 people) has no input. Regional GRDP pulls the forecast down (−0.29 logit) because Northern Mindanao is richer than average |
| 2019 | Misamis Oriental | 54.8 | 1.9 | 54.1 | 46.1 | −8.0 | +0.7 | 16 | 0.38 | 0.64 | −0.25 | **Feature resolution:** the regional GRDP input (−0.30) cannot see within-region differences. **Label uncertainty:** z = 1.9 is borderline |
| 2021 | Agusan del Sur | 57.9 | 2.6 | 64.7 | 47.5 | −17.2 | −6.8 | 24 | 0.41 | 0.87 | −0.48 | **Model behaviour:** the elapsed-time term is extrapolated beyond its training support |
| 2021 | Masbate | 59.4 | 3.1 | 68.3 | 38.4 | −29.9 | −8.9 | 24 | 0.15 | 0.93 | −0.48 | **Model behaviour:** same cause |
| 2021 | Occidental Mindoro | 56.3 | 2.1 | 66.7 | 40.8 | −25.9 | −10.4 | 24 | 0.21 | 0.91 | −0.48 | **Model behaviour:** same cause |

## 2. Answers to the brief's questions

| Question | Finding | Evidence |
|---|---|---|
| Why only 1 of 4 HIGH found in 2021? | The forecast change is dominated by the elapsed-time term, which scales with the gap since the province's own survey. In 2021 that gap was 24 quarters, longer than every training gap (8–20). The term reached −0.48 logit, against −0.19 in 2018 and −0.25 in 2019. The model predicted an average fall of 18.8 points; the actual fall was 12.9. The three missed provinces were predicted to fall 17–30 points but fell only 7–10. The anchor is also counted twice: it is refreshed to the latest round while RATE multiplies by the own-survey gap (11-13 stability study) | `FN_by_round_lead.csv`; `aiPHeed_final_stability_lead_20261113/FINAL_STABILITY_ROOT_CAUSE.md` |
| Why did persistence find all 4? | Persistence predicts no change. All four provinces were above 64 % in 2015 and still above 56 % in 2021. Because the fall was smaller than the 2015 margin, "no change" was right. Persistence pays for it with 26 false alarms in 72 forecasts (precision 0.48) | `REL_vs_baselines.csv` |
| Does FINAL systematically underestimate HIGH probabilities? | **Only in 2021.** Mean p for HIGH rows: 2018 0.86, 2019 0.66, **2021 0.41**. Over all rounds, calibration-in-the-large over-forecasts slightly (+0.046) | `FN_by_round_lead.csv`; reliability report 03 |
| Does training represent long gaps? | **No.** Every test gap lies outside the training gaps: 2018 is 12 vs 8; 2019 is 16 vs 8; 2021 is 24 vs ≤ 20. The design cannot avoid this: training rows come from earlier rounds, which had shorter gaps | `FN_by_round_lead.csv` (`test_gap_outside_training` = True everywhere) |
| Do predictors capture worsening conditions? | **Weakly.** In 2021 the factor contributions to the misses are below 0.1 logit, against a time term of −0.48. Short-term inputs (prices, harvest, weather, news) cannot offset the structural time trend | `FN_high_rows_L1to5.csv` |
| Do structural indicators dominate? | **In 2018–2019, yes:** regional GRDP is ±0.16 to 0.30 logit per row and is the largest factor. **In 2021, no:** the 2021 fits did not select GRDP or poverty. The elapsed-time term dominates instead | same |
| Class imbalance? | **Not the cause.** The 2021 training set was 52 % HIGH, and balanced class weights are applied. The training/test difference that matters is the gap, not the class mix | `REL_rows_L1to5.csv` (CLIM) |
| Survey-round composition? | **Yes, for stability.** Dropping one training round changes 2021 HIGH recall from 1/4 to 3/4, with up to 8 classification changes | `aiPHeed_final_reliability_20261113/05` §4 |
| Target uncertainty? | **Not for the 2021 misses.** The published 2018/2019 provincial SEs (1.3–4.5 points) cover the plausible range. At any SE up to 4.5, none of the four 2021 HIGH labels is within 1.96 SE of 50 %. Misamis Oriental 2019 (z = 1.9) is the one borderline label | `GT_se2021_sensitivity.csv` |
| Is the threshold appropriate? | **Lowering it does not fix 2021 without false alarms.** The missed p values are 0.15–0.41: a cut-off of 0.40 finds Agusan del Sur only, and 0.30 adds 10 false alarms pooled. The 0.50 line is the HFIAS majority definition of HIGH, not a tuned value. **It stays** | `aiPHeed_final_reliability_20261113/evidence/REL_threshold_sensitivity.csv` |

## 3. Root-cause classification

| Cause | Misses | Fixable with current public data? |
|---|---|---|
| Model behaviour: extrapolating the elapsed-time term beyond training gaps | 3 (all of 2021) | **Partly.** The candidate corrections (ET, SA, ETMIX; report 07) change which provinces are caught but do not clearly improve the thesis metrics. Choosing one now would mean selecting on the same 72 outcomes |
| Feature insufficiency: unmeasured displacement shock | 1 (Lanao del Norte 2019) | **Possibly.** DROMIC displacement data exist from 2014. Adding it is a new model input, which needs a new protocol and a prospective test |
| Feature resolution: regional input applied to provinces | 1 (Misamis Oriental 2019, together with label uncertainty) | **No.** There is no provincial GRDP before 2018 |
| Threshold | 0 | — |
| Class imbalance | 0 | — |

**Operational mitigation, adopted as display only, not as a model change:** forecasts where the own-survey gap is longer than the longest training gap already carry the `low_confidence` flag in the dashboard rows. Laguna, Quezon and Rizal are flagged at the current issue.
