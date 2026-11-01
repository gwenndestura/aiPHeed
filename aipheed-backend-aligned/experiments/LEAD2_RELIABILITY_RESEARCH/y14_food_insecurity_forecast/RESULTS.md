# Y14 results: a Lead-2 food-insecurity forecast validated on observed hunger

**Target:** TFI-2, observed Balance Luzon involuntary hunger > 11.3% two quarters ahead (`OBJECTIVE_AND_TARGET.md`).

**Plan:** `EXPERIMENT_PLAN.md`, SHA-256 `3f6d48bcb3c8a169c998d701955084a4ca22cbeb8642f1d1218c018e8c3d3172`, frozen 2026-10-29T13:17:06Z, before any model was scored.

**Data:** `DATA_AUDIT.md`.

**Reproduce** (from `runner/`):

```
python -B acquire.py               # PSA OpenSTAT downloads (manifest with hashes)
python -B indicators.py            # point-in-time indicators, no outcomes
python -B run.py                   # development gate, 2021-2026 rows, served-FIRI domain description
python -B domain_replication.py    # post hoc, descriptive
python -B issue_forecast.py --issue YYYY-MM-DD   # sealed prospective forecast (run ON the issue date)
```

**Disclosed deviations:**

1. **Missing domain fill.** The first run of `run.py` stopped before scoring anything. The in-fold mean of a domain with no training values (employment before 2006-Q3) was itself missing. Such a domain is now filled with 0.5, the neutral percentile.
2. **Served-FIRI row label.** My confirmation table first keyed the served FIRI v2 under the name of the drivers-only candidate ("F2"), so it overwrote it. I fixed the labelling and reran. `dev_results.json` was byte-identical before and after.
3. **Refactor check.** `run.frame()` was given an optional in-memory input for the prospective script. Results were verified identical by SHA-256.

## 1. Development on independent years (the frozen gate)

**Rows.** 46 targets, 2009-Q1 .. 2020-Q4. Prevalence 0.74 (12 LOW). All models are scored on identical rows, as required by the plan; the drivers-only F2 needs employment, which starts in 2006-Q3.

**Comparator.** H1, the hunger-persistence probability. The bootstrap resamples quarters (B = 5000), with a 4-quarter block version in brackets.

| Model | Acc | Bal | Prec | Rec | Spec | F1 | AUC | Brier | MAE | Δ Brier vs H1 (p; block p) |
|---|---|---|---|---|---|---|---|---|---|---|
| PERSIST (newest reading > 11.3) | 0.717 | 0.620 | 0.80 | 0.82 | 0.42 | 0.812 | 0.620 | 0.283 | 5.30 | +0.102 (0.996; 0.995) |
| CLIM | 0.739 | 0.500 | 0.74 | 1.00 | 0.00 | 0.850 | 0.277 | 0.214 | – | +0.033 (0.86; 0.94) |
| **H1 hunger persistence** | 0.739 | **0.635** | 0.81 | 0.85 | 0.42 | 0.829 | 0.740 | **0.181** | 5.30 | – |
| **F1 FIRI-analog** (v2 scoring, equal weights) | 0.543 | 0.583 | 0.81 | 0.50 | 0.67 | 0.618 | 0.647 | 0.244 | – | +0.063 (0.98; 0.99) |
| **F2 FIRI drivers only** (no hunger domain) | 0.457 | 0.551 | 0.80 | 0.35 | 0.75 | 0.490 | 0.569 | 0.283 | – | +0.102 (0.995; 0.998) |
| **M1** logistic: H1 + affordability, climate, economy | 0.696 | 0.471 | 0.73 | 0.94 | 0.00 | 0.821 | 0.642 | 0.196 | – | +0.015 (0.75; 0.86) |
| M1-0 (H1 only, recalibrated) | 0.696 | 0.471 | 0.73 | 0.94 | 0.00 | 0.821 | 0.672 | 0.188 | – | +0.007 (0.63) |
| **M2** continuous hunger change + domains | 0.717 | 0.485 | 0.73 | 0.97 | 0.00 | 0.835 | 0.525 | 0.229 | 4.98 | +0.048 (0.89; 0.92) |
| M2-0 (mean reversion) | 0.739 | 0.500 | 0.74 | 1.00 | 0.00 | 0.850 | 0.659 | 0.208 | 4.86 | +0.027 (0.75) |
| KAL (reference: SWS sampling error modelled) | 0.674 | 0.456 | 0.72 | 0.91 | 0.00 | 0.805 | 0.745 | 0.172 | – | −0.009 (0.29; 0.49) |

**Gate (frozen).** Holm p = 1.0 for every candidate.

| Candidate | G1: Brier < H1, Holm p < 0.10 | G2: balanced ≥ H1 | G3: added information helps | Passes |
|---|---|---|---|---|
| F1 | no | no | no (F1 is worse than H1) | **no** |
| F2 | no | no | no (vs CLIM: +0.069, p 0.97) | **no** |
| M1 | no | no | no (vs M1-0: +0.008, p 0.82) | **no** |
| M2 | no | no | no (vs M2-0: +0.021, p 0.96) | **no** |

**Calibration slopes:** H1 0.51, M1 0.48, M2 0.10, KAL 0.87. KAL is the best calibrated, but it never predicts LOW at 0.50.

### Does any driver lead hunger?

1999–2020, Lead-2 horizon. The outcome is the hunger change from the newest reading to the target quarter. Bootstrap 90% CIs.

| Indicator (driver label) | Leading r [CI] | Concurrent r [CI] |
|---|---|---|
| A2 headline inflation (Market / Prices) | +0.04 [−0.12, 0.21] | +0.16 [−0.01, 0.32] |
| A3 rice CPI (Market / Prices) | −0.12 [−0.28, 0.04] | +0.06 |
| C1 El Niño, ONI proxy (Climate Stress) | +0.01 [−0.18, 0.17] | +0.01 |
| C2 typhoons (Climate Stress) | −0.15 [−0.35, 0.03] | +0.12 |
| C3 palay/corn drop (Climate Stress) | **−0.29 [−0.48, −0.07]** (wrong sign) | +0.01 |
| C4 fisheries drop (Fish Kill, proxy) | −0.16 [−0.34, 0.01] | −0.07 |
| E1 unemployment change (Employment) | −0.04 [−0.24, 0.17] | +0.09 |
| E2 remittance decline (OFW Remittance) | **not testable**: BSP download blocked | – |

No driver shows a positive leading relation with rising hunger. The only CI that excludes 0 (production drop) has the opposite sign to FIRI's assumption.

## 2. Why the served FIRI v2 looks strong on 2021–2026 (descriptive; nothing selected)

AUC of each domain score against TFI-2:

| Domain | Served FIRI v2, 17 targets 2022-Q3..2026-Q3 | Y14 analog, same period (21 targets) | Y14 analog, 1999–2020 (independent) |
|---|---|---|---|
| A Affordability | **0.20** (inverted) | 0.42 | 0.59 [0.48, 0.70] |
| **C Climate and production** | **0.95** | 0.51 | **0.49** [0.37, 0.60] |
| E Household economy | – (8 rows) | 0.82 | 0.67 [0.50, 0.82] |
| H Regional hunger | 0.79 | 0.76 | 0.67 [0.56, 0.77] |
| Whole index | 0.93 | 0.72 (F1) | 0.64 (F1) |

**Verified in `firi2_history.csv`: what drives the climate domain's 0.95.**

- **Warm-up artefact.** For the first three LOW targets (2022-Q3, 2022-Q4, 2023-Q1), the served climate domain is exactly 0.0. Typhoons, production and fisheries had no score ("insufficient_history" under the 8-prior rule, or missing). Only the El Niño flag was scored, and it was 0. So 3 of the 5 LOW quarters got a low climate score because of the scoring rule's warm-up, not because of observed climate conditions.
- **A one-off coincidence.** The PAGASA El Niño alert (C1 = 1) was in force for the targets 2023-Q4 to 2024-Q3, exactly when BL hunger rose above 11.3.
- **In-sample weighting.** The served walk-forward evidence weights raised the climate domain to about 2× (and the hunger domain to below 1) from 2023-Q4, using these same outcomes.

On 1999–2020 the climate domain does not separate hunger HIGH from LOW (AUC 0.49).

**Conclusion.** FIRI v2's 0.941 accuracy on 2021–2026 is mainly the product of a scoring warm-up, one El Niño episode coinciding with the hunger onset, and weights fitted to that coincidence. It is **not** evidence that the composite forecasts food insecurity. This is a methodological finding about the evaluation, not a code defect. The served FIRI was not changed.

## 3. The 17 official FIRI Lead-2 rows (2022-Q3..2026-Q3): seven rules for every candidate

**DESCRIPTIVE ONLY.** No candidate passed the development gate, so nothing is selected from these rows. The rules are applied by `FIRI_LEAD2_FEASIBILITY/runner/score_firi_l2.rules`, unchanged.

| Forecast | Acc | Bal | P / R | AUC | Brier | TP/FP/FN/TN | R1 | R2 | R3 | R4 | R5 | R6 | R7 | All |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Served FIRI v2 | 0.941 | 0.958 | 1.00 / 0.92 | 0.933 | 0.189 | 11/0/1/5 | F | P | P | P | F | P | P | **no** |
| H1 (as stored with the FIRI rows) | 0.706 | 0.617 | 0.77 / 0.83 | 0.792 | 0.161 | 10/3/2/2 | F | F | F | F | F | P | F | no |
| Y14 H1 (recomputed) | 0.706 | 0.617 | 0.77 / 0.83 | 0.825 | 0.142 | 10/3/2/2 | F | F | F | F | F | P | F | no |
| Y14 F1 FIRI-analog | 0.588 | 0.708 | 1.00 / 0.42 | 0.883 | 0.231 | 5/0/7/5 | F | F | P | F | F | F | F | no |
| Y14 F2 drivers only | undefined in 1 row | – | – | – | – | – | – | – | – | – | – | – | – | – |
| Y14 M1 | 0.588 | 0.417 | 0.67 / 0.83 | 0.717 | 0.179 | 10/5/2/0 | F | F | F | F | F | P | F | no |
| Y14 M2 | 0.647 | 0.458 | 0.69 / 0.92 | 0.667 | 0.216 | 11/5/1/0 | F | F | F | F | F | P | F | no |
| Y14 M1-0 | 0.706 | 0.500 | 0.71 / 1.00 | 0.783 | 0.175 | 12/5/0/0 | F | F | F | F | F | P | F | no |
| Y14 M2-0 | 0.706 | 0.500 | 0.71 / 1.00 | 0.783 | 0.186 | 12/5/0/0 | F | F | F | F | F | P | F | no |
| Y14 KAL | 0.706 | 0.500 | 0.71 / 1.00 | 0.783 | 0.155 | 12/5/0/0 | F | F | F | F | F | P | F | no |

**R1 fails for every forecast:** 17 regional rows is below the 40 the rule requires (`OBJECTIVE_AND_TARGET.md` section 6). R1 was not reinterpreted.

**Effective sample.** One row per quarter, 17 independent rows, 5 LOW. Two LOW quarters sit exactly on 11.3 (Y1 sensitivity).

## 4. Sealed prospective comparison

`runner/issue_forecast.py` issues, side by side:

- H1, the FIRI-analog F1, PERSIST and CLIM;
- any gate-passing candidate (none).

For target t + 2 it records:

- the UTC write time and a validity flag (valid only if written on or before the issue date);
- the newest SWS round used;
- the forecasts and their class at 0.50;
- the indicators;
- the git HEAD and plan hash;
- the SHA-256 of all 16 input files.

It writes to `prospective/` under a timestamped name, refuses to overwrite, and appends to `prospective/SEALS.txt`. It does not touch any existing sealed artifact (P0H4, FIRI, P4H4).

**Demonstration run.** `--issue 2026-10-01` gave `seal_issue_2026-10-01_written_20261029T132913Z.json`, sha `852a09bb…`, **validProspective = false**, because it was written after the issue date. It correctly excludes the SWS 2026-Q3 round (published 2026-10-14) and uses 2026-Q2 (17.3). Target 2027-Q1: H1 0.83, F1 0.74, both HIGH.

**The first valid run is on 2027-01-01** (target 2027-Q3). It must be run on that day, and it uses only what is published by then.

## 5. Conclusion

| Question | Answer |
|---|---|
| Most defensible food-insecurity target | Observed SWS involuntary hunger in Balance Luzon > 11.3% (TFI-2). It is the only repeatedly observed food-insecurity outcome. FIES (1 regional value) and subsistence incidence (triennial, CV up to 59%) cannot serve as Lead-2 targets. **Limitations:** severe end of food insecurity only; Balance Luzon, not Region IV-A; no provincial outcome; ±4–6 point sampling error. |
| Does the FIRI composite forecast food insecurity? | **No evidence that it does.** On independent years, the FIRI method (F1) is worse than hunger persistence (Brier 0.244 vs 0.181), and its drivers alone are worse than climatology. Its 2021+ strength traces to a warm-up artefact, one El Niño coincidence and weights fitted to that period. |
| Which signals carry out-of-sample Lead-2 information? | Only the hunger reading itself (H1). None of the testable drivers leads hunger (prices, El Niño, typhoons, production, fisheries, unemployment). OFW remittances could not be tested (BSP blocked). |
| Did anything improve on persistence? | **No.** The noise-aware Kalman model had a lower Brier than H1 (−0.009, p 0.29), not significant, with lower balanced accuracy. |
| Did any candidate pass all seven rules? | **No.** R1 also cannot pass for any regional Lead-2 forecast before about 40 observed quarters. |
| Evidence still needed | **1.** A food-insecurity outcome observed more often or at a finer level than BL quarterly hunger (e.g. provincial FIES rounds, or a commissioned CALABARZON hunger module), and published before the Lead-2 issue date. **2.** OFW remittance history (manual BSP download) to test the last driver. **3.** Sealed prospective quarters from 2027-01-01 with `issue_forecast.py`. **4.** A committee decision on R1 for regional targets. The rule was not changed here. |
