# E60 final recommendation

## Decision

**1. Keep E38 as the production default, and keep E58-EW as the experimental early-warning model** (`AIPHEED_LEAD2_MODEL=e58`).
- E60's best candidate (A: E56's procedure without the old near-empty news columns) scores 0.80 vs 0.78 for E58-EW.
- It differs from E58-EW in **one** of 50 province-quarters.
- It fails the pre-registered improvement test: paired Brier CI [−0.006, +0.001].
- Replacing E58-EW with A would be a change justified by a single row. A is recorded as an equivalent alternative, not adopted.

**2. Do not add news to the forecasting model yet.**
- News did not improve the forecast: C vs A Brier +0.003 [−0.018, +0.027], and news alone has no signal.
- Adding it would make the model more complex with no evidence of benefit.

**3. Do adopt the improved news pipeline for the dashboard's evidence feed**, subject to your OK (proposal P1 in `DASHBOARD_AND_API_INTEGRATION_AUDIT.md`).
- Classifier v2 raises relevance precision from 0.28 to 0.92 on the frozen EVAL half (F1 0.38 → 0.83).
- The trigger queries add OFW, employment and fisheries coverage.
- This improves what DA sees as supporting evidence, without claiming that news drives the probability.

**4. Status of the candidate: experimental.** It is suitable for historical demonstration and internal review, **not** for controlled deployment as a validated food-insecurity forecaster.

## Minimum next steps (in order)

1. **Human-verify** the 78 EVAL annotations (`annotation/sample_*.csv`, column `human_verified`), then re-run `runner/n6_classifier_eval.py`.
2. **Score the frozen 2027-Q1 forecasts** (E56/E58) when the 2027-Q1 SWS round and March 2027 CPI are published. Freeze each later quarter at issue.
3. **Adviser decision on the issue date.** After each SWS release, E56 alone reproduces E58-EW's 2024-Q2 result (E59 S1).
4. **Obtain a provincial food-insecurity outcome** (CBMS FIES or provincial FIES/NNS tables) to validate the T43 proxy.
5. **Collect news prospectively.** Collect each quarter as it happens, with collection timestamps, so that coverage at issue time is real rather than retrospective. Consider body text (licensing permitting) and BFAR fish-kill bulletins.
6. **Adviser decision D8** (admit `.gov.ph` sources): 6,154 E60 items were rejected by the current domain policy.

## Permission needed

Nothing was committed, pushed, deployed or switched. The work is on local branch `e60-accuracy-optimization` (from 88d5266), uncommitted.

To keep it, say so, and I will commit E60 and the E59 audit as separate commits. Proposals P1–P3 are not applied.
