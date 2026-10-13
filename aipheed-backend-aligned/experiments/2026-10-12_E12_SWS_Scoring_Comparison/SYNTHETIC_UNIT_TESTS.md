# Synthetic Unit Tests (E12)

**What was run:**

- Code: `tests/test_e12_formula_synthetic.py`, using the functions in `runner/e12_lib.py`.
- Guard: E12, installed by `tests/conftest.py`. **No project data was read.**
- Output: `synthetic_test_output.txt`.

**Fixture:** one quarter; common H = 18.0; five provinces with F = 2.0, 5.5, 3.1, 8.4, 1.0. A second variant sets province 3's F to missing.

| # | Requirement | Test | Result |
|---|---|---|---|
| 1 | Deviations sum to zero | `test_1_deviations_sum_to_zero` | PASSED |
| 2 | Changing α does not change rankings (all α in the grid) | `test_2_alpha_does_not_change_rankings` | PASSED |
| 3 | Changing α does not change spread | `test_3_alpha_does_not_change_spread` | PASSED |
| 4 | Scaling β scales spread by β and preserves ranking | `test_4_beta_scales_spread_preserves_ranking` | PASSED |
| 5 | Equal α/β ratios give identical rankings and identical classifications under (β/2)·τ; the S1 group has 5 members | `test_5_equal_ratios_equivalent_rankings_and_classifications` | PASSED |
| 6 | Missing data are not replaced with zero (scores stay NaN) | `test_6_missing_not_replaced_with_zero` | PASSED |
| 7 | The five-province mean is not computed when a province is missing | `test_7_mean_not_computed_when_a_province_is_missing` | PASSED |
| + | Option B: wH = 0 has D's ranking; wH = 1 has zero spread; zero-variance flag works | `test_option_b_training_stats_zero_variance_and_equivalences` | PASSED |
| + | Option C = Option A with α = 0 | `test_option_c_is_option_a_alpha_zero` | PASSED |

**Result: 9 passed, 0 failed.**

No existing project test was run.
