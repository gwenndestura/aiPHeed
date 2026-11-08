# Test report (phase 9)

**Command:** `cd backend && python -m pytest -q -p no:cacheprovider -rfs`

## Results

| Run | Executed | Passed | Failed | Skipped | Evidence |
|---|---|---|---|---|---|
| Baseline (start, `2d9a2d9`) | 1276 | 1258 | 0 | 18 | `baseline_tests.txt` (VERIFIED) |
| After phase 1 edits, uncommitted | 1283 | 1263 | **2** | 18 | `phase1_tests.txt` (VERIFIED) |
| Final (after all phases) | 1298 | **1280** | **0** | 18 | `final_tests.txt` (VERIFIED) |

**The 2 failures after phase 1:**
- `tests/integration/test_e119r2_framework.py::test_all_validation_checks_pass`
- `tests/integration/test_e120_firi_design.py::test_e120_checks_pass`

Both experiment self-checks require `git status --porcelain -- backend/app …` to be empty. **Classification: intended change.** The edits were uncommitted when the suite ran. After commit they pass (final run). No test was deleted or weakened.

**The 18 skips** are all pre-existing and skipped by design: `E34 superseded by the E31 promotion` in `test_api_dashboard.py`, `test_api_report.py`, `test_plain_report.py` and `test_report_data.py`. They were not changed.

## New tests (22)

| File | Tests | Covers |
|---|---|---|
| `tests/unit/test_protocol_lock.py` | 4 | Lock hash; every locked source excerpt; an injected edit is detected; frozen numbers in code (1.645, N1 = 10 quarters / 40 rows, N2 = 0.75) |
| `tests/unit/test_safe_load.py` | 3 | Manifest hashes; a path outside `models/` is refused; unrecorded and tampered pickles are refused |
| `tests/unit/test_forecasting_core.py` | 15 | See below |

**`test_forecasting_core.py` covers:**
- **Leakage** (2 tests that **fail when a leak is injected**; `leak_injection_demo.txt`), plus the guard and missing-date tests.
- **Validation:** 6 injected problems are detected; the LGU code/province mismatch is detected.
- **Exact equality** with the E131 target and the E132 SEAS-LLM (seal and walk-forward).
- **Artifacts:** tampered and config-mismatched files are refused.
- **Inference failures:** not a quarter start; issue before the cutoff.
- **Records:** complete and reproducible; inference never refits; the stored forecast equals a fresh run.
- **Geography:** 142 LGUs, explicit status, province codes equal the served codes.
- **API:** 200 / 404 / 405 / 422, additive explanation, context-only groups.
- **Reliability status** pinned to the mechanical verdict.
- **Missing legacy artifact** gives 503, not 500.

## Integration and end-to-end

- **E2E:** `python -I backend/scripts/e2e_hunger_forecast.py 2026-10-01` (VERIFIED, `results/e2e_run.json`). It runs source → validate → as_of → artifact build → load → Leads 1–4 → explanations → geography → store → API.
  - It ran twice in fresh temporary stores.
  - Stored JSON and all 3 API bodies are byte-identical; the tolerance is exact.
  - The rebuilt artifact hash equals the committed artifact (`09ee23b0…`).
- **API smoke test:** `python -I backend/scripts/api_audit.py` (VERIFIED, `results/api_audit.csv`): 85 GET routes, no unhandled 500.

## Coverage

**Not measured.** Neither `coverage` nor `pytest-cov` is installed in the backend virtual environment or listed in `requirements*.txt`. I did not install it, to avoid changing the shared environment.

**To measure:**
```
pip install coverage
python -m coverage run -m pytest -q
python -m coverage report
```
