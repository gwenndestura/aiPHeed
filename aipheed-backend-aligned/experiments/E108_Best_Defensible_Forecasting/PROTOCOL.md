# E108: factored LightGBM on the 12 aiPHeed indicators. Pre-registered protocol

**Date:** 2026-10-25. **Branch:** `aiPHeed/e108-best-defensible-forecasting` (from E107 head `4ed6b27`).
**Freezing:** hashed (`runner/PROTOCOL_SHA256.txt`) before any E108 model is scored. Changes after scoring starts are dated, hashed addenda, and the affected results are labelled exploratory.

**Already seen before freezing:**
- every E107 result;
- `ROOT_CAUSE.md`, including training-set separability of single indicators on T43 and PS labels (no fitted model);
- label and coverage counts.

All outcome quarters through 2026-Q3 had been examined by earlier experiments. **There is no untouched historical period. Every retrospective E108 result is development evidence.** The E107 sealed forecasts are not opened.

## 1. Data and window

The E107 loaders and as-of rules are used unchanged (`E107/runner/e107_lib.py`): 2021-Q1..2026-Q3, issue date O(*t*) = day 1 of quarter *t* + 1.

SWS production rounds only (`definition_A = True`) for labels and inputs. Sensitivity S1 uses all rounds.

## 2. Targets

| Name | Definition | Level | Role |
|---|---|---|---|
| **T43** | HIGH iff SWS Balance Luzon hunger_q > 11.3 AND (food YoY_pq > P60_p OR food − headline_pq > gapP60_p); frozen E40 thresholds | province-quarter | **Primary** (Chapter I §1.7 risk definition; composite proxy) |
| **PS** | the price condition alone | province-quarter | Trains the price part. Its own scores are reported as **food-price-pressure forecasting**, never as food insecurity. |
| **R** | hunger_q > 11.3; also the hunger level | region, one row per quarter | Observed food-insecurity outcome, analysed separately |

**Label known at O(*t*):**
- PS of *q*: the CPI quarter is complete in `Data.cut(t)` and *q* ≤ *t* − 1.
- T43 and R: additionally, every production round of *q* was posted before O(*t*).

## 3. Forecast (identical for k = 1, 2, 3, 4; longer leads are infeasible: fewer than 6 evaluable quarters)

**P(T43 HIGH at *t* + *k*) = H1_k(*t*) × P_price,k(*t*)**

- **H1_k** is the regional hunger outlook `thesis_system.regional_hunger(t, k)` (latest production round posted before O(*t*); spread = RMSE of the rule's own earlier lead-*k* errors). It is identical for the five provinces. It is not learned.
- **P_price,k** is LightGBM on the 13 columns of the 12 families (E107 §4: A1_food, A1_gap, A2, A3, V1, C1, C2, C3, C4, E1, E2, N1, H1), trained on (features of *t*′, PS of *t*′ + *k*) with *t*′ + *k* ≤ *t* − 1 and PS known at O(*t*).
- **Class:** HIGH iff P ≥ 0.5.
- **Independence assumption.** The product assumes the regional hunger condition and the provincial price condition are independent given the inputs. It is stated in every report.

## 4. Candidates (all 13 columns; E107 grid: depth ∈ {1, 2}, trees ∈ {50, 150}, class_weight ∈ {None, balanced}; learning rate 0.05, L2 = 5, deterministic, seed 108)

| ID | Price part | min_child_samples | Role |
|---|---|---|---|
| **F1** | LightGBM on PS | **15** (three quarters) | **Primary (fixed now)** |
| F0 | LightGBM on PS | 5 (E107 value) | isolates the leaf-size change |
| F2 | F1 started from the structural price prior: init = logit(1 − (1 − Φ(A1_food/σ_F))(1 − Φ(A1_gap/σ_G))), with σ = RMSE of the projection's own errors on the fit rows (≥ 4 quarters, else 2.0), clipped to [0.01, 0.99] | 15 | E107-SP idea within the factored model |
| E107 | E107-LGBM direct (stored E107 predictions) | 5 | reference, scored on intersecting rows |

**Nested selection at every origin, on PS training rows only:**
- the last (up to) 4 training target quarters, each fitted on PS rows with target ≤ *q_v* − *k* − 1;
- pooled log loss; ties go to the lower configuration index;
- no valid fold → configuration 0.

No feature selection, no calibration, threshold 0.5.

**Replacement rule (fixed now).** F1 stays the recommended model unless a candidate has (a) a lower T43 Brier than F1 at both Leads 1 and 2 with one-sided sign-flip p < 0.10, **and** (b) passes at least as many §7 criteria at every lead. No other selection is made.

**Eligible origin:** PS training rows from ≥ 6 quarters with ≥ 5 HIGH and ≥ 5 LOW rows, and H1 available.

**Evaluation rows of lead *k*:** every labelled T43 quarter *q* ≤ 2026-Q3 whose origin *q* − *k* is eligible.

## 5. Baselines (same rows)

| Baseline | Definition |
|---|---|
| Persistence (Obj. 4-I) | the province's latest T43 label known at O(*t*) |
| Climatology / majority | training T43 HIGH share |
| Always LOW / always HIGH | accuracy only |
| STRUCT | H1 × structural price prior (F2's init), no learning |
| PSA-only LR (Obj. 4-II) | H1 × logistic price part on A1_food, A1_gap, A2, A3, V1, C3, C4, E1 (L2, C = 1, standardised, training-median imputation) |
| NLP-only LR (Obj. 4-III) | H1 × logistic price part on N1 and an N1-missing flag |
| LR-12 (Obj. 4-IV) | H1 × logistic price part on all 13 columns and missing flags |
| E56 (existing production LightGBM) | sealed `E63` `E56_p`, Leads 1–3, intersecting rows |
| FIRI v2 (served index) | Lead 2 only; class from `firi2_history.csv`; Brier flagged (not a probability) |

## 6. Metrics

Per lead:
- accuracy (Wilson and quarter-cluster bootstrap CIs);
- balanced accuracy;
- precision and recall for both classes;
- F1;
- confusion matrix;
- false-alarm rate FP/(FP + TN) and missed-HIGH rate FN/(FN + TP);
- AUC;
- Brier and log loss;
- calibration-in-the-large and a 5-bin reliability table;
- share predicted HIGH;
- per-quarter metrics;
- within-quarter SD of P (provincial variation);
- onset detection (quarters where T43 HIGH appears after a quarter with none).

Paired tests: per-quarter Brier differences (sum over the quarter's rows), bootstrap CI (2,000, seed 2026), and exact one-sided sign-flip p.

Inference is always by quarter. Provinces of one quarter share one hunger value and are never counted as independent outcomes.

## 7. Reliability rule (E107 §8 unchanged, plus one stricter criterion)

**All of the following must hold on lead *k*'s evaluation rows:**

| | Criterion |
|---|---|
| R1 | ≥ 6 evaluated quarters |
| R2 | accuracy ≥ 0.75 |
| R3 | accuracy > persistence and > majority |
| R4 | Brier < persistence and < climatology, with sign-flip p < 0.10 against the lower of them |
| R5 | recall HIGH ≥ 0.5 and recall LOW ≥ 0.5 (both classes present) |
| R6 | AUC ≥ 0.65 |
| R7 | share predicted HIGH in [0.1, 0.9] |
| G1 | quarter accuracy ≥ 0.6 in ≥ 2/3 of quarters |
| G2 | Brier below the lower of persistence and climatology in both chronological halves |
| G3 | on the most recent four quarters (2025-Q4..2026-Q3; seen, not untouched): accuracy ≥ max(persistence, majority) and Brier ≤ min(persistence, climatology) |
| **G4 (new, stricter)** | on the hunger-elevated quarters (target hunger > 11.3; 2023-Q4 onward), where risk depends on prices: accuracy ≥ 0.75, both recalls ≥ 0.5, and Brier < persistence and < climatology |

**Classification of each lead:**
- **Reliable:** every criterion holds.
- **Inconclusive:** R1 fails; or a class is absent (R5/R6 not assessable); or R2, R3, R5, R6, R7, G1 and G4 all hold but R4's significance or G2/G3 does not.
- **Not reliable:** any other failure.

**Maximum reliable lead** = the largest *k* with Leads 1..*k* all reliable. Report it separately from the maximum lead tested (4).

**The 75% requirement** is reported per lead (R2) and together with the full rule.

## 8. Regional SWS analysis (R), separate

- **Unit:** one row per quarter (never five copies).
- **Binary R forecasts:**
  - H1_k;
  - persistence (latest posted quarter > 11.3);
  - climatology (the posted share);
  - E107's regional LightGBM (stored).
- **Level forecasts** of hunger at *t* + *k*:
  - random walk (latest posted);
  - mean of the last two posted quarters;
  - mean of all posted quarters.
  - Scored with MAE.
- The same R1–R7 rule applies to H1's binary forecasts, with persistence as the comparator.

## 9. Diagnostics (no effect on §7)

**On F1:**
- ablations: −A, −V, −C, −E, −N, −H (the H1 column only; the hunger factor stays), A-only;
- grouped permutation importance per family (permute the family's columns across evaluation rows; 200 draws, seed 108; change in Brier);
- SHAP family shares per origin (mean and SD across origins).

**Also:**
- the price part alone scored on PS labels (labelled as price pressure);
- sensitivities: S1 all SWS rounds, S2 V1 strict.

## 10. Prospective seal and integration

- **Seal:** F1, F0 and F2 forecasts from origin 2026-Q3 (issue 2026-10-01), Leads 1–4, written with a SHA-256 to `out/sealed_prospective.csv` before any of those outcomes is published.
- **API:** read-only `/api/v1/e108/*`. No change to production defaults, to the dashboard design, or to `main`.

## 11. Tests (`backend/tests/unit/test_e108.py`)

- all 12 families in the fitted price booster;
- future perturbation per indicator family and lead, at feature **and prediction** level;
- PS/T43 label availability (no label of *q* ≥ *t* or posted on or after O(*t*));
- factored probability = H1 × P_price;
- reproducibility of stored predictions;
- protocol and seal hashes;
- API.
