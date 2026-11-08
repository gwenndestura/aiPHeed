# FI12: provincial food-insecurity validation and model reassessment

**FI12** · protocol `2949208888f5` locked 2026-11-03T02:31:10+00:00 · Evidence tags: [V] verified against a primary source in this repository; [S] secondary source, not verified; [R] computed by FI12 under the locked protocol; [F] read from an earlier study's result file.

**Question.** Can aiPHeed reliably forecast food insecurity at the provincial level, judged against independently
measured provincial observations?

**Answer.** No, and the available observations cannot show that any model does.
- The only verified direct provincial food-insecurity wave (FNRI 2015) cannot separate the five provinces statistically.
- The ENNS provincial values are secondary, mix three years and show internally inconsistent rankings.
- Every P0H4-family forecast starts in 2023, so the served model can be matched to one wave of food poverty only.
- FI10 price-pressure forecasts, the only ones covering every wave, rank provinces opposite to food poverty.
- No model beats simple references, no feature survives correction, no defensible HIGH/LOW label exists, and the 75 %
  target is unsupported for provincial outcomes.
- P0H4 stays served; nothing in production changed.

## Deliverables
1. [01_PROVINCIAL_DATASET_AUDIT.md](01_PROVINCIAL_DATASET_AUDIT.md)
2. [02_OUTCOME_DEFINITION_MATRIX.md](02_OUTCOME_DEFINITION_MATRIX.md)
3. [03_FORECAST_OBSERVATION_MATCHING.md](03_FORECAST_OBSERVATION_MATCHING.md)
4. [04_PROVINCIAL_VALIDATION_REPORT.md](04_PROVINCIAL_VALIDATION_REPORT.md)
5. [05_BASELINE_COMPARISON_REPORT.md](05_BASELINE_COMPARISON_REPORT.md)
6. [06_FEATURE_CONTRIBUTION_REPORT.md](06_FEATURE_CONTRIBUTION_REPORT.md)
7. [07_LEAD_TIME_ASSESSMENT.md](07_LEAD_TIME_ASSESSMENT.md)
8. [08_OVERFITTING_LEAKAGE_BIAS_AUDIT.md](08_OVERFITTING_LEAKAGE_BIAS_AUDIT.md)
9. [09_COMPLETE_MODEL_COMPARISON.md](09_COMPLETE_MODEL_COMPARISON.md)
10. [10_FINAL_METHODOLOGY_RECOMMENDATION.md](10_FINAL_METHODOLOGY_RECOMMENDATION.md)
11. [11_OBJECTIVE_ACHIEVEMENT_ASSESSMENT.md](11_OBJECTIVE_ACHIEVEMENT_ASSESSMENT.md)
12. [12_PRODUCTION_ADOPTION_DECISION.md](12_PRODUCTION_ADOPTION_DECISION.md)

## Code and outputs
- Code: `backend/app/fi12/` (`outcomes.py`, `match.py`, `study.py`, `report.py`); tests `backend/tests/unit/test_fi12.py`.
- Protocol lock: `backend/data/fi12/out/PROTOCOL_LOCK.json` (frozen before any agreement was computed).
- Outputs: `backend/data/fi12/out/` (outcomes, matches, ranking, levels, features, evaluation).
- Reproduce: `cd backend && python -m app.fi12.study run && python -m app.fi12.report`.

## Cross-source consistency of the outcomes (descriptive, computed after the lock)
| a | b | spearman |
|---|---|---|
| ENNS_MODSEV · own year | ENNS_SEV · own year | -0.10 |
| ENNS_MODSEV · own year | FNRI15_SEV · 2015 | -0.10 |
| ENNS_MODSEV · own year | PSA_SUB_FAM · 2018 | 0.70 |
| ENNS_MODSEV · own year | PSA_SUB_FAM · 2021 | 0.37 |
| ENNS_MODSEV · own year | PSA_SUB_FAM · 2023 | -0.82 |
| ENNS_SEV · own year | FNRI15_SEV · 2015 | 0.70 |
| ENNS_SEV · own year | PSA_SUB_FAM · 2018 | 0.10 |
| ENNS_SEV · own year | PSA_SUB_FAM · 2021 | 0.53 |
| ENNS_SEV · own year | PSA_SUB_FAM · 2023 | 0.10 |
| FNRI15_SEV · 2015 | PSA_SUB_FAM · 2018 | 0.50 |
| FNRI15_SEV · 2015 | PSA_SUB_FAM · 2021 | 0.11 |
| FNRI15_SEV · 2015 | PSA_SUB_FAM · 2023 | 0.36 |
| PSA_SUB_FAM · 2018 | PSA_SUB_FAM · 2021 | 0.32 |
| PSA_SUB_FAM · 2018 | PSA_SUB_FAM · 2023 | -0.46 |
| PSA_SUB_FAM · 2021 | PSA_SUB_FAM · 2023 | -0.70 |

The sources do not agree on which province is worst; two measures from the same ENNS survey rank provinces with ρ −0.1.
