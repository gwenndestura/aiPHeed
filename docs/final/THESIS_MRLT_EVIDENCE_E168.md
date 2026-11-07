# E168 against the thesis reliability rule (Chapter III, Algorithm 3 and Section 3.4.4)

Prepared 2026-11-07.

**Sources:**
- Thesis: `THESIS 2 (11).pdf`, Section 3.4, Algorithm 3 (LightGBM Lead Time Discovery), Algorithm 4, and Section 3.4.4.
- Data: the frozen E168 forecasts in `backend/data/e168/out/all_rows.csv` and `all_rows_l3_8.csv`, compared with the observed outcomes in `backend/data/e158/out/oof.csv`.
- Script: `backend/app/e168/thesis_metrics.py`; output: `backend/data/e168/out/thesis_metrics.json`. Nothing was refitted or re-selected.

## 1. The rule as the thesis states it

| Item | Thesis text (Algorithm 3 / Section 3.4.4) |
|---|---|
| Horizons | k = 1 to 8 quarters |
| Validation | Walk-forward expanding-window cross-validation, forecast gap = k, minimum 8 training quarters |
| Stopping metric | **Mean fold accuracy** across all folds, compared with 75 % |
| Stop | "When accuracy first drops below 75%, the search will halt and returns the last passing k as the Maximum Reliable Lead Time" |
| Final-model targets (Algorithm 4) | F1 ≥ 0.75 and AUC-ROC ≥ 0.80 |
| Publication rule (Section 3.4.4) | "Any lead time or model configuration that does not clear these thresholds will not be published to the dashboard" |

## 2. E168 metrics at each lead

**Validation set:** 72 province forecasts made chronologically, as of each issue date, for three survey rounds. Each round is one fold:
- ENNS 2018: 22 provinces
- ENNS 2019: 25 provinces
- ENNS 2021: 25 provinces

At Leads 7–8 only 50 rows exist, because no 2018 forecast can be made that early. HIGH means HFIAS moderate+severe ≥ 50 %. Precision, recall and F1 are for the HIGH class.

| Lead (quarters ahead) | Mean fold accuracy | Pooled accuracy | Precision | Recall | F1 (HIGH) | Weighted F1 | AUC-ROC | Persistence mean fold accuracy |
|---|---|---|---|---|---|---|---|---|
| 1 | **74.7 %** | 75.0 % | 0.595 | 0.88 | **0.710** | 0.756 | 0.891 | 62.4 % |
| 2 | 77.4 % | 77.8 % | 0.629 | 0.88 | 0.733 | 0.783 | 0.893 | 62.4 % |
| 3 | 74.5 % | 75.0 % | 0.600 | 0.84 | 0.700 | 0.756 | 0.873 | 62.4 % |
| 4 | 72.8 % | 73.6 % | 0.588 | 0.80 | 0.678 | 0.742 | 0.860 | 62.4 % |
| 5 | 71.3 % | 72.2 % | 0.571 | 0.80 | 0.667 | 0.729 | 0.849 | 62.4 % |
| 6 | 68.5 % | 69.4 % | 0.541 | 0.80 | 0.645 | 0.702 | 0.837 | 62.4 % |
| 7 | 70.0 % | 70.0 % | 0.536 | 0.88 | 0.667 | 0.707 | 0.783 | 64.0 % |
| 8 | 66.0 % | 66.0 % | 0.500 | 0.94 | 0.653 | 0.662 | 0.813 | 64.0 % |

**Fold accuracies at Lead 1:**
- ENNS 2018: 68.2 %
- ENNS 2019: 76.0 %
- ENNS 2021: 80.0 %

## 3. Applying Algorithm 3

| k | Mean fold accuracy | Decision |
|---|---|---|
| 1 | 74.7 % | **Below 75 %, so the search halts** |
| 2–8 | not considered | The search has stopped |

**Maximum Reliable Lead Time under the thesis rule: 0 quarters.** No lead time qualifies.

- **Lead 1 misses by 0.3 points.** The 75.0 % figure reported earlier is the pooled accuracy (54 of 72 rows). The thesis specifies the mean of the fold accuracies, which is 74.7 %. Choosing the pooled figure now, after seeing both, would mean changing the rule after the results.
- **Lead 2 (77.4 %) does not rescue the result.** Algorithm 3 stops at the first failure.
- **F1 for the HIGH class is 0.710 at Lead 1, below the 0.75 target.** Weighted F1, the objective named in Algorithm 4, is 0.756. AUC-ROC (0.891) clears 0.80 at every lead from 1 to 6.

## 4. What the evidence does support

- **E168 ranks HIGH and LOW provinces well.** AUC-ROC is 0.84–0.89 at Leads 1–6, against 0.83 for persistence.
- **E168 is better than reusing the latest survey** at Leads 1–6. Mean fold accuracy is 12–15 points higher, and the Brier difference CI is below 0 (`lead_horizon.json`).
- **HIGH provinces are rarely missed.** Recall is 0.80–0.88. Precision is low (0.54–0.63): roughly two in five HIGH alerts are false alarms.

## 5. Differences from Algorithm 3 that must be stated in Chapter IV

1. **Folds are survey rounds, not quarters.** HFIAS is measured only in ENNS survey years, so there are 3 folds rather than one per quarter, and 72 province rows rather than the 120 described (5 provinces × 24 quarters).
2. **The 72 validation rows are 72 different provinces across the Philippines, not the five CALABARZON provinces.** Each round contributes different provinces.
   - Only 5 rows are CALABARZON provinces. All 5 are LOW, and both E168 and persistence get all 5 right, so they cannot show CALABARZON skill.
   - 65.3 % of the rows are LOW, so always predicting LOW would score 65.3 %.
3. **The model is a constrained LightGBM.** It predicts the change from the latest survey, using 3 leaves, monotone signs and a calibration layer. Algorithm 3 describes a default LightGBM classifier on the 45-feature matrix.
4. **The label is HFIAS moderate+severe ≥ 50 %.** Section 3.5 describes a CPI-based food stress label.

## 6. Thesis decision-cutoff step tried (E172)

The thesis cutoff step (Section 3.5, cutoff from out-of-fold scores) was applied with training rows only (docs/e172). It chose cutoffs of 0.30–0.475 and lowered Lead-1 mean fold accuracy to 63.3 %. E168 (cutoff 0.5) stays.

## 7. Conclusion for the thesis

On the thesis's own metrics, **E168 does not establish a reliable lead time**:
- Mean fold accuracy at Lead 1 is 74.7 % (threshold 75 %).
- HIGH-class F1 is 0.71 (target 0.75).

Under Section 3.4.4, a lead that does not clear these thresholds is not published to the dashboard. The dashboard currently shows E168 as "approved" under the owner-defined acceptance (pooled accuracy). That conflicts with Section 3.4.4 and must either be changed back to "validation pending" or reported in the thesis as a deliberate deviation from Algorithm 3, approved by the adviser.

A defensible thesis finding is:
- *LightGBM forecasts provincial HFIAS risk better than the latest survey up to 6 quarters ahead (AUC 0.84–0.89).*
- *It reaches 74.7 % mean fold accuracy at one quarter ahead, just under the 75 % reliability threshold, so the Maximum Reliable Lead Time under Algorithm 3 is 0.*
- *Three survey rounds are the binding limit.* The 2022 forecasts are sealed (`f8228fae`) and can be scored when FNRI publishes provincial results.
