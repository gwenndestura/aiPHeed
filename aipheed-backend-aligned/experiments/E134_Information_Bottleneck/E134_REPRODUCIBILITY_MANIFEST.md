# E134 reproducibility manifest

**Environment.**
- Backend virtual environment `C:\Users\admin\aipheed\backend\venv` (Python 3.13; numpy, pandas, scipy, scikit-learn, lightgbm).
- Run every script from `aipheed-backend-aligned/experiments/E134_Information_Bottleneck/`.

**Commits** (branch `aiPHeed/corrected-data-pipeline`, local only):
- protocol `139ca7f` (sha256 in `runner/PROTOCOL_SHA256.txt`);
- results in the commit after it;
- E133 code `56d1ec1` (imported unchanged).

## Order

| Step | Command | Output | Time |
|---|---|---|---|
| 0 | `python -I runner/e134_baseline.py` | `out/baseline/*`, `out/e134_baseline_record.json` (E133 reproduced, max difference 0) | ~70 s |
| 1 | `python -I runner/e134_acquire.py` | `data/raw/*`, `data/acquisition_log.json` (already done; re-running fetches today's vintage) | ~2 min |
| 2 | `python -I runner/e134_run.py` | `out/e134_predictions.csv`, `e134_metrics.csv`, `e134_rules.json`, `e134_area_ablation.csv`, `e134_area_palay.csv`, `e134_regional_rainfall.csv` | ~70 s |
| 3 | `python -I runner/e134_diagnostics.py` | `out/t1_*`, `n1_*`, `ev_*`, `pv_*`, `e134_fssi_calabarzon_popweighted.csv` | ~1 min |
| 4 | `python -I runner/e134_summary.py` | `out/e134_summary.json`, `E134_MODEL_COMPARISON.csv`, `E134_WALK_FORWARD_RESULTS.csv`, `E134_FEATURE_CONTRIBUTION_REPORT.csv` | seconds |
| 5 | `python -I runner/e134_seal.py` | `sealed/E134_PROSPECTIVE_SEAL.csv` (sha256 `e4f844dd…`); refuses to overwrite | ~20 s |
| — | `python -I runner/score_e134.py` | Primary-only prospective scores (after SWS publishes 2026-Q4) | — |
| — | `python -I runner/e134_reissue.py <date>` | Quarterly write-once re-issues | — |

**Tests:** `backend/tests/unit/test_e134_information.py`. They cover:
- seal integrity and refusal to overwrite;
- the exact E133 reproduction;
- point-in-time availability of the new drivers;
- 2021+ raw data;
- the region → area crosswalk;
- that area drivers move only the area level;
- the selection rule and its reported outcome;
- the primary-only scorer.

**Configuration.**
- Fixed in `E134_FROZEN_PROTOCOL.md` and `runner/e134_run.py`:
  - drivers, availability rules (10 days; 75 days for palay), β prior N(0, 1), sign constraints;
  - E133 grids, bounds and starts.
- Deterministic: there is no random component in fitting. Permutation tests use seed 134.

**Inputs and hashes:**
- `data/acquisition_log.json` (E134);
- E133 `data/acquisition_log.json` (B30);
- E131/E132 acquisition logs;
- E110 SWS rounds;
- E119 regional dataset;
- FSSI v2 panel;
- POPCEN 2024.

**Determinism check.** E133's walk-forward reproduces to 0.0 (baseline record), and the E134 seal re-derives HFM-X and E134-ONI equal to the E133 seal (asserted to 1e-9).
