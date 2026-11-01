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

---

## v2 additions (docs/aipheed/v2)

| Layer | Location | Responsibility |
|---|---|---|
| Base directory | `backend/app/paths.py` | `BACKEND_DIR` and `backend_path()`. All 144 `data/`, `models/` and `config/` literals in `app/` (50 modules) resolve against the backend directory, not the cwd (AUDIT D4). Tested from two working directories (`tests/unit/test_v2_paths.py`). |
| v2 forecasting | `backend/app/forecasting/v2/` | `models` (PERSIST / LL / LL-K), `select` (walk-forward, inner-fold rule, conformal), `verdict` (frozen N1–N7 via `e130_lib`, decision table), `artifact` (hashed JSON, write-once), `inference` (no refit), `explain` (exact decomposition), `store` (write-once `data/forecasting/forecasts_v2/`) |
| v2 API | `app/api/v1/hunger_forecast.py` (`/hunger-forecast/v2/*`) | Read-only, additive |
| v2 offline scripts | `backend/scripts/v2_{diagnosis,validate,seal,score_sealed,context,e2e,coverage,mutation_check}.py`, `reexport_thesis_model.py` | Evidence; every output is under `docs/aipheed/v2/results/` |
| Thesis model (D3) | `models/thesis_food_insecurity_model_skl180.joblib` | The same fitted objects re-exported under scikit-learn 1.8.0. Scores are identical on all 135 panel rows, and there is no version warning. The original file is kept. |

**Dependencies run one way:** `as_of` ← `sws` ← `v2.models` ← `v2.select` ← `v2.artifact` ← `v2.inference` ← `v2.explain` / `geography` / `v2.store` ← API. `v2.verdict` is offline only: it loads the frozen `e130_lib` read-only.
