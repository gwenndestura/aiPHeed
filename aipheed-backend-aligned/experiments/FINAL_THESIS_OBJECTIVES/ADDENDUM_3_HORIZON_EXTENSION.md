# Addendum 3: horizon extension and verification analyses

**Applies to:** `FINAL_TARGET_AND_EVALUATION_PROTOCOL.md` (sha `dd9ab815…`), with Addendum 1 (audited inputs).

**Freezing:** frozen before any lead above 4 was scored. Its SHA-256 is in `runner/ADDENDUM_3_SHA256.txt`.

## Why

The protocol evaluates Leads 1–4. The horizon must come from the data, not from a fixed range, so scoring is extended
to every lead the data can evaluate.

## Known before freezing (data availability only; no lead above 4 scored)

`../FINAL_VERIFICATION/out/testability.json` (`runner/testability.py`) counted evaluable target quarters per lead,
without fitting or scoring a model. It used only the frozen training-eligibility minimum (6 quarters, 5 HIGH, 5 LOW
price labels before the origin), origins from 2021-Q1, and labelled targets up to 2026-Q3:

| Lead | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9+ |
|---|---|---|---|---|---|---|---|---|---|
| Evaluable quarters | 14 | 12 | 10 | 8 | 6 | 5 | 3 | 1 | 0 |
| True SWS horizon (quarters after the newest published survey) | 1–2 | 2–3 | 3–4 | 4–5 | 5–6 | 7 | 8 | 9 | – |
| A1 base months available at the issue date | 3 | 3 | 3 | 2 | 0 | 0 | 0 | 0 | – |

The Lead 1–4 results were already known (first run and audited rerun).

## What is added

1. **Leads 5–8** are scored with the unchanged model, comparators, metrics and rule R1–R7, on the audited inputs.
   Lead 9 and beyond have no evaluable quarter.
2. **Testable horizon** = the longest lead meeting R1 (≥ 10 quarters and ≥ 40 rows), the protocol's own minimum for a
   credible test. R1 is not relaxed for any lead.
3. **Maximum reliable lead**, unchanged definition: the largest K such that Leads 1…K all pass R1–R7. Also reported,
   as a diagnostic only: every individual lead that passes R1–R7, whether or not the leads before it pass.
4. **Operational horizon:** for each lead, the quarters between the issue date and the target quarter, and the
   quarters between the newest published SWS survey and the target quarter (the true horizon).

## Verification analyses (descriptive; no criterion changes)

- Independent rebuild of T43c from the verified SWS file and the fresh PSA index pull, compared with the evaluated
  labels.
- Metrics recomputed from the saved predictions with code independent of `ch1_lib`, and a fresh re-run checked for
  identical predictions.
- Issue-date checks for every test row and every training set (newest SWS publication, newest CPI month, newest
  news item, highest training target quarter).
- Results by target quarter; the latest four-quarter block; quarters where hunger rose sharply; a split of accuracy
  into the regional hunger condition (one value per quarter) and the provincial price condition.
- Quarter-level summaries, so that the five province rows sharing one regional hunger value are not counted as
  independent hunger outcomes.

Nothing here changes the target, thresholds, test period, metrics or reliability rule.
