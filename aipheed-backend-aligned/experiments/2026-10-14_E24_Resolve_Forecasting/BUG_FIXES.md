# Bug fixes and corrections (E24)

## 0. Isolation status (important)

**E24 rule:** work only in the experiment copy. All E24 code changes are in `experiments/2026-10-14_E24_Resolve_Forecasting/backend_dev/` (a copy of `aipheed-backend-aligned/app` + the CLI + config; no data, databases or models) and in `dashboard_dev/` (a copy; `node_modules` is a read-only junction to `frontend/node_modules`).

**E23, however, edited `aipheed-backend-aligned/` directly.** That folder is part of the original git checkout. It holds:

- **16 modified tracked files**, uncommitted: `app/api/router.py`, `app/config.py`, `app/db/models.py`, `app/main.py`, `app/ml/corpus/_dates.py`, `app/ml/corpus/bias_weighter.py`, `app/ml/features/label_generator.py`, `app/ml/inference/disaggregator.py`, `app/services/report.py`, `app/services/security.py`, `app/tasks/scheduler.py`, and `scripts/` `build_annotation_workbook.py`, `build_curated_corpus.py`, `build_results_docs.py`, `iso25010_summary.py`, `run_quarterly_pipeline.py`;
- **5 new untracked items:** `app/api/v1/quarterly.py`, `app/quarterly/`, `config/forecast_period.json`, `config/quarterly_sources.json`, `scripts/quarterly_update.py`.

E24 did **not** modify or revert them, to preserve existing changes. Pre-edit copies are in `E23/docs/*.before`. **You decide whether to keep them.** To revert:

```
git -C C:\Users\admin\aipheed checkout -- <the 16 files>
```

Then delete the 5 new items. `backend/`, `frontend/`, E17 and E18 are unchanged (git shows no changes; E17/E18 hash lists verified).

## Fixes made in E24 (isolated copy)

| # | Defect | Fix | Verification |
|---|---|---|---|
| B1 | **Province averages were presented as municipal poverty values.** The ranking table and dashboard showed 126 province-mean values in the same column as the 16 PSA municipal estimates. | `lgu_poverty.rank_lgus`: `poverty_lgu_estimate` is **null** where PSA publishes no municipal value. The formula's input is shown as `poverty_value_used` with `poverty_value_kind` = "province-mean substitute (no municipal estimate)", plus a per-LGU limitation sentence. **Approved formula unchanged:** risk indices identical to E23 (max diff 0.0). | `test_ranking_labels_substitutes_and_is_deterministic`; `runs/lgu_validation.json`; vitest "labels every province-mean substitute" |
| B2 | **Ties were ordered by row order** (7 tied LGUs). | Competition ranking (1, 2, 2, 4) on risk_index rounded to 4 dp; listing order inside a tie = lgu_code | `test_tie_rule_competition_rank`, shuffled-input determinism test |
| B3 | **PSGC codes read from Excel lose their leading zero** (found by the new test before any real use). A 10-digit code became 9 digits and was mistaken for the legacy form, so 0 of 3 matched. | `legacy_psgc` treats numeric codes by digit count; the workbook is read with `dtype=str` | `test_legacy_psgc`, `test_sae_workbook_ingestion_and_validation` |
| B4 | **No schema / duplicate / conflict validation** before an input could satisfy a requirement | `validation.check_table` | `test_check_table_flags_duplicates_conflicts_and_gaps` |
| B5 | **No NLP stage in the quarterly cycle** (news counted but not scored) | `nlp_stage.build_news_features` (approved functions, eligible articles only) | 2 tests |
| B6 | **No model/feature version record** for forecasts | `validation.model_version_record` | 1 test |
| B7 | **Registry paths were relative to the original backend**, so they failed outside it | Paths in `backend_dev/config/quarterly_sources.json` made absolute; same files, same hashes | 2027-Q1 cycle reruns with an identical status |
| B8 | **The dashboard rendered "accuracy > 75%" without the other criteria** | The E24 page shows C1–C9 and "Goal NOT met" unless all are true; C9 shows "not assessable" | jsdom render test |

**Did any fix change a scientific result?** No. The rankings are numerically identical, and the required models reproduce E23 exactly (see FINAL_REPORT).
