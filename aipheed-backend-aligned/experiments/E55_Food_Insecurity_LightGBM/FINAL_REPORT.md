# E55 final report: the food-insecurity target and the final LightGBM model

**Date:** 2026-10-17/18. **Branch:** `e46-lead2-policy`, not pushed. **Production default:** unchanged (E38).
- E55 is served only with `AIPHEED_LEAD2_MODEL=e55`.
- The protocol (`PROTOCOL.md`, sha `454eaec1…`) was committed in ad4d03b before any E55 score.
- Deviations D-1 and D-2 were recorded before any metric (`DEVIATIONS.md`).

**Evidence status:** every evaluated quarter (2024-Q3..2026-Q3) was examined in E43–E54. All historical figures here are **development evidence, not independent validation**. The independent test is the frozen 2027-Q1 forecast, which is pending.

## 1. Answers in brief

| Requirement | Result |
|---|---|
| Defensible food-insecurity target | **T43** (Chapter I section 1.7): HIGH when regional SWS hunger is above 11.3% **and** the province has PSA food-price pressure. The thesis Eq. 3 label is kept for comparison. It is saturated (40/45 HIGH rows in 2024–26) and its global median uses future quarters. |
| Probability refers to its target | Yes. API, record and dashboard say "food-insecurity risk (high regional hunger together with provincial food-price pressure)". The probability is shown as P(hunger stays elevated) × P(price pressure). |
| Poverty | Not in any earlier model (E54 audit). Added to LightGBM, as-of, look-ahead or as province indicators, it gives **identical forecasts**: the trees never split on it. Its proper role remains the Objective 3 vulnerability weight. |
| Five triggers and NLP | All five groups and the news shares are model inputs, with coverage documented (`tables/feature_audit.csv`). Only Market / Prices carries reliable signal. Fish-kill, news and policy inputs are never used by the trees, and no group's removal reliably worsens the forecast. |
| LightGBM deliverable | **E55-LGBM**: a reproducible, tested, served LightGBM model with exact TreeSHAP. |
| ≥ 75% one-quarter-ahead accuracy with discrimination | **Not met, by one row.** Accuracy 0.733 (33/45; 95% CI 0.62–0.84). Balanced accuracy 0.709; HIGH recall 0.643; LOW recall 0.774. It passes A2–A5 and fails A1. |
| Beats the baselines | **Yes**, on the same 45 rows: lowest Brier of every model (0.180) and higher balanced accuracy than every Objective 4 baseline. It is statistically indistinguishable from the ridge component models E46-I7 and E52. |
| Leakage | As-of invariance passes: forecasts from data truncated at the issue date are identical. There are no pre-2021 rows. |
| Explanations | Exact TreeSHAP (LightGBM `pred_contrib` equals `shap.TreeExplainer`, difference 0.0). Reconstruction error < 1e-9 on all 60 served entries. Poverty, news volume, the hunger gate and the CPI projection are each accounted for. |
| Tests | Backend 392 passed, 18 skipped. Frontend tsc clean, 45 vitest. E55 experiment 7/7, E55 serving 5/5. |
| Dashboard | Verified locally against the `e55` API. No live deployment was checked or changed. |

## 2. Model identity

| Item | Value |
|---|---|
| Name | E55-LGBM (served arm; POV-AS did not improve, so it was not adopted) |
| Type | P(T43) = P_hunger × P_price. P_price is a LightGBM classifier: depth-1 trees, learning rate 0.05, reg_lambda 10, 10 or 40 trees, `init_score` = logit of the base-effect CPI projection probability, intercept-free logistic loss (centred gradients, tree mean removed). P_hunger is the I7 regional ridge component. |
| Selection | Per origin, by embargoed forward-chaining log-loss on training targets only (24 configurations) |
| Version | protocol sha 454eaec1…; run `runs/20261017T153947Z`, repeat `20261017T154837Z` (byte-identical) |
| Predictions sha256 | `0791878764e22544c4659fa471f3767f23d65f6371a5821968877d75a21422ed` |
| Frozen 2027-Q1 sha256 | `4589ba2883666519e42395542c5d04eff7c2b5940815fe1b377e9022c4e18942` |
| Served record sha256 | `a026685a217b3f2fd7ceabe44c43843e1df2c38a9c520c2e4047bfabbd92c527` (`backend/data/e55/e55_record.json`) |
| Horizon | **One quarter ahead** = the project's Lead 2. Issued at day 1 of quarter t+1 with data published before that date, for quarter t+2. Example: issued 2026-10-01 for 2027-Q1. |

## 3. The target

**Definition.** Province-quarter q is HIGH when both hold:
- Balance Luzon SWS hunger H_q > 11.3%, the P60 of the 2021–2022 rounds;
- **and** the province's PSA food CPI YoY exceeds its own 2021–2022 P60, **or** its food-minus-headline YoY exceeds its P60.

Thresholds are the frozen E40 values. SWS rounds come from the production file, quarter mean, all rounds.

**What this target can and cannot show:**
- SWS hunger is one regional value per quarter. No public quarterly measure of provincial hunger or food insecurity exists. PSA FIES and subsistence incidence are annual or triennial.
- From 2023-Q4 hunger stayed between 14.3% and 25.3%, so condition (a) held on every evaluation row. On these rows T43 equals PS, which is checked in code.
- The evaluated skill is therefore the provincial price-shock part *under elevated hunger*. The hunger part last changed state before any evaluable origin, so its forecasting skill cannot be measured in 2021–2026.
- The one partial instance is target 2024-Q2, outside the 45 primary rows:
  - The latest SWS round posted before the issue date (2023-Q3, 10.3%) put P_hunger at 0.21.
  - Hunger then rose to 19.6%, and all 4 HIGH provinces were missed.
  - On all 50 rows E55-LGBM scores 0.68 (supplementary block).

**Thesis Eq. 3 label (preserved).** S1 = H + 2D:
- 70% of its variance is regional.
- Above any single threshold, 89–93% of 2024–26 rows are HIGH. Always-HIGH beats every model on it (E49/E51).
- Its global-median form fails as-of computability.

It is reported, not used as the primary target. Adopting T43 (single quarter, no sustain rule) needs **adviser approval**.

## 4. Data and features

**Feature audit:** `tables/feature_audit.csv` gives 33 inputs with source, geography, reference period at issue, transformation, missingness and use. Summary:

| Group | Inputs (geography) | Coverage at the 12 issue dates |
|---|---|---|
| Market / Prices | CPI projections, food and gap now, D_now, wholesale rice (provincial); 4 rice-policy features (national) | complete |
| Climate | typhoons (provincial, 300 km); ENSO (national); palay and corn (provincial); 2 interactions | complete |
| Fish kill | fisheries and aquaculture production (provincial) | complete; **no official fish-kill event series exists** |
| Employment | LFS unemployment and underemployment YoY (national) | complete |
| OFW remittances | BSP remittances USD/PHP YoY, USD/PHP (national) | **remittances missing at the 2026 issue dates** (dataset ends 2025-Q4); shown as limited data |
| News (NLP) | five trigger shares + article count (provincial) | complete |
| Poverty | PSA 2021 municipal SAE, province mean of 141 LGUs | as-of from 2025-01-01 origins |

**Cutoffs** (E47 audit, unchanged):
- CPI: months published before the origin;
- typhoons and news: quarter t;
- production, LFS, remittances, rice and ENSO: quarter t−1;
- SWS: rounds posted before the origin;
- policy: orders announced before the origin.

**Study window:** 2021-Q1..2026-Q3 outcomes only. No pre-2021 value; the 2025 poverty statistics are not used.

## 5. Results: identical 45 rows (9 quarters, 2024-Q3..2026-Q3, 14 HIGH / 31 LOW)

Full table: `tables/metrics.csv`.

| Model | Acc [95% CI] | Bal | Rec H | Rec L | F1 | Brier | AUC | TP/TN/FP/FN |
|---|---|---|---|---|---|---|---|---|
| **E55-LGBM** | **0.733** [0.62, 0.84] | **0.709** | 0.643 | 0.774 | 0.600 | **0.180** | 0.779 | 9/24/7/5 |
| E46-I7 (ridge, same target) | 0.756 [0.64, 0.87] | 0.725 | 0.643 | 0.806 | 0.621 | 0.186 | 0.776 | 9/25/6/5 |
| E52 (P(PS), ridge) | 0.756 | 0.725 | 0.643 | 0.806 | 0.621 | 0.188 | 0.776 | 9/25/6/5 |
| I7-BASE (projection only × gate) | 0.733 | 0.709 | 0.643 | 0.774 | 0.600 | 0.184 | 0.779 | 9/24/7/5 |
| B1 persistence | 0.600 | 0.592 | 0.571 | 0.613 | 0.471 | 0.400 | 0.592 | 8/19/12/6 |
| B2 PSA-only LR | 0.378 | 0.333 | 0.214 | 0.452 | 0.176 | 0.598 | 0.295 | |
| B3 PSA-only LightGBM | 0.400 | 0.290 | 0.000 | 0.581 | – | 0.424 | 0.221 | |
| B4 NLP-only LR | 0.667 | 0.523 | 0.143 | 0.903 | 0.211 | 0.235 | 0.488 | |
| B5 NLP-only LightGBM | 0.644 | 0.546 | 0.286 | 0.806 | 0.333 | 0.267 | 0.450 | |
| B6 LR combined | 0.333 | 0.301 | 0.214 | 0.387 | 0.167 | 0.646 | 0.247 | |
| B7 E38 procedure on T43 | 0.356 | 0.278 | 0.071 | 0.484 | 0.065 | 0.433 | 0.301 | |
| Climatology / always LOW | 0.689 | 0.500 | 0 | 1 | – | 0.255 / 0.311 | | |
| always HIGH | 0.311 | 0.500 | 1 | 0 | 0.475 | 0.689 | | |

**Acceptance (E52 criteria):**

| Criterion | Result |
|---|---|
| A1 accuracy ≥ 0.75 | **fails** (0.733) |
| A2 balanced ≥ 0.70 and both recalls ≥ 0.60 | passes |
| A3 Brier below every baseline | passes |
| A4 balanced accuracy above every baseline | passes |
| A5 minimum leave-one-quarter-out ≥ 0.70 | passes (0.700) |

**Accepted for development: no.**

**Paired Brier against E55-LGBM** (quarter bootstrap):
- I7: +0.007 [−0.016, 0.025];
- E52: +0.009 [−0.015, 0.029];
- persistence: +0.221 [0.033, 0.407].

LightGBM and the ridge models cannot be told apart. LightGBM clearly beats persistence.

**Calibration (E55-LGBM):**
- CITL −0.11 (forecasts about 11 points too high);
- slope 0.89, much better than E52's 0.585;
- reliability in `tables/reliability_e55.csv`.

**Per quarter** (`tables/per_quarter.csv`): 0.8, 0.6, 0.6, 0.8, 0.6, 1.0, 1.0, 0.4, 0.8.

**Other row sets:**
- Approved-SWS-only subset (35 rows): E55 0.743, I7/E52 0.800.
- E38-served is scored on a non-equivalent target: on its 35 rows against T43 it gets 0.143. It forecasts the saturated Eq. 3 label.

## 6. Why LightGBM underperformed, and what fixed it (`tables/metrics.csv`, F rows; diagnostics, not selection)

| Diagnostic | Acc | Bal | Rec H | Rec L | Brier | Reading |
|---|---|---|---|---|---|---|
| F0 naive LightGBM classifier | 0.533 | 0.642 | 0.93 | 0.36 | 0.244 | The earlier failure, reproduced: it over-predicts HIGH from the 2022–23 inflation regime. |
| F1 + projection features | 0.600 | 0.671 | 0.86 | 0.48 | 0.242 | Structure given as features is not enough with about 100 rows. |
| F2 structural offset | 0.756 | 0.744 | 0.71 | 0.77 | 0.190 | **The offset is the decisive fix.** |
| F3 offset + intercept-free | 0.711 | 0.673 | 0.57 | 0.77 | 0.186 | Better Brier, one row worse in accuracy than F2. |
| F4 + recency weighting | 0.733 | 0.728 | 0.71 | 0.74 | 0.184 | Best AUC (0.813). |
| F5 complex trees (8 leaves, 300) | 0.667 | 0.660 | | | 0.198 | Complexity hurts. |
| F6 class weighting | 0.711 | 0.673 | | | 0.183 | No gain. |
| F7 tuned threshold | 0.533 | 0.485 | | | 0.186 | **Threshold tuning hurts badly.** |
| F8 Platt calibration | 0.733 | 0.650 | 0.43 | 0.87 | 0.192 | Calibration hurts discrimination. |
| F9 no OFW group | 0.689 | 0.657 | | | 0.196 | |
| F10 last 8 quarters only | 0.711 | 0.712 | | | 0.203 | Sample size limits it. |

**Diagnosis.** Earlier LightGBM versions failed for three reasons:
- they learned price-to-label thresholds from only about 30–100 province-quarters;
- those thresholds came from a regime (2022–23) that reversed after the 2024 rice-tariff cut;
- trees cannot extrapolate base effects.

Two fixes work:
- giving LightGBM the base-effect CPI projection as its starting point (offset);
- keeping it shallow.

Tuned thresholds and post-hoc calibration hurt. The differences among F2, F3, F4 and E55-LGBM are 1–2 rows of 45, inside every CI. F2's 0.756 was seen only after scoring, so it is **not** adopted (PROTOCOL section 11).

## 7. Poverty and trigger ablations (`tables/poverty_and_ablation.csv`)

**Poverty:**
- POV-AS, POV-LA and FE are all **IDENTICAL** to E55-LGBM: max |Δp| = 0.
- With depth-1 trees, min_child 10 and five provincial values, a split on poverty is never the best split.
- E54 found the same for the ridge models (C1–C3: no improvement, 0 decision flips).
- **Conclusion:** the evidence gives no basis for using 2021 poverty as a predictor of quarter-to-quarter risk. A static provincial value cannot explain quarterly change. Its use as the Objective 3 vulnerability weight is unchanged.

**Triggers:**

| Group removed | Effect |
|---|---|
| fish kill, news, rice policy | IDENTICAL (never used) |
| climate | ΔBrier −0.0035 [−0.011, 0.001]: removing it slightly helps; not significant |
| employment | +0.0012 [0.000, 0.003] |
| OFW | +0.0021 [0.000, 0.008] |
| market only | +0.0024 [0.000, 0.006] |

No group "adds information" under the pre-registered rule (CI lower bound > 0). The five triggers are genuine inputs with documented coverage. Only Market / Prices measurably drives the forecast.

**Served TreeSHAP over 60 entries:**
- Market / Prices ranks first in 56 and contributes in 57;
- employment contributes in 20, OFW in 15, climate in 12, fish kill in 0.

## 8. Explanations (Section 9 of the brief)

- **Additive in log-odds:** logit P_price = baseline + Market CPI projection (offset minus its training mean) + Σ TreeSHAP over climate, fish kill, employment, OFW, poverty and other (news volume).
- **Exactness:** TreeSHAP equals `shap.TreeExplainer` (test). Reconstruction error < 1e-9 for every entry. Every probability is reproduced < 1e-9 from a refit at its own issue date.
- **Hunger** is a separate factor: P(hunger stays above 11.3%) and the forecast H.
- **Missing inputs:**
  - a group with no observed input is "insufficient data";
  - a group with some missing inputs (OFW in 2026) makes the summary "limited";
  - missing data is never shown as "no effect".
- **Dashboard sentence** (live, Quezon 2027-Q1): "Food-insecurity risk (high regional hunger together with provincial food-price pressure) in Quezon for 2027-Q1 is forecast LOW (15% probability), mainly because Market / Prices lowered it and Employment lowered it." Data status: limited (OFW Remittance).
- The note says "model attributions, not causes".

## 9. System verification

**Tests:**

| Suite | Result |
|---|---|
| backend full suite | 392 passed, 18 skipped |
| frontend | tsc clean; vitest 45 passed (no frontend file changed) |
| E55 experiment (`tests/test_e55.py`) | 7 passed: protocol hash, frozen hash, window and label, as-of invariance at 2024-Q3 and 2026-Q3, TreeSHAP exactness, intercept-free trees |
| E55 serving (`backend/tests/integration/test_e55_food_insecurity_lgbm.py`) | 5 passed |

**Live dashboard (local):** `aipheed-e55-api` on 8003, approved frontend on 8083, clock 2026-10-17.

| Check | Result |
|---|---|
| Target quarter | Q1 2027 (forecast); timeline Q1 2026 → Q4 2026 (Today) → Q1 2027 |
| Regional index | 0.08, Low; all five provinces Low |
| Map colours | approved yellow / red unchanged |
| Quezon | 0.15; triggers Market 79%, Employment 15%, OFW 6%; 41 municipalities as relative prioritization |
| Past quarter Q3 2026 | E55's own backtest (region 0.31; Quezon HIGH, a false positive, observed LOW); never another model's score |

**Defect found and fixed through data:** the province note read "This is a One quarter ahead (Lead 2): issued … for 2027-Q1 for Q1 2027". The record's horizon text now fits the approved sentence: "This is a one-quarter-ahead (Lead 2) forecast issued 2026-10-01 for Q1 2027 …".

**Target-quarter advance:** handled by `app/quarterly/target.py` from the clock (Q4 2026 → Q1 2027, and so on). The record must be rebuilt at each new origin; nothing is fabricated for quarters without a record.

**Not verified:** the Render/Vercel deployments. Nothing was pushed or deployed. The basemap PMTiles console error is pre-existing and unrelated.

## 10. Why 75% cannot be established with the available data (`tables/sample_size.json`)

**The gap is one province-quarter.**
- E55-LGBM is 33/45; 34/45 = 0.756 would pass A1.
- The ridge models are at 34/45. Every CI spans about 0.62–0.85.
- The data cannot tell 0.73 from 0.76.

**Quarters needed.** Per-quarter accuracy varies with SD 0.20. For the 95% lower bound to reach 0.75, roughly this many independent quarters are needed:

| True accuracy | Quarters needed | Years |
|---|---|---|
| 0.80 | 62 | about 15 |
| 0.85 | 16 | about 4 |

There are 9 evaluable quarters in 2021–2026.

**The hunger component cannot be tested at all.** SWS hunger was elevated in every evaluable quarter.

**What would resolve it:**
1. **Prospective quarters:** the frozen 2027-Q1..Q4 forecasts, scored as outcomes are released.
2. **A provincial or municipal food-insecurity outcome:** CBMS LGU FIES, a provincial SWS oversample, or PSA provincial FIES. This would multiply the independent rows and make the hunger part measurable.
3. **An adviser decision** on whether A1 is judged on development evidence with this CI, or only prospectively.

## 11. Chapter I objectives: evidence-based status

| Objective (Chapter I 1.5.2) | Implemented | Evidence | Tested | Result | Limitation / still required |
|---|---|---|---|---|---|
| 1. Two-tier NLP (XLM-R sentiment, BERTopic) → FSSI and risk patterns per province-quarter | yes (E31) | `backend/app/ml/nlp/*`, `news_e31/fssi_v2_panel.csv`, trigger classifier | E31 relevance holdout P 0.85 / R 0.40 | FSSI and trigger shares exist per province-quarter | News inputs are never used by the E55 trees; NLP-only baselines have AUC < 0.5. NLP adds no measurable forecast skill. |
| 2. Evaluate LightGBM: accuracy, precision/recall, F1, AUC, lead time | yes | E55 runs, `tables/metrics.csv` | pre-registered, nested, repeated byte-identically | acc 0.733, prec 0.563, rec 0.643, F1 0.600, AUC 0.779, Brier 0.180 at one quarter ahead | 75% not established (section 10). Lead time beyond one quarter was not re-evaluated in E55; earlier lead-1 evidence (E36) does not beat persistence. The furthest reliable horizon is undetermined. |
| 3. Municipal rankings from province forecasts, weighted by PSA poverty and density | yes | `/provinces/{id}/municipalities`, SAE 2021 (141/142) + POPCEN 2024 | E36/E54 audits, serving tests | 142 LGUs ranked; labelled relative prioritization | The Lucena substitute is unverified. It is not a validated municipal forecast. H4 needs DA evaluators. |
| 4. Compare with persistence, PSA-only, NLP-only, LR | yes | E55 B1–B7 on identical rows | same rows, same target, paired tests | E55 beats every baseline on Brier and balanced accuracy (A3, A4) | development evidence only |
| 5. Dashboard, ISO/IEC 25010 with DA IV-A, FNRI face validity | dashboard yes | `frontend/`, `backend/`, local verification | backend and frontend suites | serves forecast, map, explanations, archive, alerts | **The ISO 25010 survey (50 DA evaluators) and the FNRI NNS comparison are not done.** They need respondents and FNRI figures and cannot be produced by code. |

**Hypotheses:**

| Hypothesis | Status |
|---|---|
| H1 (FSSI and food-CPI deviation among the strongest SHAP predictors) | food-CPI terms yes (Market first in 56/60); FSSI/news no |
| H2 (reliable classification across leads) | not established |
| H3 (beats the baselines) | supported on development data; prospective test pending |
| H4, H5 | need the evaluator survey |

## 12. Decisions for the adviser / user

1. **Target:** approve T43 (single quarter) as the provincial food-insecurity risk target, with SWS hunger shown as the regional measured indicator and Eq. 3 reported as saturated.
2. **75% criterion:** E55-LGBM misses A1 by one row on 45 development rows and passes discrimination and every baseline comparison. Should A1 be judged prospectively (2027-Q1..Q4) instead of on these rows?
3. **Model of record:** E55-LGBM (LightGBM, as Chapter I specifies) or E46-I7/E52 (ridge). They are statistically indistinguishable; LightGBM has the better Brier and calibration slope.
4. **Production default:** switching the dashboard from E38 (saturated Eq. 3 label) to `e55` needs your authorization. It has not been done.
5. **Data refresh:** load the 2026 BSP remittance months.
6. **Outcome data:** request CBMS or provincial FIES data to make provincial food insecurity directly measurable.

## 13. Files and commits

**Experiment** (`E55_Food_Insecurity_LightGBM/`):
- `PROTOCOL.md`, `DEVIATIONS.md`, this report, `CHAPTER_IV_MATERIAL.md`;
- `runner/`: lib, export, baselines, evaluate, tables, feature audit, preview launchers;
- `data/`: T43 labels, persistence, SAE copy;
- `runs/`: run, repeat, two baseline runs, one aborted run;
- `tables/`, `frozen/`, `tests/`, `prospective_status.json`.

**Backend:**
- `scripts/build_record_e55.py`, `data/e55/e55_record.json`;
- `app/ml/inference/e41_lead2.py` (e55 mode), `app/api/v1/insights.py` (E55 note), `app/services/dashboard.py` (event wording);
- `tests/integration/test_e55_food_insecurity_lgbm.py`.

**Frontend:** unchanged.

**Commits:**
- ad4d03b protocol;
- dc1fbe2 D-1;
- 2ccc8cd D-2;
- e4681a8 runs;
- 2c9c8a0 serving;
- the report commit.

**Not pushed. Not deployed.**

**Left uncommitted on purpose:** the E46 D-1 attribution work of another session (`insights.py` / `e41_lead2.py` hunks, `build_record_e46_d1.py`, `e46_record_d1.json`, its test). Its owner or the user should commit it.
