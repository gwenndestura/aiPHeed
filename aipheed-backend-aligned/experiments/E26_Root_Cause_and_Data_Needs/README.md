# E26: root cause and data needs

**Question:** what prevents aiPHeed from producing reliable, useful and accurate forecasts, and what would resolve it?

**Answer:** the target's structure and the data, not the code. See `FINAL_REPORT.md`.

**Status, 2026-10-14:**

- The goal is not met.
- No new seal (`docs/CONTAMINATION_LOG.md`).
- E25 and its seal are verified unchanged.
- 38 tests pass; outputs reproduce byte for byte.
- Approvals A1/A3, R2 and R3 are pending.

| Read first | Then |
|---|---|
| `FINAL_REPORT.md` | `ROOT_CAUSE_ANALYSIS.md` → `MISSING_OBSERVATIONS_SPEC.md` → `ADVISER_APPROVAL_REQUEST.md` |

## Folder map

| Path | Content |
|---|---|
| `FROZEN_ANALYSIS_PROTOCOL.md`, `PROTOCOL_AMENDMENT_A1.md`, `_A2.md`, `_A3.md` | Rules, frozen before use; hashes in `runner/PROTOCOL_SHA256.txt` |
| `ROOT_CAUSE_ANALYSIS.md` | Causes 1–6, quantified |
| `SOURCE_INVESTIGATION.md` | Sources S1–S10, with verification levels |
| `MISSING_OBSERVATIONS_SPEC.md` | O1–O8: what to authorize, in what form, and what it makes valid |
| `ADVISER_APPROVAL_REQUEST.md` | R1–R5 |
| `BUG_FIXES.md` | My mistakes, code changes, and deviations from the freeze |
| `TEST_RESULTS.md`, `REPRODUCE.md` | Tests; commands |
| `docs/` | `HORIZON.md`, `CONTAMINATION_LOG.md` (+ addendum) |
| `runner/` | `guard.py`, `root_cause.py`, `horizon.py`, `local_power.py`, `reproduce.py`, `import_e25_seal.py`, `verify_e25_unchanged.py`; E25 libraries copied unchanged (`e25lib.py`, `e23_lib.py`, `pcf.py`) |
| `backend_dev/` | Isolated backend copy: `app/quarterly/ledger.py`, `outcomes.py`, `local_validation.py`, `pcf_engine.py` (two layers, per-round SWS n) |
| `runs/` | Analysis outputs; `ledger/` (E25 seal registered, no outcome) |
| `tests/` | 38 tests |
| `inputs/` | Empty. E26 reads E25's pinned inputs in place. |

**Not modified:** `backend/`, `frontend/`, deployed models, thesis chapters, E17–E25. Nothing was committed, pushed or deployed.
