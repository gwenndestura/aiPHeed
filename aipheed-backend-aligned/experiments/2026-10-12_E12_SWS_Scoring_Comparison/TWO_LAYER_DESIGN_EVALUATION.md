# Two-Layer Design Evaluation (E12)

**The candidate design** shows two separate layers instead of one combined provincial HIGH/LOW label:

1. **Regional layer:** SWS Balance-Luzon hunger, with its level and trend. It is one value for the region, labelled with its scope.
2. **Provincial layer:** provincial food inflation (F), its deviation from the five-province mean (D), and a ranking by relative pressure when all five provinces are available.

## 1. Evidence

| Question | Evidence | Source |
|---|---|---|
| Does the combined S1 HIGH/LOW mostly repeat the regional signal? | **Yes.** In 61 of 80 province-quarters (76.25%), S1's HIGH/LOW equals the regional-only call (H > τ0). 65.2% of S1's variance is shared between provinces (between-quarter). | `runs/…/details.json` |
| Does the combined score add provincial ranking beyond D? | **No.** S1's within-quarter ranking equals D's in every labelled quarter. | Invariance 3 |
| Is there a defensible weight for combining H and D? | **Not from the evidence.** α changes only the shared level. Equal-ratio formulas are equivalent. Standardization gives fold-dependent effective weights (wH = 0.5 → ratio 0.35–0.90). No independent outcome exists to fit a weight. | `OPTION_A_*`, `OPTION_B_*` |
| Does the regional layer have a clear source and scope? | **Yes.** SWS rounds with documented publication dates, Balance Luzon (wider than CALABARZON), one observation per quarter. | Registry |
| Does the provincial layer have complete data? | **Yes.** 20 of 20 quarters complete. Release dates are proxy (unverified). | `QUARTERLY_RESULTS.csv` |
| Is each layer's interpretation clear on its own? | Regional: hunger prevalence estimate for Balance Luzon. Provincial: relative food-price pressure. **Both are interpretable without an unvalidated weight.** | — |
| Does the two-layer design avoid treating one regional value as five observations? | **Yes.** H is shown once. A combined provincial label implicitly repeats it five times. | — |

## 2. Forecast note (Category B, internal consistency only)

- **Regional layer, forecasting its own next value:** the latest published H is a weak predictor. Normalized MAE is 1.85 SD. As a linear predictor of next-quarter S1, H alone has a **negative** training slope in 4 of 7 folds, which is unstable.
- **Provincial layer, forecasting its own next value:** D carries forward moderately well (normalized MAE 0.90 SD; within-quarter concordance 0.614).

These are not food-insecurity accuracy.

## 3. Assessment

**The two-layer design is more defensible than a single combined provincial HIGH/LOW label with the available data:**

1. it keeps each indicator's meaning and geographic scope;
2. it needs no unvalidated weight;
3. it does not repeat the regional observation as five provincial ones;
4. it loses no ranking information, because the combined score's ranking *is* D's ranking.

**What it gives up:**

- **A single HIGH/LOW per province.** The design cannot say "Province X is HIGH risk of food insecurity". Neither can the combined score defensibly.
- **The thesis's original combined framing.** The thesis was framed around Equation 3, so this is a framing change, and it needs your and your adviser's decision.

**Conditions under which a combined label would become defensible:** an independent provincial outcome (§10 of the report) against which the weight and threshold could be estimated and validated.
