# E126 baseline verification (2026-10-31)

**Starting commit:** `4343c6275cd1cb6d187254f0816b9bd35b9cc069` (E125). There were no uncommitted changes under `backend/` or `experiments/E12*`.

| Item | Value | Status |
|---|---|---|
| E124 frozen configuration (canonical JSON) | `8973ca661cfcd68d41d7d1c9eb033adcdf3454723a7253294a8343f70d2178f0` | equals the `.sha256` file and the configuration regenerated from `firi3` |
| E121 protocol | `8a431a9d…` | equal |
| Amendment 1 | `4fd05309…` | equal; active |
| Amendment 2 | `8b5f729c…` | equal; active |
| `firi3.py` at start | `b04658a4…` (v1.2) | see C-E126-1 below |
| `firi.py` (FIRI v2) | `0e583131…` | unchanged |
| `firi2_history.csv` / `firi2_reference.json` | `b84558de…` / `25af6411…` | unchanged |
| Production (`backend/app` served code, `frontend/src`, `backend/data`) | — | unchanged |
| E125 refreshed inputs | NASA POWER 2026-01..09; PAR 2026-Q3 = 7; local 100 km 2026-Q3 = 0 (all provinces) | reproduced |
| September 2026 LFS | July, August only | still missing (PSA tables end August 2026; re-queried 2026-10-31 07:00 UTC) |
| E125 blockers | C1 (date), C3 (required periods: LFS) | **both still present** |
| Registry | 1 `attempt_blocked` event (2026-10-31) | preserved |
| 2026-Q4 forecast snapshot | none | correct |
| E125 outputs | hashed in `out/summary.json` → `baseline.e125_outputs_sha256` | not modified |

## C-E126-1: code fix in `firi3.py` (no behaviour change)

**The defect.** `_dynamic` picked a unit's latest observation with `su.loc[su["period"].idxmax()]`. That fails when the caller's table has repeated row labels within the same feature and unit, which happens after `pd.concat` without `ignore_index`. E126's impact analysis hit it.

**The fix.** The latest row is now chosen by position: `su.iloc[argmax]`. That is the same row whenever labels are unique.

**Effect.** Every FIRI3 input used so far has had unique labels within a feature and unit, so no result changed:
- the E123 / E124 reproduction checks still pass;
- the E121–E125 tests pass;
- a new test shows repeated labels now give identical output.

**Hashes.** `firi3.py` goes from `b04658a4…` to `c55224e3…`. The version stays **1.2**: the method, configuration and hashes are unchanged.
