# LEAD2_OPTIMIZATION Addendum 1: LightGBM boosted from the structural price forecast (hashed before scoring)

**When.** 2026-10-27, after the frozen run (`out/results.json`). No arm improved Lead 2; P0H0 (= UNI-FINAL) was retained. Everything below is **post-hoc development evidence**.

## Why (diagnosis computed before writing this file; `out/diag_price_signal.txt`)

**M5: the LightGBM price model discards most of the structural signal.**
- **The structural feature beats the fitted models.** On the T43c evaluation rows, max(A1_food, A1_gap) has price-condition AUC 0.93 / 0.81 / 0.87 at Leads 1 / 2 / 3. The fitted P0 has 0.67 / 0.67 / 0.62, and P1 has 0.77 / 0.74 / 0.72.
  - A1 is the projected target-quarter food YoY (or gap) minus its threshold, from months ≤ m0 only. It passed the leakage audit.
- **Spurious features distort the model.** E1 is ranked inversely (AUC 0.17–0.24), a time-trend artefact.
- **Disclosure.** This diagnosis looked at all evaluation quarters, so the arm below is motivated by data it is then evaluated on.

## Known limit stated before scoring

With π_H = H0, the 7 HIGH rows of 2023-Q4 and 2024-Q2 at Lead 2 cannot reach 0.50. Recall at Lead 2 is therefore at most 10/17 = 0.588 < 0.60 **for any price model**. R6 cannot pass at Lead 2 with H0.

Only a hunger term whose π_H × π_P exceeds 0.50 in those quarters can lift this cap. In the frozen run, that is only H2 (pre-2021 history, sample b).

## Arms

**P4 (PRIOR).** One unified LightGBM, as U2 (all 12 families + lead + world prices, monotone, UNI grid, inner chronological validation). The only change: training and prediction start from the **structural prior**:

  init_score = logit(clip(STRUCT_k, 0.01, 0.99))
  STRUCT_k = 1 − (1 − Φ(A1_food/σ_f,k)) (1 − Φ(A1_gap/σ_g,k))

- σ_f,k and σ_g,k are the RMSEs of A1 against the realised excess on that fold's training rows of lead k (`e108_lib.sigmas`; fewer than 4 quarters → 2.0).
- Where A1 is missing (lead ≥ 5), the prior is the training base rate.
- LightGBM then learns only corrections from the 12 families.

**P6 (PRIOR+FE).** P4 with P1's engineered columns added as correction features.

**P5 (A1-ONLY), diagnostic, never adoptable.** P4's prior with no LightGBM corrections. It omits 11 families, so it cannot be the required model. It shows how much the corrections add or remove.

**Hunger terms.** H0 (primary). H2 (sample b; reported separately, not adoptable without a scope revision by the user).

## Selection and serving

**Selection.** Among P0H0, P4H0 and P6H0, the arm with the lowest Lead-2 development Brier (targets ≤ 2024-Q4) is adopted. Ties within 0.0005 go to the earlier arm in that order.

**Serving.** The serve rule of PROTOCOL_LEAD2 §4 is unchanged:
- reliable at Lead 1;
- maximum reliable lead ≥ 1;
- Lead-1 Brier not worse than UNI-FINAL at one-sided p < .10.

**Reporting.** All arms are reported with full R1–R7 at every lead. The sample-b arms are P4H2 and P6H2.
