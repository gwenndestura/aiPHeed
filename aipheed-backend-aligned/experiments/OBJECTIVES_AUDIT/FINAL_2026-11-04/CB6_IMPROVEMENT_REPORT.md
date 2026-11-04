# C-E6 metrics fix and model improvement (C-B6), 2026-11-04

**Result:**
- **Metric reporting fixed:** every value is now generated from the artifacts, verified, and given an explicit status.
- **New candidate C-B6** (C-b + rice stocks): **the first to pass R1–R7 at both leads**, with the best accuracy (0.806),
  balanced accuracy (0.743) and Brier (0.183 / 0.181) of all the models.
- **Not adopted:** its improvement over C-b is not significant (p 0.13 / 0.20), and the R1–R7 pass rests on one
  changed forecast.

**Recommendation: CONTINUE DEVELOPMENT.** Seal C-B6 beside C-b, C-E2 and C-E6 for the 2027 prospective test
(needs approval).

## 1. Metric reporting fix

- **Cause of the dashes:** none in the data. `evaluation.json` and the API have no missing metric. The dashes were in
  my hand-written reports:
  - "Target —" for F1, AUC and Brier, which have no pre-registered threshold;
  - "—" for always-HIGH's AUC, which is undefined for a constant forecast.
- **Fix:** `runner/report_metrics.py` writes `FINAL_2026-11-04/METRICS_REPORT.md` and `out/metrics_report.json`.
  - It recomputes accuracy, balanced accuracy, precision, recall, F1, AUC-ROC, Brier and the confusion matrix from the
    stored forecasts, for C-b, C-E2, C-E6 and C-B6 at both leads.
  - It stops if any value differs from the model's results file. **All 8 model-leads match, difference 0.0.**
  - Each cell is labelled PASS or FAIL (where a threshold exists), REPORTED (no threshold) or UNDEFINED.
- **Nothing is hard-coded.**

## 2. Improvement: C-B6 (pre-registered, one candidate)

- **Plan:** `OBJECTIVES_AUDIT/CB6_PREREGISTRATION.md`, PLAN-SHA256
  `2efd9677e3785f4b3469b416e34cd824d536e16450ae100ceea537044d20a38b`, fixed before the fit.
- **Why it is not a repeat:**
  - Rice stocks were the only input with a significant out-of-sample gain (on C-E2).
  - C-E6 inherited C-E2's architecture, which fails R3.
  - C-b's architecture (grid selection on inner folds, no national E1/E2) passes R3.
  - Stocks inside C-b had never been tested.
- **Definition:** C-b's procedure line for line (`run_news_v2._origin`) plus ST1/ST2 (stock month ≤ issue − 4).
- **Replication check:** the copied C-b code reproduces the stored C-b forecasts (max difference 1.1e-16) before C-B6
  is fitted.
- **No variant was tried.**

## 3. Before and after (62 quarters; all values from `METRICS_REPORT.md`)

| Lead 1 / Lead 2 | C-b (main) | C-E6 (before) | **C-B6 (new)** |
|---|---|---|---|
| Accuracy | 0.790 / 0.790 PASS | 0.774 / 0.758 PASS | **0.806 / 0.806 PASS** |
| Balanced accuracy | 0.717 / 0.717 PASS | 0.690 / 0.679 **FAIL** | **0.743 / 0.743 PASS** |
| Precision | 0.812 PASS | 0.796 / 0.792 PASS | **0.830 PASS** |
| Recall | 0.907 PASS | 0.907 / 0.884 PASS | 0.907 / 0.907 PASS |
| F1 | 0.857 REPORTED | 0.848 / 0.835 REPORTED | **0.867 REPORTED** |
| AUC-ROC | 0.702 / 0.704 REPORTED | 0.720 / 0.695 REPORTED | **0.723 / 0.712 REPORTED** |
| Brier | 0.187 / 0.184 REPORTED | 0.184 / 0.186 REPORTED | **0.183 / 0.181 REPORTED** |
| TP/FP/FN/TN | 39/9/4/10 | 39/10/4/9 · 38/10/5/9 | 39/8/4/11 |
| ECE (calibration, lower is better) | 0.169 / 0.152 | 0.175 / 0.108 | 0.184 / 0.169 |
| R1–R7 | R7 FAIL | R3, R7 FAIL | **all PASS** |
| R7 thirds | 0.952 / 0.571 / 0.850 | 0.952 / 0.524 / 0.850 | 0.952 / **0.619** / 0.850 (LOQO min 0.803) |
| Reliable lead (Algorithm 3) | 2 | **3** | 2 (Lead 3 = 0.742, just under 0.75) |

## 4. What changed and why (honest reading)

- **One forecast changed versus C-b:** origin 2018-Q3 went from 0.530 to 0.458. That turns two false HIGH calls into
  correct LOW calls (2018-Q4 at Lead 1, 2019-Q1 at Lead 2).
  - That one flip moves TN from 10 to 11 (R3 0.717 → 0.743) and the 2015–2020 third from 12/21 to 13/21 (0.571 →
    0.619 ≥ 0.60, so **R7 passes**).
  - **It is the same forecast S1 flipped** (S1_RESULTS.md). The R1–R7 pass is real on these data but fragile: it
    depends on one origin.
- **Probabilities:** better than C-b on average (Brier −0.0044 / −0.0031), but **not significant**:

  | | p | 95% CI |
  |---|---|---|
  | Lead 1 | 0.13 | −0.012..+0.003 |
  | Lead 2 | 0.20 | −0.011..+0.004 |

  The pre-registered H7 (p < 0.10 at both leads) **fails**, so the acceptance rule fails.
- **Calibration:** ECE is slightly worse than C-b (0.184 vs 0.169 at Lead 1; 0.169 vs 0.152 at Lead 2) and than C-E6
  at Lead 2. Not a claimed improvement.
- **Lost vs C-E6:** the reliable lead drops from 3 to 2 (C-b's architecture).
- **Dashboard consequence if it were ever served:** C-B6 has no employment or remittance inputs, so those two driver
  bars would be "not a model input" (as for C-b).

## 5. Seven baselines (C-B6; Holm over 14; one-sided cluster bootstrap, seed 2036, B 5000)

| Baseline | L1 Brier model / baseline | L1 Holm p | L1 | L2 Brier model / baseline | L2 Holm p | L2 |
|---|---|---|---|---|---|---|
| Persistence | 0.183 / 0.339 | 0.000 | PROVEN | 0.181 / 0.339 | 0.000 | PROVEN |
| LGBM government-only | 0.183 / 0.233 | 0.026 | PROVEN | 0.181 / 0.240 | 0.022 | PROVEN |
| Logistic NLP-only (news era) | 0.178 / 0.353 | 0.007 | PROVEN | 0.200 / 0.434 | 0.016 | PROVEN |
| LGBM NLP-only (news era) | 0.178 / 0.307 | 0.009 | **PROVEN (new)** | 0.200 / 0.310 | 0.081 | NOT PROVEN |
| Always-HIGH | 0.183 / 0.307 | 0.049 | PROVEN | 0.181 / 0.307 | 0.048 | PROVEN |
| Logistic government-only (PSA-only) | 0.183 / 0.208 | 0.424 | NOT PROVEN | 0.181 / 0.239 | 0.135 | NOT PROVEN |
| Logistic combined (LOGIT) | 0.183 / 0.193 | 0.424 | NOT PROVEN | 0.181 / 0.234 | 0.188 | NOT PROVEN |

- **9 of 14 PROVEN** (C-E6: 8; C-E2: 4). All 14 differences favour C-B6.
- **Not proven:** the two logistic regressions at both leads, and LGBM NLP-only at Lead 2.
- **C-B6 does not beat all seven baselines.**

## 6. Remaining failures

| Item | Status |
|---|---|
| Improvement over C-b (H7) | ❌ Not significant |
| R1–R7 robustness | ⚠️ Pass depends on one forecast |
| All seven baselines | ❌ 9 of 14 |
| Reliable lead | 2 (C-E6: 3) |

**All of this is development evidence on 62 previously examined quarters (attempt 23).** Only prospective quarters can
confirm it. `CE6_PROSPECTIVE_PREPARATION_REPORT.md` §8 gives the power limits.

## 7. Verification

- **Metrics:** recomputed from the artifacts = results files (difference 0.0, all 8 model-leads).
- **Leakage:** the C-E6 stock features are unchanged when later months are randomized (`out/ce6_checks.json`). Labels
  are known at O(t). The C-b replication is exact.
- **Tests:**
  - dashboard and API: 87 passed, 8 skipped;
  - C-E prospective: 10 passed (slow replay deselected; it passed earlier today).
- **Preserved:**
  - 200/200 protected files;
  - C-E2 and C-E6 artifacts: ce2_fits c078aa27…, ce2_results 13666bfd…, ce6_fits 249c358b…, ce6_results 7e3ae937…,
    ce6_features 011509a9…;
  - demo exports: C-E2 rows 10cef6e2…, C-E6 rows acef5713…;
  - the C-E registry verifies.
- **8081 still serves C-E2, and 8002 / 8082 still serve C-E6.** No dashboard, frontend, API or serving file changed.

## 8. Files

**Created:**
- `OBJECTIVES_AUDIT/CB6_PREREGISTRATION.md`;
- `runner/cb6_model.py`, `runner/report_metrics.py`;
- `out/cb6_fits.csv`, `out/cb6_results.json`, `out/metrics_report.json`;
- `FINAL_2026-11-04/METRICS_REPORT.md`, this report.

**Appended:** `NEW_MODEL/ALLBASE/REGISTRY.csv` (+2 rows; backup `backup/REGISTRY_before_CB6.csv`).

**Modified:** none of the existing files.

## 9. Needs your approval

1. **Add C-B6 to the prospective registry and seal it** with the others in January 2027. This needs a plan addendum,
   because `CE_PROSPECTIVE_PLAN.md` names only C-E2 and C-E6.
2. **Commit.**
3. **Optional:** a C-B6 demo. Its Employment and OFW bars would be "not a model input".
