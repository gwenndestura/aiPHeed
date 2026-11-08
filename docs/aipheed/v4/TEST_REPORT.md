# v4 Test report

## 1. Full suite

**Command:** `cd backend && python -m pytest -q -p no:cacheprovider -rfs` → `v4/results/final_tests_v4.txt` (VERIFIED).

| Run | Passed | Failed | Skipped |
|---|---|---|---|
| End of v2 | 1317 | 0 | 18 |
| **v4 final** | **1331** | **0** | **18** |

- **New tests:** 14 (12 in `test_v4_core.py`, 2 in `test_v4_preregistration.py`).
- **Skips:** the 18 pre-existing `E34 superseded` skips, unchanged.
- **Integrity:** no test was deleted, skipped or weakened.

## 2. New v4 tests

| Test | Covers |
|---|---|
| `test_tiers_snapshots_and_seal_unchanged` | SHA-256 of the TRAIN and DEVTEST tier files, the feature snapshots and the v4 seal |
| `test_tiers_are_disjoint_and_devtest_is_the_frozen_su_set` | Disjoint tiers; DEVTEST = 44 / 40 / 36 / 32 rows; the seal holds only unpublished targets |
| `test_snapshot_used_at_another_issue_raises` | Feature leak guard (`LeakageError`) |
| `test_injected_round_on_or_after_issue_does_not_change_v4_forecast` | Target leak guard, through the DELTA path |
| `test_stability_rule_admits_stable_and_rejects_flipping_or_short` | Stability rule (sign flip, < 6 issues); exact contributions; missing value → 0 |
| `test_claim_75_and_beats_all_mechanics` | CONFIRMED / REJECTED / NOT_YET_TESTABLE / DEVELOPMENT_ONLY; Holm; identical forecasts never "beat"; block bootstrap |
| `test_development_verdict_file_is_development_only_and_sealed_not_testable` | Verdict file labels; served model = artifact model |
| `test_artifact_tamper_refused_and_rebuild_reproduces` | Edits to parameters, model or claims are refused; the rebuild reproduces the hash |
| `test_inference_never_refits_and_matches_store` | `fit` patched to raise; store = fresh inference; exact explanations; amended status is PROPOSED_NOT_ADOPTED |
| `test_delta_x_path_end_to_end` | A forced DELTA-X artifact: inference and an exact five-group decomposition |
| `test_v4_geography_142_lgus` | 142 LGUs, 5 provinces, `null` estimates |
| `test_v4_api` | 200 / 404 / 405 / 422; all five groups OBSERVED |
| `test_v4_preregistration` (2) | Pre-registration hash frozen; an edit is detected |

## 3. Coverage, E2E, hashes

- **Coverage** (`cd backend && python -I scripts/v2_coverage.py v4`; standard-library tracer, as in v2):
  - **89.4 %** (1313 / 1469) of `app/forecasting/**`, the hunger-forecast router and `app/paths.py`;
  - **v4 package 91.5 %** (368 / 402).

  Per file: `v4/results/coverage.txt` (VERIFIED).
- **E2E** (`python -I backend/scripts/v4_e2e.py`):
  - 2 script runs × 2 internal runs, outputs byte-identical (`cmp`);
  - artifact hash = committed; store = committed; API = inference; seal reproduced;
  - 142 LGUs; decomposition error ≤ 1e-3 (VERIFIED, `v4/results/v4_e2e_run.json`).
- **Hashes at the end** (`v4/results/v4_hashes_end.txt`, 10 passed), all unchanged:
  - `PROTOCOL_LOCK.md` `8bae6962…dd0d3`;
  - v2 pre-registration;
  - v4 pre-registration `eaff4f63…3d22`;
  - tiers and snapshots;
  - v2 and v4 seals.
