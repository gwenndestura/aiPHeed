# Scoring the sealed P0H4 forecasts (independent validation)

The sealed file `LEAD2_OPTIMIZATION/out/sealed_prospective_P0H4.csv` (SHA-256 starting `a498b5ef`) holds the P0H4
forecasts issued 2026-10-01. It was **not opened** in this review; only its hash was checked. It is the only
independent test of P0H4: every 2021–2026-Q3 quarter has already been examined.

## When

| Target | Lead | Needs | Expected |
|---|---|---|---|
| 2026-Q4 | 1 | SWS Balance Luzon rounds fielded in 2026-Q4, and PSA CPI for Oct–Dec 2026 | SWS about January 2027; CPI early January 2027 |
| 2027-Q1 | 2 | SWS rounds fielded in 2027-Q1, and PSA CPI for Jan–Mar 2027 | about April 2027 |

## Steps (no step may change the sealed file)

1. Check the file's SHA-256 still starts `a498b5ef`. If it does not, stop: the seal is broken.
2. Build each target quarter's T43c label exactly as frozen (FINAL_TARGET_AND_EVALUATION_PROTOCOL.md §2): HIGH when
   Balance Luzon hunger (mean of the quarter's regular, non-commissioned SWS rounds) is above 11.3 **and** the
   province's food YoY or food-minus-headline YoY is above its frozen 2021–22 P60 (E40 `label_spec.json`).
3. Score the sealed probabilities at the frozen threshold 0.5: confusion matrix, accuracy, recall, Brier, and the same
   always-LOW and PERSIST-SI baselines built from information published before 2026-10-01.
4. Report the result as **prospective**, separately from every development figure.

## What one quarter can and cannot show

Each target quarter adds 5 province rows that share one regional hunger outcome, i.e. **one** independent hunger
observation. One or two quarters can falsify a claim (for example, a missed onset), but cannot by themselves
establish reliability. R1 needs at least 10 target quarters, so a prospective pass of R1–R7 needs about 10 issued
quarters (2026-Q4 … 2029-Q1 at Lead 1).
