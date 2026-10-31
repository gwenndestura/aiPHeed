# E122 final recommendation

## Classification: **PASS WITH WARNINGS**

- **Before the audit, FIRI3 would have been FAIL.** 40 provincial CPI year-on-year rows for 2021 (comparisons with 2020) entered as current values and as percentile references (V1).
- **After Amendment 1**, which rejects change-type rows whose base is before 2021:
  - no pre-2021 observation influences any feature, reference, comparison base or score;
  - no future observation enters a historical score;
  - every score is traceable and reproduces from its features;
  - the independent 2021+ re-derivation agrees for all 18 re-derivable series;
  - geography passes for all 34 features;
  - all tests pass.

## Warnings (why not PASS)

1. **Publication dates.** 30 of 34 features rest on documented release rules, not archived release dates. Only cyclones (100 km, PAR), FSSI-v3 and GDELT are verified.
2. **Retrospective reconstruction.** All inputs were ingested in October 2026, so the historical scores use the current data vintage (NASA POWER may have been revised).
3. **Coverage.**
   - provincial FIRI3: 75 of 115;
   - regional FIRI3: 10 of 23;
   - PSV from 2025-Q3 only; FIS rarely; EHS lost for 2026-Q2/Q3 (DI-3).
4. **Disclosed model inputs.**
   - FSSI uses a pretrained zero-shot language model (W1);
   - its relevance rules were written on 2021–26 development articles (W2);
   - SAE 2021 poverty is a PSA model estimate (W3).

## Owner decisions

| Item | Recommendation |
|---|---|
| Amendment 1 (2021+ comparison base) | **Confirm.** It was applied under E122 §1/§5A. It withdraws the E119/E120 "PSA-published 2021 YoY" exception for FIRI3 only. E119/E120 outputs and the E121 snapshots are unchanged as records. |
| Prospective validation | Proceed from origin 2026-Q4 with the amended FIRI3. Refresh the E119 inputs with the new quarter's releases first, and write the snapshot once. |
| Publication dates | Request PSA release calendars, needed to move features from provisional to verified |
| E121 design issues DI-1 to DI-7 | Still open (not cutoff matters) |
| Production | FIRI v2 stays served. No adoption of FIRI3 without approval. |
