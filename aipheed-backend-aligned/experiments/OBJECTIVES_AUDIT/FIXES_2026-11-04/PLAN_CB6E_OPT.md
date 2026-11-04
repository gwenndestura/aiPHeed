# C-B6E-OPT: nested optimisation of C-B6E (pre-registration, fixed before any fit, 2026-11-04)

**Owner directive (2026-11-04):** "you should optimize it", i.e. C-B6E (C-B6 + employment E1 + OFW remittance E2),
after C-B6E failed R5 and R7 (`FIXES_REPORT.md`, Fix 5).

**Development evidence:** attempt 27 on the same 62 quarters, disclosed as such.

## Principle: optimise without touching the test quarters

All tuning happens **inside** the walk-forward. At each origin t, the setting is chosen by the existing inner
chronological folds (`hr_lib.inner_folds`: the last 4 training origins, each fitted only on rows whose target precedes
it), scored by log loss on the held-out training origins. No outer verdict quarter is ever used to choose a setting.

This is the same selection rule C-b and C-B6 already use, applied to a larger search space fixed here.

## Search space (32 settings, fixed)

`hr_lib.GRID` (8: depth 1/2 × 50/150 trees × class weight none/balanced) ×

- **Direction constraints** (off / on), chosen from economic theory before any fit:

  | Input | Constraint | Meaning |
  |---|---|---|
  | E1 | +1 | rising unemployment can only raise risk |
  | E2 | +1 | a remittance decline can only raise risk |
  | ST1 | −1 | falling rice stocks can only raise risk |
  | all others | 0 | as in C-B6 |

  LightGBM `monotone_constraints_method="basic"`.
- **Regularisation:** `min_child_samples` 15 (as served) / 30 (more conservative, so weak national inputs cannot fit
  noise).

Everything else is as in `hr_lib.LGBM`: learning rate 0.05, reg_lambda 5, seed 2027, deterministic.

- **Ties:** the lowest log loss wins, rounded to 1e-9; then the lower setting id. Setting ids are ordered GRID-major,
  then mono off/on, then mcs 15/30, so setting 0 is the served C-B6 setting 0.
- **Fallback:** as `cb6_model._origin`.

## Candidate (exactly one)

- **C-B6E-OPT** = C-B6E's 25 inputs (C-B6 + E1 + E2, as `PLAN_CB6E.md`), with the 32-setting nested selection above.
- **Replication gate:** with the search space restricted to GRID × {mono off, mcs 15}, the code must reproduce the
  stored C-B6E forecasts (`out/cb6e_fits.csv`, < 1e-9), or the run stops.
- **No further variant** will be tried after seeing the results.

## Evaluation and serving rule (as PLAN_CB6E.md)

- **Reported:** all metrics, calls changed vs C-B6 and C-B6E, R1–R7, Algorithm 3, paired Brier vs C-B6, the 14-test
  Holm family with PERSIST-P, SHAP shares of E1/E2, and how often each setting was chosen.
- **Served automatically** in place of C-B6 only if it passes R1–R7 at Leads 1 and 2 **and** has accuracy ≥ 0.75 at
  both leads. Otherwise the trade-off goes to the owner.
- "Employment and remittances improve the forecast" is claimed only if its Brier is below C-B6's at Lead 1 with
  one-sided p < 0.05.

**Reported whatever the result.**
PLAN-SHA256: 0d0c310170b5f8207905283a2ba5cc3f5dea97f90b09a7c0ac652e23222efe48
