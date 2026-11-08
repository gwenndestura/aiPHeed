# E132 frozen protocol: final methodology search (final master directive)

**Freeze.** This protocol was frozen **before** any E132 result was computed. Its SHA-256 is in `runner/PROTOCOL_SHA256.txt`.

**Scope and starting point.**
- Branch `aiPHeed/corrected-data-pipeline`; starting commit `c32e5bc`.
- Offline only: nothing in production, the dashboard, FIRI v2 or FIRI3 changes. Nothing pushed.

**Unchanged from E131, and never changed after results:**
- the target (SWS involuntary hunger, 4 areas, 2021-Q2 … 2026-Q3);
- the **primary tolerance**, 1.645 × the binomial SE from published margins (E131 §1);
- **the 75 % requirement**;
- the lead definitions (`target.py`);
- the reliability rules N1–N7;
- the evaluation sets: shared rows, and each model's own set where it has ≥ 8 observed quarters.

**Data status.** All 2021–2026 SWS values have been seen in earlier work. **Walk-forward results are development evidence.** The confirmatory test is prospective (§7).

## 1. Hypotheses (new relative to E128–E131)

| Id | Hypothesis | Model or analysis |
|---|---|---|
| H1 | Since SWS's 2025 change of respondent base (household heads → adults, documented in SWS releases), part of the quarter-to-quarter swing is a stable quarter-of-year pattern (design or season) that can be learned from past data only | **SEAS-LLM**: measurement-aware local level, plus extra level variance at the documented 2025-Q2 break, plus a pooled quarter-of-year effect estimated only from post-break observations available at the issue date and shrunk toward zero (n_q / (n_q + 2)) |
| H2 | Combining forecasts beats the individual models | **ENS**: equal-weight mean of PERSIST, LLM and SEAS-LLM |
| H3 | Income-side and price-affordability drivers explain part of the change that the level model misses | **HYB-RIDGE**: LLM forecast + ridge (alpha 10) correction on theory features: area rice affordability (rice ÷ all-items CPI, 4-quarter change), area real-wage growth, area unemployment change |
| H4 | A nonlinear learner on the level-model residual uses all five groups better than trees on raw changes | **HYB-LGBM**: LLM forecast + LightGBM correction (E131 fixed settings) on H + A + C + E + N + V + the new income features |
| H5 | Area-level income data matter | New area features: real average daily basic pay growth (pay ÷ regional all-items CPI) and regional unemployment rate. PSA SDG 8.5.1.p1 and 8.5.2, annual by region, 2021+, available from 30 June of the next year (rule). Added to the E groups of RIDGE-ALL, LGBM-ALL and PSA-ONLY. |
| D1 (diagnostic) | How much of the error is unforecastable survey noise, and how much true change | **ORACLE-LEVEL** (ex-post Kalman-smoothed true level at the target) and **ORACLE-NOW** (ex-post smoothed level at the latest observed quarter). Not forecasts and never candidates. |
| D2 (diagnostic) | How well do two independent hunger surveys agree? | SWS against OCTA (Balance Luzon, about 9 matched quarters): MAE, mean difference, share within the SWS primary tolerance |

## 2. Issue policies

- **P-DASH (primary):** issue at the quarter start (`target.py`).
- **P-REL (secondary):** an operational *re-issue* after each SWS release within the dashboard quarter. Lead definitions are unchanged; this is a design option that would need owner approval to serve.

## 3. Models compared

**New models (E132):** SEAS-LLM, ENS, HYB-RIDGE, HYB-LGBM.

**Re-run unchanged from E131:** PERSIST, CLIM, LLM, DLLM, RIDGE-H, LGBM-H, RIDGE-ALL, LGBM-ALL, PSA-ONLY, NLP-ONLY. The ALL and PSA sets gain the H5 income features.

**Evaluation:** same code paths and training-row rules as E131. Learned and hybrid models need ≥ 20 training rows and ≥ 8 training target quarters.

## 4. Evaluation (unchanged rules)

**Reported, per model, lead and policy:**
- MAE, RMSE and bias;
- **share within the primary tolerance;**
- direction accuracy;
- 80 % coverage;
- results by area, by level tercile, and on sharp increases.

**Reliability:** N1–N7, with the N3 baselines PERSIST, CLIM, PSA-ONLY, NLP-ONLY and RIDGE-ALL.

**Maximum reliable lead:** consecutive leads from Lead 1.

**Ablation:** HYB-RIDGE and HYB-LGBM each without their price, income and other groups.

**Selection rule (fixed here).**
- The **E132 candidate** is the model with the highest Lead-2 share within tolerance under P-DASH on the shared rows, among every non-baseline model (E131 and E132). Ties go to the lower MAE.
- It counts as validated only if N1–N7 pass at Lead 2.
- No result-driven change to models, features or rules.

## 5. Provincial layer

No new provincial measurement exists (E130 / E131). The final provincial outputs combine:
- measured PFDR 2021/2023 with CIs;
- the E131 price-versus-income decomposition;
- labelled model-based estimates from the E132 candidate × E131 relative food deprivation, with uncertainty.

No province value is presented as a measurement or as a validated forecast.

## 6. Integrity

- Study window 2021+. Every OpenSTAT query is limited to 2021+ periods.
- No SWS copies into provinces.
- CPI, poverty and FIRI are never targets.
- No searches for PSA, BSP or SWS series values.
- Deviations go to `DEVIATIONS.md`.
- Local commits only.

## 7. Prospective seal

| Item | Definition |
|---|---|
| Issued | 2026-11-01, with all information published by then |
| Targets | 2026-Q4 … 2027-Q3 for the 4 areas |
| Models | Every E132 model's point forecast (and interval where defined) |
| Integrity | Write-once; hash recorded |
| Scoring | Primary criterion only (E131 Addendum 1) |
