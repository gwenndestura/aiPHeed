# Pre-registration: C-B6D-E-X with the paper's median cut-off (C-B6D-E-X-PM), 2026-11-05

**Owner directive:** "follow what's in the paper but make sure it is still provincial-quarter".

## What changes (only this)

- **Cut-off:** Ch. III Eq. 3 says a province-quarter is HIGH when S_p,t = H_t + 2·D_p,t is above the **median**.
  Primary: the median of S over all 250 evaluation province-quarters (2013-Q1..2026-Q3) = **14.325** (computed from
  `out/fi_labels_ext.csv` before this plan was hashed; no model output was looked at).
  This replaces the leak-free 2021–22 median (11.0) used by C-B6D-E-X.
- **Known property, stated in advance:** the all-period median uses later quarters to set the cut-off for earlier ones
  (look-ahead in the label definition). It is the paper's rule, so it is followed; results are labelled accordingly.

## What does not change

- Eq. 3 itself, the five provinces, province-quarter units, Leads 1–8, issue dates, CPI splice, D̂ = b·D1.
- The regional hunger part: the existing C-B6E walk-forward fits (with employment E1 and OFW E2, and news). **No
  refit.** Only the combination P = Φ((μ_H + 2D̂ − c)/√(σ_H² + 4σ_D²)) uses the new c.
- Code: `runner/fi_provincial.py` run unchanged with THR = c and outputs redirected to `out/pm/`. Existing outputs,
  seals and exports are not touched.

## Evaluation (same as PREREGISTRATION_FI.md)

- B-ext (q ≥ 2013-Q1), Leads 1 and 2: accuracy, balanced accuracy, precision, recall, F1, AUC, Brier; frozen R1–R7;
  Algorithm 3; Holm family vs PERSIST-X, CLIM-X, C-B6-R, PO-P-X, NP-P-X.
- B-old comparisons with C-B6D-E / C-B6P2 are printed but not interpreted (those were fitted to the 11.0 labels).
- **Sensitivity:** median over all 270 labelled province-quarters (2012-Q1..2026-Q3) = 14.42, reported only.

## Decision rule

- Reported whatever the result. No tuning, no further variant on these rows.
- Served model and production export unchanged; a local demo export may be written to
  `backend/data/foodinsecurity_engine_cb6dexpm/`.
PLAN-SHA256: 52f3c569946c4c43cf6491a12f25886351d0b5cfc32c1537bb6e60dc99b86542
