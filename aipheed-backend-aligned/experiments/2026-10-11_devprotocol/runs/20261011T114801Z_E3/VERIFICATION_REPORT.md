# E3 Independent Verification (run 20261011T114801Z_E3)

**Method:** `verify_e3.py`, in this folder. It recomputes everything from:

- the 28 saved prediction files;
- `data/processed/labels.parquet`;
- the Rule L eligibility functions;
- the development frame.

It does **not** reuse the runner's metric or bootstrap functions, and **no model was fitted**.

**Output:** `verification_recomputed_metrics.csv`.

**Not changed:** the original `REPORT.md` (SHA-256 `fb1bc6508630614e…`), the protocol, the thesis, production and every protected file.

**Result: no discrepancies found.**

## 1. Metrics, recomputed from the saved predictions and labels

| Check | Result |
|---|---|
| Labels | y recomputed as stress > τ from `labels.parquet` (80 rows, 2021–2025) |
| Thresholds | τ recomputed from the eligibility rules (A-origin) and the 80-row median 14.345 (A-global). Maximum difference from the saved τ: 2×10⁻¹⁵. |
| Scored rows matched | 700/700, with **0** label mismatches and **0** prediction mismatches |
| Carry-forward | Rebuilt from the anchor quarter's stress: **0** mismatches |
| Equation 3 rule | Rebuilt from `sws_hunger + 2·cpi_rel`: **0** mismatches in class or score |
| Every metric in `metrics.json` | Accuracy, balanced accuracy, HIGH and LOW recall, weighted precision and F1, ROC-AUC, and confusion matrices, for all 4 analysis/variant blocks × 5 predictors: **0 discrepancies** |

ROC-AUC was recomputed with an independent Mann–Whitney implementation.

**Primary: A-origin, base inputs (verified).** The test set has 32 HIGH and 3 LOW rows.

| Predictor | Correct | Accuracy | Balanced acc. | HIGH recall | LOW recall | Weighted P / F1 | ROC-AUC | [[TN,FP],[FN,TP]] |
|---|---|---:|---:|---:|---:|---|---:|---|
| E3 LightGBM | **32/35** | 0.914 | **0.802** | 0.938 (30/32) | 0.667 (2/3) | 0.928 / 0.920 | 0.797 | [[2, 1], [2, 30]] |
| Carry-forward | 30/35 | 0.857 | 0.771 | 0.875 (28/32) | 0.667 (2/3) | 0.911 / 0.877 | 0.740 | [[2, 1], [4, 28]] |
| Equation 3 rule | 29/35 | 0.829 | 0.755 | 0.844 (27/32) | 0.667 (2/3) | 0.906 / 0.857 | **0.927** | [[2, 1], [5, 27]] |
| Always-HIGH | 32/35 | 0.914 | 0.500 | 1.000 | 0.000 | 0.836 / 0.873 | undefined | [[0, 3], [0, 32]] |
| Always-LOW | 3/35 | 0.086 | 0.500 | 0.000 | 1.000 | 0.007 / 0.014 | undefined | [[3, 0], [32, 0]] |

**How the AUCs were computed:**

- **E3:** its predicted probability.
- **Carry-forward:** last published stress − τ.
- **Equation 3:** (SWS + 2·`cpi_rel`) − τ.
- **Always-HIGH and always-LOW:** undefined, because their scores are constant. **No scores were manufactured.**
- Pooling margins across folds is appropriate, because each margin is measured from its own fold's threshold.

**The three LOW rows (verified):**

| Quarter | Province | Predicted LOW by |
|---|---|---|
| 2023-Q4 | Quezon | All three predictors |
| 2024-Q1 | Quezon | All three predictors |
| 2025-Q4 | Batangas | **None** (all three predicted HIGH) |

E3, carry-forward and Equation 3 made **identical decisions on every LOW row**. Every balanced-accuracy difference between them comes from HIGH recall alone: E3 has 2 more correct HIGH rows than carry-forward, and 3 more than Equation 3.

## 2. Uncertainty

**Implementation (inspected):** both bootstrap functions resample **whole quarters**: 7 quarter indices drawn with replacement, and all 5 rows of each drawn quarter kept together. They do **not** treat provinces as independent.

**Paired balanced-accuracy difference** (primary, A-origin, base; E3 − baseline):

| Comparison | Point estimate | 95% CI (runner, reproduced exactly) | 95% CI (independent re-implementation) | Draws with difference ≤ 0 |
|---|---:|---|---|---:|
| E3 − carry-forward | **+0.031** | **0.000 to +0.069** | 0.000 to +0.074 | 9.4% |
| E3 − Equation 3 | +0.047 | +0.015 to +0.091 | +0.015 to +0.094 | 1.8% |

**Bootstrap method:**

- **Runner scheme:** percentile quarter-cluster bootstrap with `numpy.random.default_rng(42)` and 10,000 resamples. **209 resamples (2.1%) contained no LOW row and were skipped**, because balanced accuracy is undefined without both classes.
- **Independent re-implementation:** `PCG64(2026)` and 20,000 resamples drawn with `choice`.

**What the intervals mean for the decision rule:**

- **Against carry-forward (the better baseline, which the decision rule uses):** the interval **includes 0** (its lower bound is exactly 0.000). The point gain of 0.031 is also below the pre-registered 0.10. **Neither improvement condition is met; the "non-inferiority" verdict is confirmed.**
- **Against Equation 3:** the interval excludes 0. But the gain (0.047) is below 0.10, and Equation 3 is not the better baseline, so the decision rule is unchanged.
- **This interval should not be over-read.** It reflects only the 2–3 extra HIGH rows E3 got right. The 3 LOW rows contribute no difference.

**The 0.83–0.97 accuracy interval** (verified: 0.8286–0.9714):

- **What it is:** a percentile quarter bootstrap of **E3's own mean-quarter accuracy**. The per-quarter accuracies are 1.0, 0.8, 1.0, 0.8, 1.0, 1.0 and 0.8.
- **What it estimates:** how much that accuracy would vary if quarters like these 7 were redrawn.
- **What it does not do:**
  - compare E3 with any baseline;
  - correct for the reuse of these quarters across three designs;
  - correct for the regime shift.
- **Context:** always-HIGH has the same point accuracy (0.914).
- **It is not evidence of superiority** over a baseline, and not evidence for the 75% requirement.

**Row-level Clopper–Pearson** (0.769–0.982, verified) assumes the 35 rows are independent. They are not, because the five provinces share the regional SWS value. It is optimistic.

## 3. Experimental integrity

| Check | Result |
|---|---|
| Output files vs `manifest.json` hashes | 31/31 match |
| Predictions before labels | All 28 prediction files contain no label columns. All were written before `scored_rows.csv` (manifest write order). The manifest records 28 label reveals, each made by the runner only after that fold's predictions were written and registered (code: `register_predictions` precedes `reveal`). |
| No protected 2026 data | No 2026 row in any prediction or score. The labels used end at 2025-Q4. |
| Same test quarters and eligibility | Test quarters identical to E1. Eligible training quarters identical to E1's `config.json` and to a fresh recomputation today. Minimum 8 training quarters. |
| Threshold analyses distinguished | A-origin τ per fold matches the recomputation. A-global = 14.345 everywhere. Reported in separate blocks. |
| 7-input vs +FSSI | Separate prediction files and metric blocks; both recomputed with no discrepancy. The primary verdict uses the 7-input model only. |
| Protected data at runtime | The runner reported 312 protected files unchanged |
| Input provenance | 122 input files have identical SHA-256 in the E1 config, the E3 config and today |
| Production `backend/` | 54 files re-hashed today, all matching the pre-E1 baseline (served model `cbab63f8…`). No archive, candidate or pipeline-run folder exists. |

**Discrepancies: none.**

**Not re-verifiable without refitting:** the E3 probabilities themselves. They are taken from the hashed prediction files. At runtime the runner fitted every fold twice and required identical predictions.

**Verification-process note:** the first execution of `verify_e3.py` stopped on a filename-parsing error in the script itself. The partial CSV it had written was deleted and the script rerun. No E3 artifact was affected.

## 4. Thesis-ready conclusion

> In the third exploratory experiment (E3), a LightGBM classifier was trained with a compact set of seven predefined inputs and with monotonic constraints on the two hunger-level inputs. It was evaluated on seven time-ordered test quarters (35 province-quarter rows) using a threshold computed from training data only. The model classified 32 of the 35 rows correctly (91.4% accuracy), with a balanced accuracy of 0.802. However, its balanced accuracy was only 0.031 higher than that of the carry-forward baseline (95% quarter-bootstrap interval: 0.000 to 0.069). This did not meet the preregistered improvement criterion of 0.10, so the result was classified as non-inferior rather than improved. A rule that always predicts HIGH reached the same 91.4% accuracy, and the Equation 3 rule ranked the rows better than the model (ROC-AUC 0.927 compared with 0.797). The test set was small, contained only three LOW cases, and consisted of quarters already used in earlier experiments; the five provinces in each quarter also share the same regional hunger value. These results therefore do not establish that the model generalizes, and they do not yet show that it meets the study's greater-than-75% performance requirement under an independent evaluation.

## 5. What can and cannot be claimed

**Can safely be claimed:**

- A compact, constrained LightGBM (7 predefined inputs) achieved 32/35 correct (91.4%) and a balanced accuracy of 0.802 on the 7 reused test quarters, under a training-only threshold.
- It clearly improved on the earlier 44-input LightGBM configuration on the same quarters: balanced accuracy 0.615 → 0.802; HIGH recall 0.56 → 0.94.
- Under the pre-registered rule, it was **non-inferior** to carry-forward and the Equation 3 rule. Its balanced-accuracy gain over carry-forward was 0.031 (95% CI 0.000 to 0.069).
- The Equation 3 rule had the highest ROC-AUC (0.927).
- The evaluation was time-ordered, used only information published before each forecast date, and wrote each fold's predictions before reading its labels.

**Must not be claimed:**

- That the model meets or exceeds the > 75% requirement, or that 91.4% shows it does.
- That LightGBM **outperforms** or **adds value beyond** the baselines.
- That the results generalize, or that this was an independent or blind validation.
- That the 0.83–0.97 interval shows superiority, or that row-level intervals reflect 35 independent observations.
- That the model identifies LOW-risk cases well. There were only 3 LOW rows, and all predictors made the same decisions on them.
- That the FSSI (news) hypothesis was tested. FSSI was missing in most rows.
- That the global-threshold (14.345) results are leakage-free.
- That E3 is approved for, or frozen as, the 2026 forecasting model.
