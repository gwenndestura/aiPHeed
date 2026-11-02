# LEAD2_FOODINSECURITY: Lead-1 and Lead-2 reliability under a hunger-only target (EXPLORATORY)

**Written:** 2026-11-02, before any model in this folder was scored.

**Label: EXPLORATORY.** Every quarter scored here (2023-Q1 to 2026-Q3) has been examined by earlier experiments. A pass here is only a **candidate** for a new pre-registration judged on 2027+ quarters. It is not a validated result.

**What this does not change:**
- the served model (P0H4), the dashboard, `backend/data`;
- `backend/seals/PREREG_LEAD2.md`, its addenda, and every sealed forecast;
- the T43c target used everywhere else.

The runner reads existing files and writes only to this folder's `out/`.

**Hash.** The SHA-256 of this file is computed over every byte before its last line, which begins `PLAN-SHA256:`. The runner refuses to run if the file changed after hashing.

**Disclosure.** While checking the input files for this plan, the label counts were seen: the hunger condition was HIGH in 11 of the 14 Lead-1 target quarters and in 11 of the 13 Lead-2 target quarters. No model or baseline was scored before this plan was committed.

## 1. Target

**HIGH in quarter q** when SWS Balance Luzon involuntary hunger in q is **above 11.3%**. Hunger is the mean of the non-commissioned rounds of q (the verified series, `ch1_lib.bl_quarters`; the column `hunger` in the evaluated predictions). There is **no price condition**.

The target is region-wide, so all five provinces have the same label in a quarter.

## 2. Leads, issue date and information

| Item | Definition |
|---|---|
| Leads | 1 and 2 |
| Issue date | O(t) = the first day of quarter t+1 (as served). The target is q = t + lead. |
| Information | Only data published before O(t), with the same cut-offs as the served system |

## 3. Walk-forward window (unchanged from LEAD2_OPTIMIZATION protocol `88ee80bc`)

The rows are exactly the Lead-1 and Lead-2 rows of `FINAL_ARCHITECTURE/out/predictions.csv`, the walk-forward window the P0H4 Lead 1 / Lead 2 results were scored on:

| Lead | Target quarters | Quarters | Rows |
|---|---|---|---|
| 1 | 2023-Q1..2026-Q3 | 14 | 70 |
| 2 | 2023-Q2..2026-Q3 | 13 | 65 |

2025-Q1 has no Balance Luzon round, so it has no label. The runner asserts these counts.

## 4. Models (fixed list; nothing is added later)

| ID | Model | Forecast probability |
|---|---|---|
| **(a) PERSIST** | Persistence | 1 if the latest Balance Luzon reading before O(t) is above 11.3, else 0. That reading (`h_last`) is the mean of the rounds of the newest quarter that were published before O(t) (`fi_lib.known`) |
| **(b) PIH** | The existing hunger part of P0H4 | `pi_H4` from the evaluated predictions. For Lead 1 the runner asserts it equals the served `pi_hunger` in `backend/data/ch1_engine/rows.csv` (max abs diff < 1e-6) |
| **(c) LOGIT** | One logistic regression on the 12 indicator families plus the latest SWS reading | See below |

**(c) LOGIT, fixed specification:**
- **Features.** The 16 columns of the served 12-family table, `ch1_lib.COLS`: A1_food, A1_gap, A2, A3, V1, C1, C2, C3, C4, E1, E2, N1, H1, A_mom, G_pri_yoy and NG_gap_price, families A1–A3, V1, C1–C4, E1, E2, N1, H1. Plus `h_last`. They are built by `uni_lib.stack(2)`, with the same issue-date cut-offs as served.
- **Model.** scikit-learn `LogisticRegression(penalty="l2", C=1.0, solver="lbfgs", max_iter=5000)`, no class weights.
- **Preprocessing.** Fitted on the training rows only: missing values are filled with the training median, and every column is standardized with the training mean and sd. A column with no training value, or an sd of 0, is dropped at that origin.
- **No tuning and no feature selection.** One model per lead.
- **Training rows at origin t, lead k:** stacked rows of the same lead with origin t′ < t and target q′ = t′ + k ≤ t − 1, kept only if **every** Balance Luzon round of q′ was published before O(t). Each row's label is the hunger condition of q′. Origins start at 2021-Q1, the first origin of the table.
- **Fallbacks.**
  - Training labels of one class only: predict that class's training share.
  - No training rows: predict CLIM.
  - The runner reports how many origins used each fallback.
- **Output.** The model gives one forecast per province row, because some features are provincial. It is evaluated on those rows as they are. The runner also reports the number of quarters in which the five provinces' HIGH/LOW decisions disagree.

**Decision rule for all models:** HIGH when the probability is ≥ 0.50, the approved dashboard rule.

## 5. Baselines

| Baseline | Probability |
|---|---|
| ALWAYS-HIGH | 1 |
| ALWAYS-LOW | 0 |
| Persistence (PERSIST-SI for this target) | Model (a). It is the hunger half of the served PERSIST-SI (`ch1_lib.persist_si`) |
| CLIM | Share of HIGH quarters among the 2021+ Balance Luzon quarters whose every round was published before O(t) |

## 6. Evaluation

**The R1–R7 rules are applied unchanged.** They are FINAL_THESIS_OBJECTIVES §7, as frozen for LEAD2_OPTIMIZATION protocol `88ee80bc` and recomputed in `P0H4_LEAD12_REVIEW/runner/reproduce.py` `rules()`:
- same thresholds;
- same thirds (`np.array_split`) and leave-one-quarter-out (LOQO);
- same one-sided paired cluster bootstrap by target quarter (seed 2036, 5000 draws).

For this target, PERSIST-SI is baseline (a) and CLIM is the CLIM above. The runner imports that `rules()` code and swaps in this target and these baselines; it does not re-implement it.

**Reliable** means a model passes **all of R1–R7** AND has a **lower Brier score than ALWAYS-HIGH and than persistence**. The Brier comparison uses the point estimate. The one-sided cluster-bootstrap p is reported beside each.

**Unit.** The target is region-wide, so the five province rows of a quarter are not independent. Every result is reported with **n in quarters**, and the bootstrap resamples quarters.

R1 as written ("≥ 10 target quarters and ≥ 40 rows") counts rows. Those 40+ rows are five copies of 13–14 quarters, so R1's row count is met only by the copies. The runner reports R1 as written and, beside it, R1 in quarters: ≥ 40 independent quarters, which no model can meet with 13–14 quarters. The verdict uses R1 as written. RESULTS.md states plainly that n is 14 (Lead 1) and 13 (Lead 2) quarters.

**By construction:** model (a) is also the persistence baseline. It cannot beat itself, so it cannot pass R4, R5 or the Brier criterion against persistence. It is reported anyway.

**Reported for every model and baseline at each lead:**
- the confusion matrix;
- accuracy, balanced accuracy, precision, recall, AUC (undefined for a constant forecast) and Brier;
- each of R1–R7 with its value;
- the Brier comparison against ALWAYS-HIGH and persistence, with p;
- the verdict;
- each quarter's forecast and outcome.

Failures are reported the same way as passes.

## 7. Leakage checks (assertions, before scoring)

The runner stops if any of these fail:
- For every model (c) training row, every Balance Luzon round of its target quarter was published before O(t), and its target quarter is ≤ t − 1.
- For every evaluation row, `sws_newest_published` < O(t).
- For every evaluation row, `h_last` equals the mean of the rounds published before O(t) of the newest Balance Luzon quarter with such a round (`fi_lib.known`).
- Every evaluation row's (t, lead, province) exists in the predictions file, and target = t + lead.

## 8. Outputs

- `runner/run_fi.py`
- `out/results.json`
- `out/rows.csv`: every row's probability per model.
- `RESULTS.md`: every model's metrics, including failures. It states:
  - which models pass at Lead 1 and at Lead 2;
  - the number of quarters;
  - whether any model beats ALWAYS-HIGH.

PLAN-SHA256: 23a030ae55f61c92c1a8235272d3c90f9285abaa3d4dcef8a5401b7e125b43ee
