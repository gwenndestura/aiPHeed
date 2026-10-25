# FINAL_OBJECTIVE_ACHIEVEMENT forecasting protocol

**Branch:** `aiPHeed/final-objective-achievement`, from `ecb18dc` (FINAL_FOOD_INSECURITY_LIGHTGBM). E107–E114 and FINAL are preserved.

**Freezing:** this file's SHA-256 goes in `runner/PROTOCOL_SHA256.txt` before any model in it is scored. Changes go in addenda only.

**Disclosure.** Every 2021–2026 SWS reading, and every E107–FINAL result on them, has been seen. All 2021+ results here are therefore **development (exploratory) evidence**. The only untouched evaluation available is prospective: the seal in §8.

**Data window.** The primary analysis uses 2021+ data only. No pre-2021 data enter any test, model or simulation parameter in this protocol. FINAL's separate long-history arm is cited, not re-run.

## 1. The failures this protocol addresses

| # | Identified failure (FINAL, E107–E114) | Change tested here |
|---|---|---|
| F1 | FIL learned "hunger reverts to its average" from 2021–23 and failed in the 2024 surge. Persistence was better. | The target is anchored on persistence: LightGBM learns only the **change from the latest reading**, d = H_q − h_last. It learns deviations from "no change", not a level. |
| F2 | SWS publishes 17–99 days late, so Lead 1 is really 2 quarters past the newest reading. | **Lead 0 is added:** nowcasting the quarter that just ended, whose survey is not yet published (true horizon 1). |
| F3 | The news corpus was collected retrospectively, and the agri-supply signal did not replicate. | Primary news = **GDELT GKG** CALABARZON documents. They are timestamped by GDELT in real time, so there is no retrospective labelling. The same gap-aligned, de-duplicated categories are used, plus the anticipatory share (FINAL `news_features`, source "G"). |
| F4 | The SWS respondent base changed from household heads to adults in 2025, with no bridge round. | Feature `post_break` = 1 if the newest known reading was an adult-base round, i.e. published on or after 2025-06-27. |
| F5 | Surges are missed by 10–13 points. | Variant ASYM: LightGBM with a quantile objective (α = 0.7), which penalises under-prediction more than over-prediction. |
| F6 | "75% is impossible" rested on a model-based ceiling. | The ceiling is verified empirically (§6) before it is used in any conclusion. |

## 2. Outcome, label and data roles

**Outcome.** As in FINAL §2: SWS involuntary hunger for 4 areas (`../FINAL_FOOD_INSECURITY_LIGHTGBM/data/sws_area_rounds_2021.csv`), with the vintage rule.

**Label.** ELEVATED, unchanged: H(a,q) is above the mean of the area's readings for quarters q−4 … q−1 (at least 2 needed). It is kept because:
- it is two-class (base rate 0.57);
- it is the label already frozen in FINAL; changing it now would be choosing a label after seeing results.

**Province-level classification.** Chapter I Objective 2 speaks of high- and low-risk provinces. No provincial food-insecurity outcome exists in any period (see `DATA_AVAILABILITY_AND_TARGET_VALIDATION.md`), so provincial classifications cannot be scored. This is reported as a data gap. No proxy label is invented.

**PSA food CPI deviation (economic access).** It is used as an input (A1, A2, A3) and as FINAL's provincial food-price squeeze indicator. It is never used as a hunger label.

## 3. The primary model: FIL-OA

- **Rows:** 4 areas × Leads 0–4.
- **Rule for a valid row:** the target quarter must not be published at the issue date (true horizon ≥ 1).
- **Target:** d = H_q − h_last (the training value is the vintage known at the origin).
- **Level forecast:** Ĥ = h_last + d̂.
- **ELEVATED call:** Ĥ > REF̂.
- **Probability:** P = Φ((Ĥ − REF̂)/σ), with σ by FINAL's rule (the model's own past errors at that lead, at least 6).

**Columns**
- FINAL's columns, except that news `NC_*` is replaced by `NG_gap_*` (6) + `NG_ant`.
- `N1` (FSSI-v3) is kept.
- `post_break` is added.
- All 12 families stay present. The family map is in `data/feature_map.csv`.

**Unchanged from FINAL:** the grid {3, 7} leaves × {100, 300} trees, chronological inner validation (last 4 training target quarters), the issuing rule, seed 2026, and the leakage cut-offs.

## 4. Comparisons (all on the rows where FIL-OA is issued)

**Baselines**

| ID | Baseline |
|---|---|
| PERSIST | Latest reading |
| MA2 | Moving average of the two newest readings |
| MAJ | Climatology |
| ALWAYS | Always ELEVATED |
| LOGIT | Logistic regression on FIL-OA's columns |
| PSA-ONLY | Logistic regression on the PSA columns |
| NLP-ONLY | Logistic regression on the news columns |

**Pre-registered variants**

| Variant | Change |
|---|---|
| FIL-OA-NONEWS | Without news |
| FIL-OA-NEWSONLY | Hunger-history columns + news columns only |
| FIL-OA-CORPUS | Project-corpus news (`NC_*`) instead of GDELT |
| FIL-OA-ASYM | Quantile objective, α = 0.7 |
| FIL-OA-H | Hunger-history columns only |

**Verdict model.** Only FIL-OA decides the verdict. A variant that passes is reported as exploratory.

## 5. Metrics, 75% target and reliability rule

**Metrics:** as in FINAL §6.

**Reliability rule:** R1–R8 unchanged, applied at Leads 0–4.

**Maximum reliable lead:** the largest K such that every lead from the shortest evaluated lead up to K passes.

**Additional checks (reported; they cannot rescue a failing lead)**

| ID | Check |
|---|---|
| S1 | **Leave-one-quarter-out.** The accuracy difference FIL-OA − PERSIST, recomputed with each target quarter removed; reported as min and max. |
| S2 | **Surges.** For sharp increases (FINAL definition), ELEVATED recall and mean under-prediction. False alarms = ELEVATED calls on rows that were not ELEVATED. Reported for FIL-OA, ASYM and PERSIST. |
| S3 | **News value.** FIL-OA vs FIL-OA-NONEWS: paired cluster bootstrap on Brier, McNemar, Holm across leads. A 100-permutation news placebo at Leads 0–1. |

## 6. Verification of the accuracy ceiling (2021+ parameters only)

### V1. Test–retest of the label (empirical; no model)

**Data.** Quarters with two non-commissioned rounds in 2021+ (2021-Q2, 2022-Q2, 2025-Q2) give 12 area pairs.

**Measurement.** ELEVATED is computed from each round separately against the same REF, and the agreement rate is recorded. Two independent measurements of the same truth that agree at rate a imply that a forecaster who knew the truth perfectly scores at most p = (1 + √(2a − 1))/2 against a single-round label (if 2a − 1 > 0). The point differences between paired rounds are reported too.

### V2. Simulation calibrated on 2021+ and checked against real baselines

**Parameters**
- Per area, Q is estimated from consecutive 2021+ quarter means, with each quarter's own sampling variance R (margin²/1.96²/number of rounds), floored at 0.25.
- R is taken as each area's 2021+ mean round variance.

**Simulation**
- 2,000 series with the observed 2021+ length (23 quarters) and observed gap pattern.
- At each horizon h = 1 … 5 the simulation reports three accuracies: Bayes (random-walk level), persistence (FIL's PERSIST rule) and MA2.

**Validity check.** For each lead, the observed 2021+ accuracy of PERSIST and MA2, over all panel rows with a label, must fall inside the simulated 5–95% range for the same number of rows.

| Result | Interpretation |
|---|---|
| Check passes at ≥ 80% of (rule, lead) cells | The simulation reproduces what simple rules achieve on real data, and its Bayes accuracy is reported as a validated ceiling |
| Check fails | The ceiling is reported as **unverified** and must not be used to call 75% impossible |

### V3. Statistical recheck

The paired cluster bootstrap (`boot_diff`) is run on 1,000 simulated null datasets: two forecasts with equal expected Brier, 15 quarters × 4 areas, with a correlated quarter effect. Its rejection rate at α = 0.10 is reported, and must lie between 0.06 and 0.14.

## 7. Leakage

The FINAL leakage audit is repeated for FIL-OA at 10 origins:
- future SWS rounds randomised;
- future corpus headlines shuffled;
- future GDELT documents' categories shuffled;
- a negative control.

It must pass before scoring.

## 8. Seal

FIL-OA, ASYM and PERSIST forecasts are issued at 2026-10-01 for Leads 1–4 (targets 2026-Q4 … 2027-Q3). The Lead-0 target, 2026-Q3, was published on 2026-10-14 and has been seen, so it is not sealed.

Output: `out/sealed_prospective.csv` + SHA-256. Scorer: `runner/score_prospective.py`.
