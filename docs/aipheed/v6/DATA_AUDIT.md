# v6 Stage 1: Data audit from source

**Command:** `python -I backend/scripts/v6_data_audit.py` (about 75 s, including XLM-R on CPU from the local Hugging Face cache, offline).
**Outputs:** `v6/results/data_audit.json`, `data_audit_run.txt`, `audit_sws_vs_release_tables.csv`, `audit_cpi_recompute.csv`, `audit_firi_nlp.csv`, `audit_xlmr_rescore.csv`. All results below are VERIFIED unless tagged.

## A. Target: SWS involuntary hunger

| Check | Result |
|---|---|
| Backend copy vs E110 source file | Byte-identical |
| Validation (columns, dates, ranges, duplicates, booleans, 2021+ window) | 0 problems; 23 rounds; 0 duplicates; 0 commissioned rounds kept |
| Fieldwork midpoint quarter = quarter label | 23 / 23 |
| Publication lag after fieldwork end | 17–99 days (median 42) |
| **Values vs an independent extraction of SWS's official release tables.** Source: SWS media release 14 Oct 2026, Tables 1–6, extracted on branch `aiPHeed/e114-genuine-forecast`, which records the PDF's SHA-256. The PDF itself was not re-opened this session (SWS web access withheld). | **88 of 88** area-round values matched, max abs diff **0.0**. This also shows **no revisions** between first publication and the 2026-10 tables. |
| Round not found in those tables | 1: fieldwork 2025-04-23/28 (the first 2025-Q2 round). Its value is NOT VERIFIED against the release tables; it is in the stored file with its own release URL. |
| Margins of error | 14 rounds recorded from releases; 8 rounds (2021-Q2 … 2023-Q1) **assumed ±6** (E110 protocol): NOT VERIFIED (DATA_REQUESTS #1) |
| **Alignment, Lead 2** (Stage 2d) | Issue date → target fieldwork midpoint: **4.8–5.9 months** (median 5.7). Latest fieldwork used → issue: median 3.4 months. **Latest fieldwork → target fieldwork: median 8.9 months.** So "two quarters ahead" is in practice about 9 months past the newest measurement. |

## B. CPI (market group)

**Method:** area rice-CPI YoY recomputed from the raw OpenSTAT file (`psa_cpi_regional_2021_2026.csv`) with independent code (region matching, 12-month change, complete quarters only, YoY from 2022 only per lock C3), at 3 issues × 4 areas.

**Result:**
- **Max abs diff vs the v4 snapshot: 3.6e-15.**
- Every period ends before its issue (as-of holds).
- Regions per area: Balance Luzon 7, Metro Manila 1, Visayas 4, Mindanao 6.

## C–D. Point-in-time features and poverty

- **Periods:** 0 snapshot values have a period at or after the issue quarter.
- **Missing values** (by design, not imputed):
  - rice YoY: 16 (no pre-2022 base);
  - unemployment change: 16.
- **E119 status types across all cells:** verified 274, `rule_unverified` 512, missing 134.
  - **Defect, not fixable locally:** 512 cells use a publication **rule** (one quarter back), not a verified release date (E122: 30 of 34 publication dates provisional).
  - **Impact:** only the exogenous candidates, which failed anyway (v4). The served model uses SWS only. **Logged in DATA_REQUESTS #4.**
- **Poverty:** NCR 2025, raw 1.2 = snapshot 1.2.

## E. FIRI v2 (A1–H1) recomputed

- **Method:** at 3 historical issues (2022-04-01, 2024-07-01, 2026-10-01) × 5 provinces, `firi.score_v2` was applied to the stored raw indicators, with the expanding prior (`prior_for`) and the stored Lead-2 weights.
- **Result:** **max |stored − recomputed| = 4.9e-7** (storage rounding).
- **Scope (NOT VERIFIED):** the raw indicator values were taken from the stored history, not re-derived from each primary source. A3 rice and N1 news were re-derived separately (B and F).

## F. NLP pipeline, end to end

| Step | Result |
|---|---|
| FSSI-v3 recomputed from the stored articles and the stored XLM-R intensities (`pipeline_v3.fssi_v3`) for the 5 audited rows with a value | Max abs diff **0.0** |
| **XLM-R re-scoring.** Model `joeddav/xlm-roberta-large-xnli@b227ee84` from the local cache, offline. Classifier hash `35119d38`. 12 articles sampled deterministically from the 321 stored OK scores under the current model key. | Max abs diff **0.0**: stored scores reproduced exactly |
| Article collection (RSS / GDELT harvesting) | NOT VERIFIED: it needs network access and was not re-run |

## Gate 1: PASSED

The data are declared valid for the v6 work, with 3 documented limitations:
1. 8 assumed SWS margins;
2. 1 SWS round not in the release tables;
3. 512 E119 cells with rule-based availability dates.

No defect requires a code change. All three need external data (DATA_REQUESTS.md).

**Earlier runs re-verified by re-execution:**
- **E131/E136 target rows:** reproduced 272/272 (v2 DIAGNOSIS Q6).
- **v2 / v4 results:** reproduced byte-for-byte (v2 and v4 TEST_REPORTs).
- **Stage 2 re-runs** `v2_diagnosis.py` and `v4_validate.py` again and checks `git diff` (FEASIBILITY §0).
