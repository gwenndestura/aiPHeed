# aiPHeed release verification report (2026-11-03)

Branch `pfi/survey-anchored-final`. Checkpoint of earlier uncommitted work: `ff340a49`.

## 1. Production decision

**No model is promoted. The dashboard shows no new model and no new forecast.**

- Candidate `pfi-1.0` was evaluated by the release gate and **REJECTED** (9 of 16 checks not passed). Promotion was
  attempted and refused by the code (`PermissionError`).
- The public route `/api/v1/final/food-insecurity/outlook` answers **503 `validation_pending`** and names the failed checks.
- The dashboard is unchanged from the checkpoint. An earlier step of this session had put PFI on the provincial card
  and on `/api/v1/final/food-insecurity/*`. Both were reverted before the gate existed (frontend diff against `ff340a49` is empty).

## 2. Gate result for pfi-1.0 (`backend/data/registry/gate_results/pfi-1.0.json`)

| Check | Status | Evidence |
|---|---|---|
| B1 training completed, artifact hash verified | pass | `data/pfi/model/pfi_model.json` |
| B2 five groups and twelve families in the model | **fail** | uses V1 and H1 only; A1–A3, C1–C4, E1–E2, N1 absent |
| B3 improved N1 in the predictive pipeline | **fail** | no N1 |
| B4 data and release-date audits | pass | 3 release tests pass; survey release dates approximate |
| B5 leakage checks | pass | LOO isolation and as-of tests pass |
| B6 chronological evaluation on the target | **not evaluable** | no chronological FIES series for provinces (CALABARZON 2023 and 2025 only) |
| B7 independent validation where data permit | pass | 17-region leave-one-out: accuracy 17/17 (CI 0.82–1.00), regional level only |
| B8 beats the best simple baseline on the target | **not evaluable** | needs B6 data |
| B9 accuracy and class metrics on the target | **not evaluable** | needs B6 data |
| B10 calibration and uncertainty | **fail** | 95% interval covered 0.88; calibration error 0.18 (limit 0.10) |
| B11 geographic generalization at province level | **not evaluable** | no province has a FIES measurement |
| B12 forecast horizon justified | **not evaluable** | no lead validated on the target |
| B13 five-group ablation | **fail** | climate and news not testable for the level model |
| B14 automated tests | pass | `tests/unit/test_pfi.py` |
| B15 model card and methodology | pass | `docs/pfi/METHODOLOGY.md` |
| A1 valid food-insecurity target | pass | FIES moderate-or-severe |

## 3. Why no candidate can pass today

Checks B6, B8, B9, B11 and B12 need a repeated, measured food-insecurity outcome at the served resolution. The public
record contains:
- FIES for 17 regions in 2023 only;
- national FIES for 2019, 2021 and 2023;
- a provisional CALABARZON value for 2025;
- HFIAS by province for 2015 only.

Five provinces measured once (2015, a different instrument) cannot support chronological or leave-one-province-out
evaluation. More features cannot change these five checks:
- adding all five groups (B2, B13);
- an improved N1 (B3);
- a different learner.

The comparable published systems (registers 9–11) learn against repeated survey or IPC outcomes. CALABARZON has none
at province level.

**What would make the gate evaluable** (public data, no requests sent): FNRI ENNS 2018/2019/2021 and NNS 2023
household public-use files. The FNRI site blocks this network, so the owner must download them from another network
into `backend/data/fi_labels/raw/fnri/puf/`. With those files, provincial FIES can be estimated for four waves, which is
the minimum for a chronological test. The other route is PSA's 2026 FIES (expected 2027).

## 4. What was built and verified

| Component | Status | Evidence |
|---|---|---|
| Model registry (statuses, artifact hashes, history, production pointer) | IMPLEMENTED AND VERIFIED | `app/registry/__init__.py`; `test_registry.py` |
| Release gate (16 checks, frozen thresholds with digest, runs the candidate's tests) | IMPLEMENTED AND VERIFIED | `app/registry/gate.py`; `test_registry.py`; live run on pfi-1.0 |
| Promotion refuses failed or changed artifacts; approval written only on success | IMPLEMENTED AND VERIFIED | live refusal; tests |
| Production route serves only the approved model (no latest-artifact selection) | IMPLEMENTED AND VERIFIED | live 503; `test_pfi.py::test_candidate_is_not_public` |
| Candidate routes isolated behind admin login | IMPLEMENTED AND VERIFIED | live 401; test with admin override |
| PFI v1.0 candidate (FIES, small-area composite, SWS bridge, next-quarter clock, register) | IMPLEMENTED, REJECTED BY GATE | `docs/pfi/METHODOLOGY.md` |
| Research evidence register (9 DOIs checked against Crossref) | IMPLEMENTED | `RESEARCH_EVIDENCE_REGISTER.md` |
| Unified model with all five groups and twelve families | NOT IMPLEMENTED | would not change B6/B8/B9/B11/B12 (section 3) |
| Improved N1 (event extraction, geo-attribution, credibility, deduplication) | NOT IMPLEMENTED | same |
| Dashboard display of an approved model | NOT APPLICABLE | no approved model |

Registered models (`/api/v1/final/model-registry`):
- `ch1-p0h4`: **legacy_incumbent**. It is the engine behind the current map and left panel. It was never evaluated by
  this gate, and its own metadata says it is a price-pressure risk index, not a food-insecurity measurement.
- `pfi-1.0`: **rejected**.

## 5. Tests executed (2026-11-03)

| Suite | Command | Result |
|---|---|---|
| Registry and PFI | `python -m pytest tests/unit/test_registry.py tests/unit/test_pfi.py` | 31 passed |
| Backend unit suite | `python -m pytest tests/unit` | 787 passed (4 min 7 s) |
| Frontend | `npx tsc --noEmit` and `npx vitest run` | typecheck clean; 83 passed (17 files) |
| Live API | curl against `uvicorn app.main:app` | FI outlook 503 validation_pending; candidate 401; overview, fi9, fi10, lgus 200 |

## 6. Open decisions for the owner

1. The dashboard still shows, from earlier sessions, the CH1 price-pressure map and left panel, plus two cards:
   - the FI9 regional hunger card (provisional; it states that it misses too many HIGH quarters);
   - the FI10 provincial food-inflation card (provisional).

   None of them has passed this gate. Under the directive's absolute rule they are unqualified forecasts. Removing them
   changes the approved dashboard, so the owner decides.
2. Download the FNRI public-use files (section 3) so that a candidate can be evaluated at all.

## 7. Operation, deployment and rollback

- Register or refresh models: `python -m app.registry.catalog`.
- Evaluate: `python -m app.registry.gate evaluate <model_id>`. Promote: `python -m app.registry.gate promote <model_id> --approver "<name>"`. Status: `python -m app.registry.gate status`.
- Deployment: the registry files live in `backend/data/registry/` and ship with the Docker image. No environment variable
  can select a model for the food-insecurity route.
- Rollback: restore the previous `registry.json` (its history lists every event). An approved artifact whose file
  changes is refused automatically.
