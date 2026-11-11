# E178: synthetic scenario data (Part A) and synthetic-augmented retraining (Part B). Fixed before results.

Written 2026-11-09, before any E178 output existed. Committed first on branch `feature/e178-synthetic-scenarios`.
Nothing in this experiment changes the served model, the registry or any E168 file.

## Honesty statement
- The 72 outer rows (ENNS2018, 2019 and 2021 at Leads 1 and 2) have been read by E151–E168. E178 is retrospective
  evidence on rows that are already known, like E168.
- **Part A** feeds synthetic *inputs* through the frozen E168 procedure. Its numbers are demonstrations of how the
  system responds, not forecasts and not validation evidence.
- **Part B** is run once with the settings below. Its result is reported whatever it is. If synthetic augmentation does
  not beat E168 under the decision rule, the conclusion is "synthetic augmentation did not improve the model", and E168
  stays in production. **Even if E178 passes, it is not promoted. Promotion is the owner's decision.**

## Rules that apply to both parts
1. **Production untouched.** No change to `backend/app/e168/*`, `backend/data/e168/out/*`, `backend/data/e168/issues/*` or
   `backend/data/registry/*`. `AIPHEED_STRICT_MODEL=1` must keep working. Nothing is registered or promoted.
2. **Labelling.**
   - Every synthetic row carries `is_synthetic=True`, a `scenario_id` and a `generator_seed`.
   - Every synthetic file is written under a folder named `synthetic/`.
   - Every UI view, chart and report section that shows synthetic data carries the label **SYNTHETIC – FOR DEMONSTRATION**.
   - S0 rows use real inputs and carry `is_synthetic=False`.
3. **Separation.**
   - Synthetic rows never enter any validation, test or calibration-scoring set. That includes inner validation folds,
     out-of-fold errors, calibration fitting and the outer rows.
   - Every reported accuracy, Brier score, recall or similar metric is computed only on the 72 real chronological outer
     rows per lead.
4. **Time validity.** Part B generates synthetic training rows inside each outer fold, from that fold's training rows
   only. These come from `M.released`/`M.Pipeline`, so only data released before the fold's origin is used.
5. **Reproducibility.**
   - LightGBM seed 168, as E168.
   - Scenario seeds 17810–17829; generator seeds 17801–17805.
   - Run logs (`run_log.jsonl`) and SHA-256 hashes (`hashes.json`) of the outputs, inputs and code.

## Inputs and their provenance
- **Live issue reproduced by Part A:** the registry's production artifact
  `backend/data/e168/issues/2026-Q4_2026-11-01/live.json`.
  - Information cut-off 2026-11-01; data published by 2026-11-08.
  - The procedure runs with `AIPHEED_LIVE_ASOF=2026-11-01` and `AIPHEED_LIVE_PUBLISHED=2026-11-08`, set before any
    pipeline import (subprocess), as `app.e168.live_refresh` does.
  - The input hashes recorded in the issue's manifest (provincial panel, news panel, HFIAS) are re-checked at run time.
- **Gitignored raw inputs.**
  - `backend/data/e154/raw/regional_income_long.csv` (PSA regional consumption) is gitignored. It was supplied by the
    owner, and its SHA-256 equals the locked value in `backend/data/e154/out/lock.json`
    (`6bff3d80f49c0c12db48bd2aa92ddd6f798e093ad1991c002143e334e4d05888`).
  - `backend/data/e155/raw/sunstar.parquet` (SunStar headlines) is gitignored and not available. Its columns (`sun_*`)
    are merged into the frame by `N.add_sources`, but they are in **no** E168 feature set and **no** trigger list. An
    empty panel with the same columns is used instead.
  - This is accepted only if E168 reproduces bit-for-bit: S0 against the production artifact, and Part B's
    no-augmentation run against `backend/data/e168/out/all_rows.csv`. If it does not, the run stops.
- **Feature bounds.**
  - The brief named `e152/out/local_panel.parquet`, but E168 uses none of its columns (`l_*`, `r_*`). The model's
    features come from `e148/out/gov_panel.parquet`, the news panels and income.
  - Bounds are therefore the per-feature minimum and maximum over the **real as-of feature rows that the frozen
    procedure builds at the live issue**: all training rows (every released survey row, all provinces nationwide,
    Leads 1–8) plus the five live rows. This is also the range the trees were fitted on.

---

# Part A: scenario inputs through the frozen E168 procedure

## Procedure
- For each lead 1–3, `app.e168.serve._forecast(lead, "2026-Q4")` runs unchanged. Its call to
  `app.e168.lgbm_only.run_proc(tr, te, AN)` is wrapped only to capture `(tr, te, AN)`.
- Every scenario variant is a copy of the five live rows `te` with some input columns changed. Each copy carries the same
  test-anchor values, tiled. All variants of a lead are stacked into one frame and passed to the **original** `run_proc`
  with the same `tr` and `AN`.
- This is exact because the configuration, pruning, final model, calibration and the 90 % scale depend only on `tr`. A
  test row's output depends only on that row.
- Drivers: SHAP values per trigger group, from LightGBM `pred_contrib` on the final model. The group mapping is
  `app.e168.dashboard_export` (`GROUPS`, `OWN_BAR`, `BARS`), the same as the dashboard.
- Output per row: province, issue, target quarter, lead, `scenario_id`, variant, `score_pct`, 90 % range, `p_high`,
  `risk_class` (HIGH when `p_high` ≥ 0.5), top-3 drivers, `is_synthetic`, `generator_seed`, `extrapolated`, `clipped`.

## Trigger groups and stress directions
Official-statistics columns only. News columns, `h2`, `gap_q` and `lead` are never changed in S1 and S3.

| Group (panel name) | Columns | Stress direction |
|---|---|---|
| Weather and farm | `c_tc_4q`, `tc_rate_since` | + (`Pv.SIGN`) |
| | `c_agri_yoy`, `agri_since` | − (`Pv.SIGN`) |
| | `oni` | + (El Niño; unsigned in the model) |
| | `c_rain_anom_6m`, `c_soil_anom_3m`, `rain_since`, `soil_since` | − (drought; unsigned in the model) |
| Food prices | `cpi_food_yoy`, `cpi_rice_yoy`, `cpi_food_3m`, `cpi_food_accel`, `cpi_since` | + (`Pv.SIGN`) |
| | `cpi_food_rel_nat` | + (unsigned in the model) |
| Jobs | `unemp_rate`, `unemp_yoy`, `unemp_chg_since`, `unemp_region` | + (`Pv.SIGN`) |
| Remittances | `remit_yoy`, `remit_since`, `remit_q_yoy` | − (`Pv.SIGN`) |
| Fish catch | `c_fish_yoy` | − (`Pv.SIGN`) |

- A column is changed only where the live row has a value. Missing values stay missing.
- `SD` is the column's standard deviation over the bound rows above.

## Scenarios
| ID | Variants | Rule |
|---|---|---|
| **S0** | 1 | Real inputs. **Must equal the production artifact exactly**: score, P(HIGH), class and 90 % range for all 15 province × lead rows, and the dashboard rows' SHAP columns. |
| **S1** | 5 groups × k ∈ {−2, −1, +1, +2}, plus 100 noise draws | Shift each column of one group by k·SD in its stress direction (k < 0 is relief). Clip to bounds and record `clipped`. Noise: every column of all five groups gets an independent N(0, SD) draw, clipped. Seed 17810. |
| **S2** | 3 fractions × 20 masks, plus all triggers missing, plus latest survey missing | Set a random 25 %, 50 % or 75 % of each live row's trigger cells (`lgbm_only.TRIG`, the columns the shuffle control uses) to NaN, which is what production does when a source is missing. Seeds 17811–17813. "All triggers missing" sets every trigger cell to NaN. "Latest survey missing" re-runs the frozen procedure with ENNS2021 removed from the survey rows, by patching `Pv.target_rows(with_2021=True)` to return the rows without it. |
| **S3** | 7 shocks × t ∈ {0.25, 0.5, 0.75, 1.0, 1.25, 1.5} | Shocks: typhoon (`c_tc_4q`, `tc_rate_since` up; `c_agri_yoy`, `agri_since` down); El Niño drought (`oni` up; rainfall and soil anomalies and their since-survey means down; `c_agri_yoy`, `agri_since` down); rice and food price spike (the food-price group); job loss (jobs group); remittance drop (remittances group); low fish catch; and all of them combined. Each live value x₀ moves toward the historical extreme in its stress direction: x(t) = x₀ + t·(x_ext − x₀). t = 1 reaches the extreme. t > 1 is extrapolation, flagged `extrapolated=True` and logged. The shock hits all five provinces together. Reported: the smallest t at which at least one province reaches P(HIGH) ≥ 0.5. |
| **S3-B** | only if no S3 variant reaches 0.5 | Combined shock at t = 1.0, plus a **hypothetical higher survey baseline**: the test-anchor values of every anchor (H, OH, RSS) are raised by δ ∈ {0.1, 0.2, …, 2.0} logit until at least one province reaches 0.5. Labelled as a hypothetical worse latest survey, not a re-estimated survey. |
| **S4** | from S3 (or S3-B) | The first variant that turns a province HIGH at Lead 1: smallest t, then shock order as listed (typhoon first, combined last), or the smallest δ for S3-B. Its rows at Leads 1–3 are used. In the offline CLI process only, `app.ml.inference.e168_system.rows` and `state_token` are temporarily replaced by those synthetic rows, and the dashboard caches are cleared before and after. The run records: `alerts_e168.candidates()`; `e168_system.drivers`, `plain_evidence` and `evidence_note`; `province_row(...)["confidence_statement"]` (the report sentence); and the province ranking. The review flow is described from `app/api/v1/alerts.py`: a candidate is staged, then confirmed or dismissed by a DA administrator. **Nothing is written to the database.** |
| **S5** | from S4 | With the same temporary rows, `app.services.dashboard.municipality_summary(quarter, province_id)` for each HIGH province. The run lists its highest-ranked cities and municipalities with `disaggregationLabel` and the note "reweighted provincial estimate, not a municipal forecast". |

## What Part A must show (checked by tests)
- S0 equals production exactly.
- Every `p_high` is within 0–1, and every `risk_class` matches `p_high ≥ 0.5`.
- S3 (or S3-B) yields at least one HIGH.
- Every changed input lies within bounds unless the row is flagged `extrapolated`.
- Every row carries the labels.
- Real endpoints never return synthetic rows.

## Serving the scenarios
- `GET /api/v1/demo/scenarios` and `GET /api/v1/demo/scenarios/{scenario_id}`: administrator login required (the demo
  account included). The endpoints read only `backend/data/e178/synthetic/`, and every response carries `synthetic: true`
  and the label.
- The frontend "Scenario / Demo mode" toggle is off by default, kept only for the browser session, and offered only in
  the administrator area. Public pages never read it.

---

# Part B: E178, synthetic-augmented E168 (candidate only)

## What stays exactly as E168
- Outer jobs: ENNS2018, 2019 and 2021 at Leads 1 and 2 (`lgbm_only.task`: `Store2`, `M.released`, `M.Pipeline`,
  `Pv.add_inputs`, `N.add_sources`, `A4.anchors`).
- Anchors {H, OH, RSS}; feature sets {GOV, FULL, GOV+cons, FULL+cons} × prune {False, True}; HPO grid
  `num_leaves` {3, 7} × `min_child_samples` {10, 40} × `reg_lambda` {5, 20} × `n_estimators` {150, 400}.
- Fixed LightGBM parameters; monotone constraints from `Pv.SIGN`; seed 168.
- Real-row weight `1/(se² + 0.05)`; no class weighting; threshold 0.5.
- Inner region GroupKFold(5), scored by weighted logit SSE on real rows.
- Calibration layers {raw, linear, soft Platt}, cross-fitted on inner out-of-fold forecasts of real rows, chosen by
  lowest inner Brier.

## The only change: synthetic training rows
- **Where.** In each inner fold, synthetic rows are generated from that fold's real training rows and added to that
  fold's fit set only. For the final model, they are generated from the outer job's real training rows. Synthetic rows
  are never predicted for scoring, never in out-of-fold errors, never in the variance scale and never in calibration.
- **Weight.** `0.4 × 1/(se'² + 0.05)`, fixed in advance and not tuned.
- **Ratio.** r ∈ {0.25, 0.5, 1.0}, so `n_syn = round(r · n_real)`. The generator and r are chosen **only** by the inner
  selection, jointly with the anchor, feature set, pruning and HPO, by the same weighted real-row SSE.
- **Column filter and pruning.** The `notna().any()` and `nunique() > 1` filter and the Spearman > 0.95 pruning are
  computed on real rows only.
- **Balancing.** Class = HIGH when `y_true ≥ 0` (share ≥ 50 %). The synthetic budget goes first to the minority class
  until the classes are equal, and the remainder is split by the classes' real shares. Parents are drawn uniformly with
  replacement within the class. Class counts before and after are logged per fold.
- **Every synthetic row carries:**
  - the parent's (or interpolated) anchors for H, OH and RSS;
  - `y'`, `se'`, `q' = Φ(y'/se')` and `e' = y' − anchor`;
  - `is_synthetic=True`, `scenario_id` (`B:<generator>:r<r>`) and `generator_seed`.

## Generators
- **`jitter` (a):**
  - Target: `y' = y + N(0, se_true²)`, on the logit scale.
  - Inputs: `x' = x + N(0, (0.25·SD)²)`, where SD is the column's SD in the rows given, clipped to their min/max.
  - Copied from the parent instead of jittered: NaN values; columns with ≤ 10 distinct values; columns whose most common
    value covers ≥ 50 % of rows (such as zero-inflated news counts); and `lead`, `gap_q`, `se_true` and the anchors.
- **`smote` (b):**
  - For a parent, choose one of its k = 5 nearest neighbours of the same class and the same lead. Distance is Euclidean
    on columns standardized by the rows' SD, with NaN treated as 0 (the mean).
  - With one λ ~ U(0, 1) per synthetic row, interpolate all inputs, `y`, `se_true`, the anchors and `gap_q` (rounded).
    Where either value is NaN, the parent's value is kept.
  - Same-class neighbours keep the class, and convex combinations stay within bounds.
  - If a class-and-lead cell has fewer than 2 rows, its parents are copied with jitter instead (logged).
- **Seeds.** A seed sequence of (generator seed, outer job, inner fold or "final", generator, r) keeps every draw
  reproducible under parallel execution. The primary generator seed is 17801. Seeds 17801–17805 are the stability runs.

## Fidelity checks (Stage 1, before evaluation)
- **When.** For each generator, on each of the six outer jobs' real training rows, at r = 1.0 and seed 17801.
- **Primary criteria.** Comparisons are made within class (HIGH, LOW), weighted by the synthetic class counts, so the
  intended rebalancing is not counted as infidelity.

| Check | Pass rule |
|---|---|
| KS statistic per feature (two-sample, non-missing values) | median over features ≤ 0.15 |
| Wasserstein-1 per feature, divided by the real SD | maximum over features ≤ 0.50 |
| Spearman correlation matrix | mean absolute difference ≤ 0.10 |
| Train on synthetic, test on real (TSTR) | Region GroupKFold(5) inside the training rows: LightGBM (anchor OH, GOV, prune, 3 leaves, `min_child_samples` 10, λ 20, 150 trees) fitted on synthetic rows generated from the other regions only, predicting the held-out real regions. Weighted SSE ratio TSTR/TRTR ≤ 1.25 |
| Not copies (distance to the closest real record, standardized) | ≤ 10 % of synthetic rows closer than 0.05 × the median real-to-real leave-one-out nearest-neighbour distance, and no exact duplicate |

- **Descriptive only.** For each `Pv.SIGN` column, whether its Spearman correlation with e has the same sign in
  synthetic and real rows.
- **A generator that fails any primary criterion in any of the six jobs is rejected** and removed from the Stage 2 menu.
  If both are rejected, Stage 2 is not run, and the result is "no synthetic generator met the fidelity criteria".

## Evaluation (Stage 2)
- **Jobs.** Six main jobs (3 surveys × 2 leads) at generator seeds 17801–17805. Lead 1 controls at seed 17801:
  - `shuf1`–`shuf3`: `C.shuffle_cols` on the trigger columns, applied before augmentation, so synthetic rows are made
    from shuffled rows;
  - `corrupt`: unreleased rounds' `y` replaced by noise before `M.Pipeline`.
- **Arms.**
  - **E178** (primary): the inner-selected generator and r, at seed 17801.
  - Descriptive: each generator with its own inner-selected r, and each generator × fixed r.
  - Comparators: **E168** (`backend/data/e168/out/all_rows.csv`) and **PERS** (`backend/data/e158/out/oof.csv`).
- **Code path.** As `lgbm_only.evaluate`: merge with `e158/out/oof.csv`, `assert len(x) == 72`, `C.cls_metrics`,
  `F5.prob_cal` and reliability bins [0, .2, .4, .6, .8, 1].
- **Metrics at Leads 1 and 2.** Accuracy, balanced accuracy, HIGH recall and precision, F1, macro-F1, AUC, Brier, and
  calibration slope with CI, plus the reliability table.
- **Comparisons.**
  - Paired region-cluster bootstrap CI of the Brier difference E178 − E168 (`E7.diff_ci`, 2,000 draws, rng 178).
  - Exact McNemar test (binomial on discordant pairs).
  - Leakage = max |mu − mu_corrupt| at Lead 1.
  - Shuffled: E178 − mean(shuf1–3) Brier CI.
- **Stability.** Mean ± SD of each metric over seeds 17801–17805, and the number of seeds that meet the decision rule.
- **Equivalence check.** With augmentation switched off, the E178 code must reproduce `lgbm_only.run_proc` and the E168
  rows bit-for-bit (unit test and a logged full re-run).

## Decision rule (fixed now; strict reading)
E178 is **"better than E168"** only if **all** of these hold for the primary arm (seed 17801):
1. The upper bound of the Brier-difference CI (E178 − E168) is **< 0 at Lead 1 and at Lead 2**.
2. Accuracy is **≥ E168's at Lead 1 and at Lead 2** (E168: 0.750 and 0.778).
3. Leakage is **< 1e-9**.
4. **It beats shuffled**: the upper bound of the E178 − shuffled Brier CI is < 0.

Otherwise the conclusion is **"synthetic augmentation did not improve the model"**. E168 stays in production in either
case until the owner decides. If E178 passes, a staging command (`python -m app.e178.candidate stage`) is prepared
that writes a candidate artifact under `backend/data/e178/candidate/`. It is never promoted by this work.

## Outputs
- **Part A:** in `backend/data/e178/synthetic/`: `scenarios_inputs.csv`, `scenarios_outputs.csv`, `s4_response.json`,
  `s5_municipal.csv`, `run_log.jsonl` and `hashes.json`. The report is `docs/e178/SCENARIO_TEST_REPORT.md`.
- **Part B:**
  - In `backend/data/e178/out/`: `fidelity.json`, `balance.csv`, `all_rows.csv`, `results.json`, `run_log.jsonl` and
    `hashes.json`.
  - Final-fit synthetic training rows of the primary seed go to `backend/data/e178/synthetic/train/`.
  - The report is `docs/e178/AUGMENTATION_REPORT.md`.
