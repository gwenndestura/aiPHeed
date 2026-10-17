# E55 deviations (each recorded before the evaluation run it affects)

## D-1 (2026-10-17, after the baseline run, before any E55 evaluation score)

**What happened.**
- The Objective 4 baselines run through the E38 walk-forward framework (`e37_lib.eval_dates`).
- That framework skips a forecast date whose as-of training set has fewer than 10 rows or a single class.
- On T43 labels this removes target 2024-Q2 (origin 2023-Q4).
- `runs/baselines_20261017T153459Z` therefore has 45 rows (9 quarters, 2024-Q3..2026-Q3, 14 HIGH), not the expected 50.

**Rule applied.**
- PROTOCOL section 3 defines the evaluation rows as those "where every arm and baseline has a prediction". So the **primary rows are the 45 common rows**.
- "Expected: 10 quarters, 50 rows" was an expectation, not a rule.
- The acceptance criteria A1–A5 are computed on the 45 rows.

**Also reported.**
- A supplementary block on all 50 E52 rows (with 2024-Q2) for every arm that covers them: the E55 arms, the diagnostics, E46-I7, I7-BASE, E52, and always HIGH / LOW.

**What did not change.** The labels, the rows' labels (checked against E52), the models, the grids and the decision rules.

**Information seen before this deviation:** only the baseline run's row count, quarters and HIGH count (14). No model score was seen.

## D-2 (2026-10-17, run aborted before any metric)

**What happened.**
- Run `runs/<first stamp>` (marked `ABORTED.txt`) stopped with a KeyError while it was assembling the rows.
- The committed E38 predictions forecast the thesis Eq.3 label. That label has no value in 2025-Q2/Q3 (no approved SWS round), so E38 has no prediction there.
- No metric had been computed. The predictions file of the aborted run is kept.

**Fix.**
- E38-served is a non-equivalent comparator (PROTOCOL section 7). It is removed from the identical-rows block.
- It is scored separately, against T43 and for information only, on the 35 rows where it exists.
- Nothing else changes.
