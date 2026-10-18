# aiPHeed final model report (E56): two-quarter LightGBM food-insecurity forecast

**Date:** 2026-10-18. **Branch:** `e46-lead2-policy`, 18 commits ahead of origin, **not pushed, not deployed**.
**Production default:** E38, unchanged. It is the rollback.
**Final model:** served only with `AIPHEED_LEAD2_MODEL=e56`.

## 1. Selected model and why

**E56-TUNED** is a LightGBM food-insecurity risk model:

P(HIGH) = P(regional SWS hunger stays above 11.3%) × P(provincial food-price pressure)

**Price part:**
- A LightGBM classifier whose starting score (offset) is the base-effect projection of provincial food inflation from PSA CPI.
- Intercept-free boosting: gradients centred and the trees' training mean removed. The trees adjust risk between provinces and quarters but cannot carry an old price regime's level.
- Inputs: the five trigger groups, news shares, rice-policy orders and, as a candidate, poverty.

**Hunger part:** E46-I7's regional ridge component.

**How it was selected:**
- One bounded optimization cycle (`PROTOCOL.md`, frozen at 8e3e37b before scoring).
- 72 configurations: the 24 E55 configurations plus 48 drawn once with seed 56, over:
  - leaves, depth, learning rate and rounds;
  - min_child, feature and bagging fraction, L1/L2;
  - class weighting, CPI drift, recency weighting, feature set and poverty.
- At every forecast origin the configuration is chosen by nested chronological validation (embargoed forward-chaining log-loss on training targets only).
- It replaced E55-LGBM under the pre-registered rule: lower Brier (0.178 vs 0.180) and balanced accuracy not worse (0.760 vs 0.709).
- The run and its repeat are byte-identical.

**Why not more:**
- The improvement over E55 is small and not statistically distinguishable: paired Brier −0.001 [−0.015, 0.011].
- No second tuning cycle was run (PROTOCOL section 7).

## 2. Target and horizon

| | |
|---|---|
| **Target (T43)** | HIGH when Balance Luzon SWS hunger > 11.3% (P60 of 2021–22) **and** the province's PSA food inflation, or food minus headline inflation, exceeds its 2021–22 P60 (Chapter I section 1.7). A risk indicator, **not** a measured prevalence. Requires adviser approval. |
| **Horizon** | Two quarters. Predictor quarter t, issued day 1 of t+1 with data published before that, target t+2. |
| **Dashboard forecast** | t = 2026-Q3, intermediate 2026-Q4, target **2027-Q1**, issued 2026-10-01 |
| **Target-data freshness** | T43 is observed through 2026-Q3 (SWS round posted 2026-10-14, September CPI). At the issue date the latest known T43 quarter was **2026-Q2**. |
| **Direct food-insecurity surveys** | FNRI FIES (CALABARZON 19.1%, 2023) and PSA subsistence (2021, 2023) end in **2023**. They are regional or provincial, annual or triennial, and are **not** targets. They serve only as reference and the Objective 5 face-validity anchor. |

**What the evaluation measures:** on every evaluated quarter hunger was above 11.3%. The evaluation therefore measures the provincial food-price part under elevated hunger. The hunger part cannot be validated in 2021–2026 data.

## 3. Latest observation of each critical dataset (`tables/data_freshness.csv`)

| Dataset | Latest in data | Used for the 2027-Q1 forecast |
|---|---|---|
| PSA CPI food and all items (provincial) | 2026-09 | 2026-08 |
| SWS hunger, Balance Luzon | 2026-Q3 (posted 2026-10-14) | 2026-Q2 (posted 2026-08-24) |
| PSA palay, corn, fisheries production | 2026-Q2 | 2026-Q2 |
| PSA LFS unemployment (national) | 2026-08 | 2026-06 |
| Typhoon tracks / ENSO | 2026-Q3 | typhoons 2026-Q3; ENSO 2026-Q2 |
| BSP remittances (national) | **2025-Q4** | 2025-Q4 (missing for 2026; shown as limited data) |
| Wholesale rice | 2026-Q3 | 2026-Q2 |
| News trigger shares / FSSI | 2026-Q4 (partial) | 2026-Q3 |
| Rice-policy orders | 2025-10-30 | 2025-10-30 |
| PSA 2021 municipal SAE poverty | 2021 (published 2024) | candidate input from 2025 origins |
| PSA subsistence; FNRI FIES | 2023 | not used |

## 4. Chronological evaluation (identical rows)

**Rows:** 45 province-quarters, 9 quarters (2024-Q3..2026-Q3), 14 HIGH / 31 LOW. All are out-of-sample at their own origin. The 2024-Q2 target is excluded because the E38-framework baselines cannot forecast it (E55 D-1). A supplementary 50-row block includes it.

| Model | Acc [95% CI] | Bal | Rec H | Prec H | Rec L | Prec L | F1 | Brier | AUC | TP/TN/FP/FN |
|---|---|---|---|---|---|---|---|---|---|---|
| **E56-TUNED (final)** | **0.778** [0.69, 0.87] | **0.760** | 0.714 | 0.625 | 0.806 | 0.862 | 0.667 | **0.178** | 0.763 | 10/25/6/4 |
| E55-LGBM | 0.733 [0.60, 0.87] | 0.709 | 0.643 | 0.562 | 0.774 | 0.828 | 0.600 | 0.180 | 0.779 | 9/24/7/5 |
| E46-I7 (ridge) | 0.756 | 0.725 | 0.643 | 0.600 | 0.806 | 0.833 | 0.621 | 0.186 | 0.776 | 9/25/6/5 |
| E52 (price-pressure ridge) | 0.756 | 0.725 | 0.643 | 0.600 | 0.806 | 0.833 | 0.621 | 0.188 | 0.776 | 9/25/6/5 |
| Persistence | 0.600 | 0.592 | 0.571 | 0.400 | 0.613 | 0.760 | 0.471 | 0.400 | 0.592 | 8/19/12/6 |
| Majority class (always LOW) | 0.689 | 0.500 | 0 | – | 1 | 0.689 | – | 0.311 | – | 0/31/0/14 |
| Climatology | 0.689 | 0.500 | 0 | – | 1 | 0.689 | – | 0.255 | 0.235 | |
| PSA-only LR / LightGBM | 0.378 / 0.400 | 0.333 / 0.290 | | | | | | 0.598 / 0.424 | | |
| NLP-only LR / LightGBM | 0.667 / 0.644 | 0.523 / 0.546 | | | | | | 0.235 / 0.267 | | |
| Logistic regression (combined) | 0.333 | 0.301 | | | | | | 0.646 | | |
| E38 procedure on T43 | 0.356 | 0.278 | | | | | | 0.433 | | |

**Acceptance A1–A5:** all pass.
- A1: accuracy ≥ 0.75.
- A2: balanced accuracy ≥ 0.70 and both recalls ≥ 0.60.
- A3: Brier below every baseline.
- A4: balanced accuracy above every baseline.
- A5: minimum leave-one-quarter-out accuracy 0.75.

**Paired Brier, E56 minus comparator** (quarter bootstrap):

| Comparator | Difference [95% CI] | Reading |
|---|---|---|
| persistence | −0.222 [−0.405, −0.047] | significant |
| always LOW | −0.133 [−0.295, 0.030] | not significant |
| climatology | −0.076 [−0.173, 0.014] | not significant |
| E46-I7 | −0.008 [−0.031, 0.020] | not significant |
| E52 | −0.010 [−0.034, 0.018] | not significant |

**Per quarter:** 0.6, 0.6, 0.8, 0.8, 0.6, 1.0, 1.0, 0.8, 0.8.

**Per province:**

| Province | Accuracy | HIGH rows |
|---|---|---|
| Quezon | 0.89 | 5 |
| Laguna | 0.78 | 4 |
| Batangas | 0.78 | 2 |
| Rizal | 1.00 | 0 |
| Cavite | **0.44** | 3 |

Cavite is the weak case: its mean forecast of 0.43 is too high for its outcomes.

**Province discrimination:**
- within-quarter AUC 0.767 (30 same-quarter pairs);
- mean within-quarter SD of probabilities 0.19;
- the five decisions differ in 6 of 9 quarters.

The model does separate provinces; it does not give every province the same category.

**Calibration:**
- CITL −0.10: forecasts about 10 points too high on average.
- Slope 0.81.
- Reliability: 0.0–0.2 → 0.27 observed; 0.2–0.4 → 0.00; 0.4–0.6 → 0.40; 0.6–0.8 → 0.40; 0.8–1.0 → 0.83.
- Calibration was not tuned. Earlier calibrators made it worse because they were fitted on a reversed price regime.

**Supplementary 50 rows (with 2024-Q2):**

| Model | Accuracy | Balanced |
|---|---|---|
| E56 | 0.72 | 0.684 |
| E52 | 0.76 | |
| E55 | 0.68 | |

At 2024-Q2 the hunger gate said 0.21. Only the 2023-Q3 SWS round (10.3%) was posted before 2024-01-01, and hunger then rose to 19.6%. This is the one evaluable case of the hunger part, and it was missed.

**Configuration stability:**
- Nested selection chose 9 different configurations across 12 origins. Poverty was chosen at 4 origins.
- At the 2027-Q1 origin it chose E55's configuration (stumps, 40 rounds, all groups, recency 6, no poverty). The 2027-Q1 forecast is therefore identical to E55's.

## 5. Was the 75% goal met?

**Yes on the development backtest:** 0.778 two-quarter-ahead accuracy, with balanced HIGH and LOW detection and lower Brier than every baseline.

**It is not established as a generalizable 75%:**
- **CI:** the 95% interval is 0.69–0.87, and the gain over E55 (0.733) is 2 province-quarters.
- **Prior exposure:** every evaluated quarter was examined in earlier experiments.
- **Sample size:** 9 quarters. A lower bound of 0.75 would need about 62 quarters if the true accuracy were 0.80, or 16 if it were 0.85 (E55 `tables/sample_size.json`).
- **Majority class:** the Brier advantage over always-LOW and climatology is not statistically significant.

The independent test is the frozen 2027-Q1 forecast (`frozen/E56_TUNED_PROSPECTIVE_2027Q1.json`, sha `044499b2…`), scored when 2027-Q1 SWS and CPI are published. Its status is **pending**.

## 6. Final 2027-Q1 forecast (issued 2026-10-01)

| Province | P(HIGH) | Decision | P(hunger > 11.3%) | P(price pressure) | Top factors (TreeSHAP) |
|---|---|---|---|---|---|
| Quezon | 0.146 | LOW | 0.962 | 0.152 | Market / Prices ↓, Employment ↓, OFW ↓ |
| Cavite | 0.109 | LOW | 0.962 | 0.113 | Market ↓, Employment ↓, OFW ↓ |
| Laguna | 0.070 | LOW | 0.962 | 0.073 | Market ↓, Employment ↓, OFW ↓ |
| Rizal | 0.050 | LOW | 0.962 | 0.052 | Market ↓, Employment ↓, OFW ↓ |
| Batangas | 0.043 | LOW | 0.962 | 0.044 | Market ↓, Employment ↓, OFW ↓ |

**Data used:**
- CPI through August 2026;
- SWS through 2026-Q2;
- typhoons and news through 2026-Q3;
- production, LFS and rice through 2026-Q2;
- remittances missing for 2026 (data status "limited").

**Reading:** hunger is expected to stay elevated, but provincial food-price pressure is projected low after the 2024–25 rice-tariff and price-control period.

## 7. Explanations

**Method:**
- Exact TreeSHAP (LightGBM `pred_contrib`, equal to `shap.TreeExplainer`), in log-odds of the price part.
- Grouped into the five trigger groups; the CPI projection offset is counted in Market.
- Poverty and news volume are shown outside the five bars. The hunger part is a separate factor.

**Checks:**
- Reconstruction error < 1e-9 on every served entry (60).
- Every served probability is reproduced < 1e-9 by refitting at its own issue date.
- Missing inputs are disclosed as limited or insufficient data, never as zero risk.

**Dashboard wording:** "food-insecurity risk (high regional hunger together with provincial food-price pressure) … model attributions, not causes."

## 8. Integration and verification

**Saved final model** (`backend/data/e56/model/`, manifest in the record):

| File | sha256 (first 8) |
|---|---|
| `booster.txt` | d3f0a5df |
| `feature_schema.json` (30 ordered inputs, group and source) | 956c43d7 |
| `config.json` | 557f82ac |
| `offset.json` (drift, RMSEs, correlation, thresholds, tree-mean constant) | 0b24a373 |
| `hunger.json` | 90b08ebc |
| `features_2027Q1.csv` | 3505a50e |

**Record:** `backend/data/e56/e56_record.json`, sha `a63987b1…`.

**Independent reproduction:** `tests/integration/test_e56_final_model.py` recomputes the served 2027-Q1 probabilities from these files alone (LightGBM Booster, bivariate normal, normal CDF): equal within 1e-9 and equal to the frozen file.

**Serving:**
- `e56` mode in `app/ml/inference/e41_lead2.py`;
- E56 note in `app/api/v1/insights.py`;
- event wording in `app/services/dashboard.py`;
- `dataFreshness`, `modelFamily`, `modelVersion` and `finalModelArtifacts` exposed by `/api/v1/lead2/summary`.

**Target quarter:**
- Advances from the server clock: Q4 2026 → 2027-Q1, Q1 2027 → 2027-Q2, and so on (tested).
- The record serves only its own target. In 2027-Q1 it will not stand in for 2027-Q2 (tested).

**Historical forecasts:**
- Frozen prospective files (E55 and E56) are hash-checked in tests.
- Past quarters show E56's own as-of backtests, labelled as backtests; never another model's scores.

**Tests:**

| Suite | Result |
|---|---|
| Backend | **398 passed, 18 skipped** |
| Frontend | tsc clean; **45/45 vitest** |
| E56 serving | 6 |
| E55 serving | 5 |
| E55 experiment | 7 |

**Live dashboard** (local; API on 8003 with `e56`, approved frontend on 8083, clock 2026-10-17):
- Q1 2027 forecast; regional 0.08 (Low); all provinces Low.
- Quezon 0.15 with the note: "This is a two-quarter-ahead forecast issued 2026-10-01 from predictors through 2026-Q3 (latest observed food-insecurity risk data: 2026-Q2) for Q1 2027 …".
- Triggers: Market 79%, Employment 15%, OFW 6%.
- 41 municipalities as relative prioritization; approved colours unchanged.

**Not verified:** the Render and Vercel deployments. Nothing was pushed or deployed.

## 9. Enabling the final model in production (needs your authorization)

1. **Approve:**
   - T43 as the target (adviser);
   - the development evidence in section 5, with the prospective test pending.
2. **Push** branch `e46-lead2-policy` and merge it into the branch Render and Vercel deploy from. `backend/data/e56/**` is tracked and marked `-text`.
3. **Render backend:** set the environment variable `AIPHEED_LEAD2_MODEL=e56`. Leave `AIPHEED_NOW` unset. No frontend change or Vercel variable is needed.
4. **Verify the live API:**
   - `GET /api/v1/lead2/summary` → `targetQuarter` 2027-Q1, `modelFamily` LightGBM, `finalModelArtifacts` equal to `backend/data/e56/model/manifest.json`;
   - `GET /api/v1/provinces?quarter=2027-Q1` → indicator `food_insecurity_risk_probability`.
5. **Rollback:** unset `AIPHEED_LEAD2_MODEL` (or set `e38`).
6. **Quarterly operation:**
   - The record covers only 2027-Q1, so from 2027-01-01 the dashboard target becomes 2027-Q2.
   - At that origin (issue 2027-01-01, t = 2026-Q4), load the newly published data and rerun `build_record_e56.py` adapted to the new origin. Freeze its forecast before outcomes exist.
   - Until a new record is built, `e56` does not govern 2027-Q2, and the dashboard falls back to E38 for that quarter.
7. **Score** `frozen/E56_TUNED_PROSPECTIVE_2027Q1.json` when the 2027-Q1 SWS round and the March 2027 CPI are published.

## 10. Limitations and remaining validation

- **Regional hunger only:** hunger is measured for Balance Luzon and was elevated in every evaluated quarter. The hunger component is unvalidated, and provincial risk differences come from food prices.
- **Too few quarters:** 9 quarters make every accuracy unstable (±0.09). Results are development evidence.
- **Per-origin configuration:** the selected configuration changes between origins. The method is fixed; the hyperparameters are not.
- **Over-prediction:** about 10 points (CITL −0.10). Cavite is poorly forecast.
- **National and missing data:** employment, OFW, ENSO and policy inputs are national. 2026 remittances are missing. No official fish-kill series exists.
- **Poverty:** never improved a forecast (E54, E55). It remains the Objective 3 vulnerability weight for the 142 LGU rankings, which are relative prioritization and not municipal forecasts.
- **External evaluations still needed** (not done, not simulated):
  - the ISO/IEC 25010 evaluation by 50 DA IV-A personnel;
  - expert review by DA IV-A;
  - the FNRI NNS face-validity comparison.
- **Lead time:** the furthest reliable lead time (Objective 2.V) was not re-evaluated beyond two quarters.

## 11. Commits

**E56 (this cycle):**
- 8e3e37b: protocol and freshness;
- 5daaa8f: runs;
- 0193984: serving and artifacts;
- this report.

**Earlier in this session:** E55 ad4d03b, dc1fbe2, 2ccc8cd, e4681a8, 2c9c8a0, a9c717b.

**Left uncommitted on purpose:** another session's E46 D-1 attribution edits (`insights.py` / `e41_lead2.py` hunks, `build_record_e46_d1.py`, `e46_record_d1.json`, its test).
