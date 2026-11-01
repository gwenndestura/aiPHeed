# Y12 results: domestic rice supply and the Lead-2 price condition

**Plan:** `EXPERIMENT_PLAN.md`, SHA-256 `25f672cd34aa28220dcf7ec6971a374686901bfa327ed33321401d4ea731da79`, frozen 2026-10-29T12:52:54Z. That was before any supply feature was related to any outcome.

**Data:** `DATA_AUDIT.md`.

**Reproduce** (from `runner/`):

```
python -B acquire.py       # downloads (re-download changes hashes; the run checks the pinned ones)
python -B tidy.py          # tidy series + out/coverage.json
python -B audit_checks.py  # 2012 vs 2018 overlap, prevalence (pre-plan)
python -B run_dev.py       # step 3: out/dev_results.json, out/dev_rows_main.csv, out/dev_rows_sens.csv
```

Logs are in `out/log_*.txt`. `run_dev.py` asserts the plan hash and the pinned data hashes before running.

## Answer

| Question | Answer |
|---|---|
| Did the price-side model genuinely improve? | **No.** No candidate met the acceptance rule. The supply features add nothing out of sample: the best candidate gains Brier 0.0003 over its own no-supply version, p = 0.43. |
| Was the full P0H4 Lead-2 forecast tested? | **No, by the frozen rule.** Step 4 runs only with a credible price model, and there is none. P0H4 Lead 2 therefore still fails R3, R5 and R6, unchanged: 0.769 / 0.635 / P 0.60 / R 0.35, Brier 0.194. |
| Did anything pass all seven rules? | **No.** |

## Step 3: independent years, 2002–2020

**Rows.** 5 provinces × 76 target quarters = 380 rows. Prevalence 0.518. Clusters are the 76 quarters.

**Fitting.** Each origin is refitted on 110–485 earlier rows. Supply cells were missing in 21 rows (26 cells), filled by the plan's rule.

**Main availability bounds:** stocks M ≤ m0 − 2; farmgate M ≤ m0 − 1.

| Model | Acc | Bal | Prec | Rec | Spec | F1 | AUC | Brier | Δ Brier vs PERS-PROB (cluster p; block-4 p) |
|---|---|---|---|---|---|---|---|---|---|
| PERS-BIN (0/1 persistence) | 0.658 | 0.659 | 0.68 | 0.64 | 0.68 | 0.660 | 0.659 | 0.342 | – |
| CLIM | 0.532 | 0.543 | 0.63 | 0.23 | 0.85 | 0.341 | 0.503 | 0.259 | +0.029 (0.996; 0.967) |
| **PERS-PROB** (primary comparator) | 0.624 | 0.629 | 0.69 | 0.49 | 0.77 | 0.576 | 0.669 | **0.2299** | – |
| **M1** SUPPLY-SIMPLE: xF, xG, stocks YoY, farmgate YoY | 0.634 | 0.639 | 0.71 | 0.50 | 0.78 | 0.585 | 0.652 | 0.2391 | +0.009 (0.86; 0.81) |
| **M2** SUPPLY-REG: L2 logistic, 7 price + 6 supply features | 0.629 | 0.635 | 0.72 | 0.47 | 0.80 | 0.566 | 0.664 | 0.2381 | +0.008 (0.70; 0.69) |
| **M3** SUPPLY-CONT: continuous food YoY + stocks and farmgate YoY | 0.613 | 0.608 | 0.60 | 0.76 | 0.46 | 0.670 | 0.700 | 0.2248 | −0.005 (0.36; 0.39) |
| M2-0 (M2 without supply) | 0.653 | 0.660 | 0.77 | 0.47 | 0.85 | 0.585 | 0.670 | 0.2366 | +0.007 (0.66) |
| M3-0 (M3 without supply) | 0.605 | 0.600 | 0.59 | 0.75 | 0.45 | 0.664 | 0.699 | 0.2251 | −0.005 (0.36) |
| WAR-P (world-price comparator, Y11 design, provincial) | 0.605 | 0.601 | 0.60 | 0.71 | 0.50 | 0.650 | 0.636 | 0.2509 | +0.021 (0.88; 0.74) |

**Acceptance (frozen):**

| Candidate | A1: Brier < PERS-PROB, Holm p < 0.10 | A2: balanced ≥ PERS-PROB | A3: supply beats its ablation, p < 0.10 | A4: lag-robust | Credible |
|---|---|---|---|---|---|
| M1 | no (+0.009; Holm p 1.0) | yes (0.639) | no (+0.009, p 0.86) | no | **no** |
| M2 | no (+0.008; Holm p 1.0) | yes (0.635) | no (+0.002 vs M2-0, p 0.58) | no | **no** |
| M3 | no (−0.005; Holm p 1.0) | no (0.608) | no (−0.0003 vs M3-0, p 0.43) | yes | **no** |

**Sensitivity bounds** (stocks M ≤ m0 − 5, farmgate M ≤ m0 − 4): the results are the same or worse.

| Model | Brier |
|---|---|
| M1 | 0.2358 |
| M2 | 0.2399 |
| M3 | 0.2273 |
| PERS-PROB | 0.2299 |

**What M3's small edge comes from.** M3's lower Brier comes entirely from forecasting continuous food inflation (M3-0, without supply, does the same). It is not significant (p 0.36), and its balanced accuracy is lower (0.60 vs 0.63).

**Calibration.**

| Model | Slope | Intercept | Note |
|---|---|---|---|
| PERS-PROB | 0.86 | 0.21 | Close to calibrated |
| M1 | 0.61 | 0.25 | Overconfident: lowest bin forecasts 0.17, observed 0.40 |
| M2 | 0.58 | 0.24 | Overconfident |
| M3 | 0.76 | −0.25 | Over-forecasts the upper bins: 0.58 forecast vs 0.43 observed |

**Per-province Brier** (PERS-PROB / M1 / M2 / M3):

| Province | PERS-PROB | M1 | M2 | M3 |
|---|---|---|---|---|
| Cavite | 0.227 | 0.212 | 0.225 | 0.278 |
| Laguna | 0.198 | 0.227 | 0.230 | 0.230 |
| Quezon | 0.267 | 0.277 | 0.272 | 0.192 |
| Rizal | 0.205 | 0.212 | 0.213 | 0.201 |
| Batangas | 0.253 | 0.268 | 0.250 | 0.224 |

No candidate is better in every province.

### Do the supply indicators lead the outcome?

The outcome here is the change from the issue-time 3-month food YoY to the target-quarter food YoY. Cluster-bootstrap 90% CIs.

| Indicator | Leading r (at issue date) | Concurrent r (at target months) | Reading |
|---|---|---|---|
| S1 stocks YoY | **−0.19 [−0.37, −0.004]** | −0.09 [−0.33, 0.13] | Weak leading signal; the sign is plausible (lower stocks → rising food inflation). About 4% of variance. |
| S2 stocks, 3-month change | −0.03 [−0.22, 0.16] | +0.02 | None |
| S3 NFA share of stocks | −0.11 [−0.26, 0.05] | −0.21 [−0.36, −0.05] | Concurrent, not leading |
| S4 commercial stocks YoY | −0.12 [−0.31, 0.06] | −0.01 | None |
| S5 farmgate palay YoY | −0.01 [−0.16, 0.14] | **+0.46 [0.32, 0.59]** | **Coincident:** moves with retail food inflation, does not anticipate it |
| S6 farmgate, 3-month change | +0.19 [0.03, 0.35] | +0.10 | Weak leading signal |

**Why the models do not use these signals.**

- **Farmgate palay** is coincident with retail food inflation (r = 0.46 in the same months, 0.01 when leading). By the time it is published, the retail CPI it tracks is already in the persistence term.
- **Stocks** carry a weak leading signal (r ≈ −0.19). It does not survive out-of-sample estimation with 110–485 training rows: adding it to persistence raised the Brier score.
- **Rice is a modest share** of the food basket. The provincial food condition at 5–7 months is driven by more than rice supply.

## Step 4: full P0H4 Lead-2 forecast

**Not run.** EXPERIMENT_PLAN section 7 allows step 4 only for a credible price model. Running it anyway would mean scoring non-credible models on the already-used 2021–2026 rows, which the plan rules out.

For reference, the unchanged served P0H4 Lead 2 is reproduced in Phase 2 (Y0):

| Accuracy | Balanced | Precision | Recall | Brier | TP/FP/FN/TN | Fails |
|---|---|---|---|---|---|---|
| 0.769 | 0.635 | 0.60 | 0.35 | 0.194 | 6/4/11/44 | R3, R5, R6 |

PERSIST-SI on the same rows has accuracy 0.677 and Brier 0.323.

## Step 5: is another hypothesis justified?

**Not with the data available. No further model was run.**

1. **Post-hoc features.** The only signals with leading correlation CIs excluding zero (stocks YoY, farmgate 3-month change) were identified in this development data. A model built on them would be chosen with the same data used to judge it, which is the pattern that failed out of sample in Y10/Y11. No untouched price period remains in which to confirm it, except prospective quarters.
2. **Effect size.** r ≈ 0.19 is too small to lift the price condition from about 0.63 to the ≥ 0.70 balanced accuracy the joint T43c target needs. Y9 showed the joint target passes R2 + R3 + R6 in 13-quarter windows only when the price condition is close to known.
3. **The remaining supply channels are not available as history:**
   - provincial or regional stocks (2026 only);
   - import arrivals and shipments (only from 2015; commodity codes not exposed before that);
   - real-time vintages of all series.
4. **Event-driven policy shocks are too few to model statistically:** the Rice Tariffication Law (2019), the EO 39 price cap (2023), and the EO 62 tariff cut (2024).

**What would change the conclusion:**

- regional (CALABARZON) stocks and import arrivals with at least 10 years of monthly history and documented release dates;
- verified historical PSA release dates;
- above all, **prospective sealed Lead-2 forecasts**. These are the only untouched test available for any new price term, including the stocks signal.

## Integrity

- All work is in `LEAD2_RELIABILITY_RESEARCH/y12_domestic_rice_supply/`. Inputs outside it were only read: E41 thresholds, the Y10 Pink Sheet.
- No production model, protected file or dataset was modified.
- The seven criteria, the threshold, the target definition and the test period were not changed.
- No commit, push or deploy.
