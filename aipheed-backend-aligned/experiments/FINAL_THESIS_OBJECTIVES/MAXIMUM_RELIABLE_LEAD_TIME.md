# Maximum reliable lead time (Objective 2 V)

> **Superseded for the served model (2026-10-27).** This document describes the per-lead CH1-LGBM. The served
> methodology is now one unified LightGBM across all leads (UNI-FINAL), as the user's directive requires: see
> `../FINAL_UNIFIED_LGBM/UNIFIED_RESULTS_AND_OBJECTIVES.md`. CH1-LGBM's results below remain valid as a comparison.


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

The dashboard labels Lead 1 forecasts as reliable and Leads 2–4 as experimental (generated, tested, failed).

## Update: Addendum 3 (horizon not capped at Lead 4)

Leads 5–8, the last leads with any evaluable quarter, were scored under the same rule (Addendum 3, frozen before
scoring). They fail (accuracy 0.36–0.40, Lead 8 0.0 on 5 rows), and none of Leads 4–8 has the 10 quarters R1 requires.
The longest credibly testable lead is 3; the maximum reliable lead stays **1**, which is 1–2 quarters after the newest
published SWS survey. Details: `../FINAL_VERIFICATION/MAXIMUM_RELIABLE_LEAD_TIME_VERIFIED.md`.
