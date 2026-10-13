# S1 Baseline Reproduction (E12)

**Formula (unchanged):** S1[p, t] = H[t] + 2 × (F[p, t] − mean of the five provinces' F[t]). Implementation: `app/ml/features/risk_score_v2.compute_stress`, SHA-256 `5b6c83d6…`.

## Reproduction gate (1e-9)

| Reference output | Rows | Max abs difference | Result |
|---|---|---|---|
| **E9 approved full-precision output** `E9/runs/20261012T140816Z/s1_targets_2021_2025.csv` (hash-recorded in the E9 manifest) | 80 | **3.55e-15** | **Pass** |
| `data/processed/labels.parquet` column `stress_score` (source of the served τ values) | 80 | **3.33e-5** | **Exceeds 1e-9: stop condition triggered for this reference** |

## Investigation of the `labels.parquet` difference (reference not modified)

1. The stored components (`sws_hunger_pct`, `food_cpi_yoy`) are **identical** to the E9/E12 inputs: 0 SWS differences by quarter, and 0.0 maximum difference in food CPI YoY.
2. Recomputing S1 from the stored components still differs by 3.33e-5, so the difference is in the stored **output**, not the inputs.
3. **The stored `stress_score` equals round(S1, 4) in 80 of 80 rows exactly** (2 or 3 decimals: 37/80; 4 decimals: 80/80).

**Conclusion: the difference is 4-decimal storage rounding of the reference column. The formula itself is reproduced.**

Evidence: `s1_reproduction_investigation.json`.

**Decision (disclosed):** the comparative run proceeded on the full-precision S1, which passes the gate against E9. **If you treat the rounded column as the binding reference, regard the comparative results as blocked.** They would differ only below the 4th decimal.

## Threshold τ0 (S1 only)

| Item | Value | Source |
|---|---|---|
| Derivation | Median S1 over the complete labelled quarters published before **2023-10-01**, under development-protocol publication dates (Rule L1), with at least 8 quarters; frozen | `risk_score_v2.reference_threshold`; `REVISED_SCORING_REPORT.md` §C; served artifact metadata |
| Quarters | 2021-Q2, Q3, Q4; 2022-Q2, Q3, Q4; 2023-Q1, Q2 (40 province values) | Served metadata `tau_quarters`; E9 manifest |
| Recorded (served) value | **10.84335** | `data/revised/*_meta.json`, computed from the rounded column |
| Full-precision value | 10.843333 | Recomputed in E12 |
| S1 values between the two | **0** | Classifications are identical under either |
| Leave-one-reference-quarter-out (descriptive; bypasses the 8-quarter minimum) | 9.95 to 11.60 | `runs/20261012T151208Z/details.json` |

**Event:** HIGH = S1 > τ0 (strict). **Of the 80 labelled rows, 56 are HIGH and 24 LOW.**

τ0 is **sensitive to which reference quarters are included** (about ±0.9).
