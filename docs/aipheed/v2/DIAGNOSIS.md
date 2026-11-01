# v2 Step 1: Diagnosis and Gate 1

**Tags:** VERIFIED = computed by the command below, output saved; INFERRED = reasoning from verified numbers or code; NOT VERIFIED = not checked.

**Command:** `python -I backend/scripts/v2_diagnosis.py` (backend venv, seed 2026, 5 000 bootstrap / permutation draws).
**Outputs:** `docs/aipheed/v2/results/diagnosis_summary.json` (all numbers below), `diagnosis_run.txt`, `diag_su_rows_with_oracles.csv`, `diag_signal_table.csv`, `diag_q3_leading_signals.csv`.
**Data:** `backend/data/forecasting/sws_area_rounds.csv`, SHA-256 `936d0c26…f19ec2`. All of it had been seen in earlier experiments, so every number here is **DEVELOPMENT** evidence.

**Frozen definitions used, unchanged (PROTOCOL_LOCK.md):**
- target y(a, q): SWS involuntary hunger by area (T1);
- tolerance = 1.645 × SE (T1–T4);
- P-DASH issue and Lead k = D − 1 + k (E1);
- S-U rows, n_obs ≥ 8 (E2);
- N1–N7 (R1–R2).

**Lead-2 S-U scale:** 40 rows over 10 target quarters (2024-Q1 … 2026-Q3). The newest SWS reading is h = 3 quarters before the target on 36 rows and h = 2 on 4 rows. Median tolerance is ±3.78 pp.

---

## Q6 first: target, lead and issue-date alignment (VERIFIED)

A silent alignment error would explain failure better than any model choice, so this was checked before anything else.

| Check | Result |
|---|---|
| P-DASH rows rebuilt from scratch with backend code (`as_of` → quarter table) vs the E136 research rows | 272 = 272 rows, all matched. Target, y_true, y_latest, h and n_obs all identical; tolerance max diff 4e-16. |
| The dashboard clock (`app/quarterly/target.py`) at 4 test instants equals Lead 2 = D − 1 + 2, with origin = first day of D | True |
| Rounds used at an issue that were published on or after it | 0 |
| A planted one-quarter target shift is detected by the same comparison | 272 of 272 rows flagged, so the check is not vacuous |
| Partial quarters at issue (only one of a quarter's two rounds published yet) | 8 area-quarter cases, counted with the rounds then published, as the protocol says (E1 "Partial quarters") |

**Verdict Q6: no alignment bug.** The failure of earlier models is not an artefact of misaligned rows.

## Q1: Noise floor and oracle bound

**Sampling error (VERIFIED).**
- Round SE ranges from 1.29 to 2.75 pp (median 2.12).
- Quarter tolerance ranges from ±1.78 to ±4.52 pp (median ±3.21).

**Is the binomial SE the whole noise?** No, judging by the 12 same-quarter round pairs (2021-Q2, 2022-Q2 and 2025-Q2, 4 areas each):
- their differences have an RMS z of 1.84 against the binomial SE (χ² p = 6e-5);
- so the real round-to-round noise is about 1.8 times the SE behind the tolerance, unless hunger moves materially within one to three months. The two cannot be separated with these data (INFERRED).
- **Consequence:** the frozen tolerance is tight relative to the survey's real repeatability. It is not changed (frozen); it is a reason the target is hard.

**Revisions:** none are recorded; each round has one published value. Whether SWS ever revises: NOT VERIFIED.

**How big are the moves to be forecast?** All area pairs, full data:

| h (quarters) | Pairs | SD of change (pp) | Median \|change\| | Median tolerance | Share of changes already inside tolerance |
|---|---|---|---|---|---|
| 1 | 68 | 4.73 | 2.80 | 3.35 | 0.49 |
| 2 | 64 | 5.98 | 3.30 | 3.25 | 0.45 |
| 3 | 60 | 6.54 | 4.15 | 3.21 | 0.42 |
| 4 | 60 | 6.84 | 3.80 | 3.32 | 0.48 |

The last column is the ceiling of any "no change" forecaster at that horizon. At h = 3, which is Lead 2, it is **42 %**.

**Oracle bounds on the S-U rows (VERIFIED).** Each oracle uses hindsight that no real forecaster has. "Known level" assumes a pooled local level fitted on all data (true-level innovation variance q = 12.3 pp² per quarter).

| Lead | n | PERSIST | O-NOW: knows today's true level (smoothed with hindsight) | O-LOCAL-MEAN: mean of the two neighbouring quarters | O-AREA-MEAN: full-sample area mean | Analytic: knows today's true level exactly | Ceiling: knows the target's true level |
|---|---|---|---|---|---|---|---|
| 1 | 44 | 0.477 | 0.545 | 0.455 | 0.455 | 0.493 | 0.90 (analytic) / 0.977 (empirical) |
| **2** | **40** | **0.400** | **0.350** | **0.450** | **0.475** | **0.425** | 0.90 / 0.975 |
| 3 | 36 | 0.361 | 0.417 | 0.444 | 0.444 | 0.382 | 0.90 / 0.972 |
| 4 | 32 | 0.375 | 0.438 | 0.469 | 0.406 | 0.351 | 0.90 / 0.969 |

**What 75 % requires, mechanically:**
- 75 % within 1.645 SE needs the forecast error of the target's true level to have SD ≤ 1.022 × SE: **2.35 pp** at Lead 2 (median).
- The true level moves by an SD of **6.06 pp** over the Lead-2 horizon.
- So a forecaster must predict about **85 % of the variance of the true 3-quarter change** (Lead 1: 78 %; Lead 3: 88 %; Lead 4: 90 %).
- Knowing today's true level exactly gives only **42.5 %** at Lead 2.

**Q1 answer:**
- The bound for any forecaster that uses the hunger history alone, even with perfect knowledge of the current true level, is **about 43 % at Lead 2**. This is far below 75 %.
- 75 % is not impossible in principle: the noise-only ceiling is 90 %. It is reachable **only** with information that predicts ≈ 85 % of the true change three quarters ahead.

## Q2: Why existing models fail

**Error decomposition at Lead 2, S-U** (VERIFIED, E136 predictions):

| Model | MSE | Bias | Bias² share of MSE | SSE share in the 2024 surge (16 rows) | Bias in surge | Bias 2025–26 (24 rows) | Top 10 % rows' share of SSE |
|---|---|---|---|---|---|---|---|
| PERSIST | 59.4 | −3.07 | 0.16 | **0.71** | −8.49 | +0.54 | 0.53 |
| SEAS-LLM | 57.4 | −3.19 | 0.18 | **0.80** | −9.00 | +0.68 | 0.57 |
| HFM-X | 41.2 | −2.53 | 0.15 | 0.57 | −4.35 | −1.32 | 0.54 |

**Measurement noise** (SE² of the latest reading plus SE² of the target) is **15 %** of persistence's Lead-2 MSE. The other 85 % is true change over the horizon.

**Why the bias is about −3** (INFERRED from VERIFIED numbers):
- On these rows the true level rose by +3.17 pp on average over the horizon (smoothed); persistence's bias is −3.07.
- The bias is the 2024 surge: −8.5 during the surge and +0.5 afterwards.
- So it is **not a stable, systematic bias**, and a learned bias correction would add about +3 to every forecast. That would have hurt in 2025–26.

**Why the high-tercile bias is about −7.7** (14 rows):

| Part | Value |
|---|---|
| Selection: high observations carry positive sampling error, which any true-level forecaster shows | −1.88 |
| Lag: the true level rose by about +6.2 pp over the horizon on those rows | −5.78 |

So it is mostly the lag behind the 2024 surge.

**Dynamics** (VERIFIED, area-demeaned, consecutive-quarter pairs):

| Property | Result | Reading |
|---|---|---|
| Autocorrelation of levels, lags 1–4 | 0.70, 0.50, 0.44, 0.33 | Persistent |
| Autocorrelation of quarter changes, lags 1–4 | −0.27, 0.09, −0.02, −0.09 | Lag 1 negative is what sampling noise in a random walk produces; no momentum, so no trend to extrapolate (TREND-D fails for this reason) |
| Dickey–Fuller t (constant), per area | −0.75 to −1.45 (pooled within: −2.22) | Unit root not rejected at 5 % (critical value ≈ −3.0); low power at n ≈ 17 |
| Mean-reverting true level (φ) vs local level, ML | φ = 0.80, LR = 7.3 | In-sample support for reversion, **but** see below |
| Lead-2 change regressed on the latest value's distance from the expanding mean | slope −0.98, p = 3e-8 | Looks like strong regression to the mean |
| **The same reversion, estimated only from data known at each issue (out of sample)** | within 0.375 vs persistence 0.400; MAE 5.97 vs 5.98 | **No gain.** The in-sample "reversion" is the 2024 level shift seen from both sides, not a forecastable force. |
| Forecast = expanding area mean | within **0.15**, MAE 7.75 | Mean reversion towards history is badly wrong after a level shift |
| Seasonality: quarter-of-year mean change (Kruskal–Wallis) | all p = 0.94; pre-break p = 0.53; post-break p = 0.44 (n = 4–8 per cell) | **No detectable seasonality** |
| Structural breaks: mean level | pre-surge 11.8, surge 20.4, 2025–26 21.5 (Welch p < 1e-14) | A **level shift** in 2024 that persisted; the 2025-Q2 respondent-base change coincides with the new level |

**Q2 answer:** the series behaves like a noisy random walk with one large level shift.

| Component | Forecastable? |
|---|---|
| Measurement noise in the anchor | **Yes, a little.** Filtering can reduce part of the 15 % noise share. |
| Level error | The best anchor is the latest (filtered) reading |
| Trend / turning points | **No.** No momentum; changes are not autocorrelated beyond the noise signature. |
| Regression to the mean | **No.** In-sample artefact of the level shift; zero out-of-sample gain. |
| Seasonality | **No** |
| Surge / outliers | **No.** One event carries 71–80 % of the squared error; it was not preceded by a repeatable signal (Q3). |

## Q3: Is there a genuine leading signal?

**Design:**
- **Target:** the future change y(target) − y_latest, area rows, Leads 1 and 2. P-DASH issues 2021-Q3 … 2026-Q4, n_obs ≥ 2.
- **Features:** only values published before the issue (area CPI available 10 days after the quarter; E119 point-in-time table; poverty by release date).
- **Pre-chosen primary feature per group** (the HFM-X drivers, fixed in E133 before results): rice CPI YoY (A), typhoons in PAR (C), unemployment change (E), GDELT shortage-news share (N), area poverty (V). Secondary features are exploratory.
- **Statistics:**
  - Spearman correlation;
  - 95 % CI by block bootstrap over issue quarters;
  - p by block permutation (feature blocks permuted across issues);
  - Holm correction, (i) over the 10 primary tests and (ii) over all 24.

**Results** (`diag_q3_leading_signals.csv`, VERIFIED):

| Group | Primary feature | Lead 1 ρ [95 % CI] | Lead 2 ρ [95 % CI] | Smallest Holm p (primary family) |
|---|---|---|---|---|
| A market | rice CPI YoY | 0.33 [−0.09, 0.61] | 0.21 [−0.30, 0.62] | 0.52 |
| C climate | typhoons PAR | −0.25 [−0.52, 0.05] | −0.30 [−0.60, 0.06] | 1.0 |
| E employment/OFW | unemployment change | 0.09 [−0.21, 0.37] | 0.11 [−0.24, 0.44] | 1.0 |
| N news/NLP | shortage share | 0.11 [−0.21, 0.43] | 0.13 [−0.22, 0.49] | 1.0 |
| V poverty | area poverty | −0.03 [−0.47, 0.44] | −0.20 [−0.71, 0.36] | 1.0 |

**No primary signal survives** (minimum Holm p = 0.52).

**One secondary feature survives Holm over all 24 tests:** ONI (El Niño index):
- Lead 1: ρ = 0.48, Holm p = 0.010;
- Lead 2: ρ = 0.51, Holm p = 0.055.

**Robustness of the ONI association** (VERIFIED, `Q2Q3_robustness`):

| Rows | Lead 1 ρ | Lead 2 ρ |
|---|---|---|
| All | 0.48 | 0.51 |
| Targets outside 2024 | **0.12** | **0.10** |
| Issues before 2023-07 | −0.08 | 0.29 |
| Issues from 2025 | −0.02 | −0.14 |

- ONI ≥ 0.5 was seen at issues only in 2023-Q3 … 2024-Q2 (one El Niño) and 2026-Q2.
- **So the association is one episode:** the 2023–24 El Niño followed by the 2024 surge. That is one event, not a repeatable relation that can be estimated.
- It was also tried before as a model: E134-ONI reached 0.50 within at Lead 2, post-hoc (E134 package).

**Regional quarterly LFS** (the untested candidate from earlier reports) is not held locally beyond the national/regional unemployment series above. It would need an external download, which is outside this session's authority, so it is NOT tested.

**Q3 answer:** **no genuine, repeatable leading signal of hunger change exists in the data held.**

## Q4: Is the effective sample size enough?

| Lead | S-U rows | Independent target quarters |
|---|---|---|
| 1 | 44 | 11 |
| 2 | 40 | 10 |
| 3 | 36 | 9 |
| 4 | 32 | 8 |

**Clustering** (VERIFIED):
- Within-quarter ICC of the "within" indicator (persistence, Lead 2) is 0.056, a design effect of 1.17.
- So 40 rows carry about 34 effective observations.
- At a true share of 75 % the 95 % CI half-width is **±14.5 pp**.

**Quarters needed at Lead 2** (4 areas per quarter, design effect 1.17):

| Goal | Target quarters |
|---|---|
| CI half-width ±10 pp | 22 |
| CI half-width ±5 pp | 85 |
| Show > 75 % with 80 % power if the true share is 0.90 | 16 |
| … if it is 0.85 | 39 |
| … if it is 0.80 | 165 |

**Schedule:**
- Median SWS publication lag is about 32 days after quarter end; 2022-Q1 and 2025-Q1 had no round.
- The first unseen Lead-2 target is **2026-Q4**, expected about 2027-02.
- If every quarter has a round:
  - 6 unseen targets are complete about 2028-05;
  - **10 (the N1 minimum) about 2029-05**;
  - 20 about 2031-11.
- The frozen adoption window (lock W2) states the earliest decision as 2029-Q3, which is consistent.

**Q4 answer:** **no.**
- Even a model that truly achieved 75 % could not be shown to do so on 10 quarters: the CI is ±14.5 pp.
- Confirmation needs ≥ 10 unseen quarters for N1, and 16–39 quarters for a decisive test, depending on the true share.

## Q5: Is pooling the SWS areas legitimate?

**Correlation of quarter changes between areas:** mean off-diagonal 0.06. Metro Manila–Balance Luzon is 0.35 and Visayas–Mindanao 0.38; the rest are near 0 or negative. Areas do **not** share shocks; there is no common factor to borrow for forecasting one area from another.

**Homogeneity of dynamics:**

| Parameter | Per-area values | Pooled | Test |
|---|---|---|---|
| Reversion slope | −0.15 to −0.31 | −0.22 | F = 0.10, p = 0.96 |
| Local-level innovation variance q | 4.0 to 22.9 | 12.3 | LR = 5.19 (3 df), p = 0.16 |

Homogeneity is not rejected.

**Valid** (INFERRED):
- pooling the 4 areas to estimate shared **dynamics parameters** (the innovation variance, a noise multiplier, a reversion weight): this raises the information per parameter fourfold, and homogeneity is not rejected;
- scoring all 4 areas as independent rows within a quarter, with the clustering handled by bootstrapping target quarters, as the frozen protocol does.

**Not valid:**
- using another area's value as a measurement of Balance Luzon or CALABARZON;
- copying the Balance Luzon value to the 5 provinces or 142 LGUs as if they were independent measurements;
- counting the 4 areas as 4 independent quarters for N1.

## Gate 1 verdict

> **75 % within tolerance at Lead 2 is NOT ACHIEVABLE with existing measurements.**

**Numbers:**
1. **Required vs available:**
   - 75 % requires a true-level forecast error SD ≤ 2.35 pp, against a true 3-quarter change SD of 6.06 pp. A forecaster must predict about **85 % of the true change variance**.
   - Perfect knowledge of today's true level gives **42.5 %** (analytic) and 35–48 % (hindsight oracles).
   - The best history-only forecaster cannot exceed about 43–48 %.
2. **No leading signal:** none of the 5 groups predicts the change (primary Holm p ≥ 0.52). The one surviving secondary association (ONI) is a single 2023–24 episode (ρ ≈ 0.1 outside it).
3. **Insufficient n:** even a genuine 75 % model could not be confirmed on 10 quarters (±14.5 pp).

**Qualification:**
- 75 % is not mathematically impossible: the noise-only ceiling is 90 %.
- It becomes achievable only with a measurement that predicts ≈ 85 % of three-quarter hunger change, and no such measurement is held.
- Any v2 model therefore targets the forecastable remainder: a better anchor (noise filtering). It is expected to stay well below 75 % (INFERRED). The verdict will be re-tested only on unseen quarters.

**What Step 2 may build on** (only what the diagnosis supports):
- the latest reading as anchor (delta form);
- noise filtering with an observation variance that may exceed the binomial SE (Q1);
- dynamics parameters pooled across areas (Q5);
- intervals from out-of-sample residuals.

**Rejected by the diagnosis:**
- seasonality (Q2);
- trend extrapolation (Q2);
- a fixed bias correction (Q2: sign flips across periods);
- exogenous drivers (Q3);
- reversion towards the historical mean (Q2: zero out-of-sample gain). It enters Step 2 only as a falsifiable candidate tuned on inner folds, because it has in-sample support.
