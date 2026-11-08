# FINAL_UNIFIED_LGBM Addendum 1: improvement arms after the frozen confirmatory run (post-hoc; hashed before scoring)

**When.** Written on 2026-10-27, after `run_uni.py score` produced the frozen UNI-FINAL results (`out/results.json`, protocol `889e55e8`). The variants below were not scored before this file was hashed. The confirmation quarters (2025-Q2..2026-Q3) **have been seen**, so every result of these arms is **post-hoc development evidence**. UNI-FINAL's frozen verdict stands as the confirmatory result.

## Why

UNI-FINAL (U2 + π_H):

| Lead | Accuracy | Balanced accuracy | HIGH recall | AUC |
|---|---|---|---|---|
| 1 | 0.829 | 0.767 | 0.65 | 0.88 (reliable) |
| 2 | 0.769 | 0.635 | 0.35 | 0.59 |
| 3 | 0.750 | 0.648 | 0.41 | 0.72 |

Two defects can be addressed without touching labels, rows or the reliability rule:

1. **Capacity for lead differences.**
   - The grid allows depth ≤ 2.
   - The single model loses to the per-lead CH1 model at Lead 1 (0.829 vs 0.914; Brier significantly worse, p = .022).
   - A unified model can only treat leads differently through tree interactions with `lead`.
2. **Decision cutoff.**
   - HIGH is called when π_H·π_P ≥ 0.5.
   - At a base rate near 0.25, the compressed longer-lead probabilities rarely cross 0.5, so recall stays low.

**Known ceiling, stated before scoring.** With an AUC of 0.59 at Lead 2, no cutoff can reach balanced accuracy 0.70. These arms can recover Lead 1 and might move Lead 3; they cannot make Lead 2 pass unless discrimination itself improves.

## Arms (all one unified LightGBM; same rows, labels, π_H and reliability rule R1–R7)

| Arm | Change from UNI-FINAL (U2 columns, monotone constraints, news on) |
|---|---|
| **U4** | Grid depth ∈ {2, 3} with leaves 3 / 7, trees ∈ {50, 150}, class weight ∈ {none, balanced}; min child 15; same inner chronological validation (lowest log-loss) |
| **U3** | U2's model with an **in-fold decision cutoff** τ ∈ {0.20, 0.25, …, 0.50}. τ is chosen at each origin on the inner folds (the last 4 training origins held out in turn), scoring π_H · π_P(inner) against the T43c labels known at O(t) (`known_t43c(t)`). It maximises balanced accuracy among cutoffs whose inner accuracy is within 0.05 of the inner accuracy at 0.5; ties go to the larger τ. |
| **U5** | U4's model with U3's cutoff rule |

**Rules for the cutoff arms.**
- The **class call** uses τ.
- **Brier and every probability test** use the raw probability π_H · π_P, unchanged.
- Each arm's no-news twin (same arm, news columns removed) is also scored, for the news test.

## Selection (development targets ≤ 2024-Q4, Leads 1–4 only)

1. **Capacity:** U4 replaces U2 only if its mean development Brier on T43c is lower (ties keep U2).
2. **Cutoff:** the cutoff rule (U3, or U5 if U4 won) is adopted only if:
   - mean development balanced accuracy rises;
   - mean development accuracy drops by no more than 0.03.

   Otherwise the cutoff stays 0.5.
3. **Result:** the selected arm is **UNI-IMPROVED**.

## Reporting

**For UNI-IMPROVED, at every lead:**
- the frozen R1–R7 verdict;
- the comparison with UNI-FINAL and with the per-lead CH1-LGBM.

All of it is labelled post-hoc.

**The served model** follows the user's directive of 2026-10-27: one unified LightGBM is the final methodology. This supersedes the per-lead CH1-LGBM as the served method; CH1-LGBM's results stay reported for comparison.
- The served unified model is **UNI-IMPROVED** if it is reliable at Lead 1.
- Otherwise it is **UNI-FINAL**.

The protocol's earlier serve rule (§5, keep CH1 if UNI is worse at Lead 1) is overridden by that directive, and the override is disclosed.
