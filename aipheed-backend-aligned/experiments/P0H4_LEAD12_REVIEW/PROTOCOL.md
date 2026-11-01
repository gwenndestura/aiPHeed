# P0H4 Lead 1 / Lead 2 review: candidate protocol (frozen before scoring)

**Status:** experimental. Nothing here changes the served model, its 0.5 threshold, `rows.csv`, the seal `a498b5ef` or
any protected file. All 2021–2026 quarters were examined by earlier experiments, so every result is development
evidence (rolling-origin over seen quarters), never independent validation.

## Why only one candidate

LEAD2_OPTIMIZATION (protocol `88ee80bc`, addenda 1–4) already scored about 20 configurations on these rows: price-model
variants P1–P8, structural priors, regularisation, hunger regressions H1/H3a, the 1998+ hunger history (sample b,
outside the 2021–2026 window), an all-in-one LightGBM (U-ONE) and Platt calibration fitted on inner folds (F1, worse at
both leads). Repeating any of them has no new justification. Its ceiling analysis shows the binding limit at Lead 2 is
the hunger onset (an information limit): even an oracle price term leaves Lead-2 recall at 0.59.

One rule was never tested out of sample: the **decision threshold**. The reproduction (`out/reproduce.json`) shows
Lead-2 probabilities are compressed below 0.5 (mean 0.295; most HIGH rows sit at 0.27–0.34). The oracle table's
cutoff 0.70 was chosen in-sample, so it says nothing out of sample.

## Candidate T: rolling-origin threshold, chosen on earlier labelled forecasts only

**Hypothesis (H-T):** a threshold chosen at each issue date from that lead's earlier forecasts whose T43c labels were
known before the issue date raises Lead-2 HIGH recall and balanced accuracy over the fixed 0.5 without losing Lead 1's
pass of R1–R7.

**Rule (fixed now):**
1. For a forecast issued on O(t) (first day of quarter t+1) at lead k, the training set is every earlier lead-k
   forecast in `FINAL_ARCHITECTURE/out/predictions.csv` (itself walk-forward) whose target quarter q satisfies
   q ≤ t − 1 and every regular SWS round of q (`backend/data/inputs/sws_rounds.csv`, Stratbase round excluded) was
   published before O(t).
2. If that set has fewer than 20 rows or fewer than 3 HIGH rows, the threshold is 0.5 (the served rule).
3. Otherwise the threshold is the value in {0.05, 0.10, …, 0.95} that maximises balanced accuracy on the set; ties go
   to the value closest to 0.5.
4. Probabilities are not changed; only the cut.

**Evaluation:** identical rows to the served evaluation (Lead 1: 70 rows, 14 quarters; Lead 2: 65 rows, 13 quarters);
the frozen rules R1–R7 (`FINAL_TARGET_AND_EVALUATION_PROTOCOL.md` §7, implementation `ch1_lib.py`), quarter-cluster
bootstrap 5 000 resamples seed 2036. Brier and AUC are unchanged by a threshold and are reported as such.

**Decision rule (fixed now):** candidate T is recommended for approval at a lead only if it passes all of R1–R7 there
**and** Lead 1 still passes all of R1–R7 under it. Otherwise it is recorded as a negative result. Even if recommended,
it is not served without your approval: the protocol threshold is 0.5.

**Trials:** 1 candidate × 2 leads. No other variant will be scored in this review.
