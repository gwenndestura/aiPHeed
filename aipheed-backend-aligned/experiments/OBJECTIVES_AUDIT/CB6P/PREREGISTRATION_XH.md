# C-B6D-E-XH pre-registration: Lead 2 hunger component using the paper's H1/N1 momentum variables (fixed 2026-11-04, before any fit)

**Authority:** the thesis.
- Chapter I 1.2: "temporal momentum features", the FSSI, the composite Eq. 3 label.
- Chapter I 1.3 RQ3 and H3: the baselines.
- Chapter III indicator families (`FINAL_ARCHITECTURE/METHODOLOGY_WORKFLOW_CH3.md` §2): **H1** "regional hunger outlook
  and recent SWS readings", "run above or below 11.3", "other SWS areas"; **N1** news food-stress signals; **E1**, **E2**.

**No new variable family is added.** Equation 3 (S = H + 2D), the 11.0 cut-off and the objectives are unchanged.

**Disclosed deviation, already pending adviser approval:** the paper's Eq. 3 threshold is the median over **all**
province-quarters. 11.0 is the 2021–22 median, the leak-free version (CH3_AMENDMENT §1). It is not changed here.

**Development evidence.** The 250 province-quarters (2013–2026) were examined before; the untouched test is the
prospective seal.

## Why

- **C-B6D-E-X Lead 2 errors are mostly hunger-part errors** (67%; oracle accuracy 0.888;
  `PROVINCIAL_CB6_IMPROVEMENT_REPORT.md`, X2 update).
- **The regional model uses h_last, h_change, h_mean4, true_h and pi_H4L** but none of the H1 momentum, run or
  other-area constructions the paper lists, and no FSSI momentum.

## New features (H1 / N1 constructions only; computed from data published before O(t))

Let kn = the BL readings known at O(t) (`hr_lib.known`), in quarter order.

| Feature | Definition |
|---|---|
| `h_change2` | kn[-1] − kn[-3] (two-reading momentum) |
| `h_accel` | (kn[-1] − kn[-2]) − (kn[-2] − kn[-3]) |
| `h_run` | +n for n consecutive latest readings > 11.3; −n for n consecutive readings ≤ 11.3 ("run above or below 11.3") |
| `x_level` | mean latest known hunger of the other SWS areas (NCR, VIS, MIN), known at O(t) |
| `x_change` | mean of the latest change in NCR, VIS, MIN |
| `z_lag1` | `z_N1R` at origin t − 1 (FSSI lag) |
| `z_accel` | z_N1R(t) − z_N1R(t − 1) (FSSI momentum) |

Missing (fewer readings, no news) → NaN; LightGBM handles NaN as in C-B6.

## Model

1. **C-B6E-H (regional):** C-B6's procedure exactly (`cb6_model._origin`, BL rows, inner-fold grid, walk-forward from
   1998-Q3, leads 1–8) on C-B6E's 25 inputs + the 7 features above (32).
2. **C-B6D-E-XH (provincial):** C-B6D-E-X's decomposition exactly (spliced D1, THR 11.0, `fi_provincial.py` logic),
   with the regional part from C-B6E-H.

## Baselines (Chapter I RQ3), provincial, on identical B-ext rows

- **PERSIST-X; CLIM-X** (stored).
- **LightGBM government-only ablation:** PSA-only-P-X (stored in `out/x2_fits.csv`).
- **Logistic regression, three variants** (`hr_lib.logit`: median impute, standardise, L2 C = 1). Trained at each origin
  on the past province rows of the same lead with labels known at O(t); base rate if fewer than 20 rows or one class.
  - **LOGIT-COMB-P:** h_last, h_change, R_food_yoy, R_rice_yoy, E1, E2, z_N1R, D1.
  - **LOGIT-GOV-P:** h_last, h_change, R_food_yoy, R_rice_yoy, E1, E2, D1.
  - **LOGIT-NLP-P:** z_N1R. Scored on q ≥ 2021-Q1 only (the news era).
- **Also reported:** C-B6D-E-X (reference), C-B6-R (C-B6), C-B6P2 and C-B6D-E on B-old.

## Evaluation

- **Samples:** B-ext (q ≥ 2013-Q1) is primary; B-old (q ≥ 2021-Q1) is reported. Leads 1 and 2 separately.
- **Metrics:** accuracy, balanced accuracy, precision, recall, F1, AUC (quarter-cluster bootstrap 95% CI), Brier.
- **R1–R7:** frozen `rules()`, with PERSIST-SI = PERSIST-X and CLIM = CLIM-X.
- **Algorithm 3:** leads 1–8.
- **Regional hunger component:** C-B6E-H vs C-B6E on measured BL hunger > 11.3% (62 quarters; `phase_c._summ`,
  `_paired`).
- **Holm family (14):** XH minus the comparator, paired Brier, quarter-cluster bootstrap, one-sided. Comparators:
  C-B6D-E-X, PERSIST-X, CLIM-X, PSA-only-P-X, LOGIT-COMB-P, LOGIT-GOV-P, LOGIT-NLP-P (news era); Leads 1 and 2.

## Decision rules (fixed)

- **Lead 2 fixed:** XH passes all R1–R7 on B-ext at Lead 2.
- **Lead 1 preserved:** XH passes all R1–R7 at Lead 1, with accuracy ≥ 0.752 (0.772 − 0.02).
- **Improvement over C-B6D-E-X at Lead 2:** Holm p < 0.05.
- **Adoption as the provincial candidate** requires all three. Otherwise C-B6D-E-X stays the candidate.
- **No further variant on these data.** XH and C-B6D-E-X are both added to the prospective record.
**Reported whatever the result.**
PLAN-SHA256: 2b32270c9768d798694af3d65e4373b16326d80006b2ae09a4ab5aab992e12ef
