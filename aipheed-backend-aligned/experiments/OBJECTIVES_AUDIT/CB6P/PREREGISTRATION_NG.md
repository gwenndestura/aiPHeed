# Pre-registration: C-B6D-E-X + the teammate's FI6-N news (C-B6D-E-X-NG), 2026-11-05

**Owner directive:** use `aiPHeed_Best_News_Dataset_FI6N.xlsx` in the provincial model.

**EXPLORATORY.** The same 250 province-quarters have been examined by earlier variants; this tests one new input,
disclosed as such. It is not a hyperparameter change.

## What changes (only this)

- The regional hunger part (C-B6E) gets one more input: `z_G`, the FSSI-v2 news anomaly built from the teammate's
  FI6-N archive exactly as in C-B7 (`CB7_ADDENDUM_1.md`, 99dc56d7…; `out/cb7_features.csv`, unchanged).
- Fit: `cb6_model._origin` unchanged (LightGBM, hr_lib.GRID chosen on inner folds), columns = C-B6E's + `z_G`,
  walk-forward origins from 2012-Q3.

## What does not change

- Eq. 3 decomposition, D̂ = b·D1, the C-B6D-E-X cut-off 11.0 (served on localhost), provinces, leads, metrics.
- `runner/fi_provincial.py` run unchanged with the C-B6E regional fits swapped for these; outputs in `out/ng/`.

## Acceptance (all must hold, B-ext, Leads 1 and 2)

1. Brier lower than C-B6D-E-X at both leads.
2. Accuracy not lower than C-B6D-E-X at either lead.

## Decision rule

- Reported whatever the result. No tuning, no further variant on these rows.
- Only if accepted, localhost switches to `backend/data/foodinsecurity_engine_cb6dexng/`; otherwise it stays on
  C-B6D-E-X.
PLAN-SHA256: 31048a901200938a6193bda65fe92fc438827b1588ec64204edd8639a3c2e2f2
