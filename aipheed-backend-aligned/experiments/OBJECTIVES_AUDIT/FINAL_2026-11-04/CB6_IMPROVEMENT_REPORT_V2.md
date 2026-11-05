# C-B6 improvement attempt V2 (C-B7), 2026-11-04

**Result: no improvement. C-B6 is retained unchanged as the main model.** C-B7 is recorded as a failed attempt (24th).

## 1. New data investigated

| Source | Outcome |
|---|---|
| **Regional unemployment** (Region IV-A, quarterly) | **Not obtainable** as data. PSA OpenSTAT `1B/LFS` and `3K/E2` publish **national** series only (checked 2026-11-04); regional rates exist only in PDF releases. Arm dropped |
| **GDELT headlines 2017–2026** (free DOC API) | Throttled to about one response every few minutes (about 1.5 days in total). Stopped at 10 of about 510 weeks. A BigQuery alternative (1.42 TiB, about US$9) was declined. **Not used** |
| **Teammate's FI6-N publisher archive** (`aiPHeed_Best_News_Dataset_FI6N.xlsx`, SHA-256 36aee994…) | **Used** (Addendum 1, 99dc56d7…, before any scoring): 2,641 articles, 2012–2026, 95% Rappler, publication dates, restated official statistics (including SWS hunger) removed by the teammate. Credit: team member's FI6-N work |

## 2. What was built (pre-registered: `CB7_PREREGISTRATION.md` f616407e…, `CB7_ADDENDUM_1.md` 99dc56d7…)

- **Admission:** our classifier v2 on titles kept **373** headlines; 0 duplicates removed.
- **Intensity:** each was scored with our XLM-RoBERTa FSSI-v2 scorer.
- **Regional index:** G(t) = mean intensity per quarter (n ≥ 5) exists for 30 quarters. Its correlation with article
  volume is **0.14** (a weak volume link).
- **Feature:** `z_G` (anomaly vs the past 8 quarters) exists at **21 origins, from 2018-Q3**.
- **Leakage check:** passed; no headline on or after O(t) enters origin t.
- **Model:** C-B7 = C-B6 + `z_G` (24 inputs), C-b's procedure.
- **Replication check:** the copied C-b code reproduces C-b exactly (1.1e-16).

**Scripts:** `runner/news_g_build.py`, `runner/cb7_model.py`; `news_g_fetch.py` (GDELT, kept for later).

## 3. Results (62 quarters, identical procedure)

| Lead 1 / Lead 2 | C-b | **C-B6 (main)** | C-B7 |
|---|---|---|---|
| Accuracy | 0.790 / 0.790 | **0.806 / 0.806** | 0.790 / 0.790 |
| Balanced accuracy | 0.717 | **0.743** | 0.731 |
| Precision / Recall | 0.812 / 0.907 | **0.830 / 0.907** | 0.826 / 0.884 |
| F1 | 0.857 | **0.867** | 0.854 |
| AUC | 0.702 / 0.704 | **0.723** / 0.712 | **0.723** / 0.707 |
| Brier | 0.187 / 0.184 | **0.183 / 0.181** | 0.184 / 0.184 |
| R1–R7 | R7 fails | all pass | all pass |
| Reliable lead | 2 | 2 | 2 |
| Baseline tests proven (of 14) | — | **9** | 7 |

**C-B7 vs C-B6:**

| | Brier diff | p |
|---|---|---|
| Lead 1 | +0.0013 (worse) | 0.79 |
| Lead 2 | +0.0038 (worse) | 0.97 |

**H8 fails, so the acceptance rule fails.**

**C-B7 baseline comparisons** (Holm, 14 tests):
- **Proven:** persistence L1/L2, LGBM-GOV L1/L2, logistic NLP-only L1/L2, LGBM-NLP L1.
- **Not proven:** always-HIGH (0.06), LOGIT, PSA-only, LGBM-NLP L2.

## 4. Why no gain

- **Too little news.** The index exists at only 21 of 113 origins (from 2018). The 1998–2017 training rows carry no
  news.
- **A thin selection.** After our relevance filter, about 6 headlines a quarter remain, mostly national, and 95% from
  one outlet.
- **Consistent with every earlier news test.** GDELT events (OLD_NEWS), the C-E2 ablation and the FSSI early-warning
  test all show news adds little to SWS-hunger forecasting.

## 5. Protection checks

- **C-B6 artifacts unchanged:** fits, results and served export (its forecasts are byte-identical). C-b, C-E2, C-E6 and
  the 7-baseline and R1–R7 results are unchanged.
- **Snapshot:** the only snapshot difference is C-B6's `evaluation.json` description text, changed earlier by the
  approved "main model" decision.
- **Registry:** C-B7 appended to `NEW_MODEL/ALLBASE/REGISTRY.csv` (backup `backup/REGISTRY_before_CB7.csv`).
- **Not changed:** the dashboard, API and configuration. Nothing committed or pushed.

## 6. Limitations

- The teammate archive's relevance labels are machine-made and not human-verified.
- Source concentration is 95% Rappler.
- The regional labour data needs manual extraction from PSA PDFs, which was not attempted.
- All results are development evidence on 62 examined quarters.
