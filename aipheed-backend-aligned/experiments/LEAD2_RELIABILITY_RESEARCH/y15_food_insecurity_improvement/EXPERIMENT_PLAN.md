# Y15 experiment plan: improving the Lead-2 food-insecurity forecast

**Status.** Frozen before any Investigation C candidate was scored. The SHA-256 is in `runner/PLAN_SHA256.txt` and the time in `runner/PLAN_FROZEN_AT.txt`.

**Done before freezing:**

- **Investigation A** (`warmup_audit.py`): a sensitivity audit of the served FIRI on its stored history. No model is selected from it.
- **Investigation B acquisition** (`acquire_imf.py`): data only. The IMF series was cross-checked against the 2021+ BSP cash remittances: levels r = 0.997, YoY r = 0.86. No outcome was used.

## 1. Target and horizon (unchanged)

**TFI-2.** Observed Balance Luzon involuntary hunger > 11.3% in quarter t + 2. The forecast is issued at O(t), the first day of quarter t + 1 (Y14 `OBJECTIVE_AND_TARGET.md`). One regional outcome per quarter.

## 2. Inputs (point in time)

- **Y14 indicators.** `y14_food_insecurity_forecast/out/indicators.csv` (A2, A3, C1–C4, E1, H1, V1; lag rules in Y14 `DATA_AUDIT.md`), read-only.
- **New: E2 remittance decline.** −(YoY % change of IMF BOP personal transfers, quarter t−2 vs t−6). National.
  - The newest quarter used ended at least 6 months before O(t). That is conservative against BSP's quarterly BOP release, about 2.5–3 months after quarter end, and monthly cash remittances, about 6 weeks after.
  - IMF serves one current vintage (revised data), not real-time vintages. This is disclosed.

## 3. Candidates (five, predeclared)

| ID | Name | Definition |
|---|---|---|
| **C1** | FIRI-R: corrected research FIRI-style index | FIRI v2 scoring (mid-rank percentile against ≥ 8 strictly earlier origins), with **explicit missingness**: an indicator without enough history is *unavailable*, never 0. A domain counts only if at least half of its indicators are scored, else it *abstains*. The index needs ≥ 4 available domains, else **no forecast is issued** (counted, never imputed). Equal domain weights (no outcome-fitted weights). Domains: A (A2, A3), C (C1–C4), E (E1, E2), H (H1), V (V1, constant). |
| **C2** | SCREEN: parsimonious, drivers screened in-fold | At each origin, on training rows only (targets published before O(t)), each driver x ∈ {A2, A3, C1, C2, C3, C4, E1, E2} with ≥ 20 non-missing training rows is regressed: ΔH ~ 1 + (H_last − mean of known BL) + x. Keep at most the 2 drivers with the largest \|t\|, and only if \|t\| ≥ 2. Then fit a logistic y ~ Φ⁻¹(H1) + kept drivers (standardised in fold, C = 1, missing values → in-fold mean). With no driver kept, the logistic uses Φ⁻¹(H1) only. |
| **C3** | KAL: survey-uncertainty model | Phase 2 `hmodels.kalman("BL", t, 2, four areas)`: a latent AR(1) with each round's known sampling variance. The predictive distribution includes the target's own sampling error. |
| **C4** | CONT: continuous hunger forecast | OLS ΔH = H(t+2) − H_last ~ 1 + (H_last − mean of known BL) + the C2-screened drivers. Gaussian predictive with training residual σ. **Evaluated first on the continuous outcome**: MAE and Gaussian CRPS vs RW (point H_last, σ = the H1 RW σ) and vs the climatological mean. Then P(> 11.3) = Φ((μ − 11.3)/σ). |
| **C5** | REMIT: remittance-enhanced | Logistic y ~ Φ⁻¹(H1) + E2 (forced), standardised in fold, C = 1 |

**Baselines:**

- **H1**, the hunger-persistence probability (primary comparator);
- **PERSIST**, the newest reading > 11.3;
- **CLIM**, the expanding share of BL quarters > 11.3 published before O(t).

**Fitting rules.** C2, C4 and C5 need ≥ 30 training rows and ≥ 5 of each class (C2, C5). Otherwise they fall back to H1, and the fallback is counted.

## 4. Development (independent years)

- **Rows:** targets 2001-Q1 .. 2020-Q4 with an observed BL outcome and a defined H1. One row per quarter, all independent quarters, no provincial duplication.
- **Comparisons:** each candidate is compared with H1 on the rows where that candidate issues a forecast (C1 may abstain). n is reported.
- **Primary metric:** Brier score.
- **Test:** one-sided bootstrap of mean Brier(candidate) − Brier(H1). Quarters are resampled, B = 5000, seed 2036. A 4-quarter moving-block bootstrap is also reported.

**Gate.** A candidate passes only if both hold:

| | Condition |
|---|---|
| G1 | Brier < H1, with Holm-adjusted p < 0.10 over {C1, C2, C3, C4, C5} |
| G2 | Balanced accuracy at 0.50 ≥ H1's |

**Also reported:**

- accuracy, balanced accuracy, precision, recall, specificity, F1, AUC;
- confusion matrices;
- calibration slope;
- C4's MAE and CRPS;
- the drivers C2 kept at each origin (frequency);
- the leading correlation of E2 with ΔH, next to its concurrent correlation.

## 5. 2021–2026: the 17 official FIRI Lead-2 targets

- **Rules:** R1–R7 via `FIRI_LEAD2_FEASIBILITY/runner/score_firi_l2.rules`, unchanged. R1 fails structurally for 17 regional rows (Y14 `OBJECTIVE_AND_TARGET.md` section 6).
- **Every candidate** gets a seven-rule table.
- **No gate-passer:** **descriptive only**. Nothing is selected from these rows.
- **A gate-passer:** confirmatory on these rows, but labelled "already-used period", with reliability still requiring the prospective seal.

## 6. Prospective

`y14_food_insecurity_forecast/runner/issue_forecast.py` is reviewed, not modified, unless a candidate passes the gate.

- No seal is issued for any past date.
- The first valid issuance remains 2027-01-01.
