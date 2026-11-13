# 02 — Historical validation by survey round (rolling origin)

Script: `scripts/rel_eval.py`. Evidence: `evidence/REL_by_round.csv`, `REL_rows_L1to5.csv`, `LEAK_origin_check.json`.

## 1. Design
- **Folds:** one walk-forward fold per ENNS round. Each fold trains only on rounds that were released (6-quarter lag) before the forecast origin.

| Test round | Trained on | Training gaps (quarters) | Test gap at Lead 1 |
|---|---|---|---|
| ENNS 2018 | FNRI 2015 | 8 | 12 |
| ENNS 2019 | FNRI 2015 (2018 not yet released) | 8 | 16 |
| ENNS 2021 | FNRI 2015, ENNS 2018, ENNS 2019 | 8–20 | 24 |

- **Information at the origin:** inputs are as-of panels (published before the origin), and anchors come from released rounds only. These were rebuilt per origin by the cached fold builder (`run_qs.load`).
- **Leakage check (new):** across all 110 fits, every training round's reference quarter + 6 ≤ the origin, the test round is never in training, and the origin precedes the test quarter. Result: **0 violations** (`LEAK_origin_check.json`).
- **Seeds:** 168, 1, 2, 3, 4; the 5-seed mean probability is scored at the fixed 0.50 cut-off.
- **Genuinely independent evaluation periods: 3** (2018, 2019, 2021).
  - Leads 1–5 re-forecast the same 72 province-rounds from earlier origins, so they are not extra independent periods.
  - Within a round, provinces share the same national shocks.

## 2. Results at Lead 1

| Round | n | HIGH | Accuracy | HIGH recall | HIGH precision | FP | FN | Always-LOW accuracy | Persistence accuracy | Persistence recall |
|---|---|---|---|---|---|---|---|---|---|---|
| ENNS 2018 | 22 | 8 | 0.864 | 8/8 | 0.727 | 3 | 0 | 0.636 | 0.591 | 8/8 |
| ENNS 2019 | 25 | 13 | 0.840 | 11/13 | 0.846 | 2 | 2 | 0.480 | 0.760 | 12/13 |
| ENNS 2021 | 25 | 4 | 0.880 | **1/4** | 1.000 | 0 | 3 | **0.840** | 0.520 | 4/4 |
| Pooled | 72 | 25 | 0.861 | 20/25 | 0.800 | 5 | 5 | 0.653 | 0.625 | 24/25 |

- In **2021**, FINAL's accuracy (0.88) is only one row above always-LOW (0.84).
- FINAL missed 3 of the 4 HIGH provinces. The 2021 accuracy is therefore not evidence of HIGH-risk skill.

## 3. Reproduction of the existing reported metrics

| Reported earlier (11-13 standalone / completion audit) | Reproduced here | Match |
|---|---|---|
| Accuracy 0.861 | 0.8611 | yes |
| Precision 0.80, recall 0.80 (20/25), F1 0.80 | 0.800 / 0.800 / 0.800 | yes |
| AUROC 0.898 | 0.8979 | yes |
| Balanced accuracy 0.847 | 0.8468 | yes |
| Cox p 0.41 | 0.406 | yes |
| 2021 HIGH recall 1/4 | 1/4 | yes |
| "Robust" max lead 4, thesis Algorithm 3 max lead 5 | Same rules give 4 and 5; see `05_STABILITY_AND_MAX_LEAD.md` | yes |

- The fold fits used for SHAP and ablation reproduce the stored FINAL probabilities to **2.2e-16** (`CONTRIB_reproduction.json`).
- **Discrepancies:** none among FINAL's own figures.
- **Do not mix up FINAL and FINAL-ETMIX.** The ETMIX reports also show Lead-1 accuracy 0.861, but ETMIX's precision (0.778), recall (0.84) and AUC (0.903) are different.

## 4. What this establishes, and what it does not
- **Establishes:** under a leakage-free computational design, FINAL's retrospective Lead-1 forecasts are correct for 62 of 72 province-rounds.
- **Does not establish independent validity.** These 72 outcomes were scored repeatedly while the FINAL family was developed (about 45 configurations, 11-11 to 11-13). The researcher has seen them, so the result is **retrospective**.
