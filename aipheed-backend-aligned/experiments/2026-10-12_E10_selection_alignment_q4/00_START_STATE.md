# E10: Start State (verified with metadata and hashes only, 2026-10-12 22:39 local)

| Item | Verified value |
|---|---|
| Git HEAD | `eee269b92b47482d07aac769c54dd1d6c558c5ce` (`backend+frontend`); 23 status entries; last reflog entry is the 2026-10-06 checkout. No commit, push or fetch since. |
| Existing hash records | **865/865 match:** 55 protected and carrier files; E1–E7 inputs, protocols and outputs; served artifacts and their inputs; 54 production `backend/` files; E8 v1/v2. No size or mtime change in the protected baseline. |
| E9 files | All 43 match `E9_FILES_SHA256.txt`. `08_INTEGRITY_REPORT.md` = `dbb83bb8…`; `E9_FILES_SHA256.txt` = `cc17485a…` |
| Scheduled tasks | `aipheed`: `enabled=false`. `aipheed-auditing`: `enabled=false`. No next run for either. **Not re-enabled.** |
| Production backend process | None running (checked 22:10) |

**E10 folder:** `experiments/2026-10-12_E10_selection_alignment_q4/` (new). E9 and earlier records are read-only to E10.

**E10 guard:** a copy of the E9 guard with one addition: read-only access to the E9 experiment folder. E9's own guard file is unchanged.
