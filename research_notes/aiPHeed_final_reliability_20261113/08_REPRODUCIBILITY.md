# 08 — Final model reproducibility report

## 1. Model definition
- **Code:** `C:\Users\admin\aipheed_hcw\backend\app\hcw\final_engine.py` (sha256 `2c8e396e…4a81`).
  - Research twin: `research_notes/aiPHeed_hcw_final_optimization_20261112/scripts/engine_final.py` (`f56d13f4…1f16`), called with `rate='lin', miss='mind', cw='balanced'`.
  - Base engine: `app/hcw/engine.py` (`e38f6adf…e4a1`).
- **Procedure inside each fit** (chosen on training rows only):
  - choice of anchor (H / OH / RSS) and of input set (GOV / GOV+cons / FULL);
  - 25-input selection, then correlation pruning;
  - 16-setting grid, using inner GroupKFold by region;
  - monotone constraints from `Pv.SIGN` / `H.NEW_SIGN`;
  - survey-precision × balanced class weights;
  - RATE target (y − anchor)/g with weight g²;
  - MIND median fill plus missing flags;
  - raw-first calibration.
- **Cut-off:** 0.50.
- **Chosen configurations at Lead 1 (5 seeds):**
  - 2018 fold: anchor OH, with FULL / GOV / GOV+cons;
  - 2019 fold: same as 2018;
  - 2021 fold: RSS | FULL in all 5 seeds;
  - always num_leaves 3, 150 trees, learning rate 0.02.
  - Full strings are in `aiPHeed_final_stability_lead_20261113/features_lead/FINALL__*.json`.
- **Training cut-off for the live fit:** ENNS 2021 is the latest released round. The information cut-off for issue 2026-Q4 is 2026-11-01 (`AIPHEED_LIVE_ASOF`).

## 2. Data versions (sha256)

| File | sha256 |
|---|---|
| `aipheed_e145/backend/data/e158/out/oof.csv` (labels + baselines) | `9f0c9184…f3f5` |
| `data/hfias/clean/fnri2015_hfias.csv` | `c0a1ad6c…8053` |
| `data/hfias/clean/enns_hfias.csv` | `db2d1d63…56b3` |
| `data/e141/clean/nns2013_hfias.csv` | `e9cb4178…a072` |
| `data/e147/raw/sealed_2021_labels.csv` | `f15a1977…4ef5` |
| `data/e147/raw/heatmap_provincial.jsonl` | `0f845b1f…ce36` |
| `data/fi_labels/clean/published_fies_psa_sdg212.csv` | `b5ff5f35…cf30` |
| `data/fi5/raw/psa/psa_poverty_incidence_all_regions_2018_2023.csv` | `f0a2521f…482f` |
| `data/fi5/raw/sws/sws_area_rounds_full.csv` | `d2519664…6596` |
| Fold builder `aiPHeed_objective_completion_20261111/scripts/run_qs.py` (+ `cache/*.pkl`) | `b1e2b610…4c40` |

Full hashes are in `HASHES.sha256`.

## 3. Reproduction checks
| Check | Result |
|---|---|
| Reported FINAL Lead-1 metrics (0.861 / 0.80 / 0.80 / 0.898 / BA 0.847) | Reproduced exactly from the stored 5-seed fits |
| 110 contributor fold fits vs the stored FINAL probabilities | max abs difference 2.2e-16 |
| Seal `4ad9267f` (FINAL, ENNS 2022) | Hash re-verified on 2026-11-13 |
| Seal `71ebe142` (FINAL / ET / ETMIX, ENNS 2022) | Hash re-verified; its FINAL rows match `4ad9267f` within 5e-7 |
| Origin / leakage check | 110 fits, 0 violations |

## 4. Reproducibility gaps (open)
1. **The FINAL code is not under version control.**
   - `aipheed_hcw/backend/app/hcw/` is untracked in git (`?? backend/app/hcw/`).
   - All `research_notes/` folders in `aipheed_final` are untracked.
   - A clean checkout cannot rebuild FINAL. Committing them needs your approval.
2. The fold builder depends on pickled caches (`cache/*.pkl`). They hold the as-of inputs, but they are binary and not regenerated in this study.
3. Run environment: `C:\Users\admin\aipheed\backend\venv` (LightGBM, pandas, scikit-learn). Package versions are not pinned in a lock file for this path.

## 5. Re-running this study
1. From `C:\Users\admin\aipheed_e145\backend`: `PYTHONPATH=. python <folder>/scripts/gt_audit.py`
2. From `<folder>/scripts`: `python -I rel_eval.py`, `python contrib_final.py`, `python -I ext_checks.py`, `python -I stab_eval.py`
3. From `C:\Users\admin\aipheed_hcw\backend`: `PYTHONPATH=. python <folder>/scripts/stab_jobs.py --jobs 16` (about 10 minutes; it skips existing parts) and `PYTHONPATH=. python <folder>/scripts/direction_check.py`
