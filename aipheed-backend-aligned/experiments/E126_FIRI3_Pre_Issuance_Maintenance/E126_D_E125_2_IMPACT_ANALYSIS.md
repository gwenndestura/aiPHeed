# E126 D-E125-2 impact analysis: PAR zero-storm quarters

**Sources:**
- `E126_PAR_ZERO_STORM_VERIFICATION.csv`;
- `out/summary.json` → `par_verification`, `impact`;
- `E126_HISTORICAL_SCORE_RECONCILIATION.csv`.

**Status.** **Nothing in the frozen pipeline was changed.** The corrected outputs are computed separately and labelled PROPOSED.

## 1. Verification (are the three quarters genuinely zero?)

**Method.** Each quarter was checked in two independent IBTrACS files:
- E114's full Western Pacific file `ibtracs.WP.list.v04r01.csv`, last fix 2026-10-22;
- E125's all-basin `ibtracs.last3years.list.v04r01.csv`, modified 2026-10-30.

**Boundaries.**
- **Approved (E114):** the box 5–25°N, 115–135°E, counting storms by the quarter of their first fix inside it.
- **Cross-check:** the official PAR outline.

| Quarter | E114 WP file covers the quarter | Storms first entering (box) | Storms already inside, entered earlier | Storms first entering (official outline) | WP track points in the quarter | Last-3-years file | Verdict |
|---|---|---|---|---|---|---|---|
| 2023-Q1 | yes | 0 | 0 | 0 | **none in the whole WP basin** | starts 2023-01-04, so does not cover the full quarter | **true zero** |
| 2024-Q1 | yes | 0 | 0 | 0 | none | covers: 0 / 0 / 0 (nearest point: MEGAN, Southern Hemisphere, about 17° outside) | **true zero** |
| 2025-Q1 | yes | 0 | 0 | 0 | none | covers: 0 / 0 / 0 (nearest: BIANCA, Southern Hemisphere) | **true zero** |

**Interpretation.** No tropical cyclone track point exists anywhere in the Western Pacific basin in these quarters. So zero is the observed count, not missing coverage.

**Storm identifiers.** De-duplication used the storm key of one ATCF id per SID. It changes nothing in these quarters.

**Cause of the defect.** E114 `collect_covariates.ibtracs()` builds the series as `first.groupby("q").size()`. That produces rows only for quarters with at least one storm, so the three quarters are simply absent.

**Every other quarter.** All 2021–2026-Q2 quarters with storms equal the de-duplicated recount from the WP file.

## 2. Effect of recording them as 0 (proposed Amendment 3)

**Only the regional feature `CEC_cyclones_R` (PAR count) changes**, through two routes:
- **the as-of value:** the score uses a true 0 instead of falling back to an older quarter's count;
- **the percentile reference history:** the three zeros join the earlier values.

**On the E125 refreshed inputs** (the current state):

| Origin | FIRI3 now | FIRI3 with A3 | Δ | Band now | Band with A3 |
|---|---|---|---|---|---|
| 2024-Q2 | 0.5479 | 0.5347 | −0.0132 | above usual | above usual |
| 2024-Q3 | 0.5729 | 0.5808 | +0.0079 | above usual | above usual |
| 2024-Q4 | 0.4973 | 0.4977 | +0.0004 | usual or below | usual or below |
| 2025-Q1 | 0.4522 | 0.4549 | +0.0027 | usual or below | usual or below |
| **2025-Q2** | 0.5282 | 0.4862 | **−0.0420** | above usual | **usual or below** |
| 2025-Q3 | 0.3431 | 0.3541 | +0.0109 | usual or below | usual or below |
| 2026-Q1 | 0.3305 | 0.3348 | +0.0043 | usual or below | usual or below |
| 2026-Q2 | 0.3624 | 0.3700 | +0.0076 | usual or below | usual or below |
| 2026-Q3 | 0.6826 | 0.6876 | +0.0050 | elevated | elevated |

Every row is CALABARZON (regional).

**On the pre-refresh (E123) inputs:** the same 9 origins change, with **2 band changes**. The second is 2026-Q3, above usual → elevated, a row that E125's NASA refresh had already moved to elevated.

| Question | Answer |
|---|---|
| Affected historical quarters | PAR inputs 2023-Q1, 2024-Q1, 2025-Q1. Regional scores 2024-Q2 … 2026-Q3 (9 of the 10 computable regional quarters). |
| Provincial scores affected? | **No**: PAR is a regional-only feature |
| CCS affected? | Yes, for the same 9 regional rows (CEC is a conditions indicator) |
| 2026-Q4 planned forecast affected? | **Yes.** The PAR value it would use (2026-Q3, 7 storms) is unchanged, but its percentile rises from **0.711 to 0.750**: the reference history gains three zeros. The decision must be made **before** issuance. |
| FIRI v2 comparisons affected? | **No.** FIRI v2 has no regional index; the FIRI3-vs-FIRI v2 comparison is provincial only. |

## 3. Recommendation

**Approve Amendment 3** (`E126_AMENDMENT_3_PROPOSAL.md`).

**Why:**
- The evidence shows true zero counts: no storm in the basin, in two independent files, under both boundaries.
- Recording them is a correction of an extraction defect, not imputation.
- Without it, the regional score quietly substitutes an older quarter's count.
