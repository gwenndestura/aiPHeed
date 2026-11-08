# E152 results: regional signals and local prices

**Verdict: E152 did not improve accuracy. It scored lower than the E151 required model. It is not adopted, and production is unchanged.** One locked run; a second is refused by the code. Evidence is retrospective: all rows were read before, and their errors were studied before this design.

## Result, Lead 1, 72 rows

| Arm | Correct | Accuracy | HIGH recall | LOW recall | AUC | Brier | Error (pts) | Within-round correlation |
|---|---|---|---|---|---|---|---|---|
| **E152: new inputs + drift** | 50 | **0.694** | 0.84 | 0.62 | 0.843 | 0.191 | 9.13 | 0.68 |
| New inputs, no drift | 51 | 0.708 | 0.88 | 0.62 | 0.849 | 0.190 | 8.64 | 0.69 |
| Drift, no new inputs | 50 | 0.694 | 0.84 | 0.62 | 0.854 | 0.185 | 8.86 | 0.68 |
| E151 inputs, half adjustment | 52 | 0.722 | 0.88 | 0.64 | 0.857 | 0.186 | 8.43 | 0.69 |
| E151 required model | 52 | 0.722 | 0.76 | 0.70 | 0.855 | 0.172 | 8.05 | 0.67 |
| Persistence | 45 | 0.625 | 0.96 | 0.45 | 0.827 | 0.247 | 11.16 | 0.68 |

* E152 - E151 required, Brier: +0.019 [+0.004, +0.039], **clearly worse.**
* E152 - persistence, Brier: -0.057 [-0.107, -0.013], still better than an old survey.
* 2021 round: 0.80, below always-LOW's 0.84. 2018: 0.636. 2019: 0.64.
* Confusion: TP 21, FP 18, TN 29, FN 4.
* Slope interval [0.43, 0.83] excludes 1. Not prevalence. R1, R5 and R7 fail, as well as R8 and R9.

## What this shows

1. **Regional drift failed.** On 2021 it lost one to two rows and raised error by about 1 point against the same model without it. My diagnosis ranked it first. **The ceiling calculations showed where error sits, not that this signal could capture it.**
2. **Local prices and complete rainfall did not help on these rows.** The model used them (23 % of the live adjustment) but ranking between provinces did not improve (0.68 against 0.67), and that was the gap this set out to close.
3. **Regional labour and income data were not found** in a usable form, so that part of the plan was not tested.
4. **Limits of this test:** the 3-month release lag is an assumption; prices are missing on 27 to 40 % of test rows at the forecast quarter; rainfall is a province centroid; 156 training rows for 2018 and 2019.

## What this means for the D5 attempt

"E151 inputs, half adjustment" uses all five groups at the setting D5 chose for 2021, and it reaches **52 of 72, the same as the required model.** D5's 54 of 72 therefore depends on the three-group setting on the 2018 and 2019 rows, which drops employment, remittances and news. **With all five groups kept, no setting tested here reaches 75 % on the pool.** This was not known when D5 was reported.

## Live forecast, issue 2026-10-01, target 2027-Q1

Batangas 25.4, Cavite 32.4, Laguna 28.5, Quezon 32.5, Rizal 36.1, all LOW. Ranges overlap. Sealed `backend/data/e152/out/sealed_2027-Q1.json`, sha256 `f6c07789...`. It is kept as a comparator against the E151 seals, not as the model.

## Decision

**No further model search on these rows.** The E151 result stands. New provincial evidence needs a new FNRI round; new quarterly area evidence needs SWS releases.

Files: `docs/e152/PROTOCOL.md`, `backend/data/e152/out/{results.json, oof.csv, live.json, panel_audit.json, lock.json}`, `backend/data/e151/out/diagnosis.json`, `backend/tests/unit/test_e152.py`.
