# E36 deviations from the frozen protocol

Every entry was written **before any E36 score was computed** unless it says otherwise.

## D-1. First development date is 2023-Q1, not 2022-Q4 (13 dates, 65 rows)

- **Conflict inside the protocol.** §2 lists 2022-Q4 as the first date. The list was enumerated from `docs/LABEL_PROBE.txt`, which counted training pairs *before* the §3 rule that drops rows with a missing COMB value.
- At O(2022-Q3) the 5 pairs for target 2021-Q4 have no `H_trend` and no `Dnow` (their origin 2021-10-01 has only one earlier SWS quarter and no Dnow months). After the §3 drop, 5 rows remain, below §2's own minimum of 10.
- **Resolution:** the binding rules (§2 minimum, §3 drop) win over the derived list. Development dates are **2023-Q1 … 2026-Q3 (13 dates, 65 rows)**; P-early = 2023-Q1..2023-Q3 (3 dates).
- Effect on labels (known from the probe, not from any score): 2 LOW rows of 2022-Q4 are lost; 13 LOW rows remain.
- Found by `tests/test_e36_timing.py::test_development_dates_match_the_protocol` on the first test run; no model had been scored.

## D-2. PCF21 diagnostic is reported only where its engine can run

- `pcf_engine.d_fit` needs at least 40 published D pairs. At the P-early origins it raises, so PCF21 has no prediction there.
- PCF21 is a diagnostic (§5), so it is reported on the dates it covers; paired tests use common dates and rows only.

## D-3. Counting errors in the protocol text (written after scoring; no rule changed)

- PROTOCOL.md section 2 says the four early dates add "11 LOW rows" and the full set has "15 LOW". The label probe shows 10 LOW rows on 2022-Q4..2023-Q3 and 14 LOW rows on 2022-Q4..2026-Q3. With D-1 the scored set has 12 LOW rows (53 HIGH / 12 LOW).
- These were prose summaries of the probe, not rules; the date and row rules are unaffected.
