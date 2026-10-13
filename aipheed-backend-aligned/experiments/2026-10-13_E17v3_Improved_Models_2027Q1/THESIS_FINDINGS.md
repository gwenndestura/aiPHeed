# Thesis-Ready Findings (E17 v3): Required-Horizon Evaluation and the 2027-Q1 Research Forecast

## Answers to the final questions

1. **What is the exact horizon for 2027-Q1 for each target?** **h = 5 quarters** for regional hunger, provincial food inflation, relative pressure and the thesis risk label. In each case the latest **authorized** observation is 2025-Q4 (SWS published 2026-01-14; CPI dates are proxies). With authorized and verified Jan–Jun 2026 data, h would be 3.
2. **How many valid independent historical origins exist at h = 5?**

   | Target | Common origins at h = 5 |
   |---|---|
   | Regional hunger | **3** (2025-Q2..2025-Q4; two in disputed supplementary-round quarters) |
   | F and D | **5** (2024-Q4..2025-Q4) |
   | Thesis classifier | 1 (E17, k = 5) |

   **All fewer than 8, so all exploratory only.**
3. **What new models were developed?**
   - For regional hunger: a ridge AR with two lags; a damped Theil–Sen trend; a ridge model with regional food inflation and national unemployment; and two ablations.
   - Also tested: drift and the historical mean.
   - The existing ridge AR(1) and the existing F and D ridge models were re-evaluated at h = 5.
4. **Did any new model satisfy the frozen selection rule?** **No.**
   - **Hunger:** drift had a lower MAE (1.92 vs 2.15) but won only 1 of 3 origins and depended on one quarter.
   - **D:** the ridge shrink models beat carry-forward but not the "no difference" baseline.
   - **F:** nothing beat carry-forward.
5. **What does the approved 2026 holdout show?** **Nothing. It was not run.** No 2026 data was authorized; a file-by-file request is in `DATA_AUTHORIZATION_AND_ALLOWLIST.md`. Even if approved, at most 2026-Q1 and 2026-Q2 would be eligible, and only as descriptive evidence.
6. **Which model was selected and refitted?** **None was improved.** Carry-forward is kept for every target by the frozen rule. Experimental candidate outputs are recorded but not selected.
7. **What is the 2027-Q1 research forecast?**
   - **Regional hunger (Balance Luzon): 16.7%** (carry-forward).
   - **Provincial food inflation:**

     | Province | % |
     |---|---|
     | Cavite | 1.90 |
     | Laguna | 2.77 |
     | Quezon | 1.20 |
     | Rizal | 1.23 |
     | Batangas | −0.50 |

   - **Relative pressure:** carry-forward values, with the note that "no difference" was more accurate over five quarters.

   **All are exploratory, with no quantified uncertainty.**
8. **What does the forecast predict?** The SWS regional hunger level, provincial food inflation and relative food-price pressure. **It does not forecast provincial food insecurity.** Every output carries that label.
9. **Is the evidence sufficient to call it reliable?** **No.**
   - There are only 3–5 previously explored origins at h = 5.
   - There is no holdout.
   - CPI timing is unverified.
   - No reliability criterion exists in Chapter I.
10. **Objective status:**

    | Status | Objectives |
    |---|---|
    | Partially achieved | General, 1, 3 |
    | Measured, not better than baselines | 2-I to 2-IV |
    | Inconclusive | 2-V |
    | Comparison achieved, no improvement | 4 |
    | Not achieved | 5 |

## Suggested thesis wording

The study tested whether simple or regularized forecasting models could improve on carrying forward the latest observed value five quarters ahead. Five quarters is the horizon required for a 2027-Q1 forecast from data available through 2025-Q4.

No candidate satisfied the pre-specified selection rule:

- **Regional hunger:** with only three historical forecast origins available at this horizon, the latest published value remained the reference forecast (16.7 percent).
- **Provincial food inflation:** no model outperformed carrying forward the latest value.
- **Relative food-price pressure:** a forecast of no difference between provinces was more accurate than any province-specific forecast.

These forecasts are exploratory research outputs. They do not represent forecasts of provincial food insecurity.
