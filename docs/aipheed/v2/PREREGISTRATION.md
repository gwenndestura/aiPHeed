# v2 Pre-registration (Steps 2–3)

**Status:** written and committed **before** any v2 model was fitted or any v2 forecast computed. Its SHA-256 is stored in `backend/tests/unit/test_v2_preregistration.py`; an edit makes the test fail. Any change after fitting begins goes to `docs/aipheed/v2/DEVIATIONS.md`, and results affected by it are labelled **EXPLORATORY**.

**Basis:** `DIAGNOSIS.md` (Gate 1: 75 % at Lead 2 NOT ACHIEVABLE with existing measurements). Frozen values are taken from `PROTOCOL_LOCK.md` and are not reinterpreted:
- target and tolerance (T1–T4);
- P-DASH issue, Lead k and evaluation quarters (E1);
- S-U rows n_obs ≥ 8 (E2);
- N1–N7 (R1–R2);
- CPI rule (C1–C4, unused here: v2 has no CPI input);
- the 2021+ window (W1).

---

## 1. Design derived from the diagnosis (Step 2)

The diagnosis leaves **one forecastable component**: the anchor. The latest SWS reading carries sampling noise, which is 15 % of persistence's Lead-2 MSE (DIAGNOSIS Q1–Q2). Everything else is rejected (§1.3). The v2 method is therefore a **delta-form forecast with a zero-change prediction beyond a denoised anchor**:

  forecast(a, target) = latest reading(a) + [filtered true level(a) − latest reading(a)] + 0 × (horizon)

with the dynamics parameters pooled across the 4 SWS areas (Q5: homogeneity not rejected).

### 1.1 Candidates (exactly 3, simplest first)

| # | Name | Definition | Estimated parameters | Hypothesis, and why the diagnosis supports it | Rejected if |
|---|---|---|---|---|---|
| 1 | **PERSIST** | f = latest quarter value known at the issue (`as_of`) | 0 | Reference: the true level is close to a random walk (Q2) | (never rejected; it is the default) |
| 2 | **LL** | Local level, pooled over areas: x_t = x_{t−1} + η_t, η ~ N(0, q); y_t = x_t + ε_t, ε ~ N(0, SE_t²) with SE_t the frozen binomial quarter SE. f = filtered x at the latest observed quarter (no drift, no season). | 1: q | Filtering removes part of the anchor's sampling noise; the series is a noisy random walk (Q2: lag-1 change ACF −0.27, the noise signature) | It does not beat PERSIST under §3 on inner folds |
| 3 | **LL-K** | As LL, with observation variance κ·SE_t² | 2: q, κ | Real round-to-round noise exceeds the binomial SE (Q1: RMS z = 1.84 of same-quarter round pairs, p = 6e-5). The right noise variance gives the right amount of smoothing. | It does not beat the incumbent under §3 on inner folds |

**Estimation:**
- q and κ are estimated by **pooled maximum likelihood** (prediction-error decomposition of the Kalman filter, diffuse start at each area's first observation), from the quarter values known at the issue only.
- Grids:
  - q ∈ `S2_GRID` = 60 log-spaced values from 0.05 to 80 pp² (as `app.forecasting.models.S2_GRID`);
  - κ ∈ {1, 1.5, 2, 3, 4, 6}.
- Ties go to the smaller κ, then the smaller q.

**Forecast for lead k:** target = D − 1 + k, horizon h = target − latest observed quarter.
- Point: f = filtered level (random walk: no change beyond the anchor).
- Model SD: sd = √(P + h·q + κ·median(SE²)), with P the filtered state variance.

### 1.2 Inputs and features

- **Only the SWS hunger history known at the issue:** rounds published strictly before 00:00 PHT on the issue day (`app.forecasting.as_of`), and their published margins (for SE).
- **No exogenous feature:** Q3 found no repeatable leading signal.
- The five trigger groups are kept for explanation as **context indicators** with their data state, never as contributions.

### 1.3 Rejected ideas (with the diagnosis evidence)

| Idea | Rejected because |
|---|---|
| Seasonal / quarter-of-year terms | Kruskal–Wallis p = 0.94 (all), 0.44 (post-break); 4–8 changes per cell |
| Trend or damped trend | No momentum (change ACF lag 1 = −0.27, which is the noise signature). TREND-D was already worse than persistence (MODEL_REPORT). |
| Mean reversion towards a training mean (AR latent, shrinkage) | In-sample φ = 0.80, but out of sample (parameters from data known at each issue) within 0.375 vs persistence 0.400, MAE equal. The expanding-mean forecast scores 0.15. The in-sample effect is the 2024 level shift. |
| Learned bias correction | The bias is not stable: −8.5 in 2024, +0.5 in 2025–26 |
| Exogenous drivers (5 groups, ONI) | No primary signal (Holm p ≥ 0.52). ONI is one 2023–24 episode (ρ ≈ 0.1 outside it). E134-ONI was already tried post-hoc (0.50). |
| Ensemble of persistence and a structural model | LL is already a data-weighted combination of the latest reading and the earlier level. A further blend has no diagnostic support and would add a weight to tune on 10 quarters. |
| Learned models (ridge, LightGBM) | Overfit in E131–E132 (ridge train/test MAE 2.08 / 7.36, MODEL_REPORT) |
| Provincial/LGU model values | No provincial measurement exists (E129–E130); Balance Luzon may not be copied as provincial truth |

## 2. Validation design

### 2.1 Rows

- **Outer rows:** the frozen S-U rows. These are P-DASH issues (first day of dashboard quarter D, 2021-Q3 … 2026-Q4) with Lead k target = D − 1 + k, n_obs ≥ 8 known at the issue, and the target observed.
  - Lead 2 has 40 rows over 10 target quarters (2024-Q1 … 2026-Q3).
  - Leads 1, 3 and 4 have 44, 36 and 32 rows.
- **Truth** is the quarter value from all rounds held (protocol E1). The row set must equal the E136 / DIAGNOSIS Q6 rows exactly (asserted in code).

### 2.2 Nested expanding window

At each outer issue I:

1. **Inner rows.** These are the Lead-2 P-DASH rows with:
   - issue J < I;
   - n_obs ≥ 4 at J;
   - a target quarter value **known at I** (rounds published before I).

   Their truth is that value as known at I (it may be a partial quarter). Each inner forecast uses parameters re-estimated from data known at J.
2. **Selection** (§3) on the inner rows.
3. **Selected model fit and forecast.** The selected model is re-estimated on data known at I and forecasts Leads 1–4.
4. **Interval** (§2.3).

**Outer rows are scored once,** after all forecasts are produced. The 3 fixed candidates are also run walk-forward on the outer rows for reporting. The **v2 procedure** (V2 = selection + selected model + interval) is the object under test.

### 2.3 Prediction interval (80 %)

**Split-conformal,** per lead, at each issue I:
- **Residuals:** the absolute walk-forward residuals |f − y| of the model selected at I, recomputed on that lead's inner rows. The inner rows are defined as in §2.2, but with the lead's own targets.
- **If there are ≥ 8 residuals:** half-width = the ⌈0.8 (n + 1)⌉-th smallest.
- **Otherwise:** Gaussian, f ± 1.2816 × sd (§1.1 model SD; for PERSIST the LL sd at the LL estimate).

**Reported:** empirical coverage (N7 needs 0.70–0.90).

### 2.4 Served model

The served model is chosen by the same rule, applied once at the latest issue (2026-10-01), with inner rows = every Lead-2 row whose target is known before 2026-10-01. Its parameters are frozen in a hashed JSON artifact.

## 3. Selection rule (applied mechanically in code)

**Primary metric:** share within the frozen tolerance at Lead 2.

**Procedure:**
1. The incumbent is **PERSIST**.
2. For each challenger in order (LL, LL-K):
   - compute the **paired block-bootstrap 95 % CI** of Δ = within(challenger) − within(incumbent) over inner target quarters (resample target quarters with replacement, 2 000 draws, seed 2026);
   - the challenger replaces the incumbent only if **the CI lies entirely above 0 and the inner rows cover ≥ 6 target quarters**.
3. Otherwise the simpler incumbent stays.

**Nothing else may change the choice:** not MAE, not outer results.

## 4. Metrics (outer rows, per lead; V2, each candidate and the context baselines)

**Primary:**
- n within / n eligible and share within tolerance, with a 95 % block-bootstrap CI over target quarters (10 000 draws, seed 2026);
- the paired CI of Δ within vs PERSIST.

**Secondary:**
- MAE, RMSE, bias;
- high-tercile bias (top third of observed values);
- sharp-increase detection (rows with y − y_latest > 2·SE: share within tolerance);
- prediction variance ÷ target variance;
- Pearson correlation;
- 80 % interval coverage and mean width.

**Context baselines on the same rows** (reported, never selected):
- PERSIST;
- TREND-D;
- CLIM (expanding area mean known at the issue);
- RIDGE-ALL;
- SEAS-LLM;
- HFM-X (from E136 predictions, re-scored).

**Overfitting and stability:**
- training (in-sample one-step) vs inner vs outer MAE;
- training-window start 2021-Q2 (primary) vs 2022-Q1 (sensitivity);
- results by period: pre-surge, 2024 surge, 2025–26.

## 5. Leakage controls (must behave as stated)

| Test | Expected |
|---|---|
| Shuffle-target: SWS quarter values permuted within area (seed 2026), publication dates kept, V2 rerun | No advantage over PERSIST; within share collapses to the shuffled-series level |
| Future-shift (positive control): information cutoff moved to the day after the target's publication | Within share rises far above the honest run, so the evaluation is sensitive to leakage |
| Injected leak: a round published on or after the issue added to the data | The forecast is unchanged (`as_of` drops it); `assert_point_in_time` raises on a table containing it |
| Injected leak: a feature table row dated after the issue | `LeakageError` |

## 6. Decision table (mechanical, `backend/app/forecasting/v2/verdict.py`)

**Reliability at each lead:** frozen N1–N7 via `e130_lib.numeric_reliability`.
- Rows: area as "province", target quarter clusters.
- N3/N4 baselines: persistence and climatology, exactly as the completed backend run applied them.

| Outcome on DEVELOPMENT rows (all S-U rows, seen before) | Label |
|---|---|
| N1–N7 all pass | `DEVELOPMENT_PASS`: still **not** a research pass |
| Any rule fails | `NOT_RELIABLE` (development) |

| Outcome on FUTURE rows (sealed set, §7) | Label |
|---|---|
| Fewer than 10 unseen target quarters or 40 rows (N1) | `NOT_YET_TESTABLE` |
| N1–N7 all pass | `RELIABLE`; Lead 2 `VALIDATED` only if N2 (≥ 75 %) holds |
| Any rule fails | `NOT_RELIABLE` |

**Maximum reliable lead:** the furthest consecutive `RELIABLE` lead from Lead 1, on future rows only.
**Served `reliability_status`:** the development label until future rows reach N1, then the future label. It is computed by code from the results files, never typed.

## 7. Sealed confirmation set

- **All quarters 2021-Q2 … 2026-Q3 were seen** in E110–E136 and in the completed backend run. Withholding any of them now would not make them unseen. The number of genuinely unseen complete quarters is **0 (< 6)**, so **no historical quarters are sealed**.
- **The sealed set is "future data only":** every SWS target quarter from **2026-Q4** onward.
- **All results on 2021–2026-Q3 are DEVELOPMENT.**
- **Prospective seal:** before any outcome exists, V2 and the 3 candidates are issued for the dashboard issues 2026-07-01 and 2026-10-01 (targets 2026-Q4 … 2027-Q3; already-published targets excluded). The file is `docs/aipheed/v2/sealed/V2_PROSPECTIVE_SEAL.csv`; its SHA-256 is stored in a test. Later issues are appended as new files each quarter.
- **Scoring:** `backend/scripts/v2_score_sealed.py`.
  - It scores only targets whose rounds are published.
  - It logs every opening to `docs/aipheed/v2/sealed/ACCESS_LOG.md`.
  - It never edits the seal.

## 8. What counts as failure

**The research claim fails** (expected per Gate 1) if, on outer rows or on future rows once N1 is met:
- Lead-2 V2 within < 0.75; **or**
- any N1–N7 rule fails; **or**
- V2 does not beat PERSIST with a paired CI above 0.

A development pass would not count as research success.

**The method itself fails** (it should not be served over PERSIST) if the inner-fold rule never selects it. In that case the served forecast is PERSIST, explained as "last observed value carried forward".

**Software success** is judged separately (FINAL_REPORT verdict A).

## 9. Fixed constants

| Constant | Value |
|---|---|
| Seed | 2026 |
| Inner bootstrap draws | 2 000 |
| Outer bootstrap draws | 10 000 |
| Minimum inner target quarters for replacement | 6 |
| Inner n_obs minimum | 4 |
| Minimum residuals for conformal | 8 |
| Z90 | 1.6448536 (frozen T4) |
| Z80 | 1.2815516 |
