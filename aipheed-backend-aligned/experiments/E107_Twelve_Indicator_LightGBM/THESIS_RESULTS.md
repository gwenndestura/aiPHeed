# E107 Deliverable E: thesis-ready results

**Scope.** Chapter I Objectives 2 and 4 (LightGBM evaluation, lead time, baselines), the 12-indicator requirement, and the target definition.

**Evidence status.** Development evidence. Every evaluated quarter (2023-Q2..2026-Q3) had been examined by earlier aiPHeed experiments. Within E107, the rules were frozen before scoring, and the last four quarters were scored once, after the development block. The sealed forecasts for 2026-Q4..2027-Q3 are the only unseen test.

## 1. Plain-language summary for the defense

1. **What the model predicts.**
   - LightGBM predicts the Chapter I food-insecurity **risk** label (T43): a province is HIGH when Balance Luzon hunger is above 11.3% **and** its food prices are under pressure.
   - This is a composite proxy, not a measured share of food-insecure households.
   - Hunger stayed above 11.3% in every quarter from 2023-Q4 to 2026-Q3. In that period the label's ups and downs came from prices.
   - We also tested the only observed food-insecurity outcome, SWS hunger itself.
2. **All 12 indicators.** All 12 aiPHeed indicators now enter one LightGBM: 13 columns, checked by automated tests. Every value is cut at the forecast issue date, which is also tested.
3. **Lead time.** Leads 1–4 were tested with the same rolling-origin design. **No lead time met the pre-registered reliability rule**, so the data do not establish a maximum reliable horizon.
   - **Lead 1** is the only horizon with supporting evidence: accuracy 0.750 on 40 province-quarters.
   - **Leads 2–4** fail clearly, with accuracy 0.10–0.55 against 0.80–0.95 for "always LOW".
4. **Why.**
   - Only 18 HIGH province-quarters exist in 19 outcome quarters.
   - Four of the 12 indicators (C1, E1, E2, H1) have one value per quarter for all five provinces. With so few HIGH quarters, a tree model uses them as markers of "the 2023-24 high-risk period". In 2025-26 those markers called for HIGH risk while food inflation was falling.
   - The price projection (indicator A1) carries the real signal, and it fades after one quarter.

## 2. Objectives: achieved, partly achieved, not achieved

| Requirement | Status | Evidence |
|---|---|---|
| All 12 indicators in the LightGBM pipeline | **Achieved** | 12 families as 13 columns; `test_all_twelve_families_are_model_columns`, `test_fitted_booster_uses_every_column_as_an_input` |
| No data leakage | **Achieved** for every tested path | Future-perturbation tests (6 origins × 4 leads), split-integrity tests, frozen protocol. Real-time data vintages are not reconstructed (limitation). |
| Clearly defined target related to food insecurity | **Achieved, with limits** | T43 stated as a composite risk proxy; R tested as the observed outcome. No provincial food-insecurity measurement exists. |
| Obj. 2 I–IV: accuracy, precision/recall, F1, AUC | **Achieved** | `EXPERIMENT_REPORT.md` §2–3, `out/results.json` |
| Obj. 2 V: furthest reliable horizon by walk-forward expanding-window evaluation | **Procedure achieved; no reliable horizon found** | §3 below |
| Generalization across quarters | **Not achieved** | G2 and G3 fail at every lead, for every model, including the best structural ones. The final block (1 HIGH row in 20) is won by "always LOW". |
| ≥ 75% accuracy | **Lead 1 only, and only at the margin** | 0.750 (30/40, 95% CI 0.60–0.86). Not met at Leads 2–4, nor for R at any lead. |
| Obj. 4: comparison with four baselines | **Achieved; LightGBM does not dominate** | Lead 1: E107-LGBM 0.750 vs persistence 0.625, PSA-only 0.750, NLP-only 0.625, logistic 0.600. The no-learning structural rule (0.875–0.900) and the existing E56 (0.875) are better. |
| Better than the current implementation | **Not achieved** | E56 beats E107-LGBM at Leads 1–3 on the same rows (Lead 2: 0.88 vs 0.24). E56 was itself designed on these quarters (selection bias). |
| Simple, explainable workflow | **Achieved** | `METHODOLOGY.md` (one model, one table of indicators, one rule) |
| Reproducible record | **Achieved** | `REPRODUCIBILITY.md`; stored predictions reproduce exactly (test) |

## 3. Minimum accuracy and reliability per horizon

**T43 (primary).**

| Lead | Accuracy | ≥ 75%? | Reliable (§8)? | Failed criteria |
|---|---|---|---|---|
| 1 (40 rows, 8 quarters) | 0.750 | yes (exactly) | **no** | R4 (Brier vs climatology, p = 0.16), R5 (HIGH recall 0.46), G2, G3 |
| 2 (25 rows, 5 quarters) | 0.240 | no | no, not assessable | R1 and 8 others |
| 3 (20 rows, 4 quarters) | 0.100 | no | no, not assessable | R1 and 8 others |
| 4 (20 rows, 4 quarters) | 0.550 | no | no, not assessable | R1 and 6 others |

- **Extended eligibility (Addendum 1):** Lead 2 0.343 (7 quarters), Lead 3 0.167 (6 quarters). Both are not reliable.
- **R (observed hunger outcome):**
  - Lead 1: 0.583 vs persistence 0.833 and the H1 hunger outlook 0.833 (Brier 0.272 vs 0.083).
  - Leads 2–4: 0.57 / 0.00 / 0.20 against perfect persistence.
  - Not reliable at any lead.

**Maximum reliable lead time: none established**, for both targets.

**Closest to passing.** If the three disputed supplementary SWS rounds are counted as outcomes (sensitivity S1), T43 Lead 1 reaches 0.780 and fails only G3. Lead 1 is therefore the only horizon the evidence leans toward. It should be presented as "supported only at Lead 1, conditional on the data choice, and not yet validated on unseen quarters".

## 4. What the exploratory structural model shows (Addendum 2; development rows seen)

- **The model:** LightGBM started from the label's own structural probability (hunger outlook × probability that projected prices exceed the threshold) and learned corrections from the 12 indicators (SP).
- **Lead 1 result:** 0.900 accuracy, balanced 0.906, AUC 0.937, Brier 0.099, sign-flip p = 0.066 vs climatology. It still fails G2 and G3.
- **Leads 2–4:** it collapses like the plain model.
- **What this means:** domain structure, not more learning capacity, is what works at this data size.
- **Limits:** SP was designed after the development results, so it is a candidate for prospective validation only. Its sealed forecasts are in `out/sealed_prospective.csv`.

## 5. Limitations that remain

1. **No provincial measured food-insecurity outcome.** T43 combines a regional hunger survey with provincial prices. The hunger part was above its line in every evaluated quarter, so evaluated skill is price-pressure skill during elevated hunger.
2. **Tiny effective sample.** 19 outcome quarters, 18 HIGH province-quarters, 4–8 evaluable quarters per lead. Confidence intervals are wide (Lead 1 accuracy 0.60–0.86).
3. **No untouched historical period.** All quarters were examined in E38–E106. E107's final block is untouched only within E107.
4. **Disputed SWS rounds** (2025-Q2, 2025-Q3) change the Lead-1 verdict (S1).
5. **Indicator data limits.**
   - FSSI-v3 exists for 20 of 115 province-origins and never entered a fitted tree.
   - Remittances end in 2025-Q4.
   - V1 uses data published around 2025 at every origin.
   - Data vintages are not reconstructed.
6. **Municipal rankings** (Objective 3) remain a disaggregation of province forecasts that are not validated. They are not independent municipal forecasts.
7. **Not deployed.** The dashboard still serves FIRI v2, unchanged. E107 is available only through read-only API routes on this branch.

## 6. Suggested thesis wording (Objective 2-V)

> Walk-forward expanding-window evaluation of the LightGBM model, using all twelve indicators, was carried out at Leads 1 to 4 under a reliability rule fixed before scoring. No horizon met the rule. Lead 1 reached the 75% accuracy level (0.75; 95% CI 0.60–0.86), but its probabilities were not significantly better than climatology, and it missed more than half of the high-risk cases. Leads 2 to 4 performed below a constant "low risk" forecast. The furthest reliable horizon therefore could not be established with the 2021–2026 data; Lead 1 is the only horizon with supporting evidence.
