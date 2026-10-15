# E25 test results (2026-10-14)

**Environment:** Python 3.13.2 (`backend/venv`), LightGBM 4.6.0, scikit-learn 1.8.0, SciPy 1.17.1, NumPy 2.4.4, pandas 2.3.3. Node via `dashboard_dev/node_modules`, a junction to `frontend/node_modules` used read-only (caches kept in `dashboard_dev/.vite-cache`).

## Summary

| Suite | Command | Result |
|---|---|---|
| Python (guard installed for every test) | `python -B -m pytest -q --noconftest -c tests/pytest.ini --rootdir tests tests/` | **38 passed**, 0 failed |
| Frontend unit and render tests (jsdom) | `npx vitest run` (in `dashboard_dev/`) | **18 passed** (5 files; 5 new E25 timeline tests) |
| Frontend build | `npx vite build --outDir dist-e25` | **Built.** Only a chunk-size warning. |
| TypeScript (new E25 files) | `npx tsc --noEmit -p tsconfig.app.json` | New files clean. **Pre-existing errors in `src/data/mockData.ts`**, inherited unchanged from `frontend/` (reported, R4). |
| Reproducibility (C8) | `python -B runner/reproduce.py 20261014T002026Z 20261014T002520Z MONTHLY_20261014T002535Z MONTHLY_20261014T002933Z` | **All 19 output files byte-identical.** Prediction seals identical; run code identical; monthly seal identical. |
| Seal integrity | `python -B runner/seal_e25.py --verify` | Recomputed SHA-256 = sealed `417ce60fd07106179f6ea84d109442b15b97f29a57191bb457f42ba5ebcce4d0`; a second seal is refused |
| Read-only experiments | `python -B runner/verify_readonly.py <snapshot>` | E17, E18, E23, E24, E24v2: **0 content differences** (`docs/READONLY_VERIFICATION.md`) |
| Pinned inputs | `guard.verify_allowlist()` (every run) | All 22 pins match |
| Quarterly pipeline, live 2027-Q1 cycle | `python -m scripts.quarterly_update run` (in `backend_dev/`) | INSUFFICIENT_DATA with the exact missing list; no forecast attached |

## Python tests by area

| Area (task section 7) | Tests | What they check |
|---|---|---|
| Data and labels | `test_D_is_mean_zero_per_quarter_and_S1_is_H_plus_2D`, `test_readings_label_counts` | D sums to 0 in every quarter. S1 = H + 2D reproduces E12's approved S1 exactly. Readings B/C add exactly 2025-Q2/Q3. |
| Window | `test_window_no_pre2021_and_no_post_2026Q2` | No row before 2021-Q1 or after 2026-Q2 / 2026-06 |
| Feature timing and leakage | `test_masking_removes_2020_information`, `test_features_use_quarter_t_news_and_t_minus_1_government`, `test_label_publication_rule_and_training_pairs`, `test_2026_rounds_unusable_at_every_backtest_origin`, `test_dnow_available_before_origin_and_matches_quarter` | The 2020-carrying cells are masked. Government features are from quarter t−1. Every training label is published before its origin. No backtest origin uses a 2026 round. |
| Chronological splits | `test_chronological_folds`, `test_identical_rows_across_models_in_R_A` | target = t + lead; origin = first day of t+1; ≥ 8 training quarters; every model on identical rows |
| Cutoff and authorization | `test_guard_denies_unlisted_project_data_and_other_experiments`, `test_guard_rejects_hash_mismatch`, `test_production_sws_is_read_only_with_its_2026H1_filter`, `test_seal_refuses_to_seal_twice`, `test_score_sealed_refuses_without_authorization`, `test_score_sealed_refuses_wrong_hash_and_unlisted_quarters`, `test_score_sealed_scores_complete_synthetic_outcomes` | Unauthorized reads raise. Hash mismatches raise. Seals are written once. Sealed forecasts are never scored without researcher-authorized outcomes. A file holding an unlisted quarter is refused, not filtered. Incomplete outcomes are never partially scored. |
| Missing and stale data | `test_requirement_status` (4 cases), `test_insufficient_record_never_carries_a_forecast`, `test_live_2027Q1_record_lists_missing_inputs` | STALE, UNAUTHORIZED, NOT_AVAILABLE_BY_CUTOFF and OK are classified correctly. A record that is not ready never carries a forecast. |
| Ranking determinism | `test_ranking_deterministic_and_labels_substitutes` | 142 unique LGUs; identical ranks under shuffled input; 126 substitutes labelled; within-province order independent of the province probability |
| API / dashboard / PDF | `test_api_dashboard_pdf_read_one_record`, `test_api_refuses_a_tampered_record` | The API returns the record that the dashboard file holds byte for byte. The PDF carries its hash, status and probabilities. A tampered record returns 500. |
| Quarterly transition (**synthetic fixtures only**) | `test_quarterly_transition_with_synthetic_complete_inputs` | INSUFFICIENT_DATA before the cutoff; READY after it; `indicative_only` on every block; 142 LGUs; history kept; advance to 2027-Q2 |
| Engine fixes | `test_engine_never_uses_pre2021_D_pairs`, `test_unverified_round_usable_only_after_its_upper_bound` | F1, F2 and F3 |
| Statistics | `test_reachability_exact_p_is_two_to_minus_m` | The exact sign-flip best case is 2^-m |
| Reporting honesty | `test_no_criterion_reported_met_when_it_is_not`, `test_sealed_predictions_match_their_hash`, `test_reproduction_byte_identical` | The T1 goal is not reported as met; C9 is NOT ASSESSABLE |
| Participant scorer (synthetic responses inside the test only) | `test_score_responses.py` (5) | Decision rules, exclusions, Forms-export check |

## Frontend tests (`dashboard_dev/src/test/e25Timeline.test.tsx`, on the real record)

- Nine quarters, 2025-Q1 to 2027-Q1, in order.
- 2027-Q1 cells show MISSING INPUTS and "not a low-risk state". There is no probability and no "LOW", and every missing input is listed.
- 2026-Q3 and 2026-Q4 cells show "outcome pending".
- 2025-Q2 and 2025-Q3 cells have their own NO LABEL state.
- Every displayed probability equals the record's. "Indicative only" appears in every back-test cell. The constructed-composite statement and the record hash are shown.

## Not done

- **No browser screenshot.** The page was rendered in jsdom tests only.
- No load or security testing.
- **Production `frontend/` and `backend/` were not run or changed.**
