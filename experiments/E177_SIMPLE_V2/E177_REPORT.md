# E177: SIMPLE v2 training-only development (2026-11-07)

## Outcome B: no defensible improvement found
SIMPLE is preserved unchanged. A candidate was selected mechanically by the registered rule (C3, SIMPLE with stumps), but its
advantage is 0.0001 in Brier, about 1/100 of the seed-to-seed noise. It is not adopted as an improvement.

## 1. The decisive data fact
The 72 evaluation rows are the ENNS 2018/2019/2021 outcomes. Training rows reuse those outcomes as targets (same province, same
survey, different lead):

| Forecast | Training rounds | Training rows | Rows sharing an outcome with the 72 |
|---|---|---|---|
| ENNS 2018 / 2019 (Leads 1-2) | FNRI 2015 only | 156 | 0 |
| ENNS 2021 and every later issue (live) | FNRI 2015, ENNS 2018, ENNS 2019 (+2021) | 532+ | 376+ |

Under rule 3, the only labelled rows that may inform development are the 156 FNRI 2015 rows (NNS 2013 -> FNRI 2015, one survey
transition). Forward-in-time validation needs two or more rounds, so only region-grouped folds are possible.

## 2. Registered before running (`candidate_registry.csv`)
C0 SIMPLE (E173 rule) / C1 + Platt / C2 + temperature / C3 stumps; reference: E168's settings. Rule: lowest cross-fitted
out-of-fold Brier among candidates whose accuracy is not below C0; ties keep the simpler one. All calibration was fitted per fold
on the other folds only.

## 3. Training-only results (156 untainted rows, region folds; `training_only_validation.csv`)
| Candidate | Accuracy | Brier | ROC-AUC | Calibration slope |
|---|---|---|---|---|
| C0 SIMPLE (OH, 3 leaves, GOV) | 0.782 | 0.0825 | 0.770 | 0.77 |
| C1 + Platt | 0.744 | 0.0861 | 0.724 | 0.80 |
| C2 + temperature (lambda 0.75-1.0 by fold) | 0.782 | 0.0845 | 0.756 | 0.81 |
| C3 stumps (selected by rule) | 0.782 | 0.0824 | 0.767 | 0.84 |
| E168 settings (reference) | 0.744 | 0.0808 | 0.770 | 0.78 |

- Calibration did not improve with training-only fitting: Platt and temperature are both worse than C0 on held-out folds.
- C3 beats C0 by 0.0001 Brier, with the same accuracy and lower ROC-AUC. That is within noise.
- Stability (`model_stability.csv`): across 5 seeds the C0 score moves by 0.012 on average and 8 of 156 rows change class;
  E168's settings move by a similar amount but only 3 rows change class. SIMPLE is less stable, not more.
- On these rows E168's settings have the best Brier (0.0808) but lower accuracy (0.744), the same trade-off seen on the 72 rows.

## 4. Why a SIMPLE v2 cannot be made defensible here
1. Only one untainted survey transition (156 rows). Calibration or shrinkage for the later issues (2021, live) would have to be
   fitted on rows that share outcomes with the 72; rule 3 forbids that.
2. No candidate beats C0 by more than noise on the untainted rows.
3. A selected candidate cannot be evaluated legitimately: the 72 rows are inspected, and no independent provincial HFIAS rows
   exist (E174: 4 rows).

## 5. Answers
1. Outcome: **B**.
2. New LightGBM candidate developed legitimately? Developed and compared, yes (C1-C3); none is a real improvement.
3. Training-only? Yes: only the 156 FNRI 2015 rows, asserted in code; the 72 outcomes were never read.
4. Calibration improved? **No.** Platt +0.0036 and temperature +0.0020 worse in Brier.
5. More stable than SIMPLE? No candidate is meaningfully more stable; SIMPLE flips more classes across seeds than E168's settings.
6. Defensible? The process is; an improvement claim is not.
7. Unverified: everything about performance on new data. The E173 sealed comparison (SIMPLE vs E168) remains the test.
8. E168 and SIMPLE unchanged: **yes** (`PROTECTED_ARTIFACTS_CHECK.md`).
9. Protected files or Git state changed: **no**. Only `experiments/E177_SIMPLE_V2/` was created.
