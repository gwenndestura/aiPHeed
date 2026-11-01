# Y14 experiment plan: a Lead-2 food-insecurity forecast validated on observed hunger

**Status.** Frozen before any model in this plan was scored. The SHA-256 is in `runner/PLAN_SHA256.txt` and the time in `runner/PLAN_FROZEN_AT.txt`.

**Already done before freezing (no outcomes linked to these indicators):**

- data acquisition;
- `indicators.py`, which builds the indicators;
- coverage counts.

## 1. Target

**TFI-2.** Observed Balance Luzon involuntary hunger > 11.3% in quarter t + 2. The forecast is issued at O(t), the first day of quarter t + 1. See `OBJECTIVE_AND_TARGET.md`.

The outcome is the mean of the SWS rounds in the quarter, from the same series used throughout this research (`rlib.observed`).

## 2. Hypotheses

| ID | Hypothesis |
|---|---|
| **H-F1** | The FIRI method (v2 scoring applied to point-in-time analogs of its indicators) forecasts TFI-2 better than the hunger-persistence probability H1 on independent years. |
| **H-F2** | The FIRI driver domains **without** the hunger domain carry a Lead-2 signal: FIRI-drivers-only beats climatology and adds to H1. |
| **H-M1** | A parsimonious logistic combination of H1 with the affordability, climate and economy domain scores, fitted only on earlier origins, improves on H1. |
| **H-M2** | A continuous model of the hunger change (target − newest reading) on the same domain scores, converted to P(> 11.3) through a Gaussian predictive distribution, improves on H1. |
| **Reference** | The Y2 Kalman latent-state model, which accounts for SWS sampling error. It is reported for comparison; it failed in Phase 2 and is not a candidate here. |

## 3. Models

All of these use only `out/indicators.csv` rows for origin t and outcomes published before O(t).

| Name | Role | Definition |
|---|---|---|
| PERSIST | baseline | 1{newest published BL reading > 11.3} |
| **H1** | **primary comparator** | RW probability (Phase 1 `rlib.forecast`, pooled four-area horizon σ) |
| CLIM | baseline | Expanding share of BL quarters > 11.3 among outcomes published before O(t) |
| **F1 FIRI-analog** | candidate | FIRI v2 scoring (code below) |
| **F2 FIRI-drivers** | candidate | F1 without domain H |
| **M1** | candidate | L2 logistic, C = 1, on [Φ⁻¹(H1) clipped to ±4, dom_A, dom_C, dom_E] |
| M1-0 | ablation | Logistic on [Φ⁻¹(H1)] (recalibrated persistence) |
| **M2** | candidate | OLS of ΔH = H(t+2) − H_last on [H_last − mean of known BL readings, dom_A, dom_C, dom_E]. σ = training residual RMSE. P = Φ((H_last + μ̂ − 11.3) / σ). |
| M2-0 | ablation | The same without the domains (mean reversion) |
| KAL | reference | Phase 2 `hmodels.kalman("BL", t, 2, four areas)` |

**FIRI v2 scoring** (`backend/app/ml/inference/firi.py`, `score_v2`):

- each continuous indicator (A2, A3, C2, C3, C4, E1) is scored as its mid-rank percentile among its own values at strictly earlier origins (at least 8, else missing);
- C1, H1 and V1 are used as they are (0–1);
- each domain score is the mean of its available indicator scores;
- the index is the equal-weighted mean of the available domains, which needs at least 4 domains;
- HIGH if ≥ 0.50.

The served walk-forward evidence weights were estimated on 2021+ outcomes and are **not** used. The analog is equal-weighted, which is FIRI's own fallback.

**Fitting rules for M1 and M2:**

- Training rows are origins t′ whose target t′ + 2 outcome was published before O(t).
- A fit needs at least 30 rows and at least 5 of each class (M1). Below that, the prediction falls back to H1 and the fallback is counted.
- A missing domain score (E before 2006-Q3) is replaced by the in-fold training mean.

## 4. Development: independent years

- **Rows:** targets 2001-Q1 .. 2020-Q4 with an observed BL outcome. One row per quarter. All models are scored on the identical rows where every candidate is defined (n is reported).
- **Primary metric:** Brier score.
- **Test:** one-sided bootstrap of the mean Brier difference (candidate − H1). Quarters are resampled, B = 5000, seed 2036. A moving-block (4-quarter) bootstrap is also reported.

**Gate.** A candidate passes only if all three hold:

| | Condition |
|---|---|
| G1 | Brier < H1, with Holm-adjusted p < 0.10 over {F1, F2, M1, M2} |
| G2 | Balanced accuracy at 0.50 ≥ H1's |
| G3 | The added information helps: F1 Brier < H1 is G1 itself; F2 Brier < CLIM with p < 0.10; M1 beats M1-0 and M2 beats M2-0, each with p < 0.10 |

**Also reported:**

- accuracy, balanced accuracy, precision, recall, specificity, F1, AUC;
- calibration (bins and slope);
- MAE of the level, for M2;
- the leading correlation of each indicator at O(t) with ΔH (90% bootstrap CI), next to its concurrent correlation (indicator measured at the target quarter).

## 5. Confirmation: 2021–2026, only for candidates that pass the gate

- **Rows:** the 17 FIRI Lead-2 targets 2022-Q3 .. 2026-Q3 (`FIRI_LEAD2_FEASIBILITY/out/firi_l2_rows.csv`), the same rows the served FIRI v2 is scored on.
- **Rules:** R1–R7 as applied by `FIRI_LEAD2_FEASIBILITY/runner/score_firi_l2.rules`, unchanged. **R1 fails structurally (17 rows)**; see `OBJECTIVE_AND_TARGET.md` section 6.
- **Reported alongside:** served FIRI v2 (F2 column), H1, PERSIST and CLIM.

**If no candidate passes the gate,** every candidate is still scored on the 17 rows. That scoring is **descriptive only**, and no candidate is selected from it.

## 6. After scoring (descriptive)

A domain-by-domain description of the served FIRI v2 on 2021+: AUC of each domain score against TFI-2. Its purpose is to explain FIRI's 2021+ accuracy. It is not used for any choice.

## 7. Prospective comparison

`runner/issue_forecast.py --issue YYYY-MM-DD` issues H1, F1 and any gate-passing candidate for target t + 2. It writes:

- a sealed JSON with forecasts;
- the UTC time;
- SHA-256 hashes of every input file;
- the newest SWS round used.

It refuses to call a forecast valid if it is written after the issue date. It never touches existing sealed artifacts.
