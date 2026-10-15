# E25: reliable, useful and accurate forecasts (2021–2026 data only)

**Start here: `FINAL_REPORT.md`.** Then read `ADVISER_AND_AUTHORIZATION_CHECKLIST.md` (one page).

## Result in four lines

1. On the approved label, the forecasting goal is **not met**. FINAL_T1 (PCF21) ties persistence on accuracy (0.875) and beats it on Brier only with leads pooled and before multiplicity adjustment (p = 0.027; Holm 0.082). Always-HIGH (no data) is best on these high-hunger quarters.
2. Several criteria **cannot be met by any model** on this data (reachability analysis, run before any model). The proposed proper-scoring criteria await adviser approval and are not met either.
3. The exploratory provincial price-pressure target is forecast better than persistence at lead 1 (development evidence).
4. The 2027-Q1 forecast is **INSUFFICIENT_DATA**. Its missing inputs are listed in `AUTHORIZATION_REQUEST.md`. Forecasts for 2026-Q4 and 2027-Q1 are sealed for evaluation.

## Layout

| Path | Content |
|---|---|
| `FROZEN_EVALUATION_PROTOCOL.md`, `runner/PROTOCOL_SHA256.txt` | Rules, frozen before any model was fitted |
| `IDEA_LOG.md` | 19 ideas: power, results, decisions |
| `runner/` | `guard.py` (data access), `e25lib.py`, `run_e25.py`, `score_e25.py`, `monthly_d_eval.py`, `seal_e25.py`, `score_sealed.py`, `lgu_rankings.py`, `completeness.py`, `build_outputs.py`, `export_pipeline_inputs.py`, `reachability.py`, `power_sim.py`, `verify_readonly.py`, `materialize_inputs.py`, `reproduce.py` |
| `runs/` | Primary and repeat runs, monthly runs, `SEAL_E25_*`, reachability, power, verification, reproducibility |
| `inputs/` | Byte-identical, hash-pinned copies of authorized inputs that exist only in commit 5113ae5, plus the E24/E24v2 seals |
| `backend_dev/` | Isolated pipeline copy (fixes F1–F5), API `/api/v1/quarterly/e25-timeline` |
| `dashboard_dev/` | Isolated dashboard copy, page `/forecast-timeline`, build `dist-e25/` |
| `instruments/` | DA Region IV-A evaluation instruments (H4/H5) |
| `tests/` | 38 Python tests (`pytest -c tests/pytest.ini`) |
| `docs/` | Reachability, power simulation, read-only verification, frozen idea log part 1, Chapter I source |
| `thesis_source/` | Chapter I verbatim extract (from E24, hash-verified) |
