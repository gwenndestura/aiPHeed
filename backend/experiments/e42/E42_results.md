# E42 — E36 plus the four other risk drivers (lead 1)

**Question.** Does keeping all 13 E36 inputs and adding Climate Stress, Fish Kill, Employment and OFW Remittance inputs keep or improve E36's one-quarter-ahead accuracy?

**Answer: PASS — `E42-abl-Employment` (E36 + national unemployment).** It is the only arm whose Brier is significantly lower than E36's. Adding all four drivers, or Climate or Fish Kill alone, made the model worse. See the verdict and caveats at the end.

Experiment only. Nothing is wired into the live system. Run `runs/20261015T151205Z`; predictions SHA-256 `881165d6…`; all numbers are in `E42_results.json`.

## Setup

**Procedure.** E36's own walk-forward code (`e36_lib.walk_forward`) runs unchanged:
- **Target:** S1 = H + 2D above the trailing-median τ.
- **Folds:** 13 test quarters, 2023-Q1 to 2026-Q3 (65 province-quarters: 53 HIGH, 12 LOW).
- **Training rows:** E36's rule.
- **Grid:** G1/G4/G3/G2, seed 36.
- **Nested rule:** the lowest mean per-date Brier on eligible prior dates; a tie within 0.002 goes to the simpler setting.
- **Threshold and baselines:** threshold 0.5 and the six baselines.

E42 arms are added as extra pools in memory only. No E36 file was changed.

**Reproduction.** All 28 arms E36 stored (1,805 rows) reproduce:
- **Predictions:** the largest probability difference is 5×10⁻¹¹.
- **Labels and choices:** labels are identical, and E36 picks the same configuration at every test quarter.
- **Q4 2026:** the forecast equals the served record (Cavite 0.983, Laguna 0.9886, Quezon 0.9862, Rizal 0.9807, Batangas 0.169).

**Builders reused.** `e36_lib` (features, grid, nested rule, baselines), `e37_lib` (lead-k training rows), `e38_lib` (news trigger shares from `app/ml/nlp/trigger_classifier.py`) and `e28_metrics` (metrics and date-cluster bootstrap). The E39–E41 builders were removed in the revert to bf94bb3, so the driver features were rebuilt in `runner/e42_lib.py` from `backend/data/processed` (read only).

### Driver features (8; at most 2 per driver; E36 timing rule)

At origin O(t) (the first day of quarter t+1), a series contributes its value for quarter t−1 and news contributes the titles published in quarter t.

| Driver | Feature | Source | Level |
|---|---|---|---|
| Climate Stress | `rain_absanom_l1`: absolute rainfall anomaly (% vs 1991–2020 normal), t−1 | NASA POWER | province |
| | `tc_max_l1`: strongest tropical-cyclone signal within 300 km, t−1 | NOAA IBTrACS | province |
| Fish Kill | `fish_chg_l1`: **proxy**, total fisheries production year-on-year log change, t−1 | PSA | province |
| | `trig_fish_kill`: share of the province's news titles classified as fish kill, quarter t | E31 news store | province |
| Employment | `u_nat_l1`: national unemployment rate, t−1 (observed through 2025-Q4, then carried forward) | PSA LFS | national |
| | `u_stale`: 1 when `u_nat_l1` is carried forward | — | national |
| OFW Remittance | `remit_l1`: national OFW cash remittances year-on-year growth, t−1 (observed through 2025-Q4, then carried forward) | BSP | national |
| | `remit_stale`: 1 when `remit_l1` is carried forward | — | national |

### Leakage check
- **Result:** every lagged value in all 670 training and test rows comes from a data quarter between 2021-Q1 and t−1. No problems were found.
- **Carried-forward values:** 10 test rows for unemployment and 10 for remittances (targets 2026-Q3 and 2026-Q4, all five provinces). No training row is stale, so the `*_stale` flags are always 0 in training and the model cannot learn from them.
- **Assumption 1, publication timing:** PSA fisheries production for quarter t−1 is assumed to be published before the origin. The release dates are not verified (the same assumption as the risk-indicator layer).
- **Assumption 2, rainfall service:** the 2026 rainfall comes from NASA POWER's daily service, while 2021–2025 comes from the monthly service. Their comparability is not verified; 10 test rows use 2026 rainfall.

## Results (65 test rows, 13 quarters)

| Arm | New features | Accuracy (95% CI) | Brier | Log loss | AUC | Brier diff vs E36 (95% CI) | McNemar p | Pass? |
|---|---|---|---|---|---|---|---|---|
| **E36-repro** (E36 nested) | 0 | 0.815 (0.738–0.892) | 0.154 | 0.508 | 0.850 | — | — | reference |
| E42-fixed (COMB+8, G2) | 8 | 0.785 (0.646–0.908) | 0.202 | 0.986 | 0.825 | +0.048 (−0.038, +0.150) | 0.754 | no (acc) |
| E42-nested | 8 | 0.692 (0.569–0.815) | 0.189 | 0.562 | 0.836 | +0.035 (+0.003, +0.071) | 0.008 | no |
| E36 + Climate | 2 | 0.754 (0.646–0.862) | 0.179 | 0.727 | 0.798 | +0.025 (−0.010, +0.069) | 0.125 | no (acc) |
| E36 + Fish Kill | 2 | 0.708 (0.600–0.831) | 0.176 | 0.528 | 0.854 | +0.022 (+0.003, +0.043) | 0.016 | no |
| **E36 + Employment** | 2 | **0.846 (0.769–0.923)** | **0.139** | 0.492 | 0.855 | **−0.015 (−0.029, −0.004)** | 0.500 | **PASS** |
| E36 + OFW | 2 | 0.846 (0.769–0.923) | 0.150 | 0.469 | 0.873 | −0.005 (−0.012, +0.001) | 0.500 | PASS |
| *E36 COMB×G2 fixed (diagnostic)* | 0 | 0.862 (0.800–0.923) | 0.132 | 0.721 | 0.881 | −0.022 (−0.064, +0.013) | 0.375 | not an E42 arm |
| B1 persistence | – | 0.877 | 0.123 | 1.700 | 0.860 | | | baseline |
| B2 LR combined | – | 0.862 | 0.120 | 0.531 | 0.840 | | | baseline |
| B3 LR government | – | 0.846 | 0.102 | 0.420 | 0.866 | | | baseline |
| B4 LR news | – | 0.708 | 0.198 | 0.581 | 0.658 | | | baseline |
| B5 LightGBM government | – | 0.846 | 0.145 | 0.452 | 0.870 | | | baseline |
| B6 LightGBM news | – | 0.677 | 0.195 | 0.576 | 0.736 | | | baseline |
| always-HIGH | – | 0.815 | 0.185 | 2.551 | 0.500 | | | diagnostic |

- **Brier difference:** arm minus E36, averaged per date; negative favours the arm. The 95% CI is a paired date-cluster bootstrap (2,000 resamples, seed 20261014).
- **McNemar:** exact test on the 65 paired classifications.
- **Accuracy CI:** the E36 date bootstrap.

**Adoption rule (fixed before the results).** An arm passes if (a) its Brier-difference CI includes 0 or favours the arm, (b) its accuracy is at least 0.815 − 0.01, and (c) no leakage is found. Passing arms are `E42-abl-Employment` (Brier 0.139) and `E42-abl-OFW` (0.150); the lower Brier selects **E36 + Employment**.

## Q4 2026 (origin 2026-10-01, lead 1)

| Model (chosen setting) | Batangas | Cavite | Laguna | Quezon | Rizal | **CALABARZON** |
|---|---|---|---|---|---|---|
| E36 (COMB × G2) = served | 0.169 | 0.983 | 0.989 | 0.986 | 0.981 | **0.822** |
| E36 + Employment (COMB_EMP × G2) | 0.067 | 0.988 | 0.983 | 0.989 | 0.988 | **0.803** |

**SHAP shares for CALABARZON at Q4 2026** (sum of |SHAP| per group over the five provinces ÷ total; each row adds to 100%):

| Model | Market | Climate | Fish Kill | Employment | OFW | Other (hunger, y_last, news, FSSI) |
|---|---|---|---|---|---|---|
| E36 | 38.7% | 0% | 0% | 0% | 0% | 61.3% |
| E36 + Employment | 36.2% | 0% | 0% | 9.9% ⚠ | 0% | 53.9% |

⚠ At Q4 2026 the unemployment input is the carried-forward 2025-Q4 value (4.97%), not an observed 2026-Q3 value.

**Mean |SHAP| per driver over the evaluation set** (log-odds, per row, 65 rows; share of the total in brackets). E36 + Employment carries only the Employment driver, so the two 8-feature arms are shown as well:

| Model | Market | Climate | Fish Kill | Employment | OFW | Other |
|---|---|---|---|---|---|---|
| E36 | 1.732 (50.1%) | — | — | — | — | 1.726 (49.9%) |
| E36 + Employment | 1.899 (50.0%) | — | — | 0.464 (12.2%) | — | 1.439 (37.9%) |
| E42-fixed (all 8) | 3.280 (45.5%) | 0.579 (8.0%) | 0.877 (12.2%) | 0.710 (9.8%) | 0.297 (4.1%) | 1.473 (20.4%) |
| E42-nested (all 8) | 1.464 (59.3%) | 0.153 (6.2%) | 0.200 (8.1%) | 0.121 (4.9%) | 0.021 (0.8%) | 0.508 (20.6%) |

In the 8-feature models every driver is split on and receives SHAP, but those models are worse than E36 (Brier +0.035 to +0.048). The drivers are used, but they mostly add noise.

## Caveats
- **National series.** The passing input is the same value for all five provinces, so it can only move every province up or down together. With 13 test quarters, a national trend can line up with the outcome by chance.
- **Multiple tries.** Six E42 arms were tested and the rule does not correct for multiplicity. The Employment CI excludes 0 only narrowly (upper bound −0.004), and the McNemar test shows no significant accuracy difference (2 vs 0 discordant rows, p = 0.5).
- **Hyperparameter comparison.** E36 run with its served setting fixed at every date (no drivers, diagnostic) scores Brier 0.132, lower than E36 + Employment. That setting was chosen with hindsight, so it is not an adoptable arm, but the Employment gain (−0.015) is of the same size as this selection noise.
- **Not fresh data.** These test quarters have been examined since E25. This is development evidence, not validation.
- **Stale input.** At Q4 2026 the Employment input is carried forward. A prospective check needs observed 2026 unemployment.

## Verdict
**PASS — `E42-abl-Employment` (E36's 13 inputs + national unemployment of t−1 and its stale flag)**, under the rule fixed beforehand. Its Brier fell from 0.154 to 0.139 (difference −0.015, 95% CI −0.029 to −0.004), and accuracy rose from 0.815 to 0.846 (McNemar p = 0.5), with no leakage found. Adding all four drivers, or Climate or Fish Kill alone, made E36 worse, and OFW alone was neutral. The gain is small: it comes from one national series, which is carried forward at Q4 2026, and it is one of six arms tried on quarters already examined many times. It should therefore be confirmed on a new quarter, with observed 2026 unemployment, before it replaces E36.
