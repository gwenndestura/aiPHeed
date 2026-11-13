# 03 — Metric comparison against all baselines

Script: `scripts/rel_eval.py`. Evidence: `evidence/REL_vs_baselines.csv`, `REL_summary_by_lead.csv`, `REL_reliability_L1.csv`.

## 1. Lead 1 (72 province-rounds, identical rows)

| Model | Accuracy | HIGH precision | HIGH recall | HIGH F1 | Macro F1 | Balanced accuracy | PR-AUC | ROC-AUC | Brier |
|---|---|---|---|---|---|---|---|---|---|
| **FINAL** | **0.861** | 0.800 | 0.800 | **0.800** | **0.847** | **0.847** | **0.846** | **0.898** | **0.123** |
| Always-LOW (p = 0) | 0.653 | undefined (no HIGH calls) | 0.000 | 0.000 | 0.395 | 0.500 | 0.347 | undefined | 0.347 |
| Climatology (training HIGH share) | 0.347 | 0.347 | 1.000 | 0.516 | 0.258 | 0.500 | 0.431 | 0.643 | 0.292 |
| Persistence (latest provincial survey) | 0.625 | 0.480 | **0.960** | 0.640 | 0.624 | 0.703 | 0.705 | 0.827 | 0.253 |
| PSA-indicator logistic | 0.556 | 0.436 | 0.960 | 0.600 | 0.550 | 0.650 | 0.675 | 0.762 | 0.274 |
| Logistic, all inputs + anchor | 0.611 | 0.467 | 0.840 | 0.600 | 0.611 | 0.665 | 0.689 | 0.803 | 0.320 |
| NLP-only logistic | 0.639 | 0.487 | 0.760 | 0.594 | 0.634 | 0.667 | 0.611 | 0.703 | 0.244 |

- Confusion matrices (TP/FP/FN/TN): FINAL 20/5/5/42; always-LOW 0/0/25/47; persistence 24/26/1/21; PSA 24/31/1/16; logistic (all) 21/24/4/23; NLP-only 19/20/6/27.
- Every baseline at every lead is in `REL_vs_baselines.csv`.

**Paired bootstrap at Lead 1** (4,000 resamples; the difference is FINAL minus the baseline):

| vs | ΔBrier | 95 % CI | ΔAccuracy 95 % CI |
|---|---|---|---|
| Always-LOW | −0.224 | [−0.338, −0.112] | [+0.083, +0.333] |
| Climatology | −0.169 | [−0.220, −0.119] | [+0.361, +0.653] |
| Persistence | −0.130 | [−0.197, −0.069] | [+0.111, +0.375] |
| PSA logistic | −0.150 | [−0.211, −0.088] | [+0.167, +0.444] |
| Logistic (all) | −0.197 | [−0.288, −0.116] | [+0.139, +0.362] |
| NLP-only | −0.121 | [−0.183, −0.063] | [+0.083, +0.361] |

## 2. Majority-class check (brief §3)
- Always-LOW scores 0.653 accuracy, so accuracy alone is not used as evidence.
- FINAL's lead over always-LOW is significant at Leads 1–4. At **Lead 5** the CI lower bound is 0.000, so it is not significant.
- On the class-balanced measures FINAL is far above the majority rule:
  - macro F1: 0.847 vs 0.395;
  - balanced accuracy: 0.847 vs 0.500;
  - PR-AUC: 0.846 vs 0.347.
- **The exception is the 2021 round.** There, FINAL is essentially the majority rule: accuracy 0.88 vs 0.84, with 1 of 4 HIGH found.

## 3. Calibration at Lead 1
- ECE (10 bins): 0.080.
- Mean p − observed rate: +0.046.
- Calibration slope: 1.25. Logit intercept: −0.33.
- Cox recalibration test: p = 0.41, so miscalibration is **not detected**. At n = 72 this test has low power; the 11-13 simulation showed that ECE ≤ 0.05 is met only 0.7 % of the time even by a perfectly calibrated model at this n.
- Reliability table (`REL_reliability_L1.csv`): the 0.4–0.5 bin over-forecasts (mean p 0.45, observed 1/7). The other bins lie within sampling noise.

## 4. Result
- On these retrospective rows, FINAL is better than every baseline on Brier, accuracy, macro F1, balanced accuracy and PR-AUC, at every lead from 1 to 5. The Brier advantage is significant against all six baselines at Leads 1–5, except against the all-input logistic at Lead 4, where the CI includes 0.
- **Persistence still has higher HIGH recall** (0.96 vs 0.80), at the cost of 26 false alarms against FINAL's 5.
