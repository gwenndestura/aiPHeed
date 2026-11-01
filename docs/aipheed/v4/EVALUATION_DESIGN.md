# v4 Step B: Sample size and evaluation design

**Tags:** VERIFIED / INFERRED / NOT VERIFIED. The sample-size numbers are recomputed by `backend/scripts/v4_validate.py` and saved to `v4/results/v4_sample_size.json`.

## 1. How many Lead-2 test observations a 75 % claim needs

95 % CI half-width at p = 0.75: n_eff = 1.96² × 0.75 × 0.25 / hw².
- **±10 pp:** n_eff = 72.0.
- **±15 pp:** n_eff = 32.0.

| Target option | Design effect | Rows for ±10 pp | Target quarters for ±10 pp | Rows for ±15 pp | Target quarters for ±15 pp | Unseen rows available today | When the ±15 pp test becomes possible | When the ±10 pp test becomes possible |
|---|---|---|---|---|---|---|---|---|
| **SWS, 4 areas** (primary) | 1.17 (ICC 0.056 of within-hits across areas in a quarter; DIAGNOSIS Q4) | 85 | **22** | 38 | **10** | **0** | 10 future Lead-2 targets, 2026-Q4 … 2029-Q1 → about **2029-05** | 22 targets, 2026-Q4 … 2032-Q1 → about **2032-05** |
| SWS, Balance Luzon only | 1 per quarter, before serial correlation | 72 | 72 | 32 | 32 | 0 | 2026-Q4 … 2034-Q3 → about 2034-11 | about 2044 |
| PSA, FNRI or CBMS provincial | — | — | — | — | — | — | Never: no Lead-2 series | Never |

**Assumptions behind the dates:**
- They assume a round every quarter and a 32-day median lag (VERIFIED, DIAGNOSIS Q4).
- SWS skipped Q1 in 2022 and 2025, so slippage of a quarter or more per missed round is possible (INFERRED).
- The frozen N1 minimum (10 quarters, 40 rows) coincides with the ±15 pp design. The frozen W2 decision date is 2029-Q3.

**Serial correlation:**
- Lead-2 errors of consecutive issues share 2 of 3 horizon quarters (h = 3), so they are autocorrelated.
- CIs therefore use a **moving-block bootstrap over target quarters** (block length 3, the horizon) as well as the cluster bootstrap. If autocorrelation is positive, the effective n is smaller than the table states (INFERRED).

## 2. Three disjoint tiers (physically separated, hashed)

| Tier | Contents | Use | File (hash in `tests/unit/test_v4_core.py`) |
|---|---|---|---|
| **TRAIN** | All P-DASH rows whose target is ≤ 2023-Q4 (published before 2024-04-30): inner validation for selection, stability-rule features and ridge coefficients. Nested expanding window: at each issue only rows whose truth is known at that issue. | Fitting and inner selection | `v4/tiers/TRAIN_rows.csv` |
| **DEVELOPMENT-TEST** | The frozen S-U rows (n_obs ≥ 8; Lead 2: 40 rows, 10 target quarters, 2024-Q1 … 2026-Q3) | Design iteration; **non-confirmatory**. Already seen in E110–E136, v2 and v3. | `v4/tiers/DEVTEST_rows.csv` |
| **SEALED CONFIRMATION** | (a) **Withheld recent quarters: none.** All quarters through 2026-Q3 were seen; 0 < 6 independent unseen quarters. (b) **Every future target from 2026-Q4.** (c) **Held-out area set: none sealable.** All 4 areas were seen; a leave-one-area-out check is run on development data only. | Confirmation, opened once per quarter by `v4_score_sealed.py`, access logged | `v4/sealed/V4_PROSPECTIVE_SEAL.csv` + `V4_SEAL_SHA256.txt` |

**Pooling:**
- Dynamics parameters (q, κ) and ridge coefficients are pooled across the 4 areas, because homogeneity is not rejected (DIAGNOSIS Q5: slope F p = 0.96; q LR p = 0.16).
- Pooled results are **never** presented as a CALABARZON measurement. Balance Luzon is a broader-area reference.

## 3. Minimum n per claim

| Claim | Test | Minimum before it is testable | Today |
|---|---|---|---|
| "≥ 75 % within tolerance at Lead 2" (frozen) | Share within; one-sided 95 % lower bound ≥ 0.75 for "confirmed"; upper bound < 0.75 for "rejected" | N1: 10 target quarters / 40 rows | **NOT YET TESTABLE** (0 unseen) |
| The same, amended tolerance (if signed) | Same | Same | NOT YET TESTABLE; not adopted |
| "Beats every other model" | Paired block-bootstrap difference vs each baseline, one-sided α = 0.05, Holm across baselines | N1 | NOT YET TESTABLE |
| Lead k reliable | Frozen N1–N7 | N1 | NOT YET TESTABLE |

**The earliest any confirmatory claim can be tested is about 2029-05** (10 unseen quarters), with a ±15 pp CI. **A ±10 pp CI needs about 2032-05.**
