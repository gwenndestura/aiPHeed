# FI-FOCUS pre-registration: food-insecurity focus and extended provincial history (fixed 2026-11-04, before any fit)

**Development evidence.** Two parts, both fixed before any fit or score.

## Part A: Is the forecast food-insecurity driven or price driven? (regional, measured hunger)

**Outcome: measured food insecurity.** SWS Balance Luzon involuntary hunger > 11.3% (`iv2_lib.area_labels`, BL), on
C-B6's 62 verdict quarters, Leads 1–2 (Algorithm 3: Leads 1–8). This is the measured food-insecurity signal; no price
enters the outcome.

**New regional fits** use C-B6's procedure exactly (`cb6_model._origin`: BL rows, inner-fold grid selection, walk-forward
from 1998-Q3, seed and leads unchanged), with these input sets (all + `lead`):

| Arm | Inputs |
|---|---|
| FULL (= C-B6E, stored fits) | C-B6's 23 + E1 employment + E2 OFW |
| NP (non-price) | hunger (h_last, h_change, h_mean4, true_h, pi_H4L), climate (ONI_last, ONI_max12, tc_mean), crops R_C3, fisheries R_C4, rice stocks ST1/ST2, E1, E2, news z_N1R |
| PO (price only) | R_food_yoy, R_head_yoy, R_rice_yoy, R_food_mom + five world prices |
| HO (hunger only) | the five hunger inputs |

**Decision rules (paired Brier, `phase_c._paired`, cluster bootstrap by quarter, one-sided):**

- **A1 non-price indicators improve food-insecurity forecasting:** FULL < PO at both leads, p < 0.10.
- **A2 prices add beyond the non-price inputs:** FULL < NP at both leads, p < 0.10.
- **A3 the non-food-price drivers add beyond hunger history:** NP < HO at both leads, p < 0.10.
- **Price reliance (descriptive):** FULL's mean |SHAP| share of price inputs vs the hunger inputs, and accuracy of PO vs
  FULL.

## Part B: Extended provincial history (Eq. 3)

**New data (fetched 2026-11-04; `data/raw/FETCH_LOG.json`):** PSA OpenSTAT provincial CPI year-on-year, Food, for the
five provinces:

| Table | Base | Use | Months |
|---|---|---|---|
| `0012M4ACPI2` | 2012 | before 2019 | 2012-01..2018-12 |
| `0012M4ACP10` | 2018 | from 2019 | 2019-01..2020-12 |
| existing E40 file | 2018 | unchanged | 2021-01.. |

**Splice checks (before this plan):**
- the 2018 base equals E40 exactly (2021–25);
- the 2012 base vs the 2018 base on 2019–21: province deviation D correlation 0.93, mean |difference| 0.42.

**Disclosed:** current vintage (PSA revisions are rare); base change at 2019-01.

**Labels:**
- Eq. 3 on every quarter with BL hunger and three months of D, **THR = 11.0 unchanged** (the 2021–22 median; the existing
  labels for 2021+ are identical).
- Known at O(t) by C-B6P's rule.

**Arms (C-B6D's decomposition and code, with only the D series and the label set extended):**

| Arm | Regional part | Province part |
|---|---|---|
| **C-B6D-E-X** | C-B6E | D1 on the spliced series |
| NP-P-X | NP | D1, spliced |
| PO-P-X | PO | D1, spliced |
| PERSIST-X | last province label known at O(t) | — |
| CLIM-X | share HIGH among the province labels known at O(t) | — |
| C-B6-R | C-B6's regional p | — |

**Samples:**
- **B-old:** the same 100 province-quarters (2021-Q1..2026-Q3), identical rows. Compare with C-B6D-E and C-B6P2.
- **B-ext:** every labelled province-quarter with q ≥ 2013-Q1. Primary for R1–R7, Algorithm 3 and the Holm family
  (C-B6D-E-X vs PERSIST-X, CLIM-X, C-B6-R, PO-P-X, NP-P-X; Leads 1 and 2; 10 tests).

**Decision rules:**

- **B1 the extended history improves the provincial model:** C-B6D-E-X Brier < C-B6D-E on B-old at both leads,
  p < 0.10.
- **B2 reliable at lead k:** R1–R7 all pass on B-ext at lead k.
- **B3 non-price drivers add to provincial food-insecurity risk:** C-B6D-E-X < PO-P-X on B-ext at both leads,
  p < 0.10.
- **Component report:**
  - the hunger part, scored against measured BL hunger > 11.0 (the share of correct quarterly calls);
  - the price part, the sign accuracy of D̂ vs the realised D;
  - each part's contribution share.

**Nothing is served.** Adoption is a team and adviser decision. **Reported whatever the result.**
PLAN-SHA256: 2109fecddb82196b98d694d59ed3058e26a49d88c816daa88ef06413e6c774d3
