# Maximum reliable lead time (Objective 2 V)

**Time convention.** Forecasts are issued on O(t), the first day of quarter t+1, using only data published before it.
Lead k targets quarter t+k. Lead 1 is the quarter that starts on the issue date: a real forecast, made before any of
its data exist, and up to 3 months ahead of its end. Lead 0 (quarter t, already ended, survey not yet published) is a
nowcast and does not count as a horizon.

**Rule (frozen, same at every lead).** R1 ≥ 10 quarters and ≥ 40 rows; R2 accuracy ≥ 0.75; R3 balanced ≥ 0.70; R4 beats
always-LOW and same-information persistence; R5 Brier below persistence and climatology (p < 0.10); R6 precision and
recall ≥ 0.60; R7 every third ≥ 0.60 and leave-one-quarter-out minimum ≥ 0.70. Maximum reliable lead = largest K with
Leads 1…K all passing.

| Lead | R1 | R2 | R3 | R4 | R5 | R6 | R7 | Reliable |
|---|---|---|---|---|---|---|---|---|
| 0 | ✓ | ✓ | ✓ | ✗ | ✗ | ✗ | ✓ | no (nowcast) |
| **1** | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | **yes** |
| 2 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | no |
| 3 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | no |
| 4 | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | no |

**Answer: one quarter (up to 3 months).** Same answer on held and audited inputs and with pooled-area σ.

Under the stricter variant (balanced accuracy above every comparator, including LGBM-GOV which ties at 0.883) no lead
qualifies; both verdicts are reported.

The dashboard labels Lead 1 forecasts as reliable and Leads 2–4 as "indicative, outside the tested horizon".
