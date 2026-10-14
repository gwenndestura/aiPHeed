# E28 evaluation protocol: Objectives 2 and 4 (frozen before any E28 model is fitted)

**Frozen:** 2026-10-14. The SHA-256 of this file is written to `runner/E28_PROTOCOL_SHA256.txt` before
`runner/e28_evaluate.py` first fits a model, and the runner refuses to start if the hash differs.

**Requirement basis:** Chapter I only (E25 `thesis_source/CHAPTER_I_verbatim.txt`, sha 88dd0b62… of the thesis PDF).
Chapter I sets no numeric success threshold, so none is invented; accuracy above 75% is never treated as success.

**What this protocol does not change:** the approved target (T1: S1 = H + 2D > tau, with tau the median of the S1
labels usable before the origin), E25's rows and origins, E25's seal, E27's protocol and determination. The E25 and
E27 results remain the "original" results. E28 adds new arms, scored on exactly the same rows.

**Status of the data:** every 2021-Q1…2026-Q2 outcome has been examined in earlier experiments. All results here are
**development evidence**. They cannot validate a forecast. Only ledger-scored outcomes of forecasts sealed before
the outcome existed can do that.

## 1. Rows (same eligible observations for every arm)

- **Test rows:** E25 run `20261014T002026Z`, `predictions_T1_A.csv`, model `B1_naive_persistence`. For each row (lead,
  t, origin, target_quarter, province_code) the file gives y, the threshold tau of that origin, the realised S1
  (`value`) and the last S1 known at the origin (`v_last`). The file's SHA-256 is checked against E25's `SEALS.json`
  or manifest before use. Leads 1–6.
- **Training rows for (origin o, lead L):** every pair (t', t'+L) with t'+L ≤ t and the S1 label of t'+L usable
  before o. Usable means the target quarter's SWS round was published (`published_eff` in `sws_rounds.csv`) before
  o, the round is a definition-A production round, and the quarter has a D value. The training label is
  S1(t'+L) > tau_o. **Alignment check (must pass before fitting):** the number of training rows and the HIGH/LOW counts
  per (lead, t) equal E25's `fold_meta_T1_A.json` (`n_train_rows`, `train_HIGH`, `train_LOW`). If they differ, the run
  stops, and the difference is reported, not repaired after the fact.

## 2. Features (information set of origin o = first day of quarter t+1)

| Group | Feature | Source | Available at o because |
|---|---|---|---|
| NEWS | `FSSI_t`, `FSSI_lag1_t` (calendar-aligned), `FSSI_accel_t`, `log1p(n_in_fssi_t)`, `news_missing_t` | E28 news store (`backend_dev/data/news_e28/fssi_panel.csv`), built only from articles published ≤ end of t (PHT) | articles of quarter t end before o |
| GOV (PSA) | `Dnow_t` (relative food inflation, months 1–2 of t), `D_{t-1}`, `F_{t-1}` (provincial food CPI YoY, quarter mean), `dD = Dnow_t − D_{t-1}` | `backend_dev/data/inputs/dnow_panel.csv`, `d_quarterly_panel.csv` (E25 exports of public PSA CPI) | month-2 CPI is released in month 3 of t; quarter t−1 is complete |
| PERSIST | `v_last − tau_o` (last known S1 minus threshold), `y_last` | E25 row | by construction (E25) |

- A missing FSSI (no usable news) is NaN plus `news_missing = 1`. It is never 0. LightGBM handles NaN natively; the logistic
  models impute the **training-fold** median.
- **Leakage assertions** (the run fails if any fails): no feature row has a quarter after t; no article in an FSSI cell
  was published after the end of its quarter (PHT); no training label's round is published on or after o; the
  scaler/imputer is fitted on training rows only; no test row's (province, target_quarter) appears in its own training
  set; the 2021-Q1 lag features are NaN, not pre-2021 values.

## 3. Arms

Chapter I Objective 4 baselines (definitions as in E25, unchanged):

| Arm | Objective 4 item | Definition |
|---|---|---|
| `B1` | I. naive persistence | y_last (score 1/0; for Brier, the score itself) |
| `PSA_LR`, `PSA_LGBM` | II. PSA-only indicator | logistic regression / LightGBM on GOV |
| `NLP_LR`, `NLP_LGBM` | III. NLP-only sentiment | logistic regression / LightGBM on NEWS |
| `LR_COMB` | IV. logistic regression | logistic regression on NEWS + GOV |
| `PROPOSED` | the proposed model | LightGBM on NEWS + GOV |

No-skill references: `ALWAYS_HIGH` (p = 1 − 1e-6), `MAJ` (training majority), `CLIM` (training HIGH rate).

Fixed configurations (taken from E25 and not tuned on outcomes):
- logistic regression: `LogisticRegression(C=1.0, max_iter=2000)` on standardised features;
- LightGBM: `num_leaves=3, min_child_samples=10, n_estimators=50, learning_rate=0.1, subsample=1.0,
  colsample_bytree=1.0, random_state=20261014, verbose=-1`;
- a fold whose training labels have a single class predicts that class's training rate.

New E28 candidates (registered now; each is a legitimate improvement attempt with all selection inside the training
rows):
1. `PROPOSED_NESTED`: LightGBM on NEWS + GOV. Hyperparameters are chosen from `num_leaves ∈ {3, 7}`,
   `min_child_samples ∈ {5, 10, 20}`, `n_estimators ∈ {50, 150}`, `class_weight ∈ {None, "balanced"}`
   (learning_rate 0.05) by **inner expanding-window validation on the training quarters only**. The inner folds are
   the last three training target quarters, each predicted from the earlier ones. The criterion is mean Brier. Ties go to
   the earlier grid entry.
2. `PROPOSED_PERSIST`: LightGBM (fixed configuration) on NEWS + GOV + PERSIST, i.e. stronger temporal features.
3. `LR_STRUCT`: logistic regression on PERSIST + `dD` + `FSSI_accel`, i.e. a regularised structural model.
4. `PROPOSED_E25`, `PCF21_E25`: the original E25 predictions for the same rows (from the file; not refitted).

That is five new fitted arms (1–3, plus NEWS rebuilt for II–IV). The lineage's multiplicity is reported; no arm is
selected after seeing outer results.

## 4. Metrics (per target × arm × lead 1–6, and pooled over leads)

Rows, **independent dates** (origins), HIGH/LOW counts, a confusion matrix at 0.5 (positive = HIGH), accuracy,
balanced accuracy, precision, recall, F1, ROC-AUC, PR-AUC (average precision, positive = HIGH), Brier, log loss,
calibration-in-the-large, ECE (three bins as E27), and date-cluster bootstrap 95% intervals (2,000 resamples, seed
20261014) for accuracy, Brier and AUC.

**Estimability (fixed now):**
- AUC and PR-AUC are NOT_ESTIMABLE when either class is absent.
- Precision is NOT_ESTIMABLE when there are no predicted HIGH. Recall is NOT_ESTIMABLE when there are no actual HIGH.
- Every class-dependent metric is flagged UNSTABLE when the minority class has fewer than 5 rows.
- Any metric is flagged UNSTABLE when there are fewer than 8 dates.

**Majority check:** each arm reports the share of rows predicted HIGH, and whether its predictions equal ALWAYS_HIGH
on every row.

**Province view:** per province, rows, HIGH/LOW and accuracy, labelled "shared regional outcome; not an independent
provincial evaluation".

Paired tests: one-sided exact sign-flip over dates on the per-date mean loss difference (reference − arm) for 0/1
error and Brier, with Holm across references, as in E27.

## 5. Horizon and qualification rules (unchanged from the existing protocols)

- **Reliable lead (E23/E25 C6, adviser approval pending):** lead k is reliable iff it is evaluable (≥ 8 dates,
  ≥ 5 HIGH, ≥ 5 LOW), the date-cluster bootstrap lower bound of AUC is > 0.5, AND the arm's Brier beats B1 with a one-sided
  sign-flip p < 0.05. The furthest reliable horizon is the largest such k. With no reliable lead it is "not
  determinable on the available outcomes", never 0 or 1 by default.
- **Beats the baselines (E27 qualification rule):** for BOTH accuracy and Brier, with leads pooled, the Holm-adjusted p is
  < 0.05 against EVERY reference (B1, ALWAYS_HIGH, CLIM, MAJ and the four Objective 4 baselines), and the mean
  difference is positive against each.
- **Reachability (computed, not assumed):** for each lead, whether the criteria could be met by a perfect forecaster on
  these rows. Where a criterion is unreachable, the result is a property of the outcome data, not of the model.

## 6. Determination file

`runs/e28_eval/E28_DETERMINATION.json` records:
- for T1, the reliable leads per arm and the furthest reliable horizon (or "not determinable");
- whether any arm qualifies on development data;
- reachability;
- the smallest additional outcome data that would make a lead evaluable, i.e. the number of LOW rows still missing at each lead;
- that every result is development evidence.

T2 (D > 0, constructed price pressure) is evaluated with the same arms as an **exploratory price-pressure indicator,
never a food-insecurity forecast**.
