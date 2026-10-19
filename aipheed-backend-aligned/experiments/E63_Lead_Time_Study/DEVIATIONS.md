# E63 deviations

## From PROTOCOL.md

None.

The following ran exactly as frozen:
- the leads, origins and cutoffs;
- the procedure, with no retuning;
- the seal-before-score order;
- the metrics, bootstrap (4000 draws, seed 63) and rule.

The lead-2 reproduction check passed on the first run (max abs difference 5.0e-13), so no implementation correction was needed.

## From the requesting brief

| ID | Brief | What was done | Why |
|---|---|---|---|
| B-1 | Create `aipheed-backend-aligned/experiments/E63_Lead_Time_Study/` | The folder sits at that relative path **inside the session worktree** (`C:\Users\admin\aipheed\.claude\worktrees\serene-sanderson-0c7a84\`, branch `claude/bold-euclid-f53301`), not in the main checkout (`C:\Users\admin\aipheed`, branch `e62-final-audit`). The code reads the frozen E41–E57 code and data from the main checkout, read-only (env var `AIPHEED_EXP` overrides the path). | The session harness refuses writes into the main checkout. The worktree branch is a frontend branch and does not contain `aipheed-backend-aligned/`. Moving the folder onto the `e62-final-audit` branch is left to the user's approval, together with any commit. Empty folders created briefly in the main checkout before the refusal were removed; nothing else was written there (`out/guard_check.json` covers E56–E62 and `backend/data`). |
| B-2 | "other inputs to t−1" | Typhoon and news counts use quarter t, as in E56. | This is the actual E56 rule: quarter t has ended at O(t). It was kept unchanged so that the procedure is E56's, and it is stated in PROTOCOL section 2. |
| B-3 | Leads 1–4 | Lead 4 is reported as not computable. | Under the CPI cutoff, the base-effect projection is undefined at lead 4. This was found by the score-free eligibility check and pre-registered in PROTOCOL section 1. |

## Other notes

- **The score step ran twice.** The second run filtered a scikit-learn `FutureWarning` (the `penalty=None` deprecation) so that `out/score_console.txt` is readable. All output tables and `out/scores.json` were byte-identical across the two runs (SHA-256 compared).
- **Lead-2 CIs differ slightly from E57's** (4000 draws, seed 63 here vs 2000 draws, seed 57 in E57). All lead-2 point estimates are identical to E57's.

## Relocation (2026-10-19, on the user's instruction)

- **Copy:** the folder was copied unchanged from the worktree onto branch `e62-final-audit` in the main checkout, at `aipheed-backend-aligned/experiments/E63_Lead_Time_Study/`.
- **Frozen text:** `PROTOCOL.md` still names the worktree location, because it is frozen.
- **Line endings:** a folder-local `.gitattributes` (`sealed/** -text`) keeps the sealed CSV byte-for-byte, so its hash stays valid on checkout.
- **Checks after the copy:**
  - the 5 tests pass;
  - `runner/e63_score.py` reproduces `out/scores.json`, `tables/lead_metrics.csv` and `tables/paired_tests.csv` byte-for-byte.
