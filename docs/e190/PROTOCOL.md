# E190: truly class-balanced synthetic data for E184. Fixed before results. Local only (not committed).

Written 2026-11-10 at the owner's request ("make the synthetic data better"). The motivation comes from the E189 audit.

## Two flaws in E184's synthetic rows
1. **Uneven HIGH/LOW split.** E184's allocation gives the minority class rows only up to parity, then splits the rest
   by the real class shares. For the ENNS2018/2019 origins (real 108 HIGH / 48 LOW), real + synthetic is therefore
   still 56 % HIGH as planned.
2. **Class flips.** The outcome is redrawn as y + N(0, se) and can cross the HIGH line. Near the line, which the
   boundary focus favours, copies switch class, and the realised balance drifts (for example 66 planned → 84 realised
   synthetic HIGH in the E178 log).

## Arms (everything else is E184 exactly)
E184's settings, unchanged in every arm: E168 selection, jitter, 50/50 rows, weight 1.0, input noise 0.5 SD, boundary
focus, seeds 17901–17905. Synthetic rows stay inside the inner and final fit sets.

| Arm | Synthetic rows |
|---|---|
| E184 (re-run; must equal the stored rows) | as in E184 |
| **E190a** | **Parity allocation.** Synthetic HIGH = clip((n_real + n_syn)/2 − real HIGH, 0, n_syn), the rest LOW, so real + synthetic is exactly 50 % HIGH. |
| **E190b (primary)** | Parity allocation **and label-preserving outcomes.** A copy whose redrawn outcome crosses the HIGH line is folded back across it (y' → −y'). The copy keeps its parent's class and its distance from the line, and the realised balance is exactly 50/50. |

## Test
- Leads 1–6; ENNS2018, 2019 and 2021 origins; 72 real rows per lead.
- Same metrics as E188: accuracy, balanced accuracy, recall, specificity, false alarms, Brier.
- Brier difference against E184 with a 95 % region-cluster CI (2,000 draws, seed 188 - E188's evaluator reused unchanged), exact McNemar against E184, and the owner
  rule.
- The realised synthetic HIGH share is logged per job and seed.

## Decision
- **Preference rule.** An arm is preferred to E184 only if all three hold:
  - accuracy ≥ E184's at all six leads;
  - Brier ≤ E184's at all six leads;
  - accuracy higher at at least one lead.
- **If both qualify,** the one with the lower mean Brier is preferred. Otherwise E184 stays.
- **80 % target.** Whether Leads 1–3 reach 80 % is reported separately.
- **Scope.** Nothing is staged or deployed.
