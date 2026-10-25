# E111: audited hunger forecasting with true horizons, surge costs and indicator screening. Pre-registered protocol

**Date:** 2026-10-25. **Branch:** `aiPHeed/e111-hunger-forecast-audit`, from E110 `560970c`. **Window:** 2021 onward only.
**Freezing:** hashed in `runner/PROTOCOL_SHA256.txt` before any E111 candidate is scored.

**Already seen before freezing:**
- every E109 and E110 result;
- the E111 audit (`out/audit_e110.json`);
- the horizon table (`out/horizon_table.csv`).

Every outcome quarter through 2026-Q3 has been examined, so **all retrospective results are exploratory / development evidence. No quarter is untouched.**

## 1. Outcome, data and cutoffs (unchanged from E110)

- **Outcome:** SWS Total Hunger, non-commissioned rounds, quarter mean by fieldwork quarter.
- **Areas:** Balance Luzon (BL) is primary; Metro Manila, Visayas and Mindanao form the generalization panel.
- **Vintages:** rounds published before the issue date O(*t*) (day 1 of quarter *t* + 1).
- **Predictors:** E107 cutoffs (`out/horizon_table.csv`).
- **True horizon h** = target quarter − newest SWS fieldwork quarter known at O(*t*). Results are reported by **lead** and by **true horizon**.

## 2. Methods

**Panel methods (4 areas, inference by quarter):**

| Name | Definition | Hypothesis |
|---|---|---|
| RW | latest known reading | baseline |
| MA2 | mean of the last two known quarters | baseline |
| LLR | E110 local-level filter (published round margins, pooled Q) | E110 reference |
| **DT** | H_last + φ̂ · s · g, where s is the per-quarter slope between the last two known quarters, g the true horizon, and φ̂ ∈ [0, 1] is pooled least squares over the 4 areas on training pairs (target − H_last on s · g). Training pairs = targets known at O(*t*). | momentum anticipates surges (the 2024 rise) |
| **BRK** | LLR run only on quarters ≥ 2025-Q2 when the target is ≥ 2025-Q2 and at least one such quarter is known; otherwise LLR | the 2025 respondent-base change breaks comparability |
| **ASYM** | max(RW, LLR) | asymmetric cost: never forecast below the latest reading (underpredicting hunger costs more), but use the smoothed level when the latest reading is below it |

**BL-only methods (CALABARZON predictors):**

| Name | Definition |
|---|---|
| **LGBM12 (required)** | E109's LightGBM (H_last + LightGBM on Δ, 13 columns = all 12 FIRI families, depth 1, min_child 3, trees ∈ {25, 75} by inner MAE), E109 eligibility (≥ 8 pairs) |
| FAM-*f* (exploratory screen, 12 models) | H_last + ridge (α = 10) of Δ on the columns of family *f* only |

## 3. Metrics

- **Continuous error:** MAE, RMSE, bias; quarter-cluster block-bootstrap CIs.
- **Paired test:** quarter-averaged absolute-error differential vs RW, one-sided HLN-DM (lag *k* − 1).
- **Interval coverage:** 80% interval = forecast ± 1.2816 σ̂, where σ̂ is the RMSE of the method's own earlier errors.
- **Change classes** (vs the area's latest reading H_last and its published margin m):
  - **sharp increase:** y − H_last > m;
  - **sharp decrease:** y − H_last < −m;
  - **stable:** otherwise.
- **Surge cost:** mean underprediction max(0, y − f) and miss rate (f < H_last + m/2) on sharp-increase rows.

## 4. Reliability rule (E110 P1–P6, plus two new criteria)

| | Criterion |
|---|---|
| P1 | ≥ 8 target quarters; mean quarter differential < 0 with DM p < 0.10 |
| P2 | BL: ≥ 8 quarters, MAE ≤ RW and ≤ 4.0 |
| P3 | better than RW in every chronological third, in rising and falling rows, and after 2025-Q2 |
| P4 | survives leave-one-quarter-out |
| P5 | not worse than RW on the last 4 quarters |
| **P7 (new)** | surge cost: mean underprediction on sharp-increase rows ≤ RW's |
| **P8 (new)** | 80% interval coverage ≥ 0.70 (panel) |
| P6 | confirmed on unseen outcomes |

**Status:** provisional = P1–P5, P7 and P8; insufficient evidence = fewer than 8 quarters; reliable additionally needs P6.

**Maximum reliable lead** is defined as in E110. Also reported: the maximum provisional lead, and the maximum lead and true horizon tested.

**Family screen.** For each FAM-*f*, the BL DM p vs RW at Leads 1–2, Holm-adjusted over the 12 families. A family "adds measurable value" only if its Holm-adjusted p < 0.10 at a lead **and** its gain survives:
- S-ALL (all SWS rounds, including the commissioned one);
- S-HH (household-head rounds only, if ≥ 8 quarters).

## 5. Sensitivities

- **S-NOINF:** panel methods without the inferred June-2021 Metro Manila, Visayas and Mindanao cells.
- **S-VOTERS:** add the April 11–15, 2025 voter round.
- **S-ALL / S-HH** for LGBM12 and the family screen.

## 6. Seal

- Every method from origin 2026-Q3 (issue 2026-10-01): Leads 1–6 for the panel, 1–4 for BL-only methods.
- Point forecast, true horizon, 80% interval.
- Written to `out/sealed_prospective.csv` with its SHA-256. The E107–E110 seals are untouched.

## 7. Tests (`backend/tests/unit/test_e111.py`)

- horizon table vs the publication dates;
- no future round changes any E111 forecast, plus a negative control;
- φ̂ uses known pairs only;
- BRK break rule;
- ASYM ≥ RW;
- family columns;
- reproducibility;
- protocol and seals;
- API.
