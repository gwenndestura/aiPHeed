# aiPHeed research objectives: completion matrix (2026-11-13)

**Scope.**
- **Objectives:** as audited on 2026-11-11 (`../aiPHeed_objectives_audit_20261111/OBJECTIVES_AUDIT_REPORT.md`), with the owner's statements of that evening applied: 50 DA Region IV-A participants evaluated the system, and DA checked the news dataset.
- **Model:** FINAL (RATE + MIND) is the model under investigation. E196 is the served production model.
- **Status rule:** "Completed" requires evidence that the objective's stated requirement is met, not merely that a component exists in code.

| # | Objective | Status | Evidence (what verifies it) | Remaining work |
|---|---|---|---|---|
| 1 | **NLP pipeline:** XLM-R zero-shot events and BERTopic topics into province-quarter news indicators (FSSI) inside the trigger groups | **Completed (as specified)** | `app/e151/score.py` (XLM-R zero-shot, 10 bilingual hypotheses); BERTopic refitted per origin (NPMI 0.256, diversity 0.872); FSSI for 4,368 province-quarters; news dataset validated by DA (owner-attested, 11-11). Pipeline as-of tests pass (`test_e151`: no story after the issue date enters a window). In FINAL, news indices are counted inside their topic's group (`FINAL_FIVE_TRIGGER_GROUP_AUDIT.md`) | Disclose: news indices carry little weight in FINAL (cross-topic news 0.09 gain share at Lead 1, 0 at Leads 3–8; removing them changes no forecast); FSSI itself is not a FINAL input; no inter-annotator agreement statistic |
| 2 | **LightGBM forecasting with full evaluation and a maximum reliable lead time** | **Partially completed** | FINAL is implemented, reproduced exactly (45/45 and 110/110 fits) and evaluated walk-forward at Leads 1–8 with every required metric, intervals, confusion matrices, and round and province breakdowns (`FINAL_MAX_RELIABLE_LEAD_REPORT.md`; `evidence/LEAD_*`). Rules 1–5 pass at Lead 1 | **Not demonstrated: a reliable lead.** Under the locked standalone rules no lead is reliable: FINAL fails stability (2021 recall 1/4); the elapsed-time correction FINAL-ET fails calibration. All results are retrospective on reused rows; no independent round exists |
| 3 | **Geospatial disaggregation:** city and municipal prioritisation by poverty incidence (60 %) and density (40 %) | **Completed (as specified; served with E196)** | 11-11 audit: 142 LGUs; formula exact 142/142; PSA SAE values exact 141/141; labelled "not a measured municipal rate"; re-verified 11-13 (`LGU rows` API checks pass, 22/22) | Ranks derive from E196, not FINAL. Lucena's substituted poverty value is unverified. No municipal outcome exists to validate the ranking |
| 4 | **Comparison with baselines** | **Completed (retrospective)** | FINAL against the six stored baselines (persistence, GNT, PSA-only, LR, LR + news, news-only) on identical rows at Leads 1–8: lower Brier in 48/48, significant in 43/48 (paired bootstrap; `evidence/LEAD_baselines_paired.csv`) | The rows are reused. Persistence detects more HIGH provinces (recall 0.96) at half the precision (0.48), which should be disclosed |
| 5 | **Dashboard deployment, DA evaluation, face validity** | **Partially completed** | Deployed at aipheed.vercel.app (E196). The 11-13 app fixes are verified locally (API 22/22, frontend 101/101) but **not yet committed or deployed**. DA Region IV-A evaluation, n = 50 (owner-attested). FNRI face validity: CALABARZON provinces correctly LOW in their ENNS rounds | The dashboard serves **E196, not FINAL**. Its five trigger bars do not match the brief's five groups (it shows Fish Production; FINAL uses no remittance input; climate and employment are inert in FINAL). The 11-13 fixes await commit approval. No HIGH CALABARZON case exists to test detection |
| G | **General objective:** develop, validate and deploy a food-insecurity risk forecasting system for DA IV-A | **Partially completed** | Developed and deployed (E196); FINAL researched with full standalone evaluation | **Not independently validated.** No model passes all seven standalone rules on the available data |

## What would move the partial objectives to completed
- **Objective 2:**
  - an independent provincial HFIAS round with sealed forecasts (`FINAL_MAX_RELIABLE_LEAD_REPORT.md`, last section), and a model passing all seven rules at Lead 1 on it;
  - or your decision on how to treat the stale-anchor condition, documented as a limitation.
- **Objective 5:**
  - your approval to commit the 11-13 application fixes;
  - a decision on which model the dashboard serves;
  - a decision on how its five bars map to the model's actual inputs.
