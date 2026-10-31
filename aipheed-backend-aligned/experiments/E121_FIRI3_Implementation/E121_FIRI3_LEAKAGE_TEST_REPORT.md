# E121 FIRI3 leakage test report

**When the checks run.** `runner/run_e121.py` computes them on the full run and **stops if any fails**. Results are in `out/summary.json` → `leakage`. Unit tests (`backend/tests/unit/test_firi3.py`) and integration tests (`backend/tests/integration/test_e121_firi3.py`) repeat them independently.

**Result: 15 of 15 boolean checks PASS.** One further entry, `pre2021_rows_rejected_count`, records a count: 0 rows needed rejecting.

| # | Check | How | Result |
|---|---|---|---|
| 1 | Protocol hash verified | The file, `PROTOCOL_SHA256.txt` and `firi3.PROTOCOL_SHA256` are identical | PASS |
| 2 | No future observation | Every scored dynamic value's observed quarter ≤ its origin | PASS |
| 3 | No future publication | Every scored value's availability date < its issue date | PASS |
| 4 | No stale value | Observed quarter at most 3 quarters before the origin | PASS |
| 5 | No SWS or index series among FIRI3 features | No series name contains sws / hunger / h1_ / firi | PASS |
| 6 | SWS refused if passed | `validate_inputs` raises when an SWS hunger series is added to the inputs (tested on the real inputs) | PASS |
| 7 | No pre-2021 observation scored | All scored periods 2021+; pre-2021 rows rejected before scoring (0 present in the inputs; unit test rejects 5 synthetic ones) | PASS |
| 8 | Provincial scores from provinces only | Units = the five provinces, series unit = province | PASS |
| 9 | Regional scores from regional units only | Series units ⊆ {Region IV-A, CALABARZON centroid proxy, PHILIPPINES} | PASS |
| 10 | No national feature in a provincial score | No `_R` feature in a provincial row | PASS |
| 11 | No annual-to-quarterly expansion | rank5 features keep a reference year, never a quarter | PASS |
| 12 | Rolling window valid | 200 sampled dynamic scores recomputed independently from observations with availability < issue **and** period < current period: identical | PASS |
| 13 | Missing never scored | Missing, stale, insufficient-history, unavailable and incomplete-year rows all have no score | PASS |
| 14 | FIRI3 only when complete | Every computed FIRI3 has ≥ ⌈2/3 × defined⌉ indicators | PASS |
| 15 | FIRI v2 files unchanged | SHA-256 of `firi.py`, `firi2_history.csv` and `firi2_reference.json` equal before and after | PASS |

## Target separation

- **SWS hunger** is read by the runner only after FIRI3 is computed, for the descriptive regional comparison (`out/regional_vs_sws_descriptive.csv`). It is never passed to `firi3`.
- **The weights** are fixed (equal); none are learned.

## Disclosed, not leakage

- **Retrospective vintage.** Historical scores use the current vintage of each input (E119 is one vintage). NASA POWER values in particular may have been revised since their first release. Snapshots from 2026-Q4 onward will be computed at the time and kept unchanged.
- **Release dates.** Most availability dates come from PSA release rules, not archived releases (DI-4).
