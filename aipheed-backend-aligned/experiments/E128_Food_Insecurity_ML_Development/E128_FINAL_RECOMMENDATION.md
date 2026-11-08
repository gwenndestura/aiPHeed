# E128 final recommendation

## Classification: **DEVELOPMENT WITH LIMITATIONS**

**Done**
- All five models were trained with expanding-window walk-forward at Leads 1–4, on two targets (40 model × target × lead cells).
- 264 fold model artifacts were saved; there are 330 traceable out-of-sample predictions.

**Result.** **No candidate meets the frozen R1–R7 reliability criteria at any lead.** No maximum reliable horizon is established, and the result is **inconclusive**.

**Why not BLOCKED.** Evaluation was carried out, but it can only show the absence of established reliability, not its presence. The binding limits are:
- 20 independent regional quarters;
- a target saturated since 2023-Q4.

**Production.** Nothing changed: no served model, dashboard, `/api/v1/final/` route, FIRI v2 or FIRI3 change. Local commits only.

## Answers

### Target and data

1. **Is the target valid for the level predicted?**
   - **Regional: yes, as a proxy.** SWS Balance Luzon contains CALABARZON but is not CALABARZON.
   - **Provincial and LGU: no.** No local labels exist. T43c's provincial class rests on the copied regional value, so it was not used (`E128_TARGET_VALIDITY_AUDIT.md`).
2. **Independent target observations:** **20 quarters** (2021-Q2 .. 2026-Q3). 2021-Q1, 2022-Q1 and 2025-Q1 have no round.
3. **Observations per lead:**

   | Target | Labelled pairs (L1 / L2 / L3 / L4) | Outer evaluation rows |
   |---|---|---|
   | T1 | 20 / 19 / 18 / 17 | 13 / 8 / 7 / 6 |
   | T4 | 18 / 17 / 17 / 16 | 11 / 8 / 7 / 6 |

4. **Eligible features at each issue date:** 25 point-in-time features (`E128_FEATURE_AVAILABILITY_AUDIT.csv`).
   - From 2022-Q2 onward, all except production (from 2022-Q3).
   - Before that, only hunger history, ONI, typhoons, unemployment, El Niño and news.
   - The same set at every lead.
5. **Sufficient for defensible training?** **No.**
   - 6–18 training rows per fold for 25 features.
   - 20 quarters in total.
   - R1 (≥ 40 rows) cannot be met by one regional series.

### Model training and comparison

6. **All five trained?** **Yes.** LightGBM, persistence, PSA-only, NLP-only and Logistic Regression, with in-fold tuning (`E128_MODEL_TRAINING_RESULTS.csv`, `E128_MODEL_ARTIFACT_MANIFEST.csv`).
7. **Best at Lead 1:**
   - T1: persistence (accuracy 0.846, Brier 0.154).
   - T4: PSA-only (0.909, 0.156), not significantly better than persistence.
8. **Best at Lead 2:**
   - T1: persistence (8 / 8, all HIGH).
   - T4: no model above chance; CLIM has the lowest Brier.
9. **LightGBM vs naive persistence:** **no.** Worse at every T1 lead.
10. **LightGBM vs PSA-only:** **no** (not significant at any lead).
11. **LightGBM vs NLP-only:** **no.**
12. **LightGBM vs Logistic Regression:** **no meaningful difference.** The only Holm-significant case (T1 Lead 4) compares two 0 %-accurate models.
13. **Do all five trigger groups contribute?** **No.**
    - Removal effects change sign across leads, and none is stable (`E128_FEATURE_GROUP_ABLATION.csv`).
    - Employment/OFW shows small, consistent removal costs at T4 (+0.004 to +0.033 Brier). These are inside the seed noise of about 0.03–0.05, so this is **weak, not demonstrated**.
    - Poverty is **not testable**: there is no time-varying regional series.
14. **Why previous models underperformed:** in order,
    1. too few independent quarters;
    2. a saturated or noisy target;
    3. regime shift between the training and evaluation years;
    4. national or lagged predictors with no stable relation to hunger.

    Architecture is not the bottleneck (`E128_PREVIOUS_EXPERIMENT_FAILURE_ANALYSIS.md`).

### Reliability and generalization

15. **Overfitting:** **yes, severe.**
    - Training accuracy 0.86–1.00 vs outer 0.00–0.88.
    - Outer log-loss up to 6× inner log-loss.
16. **Generalizes across unseen periods:** **no.** LightGBM fails in the high-hunger regime (Lead 1 0.55, Lead 4 0.00), where persistence is right.
17. **Class bias:** **yes, against HIGH.** False negatives in the worst hunger quarters; LOW cannot be evaluated beyond Lead 1 under T1.
18. **Calibration acceptable:** **no.** LightGBM's Brier is worse than climatology at T1 Leads 1 and 4. Probabilities below 0.2 were given to quarters that were all HIGH.
19. **Does Lead 2 satisfy every criterion?** **No.**
    - LightGBM T1 Lead 2 fails R1 (8 rows), R3 (not evaluable, 0 LOW rows), R4 (0.875 vs persistence 1.00) and R5 (Brier 0.082 vs 0.000).
    - T4 Lead 2 fails all seven criteria: accuracy 0.375, balanced accuracy 0.367.
20. **Are Leads 3 and 4 reliable?** **No.**
21. **First unreliable lead:** **Lead 1.**
22. **Failed criteria at each unreliable lead:** see `E128_FIRST_UNRELIABLE_LEAD_ANALYSIS.md`.
    - LightGBM T1: Lead 1 R1, R2, R4, R5, R6, R7; Leads 2–3 R1, R3, R4, R5; Lead 4 all seven.

### Maximum reliable lead time

23. **LightGBM:** **none established** (0 quarters, 0 months).
24. **Baselines:** persistence, PSA-only, NLP-only and Logistic Regression: **none established**.
25. **Does LightGBM extend the horizon?** **No.**
26. **Independent evaluation observations:**
    - T1: 13 / 8 / 7 / 6 quarters at Leads 1–4.
    - T4: 11 / 8 / 7 / 6.
27. **Confirmed, provisional or inconclusive:** **inconclusive.**
28. **Furthest defensible horizon:** **none at the regional level with 2021–2026 data** (0 quarters).

### Final research decision

29. **Suitable for further development?**
    - **Not as a quarterly supervised classifier on the current target.**
    - Worth keeping only as a **prospective** exercise: seal forecasts each quarter and score them as SWS publishes. That grows the unseen sample without reusing inspected rows.
30. **Improvements supported by evidence:**
    1. **A real local target.** Provincial or LGU food-insecurity measurements with dates: CBMS, FNRI ENNS, or DSWD/DA administrative data. This is the only change that addresses the binding limit.
    2. **More independent quarters.** Prospective accumulation. Pre-2021 SWS history needs an owner decision to widen the study window; E114 showed it carries level-forecast skill.
    3. **Simpler references** (damped mean reversion, persistence) as the operational forecast while the sample grows. E114 and E117 found they match or beat LightGBM.
    4. **Verified publication dates** for CPI and production. These are partly rule-based today.
31. **Limits on longer-term forecasting:**
    - 20 regional quarters, two hunger regimes, ±6-point sampling error;
    - no provincial outcome;
    - national or lagged predictors;
    - persistence dominance under a saturated threshold.
32. **Recommended for production integration?** **No.** No candidate passed the frozen evaluation, and none has been approved.
    - The dashboard should not present any model-based food-insecurity horizon as validated.
    - It may show the latest SWS reading and the FIRI3 composite for what they are.
