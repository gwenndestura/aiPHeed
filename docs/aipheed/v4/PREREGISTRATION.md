# v4 Pre-registration (Step C)

**Status:** committed **before** any v4 model is fitted or any v4 forecast is computed. Its SHA-256 (LF-normalised) is frozen in `backend/tests/unit/test_v4_preregistration.py`. Changes after fitting go to `v4/DEVIATIONS.md`, and affected results are labelled EXPLORATORY.

**Basis:** `../v2/DIAGNOSIS.md`, `../v3/PROTOCOL_VALIDITY.md`, `TARGET_OPTIONS.md`, `EVALUATION_DESIGN.md`. Frozen values (`../PROTOCOL_LOCK.md`, SHA-256 `8bae6962…dd0d3`) are read-only.

## 1. Target and tolerance

- **Target:** SWS involuntary hunger, % of families, 4 SWS areas (lock T1). P-DASH issue; Lead k = D − 1 + k; **Lead 2 primary** (lock E1).
- **Primary tolerance: FROZEN** (lock T1–T4). |forecast − SWS| ≤ 1.645 × binomial SE of the SWS quarter.
- **Proposed amended tolerance:** **NOT ADOPTED**; reported alongside, never instead.
  - **Formula** (from measurement properties only, v3 option b2): tol_A(a, q) = 1.96 × SE_pub(a, q), where SE_pub = √(Σ_i (MoE_i / 1.96)²) / k over the k non-commissioned rounds and MoE_i is the published area margin.
  - **Disclosure:** its development values were computed in v3 (oracle 0.59 / 0.78, persistence 0.50 at Lead 2), before this pre-registration.
  - **Status until signed:** `PROPOSED_NOT_ADOPTED`. Sign-off: adviser `________`, date `________`. Effective only for target quarters with no SWS round published on the sign-off date.

## 2. Candidates (4, simplest first) and inputs

| # | Name | Definition | Parameters fitted in-fold |
|---|---|---|---|
| 1 | **PERSIST** | Latest SWS quarter value known at the issue | 0 |
| 2 | **LL-K** | v2 pooled local level with noise multiplier κ (`app.forecasting.v2.models`, unchanged) | q, κ |
| 3 | **DELTA-X** | PERSIST + predicted change. Change = Σ β_j z_j over the exogenous features that pass the stability rule (§2.2) in the fold; ridge α = 10 on in-fold z-scores; **no intercept**. With no feature passing, change = 0. | Features selected; β |
| 4 | **DELTA-X-LLK** | LL-K level + the same predicted change (β fitted on change from the LL-K level) | q, κ, features, β |

**Fixed choices:**
- **No intercept / no bias correction:** the diagnosis showed the bias flips sign across periods (−8.5 in 2024, +0.5 in 2025–26).
- **Fixed α:** no α grid, to avoid tuning on 10 development quarters.
- **One model per lead:** fitted on that lead's rows.

### 2.1 Exogenous features (6, fixed here; one or more per group; all point-in-time)

| Group | Feature | Source and availability |
|---|---|---|
| A market | `rice_yoy`: area rice CPI YoY of the latest complete quarter | E131 regional CPI; quarter end + 10 days < issue; YoY only from 2022-01 (lock C1–C4) |
| C climate | `typhoons_PAR` | E119 point-in-time row of the issue date |
| C climate | `oni_quarter_mean`. **Post-hoc flag:** first noticed in E133 D2 on outcomes; one-episode association (DIAGNOSIS Q3). It is included so the stability rule, not the analyst, decides. | E119 point-in-time row |
| E employment/OFW | `E1_unemployment_change_pp` (national) | E119 point-in-time row |
| N news | `news_gdelt_shortage_share` | E119 point-in-time row (GDELT by publication date) |
| V poverty | `poverty`: area poverty incidence of the latest published PSA round | E131 poverty; PSA release date < issue |

- **Snapshot table:** values are frozen per (issue, area) in `backend/data/forecasting/v4_feature_snapshots.csv`, built by `backend/scripts/v4_features.py`.
- **Snapshot use:** a snapshot may be used only at its own issue. Using it at any other issue raises `LeakageError`.
- **Missing values:** missing in-fold stays missing. The row is dropped from that feature's stability statistics and contributes z = 0 at prediction (neutral; disclosed).

### 2.2 Stability rule (applied in-fold at each issue I and lead k; fixed here)

1. **Training rows:** lead-k P-DASH rows with issue < I, n_obs ≥ 4, truth known at I (`as_of`), and the feature present. Training target = truth − anchor.
2. **A feature enters only if all three hold:**
   - its training rows span **≥ 6 distinct issues**;
   - **|Spearman ρ(feature, change)| ≥ 0.30** on all training rows;
   - **the sign of ρ is the same** in the earlier and later halves of the training issues (split at the median issue; each half ≥ 3 issues).
3. **Group identity** is kept for explanation (β_j × z_j summed by group). No manual or equal weights.

### 2.3 Baselines (re-scored on identical rows; never selectable)

| Baseline | Source |
|---|---|
| PERSIST | Also a candidate |
| TREND-D (damped trend) | E136 predictions |
| CLIM (expanding mean) | E136 predictions |
| RIDGE-ALL | E136 predictions; scored on its own rows |
| HFM-X | E136 predictions |
| SEAS-LLM | E136 predictions |
| **V2** | v2 nested selection (`v2_outer_predictions.csv`) |

## 3. Validation

- **Tiers:** as in `EVALUATION_DESIGN.md` §2.
  - **TRAIN** = P-DASH rows with targets ≤ 2023-Q4.
  - **DEVELOPMENT-TEST** = S-U rows (Lead 2: 40 rows, 10 quarters).
  - **SEALED** = future targets from 2026-Q4.
  - The tier files' SHA-256 are stored in a test.
- **Nested expanding window:** at every P-DASH issue 2021-Q3 … 2026-Q4, each candidate is fitted on data known at the issue, and selection uses inner rows only (§4).
- **Development-test rows are scored once.**
- **Leave-one-area-out** (development only, spatial generalisation): LL-K and DELTA-X are refitted with pooled parameters estimated without the held-out area, then forecast it. Reported, never used for selection.

## 4. Selection rule (mechanical)

- **Incumbent:** PERSIST.
- **Procedure:** challengers in the order LL-K, DELTA-X, DELTA-X-LLK. Each replaces the incumbent only if, on the inner Lead-2 rows at the issue (≥ 6 inner target quarters), the paired cluster-bootstrap 95 % CI (2 000 draws, seed 2026) of Δ within (frozen tolerance) lies entirely above 0.
- **V4** = the selected model at each issue.
- **Served V4** = the rule applied at issue 2026-10-01.

## 5. Primary metric and the "beats all models" test

**Primary metric:** share within the frozen tolerance at Lead 2, with a 95 % CI from a **moving-block bootstrap over sorted target quarters, block length 3** (10 000 draws, seed 2026). The cluster bootstrap is also reported.

**"Beats every other model":** for each baseline b (§2.3) on the rows where both exist:
- compute the one-sided p = share of moving-block bootstrap draws with within(V4) − within(b) ≤ 0;
- apply Holm correction across the 7 baselines at α = 0.05;
- **V4 beats all** only if every Holm-adjusted p < 0.05.

**Secondary (reported):**
- MAE, RMSE, bias;
- high-tercile bias;
- sharp-increase detection (y − y_latest > 2·SE);
- variance ratio, correlation;
- 80 % split-conformal coverage and width;
- train / inner / outer MAE;
- results under the proposed amended tolerance (labelled PROPOSED_NOT_ADOPTED).

**Reliability:** the frozen N1–N7 via `e130_lib.numeric_reliability`. N3/N4 baselines are persistence and climatology, as in the earlier runs.

## 6. Mechanical verdict table (code: `backend/app/forecasting/v4/verdict.py`)

| Claim | Tier | Condition | Verdict |
|---|---|---|---|
| ≥ 75 % within (frozen or amended) | DEVELOPMENT-TEST | — | `DEVELOPMENT_ONLY`: the share and CI are reported, never as confirmation |
| ≥ 75 % within | SEALED | < 10 target quarters or < 40 rows | `NOT_YET_TESTABLE` |
| ≥ 75 % within | SEALED | N1 met and one-sided 95 % lower bound ≥ 0.75 | `CONFIRMED` |
| ≥ 75 % within | SEALED | N1 met and one-sided 95 % upper bound < 0.75 | `REJECTED` |
| ≥ 75 % within | SEALED | Otherwise | `INCONCLUSIVE` |
| Beats all | Either tier | Holm rule of §5 (sealed: only once N1 is met) | `YES` / `NO` / `NOT_YET_TESTABLE` |
| Lead k reliable | SEALED | Frozen N1–N7 | `RELIABLE` / `NOT_RELIABLE` / `NOT_YET_TESTABLE` |

**Served `reliability_status`:** the development label until N1 is met on sealed rows, then the sealed label. It is computed, never typed.

## 7. Leakage and sanity controls

| Control | Expected |
|---|---|
| Shuffle-target (values permuted within area, publication dates kept, full procedure rerun) | No advantage over PERSIST |
| Future shift (cutoff after the target's publication) | Within share rises far above the honest run |
| Round injected on or after the issue | Forecast unchanged |
| Feature snapshot used at another issue | `LeakageError` |
| Mutation check (`as_of`, lead, snapshot guard) | Guarding tests fail |

## 8. Failure

**On sealed data (once testable):**
- `REJECTED` for 75 %, or `NO` for beats-all, is a failure of the research claim.
- It is reported as such, with no re-tuning, re-splitting, tolerance change or row dropping.

**On development data:** a share below 0.75 is the expected outcome (Gate 1). It is reported, not treated as a reason to change the design.

**If DELTA-X never enters at any issue:** the exogenous route has failed under this rule, and the served model is whatever the rule selects.

## 9. Constants

| Constant | Value |
|---|---|
| Seed | 2026 |
| Inner draws | 2 000 |
| Outer draws | 10 000 |
| Block length | 3 |
| Ridge α | 10 |
| Spearman threshold | 0.30 |
| Minimum issues | 6 |
| Minimum inner quarters | 6 |
| Inner n_obs minimum | 4 |
| Conformal minimum | 8 residuals |
| Holm α | 0.05 |
