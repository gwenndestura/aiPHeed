# E125 baseline verification (2026-10-31)

| Check | Result |
|---|---|
| Starting commit | `7d7390886567506b862810f47ca890ceca622cd7` (E124) |
| Frozen configuration | `E124_FROZEN_VALIDATION_CONFIGURATION.json`; canonical-JSON SHA-256 `8973ca66…` equals the `.sha256` file, and equals the configuration regenerated from `firi3` v1.2 (no drift). The raw file SHA-256 is `2836d90e…`; the canonical form is the one frozen. |
| E121 protocol | 8a431a9d…, equal to the file, `firi3` and the configuration |
| Amendment 1 | 4fd05309…, equal; active (40 rows rejected) |
| Amendment 2 | 8b5f729c…, equal; active (2025 skipped, 2024 used) |
| Snapshot store | `store/forecasts/` **empty**: no 2026-Q4 snapshot exists |
| Registry | 1 event: `attempt_blocked` (2026-10-31), preserved unchanged |
| FIRI v2 | `firi.py` 0e583131…, `firi2_history.csv` b84558de…, `firi2_reference.json` 25af6411… (unchanged) |
| Production | `git status` of `backend/app`, `frontend/src`, `backend/data` is clean |
| Previous results | The pre-refresh FIRI3 recomputation equals E123 exactly (138 of 138) |

**Untouched:** E114, E118, E119 and the corrected-pipeline inputs, and the E121–E124 outputs and snapshots. Refreshed raw data is saved only under `E125_FIRI3_Pre_Issuance/data/raw/`, with fetch metadata in `data/refresh_log.json`.
