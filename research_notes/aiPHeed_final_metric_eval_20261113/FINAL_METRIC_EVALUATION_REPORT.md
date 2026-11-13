# FINAL LightGBM: metric-by-metric evaluation against the project acceptance targets (2026-11-13)

**Model:** FINAL (RATE + MIND), frozen configuration. Nothing was retrained, re-thresholded or synthesised.

**Data:** the 5-seed rolling-origin walk-forward predictions already stored (110 fits). The cut-off is fixed at 0.50; HIGH means HFIAS moderate+severe ≥ 50 %.

**Script:** `scripts/metric_eval.py`. **Evidence:** `evidence/ME_by_lead.csv`, `ME_by_round.csv`, `ME_baselines.csv`, `ME_by_seed.csv`.

## 1. Evaluation requirements check

| # | Requirement | Verified? | Evidence |
|---|---|---|---|
| 1 | Metrics on genuine held-out data | **Partly.** Each fold's test round is held out of its own training: chronological, real FNRI survey labels. **But** the same 72 outcomes were scored many times during model development, so this is *retrospective* evaluation, not an untouched test set | `../aiPHeed_final_reliability_20261113/02` |
| 2 | Chronological / rolling-origin validation | Yes. Folds are ENNS 2018, 2019 and 2021; each trains only on rounds released before its origin (expanding window) | `../aiPHeed_final_official_20261113/07` |
| 3 | HIGH and LOW reported separately | Yes | §3 |
| 4 | Accuracy not driven by predicting LOW | Yes. FINAL predicts 25 HIGH out of 72 (always-LOW would score 65.3 %); recall_HIGH and recall_LOW are both about 0.80–0.89 | §3, §4 |
| 5 | Compared with persistence / naive | Yes (persistence, always-LOW) | §4 |
| 6 | Stability across rounds | Yes, and **it fails in 2021** | §5 |
| 7 | No future information or leakage | Yes. 110 fits, 0 violations (training rounds released before each origin; test round never in training) | `../aiPHeed_final_reliability_20261113/evidence/LEAK_origin_check.json` |
| 8 | One-quarter-ahead performance out-of-sample | Yes, retrospectively (Lead 1 = forecast made one quarter before the survey reference quarter) | §2 |
| 9 | Calibration via Brier | Yes | §2 |
| 10 | No synthetic labels, threshold changes or edited results | Yes | — |

## 2. Metric-by-metric result: one quarter ahead (Lead 1, 72 province-rounds, 25 HIGH)

| Priority | Metric | Achieved | 95 % CI | Target | Status |
|---|---|---|---|---|---|
| 1 | HIGH-risk recall | **0.800** (20/25) | [0.615, 0.947] | ≥ 0.70 | **PASS** (CI lower bound below 0.70) |
| 2 | F1 (HIGH) | **0.800** | [0.667, 0.906] | ≥ 0.70 | **PASS** (CI lower bound below 0.70) |
| 3 | Precision (HIGH) | **0.800** (20/25) | [0.633, 0.952] | ≥ 0.70 | **PASS** (CI lower bound below 0.70) |
| 4 | Balanced accuracy | **0.847** | [0.751, 0.936] | ≥ 0.70 | **PASS** |
| 5 | Brier score | **0.123** | [0.083, 0.165] | ≤ 0.20 | **PASS** |
| 6 | Accuracy | **0.861** | [0.778, 0.931] | ≥ 0.75 | **PASS** |
| 7 | ROC-AUC | **0.898** | — | ≥ 0.70 | **PASS** |
| 8 | PR-AUC | **0.846** | — | > prevalence 0.347 | **PASS** |

## 3. HIGH vs LOW performance (Lead 1)

| Class | Recall | Precision | F1 | Counts |
|---|---|---|---|---|
| HIGH (n = 25) | 0.800 | 0.800 | 0.800 | 20 found, 5 missed |
| LOW (n = 47) | 0.894 | 0.894 | 0.894 | 42 correct, 5 false alarms |

Confusion matrix (TP / FP / FN / TN): **20 / 5 / 5 / 42**.

## 4. Baseline comparison (Lead 1, same 72 rows)

| Metric | FINAL | Persistence (latest provincial survey) | Always-LOW |
|---|---|---|---|
| HIGH recall | 0.800 | **0.960** | 0.000 |
| F1 | **0.800** | 0.640 | 0.000 |
| Precision | **0.800** | 0.480 | undefined |
| Balanced accuracy | **0.847** | 0.703 | 0.500 |
| Brier | **0.123** | 0.253 | 0.347 |
| Accuracy | **0.861** | 0.625 | 0.653 |
| ROC-AUC | **0.898** | 0.827 | — |
| PR-AUC | **0.846** | 0.705 | 0.347 |

FINAL's Brier is better than persistence by 0.130 (95 % CI [0.064, 0.193]) and better than always-LOW by 0.224 (CI [0.111, 0.337]).

**Persistence catches more HIGH provinces (24 vs 20) but raises 26 false alarms against FINAL's 5.** Persistence fails the precision, F1 and accuracy targets; FINAL passes all of them.

## 5. Stability across validation rounds (Lead 1)

| Round | n | HIGH | Recall | F1 | Precision | Balanced accuracy | Brier | Accuracy | ROC-AUC | PR-AUC (prevalence) |
|---|---|---|---|---|---|---|---|---|---|---|
| ENNS 2018 | 22 | 8 | 1.000 ✓ | 0.842 ✓ | 0.727 ✓ | 0.893 ✓ | 0.130 ✓ | 0.864 ✓ | 0.964 ✓ | 0.950 (0.36) ✓ |
| ENNS 2019 | 25 | 13 | 0.846 ✓ | 0.846 ✓ | 0.846 ✓ | 0.840 ✓ | 0.151 ✓ | 0.840 ✓ | 0.853 ✓ | 0.841 (0.52) ✓ |
| ENNS 2021 | 25 | 4 | **0.250 ✗** | **0.400 ✗** | 1.000 ✓ | **0.625 ✗** | 0.090 ✓ | 0.880 ✓ | 0.857 ✓ | 0.610 (0.16) ✓ |

**2021 fails three priority targets.** Only 1 of 4 HIGH provinces was found (Tawi-Tawi). Masbate, Occidental Mindoro and Agusan del Sur were missed:
- **Cause:** the model's elapsed-time term extrapolates beyond the survey gaps seen in training (24 quarters vs ≤ 20). See `../aiPHeed_final_official_20261113/06`.
- **Accuracy (0.88) hides this.** Always-LOW would score 0.84 in that round.

**Seed stability (Lead 1, 5 seeds):**
- recall 0.76–0.80; F1 0.776–0.800; precision 0.792–0.800;
- balanced accuracy 0.827–0.847; accuracy 0.847–0.861; Brier 0.123–0.125.

Every seed passes every target.

**Training-round sensitivity:** removing one training round from the 2021 fold changes its HIGH recall between 1/4 and 3/4 (up to 8 class changes in 25 provinces). HIGH detection there is not stable.

## 6. All forecast horizons (pooled; supplementary)

| Lead | Recall | F1 | Precision | BA | Brier | Accuracy | ROC-AUC | PR-AUC (prev. 0.35) | All 8 pass |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 0.800 | 0.800 | 0.800 | 0.847 | 0.123 | 0.861 | 0.898 | 0.846 | **Yes** |
| 2 | 0.800 | 0.784 | 0.769 | 0.836 | 0.123 | 0.847 | 0.899 | 0.855 | **Yes** |
| 3 | 0.760 | 0.745 | 0.731 | 0.806 | 0.133 | 0.819 | 0.883 | 0.775 | **Yes** |
| 4 | 0.800 | 0.755 | 0.714 | 0.815 | 0.135 | 0.819 | 0.885 | 0.775 | **Yes** |
| 5 | 0.760 | 0.717 | **0.679 ✗** | 0.784 | 0.138 | 0.792 | 0.874 | 0.815 | No |
| 6 | **0.680 ✗** | **0.654 ✗** | **0.630 ✗** | 0.734 | 0.146 | 0.750 | 0.866 | 0.792 | No |
| 7 | 0.706 | **0.615 ✗** | **0.545 ✗** | 0.701 | 0.180 | **0.700 ✗** | 0.815 | 0.686 | No |
| 8 | 0.824 | **0.683 ✗** | **0.583 ✗** | 0.760 | 0.175 | **0.740 ✗** | 0.818 | 0.674 | No |

- Under these project targets, **Leads 1–4 pass all eight metrics pooled.**
- The 2021 round fails recall, F1 and balanced accuracy at Leads 1–5 (`ME_by_round.csv`).
- Seed minimums at Lead 3 dip just below 0.70 for precision (0.692); at Lead 4 every seed passes.

## 7. Overall assessment

| Question | Answer |
|---|---|
| Does FINAL meet all 8 targets one quarter ahead (pooled)? | **Yes.** Recall 0.80, F1 0.80, precision 0.80, BA 0.847, Brier 0.123, accuracy 0.861, ROC-AUC 0.898, PR-AUC 0.846 > 0.347 |
| Is the accuracy produced by predicting LOW? | **No.** Both classes are predicted well (HIGH 0.80, LOW 0.89) |
| Is it better than the naive baseline? | **Yes.** Better than persistence on F1, precision, BA, Brier, accuracy, ROC-AUC and PR-AUC. Persistence has higher recall but fails precision |
| Is it stable across validation rounds? | **No.** 2018 and 2019 pass every target, but **2021 fails recall (0.25), F1 (0.40) and balanced accuracy (0.63)** |
| Are all mandatory requirements verified? | **Not fully.** The evaluation is chronological and leakage-free, but the evaluation data were reused during development (requirement 1 only partly met), and there is no untouched independent test round |

**Verdict:**
- FINAL **passes all eight project targets at the pooled level for Leads 1–4.**
- It **does not pass consistently across validation rounds.** It misses most HIGH-risk provinces when the last survey is older than anything seen in training (the 2021 round).
- It can be called a **retrospectively validated provincial risk screen for one to four quarters ahead.**
- It **cannot yet be called reliable for HIGH-risk detection in every period, nor independently validated.** That needs scoring of the sealed forecasts (`80b20aed…`) against the next FNRI provincial HFIAS round.
- Recommended display safeguard: flag provinces whose last survey is older than the training range.
