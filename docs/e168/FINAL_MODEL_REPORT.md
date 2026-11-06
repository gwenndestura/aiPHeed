# Final model report: LightGBM-only (E168)

## Decision: **IMPROVED BUT NOT ACCEPTED. E158 stays in production.**
- **The final algorithm is LightGBM**, as required: a survey baseline, plus LightGBM forecasting the change, plus a calibration layer chosen on training data.
- **It improves E158 on point estimates:** Lead 1 is 75.0 % vs 73.6 %, Brier 0.123 vs 0.134, HIGH recall 0.88 vs 0.84. Lead 2 is 77.8 % vs 73.6 %.
- **The gains are not significant:** Brier −0.011 [−0.033, +0.011]; McNemar p = 1.0.

**Acceptance (fixed in advance):**

| Requirement | Result |
|---|---|
| E156 C1–C6 at Lead 1 | ❌ C1 (54/72, needs 56); C4 (0.76 [0.55, 0.90]) |
| No leakage | ✅ 0.0 change |
| Real inputs beat shuffled | ❌ −0.0003 [−0.015, +0.018] |
| Non-inferior to E158 | ✅ |

**Maximum reliable lead: 0.**

## Objective-aligned metrics (Lead 1, n = 72)
| | Accuracy | Precision (HIGH) | Recall (HIGH) | F1 (HIGH) | Macro F1 |
|---|---|---|---|---|---|
| E158 | 73.6 % | 0.58 | 0.84 | 0.69 | 0.73 |
| **E168 LightGBM** | **75.0 %** | **0.60** | **0.88** | **0.71** | **0.75** |
| E166 (not LightGBM-only) | 76.4 % | 0.61 | 0.92 | 0.73 | 0.76 |

## What LightGBM-only established
1. **The best LightGBM is the most constrained** (3 leaves, 150 trees, strong regularisation) on a survey-history baseline. Flexible LightGBM overfits province noise.
2. **Market and prices is the one trigger group with a demonstrated contribution** (−0.0073 [−0.0154, −0.0001]). That information is about timing, not province-specific.
3. **No calibration layer passes C4.** Linear recalibration comes closest (0.84 [0.61, 0.99]). The cause is the round-level shift that the 2018/2019 origins could not see.
4. **C1 is a sample-size limit** (about 46 effective rows).

## Supplementary output (not validated forecasting)
The current-period relative-risk view can be shown **as context, not as a validated forecast**:
- all five provinces LOW;
- the Quezon evidence note;
- LGU-v2.

## Data needed to accept a LightGBM model
- ENNS 2022 or later provincial HFIAS (the frozen E158/E166 forecasts are sealed; E168 can be sealed next);
- provincial employment and remittances;
- PSA 2025 regional consumption.

**Companion documents:**
- `LIGHTGBM_ROOT_CAUSE_AUDIT.md`
- `LIGHTGBM_OPTIMIZATION_REPORT.md`
- `LIGHTGBM_CALIBRATION_REPORT.md`
- `TARGET_AND_DATA_VALIDITY_REPORT.md`
- `ENNS_2022_VALIDATION_REPORT.md`
- `LIGHTGBM_FEATURE_ABLATION_REPORT.md`
- `MAX_RELIABLE_LEAD_REPORT.md`
