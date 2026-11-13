# FINAL: maximum reliable forecast lead

## Method
- **Design:** walk-forward expanding window; locked lead rule (`../aiPHeed_final_stability_lead_20261113/FINAL_IMPROVEMENT_PROTOCOL.md` section 3).
- **What is refitted inside each fold:** origin = target − lead; training contains only outcomes released by the origin; inputs are as of the origin. Preprocessing, input selection, anchor and feature-set choice, hyperparameters, calibration and threshold are all fitted in the fold. Five seeds.
- **Code and evidence:** `scripts/lead_eval_mix.py` writes `evidence/LEAD_results.json`, `LEAD_summary_table.csv` and `LEAD_province_by_lead.csv`. Baselines: `../aiPHeed_final_stability_lead_20261113/evidence/LEAD_baselines_paired.csv`.
- **Leads the genuine data support:**
  - Leads 1–6: 72 province-rounds, 72 provinces, 25 HIGH / 47 LOW.
  - Leads 7–8: 50 province-rounds, 17 HIGH / 33 LOW (2018 has no fold beyond Lead 6).
  - Nothing beyond Lead 8.

## Lead versus survey-anchor gap (kept separate)

| Quantity | Definition | Values in the evaluation |
|---|---|---|
| Forecast lead | Origin → target quarter | 1–8 |
| Own-survey gap | The province's latest survey → target | 12 (2018), 16 (2019), 24 (2021), whatever the lead; confounded with the round |
| Anchor information age | Latest released round → target | Equals the gap except 2021 Leads 1–2 (8) and 3–6 (12) |
| Survey age at the origin (latest released anchor → origin) | Anchor age minus lead | 2018: 11 → 6 quarters; 2019: 15 → 8; 2021: 7 (L1) → 16 (L8) |

Longer leads have **older information at the origin and smaller training sets**. In 2021, Leads 7–8 train only on the 2015 transition. Lead effects therefore mix "further ahead" with "less training evidence".

## FINAL (fixed before these rows were scored at Leads 4–8)

| Lead | n | Accuracy [CI] | BA [CI] | AUROC | Precision | HIGH recall [CI] | LOW recall | F1 | Brier | TP/FP/FN/TN | Cox p | Mean p − rate | 2018/2019/2021 recall | Reliable |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 72 | 0.861 [0.78, 0.93] | 0.847 [0.76, 0.93] | 0.898 | 0.80 | 0.80 [0.64, 0.95] | 0.89 | 0.80 | 0.123 | 20/5/5/42 | 0.41 | +0.05 | 1.00/0.85/**0.25** | No (7c) |
| 2 | 72 | 0.847 | 0.836 [0.73, 0.92] | 0.899 | 0.77 | 0.80 | 0.87 | 0.78 | 0.123 | 20/6/5/41 | 0.57 | +0.04 | 1.00/0.85/**0.25** | No (7c) |
| 3 | 72 | 0.819 | 0.805 [0.70, 0.90] | 0.883 | 0.73 | **0.76** | 0.85 | 0.75 | 0.133 | 19/7/6/40 | 0.52 | +0.04 | 0.88/0.77/0.50 | No (4) |
| 4 | 72 | 0.819 | 0.815 [0.71, 0.91] | 0.885 | 0.71 | 0.80 | 0.83 | 0.76 | 0.135 | 20/8/5/39 | 0.32 | +0.05 | 1.00/0.85/**0.25** | No (7c) |
| 5 | 72 | 0.792 | 0.784 [0.68, 0.88] | 0.874 | 0.68 | **0.76** | 0.81 | 0.72 | 0.138 | 19/9/6/38 | 0.47 | +0.05 | 1.00/0.77/**0.25** | No (4, 7c) |
| 6 | 72 | 0.750 | 0.734 [0.62, 0.84] | 0.866 | 0.63 | **0.68** | 0.79 | 0.65 | 0.146 | 17/10/8/37 | 0.54 | +0.04 | 0.88/0.69/**0.25** | No (4, 7c) |
| 7 | 50 | 0.700 | 0.701 [0.56, 0.84] | 0.815 | **0.55** | **0.71** | 0.70 | 0.62 | 0.180 | 12/10/5/23 | 0.13 | **+0.11** | —/0.62/1.00 | No (4, 5, 6) |
| 8 | 50 | 0.740 | 0.760 [0.63, 0.87] | 0.818 | **0.58** | 0.82 | 0.70 | 0.68 | 0.175 | 14/10/3/23 | 0.13 | **+0.11** | —/0.77/1.00 | No (5, 6) |

**Maximum reliable lead for FINAL: none established.** It fails at Lead 1 on 7c. Performance deteriorates with lead: balanced accuracy 0.85 → 0.73 and HIGH recall 0.80 → 0.68 from Lead 1 to Lead 6.

## FINAL-ETMIX (retrospective; inadmissible, see the seven-rule report)

| Lead | Accuracy | BA [CI] | AUROC | Precision | HIGH recall [CI] | LOW recall | F1 | Brier | TP/FP/FN/TN | Cox p | Mean p − rate | 2021 recall | Passes locked criteria |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 0.861 | 0.856 [0.77, 0.94] | 0.903 | 0.78 | 0.84 [0.68, 0.96] | 0.87 | 0.81 | 0.127 | 21/6/4/41 | 0.10 | +0.07 | 0.50 | Yes (retrospective) |
| 2 | 0.833 | 0.826 [0.72, 0.92] | 0.907 | 0.74 | 0.80 | 0.85 | 0.77 | 0.123 | 20/7/5/40 | 0.14 | +0.07 | **0.25** | No (7c) |
| 3 | 0.819 | 0.805 | 0.895 | 0.73 | **0.76** | 0.85 | 0.75 | 0.129 | 19/7/6/40 | 0.47 | +0.05 | 0.50 | No (4) |
| 4 | 0.833 | 0.835 | 0.898 | 0.72 | 0.84 | 0.83 | 0.78 | 0.129 | 21/8/4/39 | 0.30 | +0.07 | 0.50 | Yes (isolated) |
| 5–8 | as FINAL ± 0.01 | 0.784 / 0.734 / 0.701 / 0.760 | | | 0.76 / 0.68 / 0.71 / 0.82 | | | | | | | | No |

**Retrospective maximum lead for FINAL-ETMIX: 1** (Lead 2 fails 7c: Agusan del Sur at 0.46). **Inadmissible**: the candidate was designed with knowledge of its components' results on these rows.

## Baselines (FINAL, same rows; paired Brier)
FINAL has a lower Brier score than persistence (latest survey), GNT, PSA-only, logistic regression, LR + news and news-only at every lead: 48 of 48 comparisons, 43 significant.
- **Persistence:** balanced accuracy 0.70, recall 0.96, **precision 0.48**, Brier 0.25.
- **Climatology and always-LOW:** balanced accuracy 0.50.

Beating the baselines is reported for Objective 4. It is **not** the acceptance rule.

## Decision

| | Maximum reliable lead |
|---|---|
| Admissible evidence (FINAL, or any model fixed before scoring) | **No reliable lead is established** |
| Inadmissible retrospective (FINAL-ETMIX) | Lead 1 |
| Prospective (to be established) | Leads 1–2 via the sealed ENNS 2022 forecasts (sha `71ebe142`) |

**Evidence that would establish Leads 3 and beyond:** forecasts sealed at those origins for a future round. The pooled HIGH count would also have to reach about 35 or more at each lead, so that the per-round recall floor (≥ 0.50 with ≥ 5 HIGH per round) is not decided by one province.
