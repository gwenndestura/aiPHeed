# Model-Selection Recommendation (E12)

## 1. Answer to the three questions

| Question | Recommendation | Evidence |
|---|---|---|
| How should **regional hunger** be represented? | **As its own regional indicator:** SWS Balance-Luzon level and trend, one value per quarter, with scope and publication date | It carries no provincial information (invariances 2–5). It drives 76% of S1's HIGH/LOW calls. It is not five provincial observations. |
| How should **relative provincial food-price pressure** be represented? | **As D** (deviation from the five-province mean), with the province ranking shown when all five are available, labelled "relative pressure" | It is the **only** source of provincial differentiation in every combined score. Data are complete in 20/20 quarters. |
| Is a **single combined score** defensible for predicting future outcomes? | **Not with the available evidence.** No combined weight can be justified, and no combined HIGH/LOW can be validated. | See §2 |

## 2. Why no single blended formula is selected

1. **No independent provincial outcome exists.** Category B can only predict next-quarter **S1**, which S1 itself defines. That comparison is circular, and it inherently favours S1-like scores.
2. **The weight on H is not identifiable from the evidence.**
   - α changes only the level shared by all provinces.
   - The 36 grid points reduce to 22 ratios.
   - Standardized weights become fold-dependent ratios.
3. **The Category B pattern is a forecasting effect, not a measurement result.**
   - **What was seen:** after training-only mapping to the S1 scale, ratios α/β ≈ 1 to 2.5 predicted next-quarter S1 with lower error (MAE 3.27–3.47) than S1's own ratio of 1/2 (4.63 mapped; 4.55 raw). Leave-one-quarter-out ranges barely overlap: 2.99–3.43 for ratio 5/4 vs 4.39–4.94 for S1.
   - **What it means:** the latest provincial deviation persists only partly, so a forecast should **shrink** it. That is a statement about **how to forecast** the S1 indicator. It does not say how to **define** a food-insecurity score.
   - **Why it is not a validated finding:** the effect was found by scanning ratios on the same 7 reused quarters.
4. **Classification for alternatives is not evaluable.** No approved threshold exists for any score except S1 and its exact scale-equivalents. Class balance and dashboard appearance were not used.
5. **The S1 combined label mostly restates the regional level** (76% agreement; 65% of variance shared by all provinces). The test period is 33 HIGH / 2 LOW.

## 3. Recommendation

| Use | Recommended representation | Status |
|---|---|---|
| Regional context | **SWS Balance-Luzon hunger: level, trend, scope, publication date** | Supported (clear source and meaning) |
| Relative local price pressure | **D and its within-quarter ranking**, labelled as relative pressure, not risk | Supported as a descriptive indicator |
| Combined S1 score | **Keep as the documented thesis indicator (Equation 3),** reported **alongside** the two layers, with its limits: α = 2 unvalidated; the HIGH/LOW reflects mostly the regional level | Retained for continuity; **not validated** as food insecurity |
| A new blended formula (other α/β or standardized) | **None selected** | Not supported |
| Forecasting next-quarter S1 (if needed) | Treat **shrinkage of the provincial deviation** as a hypothesis to test **prospectively** on new quarters, not as a selected method | Exploratory |

**The study cannot establish which formula best predicts actual provincial food insecurity.**

**Decision needed (you and your adviser):** whether the dashboard and thesis present the **two-layer design** as the primary output, keeping S1 as the documented combined indicator, rather than a single combined provincial HIGH/LOW label.
