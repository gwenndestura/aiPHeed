# Memo for the adviser: evaluation rule for new survey outcomes (decision needed BEFORE any new outcome is scored)

## Request
Confirm (or reject) the evaluation rule locked in `docs/e171/PROTOCOL.md` section 3. It applies to all sealed models (E158, E166, E168, E170, E171) when new provincial HFIAS outcomes are scored.

## The rule
| Criterion (definitions unchanged from E156) | Computed on |
|---|---|
| C1 accuracy above majority (effective-n lower bound) | historical 72 rows **plus** new rows |
| C2 beats persistence; C3 HIGH and LOW recall; C5 rounds; C6 n ≥ 40 | historical plus new |
| **C4 calibration slope CI includes 1** | **new rows only, once there are 40 or more** |

The original rule (C4 on historical plus new) is always reported beside it.

## Why C4 moves to new rows
1. **Power.** With 72 rows from 3 rounds, the C4 test rejects a truly calibrated model about **21 %** of the time (simulation, E169 `reliability_decomposition.json`).
2. **Cause.** The historical miscalibration comes from a known, explained event: the 2015-anchored level drift, which no as-of data could reveal. Pooling those rows would re-test that event, not the models.
3. **Timing.** The rule is fixed before any new outcome is seen, and every forecast it will judge is already sealed. It cannot be tuned to a result.

## What new data can achieve
- **The 2022 follow-up survey** has 16 provinces in the sealed panel, about 16 new rows per lead.
  - C1 for the best models needs roughly **14 or more of the 16** classified correctly (pooled lower bound above the majority rate). The exact figure depends on the HIGH share in 2022.
  - C4 under this rule needs **40 or more new rows**, so it requires the 2022 round **plus** the next provincial HFIAS round.
- **If you do not confirm the rule,** C4 stays pooled. The historical rows then make a C4 pass unlikely for every model, regardless of new data.

**Decision:** ☐ Confirm  ☐ Reject (keep original E156 rule)  — signature / date
