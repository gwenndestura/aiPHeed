# aiPHeed: objectives completion and model validation (E71)

This report answers the E71 brief. Its detail is in `FOOD_INSECURITY_DIMENSIONAL_FRAMEWORK_AND_REDESIGN.md`, and the final consolidated status is in `FINAL_AIPEED_THESIS_AND_MODEL_REPORT.md`. Item numbers follow the brief.

**1. Objectives and status.** The approved wording is quoted verbatim in the final report §9.

| Objective | Status |
|---|---|
| 1 | Partially met |
| 2 | Partially met |
| 3 | Partially met |
| 4 | Partially met |

None is fully met.

**2. Changes for each E70 finding.**

| E70 finding | E71 change |
|---|---|
| T43 collapses to price pressure | Replaced for analysis by the outcome-free dimensional target FIR71. FIR71 is not collapsed: it equals the price condition on 48/90 rows. |
| Missed HIGH, calibration | DIMFUSE projection model. Calibration slope 1.01 at Lead 2. |
| Weak LightGBM trees | Fixed-configuration LightGBM vs simpler models. The simpler models won. |
| Regimes | Per-quarter results reported |
| Objective 1 human validation | Two-annotator workflow with κ |
| NLP value | Ablation Δ +0.002, so no value |

**3. Revised target and its validity.**
- FIR71 is defined in the framework document §4.
- **Validity was not established.** Its rank correlation with SWS hunger is −0.21 [−0.68, +0.35], and with subsistence −0.40 and −0.87.

**4. Metrics.** Lead-1, Lead-2 and Lead-3 metrics and baselines are in framework document §6.2 and `E71/tables/E71_TABLES.md`.

**5. 80% Lead-2.** Not reached: the best result is 29/45 = 0.644 on 45 rows. The evaluation quarters were not unseen.

**6. Human validation.**
- No labels exist yet.
- **For you to complete:** label `E70_Objectives_Completion/annotation/HUMAN_ANNOTATION_SAMPLE.csv`. A second annotator labels `E71_Food_Insecurity_Dimensions/annotation/HUMAN_ANNOTATION_SAMPLE_annotator2.csv`.
- Then run `python -B runner/e71_annotation.py score`.

**7. Tests, reproduction, files, commits.** See `FINAL_IMPLEMENTATION_AND_TEST_REPORT.md`.

**8. Completed work vs open requirements.**

| Completed implementation | Needs external data, researcher input or future outcomes |
|---|---|
| Framework, index, forecasts, seals, validation tests, annotation tooling, served-system explanation | CBMS / FNRI outcomes |
| | Human labels |
| | Prospective outcomes for 2026-Q4 and 2027-Q1 |
