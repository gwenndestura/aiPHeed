# E107 Deliverable C: forecasting experiment report

**Evidence status.**
- The rules were frozen before scoring: `PROTOCOL.md` at 02:18 UTC, Addendum 1 at 02:25 and Addendum 2 at 02:28, all on 2026-10-25.
- The development block was scored first. The final block (2025-Q4..2026-Q3) was scored once, afterwards, by commit `6c720c2`.
- Every evaluated quarter had already been examined by earlier aiPHeed experiments. "Untouched" applies within E107 only.
- **All results are development evidence.** The only unseen-outcome test is the sealed prospective file (section 7).

**Rows.**
- T43 is scored per province-quarter (5 rows per quarter). Provinces in the same quarter share one hunger value, so all inference is by quarter: quarter-cluster bootstrap and quarter-level sign-flip tests.
- R is scored per quarter (one row).

Source of every number: `out/results.json` (decisions, metrics, paired tests), `out/predictions_*.csv` (rows), `out/diagnostics.json` (sections 5–6).

## 1. Decision (protocol §8): maximum reliable lead

| Target | Lead 1 | Lead 2 | Lead 3 | Lead 4 | **Maximum reliable lead** |
|---|---|---|---|---|---|
| T43, primary (frozen eligibility) | not reliable | not assessable (5 quarters) | not assessable (4) | not assessable (4) | **none established** |
| T43, extended eligibility (Addendum 1, secondary) | not reliable | not reliable | not reliable | not assessable (5) | **none** |
| R, observed hunger outcome | not reliable | not reliable | not reliable | not assessable (5) | **none established** |

**The 75% accuracy requirement** (R2 alone) is met by E107-LGBM only at T43 Lead 1, and only at exactly 0.750 (30/40; Wilson 95% CI 0.60–0.86; quarter-cluster CI 0.55–0.93). It is not met at any other lead or on R. Even at T43 Lead 1, the rest of the rule fails:
- **R4:** the Brier score is not significantly below climatology (sign-flip p = 0.16).
- **R5:** HIGH recall is 0.46.
- **G2:** the model is worse than climatology in the second half of the period.
- **G3:** the model is worse than climatology on the final block.

## 2. T43 (Chapter I food-insecurity risk proxy): all arms on identical rows

**Lead 1: 40 rows, 8 quarters (2024-Q2..2026-Q3), 13 HIGH.**

| Arm | Accuracy | Balanced acc. | HIGH recall | LOW recall | AUC | Brier |
|---|---|---|---|---|---|---|
| **E107-LGBM (primary, all 12)** | **0.750** | 0.675 | 0.46 | 0.89 | 0.755 | 0.183 |
| E107-SP (exploratory, structural prior) | 0.900 | 0.906 | 0.92 | 0.89 | 0.937 | 0.099 |
| STRUCT (structural probability, no learning) | 0.900 | — | — | — | — | 0.100 |
| RULE (structural rule, no learning) | 0.875 | — | — | — | — | 0.122 |
| E56 (existing LightGBM, sealed E63 outputs) | 0.875 | — | — | — | — | 0.112 |
| PSA-only logistic (Obj. 4-II) | 0.750 | — | — | — | — | 0.224 |
| Logistic, all 12 (Obj. 4-IV) | 0.600 | — | — | — | — | 0.294 |
| NLP-only logistic (Obj. 4-III) | 0.625 | — | — | — | — | 0.295 |
| Climatology / majority | 0.675 | — | — | — | — | 0.268 |
| Naive persistence (Obj. 4-I) | 0.625 | — | — | — | — | 0.375 |

E107-LGBM confusion matrix: TP 6, FP 3, FN 7, TN 24. "—" marks values not computed for the comparison arms in this table; they are in `out/results.json`.

**Quarter by quarter, Lead 1** (correct out of 5 provinces):

| Quarter | Block | HIGH | E107-LGBM | SP | STRUCT | E56 | Persistence | Climatology |
|---|---|---|---|---|---|---|---|---|
| 2024-Q2 | dev | 4 | 1 | 4 | 4 | 4 | 4 | 1 |
| 2024-Q3 | dev | 1 | 4 | 5 | 5 | 5 | 4 | 4 |
| 2024-Q4 | dev | 3 | 2 | 4 | 5 | 3 | 4 | 2 |
| 2025-Q1 | dev | 4 | 5 | 5 | 5 | 5 | 2 | 1 |
| 2025-Q4 | final | 0 | 4 | 4 | 4 | 4 | 1 | 5 |
| 2026-Q1 | final | 0 | 5 | 5 | 5 | 5 | 1 | 5 |
| 2026-Q2 | final | 1 | 4 | 4 | 4 | 4 | 4 | 4 |
| 2026-Q3 | final | 0 | 5 | 5 | 4 | 5 | 5 | 5 |

The final block contains 1 HIGH row in 20. A forecast of "LOW everywhere" (climatology) has the best Brier score there (0.076), so no model can pass G3 on this block. This is a property of the 2025–26 disinflation period, not of a single model.

**Leads 2–4 (frozen eligibility).** The rows below come from origins whose training data had at least 5 HIGH rows: 25 rows at Lead 2, 20 at Leads 3 and 4.

| | Lead 2 | Lead 3 | Lead 4 |
|---|---|---|---|
| E107-LGBM accuracy / AUC / Brier | 0.24 / 0.20 / 0.315 | 0.10 / 0.97 / 0.351 | 0.55 / 0.76 / 0.302 |
| E107-SP accuracy / Brier | 0.36 / 0.474 | 0.25 / 0.490 | 0.45 / 0.413 |
| E56 accuracy / Brier | 0.88 / 0.139 | 0.75 / 0.175 | — |
| STRUCT accuracy / Brier | 0.72 / 0.158 | 0.55 / 0.244 | 0.45 / 0.279 |
| Climatology accuracy / Brier | 0.80 / 0.181 | 0.95 / 0.075 | 0.95 / 0.073 |
| Persistence accuracy / Brier | 0.56 / 0.440 | 0.30 / 0.700 | 0.45 / 0.550 |

**Extended eligibility (Addendum 1).** Lead 2: 35 rows / 7 quarters. Lead 3: 30 / 6.

| | Accuracy | Balanced acc. | AUC | Brier |
|---|---|---|---|---|
| E107-LGBM, Lead 2 | 0.343 | 0.267 | 0.244 | 0.310 |
| E107-LGBM, Lead 3 | 0.167 | 0.153 | 0.168 | 0.451 |
| E56, Lead 2 | 0.800 | — | — | 0.171 |
| E56, Lead 3 | 0.633 | — | — | 0.243 |
| Climatology, Lead 2 | 0.743 | — | — | 0.231 |
| Climatology, Lead 3 | 0.733 | — | — | 0.252 |

**Why the 12-indicator LightGBM collapses beyond Lead 1** (`out/final/origin_records.json`, SHAP in log-odds):
- At every Lead-2 final-block origin, the largest push toward HIGH is **E1, national unemployment change (+1.5 to +1.8)**, followed by E2 (remittances).
- E1 and E2 have one value per quarter for all five provinces. With 2–5 HIGH quarters in training, a national series that differs between the 2023-Q4..2025-Q1 high-risk period and other quarters becomes a period marker.
- In 2025-26 that marker said "high-risk period" while food inflation was falling, so the model called HIGH for provinces that were LOW (FP 15 of 16 HIGH calls at Lead 2).
- At Lead 1 the strongest input is the structural price projection A1_gap, which carries the real signal. This is why Lead 1 works and Leads 2+ do not.

## 3. R (observed food-insecurity outcome: SWS Balance Luzon hunger > 11.3%)

**Lead 1: 12 quarters (2023-Q2..2026-Q3, 10 HIGH).**

| Arm | Accuracy | Brier | Correct quarters |
|---|---|---|---|
| E107-LGBM | 0.583 | 0.272 | 7/12 |
| E107-SP | 0.750 | 0.088 | 9/12 |
| H1 hunger outlook alone | 0.833 | 0.083 | 10/12 |
| Persistence | 0.833 | 0.167 | 10/12 |
| Climatology | 0.500 | 0.307 | 6/12 |
| E56 hunger part (10 quarters) | 0.800 | 0.087 | 8/10 |

**Leads 2–4:** every evaluated quarter was HIGH (hunger was above 11.3% throughout 2023-Q4..2026-Q3).
- Persistence and H1 are perfect, with Brier ≤ 0.008.
- E107-LGBM scores 0.57 / 0.00 / 0.20.
- R5 and R6 cannot be assessed, because only one class is present.

With 6–18 quarterly rows, LightGBM cannot learn more than the latest hunger reading already says. Regional hunger beyond the latest SWS round is not forecastable with these data. This agrees with E69 and E76.

## 4. Generalization across quarters

- **T43 Lead 1, E107-LGBM.** The quarter accuracy is ≥ 0.6 in 6 of 8 quarters (G1 passes). The model is worse than climatology in the second half (G2 fails). Its errors concentrate in the 2024 onset quarters: 1/5 in 2024-Q2 and 2/5 in 2024-Q4.
- **SP and STRUCT.** These are correct in at least 4 of 5 provinces in every quarter. They also fail G2 and G3, because no forecast beats "always LOW" on the 1-HIGH final block.
- **Final verdict.** Neither model generalizes in the sense of protocol §8. The structural arms are the more stable ones.

## 5. Indicator contribution (diagnostic; full tables in `INDICATOR_AUDIT.md` §3)

- **Lead 1:** affordability carries 65% of the model's mean |SHAP|. A1 alone carries 45%. FSSI-v3 (N1) and typhoons (C2) never receive a split.
- **Removing affordability** drops Lead-1 accuracy from 0.750 to 0.450 (sign-flip p = 0.004). It is the only domain whose removal is significantly worse.
- **Removing household economy (E1, E2)** improves Lead 1 to 0.825 / Brier 0.129, and improves Leads 3 and 4.
- **"Affordability only"** beats the full 12-indicator model at every lead (Lead 1: 0.875 / 0.116).
- **Status:** diagnostic only. These rows have been seen, and the required model keeps all 12.

## 6. Sensitivities (`INDICATOR_AUDIT.md` §4)

- **S1, all SWS rounds:** E107-LGBM Lead 1 reaches 0.780 accuracy on 50 rows. Balanced accuracy 0.743, AUC 0.851, Brier 0.154, sign-flip p = 0.016 vs climatology. **It fails only G3** (final block). Leads 2–3 still fail badly (0.43, 0.23). The Lead-1 verdict therefore depends on whether the three disputed supplementary rounds count.
- **S2, V1 strict:** no material change.
- **S3, A1 as the served E56 probability:** Lead 1 0.800 / AUC 0.870. Leads 2–3 still fail.

## 7. Prospective seal (the only unseen-outcome test)

`out/sealed_prospective.csv` (SHA-256 `246700a8d3c4fe76daf43adbfd5ea3c9d622dd124fb4d7137bde9f84a90c75fb`) holds E107-LGBM, SP and STRUCT forecasts from origin 2026-Q3 (issue 2026-10-01), for T43 and R, at 2026-Q4 (Lead 1), 2027-Q1 (2), 2027-Q2 (3) and 2027-Q3 (4).

- **T43 Lead 1 (2026-Q4):** all five provinces LOW under all three arms (E107-LGBM 0.02–0.04).
- **R:** E107-LGBM gives 0.19 (LOW) at Lead 1, while the latest SWS reading (2026-Q2, 17.3%) is far above 11.3%, H1 gives 0.94 and SP gives 0.84. This is the failure of section 3 in prospective form.
