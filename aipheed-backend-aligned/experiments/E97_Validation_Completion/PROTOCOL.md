# E97: validation and completion of the served aiPHeed system (pre-registered protocol)

**Branch.** `e97-validation-completion`, from `e96-target-formulation` (8a62693). Frozen before any E97 scoring.

**Evidence status.** Every SWS round up to 2026-Q3 and every T43 row up to 2026-Q3 has been examined in E56–E96. All
E97 results on these quarters are therefore **development evidence**. No unseen quarter exists on 2026-10-22: the first
independent outcome is the SWS 2026-Q4 round (survey in December 2026), against the forecasts sealed in
`FINAL_Thesis_System/out/firi2_sealed_prospective.csv` (FIRI v2) and E96/E69 seals. E97 does not alter any sealed file.

**Why no new model search.** E83–E96 ran thirteen experiments on the same thirteen T43 target quarters. A fourteenth
search on those quarters cannot produce a validated model; it can only overfit them. E97 instead answers the questions
that were never answered for the model the dashboard actually serves (FIRI v2) and completes Objectives 3–5.

## Served system audited (thesis mode, `AIPHEED_LEAD2_MODEL=thesis`)

- **FIRI v2** (`data/thesis/firi2_history.csv`, selection C3): province index 0–1, Lead 2, six domains (A
  affordability incl. the E56 LightGBM price forecast, V vulnerability, C climate/production, E national household
  economy, N news FSSI-v3, H regional hunger outlook), walk-forward evidence weights. HIGH at FIRI ≥ 0.5.
- **E56-TUNED LightGBM** price-pressure score (T43 proxy label), shown as one affordability indicator.

## Outcomes (kept separate)

| Name | Construct | Geography | Use in E97 |
|---|---|---|---|
| R | SWS involuntary hunger > 11.3% (measured household hunger) | Balance Luzon (regional) | Primary outcome for FIRI v2 |
| T43 | regional hunger > 11.3% AND provincial food-price pressure | Province (price part only varies) | Proxy; Objective 2/4 table for the LightGBM framework |
| FNRI FIES | moderate/severe household food insecurity, 12-month recall | 2021: 2 provinces + Lucena; 2023, 2025: region | Descriptive comparison only (Q7) |

R per quarter = mean of the `definition_A == True` SWS rounds of that quarter (the served rule). Quarters without such a
round (2025-Q2, 2025-Q3) have no R outcome and are not scored.

## Questions and pre-registered procedures

**Q1. Reproduction and leakage audit of the served FIRI v2 evaluation.** The generating runner is not in the repository.
- Q1a: recompute the Lead-2 R metrics from `firi2_history.csv` (regional score = mean of the province FIRI values of the
  target quarter; backtest rows only) and `sws_rounds.csv`. Reproduced if accuracy, confusion matrix and Brier match
  `firi2_evaluation.json` (C3, lead 2) to 1e-9.
- Q1b: for every row, the H domain must equal the served `regional_hunger(origin)` probability (rounds posted before the
  issue date only). Any mismatch is a leakage/parity defect.
- Q1c: recompute the C3 evidence weights from the regional domain means and only the outcome rounds posted before each
  issue date; they must equal the stored `weights_json`.
- Q1d: every row's issue date must be the first day of origin quarter + 1 and target = origin + 2.

**Q2. Fair probability comparison (Lead 2, R).** FIRI is an index, not a probability, so its raw Brier is not
comparable with H1's. Walk-forward Platt calibration: at each target quarter q (issue date I), fit
`LogisticRegression(C=1.0)` of R on the regional FIRI using only earlier targets whose outcome round was posted before
I; require ≥ 6 pairs with both classes, otherwise the prediction is the climatology (share of R = 1 among posted pairs;
0.5 if none). Compare with H1 (served regional hunger probability) and climatology on the same quarters:
- Brier, log loss, accuracy, balanced accuracy, AUC;
- paired quarter Brier differences: bootstrap 95% CI (quarters resampled, 5,000 draws, seed 97) and a two-sided sign test;
- paired AUC and balanced-accuracy differences FIRI vs H1, quarter bootstrap 95% CI.

**Q3. What drives FIRI's regional discrimination (Lead 2, R).** Recompute the index from the stored domain scores and
weights (missing domains dropped, weights renormalised) with one domain removed at a time, and each domain alone.
Accuracy at 0.5, balanced accuracy, AUC. Reported only; served weights are never changed from this (it would be fitted
to examined quarters).

**Q4. Rising stress and windows (Lead 2, R).**
- Onset quarters: R = 1 while the latest round posted at the issue date was ≤ 11.3 (persistence calls LOW). Hits by FIRI
  ≥ 0.5 versus H1 ≥ 0.5.
- Recoveries: R = 0 while the latest posted round was > 11.3.
- Windows: targets 2022-Q2..2024-Q1 and 2024-Q2..2026-Q3.

**Q5. Objective 4 on T43, fair and same-origin.** From the E96 run `runs/20261022T073838Z` (K = 1, 2): naive
persistence, majority, climatology, PSA-only LR, NLP-only LR, E96 selected framework (M-U96-POV = E94 + poverty) and
the five group ablations. **New arm LR-ALL**: the same framework with the LightGBM price part replaced by an L2 logistic
regression (`C=0.5`, training-median imputation, training-standardised) on the same price columns and training rows; the
hunger part is the stored `M-U96-POV__ph`. Accuracy, balanced accuracy, precision, recall, F1, AUC, Brier, confusion,
and quarter-clustered bootstrap 95% CIs (target quarters resampled, 5,000 draws, seed 97) for accuracy and for paired
Brier differences against the strongest simple baseline (lowest Brier among persistence, majority, climatology).
Reported for Objective 4; no arm is promoted (T43 is a proxy label and the K criteria of E83–E96 stay in force).

**Q6. Objective 3: LGU ranking audit and sensitivity.**
- Audit: 142 LGUs, unique PSGC codes, province assignment, poverty source per LGU, Lucena substitute, map-join codes.
- Sensitivity of the within-province vulnerability rank to: weights 0.5/0.5, 0.7/0.3, 0.8/0.2, poverty only, density
  only; log-density instead of density; rank (percentile) normalisation instead of min-max; Lucena excluded.
  Spearman ρ with the served rank per province, and top-3/top-5 overlap per province.
- Dominance check: share of within-province variance of the index contributed by each term.
- Reported only; the approved 0.6/0.4 weights (Chapter I, Backend Guide v3) are not changed. They are documented as
  approved heuristic weights, not empirically learned.

**Q7. Objective 5: DOST-FNRI comparison.** Descriptive/construct-level only (no predictive validation is possible with
5 values on a different construct and recall period):
- 2021 provincial FIES (Batangas, Cavite; Lucena HUC) versus PSA 2021 poverty and the V1 profile ordering;
- 2023 → 2025 regional change versus the annual means of SWS hunger and of the regional FIRI v2.
- The NNS 2019 CALABARZON regional FIES does not exist in any DOST-FNRI publication found (E22); stated, not imputed.

**Q8. Objective 5: ISO/IEC 25010.** Search the repository, the database and all branches for evaluator responses.
Compute results only from actual responses. If none exist, provide the scoring script, response template and the exact
remaining collection requirement.

## Decision rules (mechanical)

1. If Q1a fails, the stored evaluation is not reproducible: the reproduced numbers replace it in the E97 report and
   the discrepancy is disclosed. If Q1b, Q1c or Q1d fails, the served FIRI is a leakage/parity defect and is fixed.
2. A calibrated FIRI regional probability is added to the dashboard (as an extra, labelled field; FIRI unchanged) only if
   its Brier beats H1 with the bootstrap CI entirely below 0 **and** sign p < 0.05. Otherwise it is not served.
3. Nothing else changes the served model. Q3, Q5 and Q6 are reported only.
4. Claims: the 75% goal is described as "met on the regional measured outcome (development evidence)" only if FIRI
   Lead-2 R accuracy > 0.75 and above always-elevated and H1 (the FIRI2 protocol rule), and as "not independently
   validated" until the sealed 2026-Q4/2027-Q1 quarters are scored.
