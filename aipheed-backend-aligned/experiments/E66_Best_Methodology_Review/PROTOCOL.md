# E66 protocol: best defensible aiPHeed methodology for Objectives 1–4

**Date frozen:** 2026-10-19, before any E66 arm is scored. The SHA-256 of this file (LF-normalised) is stored in `runner/PROTOCOL_SHA256.txt`; every runner checks it.
**Branch:** `aiPHeed/best-model-methodology-review` (from `e62-final-audit` @ fee3b8f).
**Requirement basis:** Chapter I §1.5 only (objectives quoted from E62 `out/thesis_p1_40.txt`). Chapter I sets no accuracy threshold; none is applied.

## 1. Evidence status declared in advance

- All 50 evaluation rows (targets 2024-Q2..2026-Q3, 10 quarters, 5 provinces) were examined by E56–E65. **Every E66 metric is development evidence.** No quarter is unseen.
- The first independent evidence is the frozen 2026-Q4 / 2027-Q1 forecasts (E36/E38/E55/E56/E58/E64 seals). E66 does not reseal or alter them.
- Study window 2021-Q1..2026-10-14 (authorized). No pre-2021 row is loaded. No PSA/BSP/SWS web search is made.

## 2. What E66 does

1. **Scoreboard (r1):** every sealed row-level prediction set from E55, E57, E58, E60, E61, E64, E65 is re-scored by one scorer on the same rows and labels (T43 from E58 `data/events.csv`). Two common sets: the 50-row E57 set and the 45-row set (targets 2024-Q3..2026-Q3) where the Chapter I baselines (E55 B1–B7) exist. No sealed file is modified; the sealed SHA-256 files are verified first.
2. **New arms (r2), defined here before scoring:**
   - **N1 LR-MATCHED:** L2 logistic regression (C = 1.0, standardised, median imputation + missing indicators, fitted on training rows only at each origin) for P_price on `dfood_0.0`, `dgap_0.0` (flat-price projected food inflation and gap minus the province thresholds) plus the E56 "market" columns; trained on as-of PS labels with the E56 training frame `F.frame(d, X, B, t, "AS")`. P = E56's sealed P_hunger × N1 P_price. This is Chapter I baseline IV with inputs matched to the LightGBM.
   - **N2 LR-PROJ:** the same learner on `dfood_0.0` and `dgap_0.0` only.
   - **N3 RW-HUNGER:** E56's sealed P_price × the E61 random-walk hunger part (E61 `tables/d2_hunger_variants.csv`, H2).
   - Both LR arms use exactly the E56 origins, training rows and cutoffs. No tuning.
3. **Layer evaluation (r3):** the price layer (P_price) of E56, E58-EW, N1, N2 and the CPI-projection rule is also scored against **PS** (provincial food-price pressure, the condition T43 reduces to when regional hunger > 11.3%) on the same 50 rows.
4. **Lead-time (r4):** E63 sealed predictions re-scored per lead; leads are never pooled.
5. **El Niño (r5):** province table for 2026-Q3/Q4/2027-Q1 from the served E58 record and E65 traces; a transparent **Climate Food-Stress Watch (CFSW)** rule (below) computed at every issue date 2021-10-01..2026-10-01 from information dated before the issue date, and described against later outcomes.
6. **LGU (r6):** 142-LGU audit and rank sensitivity.
7. **Target validity (r7):** descriptive statistics of T43, PS, regional hunger.

## 3. Comparison rules (fixed)

- Decision: HIGH if p ≥ 0.5 (warning arms: their own documented rule).
- Metrics: accuracy (Wilson CI), balanced accuracy, precision/recall HIGH, recall LOW, false alarms, missed HIGH, Brier, ROC-AUC (pooled), onset detection (E58 ONSET), quarter-level accuracy.
- Uncertainty: quarter-cluster bootstrap (2,000 draws, seed 66) of the paired Brier difference; quarter sign test.
- **"Better than X"** requires the paired Brier CI upper bound < 0 **and** sign-test p < 0.05 (the E27/E63/E65 rule), with Holm correction across the arms compared to the same reference.
- Late-regime split reported separately: targets 2024-Q2..2025-Q3 vs 2025-Q4..2026-Q3.
- A selection is never based on pooled accuracy alone.

## 4. Climate Food-Stress Watch (CFSW), defined before computing it

A separately named, rule-based **hazard watch**, not a food-insecurity probability and not a model input. At issue date O:
- **Hazard H:** a PAGASA El Niño Alert, El Niño Advisory, or El Niño Climate Advisory dated before O and not ended by a Final Advisory/termination before O (`enso_context.PAGASA_ENSO`; 2021–2022 statuses from E65 `PAGASA_STATUS`).
- **Household stress S:** the latest SWS regional hunger posted before O is above 11.3%.
- **Exposure E (province):** the latest provincial palay or corn production YoY known at O is ≤ −10%.
- Levels: **CLIMATE WATCH** = H and S; **CLIMATE WATCH + LOCAL EXPOSURE** = H and S and E; **NO CLIMATE WATCH** otherwise; **INSUFFICIENT DATA** if S cannot be determined.
- Missing E is reported as "exposure unknown", never as "no exposure".
- CFSW never changes P(HIGH), the decision or the map colour.

## 5. Selection rule for the recommended methodology

The recommended architecture is chosen by, in order: (1) target validity — each output must say what it measures; (2) leakage-free reproducibility; (3) no candidate better than the Chapter I proposed model (LightGBM) by rule §3 → the LightGBM stays the forecasting model required by Objective 2; a simpler arm that is better by rule §3 is recommended instead and reported; (4) rising-risk detection; (5) interpretability. The production default (E38) is not changed.
