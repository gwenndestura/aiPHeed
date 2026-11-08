# E148: mixed-frequency, survey-anchored quarterly forecast of provincial food insecurity. Protocol E148-P1

Locked before any E148 result is computed: `backend/data/e148/out/PROTOCOL_LOCK.json`. E147 and its sealed test are preserved unchanged. No 2021 HFIAS value has been read. The sealed file (SHA-256 `f15a1977…`) is opened only after E148's 2021 predictions are hashed.

## 1. Purpose

aiPHeed's research gap is that no quarterly provincial food-insecurity measurement exists. E148 forecasts every province every quarter, and it learns from the measurements that exist.

## 2. How sparse surveys train a quarterly model

**Learning.** Each measured outcome (province p, survey quarter T) becomes one training row per lead h. The inputs are what was public at the issue date, the first day of quarter T − h:

* The province's latest **published** survey (the anchor), and quarters since it.
* Each quarterly indicator now, and accumulated since the anchor (a MIDAS-style temporal aggregation).
* SWS area hunger: latest reading, change since the anchor, and the walk-forward E144 forecast for quarter T.
* Province characteristics.

LightGBM learns: **change in food-insecure households between the anchor and quarter T**.

    logit(p_pT) = logit(anchor_p) + LightGBM(inputs at T − h, h, quarters since anchor)

**Inference.** The inputs exist every quarter, so the same function runs every quarter. It is applied to quarters with no survey exactly as HungerMap applies a model where no survey exists (Martini et al., 2022). No intermediate label is created or trained on.

**Update.** When a new survey is published, it becomes that province's anchor.

**Why this is not E146.** E146 used a fixed link plus a province-shock model on point-in-time inputs. E148 learns one function directly on change, with accumulated exposure since the anchor, pooled across leads.

**Why this is not E147.** E147 has one row per survey pair at each lead, fitted separately per lead, and has no accumulated exposure, no stage-A input and no quarterly output.

## 3. Target

Food-insecure households (any-level HFIAS). HIGH = FNRI's published "High" or above (≥ 60 %). Radimer 2011 is a predictor only. FIES is never pooled. SWS is an input and an independent check, never a provincial label.

## 4. Timing

* Lead h target: T. Issue date: first day of quarter T − h. In Q4 2026, Lead 1 is Q1 2027.
* Input release rules: `app/e147/features.py`, as of the issue date.
* **Anchor availability.** A survey may anchor only from 6 quarters after its reference quarter, an approximation of FNRI's dissemination delay. Sensitivity at 8 quarters is reported on development rows.
* Leads 1 to 8 are evaluated. Stage-A input exists for leads 1 to 4 and is missing beyond them.

## 5. Inputs

| Group | Inputs | Finest resolution in this history |
|---|---|---|
| Market and prices | Food and rice CPI year on year; food threshold | Province, annual; stale after 2018 |
| Climate stress | Soil moisture, rain, cyclones, production: now and since anchor; ONI | Province quarterly; ONI national |
| Employment | Unemployment rate, year-on-year change, change since anchor; regional rate from 2021 | **National quarterly**; region annual from 2021 |
| OFW remittances | Remittances year on year, mean since anchor; quarterly year on year from 2022 | **National** |
| Poverty and vulnerability | Poverty, subsistence, gap, density | Province, by release round |
| News/NLP | FSSI, attention, within-province change, 6 BERTopic shares, now and FSSI since anchor | Province |
| History | Anchor, gap, distance from region's latest mean, Radimer 2011, SWS terms | Province or area |

All five groups are real inputs. No influence is forced. Employment and remittances cannot separate provinces on their own; the model can only interact them with province traits. Province-level history for them is a named data blocker.

## 6. Arms, on identical rows

| Arm | Definition |
|---|---|
| **Q-G** | Government + history + SWS |
| Q-GN | Q-G + raw news |
| **Q-GNB** | Q-G + bias-corrected news |
| Q-noSWS | Q-G without any SWS input. Used for independent checks |
| Q-frozen | Q-G with inputs frozen at the anchor's release quarter. **Tests whether quarterly updating adds anything** |
| N | LightGBM on news only |
| DRIFT | Anchor + training mean change per quarter |
| B1 PERS | Naive persistence of the anchor |
| B2 LR-PSA | Logistic, poverty |
| B3 LR-NLP | Logistic, news |
| B4 LR-ALL | Logistic, all inputs |

**Settings.** E140 `GBC` parameters; tree count chosen inside training folds grouped by region. σ per lead from out-of-fold residuals in training.

**Origins.** Tests: O2 2018, O3 2019, F **2021 sealed** (25 provinces). **A separate model is fitted per test and lead, on outcomes already released at that issue date** (reference quarter + 6 ≤ issue quarter), each with its own earlier anchor. So at lead 1, 2018 and 2019 are predicted from 2015 outcomes only, and 2021 from 2015, 2018 and 2019. Where no outcome is yet released, the forecast is reported as unavailable (O2 at leads 7 and 8). Training rows use all leads 1 to 8 for those outcomes.

**Selection, on development rows only.** Default Q-G. Q-GNB replaces it only if O2 + O3 Brier at lead 1 improves with a 95 % region-bootstrap interval below 0.

## 7. Evaluation

### A. Survey-anchored backtest, per lead
Accuracy, precision, recall, F1, AUC-ROC, Brier, ECE, confusion matrix, false-negative rate, false-alarm rate. Always-HIGH and always-LOW beside them. By province where measured.

**Reliability (all required):**
* R1 accuracy ≥ 0.75
* R2 AUC ≥ 0.70
* R3 recall and precision ≥ 0.50
* R4 Brier below persistence, 95 % region-bootstrap interval below 0
* R5 ECE no higher than the 95th percentile under perfect calibration at this n
* R6 predicted and measured change correlate, interval lower bound above 0

**Maximum reliable lead** = the largest h with every lead to h passing on the 2021 test. It is 0 if lead 1 fails.

### B. Does quarterly information add value?
Q-G minus Q-frozen on Brier, per lead. A claim needs a 95 % interval below 0 at lead 1.

### C. Independent checks on quarters with no survey
None of these is a direct validation of a province-quarter.

1. **Temporal.** Q-noSWS, which never sees SWS, is run every quarter. Its area averages are compared with **measured** SWS hunger the next quarter: Spearman of quarter-to-quarter changes, area and issue block bootstrap. Pass: 95 % lower bound above 0.
2. **Spatial.** Leave-one-region-out change correlation in training.
3. **Sensitivity.** Forecast change under anchor lag 8; 20 % masked inputs.

### D. News
Q-GNB minus Q-G, lead 1 to 4, Holm. A claim needs Holm pass at lead 1, on 2021, and real news better than ≥ 95 % of 30 wrong-province placebo draws. Results by coverage tercile. Attribution audit reported.

### E. Five distinct provincial forecasts
Forecast spread across Cavite, Laguna, Batangas, Rizal and Quezon against forecast error. Spearman of forecast and measured values within Luzon. A difference is meaningful only when it exceeds the uncertainty.

## 8. Wording fixed in advance

* "Forecast for a quarter with no survey" is an **estimate** with an interval, supported by the checks in 7C, and never "validated for that quarter".
* Reliability refers to measured survey rows.
* If 7C.1 passes, the wording is "movement of the quarterly series tracked measured area hunger". If it fails, "the quarterly movement between surveys has no independent support yet".
* Production and the dashboard change only after the gates pass and the owner approves.

## 9. Limits stated in advance

One sealed test round, 25 provinces, one pandemic year; 6-year gap from anchor to 2021; national employment and remittance history; survey quarter approximated as Q3; survey SE approximated for 2021 at 3 points.
