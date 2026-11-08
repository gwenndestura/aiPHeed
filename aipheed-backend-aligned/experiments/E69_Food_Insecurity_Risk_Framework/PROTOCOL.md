# E69 protocol: a two-scale food-insecurity risk framework

**Date:** 2026-10-20
**Branch:** `e69-food-insecurity-risk-framework`, created from `resolve-e67-critical-failures` @ 9320db6.
**Freezing:** frozen before any E69 analysis is scored; SHA-256 (LF-normalised) in `runner/PROTOCOL_SHA256.txt`.
**Requirement basis:** Chapter I §1.5 and §1.7, verbatim in the E25 `thesis_source/CHAPTER_I_verbatim.txt`.

## 0. Why a different framework (rationale fixed before any E69 score)

The target used in E55–E68 (T43) is *provincial food-price pressure gated by regional hunger*. On every evaluated row it equals price pressure (E66/E68), so a LOW price projection means LOW risk by construction.

The risk literature (INFORM, IPC "convergence of evidence", WFP hazard × exposure × vulnerability) separates three things:
- the **outcome**: observed food insecurity;
- **hazards**: affordability shocks, climate shocks, livelihood shocks;
- **vulnerability**: poverty and subsistence.

It does not collapse them into one label.

The data available to aiPHeed contain exactly one observed food-insecurity outcome measured quarterly: **SWS hunger, Balance Luzon (a region, not a province)**. Its sample is 300–600 adults, with a margin of error of ±4–6 points (E27 `sws_round_sample_sizes_partial.csv`). No provincial food-insecurity outcome exists (E68 target-validity report).

E69 therefore builds and evaluates a **two-scale framework**:
- **Scale 1 (regional outcome forecast, evaluable).** A Lead-2 forecast of the observed SWS hunger outcome. This is the only place where a forecast of *food insecurity itself* can be tested against an independent observation: the outcome is a survey, and the predictors are survey lags and PSA prices.
- **Scale 2 (provincial risk outlook, not validatable).** A transparent evidence-fusion tier that combines the regional hunger outlook with province-specific hazard evidence (affordability, climate exposure) and contextual vulnerability. It is a decision-support outlook, **not a probability and not a validated provincial classification**. The province-specific skill of the existing provincial model is measured separately (§3).

The existing E56/E58 model (Lead-2 food-price-pressure score) is kept unchanged as the affordability-hazard component and as the benchmark.

**Evidence status:**
- The hunger series 2021-Q2..2026-Q3 has been used before as an input and gate. Its Lead-2 forecasting was examined in E61 (random walk vs ridge, 10 quarters). E69's regional evaluation uses all eligible quarters and is reported as development evidence; it is not unseen.
- The provincial outlook has no independent outcome and is reported descriptively.
- Forward outlooks for 2026-Q4 and 2027-Q1 are sealed.

## 1. Scale 1: Lead-2 regional hunger forecast

**Outcome.** H(q) is the quarter mean of all SWS Balance Luzon hunger rounds with fieldwork in quarter q (`backend/data/inputs/sws_rounds.csv`, as in T43). Quarters without a round (2022-Q1) have no outcome; they are excluded from scoring, never filled.

**Origins.** t = 2021-Q4..2026-Q1; issue O(t) = first day of quarter t+1; target q = t+2.

**Information at issue.** Only rounds whose `published` date is before O(t) (approved rounds, `P2.h_series(d, t, False)`). CPI is used through month 2 of quarter t (E56 rule).

**Candidates** (all refit at every origin on pairs known at O(t)):

| Code | Model |
|---|---|
| R0 RW | Ĥ = latest posted value (H_base) |
| R1 MEAN4 | mean of the last 4 posted quarter values |
| R2 EXPMEAN | mean of all posted values since 2021-Q2 |
| R3 AR1 | OLS of H(t'+2) on H_base(t') over the training pairs (≥ 6 pairs; otherwise not scored at that origin) |
| R4 RIDGE | the existing I7/E56 hunger part (`P2.hunger_component`, all groups); its Ĥ and probability |
| R5 PRICE | OLS of H(t'+2) on H_base(t') and the regional mean of provincial food YoY at issue (`F_now`, mean of 5 provinces) (≥ 8 pairs) |

**Training pairs.** A pair (t', t'+2) can be used at origin t only if H(t'+2) was published before O(t).

**Uncertainty.** σ = RMSE of the model's own Lead-2 errors on pairs known at O(t), with at least 4; otherwise the protocol default of 4.0 points (the SWS Balance Luzon margin of error at n = 600). P(H > c) = 1 − Φ((c − Ĥ) / σ).

**Events** (thresholds fixed here, not tuned):

| Event | Definition | Basis |
|---|---|---|
| E1 elevated | H(q) > 11.3% | the approved E40 hunger threshold |
| E2 significant rise | H(q) − H_base ≥ 5.0 points | ≈ 1.96 × √2 × 1.8, the sampling error of a difference between two n = 600 rounds |

**Metrics, per candidate and on the common origins:**
- MAE and RMSE of level;
- E1 accuracy, balanced accuracy, recalls and Brier;
- E2 detection (hits / events) and false alarms;
- the number of independent quarters.

**Noise floor.** The expected absolute error from sampling alone is E|N(0, √2·SE)| with SE = 1.6 points (n = 600, p = 0.2), about 1.8 points. It is reported beside every MAE.

**Comparison.** Each model is compared with R0 by paired absolute error (quarter sign test and bootstrap CI over quarters).

**Selection for Scale 2.** The model with the lowest MAE on the common origins, **but only if** its paired difference from R0 has a CI below 0. Otherwise R0, because the simplest model wins ties.

## 2. Scale 2: provincial risk outlook (evidence fusion; rule fixed here)

Components for province p at issue O(t), target t+2:

| Code | Component | Definition |
|---|---|---|
| H | regional hunger outlook elevated | P(H(t+2) > 11.3) ≥ 0.5 from the selected Scale-1 model; unknown → INSUFFICIENT DATA |
| A | affordability hazard (province) | the E56/E58 Lead-2 price-pressure part P_price ≥ 0.5, **or** observed headline inflation (latest two months at issue) above the province's 2021–22 headline P60 (E68 T-AFF thresholds: 5.01 / 4.65 / 5.06 / 6.07 / 5.55) |
| C | climate hazard | a PAGASA El Niño Alert / Advisory / El Niño-related Climate Advisory in force before O(t) (`climate_watch.hazard`) |
| X | local exposure | latest provincial palay or corn production YoY ≤ −10% at issue (unknown if both missing) |
| V | contextual vulnerability (descriptive) | PSA 2023 subsistence incidence and its CV, PSA 2021 SAE poverty (province mean of municipal estimates). Reported with the outlook; **not used in the tier**, because CVs of 17–62% make province ordering unreliable |

**Tier rule (convergence of evidence):**

| Tier | Condition |
|---|---|
| ELEVATED | H and (A or (C and X)) |
| WATCH | H and C, but not ELEVATED |
| NO ELEVATED SIGNAL | otherwise |
| INSUFFICIENT DATA | H unknown |

The tier changes no probability, decision, colour or rank. It is served beside the score, never instead of it.

**Descriptive history (no selection).** The tier is computed at every origin 2022-Q4..2026-Q3 that has the inputs. It is cross-tabulated with T43, T-AFF and the regional outcome E1 at t+2, by year and province. No accuracy claim is made for the tier, because no independent provincial outcome exists.

## 3. Province-specific skill of the existing provincial model (descriptive)

Rows: E68 `tables/r3_rows50.csv` (A0 = E56-TUNED, N1, K1).

| Measure | Definition |
|---|---|
| Intra-quarter correlation (ICC) of the T43 label | one-way ANOVA estimator |
| Design effect and effective sample size | n_eff = 50 / (1 + 4·ICC) |
| A0 vs A0-QMEAN | A0-QMEAN replaces each province's probability by the quarter mean; accuracy and Brier compared |
| Within-quarter AUC | discrimination between provinces in the same quarter |

Interpretation is fixed now: if A0-QMEAN is within 1 correct row and 0.01 Brier of A0, the provincial model has **no demonstrable province-specific skill** beyond the shared quarter signal.

## 4. Lead-2 goal statement (fixed)

**Provincial.** The > 75% Lead-2 goal applies to province-level classifications (Chapter I Obj 2 I). E69 adds no new provincial classifier (none is identifiable beyond E68), so its status is carried from E68: **not met**.

**Regional E1.** Any accuracy above 75% must beat R0 (persistence) at the quarter level to count as forecasting value. If R0 itself exceeds 75%, the result shows saturation, not skill.

## 5. Sealing and serving

- **Sealed.** For targets 2026-Q4 (issue 2026-07-01) and 2027-Q1 (issue 2026-10-01): the Scale-1 forecasts of every candidate and the Scale-2 tiers. They go to `sealed/outlook_forward.csv` with SHA-256 before any outcome exists.
- **Serving mode `AIPHEED_LEAD2_MODEL=e69`:**
  - **Unchanged:** the E58 record numbers, colours and ranks, and every e68 layer.
  - **Added**, as optional API fields and in the existing summary sentence:
    - `riskOutlook` (tier, components, rule, limitations);
    - `regionalHungerOutlook` (Ĥ, interval, P(E1), P(E2), model, evaluation summary);
    - `vulnerabilityProfile` (subsistence and poverty with CVs).
  - **No new UI element.** The E38 default is unchanged.
