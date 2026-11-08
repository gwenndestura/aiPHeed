# Addendum 2: input-family contributions (FR4 extension)

**Hashed before scoring.** Written 2026-10-27, after Addendum 1.

## Why

The protocol §7 ablates the selected arm. The selected arms are structural:
- Z1 under schedule A;
- Z0 under schedule B.

They use only two families: A1 (the food-CPI base projection) and H1 (the SWS hunger term). So §7 alone cannot say whether the other ten families carry information. This addendum keeps §7 for the selected arms and adds two tests on the continuous projection error, which has far more statistical power than a binary label (SOURCES S3).

## Tests

| ID | Test | What changes |
|---|---|---|
| **C1** (§7, selected arms) | Remove A1 | π_P becomes the price climatology: the share of training rows with a HIGH price condition, by lead |
| | Remove H1 | π_H becomes the hunger climatology |
| **C2** (add-one) | For each family f, a Z3 model (same grid and inner selection) on **f's columns + lead only**, on top of the Z0 base | Every family is tested, including A1's extra columns beyond the base and H1 = h_last |
| **C3** (leave-one-out) | Z3 on F12 minus f's columns, for each family | |
| **C4** (permutation) | Z3-full fitted once per origin; at prediction time f's columns are replaced by the same province and lead's values from a random other evaluation origin; 20 draws | Model fixed |
| **C5** (SHAP) | Mean \|SHAP\| per family of the Z3-full food-error model on each origin's rows | Grouped into chronological thirds of origins; Spearman rank agreement between thirds |

## Metrics

**C2 and C3** are compared against Z0 and against Z3-full, respectively:
- Δ continuous RMSE (food and gap) by lead, on all origins with a realised CPI quarter (2022-Q4 onwards);
- Δ Brier of the price term and of T43c under schedules A and B, on the evaluation rows;
- a 90% quarter-block bootstrap CI and a one-sided p for each Δ.

**Sign convention.** For C2, "helps" means the family model's RMSE or Brier is **lower** than Z0's. For C3 and C4, "helps" means removing or permuting the family **raises** them.

## Classification (fixed now)

**Predictive.** All three must hold:
1. C2: food or gap RMSE is lower than Z0 at ≥ 1 lead, with the 90% CI excluding 0;
2. no lead is significantly worse (CI excluding 0 the other way);
3. the C4 permutation mean is positive at that lead.

**Weak evidence.** At least one C2 or C3 point estimate is in the helpful direction, but no CI excludes 0.

**No demonstrated value.** Otherwise.

**Recorded for every family:**
- missing share in the evaluation rows;
- publication lag at the issue date;
- stability (C5).
