# E39 Label v2: anchor decision record (to be completed by the researcher and adviser)

**Status: BLANK.** No E39 label, specification or model run may proceed until every field below is filled, dated and signed.

**Researcher's decision (2026-10-15):** no pre-2021 data may be used, including for label anchors. The anchors below therefore have to be **documented methodological constants** set by the researcher and adviser. They cannot be statistics computed from SWS or PSA data before 2021-Q2, and they cannot be computed from the evaluation sample (2021-Q2..2026-Q3).

## Rules each anchor must satisfy

1. The value is fixed **before** any E39 model run and is not changed afterwards.
2. It is not computed from in-sample data (2021-Q2..2026-Q3), and not chosen by looking at model accuracy, Brier, AUC or label prevalence.
3. Its basis is stated in one paragraph with a citable source: a publication, a policy document, or the adviser's documented methodological judgement.
4. It is reported as a methodological choice, not an empirical relationship.

## Fields

| Anchor | Meaning in the label | Value | Unit | Basis and source (citation or "adviser judgement", with reason) | Set by | Date |
|---|---|---|---|---|---|---|
| H_norm | SWS Balance Luzon hunger level treated as "normal" (h = 0) | | % of families | | | |
| H_sev | Hunger level treated as "severe" (h = 1); must be > H_norm | | % of families | | | |
| P_norm | Provincial food inflation treated as "normal" (p = 0). Candidate: 4%, the upper end of the BSP/DBCC 3% ± 1 target, which is a **headline** target applied to food inflation (state whether this is accepted) | | % YoY | | | |
| P_sev | Food inflation treated as "severe" (p = 1); must be > P_norm | | % YoY | | | |
| Weights w_H / w_P | Default 0.5 / 0.5 (methodological choice) | | – | | | |
| Tier cutoffs | Default 33.3 / 66.7 (equal thirds), with HIGH also requiring h > 0 and p > 0 | | FSI points | | | |

## Not available from the data (for the record)

- No approved SWS Balance Luzon round exists before 2021-Q2 within 2021–2026, so H_norm and H_sev cannot come from a pre-label window.
- The only in-window pre-label food CPI data are 2021-Q1 (5 provincial quarterly values), too few for a percentile.
- No official "severe food inflation" threshold is known to the project.

## Alternative (needs an explicit instruction)

If the absolute hunger component cannot be anchored, the specification would have to change. One option is to drop H from the index; another is to replace the anchors with a different, in-window definition. Either is a change to the E39 task and must be instructed in writing before any run.

Signed (researcher): ____________ Date: ________ Signed (adviser): ____________ Date: ________
