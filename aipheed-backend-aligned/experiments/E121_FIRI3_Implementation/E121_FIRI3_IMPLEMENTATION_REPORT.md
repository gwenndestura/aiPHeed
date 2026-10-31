# E121 FIRI3 implementation report

**Status.** FIRI3 is implemented as a **candidate** index. FIRI v2 (`firi.py`) remains the served index, untouched. No route, dashboard or model change was made, no model was trained, and nothing was pushed or deployed.

**FIRI3 is a relative composite.** It is not a probability, and **not validated** as a provincial food-insecurity prediction.

## 1. What was built

| Item | Location |
|---|---|
| Frozen protocol (SHA-256 8a431a9d…) | `E121_FIRI3_PROTOCOL.md`; `runner/PROTOCOL_SHA256.txt`; `firi3.PROTOCOL_SHA256` |
| FIRI3 module (pure computation; independent of `firi.py`) | `backend/app/ml/inference/firi3.py` |
| Runner: inputs, results, contributions, analyses, snapshots | `runner/run_e121.py` |
| Snapshots, one per origin, immutable with a hash manifest | `snapshots/<origin>/` (23, all `retrospective`) |
| Tests | `backend/tests/unit/test_firi3.py` (23), `backend/tests/integration/test_e121_firi3.py` (5) |
| Design issues (not applied; need approval) | `E121_DESIGN_ISSUES.md` |

### `firi3.py`

| Level | What it does |
|---|---|
| Inputs | `validate_inputs` refuses SWS / hunger / H1 / FIRI series, rejects pre-2021 rows, and checks provincial units |
| Level 1 | `_dynamic`: as-of value, staleness ≤ 3 quarters, direction / abs, mid-rank against ≥ 8 earlier available observations. `_rank5`: latest published year, all five provinces, cross-province mid-rank. |
| Level 2 | `indicator_scores`: components averaged, each counted once; indicator mean; at least half of components; records component scores and feature counts |
| Level 3 | `overall`: equal-weighted mean; provincial ≥ 4 of 6, regional ≥ 4 of 5; band; leave-one-indicator-out range; verification share; contributing features |

**Inputs** are the same tables E120 used, from the E119 and E118 cleaned data, via `E120.load()`. The runner tags each observation with its source (`series @ unit`) and dataset id.

## 2. Results

| | Provincial | Regional |
|---|---|---|
| Computable FIRI3 | **75 of 115** province-quarters (65%), from 2023-Q1 | **10 of 23** quarters (43%), from 2024-Q2 |
| Indicators per computed score | 4: 54, 5: 13, 6: 8 | 4: 1, 5: 9 |
| Score range | 0.268–0.756 (mean 0.487) | 0.331–0.627 (mean 0.465) |
| Bands | usual or below 42; above usual 30; elevated 2; high 1 | usual or below 6; above usual 4 |
| Verification share (mean) | 8.6% | 16.9% |
| Leave-one-indicator-out range (mean) | 0.130 | 0.138 |

**The six indicators** (`E121_FIRI3_COVERAGE_REPORT.csv`):

| Indicator | Provincial available | First | Regional available | First |
|---|---|---|---|---|
| FMA | 87% | 2021-Q4 | 43% | 2024-Q2 |
| AFP | 65% | 2023-Q1 | 39% | 2024-Q3 |
| CEC | 70% | 2022-Q4 | 43% | 2024-Q2 |
| EHS | 70% | 2022-Q2 | 43% | 2024-Q2 |
| PSV | 22% | 2025-Q3 | — | — |
| FIS | 12% | 2025-Q4 | 61% | 2023-Q2 |

**All six function.** PSV and FIS are often unavailable, for data reasons:
- PSV: the poverty release is dated 2025-07-01;
- FIS: FSSI needs at least 5 articles.

**EHS is lost from 2026-Q2** because the 2025 provincial year is incomplete (DI-3).

**Reproduction and determinism:**
- FIRI3 reproduces the frozen E120 design computation exactly: all 138 unit-origins, same scores (|Δ| < 1e-12), same indicator counts, same bands.
- Two runs on identical inputs give identical outputs.
- Rerunning verified all 23 snapshots unchanged.

## 3. Contributions (`E121_FIRI3_FEATURE_CONTRIBUTION_REPORT.csv`)

**Frequently unavailable:** PSV (78% of province-quarters), FIS (88%), regional AFP (61%).

**Indicators carried by one feature:**
- provincial PSV (poverty only) and FIS (FSSI only) in 100% of their rows;
- provincial CEC rests on the cyclone count alone in 20 of 80 rows (before rainfall and heat have 8 earlier values).

**Largest single-feature influence on FIRI3:**

| Feature | Mean Δ when removed | Band changes |
|---|---|---|
| EHS unemployment / underemployment (provincial) | 0.026 | 12–15% |
| Regional EHS series | 0.044–0.058 | 22–30% |
| GDELT shortage share (regional) | 0.047 | 22% |

**No removal moves a score by more than 0.11.**

**Redundant information:**
- inside FMA, CPI food and headline scores correlate 0.74 (disclosed in E120; kept as separate components by the frozen design);
- inside regional AFP, crop groups correlate 0.6–0.95 on 9 quarters.

**Unstable:** regional EHS and FIS (national series) drive most regional band changes.

**Insufficient coverage by province:**
- every province has 15 computable quarters;
- Quezon averages slightly fewer indicators (4.27), as FSSI rarely reaches 5 articles there.

## 4. Validation (nine categories)

| Category | Report | Result |
|---|---|---|
| A Reproducibility | this report §2 | Deterministic; matches E120 exactly; protocol hash verified on every run |
| B Leakage | `E121_FIRI3_LEAKAGE_TEST_REPORT.md` | 15 of 15 boolean checks pass |
| C Missing data | `E121_FIRI3_MISSINGNESS_SENSITIVITY.md` | Composition effect small on average (0.011) but up to ±0.10 per province: 4- and 6-indicator scores not fully comparable (DI-2) |
| D Weighting | `E121_FIRI3_WEIGHTING_SENSITIVITY.md` | Score level robust (reasonable alternatives 0.005–0.03); bands near 0.5 sensitive to arbitrary weights (16–27%) |
| E Feature | §3 and the contribution report | No feature dominates; largest effects from EHS and regional national series |
| F Temporal | `E121_FIRI3_TEMPORAL_STABILITY.md` | Mean quarterly change 0.063 (v2 0.072); jumps come from inputs, not data structure |
| G Geographic | `E121_FIRI3_GEOGRAPHIC_VALIDATION.md` | Separation holds. Province differences mostly from EHS and PSV (DI-1). |
| FIRI v2 comparison | `E121_FIRI3_V2_COMPARISON.md` | ρ −0.30 explained by v2's regional-hunger and national domains; +0.29 with v2's provincial A and V domains |
| Prospective | `snapshots/`; this report §5 | Mechanism in place; first prospective quarter is 2026-Q4 |

## 5. Prospective validation

**Snapshot contents:** features, indicators and overall results (with the FIRI v2 value beside each province), plus a manifest with:
- file SHA-256 values;
- the protocol hash;
- the `firi.py` hash;
- the kind (`retrospective` / `prospective`).

**Immutability.** A rerun that would change an existing snapshot **stops**. Tested: the second run reported 23 × "verified unchanged".

**All 23 origins to 2026-Q3 are `retrospective`.** Their issue dates passed before E121 (2026-10-31). They were computed now, with the as-of rules, from data available now.

**The first `prospective` snapshot will be origin 2026-Q4** (issue 2027-01-01), once the E119 inputs are refreshed with that quarter's releases. No new quarter has been released since E121 began, so **no prospective snapshot exists yet**.

**SWS** will be compared with the regional FIRI3 descriptively after each release. It is never used to tune.

**Current descriptive figures** (`out/regional_vs_sws_descriptive.csv`; 10 quarters; after the freeze; not used for anything):

| Comparison | Spearman | n |
|---|---|---|
| Regional FIRI3 vs same-quarter SWS | −0.07 | — |
| Regional FIRI3 vs next-quarter SWS | +0.55 | 8 |

**This is not predictive validation.** It is too short, and inspected.

## 6. Unresolved limitations

1. **No provincial outcome.** FIRI3 provincial scores cannot be validated as food-insecurity risk.
2. **Province differences are mostly structural** (EHS, PSV ranks): DI-1.
3. **Indicator-set changes** shift single provinces by up to ±0.10: DI-2.
4. **EHS unavailable for 2026-Q2/Q3** under the frozen latest-year rule: DI-3.
5. **Verification share is low** (8.6% / 16.9%): DI-4.
6. **The leave-one-out range (≈ 0.13) is as wide as a band step**: DI-5.
7. **Batangas underemployment 31–40%** needs checking against PSA: DI-6.
8. **The regional index has only 10 quarters**: DI-7.
9. **Retrospective scores use the current data vintage**, not real-time vintages.
