# E46: rice-policy features, three price/decision defects corrected, and the Lead-2 75% requirement

**Branch:** `e46-lead2-policy`, from `dc5c0f6`. Every protocol and addendum was committed (SHA-256) before its candidate was scored. **Date:** 2026-10-17.

## Decision

**The 75% Lead-2 requirement, with balanced HIGH/LOW discrimination, is NOT met.**

| Candidate | Accuracy | Balanced | HIGH recall | Gate |
|---|---|---|---|---|
| I7 (defect-corrected) | **0.800** | 0.684 | 0.44 | fails A2 (balanced ≥ 0.70, both recalls ≥ 0.60) |
| I8 (issued at the deployed time, the 15th) | 0.771 | 0.665 | 0.44 | fails A2; best probabilities (Brier 0.132, AUC 0.902) |

- **No five-trigger candidate** passed its pre-registered final-candidate rule. All six were scored once: I6, I6b, I7, I8, I9, I10.
- **Serving (updated by section 13):** production stays **E38**.
  - **`e46` (new):** serves the defect-corrected I7 forecast, labelled "acceptance not met". This follows the user's instruction to rebuild the 2027-Q1 forecast with the corrected formula.
  - **`e44`:** still serves E44 I2, with a known-defect warning.
- **No historical result can count as acceptance:** every historical quarter had been examined before these candidates were designed (section 9).
- **Prospective forecasts:** 2027-Q1 is frozen for I6, I6b, I7, I8, I9 and I10. Acceptance requires 4 released prospective quarters (2027-Q1..Q4).

**Best verified result:**
- **Raw accuracy:** I7, 0.800 on S44 (35 rows, 7 quarters, 9 HIGH), CI 0.66–0.94, beating every baseline. Its HIGH recall is 0.44, so it does not meet the discrimination requirement.
- **Probabilities:** I8 is the best forecaster (Brier 0.132, AUC 0.902, calibration slope 1.02). At the frozen p ≥ 0.5 rule it under-calls HIGH.

## 1. Pending work completed first

| Item | Result |
|---|---|
| E46 I6 repeat (failed earlier with exit 4) | Rerun: `runs/20261016T234337Z` is **byte-identical** to `runs/20261016T225203Z` (predictions, selections, features; results identical apart from the timestamp). |
| Fresh-server live check (API 8001 in `e44` mode, approved frontend 8082) | **Map:** Quezon drill-down draws 41 LGU polygons + 5 provinces, all in the approved palette (`#EAB308`); the API returns all 142 LGUs with a band. **News:** the panel lists articles with source, date, province and status; "News articles analyzed 10" for the region. **Trend line:** province and region series carry one score type (`food_stress_risk_probability`) for both `horizon=forecast` and `horizon=nowcast`. |
| Historical scores are as-of-origin | `runner/e46_asof_check.py`: at 5 origins (2023-Q4, 2024-Q2, 2025-Q2, 2026-Q1, 2026-Q3) all post-origin data were physically deleted and everything rebuilt. Forecasts are identical, max \|Δp\| ≤ 1.1e-16 (`runs/asof_check.json`). |
| Test suites | Backend 347 passed / 18 skipped; frontend 36 passed (re-run at the end, section 11). |
| Why I6 = I2 | Two of the four policy features (price ceiling, import suspension) are **0 at every Lead-2 origin**: each was announced and expired inside the two-quarter horizon, so no forecast issued before its announcement can see it. The tariff regime is non-zero at 3 origins, the food emergency at 1. The LightGBM residual never split on them. |
| Why I6b failed balance | Removing national employment and OFW from the hunger component improved Brier (0.181 → 0.165) and AUC (0.603 → 0.675). Accuracy was unchanged (0.686), and HIGH recall fell to 0.67 while LOW recall rose to 0.69, so balanced accuracy was 0.679 < 0.70. The decision layer (defect D2) dominated. |

## 2. Defects found and corrected

### D1: inconsistent food/headline gap (E44 I2, I3, I2 variants; E46 I6)

**Calculation trace** (`runner/e46_gap_defect.py`):
1. Raw CPI index (PSA ACP22) → base-effect projections at drift multiplier m: food `base_m`, headline `hl_m`.
2. The food residual model (LightGBM) gives F̂ = base_m + residual.
3. The **headline stays at hl_m**.
4. P(price) = 1 − Φ((min(c_food, c_gap + hl_m) − F̂)/s), so the implied gap is F̂ − hl_m.

**Why this is wrong:**
- I6 selected m = 0 at every origin.
- The residual raised F̂ by +2.6 points; the headline projection stayed −1.95 biased.
- The **implied gap was biased +3.07 points**, against +0.45 for the uncorrected projections.
- The mean P(price) was 0.80, against an observed signal rate of 0.36.

**Correction (I7):**
- F̂ = base_m + residual_F and Ĝ = (base_m′ − hl_m′) + residual_G, each projected consistently.
- P(price) uses the bivariate normal of (F, G) with inner-validated s_F, s_G and ρ.
- Ĝ bias falls to +0.44 (S44 rows: +0.25).

**Regression tests:** `tests/test_e46_gap_defect.py`:
- a synthetic case where the original formula gives P > 0.5 for a below-threshold gap and the corrected one gives P < 0.5;
- the committed runs reproduce the +3.07 bias and its correction.

**Same data, same rows: I6 vs I7 on S44**

| | I6 (original) | I7 (corrected) |
|---|---|---|
| Accuracy | 0.686 | 0.800 |
| False positives | 9 | 2 |
| False negatives | 2 | 5 |
| Decisions changed | | 14 of 35: 12 HIGH→LOW, 2 LOW→HIGH; 9 fixed an error, 5 created one |

The decision counts include D2 and D3; the bias figures isolate D1 (`runs/gap_defect_quantification.json`).

### D2: unstable per-origin Platt and threshold refit (I2–I6)

Platt scaling and the threshold were refitted at every origin on out-of-fold predictions holding 3–9 HIGH labels. The same probability became HIGH at one origin and LOW at another (I4: p = 0.21 → HIGH, p = 0.40 → LOW). The served E44 record itself shows Quezon "HIGH" at p = 0.21.

**Correction:** the fixed rule p ≥ 0.5.

### D3: residual intercepts that do not transfer (I4, I5)

The gap residual learned a 2022–2024 level (food above headline) and applied it to 2025–2026 (rice prices falling), giving a +0.9 gap bias. Leave-one-quarter-out selection could not detect it, because it trains on later quarters.

**Correction:**
- ridge **without an intercept**;
- selection by **embargoed forward chaining**, where a fold at target q is fitted only on targets ≤ q − 3, published before its origin.

**Evidence from the I7 diagnostics** (S44 accuracy):
- with an intercept: 0.657;
- with LOQO selection: 0.457;
- I7: 0.800.

### D4: the backtest was issued earlier than the deployed system issues (found in I7's audit)

**The mismatch:**
- **Deployed:** the scheduler (`backend/app/tasks/scheduler.py`, E34) runs at 03:00 on the **15th** of the quarter's first month.
- **Research:** the convention issued at 00:00 on day 1, so it used CPI only to month 2 of the latest quarter and ignored SWS rounds posted on the 1st–14th.

**Release evidence:** national CPI around the 5th–7th; RSSO IV-A provincial CPI for February 2024 was posted 2024-03-07 and for March 2024 on 2024-04-08.

**I8 uses the deployed timing:** CPI through month 3 of t, SWS posted before the 15th. Production, LFS, ENSO, remittances and rice wholesale stay at ≤ t−1.

**Effect:** with the same model, AUC 0.735 → 0.902 and Brier 0.174 → 0.132.

### D5 and D6: decision cut and all-or-nothing trigger inputs (tested, not adopted)

- **D5, I9:** cut at the training prevalence, π = 0.20–0.23 at the S44 origins. It over-calls: HIGH recall 1.00, LOW recall 0.42, accuracy 0.571.
- **D6, I10:** trigger groups admitted one at a time by inner validation. Greedy selection noise made it worse than I8 (0.743, Brier 0.166).

## 3. Target (unchanged; not redefined after results)

**T43 (E43, Chapter I §1.7):** SWS self-rated hunger, Balance Luzon (regional), > 11.3% **AND** (provincial PSA food YoY > the province's 2021–2022 P60 **OR** food − headline YoY > its P60). Single quarter.
- Exploratory food-stress outcome, **not verified household food insecurity**.
- The thresholds still need adviser approval.

**What the target becomes in practice:**
- From 2023-Q4 onward, every quarter's H exceeds 11.3 (14.3–25.3), so on S44 **T43 equals the province price signal**.
- The hunger component matters only where H crosses 11.3 (2024-Q2, the EXT quarter).
- The gap thresholds are close to zero (−0.56 for Quezon to 0.92 for Rizal), so labels flip on small food-vs-headline moves.
- This makes T43 inherently hard two quarters ahead. It was **not changed**.

## 4. Data and feature audit (2021-Q3..2026-Q3 origins; no pre-2021 data, checked by parquet metadata before loading)

| Group | Inputs (geographic level) | Missing | Notes |
|---|---|---|---|
| Market and prices | M1 projection, food YoY now, food−headline gap, provincial deviation, wholesale rice YoY (provincial) | 0–20% (rice from 2022-Q2) | the only group with consistent signal |
| Climate and weather | typhoons ≤ 300 km and lag (provincial), ENSO and lag (national), palay and corn YoY (provincial), interactions | 0–14% | typhoons 50% non-zero |
| Fish kills and fisheries | fisheries and aquaculture production YoY (provincial) | 14% | **no official fish-kill event series exists**; production is a proxy |
| Employment and livelihood | unemployment and underemployment YoY (**national**) | 14% | identical for every province |
| OFW remittances | cash remittances USD and PHP YoY (**national**, curated BSP, ends 2025-Q4), USD/PHP YoY | 14–24% | identical for every province |
| News | province trigger shares and article count | 0% | OFW share always 0; employment share 1% non-zero |
| Rice policy (E46) | tariff regime, import suspension, price ceiling, food emergency (**national**, official EO/DA dates, as of announcement) | 0% | suspension and ceiling are 0 at every Lead-2 origin (section 1) |

- Missing values are median-imputed with missing-indicator flags inside the training folds. No unavailable value is treated as zero.
- No provincial observation was invented. National series are labelled national.
- Province codes were checked against all six sources.
- **Valid history cannot be expanded:** the study-window rule forbids pre-2021 data. Monthly origins would only add overlapping, non-independent targets.

## 5. Evaluation protocol

| Element | Rule |
|---|---|
| Origins | 2021-Q3..2026-Q3; Lead 2: issued after quarter t, target t+2 (dashboard rule: viewing Q4 2026 → latest completed Q3 2026 → target Q1 2027). |
| Inner selection | training targets ≤ t−1 only; embargoed forward chaining (I7–I10). |
| S44 | the E44 rows: targets 2024-Q3, 2024-Q4, 2025-Q1, 2025-Q4, 2026-Q1, 2026-Q2, 2026-Q3; 35 rows, 9 HIGH. 2025-Q2/Q3 have no approved SWS round, so T43 is undefined there. |
| EXT | S44 + 2024-Q2: 40 rows, 13 HIGH. |
| PRICE | the price signal alone, including 2025-Q2/Q3: 50 rows. |
| Gates (E44) | A0 leakage tests; A1 accuracy ≥ 0.75; A2 balanced ≥ 0.70 with both recalls ≥ 0.60; A3 Brier better than always-LOW and persistence; A4 calibration-in-the-large CI contains 0. |
| Final-candidate rule | gates + EXT ≥ 0.75 + minimum leave-one-quarter-out ≥ 0.70 (I8+: and Brier ≤ persistence-at-issue). |
| Uncertainty | date-cluster bootstrap (7 independent quarters, not 35 rows); paired date-level sign-flip tests with Holm correction. |

## 6. All serious candidates and baselines (S44, identical 35 rows)

| Arm | Acc (95% CI) | Bal | Rec H | Rec L | Prec H | F1 | Brier | AUC | TP/TN/FP/FN | Gates |
|---|---|---|---|---|---|---|---|---|---|---|
| **I7** corrected (O = day 1) | **0.800** (0.66–0.94) | 0.684 | 0.44 | 0.92 | 0.67 | 0.53 | 0.174 | 0.735 | 4/24/2/5 | fails A2 |
| **I8** = I7 at the 15th | 0.771 (0.57–0.94) | 0.665 | 0.44 | 0.88 | 0.57 | 0.50 | **0.132** | **0.902** | 4/23/3/5 | fails A2 |
| I9 = I8, cut at π | 0.571 (0.40–0.74) | 0.712 | 1.00 | 0.42 | 0.38 | 0.55 | 0.132 | 0.902 | 9/11/15/0 | fails A1, A2 |
| I10 = I8 + group selection | 0.743 (0.54–0.91) | 0.682 | 0.56 | 0.81 | 0.50 | 0.53 | 0.166 | 0.799 | 5/21/5/4 | fails A1, A2 |
| I6 = E44 I2 | 0.686 (0.46–0.89) | 0.716 | 0.78 | 0.65 | 0.44 | 0.56 | 0.181 | 0.603 | 7/17/9/2 | fails A1 |
| I6b (no national employment/OFW in hunger) | 0.686 | 0.679 | 0.67 | 0.69 | – | – | 0.165 | 0.675 | – | fails A1, A2 |
| *diag.* I8-MKT (market-only residual) | 0.800 | 0.756 | 0.67 | 0.85 | – | – | 0.140 | 0.889 | – | not eligible (market only) |
| *diag.* BASE-m0.5 (structural, fixed drift) | 0.829 | 0.776 | 0.67 | 0.88 | – | – | n/a | – | – | not eligible (picked in hindsight, no triggers) |
| *diag.* I7-BASE / I7-MKT / I7-INT / I7-LOQO | 0.771 / 0.743 / 0.657 / 0.457 | | | | | | | | | |
| always-LOW | 0.743 | 0.500 | 0.00 | 1.00 | – | – | 0.220 | – | 0/26/0/9 | |
| persistence (E44) | 0.543 | 0.583 | 0.67 | 0.50 | | | 0.457 | | | |
| persistence at the 15th | 0.600 | 0.585 | 0.56 | 0.62 | | | 0.400 | | | |
| SIM-0 | 0.771 | 0.628 | 0.33 | 0.92 | | | 0.176 | 0.701 | | |
| E41-M1 | 0.771 | 0.592 | 0.22 | 0.96 | | | 0.164 | 0.697 | | |
| E38 served (production) | 0.143 | 0.205 | | | | | 0.653 | | | |

**EXT (40 rows, 8 quarters, 13 HIGH):**

| Arm | Accuracy | Brier | AUC |
|---|---|---|---|
| I7 | 0.725 | 0.220 | 0.641 |
| I8 | 0.700 | 0.184 | 0.766 |
| I10 | 0.675 | | |
| I9 | 0.600 | | |
| I2 | 0.625 | | |
| always-LOW | 0.675 | | |
| persistence | 0.500 | | |
| BASE-m0.5 | 0.750 | | |

2024-Q2 (4 HIGH) is missed by every model: SWS hunger jumped from 10.3 to 19.6 with nothing anticipating it.

**PRICE (50 rows), price-signal accuracy:** I7 0.76, I8 0.76 (Brier 0.149 vs I7 0.190), BASE-m0.5 0.80.

**Paired date-level Brier gains:** I8 beats every comparator in mean Brier, but **none is significant after Holm** (7 quarters).

## 7. Per quarter and per province (S44)

**Accuracy per target quarter** (HIGH cases in brackets):

| Quarter (HIGH) | I7 | I8 | I2 |
|---|---|---|---|
| 2024-Q3 (1) | 1.0 | 1.0 | 0.8 |
| 2024-Q4 (3) | 0.6 | 0.6 | 0.6 |
| 2025-Q1 (4) | 0.6 | 0.4 | 0.8 |
| 2025-Q4 (0) | 1.0 | 1.0 | 0.2 |
| 2026-Q1 (0) | 1.0 | 1.0 | 1.0 |
| 2026-Q2 (1) | 0.6 | 0.4 | 0.4 |
| 2026-Q3 (0) | 0.8 | 1.0 | 1.0 |

**Robustness:**

| | Leave-one-quarter-out minimum | By province | Leave-one-province-out |
|---|---|---|---|
| I7 | 0.767 | Cavite 0.71, Laguna 0.71, Quezon 0.71, Rizal 1.00, Batangas 0.86 | 0.75–0.82 |
| I8 | 0.733 | Laguna 0.57, Cavite 0.71, others 0.86 | |

**Dependence on few cases:**
- 7 of the 9 HIGH rows fall in 2024-Q4 and 2025-Q1.
- I7 and I8 get 75–80% largely from correctly calling the 2025-Q4..2026-Q3 quarters LOW, where always-LOW also scores 0.95.
- Their errors are the gap-driven HIGHs of 2024-Q4/2025-Q1 and Cavite 2026-Q2 (food 4.73 against a 4.71 threshold).
- Accuracy therefore does rest on a few HIGH cases. This is why A2 is the binding gate.

## 8. Calibration, ranking and sensitivity

**Calibration and ranking** (`runs/calibration_i7_i8.json`):

| Candidate | AUC (date bootstrap) | Within-quarter AUC (18 pairs) | Between-quarter AUC | Slope | Intercept | Calibration-in-the-large |
|---|---|---|---|---|---|---|
| I8 | 0.902 (0.75–1.00) | 0.889 | 0.903 | 1.02 | −0.66 | −0.09 |
| I7 | 0.735 | 0.722 | | 0.54 | | |
| I2 | 0.603 | 0.667 | | 0.76 | | |

- **Within-quarter AUC** ranks provinces against each other in the same quarter. **Between-quarter AUC** mostly measures the timing of HIGH periods.
- **The ranking is genuine:** it holds within quarters, not just through period timing.
- **Probabilities slightly over-state risk on average.** In the reliability table, 5 of the 12 rows with p between 0.25 and 0.5 were HIGH. Those rows are where the fixed 0.5 cut loses recall, and the prevalence cut (π ≈ 0.2) adds 15 false alarms.
- **On EXT:** I8 AUC 0.766, slope 0.67.

**Sensitivity of I8** (`runs/sensitivity_i8.json`; the full variant reproduces I8 exactly):
- **S44 decisions:** unchanged under every drop-one variant. Inner validation chose "no residual" at most S44 origins, and P(hunger) ≈ 1.
- **Hunger component:**
  - Dropping national employment moves probabilities by < 0.001, so the E44/E45 employment dependence does not carry into I8.
  - A random-walk hunger component scores slightly better (Brier 0.122), so the five-trigger hunger ridge adds no measurable value.
- **2027-Q1 forecast** (α = 100 residuals selected):
  - Dropping climate lowers it by 0.04–0.32 and dropping market by 0.03–0.24.
  - Dropping employment raises it by 0.01–0.14, and dropping OFW lowers it by about 0.05.
  - No national proxy dominates.

## 9. Why 75% with discrimination is not reached: the evidence-based blocker

1. **Price-signal predictability.** The structural base-effect forecast, with no learning, is the strongest single predictor (PRICE accuracy 0.74–0.80). None of the five-trigger residuals (I7–I10) or the rice-policy features adds reliable out-of-sample skill. Reasons:
   - employment and OFW are national (one value for all five provinces);
   - there is no fish-kill event series;
   - news trigger shares are sparse;
   - the policy events that mattered (import suspension, price ceiling) were announced and expired within the Lead-2 horizon.
2. **A rare, threshold-sensitive target.** T43 on S44 is the price signal with near-zero gap thresholds. I8 ranks well (AUC 0.90), but with 9 HIGH cases the operating points trade HIGH recall against LOW recall:
   - p ≥ 0.5 gives recall 0.44 / 0.88;
   - p ≥ π gives 1.00 / 0.42.
   - A cut between them could look better on S44, but **choosing it on S44 is exactly the test-set tuning the protocol forbids.**
3. **No untouched historical evaluation exists.**
   - Every 2022–2026 quarter has been examined across E41–E46, and S44 has now been looked at about 12 times.
   - Valid history cannot be extended before 2021.
   - So a historical 75% could not count as independent validation, even if a model reached it.
   - The only valid evidence is prospective (2027-Q1..Q4).

## 10. Prospective record (frozen, sha256 in `frozen/`)

All target **2027-Q1**.

| Candidate | Issued (CPI through) | Cavite | Laguna | Quezon | Rizal | Batangas | Rule |
|---|---|---|---|---|---|---|---|
| I8 | 2026-10-15 (Sep 2026; SWS 2026-Q3) | **0.717** | 0.374 | 0.452 | 0.492 | 0.126 | HIGH iff p ≥ 0.5 → Cavite HIGH |
| I9 | same p | | | | | | cut 0.20 → all HIGH except Batangas |
| I10 | 2026-10-15 | 0.501 | 0.372 | 0.430 | 0.425 | 0.151 | |
| I7 | 2026-10-01 (Aug 2026) | 0.061 | 0.051 | 0.146 | 0.030 | 0.039 | |
| I6 = I2 | 2026-10-01 | 0.193 | 0.197 | 0.210 | 0.191 | 0.196 | |

Acceptance (PROTOCOL §5) requires all of the following over 2027-Q1..Q4 (20 province-quarters):
- accuracy ≥ 0.75;
- balanced accuracy ≥ 0.70;
- both recalls ≥ 0.60;
- Brier better than always-LOW and persistence.

## 11. Changes, files, tests, reproduction

**New in E46 (experiment folder `aipheed-backend-aligned/experiments/E46_Rice_Policy/`):**
- `ADDENDUM_I7.md`, `ADDENDUM_I8.md`, `ADDENDUM_I9.md`, `ADDENDUM_I10.md` (+ `runner/*_SHA256.txt`)
- `runner/e46_i7.py`, `e46_i8.py`, `e46_i10.py`
- `runner/e46_evaluate_i7.py` / `_i8` / `_i9` / `_i10`
- `runner/e46_asof_check.py`, `e46_gap_defect.py`, `e46_calibration.py`, `e46_sensitivity.py`
- `tests/test_e46_i7.py` (4), `test_e46_i8.py` (3, separate interpreters), `test_e46_i10.py` (2), `test_e46_gap_defect.py` (2), plus the earlier `test_e46.py` (6)
- runs: `20261016T225203Z` (+ repeat `20261016T234337Z`), `i7_20261017T000111Z`, `i8_20261017T001227Z`, `i9_20261017T005904Z`, `i10_20261017T010426Z`, and their repeats (see `REPEATS.md`)

**Backend:**
- `app/api/v1/forecast.py`, `app/ml/inference/e41_lead2.py`: the trend line uses one score type, the candidate's own as-of backtest.
- `scripts/build_record_e44.py` and `data/e44/e44_record.json`: known-defect warning; probabilities unchanged.
- Tests: `tests/integration/test_e44_final_candidate.py` (+ trend-line test), `test_e42_lead2.py`.

**Reports:** correction notes appended to the E44 and E45 FINAL_REPORTs. The original text is kept.

**Commands** (from `E46_Rice_Policy/`, with `PY=backend/venv/Scripts/python.exe`):

```
$PY -B runner/e46_evaluate.py          # I6 / I6b / I6-MKT
$PY -B runner/e46_evaluate_i7.py       # I7 + diagnostics
$PY -B runner/e46_evaluate_i8.py       # I8 (15th-of-month issue time)
$PY -B runner/e46_evaluate_i9.py       # I9 (prevalence cut, no refit)
$PY -B runner/e46_evaluate_i10.py      # I10 (group selection)
$PY -B runner/e46_asof_check.py; $PY -B runner/e46_gap_defect.py; $PY -B runner/e46_calibration.py; $PY -B runner/e46_sensitivity.py
$PY -B -m pytest -q tests/test_e46.py tests/test_e46_i7.py tests/test_e46_gap_defect.py
$PY -B -m pytest -q tests/test_e46_i8.py tests/test_e46_i10.py
```

## 12. Limitations and what prospective confirmation needs

**Limitations:**
- **Few independent quarters:** 7 on S44, 9 HIGH. Accuracy CIs are about ±0.17, and no paired difference is significant.
- **Hindsight:** every E46 historical score is hindsight-informed.
- **Target:** T43 is regional for hunger, near-threshold for the gap, and awaits adviser approval.
- **Trigger data:** employment, OFW and policy inputs are national; there is no fish-kill event series; the remittance series ends 2025-Q4.
- **Issue time:** I8's 15th-of-month timing matches the deployed scheduler but differs from the E41–E44 convention. Adopting it is the user's decision.

**Needed for confirmation:**
1. Score the frozen 2027-Q1..Q4 forecasts as outcomes are released (PSA CPI monthly; SWS rounds), with no reselection.
2. **Provincial** hunger/FIES, labour and remittance series, so the non-market triggers can carry provincial signal.
3. An official fish-kill and rice-policy event register, maintained as of announcement dates.
4. Adviser decision on T43's thresholds, and on whether the decision cut should weight missed HIGHs more than false alarms. This is a policy cost choice, to be fixed **before** any further outcomes are seen.


---

## 13. Observed-vs-forecast discrepancy (investigated and fixed; commit d1b17aa)

**Symptom:** with a Lead-2 candidate enabled, the dashboard showed "Observed" quarters near 0.98 and the forecast near 0.20.

**Root cause: an invalid comparison between two different measures, created in the backend API.**
- `app/services/dashboard.py::_province_forecasts_cached` swapped in the candidate only for its exact target quarter (2027-Q1).
- Every other quarter fell through to the E31/E36 engine.
- That engine reports the LightGBM probability of the **v1 label**: S1 = SWS hunger + 2 × the province's food-CPI deviation, HIGH when S1 is above the trailing median.
- With SWS hunger at 14–25% since 2023-Q4, S1 is almost always above its trailing median, so that probability sits at about 0.98.
- The 2027-Q1 value was the E44 probability of **T43**, a fixed-threshold event that was LOW in all five provinces in 2026-Q3.

So the timeline joined two models and two target events. Further points:
- **"Observed" was a misnomer:** the timeline tags quarters before today as "Observed" by calendar position (`QuarterTimeSlider.tsx`). Those values were model backtest estimates, not observations.
- **Scope of my earlier fix:** the E46 trend-line fix covered only `/forecast/timeseries`. It did not cover the timeline, province cards, map or explainability.
- **Not the cause:** the model, the data, CPI transformations, calibration, or the frontend field mapping. Each was checked: the frontend shows `riskScore`, exactly as served.
- **Default (E38) mode was consistent all along:** every quarter, 2027-Q1 included, shows the v1-label probability (0.80–0.95).

**Province audit** (`runs/observed_vs_forecast_audit.json`; latest observed quarter 2026-Q3; SWS 23.6%, posted 2026-10-14):

| Province | Food YoY | Headline YoY | Gap (P60 ref.) | Observed T43 | v1 observed (S1) | Shown "Observed" 2026-Q3, before | Candidate backtest 2026-Q3 (same event) | 2027-Q1 uncalibrated p_H × p_price | 2027-Q1 calibrated (shown) |
|---|---|---|---|---|---|---|---|---|---|
| Cavite | 3.83 (ref 4.71) | 5.23 | −1.40 (0.74) | LOW | HIGH (24.5) | 0.9841 | 0.261 | 0.249 | 0.193 |
| Laguna | 3.63 (6.05) | 7.33 | −3.70 (0.61) | LOW | HIGH (24.1) | 0.9987 | 0.233 | 0.292 | 0.197 |
| Quezon | 4.53 (6.24) | 6.50 | −1.97 (−0.56) | LOW | HIGH (25.9) | 0.9952 | 0.300 | 0.464 | 0.210 |
| Rizal | 4.07 (7.10) | 7.10 | −3.03 (0.92) | LOW | HIGH (25.0) | 0.9846 | 0.227 | 0.224 | 0.191 |
| Batangas | 0.73 (7.15) | 4.80 | −4.07 (0.66) | LOW | HIGH (18.3) | 0.9953 | 0.200 | 0.287 | 0.196 |

All 2027-Q1 values in this table are `e44` mode, i.e. the I2 candidate.

- **Like-for-like:** backtest 0.20–0.30 → forecast 0.19–0.21, differences of −0.01 to −0.09, and the observed T43 outcome was LOW everywhere.
- **The "high observed" value was the v1-label model probability**, not an observation of the forecast's event.

**Fix (backend; the approved frontend design is unchanged):**
- `e41_lead2.governs()`, `rows_for()` and `candidate_quarters()`: while a candidate's record is for the dashboard's current target, **every quarter** shows the candidate's own estimate of its own event:
  - the as-of backtest for past quarters, with `estimateKind: "backtest"` and `observedOutcome` HIGH/LOW;
  - the earlier Lead-2 forecast for 2026-Q4 (issued 2026-07-01, `earlier_forecast`);
  - the issued forecast for 2027-Q1.
- Quarters without a candidate estimate are `unavailable`, with a reason, and return 404. They are never filled with another model's score.
- This applies to the province cards, the map and the 142 LGUs (derived from the province score), the region mean, quarter-on-quarter changes, the trend line and the indicator.
- **Explainability for backtest quarters:** new status `not_recorded`, with neutral copy (text only). Attributions exist only for the issued forecast.
- **Records:** the E44 and E46 records now carry `earlierForecasts`.
- **Tests:**
  - `tests/integration/test_e46_observed_vs_forecast.py` (5): one score on every timeline quarter; the v1 value never appears; unavailable quarters; trend = cards = map; triggers `not_recorded`; default unchanged.
  - Four older tests that asserted the old mixed behaviour were updated.

**After the fix:**
- **`e44` mode, 2026-Q1 → 2027-Q1** (by province): Cavite 0.291, 0.210, 0.261, 0.221, 0.193; Batangas 0.385, 0.195, 0.200, 0.216, 0.196.
- **`e46` mode (the corrected model):**
  - 2026-Q3 backtest: Quezon 0.852 (observed LOW, a false alarm), Cavite 0.449, the others 0.06–0.10;
  - 2026-Q4 earlier forecast: 0.001–0.281;
  - 2027-Q1 forecast: 0.030–0.146.

## 14. Finalization: verification of the corrected model

**1. Evidence preserved:**
- The E44 and E45 results are intact, with correction notes appended.
- I6–I10, their runs, repeats, addenda, protocol hashes and every frozen file are unchanged. All frozen sha256 files still verify (tests).

**2. Independent validation: not available historically.**
- The S44 outcomes, and every other 2022–2026 quarter, were examined while diagnosing D1–D6.
- So **no historical evaluation can count as independent**. The study window forbids pre-2021 data, and no quarter after 2026-Q3 has an outcome yet.
- The corrected model's 0.800 is **development evidence only**.
- **The independent evaluation is prospective and frozen:**
  - I7: `frozen/E46_I7_PROSPECTIVE_2027Q1.json`, sha256 `5592d53e…3241e`;
  - I8: sha256 `284f23f2…770`;
  - acceptance per PROTOCOL §5 over 2027-Q1..Q4 (20 province-quarters).
- **When it can be scored:** the first outcome (2027-Q1) needs PSA's March 2027 CPI (about early April 2027) and SWS's 2027-Q1 hunger round.

**3. Acceptance metrics, corrected model I7** (development; S44 35 rows, 7 quarters, 9 HIGH):

| Metric | Value |
|---|---|
| Accuracy | 0.800 (date-cluster 95% CI 0.66–0.94) |
| Balanced accuracy | 0.684 |
| HIGH recall | 0.44 |
| LOW recall | 0.92 |
| Precision (HIGH) | 0.67 |
| F1 (HIGH) | 0.53 |
| Confusion | TP 4, TN 24, FP 2, FN 5 |
| Brier | 0.174 |
| AUC | 0.735 (CI 0.46–0.95) |
| EXT (40 rows) | 0.725 |

- **It does not predict only LOW:** it made 6 HIGH calls, 4 of them correct.
- **But its margin over always-LOW is small:** 0.800 vs 0.743, which is 2 rows.
- **The discrimination gate fails:** HIGH recall 0.44 < 0.60.

**4. I8 (corrected price component + 15th-of-month issue time):**
- **The correction is already inside I8.** I8 = I7 + issue timing, so its AUC 0.902 and Brier 0.132 are post-correction values, not pre-correction ones.
- **Ranking:** within-quarter AUC 0.889 (18 pairs), so it ranks provinces within the same quarter, not just HIGH periods. The AUC date-bootstrap CI is 0.75–1.00.
- **Calibration:** slope 1.02 and intercept −0.66, so probabilities slightly over-state on average (calibration-in-the-large −0.09).
- **Effect of the timing:** with the same corrected formula, the extra CPI month moves AUC 0.735 → 0.902 and Brier 0.174 → 0.132.
- **EXT:** AUC 0.766, slope 0.67.

**5. Stability (I7, S44):**
- **By quarter:** 2024-Q3 1.0, 2024-Q4 0.6, 2025-Q1 0.6, 2025-Q4 1.0, 2026-Q1 1.0, 2026-Q2 0.6, 2026-Q3 0.8.
- **By province:** Cavite 0.71, Laguna 0.71, Quezon 0.71, Rizal 1.00, Batangas 0.86.
- **Leave-one-quarter-out:** minimum 0.767. **Leave-one-province-out:** 0.75–0.82.
- **Where the score comes from:**
  - 7 of the 9 HIGH rows fall in 2024-Q4/2025-Q1, which is where I7's misses are.
  - Most of its accuracy comes from the LOW quarters 2025-Q4..2026-Q3.
  - Rizal's 1.00 reflects that Rizal was never HIGH.
- **So the performance is concentrated in a few periods and HIGH cases.**

**6. Frozen 2027-Q1 forecast, corrected formula (a FORECAST; outcome unknown):**
- **Model version:** E46-I7 (ADDENDUM_I7 sha256 `ed0db548…455c`). Issued as of **2026-10-01**: CPI through 2026-08; SWS rounds posted by 2026-08-24, latest quarter 2026-Q2.
- **Probabilities:** Cavite 0.061, Laguna 0.051, Quezon 0.146, Rizal 0.030, Batangas 0.039. All LOW at p ≥ 0.5.
- **Inputs were available at the origin:** `runner/e46_asof_check_i7.py` deleted every observation published on or after each origin (2024-Q2, 2025-Q2, 2026-Q1, 2026-Q2, 2026-Q3) and rebuilt. Forecasts are identical (|Δp| ≤ 1e-16); the 2027-Q1 forecast equals the frozen file exactly (Δ = 0).
- **Served behind `AIPHEED_LEAD2_MODEL=e46`:** record `backend/data/e46/e46_record.json`, built by `scripts/build_record_e46.py`. The refit must reproduce the frozen probabilities, and it does to 1e-9.
- **For comparison:** I8, issued 2026-10-15 with Sep 2026 CPI, calls Cavite HIGH (0.717).

**7. Dashboard (live, `e46` mode, fresh servers 8001/8082):**

| Check | Result |
|---|---|
| Target and timing | 2027-Q1, issued 2026-10-01, Lead 2 from 2026-Q3 |
| One score type on every timeline quarter | yes; backtest quarters carry their observed outcome |
| Municipalities | 142/142 carry a band; Laguna drill-down draws 30 LGUs in the approved palette |
| News | 10 articles listed |
| Five trigger groups | each with status and evidence (Cavite 2027-Q1: market 43%, climate 29%, employment 26%, OFW 2%, fish 0% no_effect) |
| Trend line | one series of one score, 2024-Q2 → 2027-Q1 |
| Suites | backend **356 passed / 18 skipped**; frontend **36 passed**; E46 experiment tests 17 passed |

Cosmetic note: the quarter-on-quarter "+295%" for Laguna is a relative change between two small probabilities (0.013 → 0.051). It is correct but easy to over-read; the approved UI was left as designed.

**8. The 75% requirement: NOT met.**

| Candidate | Accuracy | Discrimination | Status |
|---|---|---|---|
| I7 (served, corrected) | 0.800 | HIGH recall 0.44 | development evidence |
| I8 | 0.771 | best ranking (AUC 0.90), same recall problem at p ≥ 0.5 | development evidence |

- No defensible independent evaluation exists yet.
- **The next valid evidence is prospective:** score the frozen I7/I8 forecasts as 2027-Q1..Q4 outcomes are released, with no reselection.

**Commits (branch `e46-lead2-policy`):** 98c819c, 7a2c31a, a86da6d, 77ef9dc, e2a297a, 4f6d01d, 8a8ddc3, eea3781, dd16aa6, d1b17aa (discrepancy fix), 9448ed0 (corrected forecast served), plus this report commit.
