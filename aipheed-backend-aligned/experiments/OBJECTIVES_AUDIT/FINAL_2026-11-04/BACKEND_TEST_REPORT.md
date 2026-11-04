# Backend test report

**Command:** `cd backend && python -m pytest -q tests`

| Run | Result | Note |
|---|---|---|
| Baseline (2026-11-04, before this task) | 1,017 passed, 18 skipped | — |
| After the `/api/v1/config` fix | **1,022 passed, 18 skipped**, 0 failed, 1 warning (Starlette `httpx` deprecation, pre-existing) | +5 = the new `test_foodinsecurity_config_metadata.py`. No existing test changed, failed or newly skipped |

## Targeted runs after each change

- **59 passed:** `test_foodinsecurity_config_metadata.py`, `test_foodinsecurity_mode.py`,
  `test_foodinsecurity_drivers.py`, `test_thesis_system.py`.
- `obj1_annotation_v2.py selftest` passed (random labels, temporary folder, nothing saved).

## Live API probe (C-E2 demo)

- `/api/v1/config`, `/api/v1/explainability` and the other public endpoints return 200.
- Invalid input returns 404 or 422.
- Admin endpoints return 401 without a token.
