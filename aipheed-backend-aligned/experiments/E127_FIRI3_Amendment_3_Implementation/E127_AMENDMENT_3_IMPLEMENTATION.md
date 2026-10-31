# E127 Amendment 3 implementation

## Where

**In the data layer, not the scoring code.**

| File | Role |
|---|---|
| `runner/par_counts.py` | The general PAR quarterly count builder |
| `runner/firi3_inputs.py` | The single FIRI3 v1.3 input builder: E120 inputs + E125 refreshes + the Amendment 3 PAR series. `build(amendment_3=False)` gives the v1.2 / E125 state for comparison. |
| `backend/app/ml/inference/firi3.py` | Only the constants: `AMENDMENT_3_SHA256` and `VERSION = "FIRI3-candidate-1.3"`, plus a docstring line. **No scoring code changed.** |

## `par_quarterly(tracks, start_q, end_q)`

**Same as E114** (`collect_covariates.ibtracs`) **and E125:**
- box 5–25°N, 115–135°E;
- `SEASON ≥ 1996`;
- first fix inside the box decides the quarter;
- one storm = one key per IBTrACS SID (its JTWC ATCF id where present, otherwise the SID).

**New: coverage and explicit zeros.**
- A quarter is **covered** when the file's first fix is on or before its start and its last fix is after its end.
- **Covered quarters** are recorded with their count, **0 when no storm qualifies**, status `verified`.
- **Uncovered quarters** are reported as `not_covered` with the reason, and are **not passed to FIRI3**. For example, 2026-Q4 is in progress: the WP file's last fix is 2026-10-22.

**Nothing is filled. Nothing is keyed to quarter labels.** The three zeros come out of the general rule.

**Evidence kept per quarter:**
- `storms` (ATCF ids and names);
- `storms_active_in_box`;
- `evidence` (text including the file's first and last fix dates);
- `source` (file name);
- in `E127_PAR_ZERO_STORM_DATA.csv`: the E114 series value, a match flag, a note, and E126's two-file verification verdicts.

## Source

**File.** `experiments/E114_Final_Run/data/raw/ibtracs.WP.list.v04r01.csv`. This is E114's own file, so the counts are directly comparable. Its SHA-256 is in `out/summary.json` → `provenance`.

**Agreement:**
- it reproduces every E114 storm quarter from 2021-Q1 to 2026-Q2;
- it gives 2026-Q3 = 7, matching E125's recount from the newer last-3-years file.

## Results

| Check | Result |
|---|---|
| Explicit zeros added | 2023-Q1, 2024-Q1, 2025-Q1 |
| Other PAR quarters | unchanged |
| Other inputs | identical |
| v1.2 (builder with `amendment_3=False`) reproduces E125 | yes, all 138 |
| v1.3 reproduces the E126 proposal | yes, all 138 |
| Deterministic | yes |
| Leakage | none (see `E127_REGIONAL_SCORE_IMPACT.md`, `E127_2026Q4_SCORE_RECALCULATION.md`) |

## Version transition

**FIRI3 1.2 → 1.3.**
- **Active configuration:** `E127_FROZEN_VALIDATION_CONFIGURATION_v1_3.json`. It supersedes the E124 v1.2 file, which stays unchanged as the v1.2 record.
- **Forecast id:** `FIRI3-1.3-<origin>`. The first forecast will be `FIRI3-1.3-2026-Q4`. The E124 blocked attempt stays recorded under `FIRI3-1.2-2026-Q4`.
- **Historical runners:** the E124–E126 runners now refuse to regenerate their v1.2 configurations. That is the intended "new version required" behaviour; their outputs stay as records.
