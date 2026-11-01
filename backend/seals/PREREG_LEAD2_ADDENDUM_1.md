# PREREG_LEAD2 addendum 1: two decision rules from the exploration

**Written:** 2026-11-01, before any 2027 outcome exists.

**Adds to** `PREREG_LEAD2.md` (sha `91fe94e0…`) and changes nothing in it:

- its candidates C0–C2;
- its rules D0 and D1;
- its metrics and R1–R7;
- its claim conditions (§7), including its primary hypothesis, M0 under D0.

**Hash.** The SHA-256 of this file is computed over every byte before its last line, which begins `PREREG-SHA256:`. `backend/scripts/score_seal.py` checks it.

## 1. Origin

These rules were chosen by `LEAD2_EXPLORATION` (plan sha `b96368fd…`, fixed before any result) on the closed 2023–2026 rows. That search is **exploratory**: those rows were examined many times.

The rules' cross-validated results there (5 of 6 of R2–R7, failing R6) are no better than M0 under D0 in the number of rules passed. They are registered because they make different precision/recall trade-offs. Their development results are context only, never evidence.

## 2. The two rules (fixed exactly)

Both are computed from the parts already stored in every seal (`candidates.C1_M0` and `candidates.C2_M2`), so no seal changes.

| ID | Parts | HIGH when | Probability (AUC, Brier, R5) |
|---|---|---|---|
| **A1** | Post-SWS hunger part h = `C2_M2.hunger`; M2 price part p2 = `C2_M2.price` | h ≥ 0.50 **and** p2 ≥ 0.45 | h × p2 (= `C2_M2.probability`) |
| **A2** | h; mean price p̄ = (`C1_M0.price` + `C2_M2.price`) / 2 | h × p̄ ≥ 0.50 | h × p̄ |

**Baselines:** as sealed at O'(t).

## 3. Evaluation and claims

- **Rows:** on-time seals only, as in `PREREG_LEAD2.md` §5–§7. Late seals are excluded.
- **Metrics and rules:** exactly the same. The classification rules (R2, R3, R4, R6, R7) use the HIGH/LOW decision; R5 and AUC/Brier use the probability above.
- **When:** no claim before 8 resolved on-time quarters. A seven-rule pass is possible only from 10 (R1).
- **Multiplicity:** A1 and A2 are two further pre-registered hypotheses beside the primary. Every report gives all three, and says that three were tested.
- **What may be claimed:** if only A1 or A2 passes, the report says so, names the rule, and states that it was chosen by exploration on the 2023–2026 quarters. "Lead 2 is reliable" without qualification may still be said only under `PREREG_LEAD2.md` §7.
- **Wording:** both are post-SWS-issue rules and are never described as the original Lead 2.

PREREG-SHA256: 662fc2d77a6c2be2834e3a8703302a3d553bfe5669fa9ed433fafd4df92787f9
