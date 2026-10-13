# Root-cause analysis: why persistence beats the proposed model, and how the target limits provincial prediction

**Evidence files:**

- `runs/reproduction_and_audit.json` (E23 reproduced exactly);
- `PREDICTIONS_BY_QUARTER.csv` (every lead-1 row);
- `runs/20261013T160107Z/` (E24 frozen run);
- `runs/minimum_data.json`.

## 1. The reported E23 numbers reproduce exactly

Recomputed from the sealed E23 predictions:

| Model / reference | Accuracy |
|---|---|
| Proposed (E23-B) | 0.850 |
| Persistence | 0.875 |
| Always-HIGH | 0.925 |

- Every other E23 metric (accuracy, AUC, Brier, confusion counts, class counts) matches with **maximum absolute difference 0.0**.
- Every model was scored on **identical rows**: the same 40 province-quarters, 8 test quarters (asserted).
- The E24 re-run of the seven required models reproduces E23's sealed predictions **exactly** (maximum difference 0.0).

## 2. What the target is

`app/ml/features/label_generator.py` (implemented Eq. 3; E12 `realized_components`):

- **S1(p,q) = H(q) + 2 × D(p,q)**;
- **HIGH** if S1 > τ.

| Term | Geography | Source | Share of S1 variance (80 province-quarters, 2021–2025) |
|---|---|---|---|
| H = SWS hunger, Balance Luzon | **Region** (the same value for all 5 provinces) | SWS rounds (production definition) | **65.2%** |
| 2D = 2 × (provincial food CPI YoY − five-province mean) | Province | PSA OpenStat provincial CPI | **34.8%** |
| Covariance | — | — | **0** (D sums to zero within every quarter, so H and D are orthogonal by construction) |

**The label is a constructed proxy, not a measured food-insecurity outcome.**

- It contains **no** provincial measurement of hunger.
- All between-province differences in a quarter come from relative food inflation.

**Missing labels.** Quarters without a production SWS round (2021-Q1, 2022-Q1, 2025-Q2, 2025-Q3) have no label; nothing is imputed.

**Threshold and class balance.** The approved evaluation uses a **training-window median**, so training is balanced (for example 20/20). But hunger rose after 2023, so the test rows are **37 HIGH / 3 LOW** at lead 1.

**Leakage check.** No label component of the target quarter is available at the origin:

- SWS of quarter q is published 1–3 months after q;
- the final-month CPI of q is published in q+1.

The leakage assertions pass in every fold.

## 3. Why persistence wins

1. **Persistence's 5 errors are exactly the 5 rows whose label changed** relative to the last published label. Every unchanged row is, by definition, correct for persistence.
2. **The label changes are regional-hunger events plus threshold drift:**

   | Target quarter | Province | Change | Driver |
   |---|---|---|---|
   | 2023-Q4 | Laguna | LOW → HIGH | H rose 10.3 → 14.3 while the province's D stayed low |
   | 2024-Q1 | Laguna | LOW → HIGH | H 15.3 |
   | 2024-Q2 | Quezon | LOW → HIGH | H 19.6 |
   | 2024-Q3 | Quezon | LOW → HIGH | H 18.1 |
   | 2025-Q4 | Batangas | HIGH → LOW | H fell 24.0 → 16.7 and τ had risen to 14.11 |

   **All five are driven by the regional SWS level of the *target* quarter, which is unpublished at the origin.** The latest SWS value available at the origin is at least two fieldwork quarters old.
3. **No model carries information about those changes.**
   - The proposed model gets **0 of 5** changed rows right and adds 2 errors on unchanged rows (7 errors).
   - E23-B gets 1 of 5 right and adds 2 (6 errors).
   - The E24 persistence-gated candidate kept persistence in 5 of 8 quarters and made exactly persistence's 5 errors.
4. **The news block adds nothing here.** Its SHAP share is about 6%, FSSI ranks 7th of 44, and price levels (a time trend) dominate. In the E24 ablation, news-only models are the worst required arms on T1 (0.60–0.63 accuracy).
5. **Accuracy is uninformative:**
   - always-HIGH gets 0.925;
   - the training-majority classifier gets 0.400 (its training data are balanced, so it often predicts LOW);
   - **balanced accuracy and AUC** are the meaningful measures.

## 4. Why "beating persistence" cannot be demonstrated on the existing data

- **Persistence's 5 errors sit in 5 different test quarters.** A model must fix all of them with no new error anywhere to reach one-sided p = 1/2^5 = 0.031. That is a near-perfect model.
- **Even ablation arms noticed after the run are not significant on T1:** LightGBM on the persistence block, 0.925, p = 0.25.
- **Power simulation** (`runs/minimum_data.json`). A model that anticipates 75% of label changes with no false flips needs about 12 new quarters (74% power) to 16 (93%). With realistic false-flip rates of 2–5%, more than 40 new quarters are needed (≤ 65% power at 40). Reaching ≥ 5 LOW test rows needs about 20 new quarters (88%).

## 5. Provincial differentiation

| Question | Finding |
|---|---|
| Are provincial differences in the approved label real? | They come **only** from D (relative food inflation, PSA provincial CPI, correctly mapped by PSGC code). Province–quarter mapping was verified in E17/E23 (provincial table 0012M4ACP23). |
| Are the model's provincial differences supported? | Not validated. The proposed model's within-quarter probability SD has median 0.18, but in 4 of 8 test quarters the true labels are unanimous, so there is nothing to discriminate. |
| Can provincial relative pressure be forecast at all? (exploratory T2: D > 0) | **Barely.** 11 test quarters, 24 HIGH / 31 LOW (evaluable). Persistence 0.655 is the best required arm; E24-F 0.618; the proposed model 0.545; news-only models 0.40–0.44. Post-hoc only: logistic regression on persistence history has a significantly better Brier score than persistence (p = 0.003 uncorrected) but no significant accuracy gain. This indicates mean reversion in D that binary persistence ignores. |
| Are differences unstable? | Yes: leave-one-quarter-out ranges and post-hoc results are within a few rows. |

**Conclusion.** With the approved target, provincial forecasts are **not defensible as food-insecurity distinctions**. They are relative-price-pressure distinctions layered on a shared regional level, and that level drives most labels.

**An independent provincial outcome** (FNRI provincial FIES microdata, CBMS or a DA/LGU FIES module) would be needed to validate provincial food-insecurity claims. See `DATA_ACQUISITION_REGISTER.md`.

## 6. The 142 LGU rankings

- **All 142 codes, names and populations agree** across census, poverty and the reference list.
- **Density recomputes exactly.**
- **The approved formula reproduces E23 to 0.0.**
- **The limitation:** only 16 LGUs have a PSA municipal poverty estimate in the authorized data. For the other 126, the poverty term is a province-mean substitute, so their within-province order reflects population density only. This is now labelled per LGU.
- **The fix requires** the PSA 2021 SAE workbook. The official site returns 403 to automated access, and that was not bypassed. Ingestion and validation code is ready and tested.
