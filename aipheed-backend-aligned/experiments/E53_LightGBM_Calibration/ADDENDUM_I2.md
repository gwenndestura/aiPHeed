# E53 addendum I2: second-round calibration and LightGBM arms (frozen before any I2 score)

**Written:** after run `20261017T140057Z`, which failed every target set in protocol section 4:
- No calibrated arm met K1 (C1 CITL −0.112; C2 −0.127).
- No LightGBM arm met A1–A5 (LGB-R 0.640; LGB-RL 0.620; LGB-C 0.560).

**Freeze:** SHA-256 (LF) in `runner/ADDENDUM_I2_SHA256.txt`, committed before the I2 run.

**These arms are designed after seeing run 1's failures on the same 50 rows.** Their results are hindsight-informed development evidence. With them, E53 has made five LightGBM attempts in total, and this multiplicity is reported.

## Diagnosis (run 1, from `selections.json` and `rows.csv`)

1. **Calibration lags the regime.**
   - The inner-fold calibrator is fitted on 2022–2024 targets, when the model under-predicted, so early intercepts are positive (b = +1.21 at 2024-Q3).
   - It turns negative only from 2026-Q2 (b = −0.14 to −0.69).
   - E52's over-prediction is concentrated in 2025-Q3..2026-Q3, after the 2024 rice-tariff cut: mean p 0.26–0.65 against observed 0–0.4.
2. **LightGBM overfits in selection.**
   - LGB-R chose a LightGBM gap residual (market features, 2 leaves, 50 trees) at 9 of 12 origins on a tiny RMSE margin.
   - It pushed the 2025-Q4 and 2026-Q1 probabilities to a mean of 0.59 and 0.66 when no province was HIGH.
   - LGB-C chose the constant model at 6 origins.

## I2 arms

| ID | Description |
|---|---|
| **C3** outer intercept calibration | logit p′ = logit p + b, fitted on the E52 model's own earlier *issued* forecasts whose outcomes were published before the origin: targets ≤ k−3 for target k, i.e. the realized live errors. Prior N(0, 1²); identity under 10 rows or one class. No refit; uses R0's probabilities from run 1. |
| **C4** outer Platt calibration | the same data as C3, logit p′ = a·logit p + b, priors a ~ N(1, 0.5²) and b ~ N(0, 1²) |
| **LGB-R2** shrinkage-heavy LightGBM residual with a conservative selection rule | E52 component structure. Residual grid: num_leaves 2, n_estimators ∈ {25, 50, 100}, learning_rate 0.05, min_child_samples 20, reg_lambda 50, colsample 0.8, features ∈ {all, market}. A LightGBM residual is selected only if its inner RMSE is at least 5% below the best no-residual configuration; otherwise no residual. |
| **LGB-C2** monotone LightGBM classifier | features: distance-to-threshold dfood_m and dgap_m for m ∈ {1.0, 0.5, 0.0}, with monotone +1 constraints (a higher projected food inflation or gap relative to the province's threshold cannot lower P(PS)), plus E52's trigger inputs, unconstrained. Grid: {constant} ∪ num_leaves {2, 4} × n_estimators {50, 200}; min_child_samples 10, reg_lambda 10; embargoed forward-chaining log-loss; decision ≥ 0.5. |

**Disclosure:** for LGB-R2 the report states at how many origins a LightGBM residual is actually used. **A model that never uses its trees would not be a meaningful LightGBM model.**

## Acceptance (unchanged)

- **Calibrated arm (C3 or C4):** replaces R0 only if it passes A1–A5, K1 and K2. If both pass, C3 is chosen.
- **LightGBM arm:** meets the requirement for development if it passes A1–A5 **and** uses LightGBM trees at at least half of the 12 origins (LGB-C2: a non-constant model at at least half of them).
- Same rows, baselines and metric code as run 1.
- Frozen 2027-Q1 forecasts are written per protocol section 7, only for arms that pass.
