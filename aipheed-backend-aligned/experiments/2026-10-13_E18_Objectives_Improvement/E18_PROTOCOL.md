# E18 Pre-registered Protocol (frozen before any E18 comparison)

**Basis.**

- **Requirements:** Chapter I Objectives only (`OBJECTIVES_EXTRACTION.md`).
- **Prior evidence:** the E13–E17 v3 reports. **Not blind:** all 2021–2025 quarters have been examined before.
- **Data:** eligible observations through 2025-Q4, plus the **January–June 2026 sources authorized by you on 2026-10-13** (`DATA_AUTHORIZATION_RECORD.md`).
- **Previously seen 2026 values.** The two 2026 SWS values and part of the 2026 CPI file were viewed during the authorization check, before this freeze. 2026 targets are therefore **previously viewed, not an untouched holdout**, and are always reported separately.

**Freeze.** The SHA-256 of this file is in `runner/PROTOCOL_SHA256.txt`. Every script refuses to run if it changes. No candidate, feature, setting or rule may be changed afterwards without a new protocol.

## 1. One information-set convention for every target and horizon

| Item | Definition |
|---|---|
| Information set for target quarter T at horizon h | Observations of quarters ≤ T − h (CPI, SWS, news and government features) |
| Training pairs | Target quarters q ≤ T − h, with features from the information set of q − h |
| The 2027-Q1 case | Authorized data end at 2026-Q2 for SWS and CPI, so **h = 3 is the primary horizon** |
| Horizons evaluated | 1 to 5, each one separately. **A result at one h never stands in for another.** |
| News and government features | `features_fused` exists only up to 2025-Q4; 2026 news is not authorized. Models that need news can be **tested only on targets whose information set ends by 2025-Q4**, and **cannot produce a 2027-Q1 forecast.** |
| 2026 values | H: 2026-Q1 = March 2026 round, 2026-Q2 = June 2026 round (production series). F: the mean of the three monthly YoY values (the same aggregation as `openstat_fetcher._to_quarterly_avg`). D = F − the five-province mean, only when all five are present. S1 = H + 2D. |

## 2. Classification target (Objectives 2 and 4): the implemented label, HIGH if S1 > 14.6

**Features at cutoff c:**

- NLP (9): row c of `features_fused`.
- Government (36): row c, excluding `poverty_incidence` (its timing cannot be established).
- `H_last`: the latest production-series observation ≤ c.
- `D_c`, `F_c`, `F5_c` (five-province mean F).

| ID | Arm | Definition | Role |
|---|---|---|---|
| P | Naive persistence | The province's label in the latest labelled quarter ≤ c | **Chapter I baseline I** |
| B2 | PSA-only indicator | Logistic regression on the 20 PSA features | **Chapter I baseline II** |
| B3 | NLP-only sentiment | Logistic regression on FSSI, FSSI_lag1, FSSI_lag2, FSSI_accel | **Chapter I baseline III** |
| B4 | Logistic regression | Logistic regression on all 46 inputs (NLP + government + H_last) | **Chapter I baseline IV** |
| S5 | LightGBM, government only | Default LightGBM on the 36 government features | SOP context (H3 lists six comparisons). Reported; not a rule baseline. |
| S6 | LightGBM, NLP only | Default LightGBM on the 9 NLP features | SOP context. Reported; not a rule baseline. |
| MAJ | Training majority | — | Reference |
| M | Current governing LightGBM (MODEL-B2) | Defaults with scale_pos_weight; 46 inputs | Reference: the existing model |
| **N1** | Structural rule | HIGH if H_last + 2·D_c > 14.6 | New, selectable |
| **N2** | Structural rule with shrinkage | HIGH if H_last + 2·D̂ > 14.6. D̂ = ridge(α = 1) of D(q) on D(q − h), trained on pairs ≤ T − h. | New, selectable |
| **N3** | Structural logistic regression | Logistic regression on [H_last, D_c] | New, selectable |
| **N4** | Constrained, tuned LightGBM | Features [H_last, D_c, F_c, F5_c, FSSI, FSSI_lag1, cpi_dev, unemployment_rate]. max_depth 2, num_leaves 3, learning_rate 0.05, scale_pos_weight balanced, random_state 42. **Inner tuning on training rows only:** {min_child_samples ∈ {5, 10}} × {n_estimators ∈ {50, 150}}, scored by log loss on the last 3 training target quarters (each fold fit on the earlier rows). | New, selectable |

**Logistic regression settings:** median imputation and scaling fitted on training rows; C = 1.0; no class weights; threshold 0.5. Single-class training gives a constant prediction.

**Minimum training:** 8 labelled training quarters.

**Test sets:**

| Set | Contents | Status |
|---|---|---|
| **A (primary)** | Labelled targets with information ≤ 2025-Q4 | Every arm available |
| **B (extension)** | Set A plus 2026-Q1 and 2026-Q2 targets | P, MAJ, N1, N2 and N3 only; descriptive (previously viewed) |

**Selection rule for each h (on set A).** A new candidate N1–N4 is selected over persistence only if **all** of these hold:

1. Its accuracy is ≥ persistence and ≥ every Chapter I baseline (B2–B4), **and** its balanced accuracy is ≥ persistence and B2–B4 (where defined).
2. Its per-quarter accuracy is greater than persistence's in **more** quarters than it is lower.
3. Its accuracy in the later half of the test quarters is not below persistence's.
4. Its accuracy stays ≥ persistence's in **every** leave-one-quarter-out subset.
5. Its configuration is fixed (true for all arms by this freeze).

**Fewer than 5 test quarters means "insufficient evidence".** If several candidates pass, the highest balanced accuracy wins, then the highest accuracy.

**Reliability working criterion** (E18 rule; **Chapter I defines none; needs adviser approval**). Horizon h is "supported" only if a candidate is selected **and** set A has ≥ 8 test quarters **and** ≥ 5 HIGH and ≥ 5 LOW test cases. **The maximum supported lead time is the largest such h, or "none".** No absolute accuracy threshold is used.

**Diagnostics (descriptive):**

- within-quarter differentiation: the SD of predicted probability across the 5 provinces, and the number of distinct predicted labels;
- agreement with persistence;
- share predicted HIGH;
- mean |SHAP| (LightGBM `pred_contrib`) for M and N4 at h = 1 and h = 3.

## 3. Continuous targets (regional hunger H; provincial F; relative pressure D)

**Candidates:** the E17 v3 frozen sets (C1–C7, C7a/b; F1–F4; D1–D5) **plus two new level-shift candidates for H:**

| ID | Candidate |
|---|---|
| **C8** | Mean of the last 4 observed quarters ≤ T − h |
| **C9** | EWMA (α = 0.5) over the observed quarters ≤ T − h |

- **Rule:** E17 v3's frozen rule, conditions 1–5, against carry-forward for H and against every baseline for F and D.
- **Data:** targets through **2026-Q2**.
- **Primary:** h = 3.
- **Also reported:** h = 1–5, and the same results with 2026 targets excluded.
- **Fewer than 8 origins means "exploratory only".**

**E17 v3 frozen-candidate holdout.** E17 v3's exact frozen candidates (its code is copied here and its hash recorded) are scored on the 2026-Q1 and 2026-Q2 targets at h = 5, without refitting choices. **This is descriptive only** (two quarters, previously viewed).

## 4. The 2027-Q1 forecast (h = 3; information ≤ 2026-Q2)

- **H, F and D:** the selected candidate, or the baseline.
- **Classification label:** the selected candidate **only if it needs no news input.** Otherwise persistence (the 2026-Q2 label), with this limitation stated.
- **Labels on every output:** what it predicts, and "not a forecast of provincial food insecurity".
- **Uncertainty:** no interval unless it is defensible.

## 5. Dashboard (development only)

- An **isolated copy** of the frontend in `E18/dashboard_dev/`. `frontend/` and `backend/` are not changed.
- A research page reads `e18_dashboard.json`, generated from this experiment's outputs.
- It shows separate layers (regional hunger, provincial F, D, the constructed label), metrics, baseline comparisons, lead-time status and insufficient-data states.
- Verification: frontend tests, a build and a local preview. **No deployment.**

## 6. Seeds and order

| Item | Value |
|---|---|
| LightGBM | random_state 42 |
| Bootstrap | Not used for claims when n < 8 |
| Seal | Predictions are sealed (SHA-256) before scoring |
| Reproducibility | Two runs; byte-identical outputs required |
