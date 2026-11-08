# LEAD2 round 3: poverty-feature correction (protocol v3, frozen before scoring)

**Written:** 2026-10-28. The SHA-256 goes in `runner/V3_SHA256.txt` before `poverty_v3.py` runs.

**Unchanged:** the target (T43c), the evaluation rows, R1-R7, the lead convention, the S-AB hunger term, and the unified LightGBM recipe with all 12 indicator families.

## 1. Diagnostics that motivate it (`out/diag_v3.json`, no model fitted)

- **Target timing: no material defect.** The SWS recall window overlaps the price quarter by 90% on average. A recall-aligned price label would flip 4 of 65 Lead-2 labels and fix only 1 of 13 errors. **No target correction is made.**
- **Borderline errors.**
  - 6 of the 13 Lead-2 errors are within 0.5 point, and 2 of those are within CPI rounding (≤ 0.1 point).
  - No error label is in doubt on the hunger side.
  - The threshold is not changed.
- **Uncertainty.** Recall 10/17, 95% Clopper-Pearson interval 0.33-0.82. The chance (block bootstrap) that recall is at least 0.60 is 0.49. No longer valid history exists.
- **Poverty input V1 = 0.6 × min-max(poverty) + 0.4 × min-max(density):**
  1. **It mixes two opposite gradients.** Cavite (lowest poverty group, densest) gets V1 0.590, almost Quezon's 0.600 (highest poverty, least dense). As a "poverty" signal it cannot tell Quezon from Cavite.
  2. **The poverty part is an unweighted mean of LGU rates,** not a provincial rate. The population-weighted rates are: Quezon 19.7, Cavite 9.9, Batangas 8.8, Rizal 7.1, Laguna 6.0.
  3. **It is static, and its 2024 census population was published in 2025.** This is the disclosed FIRI Amendment 1 deviation. Being static, the value acts as a province profile; the correction keeps the same sources, so the deviation is unchanged and still disclosed.
  4. **In the Quezon 2024-Q3 miss,** V1 pushed the price probability down by SHAP −0.72, although Quezon is the poorest province. The model learned a direction that contradicts the indicator's meaning.

## 2. Candidates

| ID | Change |
|---|---|
| **B0** | P0H4-U (reference) |
| **D1** | V1 replaced by its two components: `V1_pov` = min-max of the **population-weighted** provincial poverty (same SAE 2021 LGU estimates and 2024 populations as V1), and `V1_den` = min-max of density. **Monotone increasing in V1_pov** (poverty can only raise food-insecurity risk; FNRI: poor households are about twice as food-insecure). V1_den is unconstrained. |
| **D2** | D1 without the monotone constraint (isolates the constraint's effect) |

Everything else is unchanged: columns, grid, inner selection, training rows, the monotone constraint on A1.

## 3. Adoption rule (fixed now)

D1 is a validity correction. It is adopted if it does no measurable harm:
- (i) its maximum reliable lead is ≥ B0's;
- (ii) its Lead-1 and Lead-2 DEV Brier (targets ≤ 2024-Q4) are each ≤ B0's + 0.002;
- (iii) it does not fail any criterion that B0 passes at Leads 1-2.

If D1 is not adopted, D2 is assessed by the same rule. Otherwise B0 stays.

A Lead-2 R1-R7 pass by an adopted model is reported as development evidence and prepared for review, not served.

## 4. Reporting

- The seven criteria at Leads 1-2, before and after;
- accuracy, balanced accuracy, precision, recall, F1, TP/FP/FN/TN, Brier;
- DEV and CONF;
- ΔBrier vs B0 with a 90% CI;
- whether the Quezon 2024-Q3 case is caught (not a selection criterion);
- the poverty group's SHAP direction for Quezon.

## 5. Not allowed

Changing the target, threshold, rows or criteria; re-running with other settings after seeing results; serving or pushing.
