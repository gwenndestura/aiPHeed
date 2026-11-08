# E132 · Final methodology search (final master directive)

**Outcome.**
- **Best model:** SEAS-LLM, a measurement-aware state-space model with the documented 2025 break and a learned quarter-of-year effect. At Lead 2 it reaches **61 %** within the frozen primary tolerance, up from 50 % in E131.
- **75 % is not achieved, and no lead is reliable.**
- The final package (`E132_FINAL_RESEARCH_PACKAGE.md`) covers all 18 required deliverables.

**Context.**
- Protocol frozen at `4b880f0` (sha256 in `runner/PROTOCOL_SHA256.txt`).
- Branch `aiPHeed/corrected-data-pipeline`; offline only. Nothing pushed, nothing in production changed.

## Reproduce

Use the backend virtual environment and run from this folder:

```
python -I runner/e132_acquire.py    # PSA SDG regional daily basic pay and unemployment, 2021+
python -I runner/e132_run.py        # all models, both issue policies, N1-N7, oracle, SWS-vs-OCTA, ablation (~2 min)
python -I runner/e132_seal.py       # write-once prospective seal (already written)
```

**Requires** the E131 outputs and data. Tests: `backend/tests/unit/test_e132_final.py`.

## Files

| Kind | Files |
|---|---|
| Report | `E132_FINAL_RESEARCH_PACKAGE.md` |
| Protocol | `E132_FROZEN_PROTOCOL.md` |
| Logs | `DEVIATIONS.md`, `CONTAMINATION_LOG.md` |

**Machine outputs** (`out/`):

| File | Contents |
|---|---|
| `e132_predictions.csv` | Predictions |
| `e132_metrics.csv` | Metrics |
| `e132_rules.json` | N1–N7 |
| `e132_univariate_and_oracle.csv` | Univariate set and oracle |
| `e132_ablation.csv` | Ablation |
| `d2_sws_vs_octa.*` | SWS against OCTA |
| `area_income_features.csv`, `area_rice_affordability.csv` | New features |

**Seals** (`sealed/`): `E132_PROSPECTIVE_SEAL.csv` and `E132_PROVINCIAL_MODEL_BASED_SEAL.csv`, with hashes in `E132_SEAL_SHA256.txt`.

**Scoring** uses the primary criterion only, with `python -I runner/score_e132.py`. It reads the same new-rounds file as E131: `E131_Objectives_Resolution/data/sws_rounds_after_2026Q3.csv`.
