# AIPHEED backend audit (phase 1)

**Evidence tags:**
- **VERIFIED:** command run, output saved.
- **INFERRED:** read from code.
- **NOT VERIFIED.**

**Scope.**
- `backend/app` (185 Python modules), `backend/config`, `backend/data`, `backend/models`, `backend/tests`, `Dockerfile` and `render.yaml`.
- The audit was **risk-directed**: I traced the served path end to end and grep-scanned all modules for unsafe deserialization, secrets, network calls without timeouts, cwd-relative paths and silent exception handling. I did **not** read every one of the 185 modules line by line (stated limitation).

## 1. What is served (INFERRED from code and config; VERIFIED where marked)

- **Deployment** (`backend/Dockerfile`, `render.yaml`): `AIPHEED_LEAD2_MODEL=thesis`, `AIPHEED_STRICT_MODEL=1`; uvicorn serves `app.main:app` from `WORKDIR /app` (= `backend/`).
- **Strict mode** (`app/main.py: strict_model_check`): the API refuses to start unless the thesis system is active and its artifacts validate. This guarantees no silent fallback.
- **Map/province number** (`app/ml/inference/ch1_system.py`, `AIPHEED_MAP_MODEL` default `ch1`): the **P0H4 Chapter I risk probability**, read from the export `backend/data/ch1_engine/rows.csv`.
  - It is P(SWS Balance Luzon hunger > 11.3 %) × P(provincial food-price condition).
  - The price part comes from one LightGBM; the classes are HIGH/LOW at 0.50.
- **Served-model metrics reproduced from the export** (VERIFIED, `docs/aipheed/served_model_reproduction.txt`): Lead 1 has 70 observed province-quarters over 14 quarters, Brier 0.1322 and accuracy 0.8429. This equals `data/ch1_engine/evaluation.json` exactly.
  - The export holds Leads 2–4 only for the current issue (5 rows each, no outcomes), so the evaluation.json values for Leads 2+ **cannot be reproduced from served artifacts** (NOT VERIFIED here; they come from the FORECAST_RESEARCH experiments).
- **Candidates not served:**
  - **SEAS-LLM:** prospective primary, E134 Addendum 2.
  - **SIMPLE and HFM-X:** challengers.
  - **X-RED:** hypothesis.
  - **E-series routers** (`/api/v1/e107` … `/e113`, `/final`, `/lead2`, `/simple`, `/fpp`): read-only exported experiment files.

## 2. Data flow

```mermaid
flowchart LR
  subgraph Sources
    SWS[SWS hunger releases]
    PSA[PSA OpenSTAT: CPI, LFS, palay, poverty, FIES]
    CLIM[NOAA ONI, IBTrACS, NASA POWER]
    NEWS[News RSS / GDELT]
  end
  SWS --> EXP[experiments/* runners<br/>offline, frozen protocols]
  PSA --> FETCH[app/ml/corpus/*_fetcher.py] --> INP[backend/data/inputs, data/news_e31]
  CLIM --> EXP
  NEWS --> NLP[app/news + app/ml/nlp<br/>XLM-R / BERTopic / FSSI] --> INP
  INP --> EXP
  EXP -->|export| CH1[data/ch1_engine/rows.csv<br/>P0H4, served]
  EXP -->|seals| SEAL[experiments/*/sealed<br/>SEAS-LLM, SIMPLE, HFM-X]
  CH1 --> SVC[app/services/dashboard.py] --> API[/api/v1/dashboard, /report, .../] --> FE[frontend]
  INP --> CORE[app/forecasting (new)<br/>as_of → validation → SEAS-LLM artifact → inference → explain] --> API2[/api/v1/hunger-forecast (new, read-only)]
  MODELS[backend/models/*.joblib] -->|verified_joblib_load| SVC
```

## 3. Defects

| ID | Location | Severity | Finding | Status |
|---|---|---|---|---|
| D1 | `app/ml/inference/ch1_system.py`, `data/ch1_engine` | **High (research validity)** | The served number is a composite **classification probability** (SWS Balance Luzon hunger × provincial food-price condition). It is not a numerical food-insecurity forecast, and provinces differ only through prices, which the code's own caveat states. Price is a predictor, not ground truth. | **Logged, not changed.** Replacing the served model needs owner approval. The numerical SWS forecast path is built separately (phases 5–8). |
| D2 | `joblib.load` at 6 sites (`explainer.py`, `forecaster.py`, `predictor.py`, `thesis_explainer.py`, `thesis_predictor.py`, `services/report_data.py`) | **High (security)** | Pickles were loaded with no integrity check | **Fixed.** `app/forecasting/safe_load.py` loads only files inside `backend/models/` whose SHA-256 matches `models/MODEL_MANIFEST.json` (3 artifacts recorded; none modified). Tests: `tests/unit/test_safe_load.py` (VERIFIED). |
| D3 | `models/thesis_food_insecurity_model.joblib` | Medium (reproducibility) | Pickled with scikit-learn 1.7.2; `requirements.txt` pins 1.8.0. Unpickling emits `InconsistentVersionWarning`. | **Logged.** Rebuilding means overwriting an artifact, which needs owner approval. |
| D4 | 104 `Path("data/…")`, `Path("models/…")` and `Path("config/…")` literals in `app/` | Low | Resolved against the cwd. Correct under Docker (`WORKDIR /app`) and when run from `backend/`; wrong from any other cwd. | **Logged.** New code resolves from `__file__`. |
| D5 | Feature paths in `app/ml/features`, `app/quarterly`, `app/news` | Medium (leakage-prevention design) | No single point-in-time selector; each path applies its own cutoff. They are tested individually (E119, E131 leakage tests), but nothing enforces one rule. | **Partly fixed:** `app/forecasting/as_of.py` is the one selector for the new forecasting path, with injected-leak tests (phase 2). Legacy paths were not refactored (risk to the served system). |
| D6 | `app/api/router.py` | Low | 13 experiment-specific routers expose exported research files under `/api/v1`, so the API surface is large | **Logged** (phase 8 API audit) |
| D7 | `app/config.py` `SECRET_KEY="changeme"` | Info | The default is guarded: `security._assert_signable` raises `ServerMisconfigured` before signing (VERIFIED by reading code; covered by existing tests) | No change |
| D8 | `app/ml/corpus/*` network calls | Info | All 4 `requests.get/post` calls set a timeout (INFERRED, grep) | No change |
| D9 | `models/lgbm_best.pkl` referenced by `predictor.py` / `explainer.py` | Low | File absent; the code raises `FileNotFoundError` (loud). It is reached only on non-default paths (`AIPHEED_DATA_LAYER=legacy`): INFERRED, not executed. | Logged |
