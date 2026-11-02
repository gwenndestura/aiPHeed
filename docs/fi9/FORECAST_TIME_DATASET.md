# Forecast-time (as-of) dataset

Rebuild: `python -m app.fi9.vintage build` (from `backend/`). Code: `app/fi9/vintage.py`, which uses
`app/fi7/design.py` and `app/fi5/features.py`.

| File (backend/data/fi9/out) | Content |
|---|---|
| `forecast_time_dataset_h1.csv` | One row per issue date (1999-Q1 – latest). Every feature holds the latest value **available on the issue date**. Columns: DATA_DICTIONARY.md |
| `data_vintage_long.csv` | Every source value with source, indicator, observation period (`period_end`), availability date (`available_from`), value, unit, domain, geographic level, revision status and quality status |
| `leakage_checks.json` | Automated checks on the dataset |

## How availability is enforced

* Every source carries `available_from`: the official release date (SWS releases, PSA poverty), or a release rule
  that is never earlier than the real calendar (CPI: the 10th of the next month; LFS and palay: +45 days;
  remittances: 15 February of the next year; NASA POWER: +30 days; typhoons: the passage date).
* `FeatureBuilder.row()` filters every source to `available_from <= issue date` before taking the latest value.
  Nothing is forward- or backward-filled across a publication date.
* The training set for each forecast holds only quarters whose SWS result was **published** by the issue date
  (`target_published <= issue_date`). This is recorded per forecast as `train_max_target_published`.
* Five-year normals and z-scores use only earlier values (expanding windows).
* News: quarterly indices come from the last complete quarter before the issue date; 90-day windows end at the
  issue date. The topic and zero-shot models are fixed pretrained models (no fitting on future documents).

## Automated tests

* `tests/unit/test_fi9.py::test_future_records_cannot_change_a_historical_row` poisons every source with absurd
  values that become available one day after the issue date and requires the row to stay identical. A control run
  (poisoning one day *before*) changes the row, so the test can fail.
* `app/fi9/audit.py` (the `predictors_equal_vintage_values_known_at_issue` check) recomputes six key features at every
  issue date from the vintage table alone. It found 0 mismatches.
* `leakage_checks.json`:
  * the target is the next quarter;
  * the issue date falls inside the issue quarter;
  * the latest reading was published by the issue date;
  * the target was published after the issue date;
  * there are no duplicate issue dates or targets.

## Known vintage limitation

CPI, LFS and the World Bank remittance series are the **current vintage**. Their first-release values were not
reconstructed. PSA CPI is rarely revised apart from rebasing, so the effect on year-on-year rates is small, and
the ablation found that these inputs add nothing at Lead 1 anyway.
