# E127 final recommendation

## Classification: **IMPLEMENTED AND VALIDATED**

**Amendment 3 is implemented exactly as approved:**
- in the data layer, as a general rule: covered quarter without a storm → 0; uncovered quarter → missing;
- as FIRI3 **version 1.3**, with a new frozen configuration (`64a7d7df…`); v1.2 is kept as the record;
- **every expected effect independently reproduced.**

**First-forecast status.** E127 does not change this: the first forecast stays **BLOCKED** until 2027-01-01 and until September 2026 unemployment is published. Re-checked today: PSA tables still end in August 2026.

## Acceptance criteria

| # | Criterion | Result |
|---|---|---|
| 1 | Amendment 3 implemented per the approved evidence | Yes (`E127_FIRI3_PROTOCOL_AMENDMENT_3.md`, 4095ad4c…; `runner/par_counts.py`) |
| 2 | The three zero-storm quarters correctly represented | Yes: 2023-Q1, 2024-Q1, 2025-Q1 = 0, `verified`, with evidence. No other quarter changed; 2026-Q4 (in progress) stays missing. |
| 3 | Historical changes independently reproduced | Yes. Rebuilt from source; v1.2 reproduces E125 and v1.3 reproduces the E126 proposal (138 / 138 each). |
| 4 | The nine regional origins reconciled | Yes: 2024-Q2, Q3, Q4; 2025-Q1, Q2, Q3; 2026-Q1, Q2, Q3. Max \|Δ\| 0.041987. |
| 5 | 2025-Q2 band change verified | Yes: 0.5282 above usual → 0.4862 usual or below. The as-of PAR value moves from 2024-Q4 = 7 to 2025-Q1 = 0. |
| 6 | No provincial score changes | Yes (0 of 115) |
| 7 | 2026-Q4 score reproduced | Yes. Regional PAR percentile 0.7105 → 0.7500: same count of 7; reference set 19 → 22 with the three zeros. |
| 8 | Amendments 1 and 2 intact | Yes. 40 CPI rows rejected; 2024 used, 2025 skipped. Hashes unchanged. |
| 9 | No future-data leakage | Yes. All scored values were available before their issue; no future reference value; uncovered quarters not recorded. |
| 10 | Snapshot store immutable | Yes. No forecast, one blocked event; immutability tests pass. |
| 11 | Full suite without unexpected failures | Yes: 1183 passed, 0 failed, 18 skipped |
| 12 | Outputs and methodology changes documented | Yes (the 11 deliverables, the amendment text, the change log, the v1.3 configuration) |

## Remaining before the first forecast (unchanged by E127)

1. **On or after 2026-12-01:** run `E126…/runner/lfs_refresh.py` and confirm September 2026. The frozen mean-of-rates method is unchanged.
2. **On or after 2027-01-01:**
   - refresh every source and check revisions;
   - build the inputs with `runner/firi3_inputs.py` (v1.3);
   - rerun the readiness checks against the v1.3 configuration;
   - **request owner authorization**;
   - issue `FIRI3-1.3-2026-Q4` through the E124 store.

**Open warnings carried forward:**
- 26 provisional and 3 unverified publication dates;
- Batangas 2024/2025 employment values not verified against PSA;
- IBTrACS 2026 tracks provisional;
- 2025 provincial employment incomplete in the source.
