# PREREG_LEAD2 addendum 2: M3, the mid-quarter update

**Written:** 2026-11-02, before any 2027 outcome exists.

**Adds to** `PREREG_LEAD2.md` (sha `91fe94e0…`) and addendum 1 (sha `662fc2d7…`), and changes nothing in them. In particular, the primary hypothesis stays **M0 under D0**.

**Hash.** The SHA-256 of this file is computed over every byte before its last line, which begins `PREREG-SHA256:`.

## 1. Origin

M3 was scored on the closed 2023–2026 rows in `LEAD2_MIDQUARTER_UPDATE` (plan sha `6b5bff74…`). Its results there were 11/8/6/40, accuracy 0.785, balanced accuracy 0.740, precision 0.579, recall 0.647, failing R6 only. That is the fifth variant scored on those rows, so it is development evidence only.

The rule exploration (plan sha `7b78e9b8…`) found **no improvement after cross-validation**. Its fixed selection rule picked h × p ≥ 0.45, which is registered below as the alternative.

## 2. Candidate C3 = M3 (fixed exactly)

| Item | Definition |
|---|---|
| Issue date | D(t) = the first day of the second month of quarter t+1 (2026-Q3 → 2026-11-01; 2026-Q4 → 2027-02-01) |
| Target | Quarter t+2 |
| Hunger part h | H4 at D(t): the newest Balance Luzon SWS round published before D(t) (`LEAD2_POST_SWS_ISSUE/runner/score.h4_at`) |
| Price part p | The served P0 arm refitted walk-forward, with every origin's CPI cutoff (test and training) = the newest month available at D(t) (month M from the first day of M+2). World prices and every other input as served (`LEAD2_MIDQUARTER_UPDATE/runner/run_m3.py`, `price_refit.py`) |
| Probability | h × p |

**Decision rules:**

| ID | HIGH when |
|---|---|
| **M3-D0** | h × p ≥ 0.50 |
| **M3-E1** (alternative, from the exploration) | h × p ≥ 0.45 |

**Baselines (sealed alongside):** PERSIST-SI and CLIM at D(t), and always-LOW.

## 3. Seals, evaluation and claims

- **Seals.** Seals are written by `backend/scripts/seal_lead2_m3.py` to `backend/seals/<D>_<target>_M3.json` and appended to `LEDGER.md`. Seals made after D(t) are late and excluded. The first seal, D = 2026-11-01 → 2027-Q1, is written on 2026-11-02 and is therefore late.
- **Evaluation.** Same metrics, the same R1–R7, and the same minimums as `PREREG_LEAD2.md` §6–§7: no claim before 8 resolved on-time quarters, and a seven-rule pass only from 10.
- **Multiplicity.** The tested hypotheses are now M0 under D0 (primary), D1, A1, A2, M3-D0 and M3-E1. Every report lists all of them. A pass by M3 alone is reported as "the mid-quarter update passed on sealed quarters", with its exploratory origin stated. It is never reported as the original Lead 2, which is issued on the first day of the quarter.

PREREG-SHA256: 0b3bf735e2b32282baa95e1d498ee14244380d005d593e003ce51f00b5964ac4
