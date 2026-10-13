# Synthetic Tests (E15)

**Code:** `tests/test_two_layer_synthetic.py`. All fixtures are synthetic (quarters 2030-Q1..Q4 with invented values), so **no project data is read by the tests.** The output is in `tests/pytest_output.txt`.

**Command:**

```
cd aipheed-backend-aligned/experiments/2026-10-13_E15_TwoLayer_Prototype
../../../backend/venv/Scripts/python.exe -B -m pytest -q -p no:cacheprovider tests
```

## 1. Required tests (from the brief)

| # | Requirement | Test | Result |
|---|---|---|---|
| 1 | D sums to zero for complete data | `test_D_sums_to_zero_for_complete_data`: \|ΣD\| < 1e-12 in every quarter; ranks are 1..5 | **Pass** |
| 2 | Missing inflation gives no D and no rank, and is never filled with 0 | `test_missing_inflation_gives_no_D_no_rank_and_no_zero_fill`: Quezon's F is missing in one quarter. Its F is null (not 0), the quarter's mean, every D and every rank are null, the status is `INCOMPLETE_NO_D_OR_RANK`, the legacy S1 is unavailable, and other quarters are unaffected. | **Pass** |
| 3 | The regional value appears once per quarter | `test_regional_value_appears_once_per_quarter`: `level_pct` occurs exactly once per quarter, no provincial record has a hunger or level field, and the regional CSV has one row per quarter | **Pass** |
| 4 | Ties are handled by a documented rule | `test_ties_follow_documented_rule`: two equal D values share rank 1, the next is rank 3, `tied_with` is correct, a 1e-12 difference ties while 1e-6 does not, and the list is alphabetical. `test_uniform_conditions_still_rank_but_all_tied`: identical F gives every province rank 1. | **Pass** |
| 5 | The legacy label reproduces S1 exactly (tolerance 1e-9) | `test_legacy_reproduces_S1_exactly_and_uses_strict_threshold`: S1 = H_A + 2D within 1e-9, the label uses a strict ">", and S1 exactly at τ0 is LOW. `test_legacy_needs_a_production_round`: with only supplementary rounds, the regional layer is shown but S1 is unavailable. | **Pass** |
| 6 | No output field uses "food insecure" or "risk" | `test_no_banned_wording_in_any_output_field`: every key and string in the JSON and the CSVs is checked. The checker flags "food insecure" and "risk_level", and accepts the mandated "not validated as food insecurity". | **Pass** |

## 2. Additional tests

| Test | Result |
|---|---|
| `test_regional_trend_uses_prior_eligible_quarter_and_records_gap`: a 2-round mean; a quarter with no round; a trend that skips a gap with `quarters_apart = 2` | **Pass** |
| `test_output_validates_against_schema`: complete and incomplete outputs validate against `TWO_LAYER_SCHEMA.json`; an output with an added `risk` field is rejected | **Pass** |
| `test_guard_decide` (12 cases): denies `psa_indicators`, `psa_subsistence`, `sws_hunger`, the 2026-H1 CPI file, the E10 sealed Q4 manifest, `~/.claude`, writes to E13 and to the frontend, and the non-allowlisted E13 `predictions.csv`; allows the allowlisted E12 and E13 reads and writes inside E15 | **Pass** |
| **Total** | **22 passed** |

## 3. Runtime checks on the eligible data (`runs/20261013T024905Z/runtime_checks.json`)

| Check | Result |
|---|---|
| Output validates against the schema | Yes |
| Banned wording in the JSON or CSVs | None |
| D against E12's D (max abs. difference) | 2.0e-15 |
| Legacy S1 against E12's S1 (max abs. difference); null pattern | 3.6e-15; identical (80 rows with S1, 20 without) |
| Thresholds 10.843, 10.8433333 and 10.84335 | Identical labels on all 80 rows (no S1 between 10.843 and 10.84335). HIGH 56/80. |
| Regional rows | 20, unique by quarter |
| Max \|ΣD\| per quarter | 4.4e-15 |
| Latest quarter loaded or output | 2025-Q4 (each loader asserts ≤ 2025-Q4) |
| Mock report wording check | None found |
