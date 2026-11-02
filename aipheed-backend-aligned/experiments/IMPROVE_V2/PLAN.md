# IMPROVE_V2: improving the food-insecurity forecast for CALABARZON (EXPLORATORY)

**Written:** 2026-11-03, before any model, baseline or label in this folder was computed.

**Label: EXPLORATORY.**

**Evidence status, stated plainly.** Every target quarter scored here (2010-Q1..2026-Q3) was already examined in
HISTORY_RETRAIN (plan `6b9f17fb…`, results `b758588`), and 2021–2026 in many earlier experiments. Any gain found here
is **weak evidence**: the three improvements were proposed knowing how the reference behaved on these quarters. **The
only clean test is the sealed 2027+ forecasts (§10).**

**What this does not change:**
- the served model (P0H4), the dashboard, the frontend, `backend/`;
- `backend/seals/PREREG_LEAD2.md`, its addenda, and every existing seal;
- HISTORY_RETRAIN, including its results;
- any file outside `aipheed-backend-aligned/experiments/IMPROVE_V2/`.

Other folders and `backend/app` are read or imported read-only, with `sys.dont_write_bytecode = True`. Nothing is pushed
to GitHub; commits are local only.

**Hash.** The SHA-256 of this file is computed over every byte before its last line, which begins `PLAN-SHA256:`. The
runner refuses to run if the file changed after hashing.

**Read before writing this plan:**
- `FINAL_ARCHITECTURE/METHODOLOGY_WORKFLOW_CH3.md` (Chapter 3);
- `docs/final_system/THESIS_OBJECTIVE_ASSESSMENT.md` and the Chapter I §1.5.2 extract (objectives);
- E109–E112 (earlier hunger forecasts: after 2021 Balance Luzon hunger is HIGH in most quarters, so short windows are
  nearly one-class; the latest reading was the strongest baseline; news showed no forecast gain);
- `HISTORY_RETRAIN/RESULTS.md` (the reference).

**What was seen before this plan:** the HISTORY_RETRAIN results for T2 (all public in its RESULTS.md), the column
layout of the SWS and E112 news files, and the code of the backend LGU ranking. No label, model or baseline was computed
in this folder.

## 1. Target: food insecurity, not food prices

| Item | Definition |
|---|---|
| **Target** | **T2 of HISTORY_RETRAIN, unchanged:** y(q) = 1 when SWS Balance Luzon (BL) involuntary hunger H(q) > 11.3%, else 0. H(q) is the mean of the non-commissioned rounds of q. A quarter without a round has no label; nothing is filled. |
| **Food prices** | A **driver** (input columns) only. **No price condition enters the target.** |
| Unit | One row per quarter (region-wide). R1 is counted in quarters. |
| Leads | 1 and 2. Target q = t + lead. |
| Issue date | O(t) = the first day of quarter t+1. Only data published before O(t) is used, with the release rules of HISTORY_RETRAIN PLAN §1 (SWS rounds count only if `published < O(t)`; CPI to month 2 of quarter t; and so on). |
| Verdict window | Targets **2010-Q1..2026-Q3** at both leads (the same quarters as HISTORY_RETRAIN T2, at most 62). |
| Sub-blocks (reported, no verdict) | 2010-Q1..2022-Q4 and 2023-Q1..2026-Q3 |

**Data and label code are reused, not rewritten:** `HISTORY_RETRAIN/runner/hr_lib.py` is imported read-only (`load`,
`t2_labels`, `complete_bl`, `known`, `pi_h4l`, `rows_t2`, `persist_t2`, `eligible`, `LGBM`, `lgbm_select`, `logit`,
`evaluate`). HISTORY_RETRAIN's data files are read in place, with their recorded SHA-256 checked first.

## 2. The proposed model (Chapter 3 algorithm)

**LightGBM, refitted at each issue date, walk-forward with an expanding window.** At each origin t, training uses only
rows whose target q′ ≤ t − 1 and whose label was fully published before O(t). Rows of leads 1–15 are stacked with
`lead` as a column, as in Chapter 3 §3 and the reference. Explanations are SHAP contributions summed into indicator
groups (§7). **No algorithm outside Chapter 3 is used as the proposed model.** Logistic regression appears only as a
Chapter I baseline (§6); Platt scaling (§3, I3) is a one-input post-processing step of the LightGBM probability, not a
second forecasting model.

**Reference to beat (REF):** HISTORY_RETRAIN `LGBM (b)` for T2, **exactly as already scored**:
- inputs F_b(T2) + `lead` (HISTORY_RETRAIN PLAN §4);
- P0's model class, grid `GRID` (depth {1, 2}, trees {50, 150}, class weight {none, balanced}), inner chronological
  validation on the last 4 training origins by log-loss, eligibility rule and fallback;
- no monotone constraints.

Its published numbers: Lead 1 accuracy 0.790, Brier 0.188; Lead 2 accuracy 0.790, Brier 0.184; both fail R7 only.
REF's forecasts are recomputed here and **must equal** `HISTORY_RETRAIN/out/rows.csv` (§9 check 1). REF's
verdict is the one in HISTORY_RETRAIN; it is not re-decided.

## 3. Exactly three improvements (each alone and all together; none added later)

| ID | Improvement | Exact definition |
|---|---|---|
| **I1** | **More training data: pool the four SWS areas** | Training rows come from all four SWS areas (NCR, BL, Visayas, Mindanao), each with its own hunger columns (`h_last`, `h_change`, `h_mean4`, `true_h`, `pi_H4L`) built from **that area's** readings published before O(t), and its own label (that area's H(q) > 11.3, known only when all its rounds of q were published before O(t)). Three indicator columns `area_NCR`, `area_VIS`, `area_MIN` (BL = all zero). The non-hunger columns (CALABARZON CPI, typhoons, production, ONI, world prices, news) are **the same issue-date values for every area**: the extra rows add hunger dynamics, not area-specific drivers (disclosed). The inner validation log-loss and the eligibility rule use **BL rows only**. **Only BL is forecast and scored.** For an area's `pi_H4L`, σ is the same four-area pooled RMSE; the H0 fallback uses that area's own errors. |
| **I2** | **Regression on the hunger rate (%)** | LightGBM `objective="regression"` (L2) on H(q) in points, same settings as REF except class weight (not applicable): grid depth {1, 2} × trees {50, 150}, inner validation by mean squared error on the last 4 training origins. Converted to a probability: **P = Φ((Ĥ − 11.3) / max(σ_k, 0.5))**, where σ_k is the RMSE of **this arm's own** earlier walk-forward errors at the same lead whose targets were known before O(t). With fewer than 8 such errors, σ_k = the `pi_H4L` σ of the issue date (latest-reading errors at the true horizon). Eligibility: ≥ 6 target quarters with a known rate; otherwise P = the training HIGH share. |
| **I3** | **Probability calibration on earlier quarters only** | **Platt scaling** (fixed now; isotonic is not used because the calibration sets are small): a one-input logistic regression of y on logit(p̃), where p̃ is the uncalibrated arm's probability. Fitted at each origin t and lead k on the arm's **own earlier walk-forward forecasts** at lead k whose targets were known before O(t). Requires ≥ 20 pairs with ≥ 5 of each class; otherwise p̃ is used unchanged (counted and reported). p̃ is clipped to [1e-4, 1 − 1e-4] before the logit. scikit-learn `LogisticRegression(C=1e6, solver="lbfgs")`. |
| **ALL** | I1 + I2 + I3 | Pooled rows (I1) → rate regression (I2; σ_k from ALL's own earlier errors) → Platt (I3, on ALL's own earlier forecasts) |

**Earlier walk-forward forecasts for I2 and I3.** To have past errors and calibration pairs, every arm is run
walk-forward from origin **1998-Q3** (the first origin with a published reading), not only over the verdict window.
Forecasts at origins before 2009-Q3 are used only as error and calibration history and are never scored.

**Arms.** {REF, I1, I2, I3, ALL} × {without news, with news} = **10 LightGBM arms**. REF without news is the reference.
"With news" adds the news columns of §5; nothing else differs.

## 4. Selection rule (fixed now)

**Per lead:** carry forward the arm with the **lowest Brier** on the verdict window **among the arms that pass all of
R1–R7**. If no arm passes, carry forward **REF**. Ties go to the earlier arm in the order REF, I1, I2, I3, ALL, without
news before with news. **The carried-forward arm is "the proposed model"** for Objectives 2 and 4 and for the seal.

All 10 arms are candidates. **Ten candidates scored on the same 62 quarters make a chance pass more likely**; RESULTS.md
says so beside any pass.

## 5. Objectives (Chapter I §1.5.2): how each is addressed

| Objective | How it is addressed here |
|---|---|
| **1 NLP** | **News columns** added to every arm in its "with news" version: `N1R` (regional FSSI-v3 intensity of quarter t, mean over items published before O(t), NaN below 5 items; `FIRI_V2_DATA_AUDIT/runner/news_coverage.py` `n1r`, via `backend/app/news` read-only); `G_pri_yoy` (GDELT price-news YoY, the HISTORY_RETRAIN regional mean); and the six E112 category shares of quarter t (`price_share`, `shortage_share`, `disaster_share`, `agri_supply_share`, `jobs_income_share`, `assistance_share`, from `E112.../out/news_quarterly_corpus.csv`, usable only if `last_published < O(t)`). **They exist only from 2021-Q1 and are NaN before** (disclosed: a NaN here marks the era, not a gap). **Ablation:** each arm with vs without news, Brier difference with one-sided paired cluster-bootstrap p, on the full window and on the news era (targets whose origin is ≥ 2021-Q1). **BERTopic topics are not used as inputs** (THESIS_OBJECTIVE_ASSESSMENT: they are mostly place names); this is disclosed. |
| **2 I–IV** | For every arm and baseline at both leads: accuracy, balanced accuracy, precision, recall, **F1**, **AUC-ROC**, **Brier**, n and the confusion matrix. HIGH at P ≥ 0.50. |
| **2 V** | Walk-forward expanding window (§2). **Maximum reliable lead** = the run of consecutive passes of the **unchanged R1–R7** from Lead 1, for the carried-forward model, counted in quarters, verdict window 2010-Q1..2026-Q3. Only Leads 1 and 2 are tested, so the answer is 0, 1 or 2. |
| **3** | **Municipal and city rankings** for the sealed quarter(s) (§10): the backend's approved ranking `app.quarterly.lgu_poverty.rank_lgus` (imported read-only) on `backend/data/inputs/lgu_vulnerability.csv`, **province probability × (0.6 poverty_norm + 0.4 density_norm)** within province. **The forecast is regional, so all five provinces receive the same probability**, and the order inside each province is set by poverty and density alone; the forecast only scales the score. Output `out/lgu_rankings.csv`, every row labelled **"priority ranking, not a measured food-insecurity rate"**. The backend's known limitation (most LGUs carry a province-mean poverty substitute) is repeated. |
| **4** | On the same quarters, the proposed model against: **naive persistence** (latest published BL reading > 11.3), **PSA-only** (§6), **NLP-only** (§6), **logistic regression** (§6) and **ALWAYS-HIGH**. Test: Brier difference, one-sided paired cluster bootstrap by target quarter (seed 2036, 5000 draws, the R5 machinery). **Holm correction across the five comparisons, separately at each lead.** NLP-only is compared on the news-era quarters only (its inputs do not exist earlier); the other four on the full window. |
| **5** | **No dashboard change.** RESULTS.md lists what the dashboard would need to show this forecast (target wording, regional scope, horizon status, SHAP group bars, news status, ranking label, seal status). |

## 6. Baselines (Objective 4 and R1–R7)

| Baseline | Definition |
|---|---|
| **PERSIST** | 1 if the newest BL reading published before O(t) > 11.3, else 0 (`hr_lib.persist_t2`; HISTORY_RETRAIN's persistence) |
| **LOGIT** (logistic regression) | HISTORY_RETRAIN `LOGIT (b)` for T2, exactly as already scored: one model per lead on F_b(T2), L2, C = 1, training-median imputation, standardization, no tuning |
| **PSA-only** | The same LOGIT specification on the PSA indicator columns only: `R_food_yoy`, `R_head_yoy`, `R_rice_yoy`, `R_food_mom`, `R_C3`, `R_C4`, `E1`, `R_A3` (E1 exists from 2006-Q3 and R_A3 from 2011-Q1; earlier rows take the training median as the LOGIT rule already does, and a column with no training value is dropped) |
| **NLP-only** | The same LOGIT specification on the news columns of §5 only, trained on rows whose origin is ≥ 2021-Q1. Eligibility as usual (≥ 6 quarters, ≥ 5 HIGH, ≥ 5 LOW); otherwise the training HIGH share. Scored on the news era only. |
| **ALWAYS-HIGH**, **ALWAYS-LOW** | 1 and 0 |
| **CLIM** (R5) | Share of HIGH among BL quarters known before O(t), 1998+ |

## 7. SHAP group shares (Chapter 3 §5)

For each LightGBM arm, TreeSHAP contributions (`pred_contrib=True`) of the fitted model at each verdict-window row.
Absolute contributions are summed into groups and rescaled to 100% per row, then averaged over the window, by lead.
For I2 and ALL they are in rate points; for I3 they are those of the uncalibrated model (Platt is monotone).

| Group | Columns |
|---|---|
| H1 Hunger (SWS) | `h_last`, `h_change`, `h_mean4`, `true_h`, `pi_H4L` |
| A1–A2 Food and headline prices | `R_food_yoy`, `R_head_yoy`, `R_food_mom` |
| A3 Rice | `R_rice_yoy` |
| C1 Climate (ONI) | `ONI_last`, `ONI_max12` |
| C2 Typhoons | `tc_mean` |
| C3 Crops | `R_C3` |
| C4 Fisheries | `R_C4` |
| World prices | the five `W_*` columns |
| N1 News | the news columns (with-news arms) |
| Area indicator | `area_*` (I1 and ALL) |

`lead` is excluded and disclosed. **Not in the T2 inputs (disclosed):** V1 (static and provincial; a regional target
cannot use it), E1 and the provincial rice wholesale A3 (HISTORY_RETRAIN option (c), kept out to stay on the reference's
inputs), E2 (BSP remittances could not be acquired). The bars are relative model influence, not causes.

## 8. Reliability and reporting

**R1–R7** are imported unchanged from `P0H4_LEAD12_REVIEW/runner/reproduce.py` `rules()` through `hr_lib.evaluate`
(including the bootstrap replacement HISTORY_RETRAIN verified as exact), with R1 counted in quarters (≥ 10 and ≥ 40).
"Reliable" means passes R1–R7.

**RESULTS.md reports**, for every arm and baseline at both leads on the verdict window: n, all Objective-2 metrics,
R1–R7 pass or fail with values, the Brier difference with REF and with PERSIST (p), and fallback, calibration-skip and
σ-fallback counts. Also: the two sub-blocks; the Objective-4 table with raw and Holm p; SHAP group shares; the news
ablation; the selection; the rankings; the dashboard list.

**Known-break sensitivities (evaluation set only; they never change a verdict or the selection):**
- **S1:** without target quarters 2020-Q2 and 2020-Q3 (phone rounds);
- **S2:** without target quarters 2025-Q2 and later (adult respondents);
- **S3:** without both.

Failures are reported the same way as passes.

## 9. Checks (assertions before any scoring; the runner stops if one fails)

1. **REF fidelity:** REF's Lead-1 and Lead-2 forecasts for every origin 2009-Q3..2026-Q2 equal HISTORY_RETRAIN
   `out/rows.csv` (T2, LGBM, option b) to 1e-12; LOGIT and PERSIST likewise.
2. **I1 labels:** the BL rows of the pooled table equal `hr_lib.t2_labels` and `rows_t2`; every other area's label is
   its own SWS mean.
3. **Leakage perturbation** at origins 2005-Q2, 2015-Q3, 2020-Q2, 2021-Q3, 2023-Q4 and 2026-Q2: every input published
   on or after O(t) (SWS rounds of all four areas, CPI, production, typhoons, ONI, Pink Sheet, LFS, news) is randomized;
   the feature rows and training labels at that origin must be identical.
4. **Training rows:** every training row has q′ ≤ t − 1 and a label known before O(t). Every Platt pair and every σ_k
   error comes from a forecast issued at an origin < t whose target was known before O(t).
5. **Counts:** at least 40 verdict quarters per lead.

## 10. Seal (Step 3)

After RESULTS.md, the carried-forward arm of each lead forecasts every target **≥ 2027-Q1 whose issue date has
passed**, with data as of that issue date.
- **On 2026-11-03 this is only Lead 2 for 2027-Q1** (origin 2026-Q3, issue date 2026-10-01). Lead 1 for 2027-Q1 has
  issue date 2027-01-01, which is in the future.
- Output `sealed_prospective_IMPROVE_V2.csv`: issue date, lead, target, P, class, arm, newest SWS round used. Its SHA-256
  goes in `SEAL_LEDGER.md`. Local commit. **Never edited after sealing.**
- `runner/seal_next.py` issues later forecasts (Lead 1 for 2027-Q1 on or after 2027-01-01, and so on) into **new**
  files `sealed_IMPROVE_V2_<issue-date>.csv`, each hashed and appended to the ledger. It refuses to run before the issue
  date or to overwrite a file.
- `runner/score_seal.py` checks every hash in the ledger, then scores sealed rows whose SWS outcome has been published.
  It reports n, accuracy, Brier, and the same for PERSIST issued on the same dates. It never refits.
- The Objective-3 rankings are produced for each sealed quarter.

## 11. Outputs

| File | Contents |
|---|---|
| `runner/iv2_lib.py`, `runner/run_iv2.py` | Pooled rows, arms, news, SHAP, scoring |
| `out/checks.json` | §9 results |
| `out/forecasts.csv` | Every arm and baseline forecast, every origin |
| `out/results.json`, `out/summary.md` | All metrics |
| `out/lgu_rankings.csv` | Objective 3 |
| `RESULTS.md` | Results and the plain-words verdict, objective by objective |
| `sealed_prospective_IMPROVE_V2.csv`, `SEAL_LEDGER.md`, `runner/seal_next.py`, `runner/score_seal.py` | §10 |

At the end: the full backend test suite is run; `git diff --stat` and `git status` confirm that only `IMPROVE_V2/`
changed; nothing is pushed.

PLAN-SHA256: 2973784ae15ba8ce45500789b3f777e78c9e2ca082386cb6fe70295dd6b046ad
