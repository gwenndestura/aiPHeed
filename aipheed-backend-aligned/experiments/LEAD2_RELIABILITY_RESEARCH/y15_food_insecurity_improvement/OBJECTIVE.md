# Y15 objective

**Improve aiPHeed's two-quarter-ahead (Lead-2) food-insecurity forecast for Region IV-A. Food-price forecasting is not the objective.**

## Target (unchanged from Y14)

**TFI-2.** Observed SWS involuntary hunger in Balance Luzon > 11.3% in quarter t + 2. The forecast is issued at O(t), the first day of quarter t + 1.

- It is FIRI's existing validation target, and the only repeatedly observed food-insecurity outcome available.
- The limitations are set out in `../y14_food_insecurity_forecast/OBJECTIVE_AND_TARGET.md`:
  - severe end of food insecurity only;
  - Balance Luzon, not Region IV-A;
  - no provincial outcome;
  - ±4–6 point sampling error;
  - one outcome per quarter.

## Fixed

- The seven reliability criteria.
- The 0.50 threshold.
- The Lead-2 horizon.
- The target definition.
- The 17 official FIRI Lead-2 targets (2022-Q3..2026-Q3).

R1 (≥ 40 rows) is structurally unreachable for 17 regional quarters. It is reported as FAIL, not reinterpreted.

## Questions

| Investigation | Question |
|---|---|
| **A** | Did FIRI's climate-domain warm-up (indicators without history) create artificial separation between LOW and HIGH hunger quarters? |
| **B** | Can a verified historical remittance series be obtained legitimately, and does it add out-of-sample information? |
| **C** | Does any of five predeclared approaches beat hunger persistence on independent years? The approaches: a corrected FIRI-style index, screened drivers, a survey-uncertainty model, a continuous forecast, and a remittance-enhanced model. |
