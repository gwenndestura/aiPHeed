# E88 protocol: in-origin model selection and combination for Lead-1 and Lead-2 accuracy (frozen before scoring)

**Branch.** `e84-objective-continuation`. This file is hashed into `PROTOCOL.sha256` and committed before any E88 score.

## 1. Idea

E83–E84 produced several walk-forward forecasters on identical rows. Each is strongest in different periods:
- S-SIM is best at Lead 1;
- S-COMP is best at Lead 2;
- LightGBM is strong once it is trainable (from target 2024-Q4).

Forecast combination and selection is a standard way to gain accuracy. It is legitimate only if the choice at origin
t uses outcomes published before O(t).

## 2. Inputs (unchanged)

- **Rows.** E84 run `20261021T093234Z`, `predictions_k{1,2}.csv`: 65 rows per lead, 13 target quarters, T43.
- **Candidate pool** (all walk-forward):
  - S-SIM, S-SIM-SEAS, S-COMP, S-COMP-NOW;
  - HYB-GBA-SIM = NA-GB where it can be trained, else S-SIM.

## 3. Arms (pre-registered)

| Arm | Definition |
|---|---|
| ENS-EQ | Equal-weight mean of S-SIM, S-SIM-SEAS and S-COMP. Unweighted, so it needs no past data. |
| SEL-ROLL | At origin t, the pool arm with the lowest mean Brier on earlier rows whose target label was published before O(t). Requires at least 3 such target quarters; otherwise S-SIM. |
| ENS-ROLL | Weighted mean of the pool. Weights are proportional to 1 / Brier on the same earlier rows, with the same fallback to equal weights. |
| ENS-ROLL-ACC | ENS-ROLL with the decision threshold chosen at each origin (grid 0.30–0.70) to maximise accuracy on the same earlier rows, with ties going to 0.5. Default 0.5 when fewer than 3 quarters are available. |

## 4. Rules (unchanged from E83)

- **Pass rule (PASS).** All four of:
  1. accuracy > 0.75, with unissued rows counted as wrong;
  2. balanced accuracy > every baseline;
  3. Brier better than persistence, climatology and always-HIGH (date sign-flip, Holm p < 0.10);
  4. recall ≥ 0.5.
- **Reporting.** Leads 1 and 2.
- **Comparisons.** Each arm is also compared with the best single E83/E84 arm at that lead.
- **Caveat.** These four arms are the only additions. They reuse quarters that E83–E84 have already examined, so any
  gain is development evidence. Only the sealed prospective forecasts can validate an E88 arm.
