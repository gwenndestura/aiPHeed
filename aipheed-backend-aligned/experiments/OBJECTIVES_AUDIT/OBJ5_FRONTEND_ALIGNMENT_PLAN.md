# Objective 5: dashboard alignment with the served model (PLAN FOR APPROVAL; nothing changed)

**Problem:**
- The deployed default (`render.yaml`: no `AIPHEED_MAP_MODEL`) serves the FIRI v2 / hunger × food-price system.
- The live Landing page and About box describe that older model and hardcode its numbers.
- C-b, the main model, is served only with `AIPHEED_MAP_MODEL=foodinsecurity`.
- Evaluators would be rating a model that is not the thesis model.

## 1. Content to change (verified file:line)

| File:line | Current | Problem | Proposed |
|---|---|---|---|
| `frontend/src/pages/Landing.tsx:154–155, 174, 177` | "food prices are rising unusually fast", "LightGBM food-price forecast" | Old target | C-b target: Balance Luzon hunger > 11.3% next quarter |
| `Landing.tsx:220, 228, 232` | Hunger × food-price definition; "12 indicator families"; "hunger chance multiplied by the food-price chance" | Old model | C-b's 21 inputs (hunger history, local/world prices, climate, supply, FSSI anomaly); one probability |
| `Landing.tsx:245, 359, 363, 456, 559, 563` | Lead 2 "experimental", AUC 0.62, accuracy 0.84 / 0.77, "70 province-quarters" | Old evaluation | C-b: MRLT 2; Lead 1/2 accuracy 0.790, AUC 0.70, 62 quarters; R7 caveat |
| `Landing.tsx:336–338` (lead table), `347–355` (Brier table) | Hardcoded numbers | Not C-b's; hardcoded | **Read from the API** (`evaluation.json` → leads, objective4) instead of constants |
| `Landing.tsx:516, 518, 551, 676` | "provinces differ only through food prices" | Old method | "Province and LGU values are vulnerability-weighted indices of the regional forecast" (Option C wording) |
| `frontend/src/components/AboutModal.tsx:42–45, 75, 119, 178` | Old definition and model row; alert at 0.60 | Old model | C-b text from the API (`model_line`, caveats) |
| `frontend/src/components/DashboardOverview.tsx:17` | "F1 / AUC 0.82 / 0.87" | Unsupported numbers (dead component) | **Delete the component** |
| `frontend/src/components/RegionSidebar.tsx:154–159` | "SMOTE + Optuna", F1 0.82, AUC 0.87, **SUS 78** | Unsupported numbers (dead component) | **Delete the component** |
| `render.yaml` / `backend/Dockerfile` | No `AIPHEED_MAP_MODEL` | C-b not served by default | Add `AIPHEED_MAP_MODEL=foodinsecurity` (deployment only on your separate authorization) |

## 2. Rule

Every number shown about the model comes from the API (`/api/v1/...` evaluation fields produced by `export_fi.py`
from the sealed results). There are no constants in the frontend. A frontend test asserts that the Landing metrics
equal `evaluation.json`.

## 3. Verification after the change

- Frontend tests; a new test for metric provenance.
- Backend mode tests 27/27; full suite.
- Manual check of map, rankings, alerts and PDF against `rows.csv`.

**Needs your explicit approval:** frontend changes, `render.yaml`/`Dockerfile`, and later any deployment.
