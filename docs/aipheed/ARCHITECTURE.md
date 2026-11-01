# Architecture

**Data flow:** `AUDIT.md` §2. **Methodology:** `METHODOLOGY.md`.

## Components

| Layer | Location | Responsibility |
|---|---|---|
| API | `backend/app/main.py`, `app/api/router.py`, `app/api/v1/*.py` | FastAPI app. Strict-model check at startup. CORS. 106 routes (`API.md`). |
| Served dashboard model | `app/ml/inference/ch1_system.py`, `thesis_system.py`, `app/services/dashboard.py`, `data/ch1_engine/` | P0H4 Chapter I risk probability in thesis mode (unchanged) |
| Legacy inference | `app/ml/inference/*` | Older engines behind environment switches; pickles load only through `app/forecasting/safe_load.py` |
| News / NLP | `app/news/*`, `app/ml/nlp/*`, `data/news_e31/` | Collection, relevance, XLM-R scoring (versioned), FSSI |
| Quarterly cycle | `app/quarterly/*`, `app/tasks/scheduler.py` | Dashboard clock (`target.py`), forecast period, staged updates (no auto-publish) |
| **Forecasting core (new)** | `app/forecasting/` | `as_of`, validation, SWS target, models, artifact, inference, explain, geography, store (`METHODOLOGY.md`) |
| Research | `aipheed-backend-aligned/experiments/E1xx_*` | Frozen protocols, runners, seals (read-only from the backend) |
| Documentation | `docs/aipheed/` | Protocol lock, audit, inventory, model report, API, tests, final report |

## Forecasting core

**Dependencies run one way:** `evidence` ← `as_of` ← `validation` ← `sws` ← `models` ← `artifact` ← `inference` ← `explain` / `geography` / `store` ← `api/v1/hunger_forecast`.

**Design rules:**
- **No pickle.** Artifacts are canonical JSON with a SHA-256.
- **Write-once.** Neither artifacts nor stored forecasts may be overwritten. Re-saving identical content is a no-op; different content raises.
- **One cache key:** (artifact hash, data vintage, issue date), which is the store file name. Nothing else is cached.
- **Fail loudly.** Typed errors are `LeakageError`, `ValidationError`, `ArtifactError` and `InferenceError`. The API maps them to 404, 422 or 503; there is no fallback model.
- **Paths are resolved from `__file__`.** The core does not depend on the cwd (AUDIT D4).
- **The model is small.** Inference loads a JSON file of about 1 KB, so per-request model-load cost is negligible. No global model object is held.

## Security and performance (phase 10)

| Item | Status |
|---|---|
| Unsafe deserialization | **Fixed (D2):** hash-checked joblib loading, limited to `backend/models/` |
| Hard-coded secrets | `SECRET_KEY` default `changeme` is refused before signing (`security._assert_signable`). No secret in any API body (`API.md`). |
| Timeouts | All outbound `requests` calls in `app/ml/corpus` set `timeout` (grep) |
| Unhandled errors | **Fixed (D10):** a missing artifact gives 503, not 500 |
| Repeated loading | Served engines use `functools.lru_cache` keyed by path and mtime (`ch1_system._rows`). The new core reads one small JSON per request. |
| Unsafe paths | Artifact loader refuses paths outside `backend/models/` |
