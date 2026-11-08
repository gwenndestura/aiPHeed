# E110: generalizing SWS hunger forecasts across areas and quarters. Pre-registered protocol

**Date:** 2026-10-25. **Branch:** `aiPHeed/e110-hunger-generalization`, from E109 `00937d0`.
**Freezing:** hashed in `runner/PROTOCOL_SHA256.txt` before any E110 model is scored. Changes go in dated, hashed addenda.
**Study window:** 2021 onward only (fixed by the researcher).

**Already seen before freezing:**
- every E109 result;
- `out/diagnosis.json`, built from E109 data and predictions only;
- the area values in `data/sws_area_rounds.csv`, including the descriptive observation that, in 2025–26, 1,500-sample rounds (March, April, September) read higher than 1,200-sample rounds (June, November) in Balance Luzon.

**Every quarter through 2026-Q3 has been seen. All retrospective results are development evidence.**

## 1. Outcomes

- **Primary:** SWS Total Hunger, **Balance Luzon** (BL), per quarter = mean of the non-commissioned rounds by fieldwork quarter. This is identical to the E109 primary series (checked).
- **Generalization panel:** the same measure and the same rounds for **Metro Manila (NCR), Balance Luzon, Visayas and Mindanao**. That is 4 areas × 20 quarters (2021-Q2..2026-Q3; no non-commissioned round in 2021-Q1, 2022-Q1 or 2025-Q1).
  - Each area is a separately sampled SWS estimate. Areas in the same quarter share national shocks, so inference is clustered by quarter.
- **Vintage at issue date O(*t*)** (day 1 of quarter *t* + 1): the mean of the rounds published before O(*t*) (E109 Addendum 1). Evaluation uses final quarter means.
- **Round precision:** R = (published area margin / 1.96)². A quarter with two rounds has variance mean(R)/2. Where a 2021–22 margin is not stated, ±6% (the 300-per-area design) is assumed.

## 2. Methods

| Name | Type | Definition |
|---|---|---|
| RW | baseline | latest known area value |
| MA2 | baseline | mean of the last two known quarters |
| MEAN | baseline | mean of all known quarters of the area |
| **LLR (primary)** | structural | Per-area local-level Kalman filter: level plus random-walk drift with variance Q per quarter; observation noise R from the **published round margin**. Q is pooled over the 4 areas by moments: mean of (ΔH² − R_i − R_j)/gap over consecutive known pairs, floor 0.25, data known at O(*t*) only. Forecast = filtered level at the last known quarter. |
| COMB | structural | (RW + LLR)/2 |
| NAT-R | indicators, panel | LLR + ridge (α = 10, standardised, training-median imputation) of the LLR residual on the **national** families C1, E1 and E2, pooled over the 4 areas |
| **LGBM-R (required 12-family LightGBM)** | indicators, BL | LLR + LightGBM regressor of the BL residual (H − LLR at *t*′) on the 13 E107 columns averaged over CALABARZON (all 12 families). Depth 1, 2 leaves, min_child 3, learning rate 0.05, L2 = 5, trees ∈ {25, 75} by inner MAE on the last 4 training targets; deterministic, seed 110. |
| RIDGE-R | indicators, BL | the same residual target, ridge α = 10 on the 13 columns |

**Eligibility:**
- panel origin: every area has ≥ 6 known quarters at O(*t*);
- BL learned models: ≥ 8 training pairs (as E109).

**Leads:**
- panel methods: 1–6, judged where ≥ 8 target quarters exist;
- BL learned models: 1–4.

## 3. Reliability rule (frozen now; lead *k*, method M; e = forecast − outcome)

d_q = mean over areas of (|e_M| − |e_RW|) in target quarter *q*. For BL-only methods, d_q = |e_M| − |e_RW| on BL.

| | Criterion |
|---|---|
| **P1 sufficiency + skill** | ≥ 8 target quarters; mean d_q < 0 and HLN-corrected Diebold–Mariano p < 0.10 (lag *k* − 1) |
| **P2 BL** | ≥ 8 BL quarters; MAE_BL(M) ≤ MAE_BL(RW) and ≤ 4.0 points (SWS ±4% Balance Luzon margin) |
| **P3 generalization** | mean d < 0 (a) in each chronological third of target quarters, (b) separately for rising (H_target > H_last) and falling area-quarters, (c) on target quarters from 2025-Q2 on (after the respondent-base change) |
| **P4 influence** | mean d_q < 0 after removing any single quarter (leave-one-quarter-out maximum < 0) |
| **P5 recent block** | mean d_q ≤ 0 on the last four target quarters (2025-Q4..2026-Q3; seen before, not used for any E110 choice) |
| **P6** | confirmed on unseen outcomes (none yet) |

**Status:**
- **provisional** = P1–P5;
- **insufficient evidence** = fewer than 8 quarters for P1 or P2;
- **not reliable** = otherwise;
- **reliable** additionally needs P6.

**Maximum reliable lead** = the largest *k* with Leads 1..*k* reliable. Also reported: the maximum provisional lead and the maximum lead tested.

**Operational recommendation rule.** The simplest method that is provisional at Lead 1 (order: COMB, LLR, NAT-R, RIDGE-R, LGBM-R). If none is, the latest SWS reading (RW).

## 4. Binary readings (secondary; research-defined; SWS has no official threshold)

| Rule | HIGH if |
|---|---|
| B3 | hunger > 20% |
| B4 | rise above the latest reading by more than the area's published margin |

- **Probabilities:** Φ((forecast − c)/σ̂), σ̂ = RMSE of the method's own earlier errors (≥ 4, else SD of changes).
- **Reported:** accuracy, balanced accuracy, precision, recall, F1, Brier, confusion matrix, against persistence and climatology (panel, clustered by quarter).
- **Rule:** the E109 binary rule (accuracy ≥ 0.75, balanced ≥ 0.65, both recalls ≥ 0.5 with ≥ 2 quarters per class, Brier below persistence and climatology). Status provisional at best.

## 5. Diagnostics and sensitivities (no effect on §3)

- **Family ablation** of LGBM-R and RIDGE-R (drop one family at a time, BL, Leads 1–2).
- **SHAP and gain shares.**
- **S-VOTERS:** add the April 11–15, 2025 voter round.
- **S-R4:** constant ±4% instead of the published round margins.
- **Design/season check:** LLR residuals by round size (1,500 vs 1,200) in 2025–26, descriptive.

## 6. Seal

- Every method, Leads 1–6 (panel) / 1–4 (BL learned), from origin 2026-Q3 (issue 2026-10-01), for BL and the panel areas.
- Point forecast, 80% interval, B3/B4 probabilities, source hashes.
- `out/sealed_prospective.csv` and its SHA-256. The E107, E108 and E109 seals are untouched.

## 7. Tests (`backend/tests/unit/test_e110.py`)

- area data equal E109 BL;
- publication-date vintages;
- future-round perturbation (no change) plus a negative control;
- pooled Q uses known data only;
- R from the published margins;
- 12-family columns in LGBM-R;
- reproducibility;
- protocol and seal hashes (E107–E110);
- API.
