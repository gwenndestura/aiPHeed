# ALLBASE, Phase B: experiment design (documentation only; nothing trained, run or committed)

**Basis:** `PHASE_A_AUDIT.md`. Development data: 62 labelled quarters (targets 2010-Q1..2026-Q3), all examined before.
Every result from them is **development evidence**.

## 1. Candidates (exactly three; nothing added later)

| ID | Name | Definition | Why | Weakness addressed |
|---|---|---|---|---|
| **K1** | O1a, simple average | p = 0.5 × p(C-b) + 0.5 × p(LOGIT), the same origin and lead | LOGIT ranks better (Lead-1 AUC 0.759 vs 0.702) and C-b classifies better (accuracy 0.790 vs 0.710), so the errors may partly offset | Ranking (AUC), calibration |
| **K2** | O1b, walk-forward weight | p = w(t, k) × p(C-b) + (1 − w(t, k)) × p(LOGIT), with w chosen at each origin from the past (§3) | Lets the data decide the mix without using the evaluated quarter | Same as K1 |
| **K3** | O4, C-b + reversal features | C-b's 21 inputs + the 4 features of §2 (25 inputs), refitted exactly as C-b | C-b gives persistence's call in 77% of quarters and errs mostly on reversals (10 of 13 Lead-1 errors) | R7 (2015–2020 reversals) |

**Not a candidate:**
- **C-b** is the reference.
- **LOGIT** (combined logistic) is a component of K1/K2 and a baseline, stored as `IMPROVE_V2/out/forecasts.csv`
  `name == "LOGIT"`.
- **Excluded by Phase A:** O2 (tuned logistic) and O3 (recalibration) cannot close the power gap. Ensembles beyond K1/K2
  and other boosting libraries are not justified with 62 quarters.

## 2. O4 reversal features (exact definitions; forecast-time eligibility)

Computed at each origin t from the BL readings **published before O(t)** (`hr_lib.known(d, t, "BL")`, the same series
as `h_last`). Readings are taken in quarter order; skipped SWS quarters are simply absent (no filling).

| Feature | Definition | Missing when | Already in C-b? |
|---|---|---|---|
| `z_dist` | (h_last − 11.3) / se_last, se_last = 2.908 / √(rounds of the latest quarter) | No reading | **New:** the distance in SWS sampling-error units. (Raw distance is just `h_last` shifted, so it is not added) |
| `run_side` | Signed length of the current run of readings on the same side of 11.3: +r if the last r readings are all > 11.3, −r if all ≤ 11.3 | No reading | New |
| `cross8` | Number of side changes (above ↔ not above 11.3) between consecutive readings among the last 8 known readings (with ≥ 4 readings; NaN otherwise) | < 4 readings | New: the reversal regime |
| `rev_last` | 1 if the last two changes have opposite signs (Δ₁ × Δ₂ < 0), 0 if the same sign or one is 0 | < 3 readings | New: an alternation indicator (`h_change` is Δ₁ alone) |

**Not added, because already present:**
- "recent direction" and "change in distance" = `h_change`;
- "distance" = `h_last`;
- "recent level" = `h_mean4`.

**Leakage check (Phase C).** For every origin, the 4 values must be unchanged when every SWS round published on or
after O(t) is randomized (seed 2036, 5 repetitions).

## 3. K2 weight rule (fixed)

At origin t and lead k:
- **Grid:** w(t, k) is the value in {0.0, 0.1, …, 1.0} that minimizes the Brier score of the blend over the **past
  paired forecasts** of C-b and LOGIT at lead k. These are forecasts from origins t′ < t whose target label was
  published before O(t) (`known_labels`).
- **Ties:** go to the value closest to 0.5.
- **Default:** w = 0.5 when there are fewer than 20 such pairs.

**History needed.**
- C-b's stored walk-forward forecasts exist from origin 1998-Q3.
- The stored LOGIT rows exist only from origin 2009-Q3 (`IMPROVE_V2/out/forecasts.csv`). Phase C therefore first
  **regenerates LOGIT walk-forward from 1998-Q3** with the unchanged specification (`iv2_lib.logit_lead`, F_b(T2)
  columns, per lead). It **must reproduce the stored 2009-Q3..2026-Q3 rows exactly** (max |Δp| ≤ 1e-12), or K2 falls
  back to the stored rows with the default w = 0.5 until 20 pairs exist. The fallback is disclosed.

## 4. Development folds and selection (separating selection from evaluation)

| Fold | Targets | Use |
|---|---|---|
| **S (selection)** | 2010-Q1..2017-Q4 (the first 30 or so labelled quarters) | Choose **one** candidate by the rule below |
| **E (post-selection development)** | 2018-Q1..2026-Q3 | Reported separately for the chosen candidate. Still development evidence: these quarters were examined before |
| **Full window** | 2010-Q1..2026-Q3 (62) | The 42-test Holm family, R1–R7, Algorithm 3: the comparable numbers |

**Selection rule (fixed).**
- Among K1–K3, choose the one with the lowest mean Brier over Leads 1 and 2 **on fold S**.
- It must also be no worse than C-b on fold S at either lead.
- If none is better than C-b on S, **no candidate is chosen and C-b stays.**
- Ties go to the simpler candidate (K1 < K2 < K3).

**Multiplicity disclosure.**
- Three candidates are evaluated. The full-window results of **all three** are reported, whichever is chosen.
- The chosen candidate's full-window numbers carry a selection bias. The fold-E numbers are the less biased reading.
- All of it is recorded in the registry (`PHASE_B_PREREGISTRATION.md` §5).

**Freezing.** The chosen candidate is frozen when chosen: inputs, settings, weight rule and the code commit and hash.
It then enters the prospective registry (`PHASE_B_PROSPECTIVE_REGISTRY_SPEC.md`) **before 2027-01-01**, or it waits
for the next issue date. No later change is allowed without a new protocol.

## 5. R7 investigation (a distinct failure mechanism)

**Reversal event.** Target quarter q at lead k is a **reversal** if its label side y(q) differs from the side of the
latest reading known at the origin (h_last > 11.3).
- This is exactly the set of quarters where persistence is wrong.
- The event is defined from the outcome for **scoring only**; the features (§2) use only the past.

**Reported for C-b, K1–K3 and persistence, at each lead:**
- **Reversal recall:** the share of reversal events called correctly. Persistence scores 0 by construction.
- **Non-reversal accuracy:** this shows whether reversal gains cost accuracy on stable quarters.
- **Both, by period:** the three R7 thirds (2010-Q1..2015-Q1, 2015-Q2..2020-Q4, 2021-Q2..2026-Q3) and the full window.
- **R7 itself:** each third ≥ 0.60 and the leave-one-quarter-out minimum ≥ 0.70, unchanged.

**Guard against displacement.** A candidate that raises the 2015–2020 third but lowers the full-window accuracy or
another third below 0.60 is reported as **not** fixing R7.

**Ceiling.** The Phase A noise ceiling is reported beside the results (0.773 for 2015–2020; 0.849 overall).

## 6. Expected outcomes, stated before any run

- **The all-baseline pass (G1) is very unlikely.** By Phase A, beating LOGIT at Lead 1 after Holm needs a Brier of
  about 0.107 with a family of 6, and lower with 42, against a noise floor of 0.103.
- **K1/K2** may improve AUC and Brier modestly, while classification may move toward LOGIT's lower accuracy.
- **K3** is the only candidate aimed at R7. With 21 middle-third quarters, a change of one or two quarters decides it.

## 7. Traceability matrix

| Experiment | Thesis objective | Target | Leads | Baselines | Primary metric | Acceptance gate (§ of PREREGISTRATION) |
|---|---|---|---|---|---|---|
| K1 average | Obj 2, Obj 4 / H3 | T1 (BL hunger > 11.3) | 1, 2 | All 7 | Paired Brier, 42-test Holm | G1, G2, G3, G4 |
| K2 weighted | Obj 2, Obj 4 / H3 | T1 | 1, 2 | All 7 | Same | G1–G4 |
| K3 reversal features | Obj 2 (R7, reliability), Obj 4 | T1 | 1, 2 | All 7 | Same + reversal recall | G1–G5 |
| LOGIT regeneration 1998+ | Support for K2 | T1 | 1, 2 | — | Exact reproduction | Pre-check |
| Prospective registry (O5) | Obj 2 (Algorithm 4), Obj 4 / H3 on new data | T1 | 1, 2 | All 7, C-b, K1–K3 (approved) | Sealed forecasts; F1, AUC; paired Brier | Prospective protocol |
| R7 analysis | Obj 2 (R1–R7) | T1 | 1, 2 | Persistence | Reversal recall by period | G5 |

**Multisource and NLP.** K1–K3 keep C-b's multisource inputs and its NLP input unchanged. No candidate adds news
weight, and none is claimed to improve news value. The province and LGU layers are unchanged (regional forecast +
vulnerability weighting).
