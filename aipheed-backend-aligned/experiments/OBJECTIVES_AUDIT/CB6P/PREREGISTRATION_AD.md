# Pre-registration: C-B6D-E-X-PM with every risk driver in every forecast (C-B6D-E-X-PM-AD), 2026-11-05

**Owner directive:** "it should have input every risk drivers" (after the 2026-Q3 forecast used only 5 inputs).

**EXPLORATORY, owner-directed.** The same 250 province-quarters have already been examined (C-B6D-E-X, -PM). This
variant is disclosed as such and does not replace any reported result.

## What changes (only this)

- **Regional hunger part:** C-B6E's LightGBM is replaced by the C-B6P4 hybrid (`runner/cb6p4_model.Hybrid4`):
  an L2 logistic on the five driver groups' inputs (market: R_food_yoy, R_head_yoy, R_food_mom, R_rice_yoy + 5 world
  prices; climate: ONI_last, ONI_max12, tc_mean, R_C3; fish kill: R_C4; employment: E1; OFW: E2) as the LightGBM
  `init_score`, then LightGBM boosting on all C-B6E inputs (incl. past hunger and news).
- Logistic C ∈ {0.001, 0.01, 0.1, 1.0} chosen jointly with the tree setting (hr_lib.GRID, 8) on the same inner
  chronological folds by log loss; ties to the smaller C, then the lower GRID id (as C-B6P4).
- SHAP = LightGBM TreeSHAP + the logistic term coef·z for each driver input (exact, additive in log-odds).

## What does not change

- C-B6E's inputs, rows, label (BL hunger > 11.3%), stacked leads, seed, walk-forward origins (from 2012-Q3).
- Eq. 3 decomposition, D̂ = b·D1, the paper median cut-off 14.325 (PREREGISTRATION_PM.md), provinces, leads, metrics.
- Code: `runner/fi_provincial.py` run unchanged with THR = 14.325, the C-B6E regional fits swapped for these, outputs
  in `out/ad/`. Existing outputs, seals and exports are not touched.

## Acceptance

1. Each of the five driver groups has |SHAP| > 0 in at least 99% of scored forecasts (Leads 1, 2, q ≥ 2013-Q1).
2. Accuracy at least 0.75 at Leads 1 and 2 (B-ext).
3. Brier not worse than C-B6D-E-X-PM by more than 0.01 at either lead.

## Decision rule

- Reported whatever the result. No tuning, no further variant on these rows.
- A local demo export may be written to `backend/data/foodinsecurity_engine_cb6dexad/`; served model unchanged.
PLAN-SHA256: e0177622496861f2238a0b9a59bbf55c68bb93176111d320b7b76e1767ce1f91
