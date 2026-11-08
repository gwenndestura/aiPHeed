# E123 design decision register

**Rerun:** `python runner/run_e123.py`.

**Code.** `backend/app/ml/inference/firi3.py` v1.2: Amendment 2, SHA-256 8b5f729c…. FIRI v2 is unchanged (verified by hash).

## Verified starting state

| Check | Result |
|---|---|
| Active protocol | E121 (8a431a9d) + Amendment 1 (4fd05309, owner-confirmed). Hashes match the files and `firi3`. |
| Amendment 1 exclusions | 40 rows rejected (`cpi_food_yoy_pct` 20, `cpi_headline_yoy_pct` 20) |
| E122 effect | 73 provincial scores changed vs E121 (`E122/out/summary.json`) |
| FIRI v2 | `firi.py`, `firi2_history.csv` and `firi2_reference.json` hashes unchanged |
| Test suite before E123 changes | **1129 passed, 18 skipped** (reproduced) |
| Commits | 75d9a25 (E121), 3275e00 and bd503d3 (E122) on `aiPHeed/corrected-data-pipeline` |

## Decisions

| # | Decision | What was done | Evidence | Status |
|---|---|---|---|---|
| DI-1 | Separate current conditions from structural vulnerability | Added the **Current Conditions Score** (FMA, AFP, CEC, FIS; ≥ 3 of 4; chance bands) and the **Structural Vulnerability Score** (EHS, PSV; both required; provincial only; a position among provinces, no band). The overall FIRI3 is unchanged. | CCS: 75/115 provincial, 10/23 regional. SVS: 25/115 provincial (from 2025-Q3); regional not defined. Province-rank agreement across quarters (Kendall W): FIRI3 0.44, **CCS 0.10, SVS 0.95**. FIRI3 puts Batangas top in 9/15 quarters; CCS spreads the top across Laguna 4, Cavite 4, Quezon 4, Batangas 3. | Implemented (Amendment 2, §2), as instructed in E123 |
| DI-2 | Common core | **Fixed core** (FMA, AFP, CEC, EHS, all four required) and **cross-province core per origin** (indicators available in all five provinces, ≥ 3; otherwise `comparison_not_possible`), shown beside FIRI3 | Fixed core: 75/115 provincial, 9/23 regional. Cross-core: 80/115 (from 2022-Q4; ≥ 3 common indicators). Spearman with FIRI3: 0.90 (fixed), 0.99 (cross). Quarter-to-quarter changes: **13%** (provincial) and 4.5% (regional) of the absolute change comes from indicator availability; the rest is feature change. | Implemented (Amendment 2, §3); reporting only, not the index |
| DI-3 | Annual data | rank5 now uses the **latest complete published year**; a newer incomplete year is skipped and named | 2025 (Batangas unemployment and Quezon underemployment missing) is skipped, so 2026-Q2/Q3 use 2024. **10 provincial scores changed** (max 0.070); none lost. Years shown; all published before the issue; no quarterly expansion. | Implemented (Amendment 2, §1), as instructed in E123 |
| DI-4 | Publication dates | Reclassified every feature into the four categories (`E123_PUBLICATION_DATE_AUDIT.csv`). No archived release evidence could be obtained: PSA sites return 403, the Internet Archive was offline (429 / "temporarily offline"). | **Verified 4**, provisionally eligible 27, **unverified 3** (EHS ×2: "30 June Y+1" is an assumption; PSV: the 2025-07-01 V1 assumption), ineligible 0. A documented-rule view without the unverified features leaves 14 provincial scores. | Open (needs PSA release calendars and archived releases) |
| DI-5 | News / NLP and GDELT | FSSI-v3 recomputed from the raw article stores; GDELT recomputed from raw daily data (`E123_NLP_AND_GDELT_AUDIT.md`) | FSSI identical in all 115 province-quarters (20 scored); 0 date violations; 0 duplicate articles. GDELT matches (max Δ 4e-13), from 2021-Q1. | Verified, with disclosed limits (pretrained model; GDELT query vintage) |
| DI-6 | Batangas employment | Source chain traced (`E123_BATANGAS_EMPLOYMENT_VERIFICATION.md`) | Values entering EHS equal the owner file (2024 unemployment derived exactly as 100 − 94.0). Internally consistent for 2021–2023. **2023 underemployment 31.0% corroborated** by a PSA RSSO IV-A release (search result; document 403). **2024 (39.5%) and 2025 (21.1%) not verified.** Without Batangas underemployment: mean Δ 0.005, rank ρ 0.98. | Partly verified; EHS remains unverified (date) |

## Proposed for owner decision (not implemented)

1. **Present the CCS beside the overall FIRI3 as the "current conditions" reading for provincial comparisons.** The FIRI3 ranking is mostly the employment rank (EHS explains 67% of between-province variance). This is a display decision; the dashboard is untouched.
2. **Treat EHS and PSV as unverified** (their availability dates are assumptions) in any strict reporting until PSA release dates are archived.
