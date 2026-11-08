# E133 frozen protocol: forecasting breakthrough search

**Freeze.** Written and hashed **before** any E133 candidate was computed. The SHA-256 is in `runner/PROTOCOL_SHA256.txt`.
The only E133 computation run before the freeze is the reproduction of E132 (`runner/e133_reproduce.py`,
`out/e133_reproduction_check.json`: every E132 forecast reproduced to 4e-15; Lead-2 SEAS-LLM 0.607 / MAE 4.78 / RMSE 6.53 on 28 rows).

**Scope.** Branch `aiPHeed/corrected-data-pipeline`, start `9db56c5`. Offline only. Production, the dashboard, FIRI v2,
FIRI3 and every earlier seal are unchanged. Local commits only.

**Unchanged from E131/E132, never changed after results:**
- target: SWS involuntary hunger, 4 areas, 2021-Q2 … 2026-Q3 (`E110 sws_area_rounds.csv`, non-commissioned rounds);
- primary tolerance |f − y| ≤ 1.645 × binomial SE from the published margins;
- the 75 % requirement; leads per `backend/app/quarterly/target.py` (Lead k = quarter D − 1 + k, issue = first day of D);
- reliability rules N1–N7 (`e130_lib.numeric_reliability`);
- study window 2021+; no SWS/PSA/BSP "latest" web searches; no sws.org.ph.

**Data status.** Every 2021–2026-Q3 SWS value has been seen in earlier work. All walk-forward results are
**development evidence**. Confirmation is only prospective (§8).

## 1. Problem statement that drives the design

For 75 % within ±1.645·SE when the observation itself carries sampling error SE, the forecast error of the **true**
level must have SD ≤ ≈1.02·SE (≈2 points). E132 found that perfect knowledge of today's true level gives 0.35–0.55 at
Lead 2, so most of the error is true change over 2–3 quarters. E133 therefore attacks (a) how well the current true
level is estimated (pooling, non-sampling noise, design effects), (b) whether true change has a persistent/momentum
component, and (c) whether any trigger group carries information **before** the change, using representations that
E128–E132 did not try (one theory-signed driver per group inside the state equation, nowcasting with indicators
published after the latest SWS round, and the bottom-30 % income households' CPI).

## 2. Candidates (new in E133)

All are linear-Gaussian state-space models fitted by maximum likelihood on information available at the issue date
only, pooled over the 4 areas, with observation variance = published-margin SE² (+ τ² where stated).

| Id | Model | Addresses |
|---|---|---|
| HFM | Hierarchical factor model. State: common level c_t (random walk, variance q_c, extra variance b at the documented 2025-Q2 respondent-base break), constant area offsets α_a (prior N(0, 25)), area deviations d_a,t AR(1) with ρ and q_d. y_a,t = c_t + α_a + d_a,t + ε | Area-specific noise treated as level change (E132 per-area local level) |
| HFM-NS | HFM + non-sampling observation variance τ² (estimated) | Measurement disagreement beyond sampling (SWS vs OCTA MAE 5.2) |
| HFM-NS-DES | HFM-NS + post-break quarter-of-year design effect (E132's SEAS rule applied to pooled innovations: mean of post-break one-step innovations by quarter-of-year, shrunk n/(n+2), then refit) | 2025+ alternating survey design |
| HFM-TREND | HFM-NS-DES + damped slope on c_t (g_t = φ g_{t−1} + η_g, φ ∈ {0.5, 0.8} by likelihood) | Sharp increases continue (coping exhaustion); high-hunger under-prediction |
| HFM-X | HFM-NS-DES + theory-signed drivers in the transitions: c_t = c_{t−1} + Σ_g β_g z_g,t−1 + η_c; d_a,t = ρ d_a,t−1 + β_V (pov_a/pov̄ − 1) z_A,t−1 + η_d. β_g ≥ 0, prior N(0, 1²) pp per SD per quarter, penalized ML with the HFM-NS-DES variances held fixed | The five groups, inside the dynamics rather than as a residual corrector |
| HFM-X-B30 | HFM-X with the market driver taken from the **bottom-30 % income households' food CPI** instead of the all-households rice CPI | Purchasing power of the population that reports hunger |
| ENS133 | Mean of SEAS-LLM (E132) and HFM-NS-DES | Combination |

**HFM-X drivers (one per group, fixed here; standardized in-fold on all quarters ≥ 2021-Q2 published by the issue):**
- **A market:** mean over the 4 areas of the area rice CPI quarter-on-quarter % change (E131 regional CPI; quarter
  available 10 days after its last month). HFM-X-B30: bottom-30 % food CPI q/q % change, mean over the regions of
  the areas, same availability rule (acquired in E133, 2021+ only).
- **C climate:** tropical cyclones entering PAR in the quarter (`typhoons_PAR`, E119 point-in-time).
- **E employment/OFW:** `E1_unemployment_change_pp` (E119 point-in-time).
- **N news:** `news_gdelt_shortage_share` (E119 point-in-time).
- **V poverty/vulnerability:** area poverty incidence (latest PSA round published before the issue) scaling the
  market driver in the area-deviation equation (above).
- Missing standardized values = 0 (neutral). For transitions after the latest SWS quarter the driver of quarter t−1 is
  used if published by the issue (nowcast), otherwise the latest published value is held.
- Sign constraints from theory: higher prices, more storms, rising unemployment and more shortage news raise hunger.

**References re-run (unchanged):** PERSIST, CLIM, LLM, SEAS-LLM (E132, reproduced).

## 3. Evaluation sets and policies

- **P-DASH (primary)** and P-REL (secondary), as in E131/E132.
- **S-U (primary set):** rows with n_obs ≥ 8 (E132 "univariate set"; Lead 2: 40 rows, 10 target quarters,
  2024-Q1 … 2026-Q3, including the 2024 surge). Every E133 candidate is defined on all of S-U.
- **S-E132:** E132's shared rows (Lead 2: 28 rows), for direct comparison with SEAS-LLM 0.61.
- Reported per model × lead × policy × set: MAE, RMSE, bias, within tolerance, direction accuracy, 80 % coverage,
  by area, by observed-level tercile, sharp increases (y − y_latest > 2·SE).

## 4. Selection and validation rule (fixed)

- **E133 candidate:** the highest Lead-2 within-tolerance share on **S-U, P-DASH** among the E133 candidates and
  SEAS-LLM; ties → lower MAE.
- **Validated** only if, at Lead 2: N1–N7 pass on S-U (N3 baselines PERSIST, CLIM, LLM, SEAS-LLM) **and** N2 and N3
  pass on S-E132 (N3 baselines PERSIST, CLIM, PSA-ONLY, NLP-ONLY, RIDGE-ALL from the reproduced E132 run).
- **Maximum reliable lead:** consecutive validated leads from Lead 1.
- No result-driven change to models, drivers, grids, priors or rules. Any deviation goes to `DEVIATIONS.md`.

## 5. Trigger-group contribution (controlled ablation)

On HFM-X (and HFM-X-B30 for A): remove one group at a time (β_g = 0), all groups, and each group alone. Report
Δ MAE and Δ within on S-U at Leads 1–4. A group's contribution counts as **demonstrated** only if removing it worsens
Lead-2 MAE and within on S-U **and** the paired cluster-bootstrap p (target quarters) for squared error < 0.10.
The report separates: investigated / useful information (diagnostic screen) / demonstrated.

## 6. Diagnostics (never candidates)

- **D1 achievability bound:** required forecast SD of the true level per lead; the fitted true-change variance over
  the horizon from HFM-NS; the share of true-change variance a predictor must explain to reach 75 %.
- **D2 leading-indicator screen:** every point-in-time numeric feature of E119 (FIRI families A1–H1) and the area CPI
  items, at the issue (Lead 1 and 2), against the later change in national SWS hunger; Spearman with 10 000
  permutations (seed 133), Holm correction. In-sample, diagnostic only.
- **D3 event analysis:** each Lead-2 sharp increase (S-E132 and S-U): information at issue, every group's values,
  each model's forecast, and whether any signal moved before the increase.
- **D4 high-hunger bias:** bias by observed-level tercile for the ex-post smoothed true level (ORACLE-LEVEL): the part
  of the "high-hunger under-prediction" that any forecaster of the true level must show because high observations
  carry positive sampling error (selection on the noisy outcome), versus the part due to lag.
- **D5 OCTA as an early channel:** for each issue, whether an OCTA reading was published before the next SWS release
  (count only; no model, because of 9 readings).

## 7. Provincial layer

Inventory of every provincial measurement held (PFDR 2021/2023, FNRI FIES 2021 Batangas/Cavite, poverty 2021/2023/2025,
FSSI news). Test whether a quarterly provincial target or validation exists. Provincial outputs stay labelled
**model-based**: selected model's Balance Luzon forecast × E131 relative food deprivation. No SWS copies to provinces.

## 8. Prospective seal

Issued 2026-11-01 with information published by then; targets 2026-Q4 … 2027-Q3; 4 areas; every E133 candidate's
point forecast and 80 % interval; write-once; hash recorded; scored with the primary criterion only.

## 9. New data (E133)

Only: PSA OpenSTAT bottom-30 % income households' CPI (table `DB/2M/PI/BIH/2018NEW/0022M4ABIR1.px`), regional
geolocations, items all / food / rice, **Year ≥ 2021 only** in the query (no pre-2021 row is downloaded), saved raw
with query and hash. No other values are fetched. Other sources are inventoried by provenance only.
