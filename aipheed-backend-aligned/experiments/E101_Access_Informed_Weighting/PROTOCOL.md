# E101: access-informed FIRI weighting. Pre-registered protocol

**Date:** 2026-10-23. **Branch inspected:** `main` @ `0239273`. **Production is not changed**; outputs go to `out/` only.
**Freezing:** this file is hashed (`runner/PROTOCOL_SHA256.txt`, LF-normalised) before any arm below is scored.

**Already examined (disclosed):** the served FIRI v2 evaluation (Lead 1/2/3, `firi2_evaluation.json`); E100 (affordability domain negatively related to regional hunger at Lead 2; level indicator not significant). No arm defined below (T1, T1-noH, T1-REL, T1-EQD, sensitivity draws) has been scored. All 2022-Q2..2026-Q3 outcomes were seen before: every result here is **development evidence**. The only unseen test is prospective (section 7).

## 1. Framework basis (theory, not data)

FAO / World Bank: four dimensions (availability, economic and physical access, utilization, stability), all of which must hold at once; household food security is not guaranteed by supply, so access (incomes, expenditure, markets, prices) is the policy focus. PSA PhilFSIS (FAO TCP/PHI/3401) splits accessibility into economic access (income, poverty, buying capacity) and physical access. SWS involuntary hunger and HFIAS/FIES are experience-based **access** measures. These sources support the *structure* below and the priority on economic access. They do **not** supply numerical weights: the numbers are **theory-informed choices**, not empirically validated.

## 2. Index structure T1 (fixed now)

Dimension scores from the stored FIRI v2 indicator scores (percentiles against strictly earlier origins; 0.5 = usual):

| Dimension | Components (each the mean of its available indicator scores) | Weight |
|---|---|---|
| ACCESS (economic access) | price conditions A = mean(A1, A2, A3); household income E = mean(E1, E2); chronic vulnerability V = V1; experienced hunger H = H1 | **0.50**, components equal within ACCESS |
| AVAILABILITY | local production: mean(C3, C4) | **0.25** |
| STABILITY (shocks) | mean(C1, C2, N1) | **0.25** |
| UTILIZATION | no indicator in the data | not represented (disclosed gap) |

ACCESS = mean of its available components (≥ 2 of 4 required). FIRI_T1 = Σ w_d × D_d over available dimensions, weights renormalised; ACCESS and at least one other dimension required, else not computable. HIGH at ≥ 0.5. **No parameter is fitted to any outcome.**

Rationale for the numbers: access receives half the weight because the frameworks name economic access as the household-level constraint and the user brief prioritises it; the remaining half is split equally between the two other measured dimensions because the frameworks require all dimensions simultaneously and give no basis for ranking them. Components within a dimension are equal because no source ranks them.

## 3. Arms

| Arm | Definition |
|---|---|
| SERVED | C3 walk-forward evidence weights (as `firi2_evaluate.evidence_weights`, recomputed per lead) |
| EQUAL | C1: six domains equally weighted |
| T1 | Section 2 |
| T1-noH | T1 with H removed from ACCESS (no SWS-derived input at all): the outcome is independent of every input and of every weight |
| T1-REL | T1 with A2 replaced inside A by REL = relative food price level (food / all-items index at t−1 over the same ratio at 2021-Q1), percentile vs strictly earlier origins (≥ 8), a level-based affordability proxy assuming nominal incomes move with general prices |
| T1-EQD | Equal dimension weights (1/3 each): tests the access priority |
| Baselines | H1 alone, ALWAYS (1.0), CLIM (share of posted rounds > 11.3 before issue) |

Per lead L ∈ {1, 2, 3}: A1 = the sealed E56 price probability for lead L (Lead 2: the stored history value; Leads 1 and 3: `E63_Lead_Time_Study/sealed/predictions.csv`, hash-checked); H1 = `thesis_system.regional_hunger(t, L)`; all other indicator scores are lead-agnostic and taken from `firi2_history.csv`. Evaluation origins: Lead 1 2021-Q4..2026-Q2, Lead 2 2021-Q4..2026-Q1, Lead 3 2021-Q4..2025-Q4. Outcome: SWS Balance Luzon mean of all rounds of the target quarter > 11.3 (as `firi2_evaluate.outcome_series`).

**Reproduction gate:** SERVED must reproduce the published C3 accuracy and Brier at each lead within 0.01 on its computable quarters; otherwise that lead is reported as "not reproduced" and only its comparisons inside E101 are shown.

## 4. Metrics

Accuracy (Wilson 95% CI), balanced accuracy, recall HIGH/LOW, AUC, Brier (index as a score), Spearman with the hunger level; paired quarter Brier difference vs SERVED and vs EQUAL (bootstrap 95% CI, 2,000 draws, seed 2026; two-sided sign test); on the quarters where both arms are computable.

## 5. Sensitivity (Lead 2)

(a) ACCESS weight ∈ {0.33, 0.40, 0.50, 0.60, 0.67}, remainder split equally; (b) 1,000 Dirichlet draws of the three dimension weights, α = 20 × (0.50, 0.25, 0.25), seed 2026: distribution of accuracy and Brier; (c) drop each ACCESS component in turn.

## 6. Duplication check

Spearman correlations of province-row indicator scores (A1, A2, A3, V1, E1, E2, H1, C3, REL) and of regional component scores per origin, over the evaluation rows.

## 7. Decision rule (fixed now) and prospective test

- **Adopt:** only after T1 (or a T1 variant) beats SERVED on paired Brier over sealed, unseen quarters, with adviser approval. Not possible in this run.
- **Test further (seal):** at Lead 2 on development quarters, T1's Brier ≤ SERVED's + 0.02, accuracy ≥ ALWAYS, and at no lead worse than EQUAL with a paired CI above 0 and sign p < 0.05.
- **Reject:** T1 worse than SERVED at Lead 2 with paired CI above 0 and sign p < 0.05, or accuracy below ALWAYS.
- T1, T1-noH and T1-REL values for Lead-2 targets 2026-Q4 and 2027-Q1 are written to `out/sealed_prospective.csv` with a SHA-256 before those SWS rounds are posted.

## 8. Independent outcomes

Only SWS is quarterly. T1-noH is the cleanest check (no SWS input, no fitting). PSA subsistence incidence (2021, 2023; provincial; CV 17–53%) is compared descriptively with the 2023 mean province index (n = 5, no inference). DOST-FNRI FIES 2025 is regional and one value: not usable.

## 9. Not done

No weight is tuned on any outcome. No pre-2021 data. No new data. No served file changed. Thresholds fixed at 0.5.
