# Backend technical readiness (Objective 5; questionnaire untouched)

## 1. Completed backend technical checks

| Area | Result |
|---|---|
| Model identification | `/api/v1/config` (`servingModel`, `modelPerformance`, `indicator`) and `/api/v1/final/risk/evaluation` all name the served model and plan hash. In the C-E2 demo: ALLBASE-CE2, a1b469da…, MRLT 3, served lead 2 |
| Evaluation metadata | Derived from the served `evaluation.json`; no hard-coded metrics (`API_CONFIG_FIX_REPORT.md`) |
| Traceability | Every forecast row carries issue date, origin, lead, model, input values, SHAP and its availability flags |
| Reproducibility | C-E2 refit is byte-identical; the seal dry runs replay exactly |
| Data validation | Strict mode (`AIPHEED_STRICT_MODEL=1`) refuses to start without required artifacts. A missing evaluation yields an explicit "unavailable" result |
| Error handling | Unknown quarter or province → 404; invalid scope → 422. No 500s after the `probabilityPricePressure` schema fix (optional when no price forecast exists) |
| Review and publication | Forecasts stay STAGED until an administrator approves (Rule 1). The archived-supersession bug was fixed on 2026-11-03 (`review.py`) |
| Performance (local) | `/config` 0.06 s; explainability 0.29–0.33 s |
| Security | Admin endpoints return 401 without a token. The demo approver account is disabled and clearly named; demo databases are separate scratch files |
| Logging | Uvicorn access log; review actions are written to the audit log |
| Maintainability | 1,022 backend tests (`BACKEND_TEST_REPORT.md`) |

## 2. Checks requiring real evaluator responses (not done; must not be simulated)

- All ISO/IEC 25010 characteristics rated by the 50 DA Region IV-A personnel (functional suitability, performance
  efficiency, compatibility, usability, reliability, security, maintainability, portability).
- FNRI face-validity judgement.
- Analysis per `OBJ5_ANALYSIS_PLAN.md` (851ea697…), once responses close.

## 3. Checks requiring adviser or stakeholder approval

- Which build the survey evaluates: the deployed FIRI v2 site or the C-b build (`OBJ5_EVALUATION_READINESS.md` §1).
- Adoption of any candidate (C-E2, S1) over C-b.
- D3.1 (province formula) and D3.2 (density weight).
- Commit and seal approvals.
