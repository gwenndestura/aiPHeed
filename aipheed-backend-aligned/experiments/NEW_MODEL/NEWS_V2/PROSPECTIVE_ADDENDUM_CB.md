# Prospective protocol, Addendum CB: C-b as the main model (effective only on adoption)

**Written:** 2026-11-03, before any 2027 target quarter has an SWS round.

**Effective:** only when the team **and** the adviser adopt C-b as the main model, recorded in `ALIGNMENT_CB.md`.
Until then `SENIOR_REVIEW/PROSPECTIVE_PLAN.md` (SHA-256 `194ecb72…224c`) applies unchanged, with REF+news as the main
model.

## What changes, and only this

1. **Main model:** **C-b** (`NEWS_V2/PLAN.md`, SHA-256 `0705ab68…5b60`).
   - 19 REF columns + `z_N1R` (FSSI-v3 anomaly against its own past 8 quarters, ≥ 4 past values) + `lead`.
   - IMPROVE_V2 grid, inner selection, LightGBM settings and seed; walk-forward refit at each issue date.
2. **Comparators sealed beside it:** REF+news and REF (reported, never used for the verdict).
3. **Already-sealed C-b forecasts:** `NEWS_V2/sealed_prospective_CB.csv` (SHA-256 `67baec66…1015`, issued 2026-10-01,
   2026-Q4 at Lead 1 and 2027-Q1 at Lead 2, P 0.8595, HIGH; sealed after the development results were known).
   - The 2027-Q1 Lead-2 row counts as C-b's first Lead-2 row.
   - The 2026-Q4 Lead-1 row precedes the prospective window (targets from 2027-Q1) and is reported only.

## What does not change

- Labels and their rules.
- One row per target quarter; **40 labelled quarters per lead** before any R1–R7 verdict.
- The frozen R1–R7 code and its independent recomputation.
- The single look on 1 March.
- The review trigger against persistence.
- The 14-day sealing window, missed-seal rule and the ban on editing seals.
- **Algorithm 4 blind holdout:** the first four labelled prospective quarters (2027-Q1..Q4) at each lead, scored once
  for F1 and AUC (targets F1 ≥ 0.75, AUC ≥ 0.80), as a report beside the single look.

## Before the first C-b seal

The sealing and scoring scripts (`SENIOR_REVIEW/runner/`) take their model list from `prospective_lib.MODELS`. Adding
C-b means:
- one entry, `"C-b": REF cols + ["z_N1R"]`;
- the anomaly built from the rebuilt table as in `NEWS_V2/runner/run_news_v2.py`;
- the main model switched to C-b.

Those scripts are hashed in `SENIOR_REVIEW/prospective/SEAL_LEDGER.md`. Their new versions must be committed and
re-hashed in the ledger **before 2027-01-01**, and must pass `dryrun_test.py` plus a replay of C-b's stored forecasts.
ADDENDUM-SHA256: fc110575d4c76224b350fbc85076399e76f1970dd0c23a43a1bffd2d3c60966c
