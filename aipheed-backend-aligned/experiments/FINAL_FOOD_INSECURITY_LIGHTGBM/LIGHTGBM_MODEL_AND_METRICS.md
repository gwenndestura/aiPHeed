# The LightGBM model and its metrics

## 1. The model (FIL: Food-Insecurity LightGBM)

**Structure**
- One LightGBM regressor, refitted at every issue date (rolling origin).
- It is pooled over the 4 SWS areas and Leads 1–4: `area` and `lead` are features.
- Code: `runner/fi_lib.py`.

**What it predicts**
- **Target:** z = hunger in the target quarter minus the area's previous-year average (REF̂), using the readings known at the issue date.
- **Level forecast:** REF̂ + ẑ.
- **Class:** ELEVATED if ẑ > 0.
- **Probability:** Φ(ẑ/σ), where σ is the model's own past same-lead error.

**Inputs:** all 12 families (27 columns; `data/feature_map.csv`).

**Fixed settings**
- learning rate 0.03, min_child_samples 10, L2 = 5, feature_fraction 0.8;
- deterministic, seed 2026;
- `area` is categorical.

**Tuning (inside the training data only)**
- Grid: num_leaves {3, 7} × n_estimators {100, 300}.
- Configurations are compared on the 4 most recent training target quarters, each fitted on earlier targets only.
- The configuration chosen at each origin is in `out/results_primary.json` → `configs`.

**Issuing rule:** at least 40 training rows, 6 target quarters and 10 of each class. FIL is first issued at 2023-10-01, after 80 training rows; the last origin had 240.

## 2. Pre-registered success definition (`FINAL_PROTOCOL.md` §6)

**Accuracy** = the share of (area, target quarter) rows where the ELEVATED call is correct.

**75% target:** accuracy ≥ 0.75 (R2), plus R1 and R3–R8:

| # | Criterion |
|---|---|
| R1 | At least 10 target quarters and 30 rows |
| R3 | Balanced accuracy ≥ 0.70 and above every baseline |
| R4 | Brier score significantly better than persistence and climatology |
| R5 | Precision and recall ≥ 0.60 |
| R6 | Accuracy ≥ 0.60 in each third of the period |
| R7 | BL accuracy ≥ 0.70 |
| R8 | Level MAE ≤ persistence |

**Continuous errors** are reported in percentage points and are never converted into an "accuracy".

## 3. Primary results (2021+ study period; development evidence)

**Scope:** 4-area panel; targets 2023-Q4 … 2026-Q3. File: `out/predictions_primary.csv`.

| Lead | Rows / quarters | Accuracy | Balanced accuracy | Precision | Recall | F1 | AUC | Brier | TP / FP / TN / FN | BL accuracy | MAE (pp) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 44 / 11 | **0.318** | 0.371 | 0.417 | 0.179 | 0.250 | 0.469 | 0.298 | 5 / 7 / 9 / 23 | 0.09 | 5.72 |
| 2 | 40 / 10 | **0.400** | 0.423 | 0.562 | 0.346 | 0.429 | 0.411 | 0.313 | 9 / 7 / 7 / 17 | 0.50 | 6.84 |
| 3 | 36 / 9 | **0.444** | 0.465 | 0.600 | 0.391 | 0.474 | 0.358 | 0.307 | 9 / 6 / 7 / 14 | 0.44 | 7.99 |
| 4 | 32 / 8 | **0.500** | 0.506 | 0.600 | 0.474 | 0.529 | 0.482 | 0.297 | 9 / 6 / 7 / 10 | 0.50 | 8.02 |

**Baselines on the same rows** (accuracy / balanced accuracy / Brier)

| Lead | Persistence | MA2 | Climatology | Always ELEVATED | Logistic (all 12) | PSA-only | NLP-only |
|---|---|---|---|---|---|---|---|
| 1 | **0.614** / 0.603 / 0.244 | 0.500 / 0.487 / 0.252 | 0.409 / 0.362 / 0.265 | 0.636 / 0.500 / 0.364 | 0.591 / **0.625** / 0.285 | 0.591 / 0.504 / **0.242** | 0.318 / 0.371 / 0.388 |
| 2 | 0.550 / 0.555 / 0.246 | 0.450 / 0.445 / 0.255 | 0.300 / 0.247 / 0.275 | **0.650** / 0.500 / 0.350 | 0.425 / 0.492 / 0.358 | 0.600 / 0.511 / 0.259 | 0.300 / 0.346 / 0.332 |
| 3 | 0.361 / 0.500 / 0.250 | 0.528 / 0.530 / 0.252 | 0.306 / 0.239 / 0.275 | **0.639** / 0.500 / 0.361 | 0.528 / 0.564 / 0.346 | **0.639** / 0.567 / 0.288 | 0.417 / 0.460 / 0.331 |
| 4 | 0.406 / 0.500 / 0.250 | 0.562 / 0.559 / 0.258 | 0.469 / 0.443 / 0.261 | **0.594** / 0.500 / 0.406 | 0.500 / 0.494 / 0.345 | 0.531 / 0.460 / 0.335 | 0.469 / 0.516 / 0.245 |

Level MAE of persistence: 5.05, 5.98, 6.46 and 6.51 at Leads 1–4. FIL is significantly worse at every lead (one-sided p ≥ .97 for "FIL better").

**Verdict.** FIL fails R2–R8 at every lead. **75% is not reached.** FIL is worse than persistence, and at Leads 1–2 worse than chance.

**Why FIL fails (diagnosed from the prediction rows)**
1. FIL first trains on 2021–23, when hunger fell back after the 2021 peak, so it learned "hunger returns to its recent average".
2. It then predicted falls through the 2024 surge: Lead-1 accuracy was 0.19 in 2024, against persistence at 0.81.
3. It predicted rises during the 2025 easing.
4. With 80–240 overlapping training rows from about 15 independent quarters, the learner cannot tell a regime from a rule.

**Pre-registered variants** (accuracy at Leads 1–4)

| Model | Lead 1 | Lead 2 | Lead 3 | Lead 4 |
|---|---|---|---|---|
| FIL-NONEWS | 0.409 | 0.425 | 0.444 | 0.531 |
| FIL-H (hunger history only) | 0.500 | 0.450 | 0.500 | 0.531 |
| FIL-HN (hunger history + news) | 0.568 | 0.450 | 0.389 | 0.531 |

- **FIL-BL** (trained on BL rows only): issuable for only 2–5 rows per lead, so the evidence is insufficient.
- **Drop-one-family runs:** no family's removal changes accuracy by more than 0.09. All are within noise (`out/results_primary.json` → `variants`).

**SHAP attribution at Lead 1**

| Family | Share |
|---|---|
| Hunger history (`h_*`) | 52% |
| H1 | 12% |
| A3 rice | 11% |
| A1 food price | 7% |
| C4 fisheries | 6% |
| E1 unemployment | 5% |
| News | 3% |
| Every other family | ≤ 1% |

V1 (static poverty) is 0%, because a constant cannot split a tree in a regional time series.

## 4. Stage 2: long-history training (secondary arm, flagged for adviser approval)

**Purpose.** This is the pre-registered corrective test of the main suspected cause: too little training data.

**Setup.** FIL's exact pipeline (FIL-LONG) was trained on SWS 1998–2026 with the 9 families that exist before 2021 (`out/predictions_long.csv`).

**Untouched evaluation:** targets 2003–2020, never used before by any experiment. There are 280 rows (70 quarters × 4 areas) per lead.

| Lead | Accuracy | Balanced accuracy | AUC | Brier | Persistence accuracy | MA2 accuracy | Logistic accuracy | BL accuracy |
|---|---|---|---|---|---|---|---|---|
| 1 | 0.504 | 0.506 | 0.509 | 0.269 | 0.525 | 0.486 | 0.489 | 0.56 |
| 2 | 0.518 | 0.521 | 0.518 | 0.272 | 0.493 | 0.511 | 0.507 | 0.66 |
| 3 | 0.554 | 0.555 | 0.548 | 0.269 | 0.475 | 0.554 | 0.521 | 0.57 |
| 4 | 0.536 | 0.537 | 0.504 | 0.279 | 0.482 | 0.536 | 0.500 | 0.49 |

On 2021+ targets (80 rows per lead), FIL-LONG scores 0.44, 0.51, 0.53 and 0.58 at Leads 1–4.

**Verdict on classification.** With 22 years of training data, the ELEVATED call is still close to a coin flip, and so are all the baselines. More data did not create predictability.

**Level forecasts on the untouched set** (MAE in percentage points, paired cluster bootstrap)

| Lead | FIL-LONG | Persistence | MA2 | p (FIL-LONG better than persistence) | p (FIL-LONG better than MA2) |
|---|---|---|---|---|---|
| 1 | 4.22 | 4.57 | **4.14** | **.031** | .72 |
| 2 | 4.52 | 4.87 | **4.34** | **.009** | .94 |
| 3 | 4.81 | 4.91 | **4.49** | .28 | .99 |
| 4 | 5.02 | 5.06 | **4.51** | .38 | 1.0 |

FIL-LONG significantly beats the latest reading at Leads 1–2 on untouched data. However, a plain average of the two newest readings (MA2) is better still. The gain is noise smoothing, not learned signal.

**SHAP attribution, untouched set, Lead 1**

| Family | Share |
|---|---|
| Hunger history | 59% |
| A1 food price | 12% |
| A3 rice | 6% |
| C3 palay | 5% |
| C1 ENSO | 4% |
| E1 unemployment | 4% |
| A2 headline inflation | 4% |
| News | 1% |

## 5. Why 75% cannot be reached on this outcome (Addendum 1, frozen before it was run)

**Question.** How accurate could a *perfect* forecaster be?

**Method.** Each area's 1998–2020 series is simulated as a true level plus survey noise (±6 margin), with the level process estimated from the data. The forecaster knows the process exactly and makes the Bayes-optimal ELEVATED call. The simulation runs 2,000 series per area.

| Lead | Random-walk level (main case) | Mean-reverting AR(1) level (optimistic) |
|---|---|---|
| 1 | **0.58** (0.56–0.60 across areas) | 0.64 (0.62–0.66) |
| 2 | 0.54 | 0.63 |
| 3 | 0.53 | 0.60 |
| 4 | 0.50 | 0.53 |

**Does better survey precision help?** BL Lead-1 Bayes accuracy by survey margin (`out/ceiling_by_margin_BL.json`):

| Survey margin | ±6 | ±4 | ±3 | ±2 | ±1 | 0 |
|---|---|---|---|---|---|---|
| Lead-1 Bayes accuracy | 0.58 | 0.61 | 0.62 | 0.62 | 0.63 | 0.63 |

**Exact cause.**
- Whether next quarter's hunger is above its past-year average depends mostly on new shocks: the true change over a 2–5 quarter horizon.
- No indicator in 22 years of data predicts those shocks (§4, and E107–E113).
- Survey noise lowers the ceiling further, but even with no noise it stays at about 0.63.

**The 75% target is therefore unattainable for this outcome by any model, not only by LightGBM.**

**An optimistic bound.** Treating every observed gap as real gives 0.79–0.81. Even that would require forecasting the true change almost perfectly.

**Noise-targeted correction (FIL-LONG-S, Addendum 1).** It adds noise-reduced anchors: MA2, MA4 and a Kalman-filtered level.

| | Leads 1–4 |
|---|---|
| Accuracy 2003–2020 | 0.49–0.54 |
| Accuracy 2021+ | 0.51–0.59 |
| Level MAE vs FIL-LONG | Essentially unchanged |
| Level MAE vs MA2 on 2003–2020 | Not better (p ≥ .74) |

No improvement.

## 6. Summary for the thesis

| Question | Answer |
|---|---|
| Was 75% reached? | **No.** |
| Primary metric | ELEVATED classification accuracy on the 4-area panel |
| Primary result | 0.32 / 0.40 / 0.44 / 0.50 at Leads 1–4 (2021+, development) |
| Untouched result | 0.50 / 0.52 / 0.55 / 0.54 at Leads 1–4 (2003–2020, FIL-LONG) |
| Beats baselines? | No. Persistence is best at Lead 1 on 2021+ (0.61). On level error, FIL-LONG beats persistence at Leads 1–2 on untouched data, but not MA2. |
| Stable across periods? | No. FIL Lead-1 accuracy is 0.50 in 2023, 0.19 in 2024 and 0.38 in 2025+. |
| Survives data not used for selection? | The untouched 2003–2020 test confirms the absence of skill: about 0.50–0.55, in line with the Bayes ceiling of 0.50–0.58. |
| Can it ever be reached on this outcome? | No: the Bayes ceiling is 0.58–0.64 at Lead 1. |
