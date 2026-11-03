# NOISE_W: C-b trained with measurement-error weights (EXPLORATORY, one candidate)

**Written:** 2026-11-03, before the candidate below was fitted or scored. Requested by you ("improve it more"), after
C-b did not significantly beat the PSA-only and combined logistic regressions.

**Label: EXPLORATORY.**

**Evidence status, stated plainly.**
- Development evidence: every quarter 2010–2026 was examined before.
- The idea comes from the Phase 2 diagnosis (T2): C-b's errors sit on quarters whose SWS reading is within the survey's
  sampling error of 11.3%.
- **One candidate only; nothing added later.** Any gain must be confirmed on sealed 2027+ forecasts.

**What this does not change:** the target and labels used for **scoring**, the frozen R1–R7, the frontend, `backend/`,
the served model and every existing result and seal. Nothing is pushed.

**Hash.** The SHA-256 of this file is computed over every byte before its last line (`PLAN-SHA256:`). The runner
refuses to run if it changed.

## 1. The candidate C-w

**C-w is C-b with one change in training only: sample weights.** Every training row of target quarter q gets

  w(q) = max(0.10, |2 Φ((H(q) − 11.3) / se(q)) − 1|),   se(q) = 2.908 / √n(q),

where:
- **H(q)** is the BL hunger value of the training label;
- **n(q)** is its number of non-commissioned rounds;
- **2.908** = 5.7 / 1.96: SWS's published ±5.7-point 95% margin for a 300-respondent area, as one standard error.

**What the weight means.** w is how sure the label is:
- about 1 far from the line;
- near 0 for a reading within the sampling error of 11.3;
- floored at 0.10, so no quarter is dropped.

**Leakage.** The weights use only labels known at the origin (the same `known_labels` rows as the label itself).

**Unchanged from C-b:**
- inputs (19 REF columns + `z_N1R` + `lead`);
- training rows and eligibility;
- the 8-setting grid and seed.

**Inner chronological selection:** the same folds and the same **unweighted** hard-label log-loss criterion. The
weights enter **only** the LightGBM fits (`sample_weight`), via a subclass of `hr_lib.LGBM` inside this folder.
`hr_lib` is not edited.

Origins 1998-Q3..2026-Q3; training leads 1–15; test Leads 1–8.

## 2. Checks before scoring

1. **Machinery:** the same code with all weights = 1 reproduces the stored C-b Lead-1 and Lead-2 forecasts
   (max |Δp| ≤ 1e-12).
2. **Leakage:** w(q) is computed only from labels in `known_labels(d, t)` at each origin.

## 3. Scoring and decision (fixed now)

**Scoring:** the frozen R1–R7 (`hr_lib.evaluate`) on the **hard** labels, targets 2010-Q1..2026-Q3, Leads 1 and 2
separately. Reported: all metrics, R1–R7, Algorithm 3 at Leads 1–8, and Objective 4 / H3 (the same stored comparators
and Holm as `NEWS_V2/runner/align_cb.py`).

**Decision:**
- **"Improves C-b"** only if, at **both** leads, C-w's Brier is lower than C-b's (one-sided paired cluster bootstrap,
  seed 2036, 5000 draws, p < 0.10) **and** its accuracy is not lower.
- **"Beats all baselines"** only if, at **both** leads, every H3 comparator is beaten with Holm p < 0.05 (the rule
  used for C-b).
- Otherwise C-b stays the main model, unchanged. The result is reported whatever it is.
PLAN-SHA256: 0c00cedd318f6e23b09e1730e094673e3403d165f4aa39536a871fcbd432831e
