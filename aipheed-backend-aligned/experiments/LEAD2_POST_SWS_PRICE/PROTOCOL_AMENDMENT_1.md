# Protocol amendment 1 (written before any model was run or scored)

**Frozen at:** see `PROTOCOL_AMENDMENT_1_FROZEN_AT.txt`.

**SHA-256:** see `PROTOCOL_AMENDMENT_1_SHA256.txt`.

**Base protocol:** `PROTOCOL.md` (sha `b547e0ab…`). The base protocol itself is unchanged.

**Why this amendment.** The base protocol set a parity tolerance of 1e-9 against the stored `P0_price`. Before any run, inspection of `FINAL_ARCHITECTURE/out/predictions.csv` showed that `P0_price` is stored with **6 significant digits** (for example `0.258237`). So a 1e-9 check against that file cannot pass, whatever the pipeline does. No M2 value, metric or rule result existed when this was written.

## Parity (replaces §2.2), two checks; both must pass

| Check | What it compares | Pass condition |
|---|---|---|
| **a. Against the stored file** | The copied pipeline, run with the served cutoff, against every stored Lead-2 `P0_price` | Equal at the stored precision: the value formatted with `%g` (6 significant digits) equals the stored value. Max abs. difference ≤ 5e-7 is also reported. |
| **b. Against the original code, full precision** | The copied pipeline against the original `l2_lib.forecast_origin(l2_lib.add_fe(S), t, ("P0",))`, in the same process, at three origins (first, middle and last Lead-2 origin) | Max abs. difference ≤ 1e-9. This is the protocol's 1e-9 tolerance, applied where full-precision values exist. The copy omits `add_fe`, because P0 does not use its columns. |

Failure of either check stops the study, and M2 is not scored.

## Leakage (clarifies §2.3)

- "The newest CPI month in `Data.cut(t)` equals m0'(t)" is checked as **≤ m0'(t)**, which is the leakage condition.
- Equality is reported for every origin. Where the CPI file ends before m0'(t) (only possible at the newest origins), this is reported, not treated as a failure.

Nothing else changes.
