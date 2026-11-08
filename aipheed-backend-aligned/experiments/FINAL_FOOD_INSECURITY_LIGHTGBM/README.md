# FINAL: aiPHeed food-insecurity forecasting with LightGBM

**Branch:** `aiPHeed/final-food-insecurity-lightgbm`, from `1baca5e` (E111 verified, plus E112–E114 preserved).

**Status:** evaluated. Nothing is merged, deployed or served.

**Result**
- 75% accuracy is **not reached**: FIL scores 0.32–0.50 at Leads 1–4, and FIL-LONG scores 0.50–0.55 on the untouched 2003–2020 quarters.
- It is **not attainable** for this outcome: the Bayes ceiling is 0.58–0.64 at Lead 1.
- **No reliable lead** exists.
- News gives **no forecast gain**.

Start with `FINAL_RECOMMENDATION.md`.

## Deliverables

| # | File |
|---|---|
| 1 | `FINAL_PROTOCOL.md`: frozen 2026-10-25T12:15Z, sha `86de5c8c…` |
| 1a | `ADDENDUM_1.md`: attainable-accuracy simulation and noise-reduced anchors; frozen before it was run |
| 1b | `ADDENDUM_2.md`: replication test of the news signal; frozen before it was run |
| 2 | `TARGET_AND_DATA_VALIDATION.md` |
| 3 | `NEWS_FEATURES_AND_CONTRIBUTION.md` |
| 4 | `LIGHTGBM_MODEL_AND_METRICS.md` |
| 5 | `GENERALIZATION_AND_SURGE_EVALUATION.md` |
| 6 | `MAXIMUM_RELIABLE_LEAD_TIME.md` |
| 7 | `THESIS_OBJECTIVE_ASSESSMENT.md` |
| 8 | `FINAL_SIMPLE_METHODOLOGY.md` |
| 9 | `FINAL_RECOMMENDATION.md` |

**Data**
- `data/sws_area_rounds_2021.csv`: the primary outcome.
- `data/long/`: the E114 SWS 1998–2026 series and long covariates, used by the secondary arm only.
- `data/feature_map.csv`: every model column with its family, source, geography, period, availability rule and missingness.
- `data/data_sources.csv`: every source file with its SHA-256.
- `data/news_headline_flags.csv`: per-headline category, anticipatory and duplicate flags, without titles.

**Code (`runner/`)**
- `fi_lib.py`: model, label, baselines and metrics.
- `news_features.py`
- `run_final.py`: all phases.
- `ceiling_by_margin.py`
- `score_prospective.py`

**Outputs (`out/`)**

| File(s) | Content |
|---|---|
| `predictions_primary.csv` | One row per (area, issue date, lead), with the timing bookkeeping and every method |
| `predictions_long.csv`, `predictions_long_s.csv` | The same for the secondary arm |
| `pred_<variant>.csv` | Ablation predictions |
| `results_*.json` | Metrics and tests |
| `leakage_audit.json` | Leakage audit result |
| `sealed_prospective.csv` | Seal, SHA-256 `c73a0709…` |
| `backend_test_suite.txt` | Full backend test log |

**Tests:** `backend/tests/unit/test_final_fi_lgbm.py`

## Reproduce

Run from `runner/`, using the backend venv:

```bash
python run_final.py all
```

This runs data → audit → score → long → news (100 placebo refits) → psa → general → addendum1 → addendum2 → seal, in about 25 minutes. Then run:

```bash
python ceiling_by_margin.py
```
