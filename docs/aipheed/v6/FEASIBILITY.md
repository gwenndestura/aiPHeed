# v6 Stage 2: Feasibility science and Gate 2

**Commands:**
- `python -I backend/scripts/v6_feasibility.py` → `v6/results/feasibility_oracles.csv`, `feasibility_route_filter.csv`, `feasibility_q.json`, `feasibility_run.txt`;
- the re-verification re-runs of `v2_diagnosis.py` and `v4_validate.py` (§0).

**Status:** all numbers are DEVELOPMENT (2021-Q2 … 2026-Q3, all seen).

## 0. Earlier runs re-verified (VERIFIED)

`v2_diagnosis.py` (E131/E136 alignment, noise, signals, pooling) and `v4_validate.py` (exogenous model, nested selection, leave-one-area-out) were re-executed this session.
- **Result:** `git status` / `git diff` of `docs/aipheed/v2` and `docs/aipheed/v4` were empty afterwards. Every saved result reproduced byte-for-byte.
- **E133–E136:** the backend's persistence equals E136's, and the v2 LL equals E131's local level on 272/272 rows (tests).
- **Fix found while re-verifying:** the first run of this stage's route R7 fitted q on an empty series. `V.fit` iterates over the 4 SWS areas only, so the oracle came out 0.87. It was found before any decision, fixed (direct fit on the national series), and re-run. The oracle is 0.28 / 0.52.

## a) Noise floor: oracle bound per route (perfect knowledge of the current true level)

**Dynamics:** q = 12.26 pp²/quarter on all data; **4.51** on calm data (rounds published before 2024).

| Route (definition fixed before computing; script header) | Lead 1 all / calm | **Lead 2 all / calm** | Lead 3 | Lead 4 | Passes ≥ 0.85 on both? |
|---|---|---|---|---|---|
| R1 frozen tolerance (1.645 × binomial SE) | 0.49 / 0.66 | **0.43 / 0.60** | 0.38 / 0.55 | 0.35 / 0.52 | **ELIMINATED** |
| R2 1.645 × SE from the published margin | 0.60 / 0.77 | **0.51 / 0.70** | 0.46 / 0.64 | 0.42 / 0.60 | **ELIMINATED** |
| R3 published 95 % margin (1.96 × SE_pub) | 0.68 / 0.85 | **0.59 / 0.78** | 0.53 / 0.73 | 0.49 / 0.68 | **ELIMINATED** |
| R4 nowcast h = 1, frozen tolerance | — | **0.57 / 0.73** (h = 1) | — | — | **ELIMINATED** |
| R4 nowcast h = 1, published margin | — | **0.81 / 0.93** (h = 1) | — | — | **ELIMINATED** (all-data 0.81 < 0.85); closest of all |
| R5 latent target (filtered true level), tolerance 1.645 × filter SD | 0.45 / 0.58 | **0.38 / 0.51** | 0.34 / 0.46 | 0.31 / 0.43 | **ELIMINATED**: denoising also shrinks the tolerance |
| R6 semiannual mean target | 0.37 / 0.54 | **0.32 / 0.48** | 0.29 / 0.44 | 0.26 / 0.40 | **ELIMINATED** |
| R7 national 4-area mean (q 6.56 / 1.46) | 0.34 / 0.59 | **0.28 / 0.52** | 0.25 / 0.47 | 0.22 / 0.43 | **ELIMINATED**, and not CALABARZON |
| R8 interval-overlap scoring | — | — | — | — | **ELIMINATED on validity:** a wider forecast interval passes more often (gameable) |
| R9 HIGH/LOW bands, R10 direction (v3) | — | c1 0.83 (degenerate: 97.5 % HIGH); d1 0.80 (base rate) | — | — | **ELIMINATED on validity** (v3 Task 2) |

## b) Sample size (v4 EVALUATION_DESIGN; VERIFIED `v4/results/v4_sample_size.json`)

- **Needed:** ±10 pp needs 72 effective observations, which is 22 target quarters × 4 areas (design effect 1.17); ±15 pp needs 32, which is 10 quarters.
- **Unseen today:** 0.
- **Arrival:** about 4 area rows per quarter → 10 quarters about **2029-05**, 22 quarters about **2032-05**.

## c) Signal: out-of-sample association with future change

| Evidence | Result |
|---|---|
| In-sample screen, 5 groups (v2 DIAGNOSIS Q3; block bootstrap, Holm) | No primary signal (Holm p ≥ 0.52). ONI significant only through the one 2023–24 episode: ρ ≈ 0.1 outside it. |
| **Out of sample:** v4 DELTA-X. Features admitted in-fold by a pre-declared stability rule; ridge on change; nested expanding window. Re-verified above. | Features entered at 34/84 fits, mostly ONI. **Lead-2 within 0.375 vs persistence 0.40; MAE 6.49 vs 5.98.** Inner MAE fell (4.43) while outer rose: overfitting signature. |
| Publication lag ≥ lead | Enforced by `as_of` and the snapshot guard (tests; mutation-checked) |
| Causal mechanism | Plausible mechanisms exist (prices → affordability; El Niño → rice supply; jobs → income), but none is supported out of sample with these n (INFERRED) |

## d) Alignment (Stage 1, VERIFIED)

- The fieldwork midpoint quarter equals the label for 23/23 rounds.
- **Lead 2 = 4.8–5.9 months from issue to target fieldwork,** and about **8.9 months from the newest measurement used to the target fieldwork.** This horizon is what makes the change unforecastable from history.

## e) Pooling

- **Dynamics homogeneous across areas:** slope F p = 0.96; q LR p = 0.16 (DIAGNOSIS Q5).
- **Area changes nearly uncorrelated:** mean ρ 0.06. So pooling helps estimate q and κ, but there is no common shock to borrow.
- **Leave-one-area-out (v4, re-verified):** LL-K 0.35 and DELTA-X 0.35 vs PERSIST 0.40. Balance Luzon 0.2–0.3. No generalisation gain.
- Pooled results are never CALABARZON measurements.

## f) Lower-noise constructs

- **R5 (latent level) and R6 (semiannual mean)** are defined from measurement properties, but both **lower** the oracle. Removing noise from the target also narrows its own precision-based tolerance, while the true-change variance over the horizon is untouched.
- **R7 (national mean)** has the same problem, and its claim is not CALABARZON.

## Gate 2: no route survives the declared filter

**Proof** (numbers above, VERIFIED):
- At Lead 2 the best oracle under any measurement-derived definition is **0.59 (all data) / 0.78 (calm)** (R3, published margin).
- The filter requires 0.85 on both.
- The binding quantity is the true-change variance over about 9 months (q·h), which no held indicator predicts out of sample (c).

**What could change the verdict** (exact requests: `DATA_REQUESTS.md`):
1. **A leading indicator** that explains ≥ 85 % of the 3-quarter true-change variance (Gate 1 of v2). The only untested candidate is regional quarterly LFS.
2. **Unseen quarters,** to test any claim at all (2029-05 at the earliest).
3. **SWS round documentation** (design effect): if real noise exceeds the binomial SE, a design-effect-adjusted margin is a legitimate measurement-derived tolerance. Its value is unknown until documented. It must not be estimated from the scored outcomes.

**Software work continues on the best available route:**
- the target is SWS area hunger;
- the primary tolerance stays **frozen**;
- R3 (published margin) is reported alongside as **PROPOSED, not adopted**;
- R4 (nowcast) is reported as a separate, non-Lead-2 objective.

## Single route most likely to yield a real, defensible 75 %

**R4: a one-quarter-ahead nowcast scored against SWS's published margin.**
- Oracle 0.81 (all data) / 0.93 (calm). Persistence reached 0.74 on development pairs (v3).
- It is the only route whose ceiling clears 75 % under both regimes. It is defined purely from SWS's own published precision.
- **Caveat:** it answers Lead 1, not the thesis's Lead-2 objective. It needs adviser sign-off and confirmation on unseen quarters.
