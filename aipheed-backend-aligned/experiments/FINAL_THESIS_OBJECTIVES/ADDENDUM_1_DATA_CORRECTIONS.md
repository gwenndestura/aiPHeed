# Addendum 1: audited inputs (FIRI v2 data audit)

**Applies to:** `FINAL_TARGET_AND_EVALUATION_PROTOCOL.md` (sha `dd9ab815…`).

**Freezing:** this addendum was frozen after the first scoring and before the rerun below. Its SHA-256 is in `runner/ADDENDUM_1_SHA256.txt`.

## What changes

**Inputs only.** The target (T43c), the model (CH1-LGBM), the grid, the baselines, the metrics and reliability rules R1–R7, the time convention and the leakage rules are all **unchanged**.

The audit (`../FIRI_V2_DATA_AUDIT/`) found three input defects. They are corrected as follows:

| Indicator | Defect found | Correction |
|---|---|---|
| E2 remittance decline | The held quarterly cash-remittance levels disagree with BSP's published releases (e.g. Q1 2025: held 8.65 vs BSP 8.44; Q2 2021: 7.96 vs 7.28). 2026-Q1 and 2026-Q2 were never collected. | Levels rebuilt from 22 cited BSP cumulative figures (Q1, H1, 9M, full year, 2021–2026), by differencing: `FIRI_V2_DATA_AUDIT/data/bsp_cash_remittances_cumulative.csv`. Figures come from BSP's latest release that reports them (revised vintages). |
| C2 typhoons | The 300 km counts used undocumented centroids; 7 of 115 province-quarters differ by one storm on recomputation; 2026-Q3 was fetched mid-quarter | Recomputed from IBTrACS (downloaded 2026-10-25) with area-weighted centroids of the app's province boundaries |
| A3 rice | The held 2026-Q3 quarter held July–August only | Complete 3-month means from PSA (affects only origins ≥ 2026-Q4, not the evaluation) |

**Implementation fix.** E107's `feature_table` cache is keyed on the CPI data object only. The corrected inputs are therefore given a distinct data object, so the cache cannot return the uncorrected table.

## Rerun

All leads (0–4), all comparators, the reliability verdicts, Objective 4 / H3 and the news ablation are re-scored with the corrected inputs, under the same rules.

**The first scoring is kept and reported.** The rerun is labelled "audited inputs". If the two disagree, the audited-input result governs, because the first run used defective inputs.

## Pre-specified sensitivity (requested): pooled-area hunger noise

**Change:** π_H's σ is computed from latest-reading errors pooled over the four SWS areas (NCR, BL, Visayas, Mindanao) known before O(t), instead of BL alone. The hunger condition itself stays Balance Luzon.

**Purpose:** it tests whether pooling other published survey areas improves the hunger condition. No regional reading is ever used as a provincial label.

**Status:** reported beside the primary result; it does not replace it.
