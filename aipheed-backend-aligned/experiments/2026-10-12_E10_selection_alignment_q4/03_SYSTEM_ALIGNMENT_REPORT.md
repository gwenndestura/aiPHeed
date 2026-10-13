# E10: System-Alignment Report (what is actually implemented, served and deployed)

**Method:** code and configuration reading, git metadata, process listing and earlier session records. **Nothing was run, started or changed.**

**Evidence labels:**

- **V:** verified in this task.
- **R:** from earlier records (memory index or reports), not re-verified.

## 1. Is anything deployed?

| Question | Finding | Ev. |
|---|---|---|
| Hosting configuration in the repository (Vercel, Netlify, Docker, Procfile, Render, Railway, Fly, CI workflows) | **None exists** | V |
| Frontend API target | `frontend/src/lib/api.ts` uses `VITE_API_BASE_URL`, default `http://localhost:8000`. Only `frontend/.env.example` exists; no `.env`. | V |
| Running backend | No python or uvicorn process (checked 18:26 and 22:10 on 2026-10-12) | V |
| Public site | `aipheed-frontend.vercel.app` served the old sample-data prototype with no `/api/v1` calls, as checked on 2026-10-07 | R |

**Conclusion:**

- **No integrated system is deployed.**
- The integrated system exists as **production `backend/` + `frontend/`, run locally**. The thesis documents this system (your choice, 2026-10-09; R).
- **The isolated research backend is not deployed** and is not the thesis system.

## 2. The four components

| Component | Target and scoring | Model | Classification rule | Status |
|---|---|---|---|---|
| **Production `backend/`** (thesis system) | **`label_cpi`**: provincial food CPI index above its trailing 24-quarter mean + 1σ in two consecutive quarters. This is the paper's Eq. 4 "CPI-only robustness label". **Not S1.** | `models/thesis_food_insecurity_model.joblib`: three-way blend, LightGBM 0.4 + government logistic regression 0.4 + weak trigger LR 0.2 (`thesis_predictor.py`). Docstring: does **not** clear F1 ≥ 0.75 / AUC ≥ 0.80. **No repository script rebuilds the blend** (R). | HIGH if blended probability ≥ the bundle's `threshold`, **0.712** per earlier records (R); the code default is 0.5 (V). Municipal pills: HIGH if `riskIndex` ≥ 0.50 (`RISK_DISPLAY_CUTOFF`). | Served when started locally; the scheduler is disabled |
| **Production municipal values** | Provincial forecast × (0.6 × LGU poverty + 0.4 × density), normalized within the province (`disaggregator.py`) | Allocation, not a model of LGU outcomes | ≥ 0.50 → "high" | Labelled as a modeled disaggregation; poverty has only 3–5 distinct values per province (code note) |
| **Isolated research backend** | **S1** (Equation 3 corrected; τ0 = 10.843) | Served M6 data-driven LightGBM artifact (`/api/v1/assessments`) | `final_classification`: p ≥ 0.50 → HIGH; INSUFFICIENT_DATA rules | Not deployed. **No UI consumes `/assessments`.** |
| **E9 experimental models** | S1, τ0 = 10.843 | B1–B4, M1–M3 (research only) | Same 0.50 / τ0 rules | Files only; never served |

## 3. Dashboard behaviour (production frontend, from code)

1. **Province and municipality pills show "high" or "low" only.**
   - The province pill uses the predictor's `risk_label`, otherwise `riskIndex ≥ 0.50`.
   - The frontend adapter maps a missing risk level to **"low"** (`adapters.ts`: `riskLevel ?? "low"`).
   - **The production dashboard has no INSUFFICIENT_DATA state**, unlike the research rule.
2. **The uncommitted frontend changes call `/api/v1/alerts` and `/api/v1/ranking`.** Those routes exist **only in the isolated backend**, not in production `backend/`. Run against production, those panels would fail. The committed frontend is unaffected.
3. **Thresholds disagree across components:**
   - production blend cutoff 0.712 (R);
   - production display cutoff 0.50 (V);
   - research rule 0.50 on S1 probabilities (V);
   - S1 event thresholds τ0 = 10.843 (served research artifact) and 14.345 (approved prospective reference).

## 4. Misalignments the thesis must not blur

| # | Misalignment | Consequence for the thesis |
|---|---|---|
| M1 | The system the thesis documents (production) uses `label_cpi` and a blend. The research results (E1–E10) use S1 and LightGBM, M6 or rules. | Evaluation results from E-experiments **do not describe the deployed or production model**. Present them as research findings about S1. |
| M2 | `label_cpi` is an index-trend artifact (100% HIGH in 2024; E5). S1 corrects the target, but production does not use S1. | Chapter text describing production outputs as "food insecurity risk" must carry the `label_cpi` caveat. Otherwise production must be changed, which is out of scope here and needs your decision. |
| M3 | Production probabilities feed a 0.712 cutoff; the research rule uses 0.50; the display uses 0.50 | State which threshold applies to each output |
| M4 | No INSUFFICIENT_DATA state in production; missing values display as LOW | Do not claim production withholds a classification when evidence is missing |
| M5 | Municipal values are allocations, not forecasts or measurements | Describe them as modeled disaggregation, **indicative and not definitive determinations** |
| M6 | No public deployment of the integrated system | Do not describe the system as deployed or in use by DA. Describe a locally run prototype. |
| M7 | Production tests: 6 of 102 failing (2026-10-07; R) | Do not claim all tests pass |

**Nothing in production was changed to match the research.**
