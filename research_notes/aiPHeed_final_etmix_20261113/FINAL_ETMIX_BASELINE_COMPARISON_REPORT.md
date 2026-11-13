# FINAL-ETMIX versus the four required baselines (Objective 4)

## Common conditions
- **Rows:** the same 72 province-rounds at Leads 1–6 and 50 at Leads 7–8.
- **Target:** the same HFIAS moderate + severe ≥ 50 % definition.
- **Folds and origins:** the same walk-forward folds and forecast origins.
- **Cut-off:** 0.50 for every model.
- **Baselines:** fitted out-of-fold inside the same folds (`app/e151/prov.py`; stored in the E158 label table `aipheed_e145/backend/data/e158/out/oof.csv`).
- **Script:** `scripts/etmix_eval.py`.
- **Statistics:** paired Brier differences with 95 % row-bootstrap intervals; McNemar exact tests on correct/incorrect classifications; bootstrap intervals for the AUC difference.

| Baseline | What it is |
|---|---|
| Naive persistence | Latest provincial survey value carried forward, with its survey uncertainty (`PERS`) |
| PSA-only indicator | Logistic regression on PSA poverty / government indicators (`PSA`) |
| NLP-only sentiment | Logistic regression on the news (XLM-R / BERTopic / FSSI) features only (`LR_NEWS`) |
| Logistic regression | Logistic regression on all inputs plus the survey anchor (`LR`) |

## Lead 1 (the thesis horizon)

| Model | Accuracy | Precision | HIGH recall | F1 | AUC-ROC | Brier | TP/FP/FN/TN |
|---|---|---|---|---|---|---|---|
| **FINAL-ETMIX** | **0.861** | **0.778** | 0.840 | **0.808** | **0.903** | **0.127** | 21/6/4/41 |
| Naive persistence | 0.625 | 0.480 | **0.960** | 0.640 | 0.827 | 0.253 | 24/26/1/21 |
| PSA-only | 0.556 | 0.436 | 0.960 | 0.600 | 0.762 | 0.274 | 24/31/1/16 |
| NLP-only | 0.639 | 0.487 | 0.760 | 0.594 | 0.703 | 0.244 | 19/20/6/27 |
| Logistic regression | 0.611 | 0.467 | 0.840 | 0.600 | 0.803 | 0.320 | 21/24/4/23 |

| ETMIX vs | Brier difference [95 % CI] | AUC difference [95 % CI] | McNemar (ETMIX right & baseline wrong / reverse), p |
|---|---|---|---|
| Persistence | −0.126 [−0.183, −0.068] | +0.08 [−0.02, +0.18] | 21 / 4, p = 0.001 |
| PSA-only | −0.147 [−0.202, −0.092] | [+0.04, +0.26] | 26 / 4, p < 0.001 |
| NLP-only | −0.117 [−0.176, −0.060] | [+0.07, +0.34] | 21 / 5, p = 0.003 |
| Logistic regression | −0.194 [−0.283, −0.108] | [+0.00, +0.21] | 21 / 3, p < 0.001 |

## All leads (required baselines)

| Comparison over Leads 1–8 | Persistence | PSA-only | NLP-only | Logistic regression |
|---|---|---|---|---|
| Brier significantly better (CI < 0) | **8 / 8** | 8 / 8 | 8 / 8 | 8 / 8 |
| Accuracy significantly better (McNemar p < 0.05) | 5 / 8 (not Leads 6–8) | 8 / 8 | 6 / 8 (not 4, 7) | 7 / 8 (not 4) |
| AUC CI above 0 | **0 / 8** | 6 / 8 | 8 / 8 | 7 / 8 |
| ETMIX higher accuracy and precision | 8 / 8 | 8 / 8 | 8 / 8 | 8 / 8 |
| ETMIX higher F1 | 7 / 8 (not Lead 7: 0.615 vs 0.640) | 8 / 8 | 8 / 8 | 8 / 8 |
| ETMIX higher HIGH recall | **0 / 8** | 0 / 8 | 6 / 8 | 4 / 8 (ties at Leads 1, 2, 5; lower at 6) |

Source: `evidence/ETMIX_vs_baselines_by_lead.csv`.

## Reference comparisons (not required baselines)

| Model, Lead 1 | Accuracy | AUC | Brier | ETMIX Brier difference [CI] |
|---|---|---|---|---|
| FINAL (g only) | 0.861 | 0.898 | 0.123 | +0.004 [−0.006, +0.013]: **no difference** |
| E151 LightGBM residual | 0.722 | 0.855 | 0.164 | −0.037 [−0.075, −0.002] |
| Anchor + NLP LightGBM | 0.667 | 0.831 | 0.178 | −0.052 [−0.088, −0.016] |

## Answers
1. **Does FINAL-ETMIX outperform each baseline?**
   - On probability accuracy (Brier), yes, significantly, against all four at every lead.
   - On accuracy and precision, it is higher at every lead; on F1, at every lead except Lead 7 against persistence.
   - It does **not** beat persistence or PSA-only on HIGH recall. Those baselines flag nearly every province (persistence: 26 false alarms at Lead 1, precision 0.48).
   - Its ranking (AUC) is not significantly better than persistence's at any lead.
2. **Strongest baseline:** naive persistence (AUC 0.83, recall 0.96). It is a strong ranker, but it raises a false alarm for more than half of the LOW provinces.
3. **Does NLP add predictive value?**
   - No. The NLP-only baseline is the weakest at Leads 2–8 (AUC 0.42–0.68).
   - Inside ETMIX, withholding or permuting the news inputs changes no forecast class, and retraining without them changes nothing (`FINAL_ETMIX_CONTRIBUTOR_IMPORTANCE_REPORT.md`).
4. **Do economic, agricultural, climate or social indicators add information?** Regional economic accounts, food prices and agriculture/fish production do (contributor report). Climate and employment do not.
5. **Is ETMIX's complexity justified?**
   - Against the required baselines, yes: the gain in precision and Brier is large and significant.
   - Against FINAL, the elapsed-time mixture is **not** shown to be better on these rows (Brier +0.004, n.s.). It is a principled treatment of an ambiguity the training data cannot resolve, not a measured improvement.

**Caveat:** all of this is retrospective, on rows reused during development.
