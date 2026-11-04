# C-B6P3 pre-registration (owner directive): every risk driver contributes to every forecast (fixed 2026-11-04, before any fit)

**Owner directive:** all five risk drivers of the thesis proposal must have inputs and be included in every forecast:
market, climate, fish kill, employment and OFW remittances. In C-B6P2, LightGBM sometimes never splits on employment or
fish kill, so their SHAP is exactly 0 in some forecasts.

**Development evidence;** same 100 province-quarters as C-B6P/C-B6P2. This is a variant after C-B6P2's "no further
variant" note, and is disclosed as owner-directed.

## Definition

- **Exactly C-B6P2:** label, THR 11.0, rows, the 28 inputs, grid, folds, seed, origins and leads.
- **Plus a linear base:** an L2 logistic regression (C = 1; train-median imputation; standardisation on training rows)
  fitted on the 15 driver inputs:
  - market: R_food_yoy, R_head_yoy, R_food_mom, R_rice_yoy and the five world-price inputs;
  - climate: ONI_last, ONI_max12, tc_mean, R_C3;
  - fish kill: R_C4;
  - employment: E1;
  - OFW remittances: E2.
- **Its log-odds are LightGBM's `init_score`;** the trees boost on top. P = sigmoid(linear log-odds + trees).
- **The grid** is selected on the same inner folds, with the linear base refitted inside each fold.
- **SHAP per input** = tree SHAP + linear SHAP (coefficient × standardised value; zero at the training mean).

## Acceptance (all required to recommend it to the team)

1. **Every driver group contributes:** |SHAP| > 0 in at least 99% of scored forecasts, for each of the five groups.
2. **Accuracy:** at least 0.75 at Leads 1 and 2.
3. **Brier:** not worse than C-B6P2 by more than 0.01 at either lead.

**Also reported:** all metrics, Algorithm 3, the Brier comparison vs C-B6P2 and PERSIST, and the driver SHAP shares.
**Reported whatever the result.**
PLAN-SHA256: 18e015043d513f8edace950548081a243d043e702e99713517e264c7716d7aa5
