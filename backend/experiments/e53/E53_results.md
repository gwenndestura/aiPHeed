# E53: retraining with measured driver conditions (cond_*), lead 1

Experiment only. The live system (E49), `backend/data/`, `backend/app/` and the frontend are untouched.

- **Run:** `20261016T104745Z` (`E53_results.json`, `runs/20261016T104745Z/predictions.csv`, `runner/e53_run.py`, `runner/e53_show.py`).
- **Protocol:** E36 walk-forward, nested rule, seed 36, G1/G4/G3/G2 grid, E49-C2 shrinkage fitted on earlier dates only; 13 test quarters 2023-Q1..2026-Q3 (65 rows: 53 HIGH / 12 LOW).
- **No forcing:** no monotone constraints, weights or feature tricks.
- **Reproduction:** A0 reproduces the served E49 walk-forward exactly (max |Δp| = 0; accuracy 0.846, balanced accuracy 0.841, AUC 0.855).

**cond_\* inputs (no leakage).**
- **Timing:** the row of target quarter F uses data quarter F−2.
- **Rank:** each component is ranked against that series' history strictly before the data quarter: 100·#{earlier < x}/n. Fewer than 2 earlier values means missing.
- **Sources:** E52 (PSA CPI, NASA POWER, IBTrACS, PSA fisheries, PSA LFS national, BSP remittances), read only. Current data vintages are used (revisions are not modelled).

## Training inputs at the Q4 2026 origin (75 rows)

| Input | Variance | Distinct values | Missing |
|---|---|---|---|
| cond_market | 792.2 | 51 | 0 |
| cond_climate | 1123.8 | 29 | 0 |
| cond_fish | 1253.8 | 33 | 0 |
| cond_employment | 719.7 | 12 (national: one value per quarter) | 0 |
| cond_ofw | 1892.7 | 11 | 15 |
| trig_market | 0.0001 | 5 | 0 |
| trig_climate | 0.0077 | 32 | 0 |
| trig_employment | 0.0000 | 2 | 0 |
| trig_ofw_remittance | 0.0000 | 1 | 0 |
| trig_fish_kill | 0.0008 | 4 | 0 |

## Performance (65 test rows)

| Arm | Acc. | Bal. acc. | AUC | Brier | Log loss | Precision | LOW caught | HIGH caught | Train acc. (raw / C2) | McNemar p (Holm) | Brier sign-flip p (Holm) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **A0** E49 as served | **0.846** | **0.841** | 0.855 | 0.151 | 0.489 | 0.957 | 10/12 | **45/53** | 1.000 / 1.000 | – | – |
| **A1** E48-A1 + cond_* | 0.785 | 0.836 | 0.880 | 0.150 | 0.482 | 0.976 | **11/12** | 40/53 | 1.000 / 1.000 | 0.22 (0.44) | 0.90 (1.00) |
| **A2** E36 + cond_* | 0.785 | 0.836 | **0.884** | 0.150 | **0.474** | 0.976 | **11/12** | 40/53 | 1.000 / 1.000 | 0.22 (0.44) | 0.97 (1.00) |

- **Brier difference vs A0:** A1 −0.0007, A2 −0.0005. No difference is significant.
- **Rows that changed:** A1 and A2 each gain one LOW (12 LOW rows in total), but miss 5 more HIGH rows than A0. McNemar: the arm alone was right on 1 row, A0 alone on 5.

## Five-driver attribution

| Arm | Mean over 65 test rows, five drivers (M / C / F / E / O) | Same, with Other in the denominator | Drivers non-zero |
|---|---|---|---|
| A0 | 78.7 / 13.6 / 0.05 / 0 / 0 | 48.8 / 5.1 / 0.0 / 0 / 0, Other 38.3 | 3 |
| A1 | 67.2 / 4.4 / 3.4 / 11.9 / 5.4 | 52.3 / 3.2 / 1.9 / 6.5 / 4.4, Other 24.0 | **5** |
| A2 | 68.7 / 4.2 / 3.1 / 10.6 / 5.7 | 53.2 / 2.6 / 1.7 / 5.9 / 4.6, Other 24.3 | **5** |

### Tree splits on the cond_* inputs

| Arm | Q4 2026 model (market / climate / fish / employment / OFW) | Sum over the 13 test-origin models |
|---|---|---|
| A1 | 44 / 42 / 26 / 43 / 3 (trig_climate falls from 36 to 6) | 229 / 202 / 106 / 232 / 68 |
| A2 | 49 / 39 / 25 / 44 / 3 | 216 / 261 / 95 / 239 / 74 |

## Q4 2026 (origin 2026-10-01)

### Index

| Arm | CALABARZON | Cavite | Laguna | Quezon | Rizal | Batangas |
|---|---|---|---|---|---|---|
| A0 | 0.778 | 0.888 | 0.877 | 0.914 | 0.877 | 0.335 |
| A1 | 0.789 | 0.917 | 0.912 | 0.917 | 0.917 | 0.284 |
| A2 | 0.788 | 0.917 | 0.914 | 0.917 | 0.918 | 0.275 |

### Driver shares

Driver shares are given as M / C / F / E / O: Market, Climate, Fish Kill, Employment, OFW.

| Arm | Unit | Five drivers (M / C / F / E / O) | With Other |
|---|---|---|---|
| A0 | CALABARZON | 65 / 33 / 2 / 0 / 0 | 33 / 16 / 1 / 0 / 0, Other 50 |
| A1 | CALABARZON | 60 / 5 / 14 / 19 / 2 | 39 / 3 / 9 / 12 / 1, Other 36 |
| A1 | Cavite | 58 / 3 / 14 / 23 / 2 | |
| A1 | Laguna | 51 / 9 / 18 / 19 / 3 | |
| A1 | Quezon | 67 / 1 / 12 / 18 / 2 | |
| A1 | Rizal | 57 / 7 / 15 / 19 / 2 | |
| A1 | Batangas | 66 / 5 / 11 / 17 / 1 | |
| A2 | CALABARZON | 62 / 2 / 15 / 20 / 1 | 38 / 1 / 10 / 13 / 0, Other 38 |

The A1 per-province rows are the five-driver shares only.

### Largest A1 inputs at Q4

**Cavite**

| Input | SHAP |
|---|---|
| Dnow | +1.00 |
| y_last | +0.87 |
| cond_employment | +0.75 |
| cond_market | +0.50 |
| cond_fish | −0.43 |

**Batangas**

| Input | SHAP |
|---|---|
| y_last | −2.18 |
| Dnow | −2.16 |
| cond_employment | +0.74 |

## Adoption (rule fixed before the run)

| Arm | Bal. acc. ≥ 0.83 | AUC ≥ 0.84 | Brier ≤ 0.16 | LOW ≥ 10/12 | Eligible | Drivers non-zero |
|---|---|---|---|---|---|---|
| A0 | ✓ 0.841 | ✓ 0.855 | ✓ 0.151 | ✓ 10 | yes | 3 |
| A1 | ✓ 0.836 | ✓ 0.880 | ✓ 0.150 | ✓ 11 | yes | 5 |
| A2 | ✓ 0.836 | ✓ 0.884 | ✓ 0.150 | ✓ 11 | yes | 5 |

**Result:** all three are eligible.
- A1 and A2 both have 5 non-zero drivers, against 3 for A0.
- They tie on balanced accuracy (0.8357), so the rule falls to lower Brier: **A1** (0.1501 vs 0.1504).

**By the fixed rule, A1 is preferred.**

## Caveats to weigh before any decision (not part of the rule)

1. **Accuracy drops** from 0.846 to 0.785. A1 misses 13 HIGH rows against A0's 8 and catches one more LOW. Balanced accuracy is about equal (0.836 vs 0.841); the difference is not significant.
2. **Still overfit.** Training accuracy is 1.000 for every arm, and the SHAP baseline is 2.80 log-odds (p 0.94), against 2.67 for A0.
3. **The index does not come down.** At Q4 2026, A1 gives 0.789 against 0.778. The four high provinces rise to about 0.92, and Batangas falls to 0.28. The cond_* inputs spread the attribution across five drivers; they do not lower the level.
4. **Employment (about 19% at Q4) is a national input.** It has one value per quarter (12 distinct), so it adds the same push (+0.6 to +0.8) to every province. It cannot tell provinces apart, and it partly tracks time: unemployment rose in 2025–26, as HIGH labels did.
5. **OFW is thin.** It has 15 of 75 training values missing and 3 splits in the Q4 model. Its 2026 values are provisional (secondary-source BSP), and the curated 2022–25 split is unverified.
6. **Climate falls from 33% to 5%.** The measured rainfall/storm score replaces most of the news-share climate input, which was the spurious protective one.
