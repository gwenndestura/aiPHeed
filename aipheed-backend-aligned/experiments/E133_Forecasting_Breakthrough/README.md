# E133 · Forecasting breakthrough search

**Outcome.**
- **Selected (frozen rule):** HFM-X, a hierarchical factor state-space model with one theory-signed driver per trigger group in the state equation.
- **Lead 2** (40 rows, 10 quarters, including the 2024 surge):

  | Measure | HFM-X | SEAS-LLM | Persistence |
  |---|---|---|---|
  | Within tolerance | **0.50** | 0.45 | 0.40 |
  | MAE | **4.87** | 5.72 | 5.98 |
  | Sharp increases caught (of 16) | **8** | 3 | 0 |

- **75 % is not achieved, and no lead is reliable** (fails N2 and N5).
- Full report: `E133_FINAL_RESEARCH_PACKAGE.md` (14 deliverables).

**Context.**
- Protocol frozen at `9683aad` (sha256 in `runner/PROTOCOL_SHA256.txt`).
- Branch `aiPHeed/corrected-data-pipeline`; offline only. Nothing pushed, nothing in production changed.

## Reproduce

Use the backend virtual environment and run from this folder:

```
python -I runner/e133_reproduce.py     # exact E132 reproduction (writes out/e133_e132_reproduced_predictions.csv)
python -I runner/e133_acquire.py       # bottom-30 % income households' CPI, regions, 2021+ only (already done)
python -I runner/e133_run.py           # all E133 models, both issue policies, both sets, N1-N7, ablation (~70 s)
python -I runner/e133_diagnostics.py   # D1-D5 (~4 min, permutation tests)
python -I runner/e133_sensitivity.py   # beta prior sensitivity
python -I runner/e133_summary.py       # headline numbers and trigger-group status
python -I runner/e133_seal.py          # write-once prospective seal (already written; refuses to overwrite)
```

Tests: `backend/tests/unit/test_e133_breakthrough.py`.

**Scoring.**
- When SWS publishes 2026-Q4, add the rounds to `E131_Objectives_Resolution/data/sws_rounds_after_2026Q3.csv`.
- Then run `python -I runner/score_e133.py`, which uses the primary criterion only.

## Files

| Kind | Files |
|---|---|
| Report | `E133_FINAL_RESEARCH_PACKAGE.md` |
| Protocol | `E133_FROZEN_PROTOCOL.md` |
| Logs | `DEVIATIONS.md`, `CONTAMINATION_LOG.md` |

**Machine outputs** (`out/`):

| File | Contents |
|---|---|
| `e133_predictions.csv` | Predictions |
| `e133_metrics.csv` | Metrics |
| `e133_rules.json` | N1–N7 |
| `e133_ablation.csv`, `e133_trigger_contribution.csv` | Ablation and trigger-group status |
| `e133_prior_sensitivity.csv` | Prior sensitivity |
| `e133_summary.json` | Headline numbers |
| `d1_` … `d5_` | Diagnostics |
| `e133_drivers_*.csv` | Drivers |
| `e133_reproduction_check.json` | E132 reproduction check |

**Seals** (`sealed/`): `E133_PROSPECTIVE_SEAL.csv` and `E133_PROVINCIAL_MODEL_BASED_SEAL.csv`, with hashes in `E133_SEAL_SHA256.txt`.
