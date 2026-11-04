# Objective 5: technical evaluation readiness

## 1. What evaluators currently see (important for the ongoing survey)

| | Deployed site (`render.yaml`, branch `main`) | Local C-b demonstration (this branch, not deployed) |
|---|---|---|
| Map colour and score | **FIRI v2 food-price-pressure index** (default `AIPHEED_MAP_MODEL`) | **C-b**: P(Balance Luzon hunger > 11.3%) × province poverty |
| Landing and About text | P0H4 (hunger × food-price) description and figures (accuracy 0.84, Brier 0.132, 70 province-quarters), correct for P0H4 (traced to `FINAL_SYSTEM_SELECTION/out/landing_figures.json`) | C-b text; every figure read from the served `evaluation.json` |
| Consistency | **Map (FIRI) and text (P0H4) describe different models** | Map, rankings, explanations and text all describe C-b |

**Consequence:** the ongoing questionnaire responses evaluate the deployed (FIRI/P0H4) system, not C-b.

**Decision for you and the adviser:**

| Option | What happens | Cost |
|---|---|---|
| (a) | Keep the deployed version for the whole survey and report that the evaluated build is not the thesis model | Simplest; the gap is reported |
| (b) | Deploy the C-b build for the remaining respondents and record the switch date | Two builds evaluated; responses must be analysed by build |
| (c) | Re-run the survey on the C-b build | Clean comparison; most effort |

**I have not deployed or changed `render.yaml`.**

## 2. Local demonstration environment (C-b)

Backend (from `backend/`):
```
set AIPHEED_LEAD2_MODEL=thesis
set AIPHEED_STRICT_MODEL=1
set AIPHEED_MAP_MODEL=foodinsecurity
set DATABASE_URL=sqlite+aiosqlite:///./demo.db
uvicorn app.main:app --port 8000
```
Frontend (from `frontend/`, `.env.local` with `VITE_API_BASE_URL=http://localhost:8000`): `npm run dev`.

Admin review: issued forecasts (2026-Q4, 2027-Q1) stay STAGED until an administrator approves them in `/admin`. For a
demonstration, approve them in the review queue; each decision is logged.

## 3. Changes made on this branch (local, uncommitted; backups in `backup/frontend_2026-11-03/`)

| File | Change |
|---|---|
| `frontend/src/lib/servedModel.ts` (new) | Detects the served model from `/api/v1/config` (`indicator.id`); reads C-b figures from `/api/v1/final/risk/evaluation` |
| `frontend/src/pages/landingCb.ts` (new) | C-b About, Methodology, Accuracy notes, Disclaimer, FAQ, footer text (no hardcoded metrics) |
| `frontend/src/pages/Landing.tsx` | Each section shows the C-b content when C-b is served; **otherwise unchanged (the deployed default renders exactly as before)** |
| `frontend/src/components/AboutModal.tsx` | C-b rows from the served payload. **Fixes a crash:** the dialog read `baseline_accuracy["ALWAYS-LOW"]`, absent from C-b's payload |
| `frontend/src/components/DashboardOverview.tsx`, `RegionSidebar.tsx` | **Removed**: unused components with unsupported figures (F1 0.82, AUC 0.87, SUS 78) |
| `frontend/src/test/landing_cb.test.tsx` (new) | The Landing figures equal `backend/data/foodinsecurity_engine/evaluation.json`; no P0H4 figure or wording in the C-b mode; the About dialog opens |
| `backend/tests/integration/test_foodinsecurity_drivers.py` (new) | Driver bars + otherPct = 100%; direction = SHAP sign; non-inputs have no bar; score and class = forecast record |

**Not changed:** the backend application code, the API, served data, `render.yaml`, the Dockerfile, C-b, seals and
the ledger.

## 4. Test evidence (2026-11-03)

| Suite | Result |
|---|---|
| Frontend (vitest) | **87 passed** (83 existing + 4 new); TypeScript: no new errors (6 pre-existing in unused `src/data/mockData.ts`) |
| Backend driver consistency (new) | 3 passed |
| Backend full suite | See `OBJECTIVE_COMPLETION_REPORT.md` |

## 5. Questionnaire check (the ongoing version is not modified)

The repository holds only the draft `frontend/meeting-materials/aiPHeed_PostTesting_Questionnaire_Draft.docx`; the
live Google Form is not in the repository. Against the thesis, the draft has these gaps. **The team should check the
live form for them; nothing here changes it.**
1. The title says "DOST Region IV-A" and the respondent groups are DOST staff and the general public; the thesis
   specifies 50 DA Region IV-A personnel (§1.7, §3.7, H5).
2. There is no H4 ranking task (evaluators' own province/LGU ranking compared with aiPHeed's).
3. ISO/IEC 25010 coverage is limited to functionality and usability. Performance efficiency, compatibility,
   reliability and security items are missing.
4. There is no pre-specified analysis. `OBJ5_ANALYSIS_PLAN.md` (hashed `851ea697…`) provides one; it should be fixed
   before the responses are opened.
5. The build evaluated must be recorded (see §1).

`OBJ5_ISO25010_INSTRUMENT.md` contains a complete item set the team can compare against.
