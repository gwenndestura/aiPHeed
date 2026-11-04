# C-E2 reproduction report

**Repository:** `C:\aiPHeed-final1`, branch `aiPHeed/system-fixes`. Nothing is committed.

## Pre-registration

- **File:** `OBJECTIVES_AUDIT/CE2_PREREGISTRATION.md`.
- **PLAN-SHA256:** `a1b469da7f325c2e7582af57c1a5f4a1b62db308624ae1ce842049e4274bd1aa`.
- **Check:** `ce2_model.check()` recomputes the SHA-256 over every byte before the final line and asserts equality.
  It passed on every run today.

## Refit from scratch

`python ce2_model.py fit` (113 origins, 904 rows, 8 processes), then `python ce2_model.py score`.

| File | Stored (copied to `out/repro_2026-11-04/` before the refit) | After refit | Identical |
|---|---|---|---|
| `out/ce2_fits.csv` | c078aa27…f933f | c078aa27…f933f | ✅ byte-identical |
| `out/ce2_results.json` | 13666bfd…18b9 | 13666bfd…18b9 | ✅ byte-identical |

## Reproduced metrics (62 quarters, 2010-Q1..2026-Q3)

| | Accuracy | Balanced | Precision | Recall | F1 | AUC | Brier | TP/FP/FN/TN | Failed |
|---|---|---|---|---|---|---|---|---|---|
| Lead 1 | 0.774 | 0.690 | 0.796 | 0.907 | 0.848 | 0.715 | 0.1875 | 39/10/4/9 | R3, R7 |
| Lead 2 | 0.758 | 0.679 | 0.792 | 0.884 | 0.835 | 0.694 | 0.1879 | 38/10/5/9 | R3, R7 |

- **Algorithm 3:** Leads 1–4 accuracy 0.774 / 0.758 / 0.758 / 0.645, so MRLT is 3.
- **Every figure in Part 4 of the prompt is reproduced.**

## Sealing replay (dry run; `runner/seal_ce2_dryrun.py`)

- C-E2 refitted at origin 2026-Q3 from the current data files equals the stored fit at every lead (max |Δ| = 0.0).
- **2027-Q1 (Lead 2):** p = 0.896098, HIGH.
- The would-be record was written only to the scratchpad. **No seal and no ledger were written.**

## Defect found and corrected (development evidence, earlier today)

- `runner/ce4_model.py` wrote to the C-E3 output names, overwriting C-E3's evidence.
- The paths were corrected, and C-E3 and C-E4 were refitted (deterministic). Their figures equal those first reported
  (C-E3: L1 0.726 / L2 0.645; C-E4: 0.758 / 0.758).
