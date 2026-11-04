# Objective 5: developer system tests (separate from evaluator feedback)

Run after the alignment plan is approved and applied. Record pass/fail and evidence for each test.

| # | ISO/IEC 25010 | Test | Pass condition |
|---|---|---|---|
| 1 | Functional correctness | API `/forecasts` values = `backend/data/foodinsecurity_engine/rows.csv` for all 5 provinces × 2 leads | Exact |
| 2 | Functional correctness | Map colours, rankings and PDF values = API values for 142 LGUs | Exact |
| 3 | Functional correctness | Every displayed model metric = `evaluation.json` (no frontend constants) | Automated frontend test |
| 4 | Functional completeness | Map, quarter selector, rankings, SHAP explanation, alerts, PDF export, admin review all reachable | Manual walkthrough |
| 5 | Functional appropriateness | Rule 6 labels (horizon, confidence, verification date) on every forecast; Rule 8 `disaggregation_label` on every LGU | Automated |
| 6 | Workflow | PENDING → STAGED → PUBLISHED/rejected; staged items invisible publicly; audit log written | Backend tests + manual |
| 7 | Alerts (Rule 7) | Alert candidates staged, never shown before confirmation; no automatic external message | Backend tests |
| 8 | Performance efficiency | Dashboard first load and map switch times on the deployed service (median of 10) | ≤ 3 s target, report actual |
| 9 | Reliability | `AIPHEED_STRICT_MODEL=1` refuses to start with a missing artifact; health check | Test |
| 10 | Security | Admin routes need authentication; refresh cookie SameSite=Strict; no secrets in the repository | Tests + scan |
| 11 | Maintainability | Backend suite (1014 passed, 18 skipped on 2026-11-03), frontend suite, lint | Pass |
| 12 | Portability | Docker build reproduces; README setup on a clean machine | Pass |
