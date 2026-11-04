# ALLBASE, Phase B: pre-registration (hashed at the Phase C authorization, before any run)

**Status:** approved with the revisions of §6. This file is hashed (SHA-256 over every byte before the final
`PLAN-SHA256:` line) **before** any Phase C run and checked by every Phase C runner. Committing it is not authorized
yet; until it is committed, the hash is recorded in `REGISTRY.csv` and in every Phase C output.

## 1. Hypotheses

| ID | Hypothesis | Test |
|---|---|---|
| HB1 | At least one of K1–K3 lowers the Brier score below C-b's at both leads | Paired one-sided cluster bootstrap, p < 0.10 at each lead (G2) |
| HB2 | A candidate beats all 7 baselines at both leads | 42-test Holm family, all 14 of its adjusted p < 0.05 (G1) |
| HB3 | K3 calls more reversal events correctly than C-b without lowering full-window accuracy | Reversal recall and accuracy (§5 of the design; no inference) |
| HB4 | The chosen candidate passes R7 at both leads | Frozen R7 (G5 / G3) |

## 2. Fixed elements

**Unchanged from C-b:**
- target T1;
- labels;
- the 62-quarter window;
- C-b's settings and code (for K3, only the 4 features are added);
- LOGIT's specification;
- the frozen R1–R7;
- Algorithm 3 (75%, minimum 8-quarter window, k = 1..8);
- bootstrap seed 2036 with 5000 draws.

**Not used in Phase C:** the sealed 2027 quarters, whose labels are never read.

## 3. Pre-checks (a candidate is not scored if one fails)

1. **C-b:** refit with C-b's columns reproduces the stored C-b (max |Δp| ≤ 1e-12).
2. **LOGIT:** regenerating LOGIT from 1998-Q3 reproduces the stored 2009-Q3+ rows; otherwise the disclosed fallback
   (design §3).
3. **Leakage:** the O4 features and the K2 weights are unchanged under randomization of every value published on or
   after O(t).
4. **Baselines:** all comparators are read from their stored files, unchanged (design: Phase A §2).

## 4. Acceptance gates and rejection criteria (fixed now)

| Gate | Pass condition | If it fails |
|---|---|---|
| **G1 all-baseline** | In the single 42-test Holm family (3 candidates × 7 comparators × 2 leads), **every one of the candidate's 14** paired Brier differences is < 0 with Holm-adjusted p < 0.05 | **No all-baseline claim.** Report every comparison as it is |
| **G2 improves C-b** | Brier lower than C-b's at **both** leads (one-sided p < 0.10 each) **and** accuracy not lower at either lead | **Rejected as an improvement**; C-b stays |
| **G3 R1–R7** | All seven rules pass at both leads | Reported as failing; no relaxation |
| **G4 Algorithm 3** | MRLT ≥ 2 | **Rejected** (it would lose Lead 2) |
| **G5 R7 targeted (K3)** | 2015–2020 third ≥ 0.60 at both leads, LOOQ minimum ≥ 0.70, and no other third below 0.60, and full-window accuracy ≥ C-b's | Not counted as fixing R7 |

**Adoption as the new main model** requires **G2 and G4**. It is then recorded as a team and adviser decision,
together with G1, G3 and G5 as they come out.

**Automatic rejection:**
- a failed pre-check;
- any use of 2027 labels;
- any change to the candidate list, folds, family, test or gates after the first Phase C result.

## 5. Experiment registry (one row per run; never overwritten)

The registry lives in `ALLBASE/REGISTRY.csv`, with these fields:
- experiment ID;
- date;
- branch and commit;
- target;
- lead;
- dataset version (input hashes);
- feature groups;
- model and settings;
- validation design (fold);
- seed;
- metrics;
- the 14 paired comparisons of the candidate (diff, raw p, 42-test Holm p, n);
- R1–R7 status;
- G1–G5 status;
- accepted or rejected;
- limitations.

**Prior experiments** (Phase A §4: E99, P0H4, HISTORY_RETRAIN, IMPROVE_V2 arms, RELIABLE_L12, RELIABLE_NEWINFO,
OLD_NEWS, NEWS_V2 C-a/C-b, NOISE_W) are entered first, from their stored results, marked "prior". K1–K3 are therefore
never presented as first attempts.

## 6. Revisions approved at the Phase C authorization (2026-11-03, before any run)

1. **Holm family:** one family of 42 tests (3 candidates × 7 baselines × 2 leads), replacing the 14-test family. All
   42 are reported, including failures.
2. **Prospective registry:** seal all seven baselines, C-b and K1–K3 at Leads 1 and 2
   (`PHASE_B_PROSPECTIVE_REGISTRY_SPEC.md`). The prospective comparison is a separate family from the historical one.
3. **K2:** weights use only forecast–outcome pairs available before the issue date; w = 0.5 with fewer than 20 pairs;
   the regenerated LOGIT follows the original issue-date cutoffs (labels known at O(t) only).
4. **K3:** the four features are verified by a second, independent implementation and by the leakage check.
5. **Unchanged:** R7's definition and periods; no quarter is removed; period-specific and full-period results reported.
6. **No promotion:** even if G2 and G4 pass, replacing the production model is not authorized by Phase C.
PLAN-SHA256: 5001657e4ef3ed9081d619f6968968bc4b5ea706520cfb2755f59f95656f6501
