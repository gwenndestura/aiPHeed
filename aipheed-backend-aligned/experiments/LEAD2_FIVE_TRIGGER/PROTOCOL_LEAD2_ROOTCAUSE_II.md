# PROTOCOL_LEAD2_ROOTCAUSE_II: measured root causes of the Lead-2 failure (frozen 2026-10-29, before running)

**Branch:** `aiPHeed/lead2-rootcause-research`. This file's SHA-256 goes in `runner/ROOTCAUSE_II_SHA256.txt`; both are committed before `runner/lead2_rootcause.py` runs.

**Status.** Diagnostic only. No model is fitted, no candidate is scored or selected, and nothing is adopted. It reads the saved predictions of PROTOCOL_LEAD2_ASOF_REEVAL (`out/asof_reeval_rows.csv`) and the stack. The frozen target, rows, R1-R7, adoption rule, served model and seals are unchanged.

## Analyses

1. **Error trace.** Every Lead-2 error of B0, CR-ANC under verified timing, and CR-ANC under day-10 timing is traced. For each one the trace records:
   - the label: hunger component, target-quarter reading, price component, and realised price margin;
   - the issue-time inputs: latest hunger reading, projected price margins, CPI cut-off, missing inputs;
   - the model output: π_H, the price probability and P.

   Each error is attributed to the hunger part, the price part, both, or neither. Price errors are typed as:
   - rose after issue;
   - fell after issue;
   - model under-calls a positive projection;
   - model over-calls a negative projection.

2. **Sample sufficiency.**
   - Rows vs quarters vs HIGH quarters.
   - The intraclass correlation of correctness within a target quarter, the design effect and the effective n.
   - A quarter-cluster bootstrap (4000 draws, seed 2031) of accuracy, recall and precision, with the share of resamples that pass R2 and R6.
   - The single-row slack of R6.
   - Class transitions (onsets and offsets) of the price label, the hunger label and T43c, and the HIGH examples available before the first evaluation issue.

3. **Target.** A statement of what each component measures and what LightGBM predicts. The data shares are reported.

4. **Price predictability ceiling (reference, not a candidate).**
   - **Error model.** The joint error of the two CPI projections (realised minus projected food and gap margins) is treated as bivariate normal.
   - **Estimation.** The error is estimated per lead on target quarters before the evaluation period only (≤ 2023-Q1).
   - **Probability.** P(price HIGH | projections) follows from it.
   - **Results reported:**
     - the expected and realised accuracy of the Bayes call (p ≥ 0.5) against the price label;
     - the same quantities for T43c with π_H;
     - the LightGBM price parts.
   - **Stacks.** It is computed on the base stack (m0) and on the verified-timing stack.
   - **Use.** It bounds what the projection inputs can deliver. It is not served, not LightGBM, and not counted.

5. **Point-in-time audit of the 12 indicators.** For each indicator: the rule used, the evidence, the revision or vintage risk, and the status (verified / assumed / violation). Also reported:
   - stack-level checks: CPI month vs issue, SWS and news publication vs issue, target after origin;
   - missing shares and missing-value handling;
   - the threshold window.

## What this does not do

- No variant is fitted or tuned.
- **Earlier development screens.** Any intervention this analysis points to is ranked against the earlier development screens: IMPROVE B1-B4, CANDIDATES C1-C5, TUNING, FINAL K1/K2, SUBGROUP, COMBINATION, CAUSES, POVERTY_V3, ROOT_CAUSE and ASOF_REEVAL.
- **A new candidate needs its own frozen protocol.** Selection must use development target quarters (≤ 2024-Q4) only.
- **The evaluation rows are no longer independent.** All 65 Lead-2 rows have been inspected repeatedly, so a candidate built after this analysis is a *development candidate*. Independent evidence can come only from the sealed prospective forecasts or from quarters scored after the candidate is frozen.
