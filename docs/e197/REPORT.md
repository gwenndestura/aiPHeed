# E197 results: training-side F1 cut-off. Not adopted. Local only.

Protocol: `docs/e197/PROTOCOL.md`, fixed before results. Output: `backend/data/e197/out/results.json`.

## Cut-offs chosen on training rows only

| Training set | Cut-off | HIGH share in training rows |
|---|---|---|
| ENNS2018 | 0.40 | 0.692 |
| ENNS2019 | 0.40 | 0.692 |
| ENNS2021, Leads 1–2 | 0.45 | 0.519 |
| ENNS2021, Leads 3+ | 0.35 | 0.518 |

## Outer results (72 rows per lead)

| Lead | E196 (0.50): accuracy / F1 / precision / recall | E197: accuracy / F1 / precision / recall |
|---|---|---|
| 1 | 81.9 % / 0.772 / 0.69 / 0.88 | 68.1 % / 0.667 / 0.52 / 0.92 |
| 2 | 80.6 % / 0.759 / 0.67 / 0.88 | 69.4 % / 0.676 / 0.54 / 0.92 |
| 3 | 79.2 % / 0.746 / 0.65 / 0.88 | 70.8 % / 0.696 / 0.55 / 0.96 |

## Decision
**Not adopted.** E197 fails all three conditions at every lead. E196 keeps the 0.50 cut-off, and its F1 is
reported as 0.772 / 0.759 / 0.746.

## Why it failed
- **Training rows are mostly HIGH.** HIGH is 52–69 % of the training rows, against 35 % (25 of 72) in the test rows.
- **So the chosen cut-offs are low.** The F1-maximising cut-off sat below 0.50 for every training set.
- **Effect on the test rows.**
  - One to two extra HIGH outcomes are caught at each lead.
  - About 9–11 extra false alarms are added.
- **Moving the cut-off to reach the target is not allowed.** Choosing a cut-off to lift Lead 3's F1 to 0.75 would use the
  72 test outcomes, which the protocol and Chapter IV forbid.

## Note added after the run (2026-11-11): which F1 the thesis targets
- **What the protocol compared.** This protocol tested the HIGH-class F1 against 0.75.
- **What the thesis actually targets.** Algorithm 4's target is **weighted F1 ≥ 0.75**
  (`app/ml/training/evaluator.py`, `lightgbm_weighted_f1_target`, committed 2026-11-08).
- **E196 already meets that target** at the 0.50 cut-off:
  - weighted F1 is 0.823 / 0.810 / 0.797 at Leads 1–3, and 0.769 at Lead 4;
  - the source is `backend/data/e196/out/thesis_metrics.json`.
- **No change to the decision.** E197 is still not adopted, and the HIGH-class F1 stays reported as 0.772 / 0.759 / 0.746.
