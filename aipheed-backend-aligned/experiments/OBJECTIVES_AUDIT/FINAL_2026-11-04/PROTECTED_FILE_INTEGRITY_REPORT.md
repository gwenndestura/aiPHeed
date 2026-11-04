# Protected-file integrity report

- **Manifest (recorded before any work on 2026-11-04):** `OBJECTIVES_AUDIT/integrity/protected_before_2026-11-04.sha256`,
  200 files.
- **Final check:** `integrity/protected_after_check_final_2026-11-04.txt`. **200 of 200 OK.**

| Group | Files | Status |
|---|---|---|
| C-b seals and ledgers | `backend/seals/*` (LEDGER.md 7b4dd9dc…), `backend/data/ledger/*`, `IMPROVE_V2/`, `NEWS_V2/` and `OPTION_1/SEAL_LEDGER.md` | ✅ unchanged |
| Prospective registry | `SENIOR_REVIEW/prospective/*` (SEAL_LEDGER.md b22faf62…, unchanged across both dry runs) | ✅ unchanged |
| C-b served export | `backend/data/foodinsecurity_engine/*` | ✅ unchanged |
| Production models | `backend/models/*` | ✅ unchanged |
| ALLBASE evidence | `NEW_MODEL/ALLBASE/out/*` | ✅ unchanged |
| Production configuration | `render.yaml`, `backend/Dockerfile` | ✅ unchanged |
| Frontend | every file in `frontend/src` | ✅ unchanged |
| Thesis documents | `THESIS 2 (18).pdf`, `#THESISDEFENDED.pdf` | ✅ unchanged |

## Git

- HEAD is still `3e15c3e`. No commit, push, merge, stash or deploy.
- **Tracked files changed by this task:**
  - `backend/app/ml/inference/foodinsecurity_system.py`;
  - `backend/app/services/dashboard.py`.
- Every other modified tracked file was already modified before the task (preserved, not reset).

**Questionnaire:** no Objective 5 instrument or response file was opened for writing.
