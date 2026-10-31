# E131 thesis-objective assessment

| Objective (master directive) | Status | Evidence | What remains, and what would make it achievable |
|---|---|---|---|
| **1. Forecast food insecurity, not its indicators** | **Achieved for the target definition; partly achieved for forecasting** | Quarterly target = SWS measured hunger (4 areas); provincial target = PSA food deprivation (survey years). CPI, poverty and FIRI are never targets. X3a shows prices are not food insecurity: deprivation fell in 3 of 5 provinces while prices rose. | Forecasts exist (LLM, sealed) but are not validated |
| **2. ≥ 75 % numerical agreement** | **Not achieved** | Best Lead-2 share within the pre-registered tolerance is 0.50 (LLM). Required forecast error is about 2.0 points; achieved RMSE is 6.5–7.8. No model reaches 0.75 at any lead. | Predictors able to anticipate true hunger changes (none found in the five groups), or a reference with more predictable variation. A practical tolerance, if the owner sets one now, could apply to the **sealed prospective** forecasts only. |
| **3. Lead 2 reliable; maximum lead established** | **Not achieved.** The maximum reliable lead was established empirically: **none**. | No model passes N1–N7 at Lead 1, so Lead 2 has failed. LLM passes 4 of 7 rules at Lead 2. | Score the seal over the coming quarters; accumulate ≥ 10 unseen quarters |
| **4. All five trigger groups investigated** | **Investigated; contribution not demonstrated** | Point-in-time ablation: no group stable. Climate helps slightly at Lead 2. Market *hurts* ridge. The income side (X3a) is the missing driver. | A quarterly provincial or regional income or earnings series |
| **5. Defensible geospatial system** | **Partly achieved** | Provincial food deprivation is measured and explained at survey years (price against income). Quarterly provincial values exist only as labelled model-based estimates (sealed), and they depend on the deprivation measure. | CBMS 2024 LGU FIES (cross-sectional check); PSA's next provincial subsistence round |
| **6. Model appropriateness** | **Achieved as a comparison: LightGBM is *not* the best model** | LGBM-ALL Lead-2 MAE 6.13 against LLM 4.70 and persistence 5.28; it overfits (training 2.1 against 6.1 out of sample). The two-parameter measurement-aware LLM is the most defensible. | — |
| FIRI v2 families | **Accounted for** | A1–A3 → A; C1, C2 → C (C3, C4 provincial only); E1, E2 → E; N1 → N; V1 → V; H1 → H | — |
| Overfitting, bias, leakage, calibration, reproducibility | **Evaluated** | See `E131_RELIABILITY_REPORT.md` | — |
| Production | **Correctly not changed** | No component validated | — |

## Bottom line

**What E131 achieved:**
- a measured food-insecurity target framework;
- a sealed, measurement-aware forecasting candidate (LLM) whose 80 % intervals are calibrated at Lead 2;
- the first quantitative separation of price and income effects on provincial food deprivation, which answers the owner's CPI questions;
- an honest model comparison showing LightGBM is not superior.

**What it did not achieve:** 75 % numerical agreement, a reliable Lead 2, or a demonstrated contribution from the trigger groups.

**The exact reason** is that measured hunger changes by several points from quarter to quarter in ways no available predictor anticipates. In the provinces, the main driver (income) is not measured between survey rounds.

**Three legitimate paths forward:**
1. Score the sealed forecasts as SWS publishes.
2. Obtain income-side or provincial food-insecurity data (CBMS 2024; provincial LFS earnings).
3. Have the owner decide now, before scoring, whether a practical decision tolerance should apply to the prospective evaluation.
