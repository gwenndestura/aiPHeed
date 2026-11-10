# E187 results: E184 at Leads 4–6, and a HIGH cut-off chosen on training folds

Run once, following `docs/e187/PROTOCOL.md` (sha256 5cdd7af4…, committed before any output).
Outputs are in `backend/data/e187/out/`. Nothing was staged, deployed or pushed.

## (A) E184 at Leads 4, 5 and 6 (72 real outer rows per lead)

The E168 rows rerun inside this job match `all_rows_l3_8.csv` exactly (maximum |Δp| = 0 at every lead).

| Lead | Accuracy: persistence / E168 / **E184** | Balanced accuracy: E168 / **E184** | HIGH recall: E168 / **E184** | Brier: E168 / **E184** | E184 − persistence Brier [95 % CI] | E184 − E168 Brier [95 % CI] | Owner rule |
|---|---|---|---|---|---|---|---|
| 4 | 62.5 / 73.6 / **77.8 %** | 0.751 / **0.792** | 0.80 / **0.84** | 0.1365 / **0.1261** | −0.087 [−0.136, −0.043] | −0.0103 [−0.0184, −0.0025] | pass |
| 5 | 62.5 / 72.2 / **75.0 %** | 0.740 / **0.752** | 0.80 / **0.76** | 0.1380 / **0.1281** | −0.085 [−0.140, −0.033] | −0.0099 [−0.0186, −0.0016] | pass (exactly at 75 %) |
| 6 | 62.5 / 69.4 / **76.4 %** | 0.719 / **0.772** | 0.80 / **0.80** | 0.1433 / **0.1286** | −0.084 [−0.143, −0.032] | −0.0147 [−0.0269, −0.0045] | pass |

- **E184's served horizon under the owner rule is 6 quarters** (Leads 1–6 all pass). E168's horizon is 3 quarters.
- At every one of Leads 4–6, E184's Brier score is significantly better than E168's. False alarms fall from 14–17 to 12.
- **Caveats.**
  - Lead 5 passes at exactly 75.0 %. One more wrong province would fail it.
  - The persistence baseline is the same at Leads 4–6 because the last released survey is the same.
  - A shuffled-trigger control was not run at these leads. At Leads 1–3, shuffled controls scored about as well as the real model, so part of the long-lead gain may come from the survey anchor and synthetic smoothing rather than from the triggers.
  - The 72 rows per lead come from the same three survey rounds used throughout E151–E187.

## (B) E187 = E184 with a HIGH cut-off chosen on training folds (Leads 1–3)

The probabilities are identical to E184's (maximum |Δp| = 0); only the HIGH/LOW decision moves.

| Lead | Cut-offs chosen (2018 / 2019 / 2021) | Accuracy: E184@0.50 / E187 | Balanced accuracy: E184 / E187 | HIGH recall: E184 / E187 | McNemar p |
|---|---|---|---|---|---|
| 1 | 0.50 / 0.55 / 0.45 | 76.4 / 77.8 % | 0.782 / 0.783 | 0.84 / **0.80** | 1.0 |
| 2 | 0.45 / 0.40 / 0.45 | 79.2 / **72.2 %** | 0.803 / **0.759** | 0.84 / 0.88 | 0.125 |
| 3 | 0.55 / 0.55 / 0.40 | 77.8 / 80.6 % | 0.792 / 0.823 | 0.84 / 0.88 | 0.69 |

- **Decision (as fixed): E184 keeps the 0.50 cut-off.** The cut-off chosen on training folds jumps between 0.40 and 0.55 from round to round.
- It lowers HIGH recall at Lead 1 and lowers balanced accuracy (−4.4 points) at Lead 2.
- The 80.6 % at Lead 3 is not a reliable gain: it comes with a 72.2 % at Lead 2, and no difference is significant.

## Conclusion
- **The tuned cut-off (B) does not help.** E184 at 0.50 stays the best model.
- **The new finding is (A).** E184 holds ≥ 75 % accuracy and beats both persistence and E168 out to 6 quarters ahead, where E168 drops below 75 % after Lead 3.
- **Extending the served horizon** from 3 to 6 quarters would be an owner decision. It needs staging of Leads 4–6, which this experiment did not do.
