# OPTION_1, Step 2: evidence for REF+news (the team's main model, pending adviser confirmation)

**Model.** IMPROVE_V2 arm **REF+news**: the IMPROVE_V2 reference LightGBM with the news columns (N1R regional FSSI-v3,
GDELT price-news year-on-year, six E112 event-category shares). It is exactly as specified in `IMPROVE_V2/PLAN.md`: no
tuning and no new settings. REF, the same model without news, is reported beside it.

**IMPROVE_V2_NEWS.** No such folder exists in the repository or its history, so no part was skipped. The H3 table for
REF+news already existed (`../OBJECTIVES_COMPLETION/OBJ4_H3_COMPARISON.md` §2). It was recomputed here and matches it
at every number.

**Evidence status:** development evidence. Every quarter 2010–2026 was examined in IMPROVE_V2 and earlier.

## 1. Re-run and reproduction (`runner/run_option1.py fit`, `out/checks.json`)

- **What was re-run.** The REF+news walk-forward over every origin 1998-Q3..2026-Q3, storing test leads 1–15. The
  pooled table, training rows, grid, selection, LightGBM settings and seed are IMPROVE_V2's; its code is imported
  read only.
- **Inputs checked before fitting.** The IMPROVE_V2 PLAN hash and the HISTORY_RETRAIN data hashes.
- **Reproduction: exact, checked before scoring.**

  | Stored IMPROVE_V2 output (Leads 1–2) | Rows matched | Max. difference |
  |---|---|---|
  | REF+news forecasts | 226 of 226, bit for bit; same configuration at every origin | 0.0 |
  | PERSIST and CLIM baselines | 138 of 138 each | 0.0 |
  | Every SHAP value of REF+news | all; same missing-value pattern | 0.0 |

- **Baselines at earlier origins.** Leads > 2 need them from origin 2006-Q2, so they were computed there with the same
  definitions, as in IMPROVE_V2_LEADS.

## 2. Algorithm 3 and the Maximum Reliable Lead Time (`runner/run_option1.py score`, `out/results.json`)

**Rule** (Chapter III pp. 41–43): mean fold accuracy ≥ 0.75, with one quarter per fold, k = 1..8, halting at the first
failing lead. The targets are 2010-Q1..2026-Q3, 62 labelled quarters at every lead.

**Maximum Reliable Lead Time:**
- **2 quarters** under Algorithm 3. Lead 3 is the first failure, at 0.694.
- **0** under R1–R7: REF+news already fails R3, R5 and R7 at Lead 1. REF without news fails only R7.

| Lead | Accuracy (= mean fold accuracy) | Algorithm 3 | Persistence | R1–R7 failed |
|---|---|---|---|---|
| 1 | **0.758** | pass | 0.661 | R3, R5, R7 |
| 2 | **0.758** | pass | 0.661 | R3, R5, R7 |
| 3 | **0.694** | **fail: stop** | 0.661 | R2, R3, R5, R7 |

### Objective 2 metrics

| Lead | Accuracy | Precision | Recall | F1 | AUC-ROC | Brier | TP / FP / FN / TN |
|---|---|---|---|---|---|---|---|
| 1 | 0.758 | 0.804 | 0.860 | 0.831 | 0.688 | 0.195 | 37 / 9 / 6 / 10 |
| 2 | 0.758 | 0.804 | 0.860 | 0.831 | 0.674 | 0.199 | 37 / 9 / 6 / 10 |
| 3 | 0.694 | 0.761 | 0.814 | 0.787 | 0.662 | 0.212 | 35 / 11 / 8 / 8 |
| *REF, Lead 1 / 2* | *0.790 / 0.790* | *0.812* | *0.907* | *0.857* | *0.702 / 0.704* | *0.188 / 0.184* | *39 / 9 / 4 / 10* |

### R1–R7 at Leads 1 and 2

| Rule | Lead 1 | Lead 2 |
|---|---|---|
| R1 ≥ 10 quarters, ≥ 40 rows | pass (62) | pass (62) |
| R2 accuracy ≥ 0.75 | pass (0.758) | pass (0.758) |
| R3 balanced accuracy ≥ 0.70 | **fail (0.693)** | **fail (0.693)** |
| R4 > always-LOW and > persistence | pass (0.758 vs 0.306 / 0.661) | pass |
| R5 Brier < persistence and < climatology, p < 0.10 | **fail**: vs persistence −0.144 (p 0.000), vs climatology −0.025 (**p 0.171**) | **fail**: −0.140 (p 0.000); −0.023 (**p 0.208**) |
| R6 precision and recall ≥ 0.60 | pass (0.804 / 0.860) | pass |
| R7 each third ≥ 0.60, LOQO min ≥ 0.70 | **fail**: thirds 0.95 / **0.57** / 0.75 | **fail**: same |

## 3. SHAP group shares (verdict window, 62 rows)

| Group | Lead 1 | Lead 2 |
|---|---|---|
| Past SWS hunger | 64.3% | 64.2% |
| World food and energy prices | 21.2% | 21.4% |
| CALABARZON food and headline prices | 6.1% | 6.0% |
| **News (N1R, GDELT, six category shares)** | **2.8%** | **2.7%** |
| Rice | 2.5% | 2.4% |
| Climate (ONI) | 1.9% | 1.9% |
| Crops | 0.8% | 0.8% |
| Fisheries | 0.5% | 0.4% |
| Typhoons | 0.1% | 0.1% |

**News inside the forecast does not improve it.** REF+news minus REF on the same 62 quarters:

| Lead | Brier | p (one-sided) | Accuracy, REF+news vs REF |
|---|---|---|---|
| 1 | +0.008 | 0.82 | 0.758 vs 0.790 |
| 2 | +0.015 | 0.96 | 0.758 vs 0.790 |

## 4. Objective 4 and H3

Brier difference is REF+news minus the comparator; negative means REF+news is better. The test is a one-sided paired
cluster bootstrap by target quarter (seed 2036, 5000 draws). Holm correction is applied within each table and lead. The
news-only comparators are scored on the news-era quarters (20 at Lead 1, 19 at Lead 2). The comparators are the stored
IMPROVE_V2 and OBJECTIVES_COMPLETION forecasts; none was refitted.

### Objective 4: the four named baselines plus always-HIGH

| Comparator | L1 diff | p | Holm p | L2 diff | p | Holm p |
|---|---|---|---|---|---|---|
| I. Naive persistence | −0.143 | 0.000 | **0.001** | −0.140 | 0.000 | **0.002** |
| II. PSA-only (logistic) | −0.013 | 0.345 | 0.690 | −0.040 | 0.106 | 0.213 |
| III. NLP-only (logistic) | −0.129 | 0.004 | **0.015** | −0.178 | 0.014 | 0.054 |
| IV. Logistic regression | +0.002 | 0.521 | 0.690 | −0.035 | 0.166 | 0.213 |
| Always-HIGH | −0.111 | 0.016 | **0.049** | −0.108 | 0.019 | 0.056 |

### H3: the six comparators

| Comparator | L1 diff | Holm p | L2 diff | Holm p |
|---|---|---|---|---|
| Naive persistence | −0.143 | **0.001** | −0.140 | **0.002** |
| LR news-only | −0.129 | **0.015** | −0.178 | 0.068 |
| LR government-only | −0.013 | 0.690 | −0.040 | 0.258 |
| LR combined (no news) | +0.002 | 0.690 | −0.035 | 0.258 |
| LGBM government-only | −0.037 | 0.081 | −0.041 | 0.114 |
| LGBM news-only | −0.083 | **0.014** | −0.054 | 0.258 |

**H3 is not rejected.** REF+news is not significantly better than all six.
- At Lead 1 it beats persistence and the two news-only models.
- It does not significantly beat the government-only or combined logistic regressions, or the government-only
  LightGBM.

## 5. Seal

- **File:** `sealed_prospective_REFNEWS.csv`, SHA-256 `cc1ff11b589256746a2503160c22d5a25ee1f0272b6fa5900b6d4b9ff9db5216`,
  recorded in `SEAL_LEDGER.md`.
- **Forecast:** issued 2026-10-01, Lead 2, target 2027-Q1, P(HIGH) = **0.869**, **HIGH**. It equals the stored
  IMPROVE_V2 REF+news forecast for that origin and lead.
- **Sealed on 2026-11-03, after the results were known.** The file and the ledger say so. It is prospective, because
  2027-Q1 has no SWS round yet, but it is not an independent test of the development results.
