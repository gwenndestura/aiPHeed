# FINAL_OBJECTIVE_ACHIEVEMENT: the served LightGBM forecasting engine

**Protocol:** `FINAL_FORECASTING_PROTOCOL.md` (sha `d94f0c2c…`, frozen 2026-10-25T14:06Z, before scoring).

**What changed from FINAL**
- LightGBM learns the change from the latest SWS reading.
- Lead 0 is added (the quarter whose survey is not yet published).
- News comes from real-time GDELT documents.
- A flag marks the 2025 survey break.
- An asymmetric (surge-cost) variant is added.
- The accuracy ceiling is verified empirically.

**Results** (development evidence)
- ELEVATED accuracy at Leads 0–4: 0.61, 0.52, 0.50, 0.36, 0.56. The 75% target is not reached.
- No reliable lead.
- At Lead 0, level MAE is 3.47 vs 4.19 points for the latest reading (p = .025).
- News gives no gain: Holm p = 1; placebo p = 0.39.
- The validated ceiling is 0.64 one quarter ahead; same-quarter SWS rounds agree on the label 3 times in 8.

**Seal:** `out/sealed_prospective.csv` (`03534689…`). Score it with `runner/score_prospective.py`.

**Reproduce:** run from `runner/` with the backend venv:

```bash
python run_oa.py all
python export_engine.py
```

`run_oa.py all` runs the phases verify → data → audit → score → placebo → seal. `export_engine.py` writes `backend/data/final_engine/`.

**Where it is documented:** the system-level documents are in `docs/final_system/`. They replace the 10 deliverables first planned here, because the user's 2026-10-26 directive moved the work to system completion.

**Local data search:** `sources/LOCAL_DATA_SEARCH_LOG.md`.
