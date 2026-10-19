# E61 consolidated report: E58's low 2027-Q1 forecast, its validity, the tested corrections, the news question, the dashboard and loading speed

**Date:** 2026-10-19.
**Branch:** `e60-accuracy-optimization`, working tree. **Nothing committed, pushed, deployed or switched.**
**Untouched:** E56–E60 artifacts, the sealed E57/E58 files and `backend/data/` (hashes verified by every script). The production default is still E38.

**Protocols:** both frozen before their candidates were scored.
- `PROTOCOL.md`: sha256 `9d38d8e7…`, candidates C1–C4.
- `PROTOCOL_ADDENDUM_1.md`: sha256 `243d619e…`; drift D1–D3, combination K1–K3, hunger H0–H2, feature ablations FA-*.

**Evidence status:**
- All 50 back-test rows (targets 2024-Q2..2026-Q3) had been examined before E61. **Every comparison here is development evidence**, and the DEV/TEST split only separates E61's own selection.
- The independent test is prospective: 2027-Q1 onward.

## 0. The answer in brief

**What the formula does and why it gives a low value**
- **Arithmetic:** correct. The served forecast reproduces exactly four ways.
- **Why it is low:** E58 multiplies P(regional hunger > 11.3%) = **0.96** by P(provincial food-price pressure) = **0.04–0.15**.
  - The price part is low because the latest food inflation (0.25–3.6%, to 2026-08) is far below each province's 2021–22 reference (4.7–7.2%).
  - Food prices also rose **slower** than prices overall (headline 4.4–6.9% in the latest months).

**Is the formula conceptually valid?** Only partly.
- **(a) The target's "food minus headline" condition** counts a surge in non-food prices as *less* pressure.
- **(b) The two parts are not independent.** Price pressure occurred in 33% of province-quarters with high hunger vs 69% with low hunger (Fisher p = 0.0008). So the product is **not a valid joint probability**. It is now labelled a "model score", not a tested probability.
- **(c) No provincial food-insecurity outcome exists.** The model forecasts an exploratory **food-stress risk indicator** whose provincial variation is CPI price pressure.

**Do the features represent the intended conditions?** Mostly price data.
- **News:** the trigger features are almost all zero.
- **Remittances:** missing at 2027-Q1 and handled through a missing-value branch.
- **Unemployment:** works in the counterintuitive direction.
- **Rice wholesale:** often used in earlier origins, but carries no supported out-of-sample signal and is unused in the 2027-Q1 trees.
- **Hunger part:** less accurate than simply carrying the last posted hunger rate forward.

**Does any correction improve out-of-sample performance?** **No.** Twelve pre-registered corrections, all tested leakage-safe on the same 50 rows:
- calibration;
- debiasing;
- a current-condition feature;
- no news;
- three drift variants;
- two probability combinations;
- three feature ablations.

None improves the Brier score under the frozen rules, and none is statistically different from E56. **The low 2027-Q1 value survives every defensible variant tested**: the alternatives that raise it (forced drift, no projection) did no better out of sample.

**Are the probabilities trustworthy?** Not as precise probabilities.
- 3 of 11 back-test price-part values below 0.20 were followed by HIGH (27%, 95% CI 10–57%).
- Calibration slope CIs are wide.
- Read 2027-Q1 as **"low under the current target, with real uncertainty"**.

## 1. Candidate evaluation, all 11 origins

**Run completeness:**
- 10 rolling origins (2023-Q4..2026-Q1 → 50 sealed rows, no missing values) plus the operational origin 2026-Q3 (2027-Q1, never scored).
- Logs: `out/c1_console.txt`, `out/d1_console.txt`.

**Timing (no leakage):** `runner/a6_truncation.py`.
- At every origin, all inputs were cut to what was published before the issue date (E59 rule: CPI to month 2 of t, SWS posted before O(t), OFW and rice to t−1, policy announced before O(t)).
- C2, C3, C23 and C4 were rebuilt and re-run on the truncated data: **all 40 forecasts identical (max difference 0.0, same configurations)** (`tables/a6_truncation_test.csv`).
- C1 and K2 fit only on earlier forecasts whose outcomes were published before O(t).
- The C0 refit equals the sealed E57 values within 1e-9 at all 10 origins, and the served 2027-Q1 values within 1e-6.

**Same target, same rows:** T43 everywhere. The scripts assert that outcomes equal the E58 events file and that all 50 rows have hunger > 11.3%.

**Selection kept apart from evaluation:**
- The rule is applied to DEV only (30 rows), then reported on all 50 and on TEST (20 rows, 1 HIGH: nearly uninformative about detection).
- Both protocols were frozen before scoring.
- The full set had been seen in earlier experiments, so the separation is internal to E61 only.

**Significance rule (addendum §1):** "supported" needs both a quarter-cluster bootstrap CI that excludes 0 **and** a quarter sign test p < 0.05. With 10 quarters, the sign test needs at least 9 of 10 quarters on one side.

**All candidates and baselines, 50 rows, T43:** sources are `tables/c2_model_comparison.csv` and `tables/d2_model_comparison.csv`.

| Model | Correct /50 | Accuracy | Balanced acc. | HIGH recall | HIGH precision | Brier | Calibration slope [95% CI] | Onsets (warning form) /10 | ΔBrier vs E56 [95% CI]; quarters better/worse; sign p | Verdict |
|---|---|---|---|---|---|---|---|---|---|---|
| **E56 (C0)** | 36 | 0.72 | 0.68 | 0.56 | 0.63 | **0.214** | 0.55 [0.17, 1.49] | 7 | — | reference |
| **E58-EW** (warning when P_price ≥ 0.5) | 39 | 0.78 | 0.78 | 0.78 | 0.67 | 0.220 (P_price) | — | **7** | — | reference |
| C1 online recalibration | 35 | 0.70 | 0.66 | 0.50 | 0.60 | 0.222 | 0.53 | 6 | +0.008 [−0.010, +0.029]; 4/2; 0.69 | no difference |
| C2 debiased projection | 32 | 0.64 | 0.62 | 0.56 | 0.50 | 0.246 | 0.45 | 7 | +0.032 [+0.005, +0.056]; 2/8; 0.11 | worse, **suggestive, not established** |
| C3 current-condition feature | 35 | 0.70 | 0.66 | 0.50 | 0.60 | 0.224 | 0.48 | 7 | +0.010 [−0.001, +0.025]; 3/5; 0.73 | no difference |
| C23 (C2 + C3) | 31 | 0.62 | 0.61 | 0.56 | 0.48 | 0.250 | 0.43 | 7 | +0.036 [+0.008, +0.064]; 2/8; 0.11 | worse, suggestive, not established |
| C4 no news in the price part | 37 | 0.74 | 0.70 | 0.56 | 0.67 | 0.212 | 0.56 | 7 | −0.002 [−0.006, +0.001]; 1/1; 1.0 | no difference |
| D1 trailing-12-month drift | 32 | 0.64 | 0.62 | 0.56 | 0.50 | 0.232 | 0.48 | 7 | +0.018 [−0.016, +0.047]; 4/5; 1.0 | no difference |
| D2 recent 6-month trend | 35 | 0.70 | 0.66 | 0.50 | 0.60 | 0.222 | 0.56 | 7 | +0.008 [−0.024, +0.037]; 5/5; 1.0 | no difference |
| D3 no projection (latest values only) | 26 | 0.52 | 0.44 | 0.17 | 0.25 | 0.260 | −0.47 | 6 | +0.046 [−0.006, +0.097]; 3/7; 0.34 | no difference (clearly poorer decisions) |
| K1 conditional P(PS ∣ high hunger) | 33 | 0.66 | 0.64 | 0.56 | 0.53 | 0.233 | 0.41 | 7 | +0.019 [−0.005, +0.044]; 1/4; 0.38 | no difference |
| K2 calibrated combination | 34 | 0.68 | 0.71 | 0.83 | 0.54 | 0.273 | 0.27 | — | +0.059 [−0.062, +0.203]; 3/7; 0.34 | no difference (overfits) |
| K3 parts reported separately (decision only) | 36 | 0.72 | 0.68 | 0.56 | 0.63 | — | — | 3 | same decisions as E56 | equal |
| FA-rice (no rice wholesale) | 34 | 0.68 | 0.63 | 0.44 | 0.57 | 0.218 | 0.55 | 7 | +0.004 [−0.015, +0.022]; 2/6; 0.29 | no difference |
| FA-emp (no employment) | 36 | 0.72 | 0.68 | 0.56 | 0.63 | 0.215 | 0.54 | 7 | +0.001 [−0.000, +0.003]; 1/3; 0.63 | no difference |
| FA-ofw (no remittances) | 34 | 0.68 | 0.65 | 0.56 | 0.56 | 0.204 | 0.64 | 7 | −0.010 [−0.030, +0.007]; 4/1; 0.38 | no difference |
| Price projection (B-PROJ) | 34 | 0.68 | 0.65 | 0.56 | 0.56 | 0.228 | 0.46 | — | +0.014 [−0.020, +0.047]; 3/7 | no difference |
| B-NOW (latest months meet the price condition, 0/1) | 35 | 0.70 | 0.69 | 0.67 | 0.57 | 0.300 | — | 7 | — | — |
| Persistence | 28 | 0.56 | 0.54 | 0.44 | 0.40 | 0.440 | — | 0 | — | — |
| Majority (always LOW) | 32 | 0.64 | 0.50 | 0 | — | 0.360 | — | 0 | — | — |

**Frozen-rule outcomes (no candidate qualifies):**

| Family | Selected on DEV | Result |
|---|---|---|
| PROTOCOL §4 | C1 | fails (a)–(d) |
| Drift | D1 | fails (a), (b), (c), (e) |
| Combination | K1 | fails (a), (b), (c), (e) |
| Calibration claim (C1) | — | not supported |
| News claim (C4) | — | not supported |

**75% goal:** no HIGH/LOW forecast reaches 0.75 pooled accuracy. The warning forms reach 0.78 (E58-EW) and 0.80 (C4 warning). The difference is one row and is not significant.

**Small-sample caution:** 50 rows, 10 quarters, 18 HIGH and 10 onsets. Two models one or two rows apart cannot be distinguished. **Correction to my earlier wording:** I had called C2 "significantly worse". Under the frozen rule it is *worse in the bootstrap but not established* (sign test p = 0.11).

**Per quarter and per province:** `tables/c2_by_quarter.csv`, `tables/d2_by_quarter.csv`, `tables/c2_by_province.csv`, `tables/a2_calibration_by_province.csv`.
- E56 accuracy by quarter ranges 0.2 (2024-Q2) to 1.0. Three quarters are all LOW.
- Cavite is the weakest province (accuracy 0.4); Rizal has no HIGH rows.

## 2. Verified root causes of the low 2027-Q1 forecast

**Reproduction (A1):** served API = record = artifacts alone = frozen E56 file = full retrain, max difference 3.7×10⁻⁷ (`tables/a1_reproduction_2027Q1.csv`).

**Model and timing:**
- Model: E56-TUNED LightGBM, configuration 23.
- Issued 2026-10-01; inputs CPI to 2026-08 and SWS to 2026-Q2 (17.3%).
- The 2026-Q3 SWS round (23.6%, posted 2026-10-14) came after the issue date.

| Province | P_hunger | P_price (projection only → with trees) | Score | Projected food YoY vs threshold | Projected gap vs threshold |
|---|---|---|---|---|---|
| Cavite | 0.962 | 0.149 → 0.113 | 0.109 | 1.03 vs 4.71 | −2.53 vs 0.74 |
| Laguna | 0.962 | 0.089 → 0.073 | 0.070 | 0.86 vs 6.05 | −2.42 vs 0.61 |
| Quezon | 0.962 | 0.182 → 0.152 | 0.146 | 2.08 vs 6.24 | −2.58 vs −0.56 |
| Rizal | 0.962 | 0.070 → 0.052 | 0.050 | 1.67 vs 7.10 | −2.55 vs 0.92 |
| Batangas | 0.962 | 0.060 → 0.044 | 0.043 | 0.75 vs 7.15 | −2.50 vs 0.66 |

**Causes, verified:**

1. **The price part drives it.**
   - Every province is far from both price conditions. The latest-months margins to the condition are −1.9 to −4.8 points, so B-NOW is 0 everywhere.
   - The joint can never exceed the smaller part (Fréchet bound), so **no dependence structure between hunger and price can raise any province above its P_price**.
2. **The gap condition reads a non-food surge as relief.**
   - In 2026-Q2/Q3, headline inflation was 6.5–8.0% in Cavite, Laguna, Quezon and Rizal, while food inflation was 3.6–4.9%.
   - Every 2026 province-quarter was LOW except Cavite 2026-Q2 (by +0.02 points).
3. **The 2027-Q1 trees lower it slightly** (−0.22 to −0.31 log-odds). They split only on national unemployment (20 splits), PHP remittances (15) and corn production (5); see section 4.
4. **Not the cause:**
   - the multiplication itself (point 1);
   - the hunger part, which is *over*-predicted and would lower the score if corrected (section 3.3).

**Missed HIGH cases (A3, `tables/a3_missed_high_cases.csv`):** all 8 E56 false negatives were re-run at their own issue dates (reproduction error 0) with exact TreeSHAP.
- **2024-Q2, four provinces:** stale hunger reading (10.3% posted vs 19.6% actual). Not predictable from hunger data then. E58-EW already handles it.
- **2024-Q4 Cavite and Laguna:** the latest gap already exceeded its threshold (+1.0 / +0.7 vs 0.74 / 0.61). The projection put it at −1.4 / −1.2. C3 (current-condition feature) and B-NOW tested this; neither improved overall.
- **2025-Q1 Batangas:** P = 0.45, near the line.
- **2026-Q2 Cavite:** borderline label (+0.02 points) after a rice-price rebound that came after the issue date.
- **Low-probability table** (`tables/a2_low_probability_cases.csv`): 14 rows below 0.20, of which 6 were HIGH, verified against the sealed files and recomputed CPI/SWS outcomes.

## 3. Drift and probability-combination results

### 3.1 The "flat-price" drift

**Is m = 0 a fixed choice?** No. E56 selects m ∈ {1.0, 0.5, 0.0} at each origin by inner forward log-loss on training targets. It chose m = 0 at 8 of 11 origins, including 2027-Q1.

**Training bias:**
- On the 2027-Q1 training rows, m = 0 under-projects food YoY by +2.19 points on average (gap bias +0.01).
- The trees are intercept-free and cannot remove that.

| Alternative | Out-of-sample result (50 rows) | 2027-Q1 effect | Disposition |
|---|---|---|---|
| Debias by the training mean error (C2) | Brier 0.246 vs 0.214, worse (suggestive): false positives 6 → 10 | 0.02–0.16 | **rejected** |
| Drift from the trailing 12 months, forced (D1) | 0.232, no difference; accuracy 0.64 | raises to 0.09–0.41 | **rejected** (higher, not better) |
| Recent 6-month trend (D2) | 0.222, no difference | 0.08–0.25 | **rejected** |
| No projection, latest values only (D3) | 0.260; balanced accuracy 0.44, HIGH recall 0.17 | 0.13–0.46 | **rejected** |

**Conclusion:**
- The projection is biased low for food YoY, but the target's thresholds are high. Selecting m = 0 by inner validation is not beaten out of sample.
- **The original is kept and the limitation documented.**
- The variants that would raise 2027-Q1 did not forecast better. Adopting them would only raise the number.

### 3.2 The probability combination

**What the parts are:**
- **P_hunger:** P(regional SWS hunger > 11.3% in the target quarter), from a ridge forecast of the regional hunger rate with a normal error.
- **P_price:** P(provincial price condition), trained on PS labels from all rows, both hunger regimes. On the evaluation rows, where hunger was always high, it acts as an estimate of P(PS ∣ high hunger).

**Validity of the product:** dependence is shown, so the product is not a valid joint probability.

| Option | Result | Disposition |
|---|---|---|
| K1 conditional (price part trained only on high-hunger quarters) | Brier 0.233; falls back at 5 early origins (< 6 quarters) | **rejected** (too little data) |
| K2 calibrated combination (stacking on earlier forecasts) | Brier 0.273, slope 0.27: overfits 10–35 rows | **rejected** |
| K3 report the two parts separately | same decisions as E56 | **accepted for display** |

**Display change:**
- The dashboard now shows both parts and calls the product a **"model score … not a tested probability"**. The served numbers are unchanged.
- The parts are scored separately:
  - P_price vs PS: Brier 0.182, accuracy 0.78;
  - P_hunger: Brier 0.062 over 10 quarters, all with hunger > 11.3%, so its false alarms cannot be evaluated.

### 3.3 The hunger part (addendum §4)

Sources: `tables/d2_hunger_variants.csv`. 10 targets, predicted hunger rate vs observed.

| Variant | RMSE (points) | Mean error | Better than H0 in | Disposition |
|---|---|---|---|---|
| H0 served ridge (12 inputs incl. news volume) | 8.24 | +2.39 | — | — |
| H1 without total news volume | 8.01 | +1.50 | 6/10 | meets the rule |
| H2 random walk (last posted rate) | **6.10** | −1.66 | 6/10 | **meets the rule; best** |

**Reading:**
- The served hunger regression over-predicts 2025–2026 hunger by up to 7 points (e.g. 30.8 vs 17.3 for 2026-Q2). Carrying the last posted value forward is more accurate.
- At 2027-Q1, H2 gives P_hunger 0.88 instead of 0.96, so the score would be **0.04–0.13**: lower, not higher.

**Disposition:** accepted as a **finding and recommendation** (use the random walk for the hunger part from the next prospective origin). **Not applied** to the served model, which needs your authorization.

## 4. Disposition of every identified feature defect

| Issue | Type | Evidence | Disposition |
|---|---|---|---|
| Gap above threshold at issue not carried forward (2024-Q4) | model limitation | C3 and B-NOW tested; no improvement (C3 +0.010, no difference) | evaluated, **rejected**; documented |
| News and policy features mostly zero | data and feature defect | zero share: OFW news 100%, employment and fish-kill news 98%, market news 96%, import-suspension and price-ceiling 100% (`tables/a5_feature_audit.csv`); removing news: −0.002 (C4, no difference) | evaluated; **no predictive value shown**; improved news pending E60 (section 6) |
| Hunger forecast leans on total news volume (+5.1 points at 2027-Q1) | feature-engineering defect | H1 without it: RMSE 8.01 vs 8.24; random walk 6.10 | evaluated; **random walk recommended** for the hunger part (not served) |
| Remittances missing for 2027-Q1 | data defect (BSP series ends 2025-Q4; bsp.gov.ph returns 403 to scripts) | the 15 tree splits on `remit_php_yoy` send a missing value down a branch learned from 2021 rows where the year-earlier base did not exist; group effect −0.097 log-odds; removing remittances changes 2027-Q1 by ≤ 0.008 and 50-row Brier by −0.010 (no difference). Not zero-filled (LightGBM `missing_type = NaN`; ridge uses the median plus an indicator). | **disclosed** in the dashboard text; **data refresh deferred** (manual BSP download needs your OK) |
| Unemployment direction counterintuitive and mislabelled | model limitation | rising unemployment (+0.90 points) lowers both parts; removing employment changes Brier by +0.001 (no difference) | **explanation fixed** (dashboard says it is a statistical pattern, not evidence); feature kept |
| Rice wholesale prices get zero weight | legitimate lack of shown signal | most-split feature over origins (198 splits at 6 of 11) but 0 splits in the 2027-Q1 model; removing it: +0.004 (no difference) | evaluated; **no supported signal**; kept |
| Stale or misaligned features | — | E59 timing table plus E61 truncation test: no input after the issue date. Rice and OFW use t−1; SWS is 1–2 months late (the 2024-Q2 stale-hunger case). | issue-date change (after each SWS release) **deferred** to an adviser decision |
| Training vs serving consistency | — | C0 refit = sealed (1e-9) and = served 2027-Q1 (1e-6); the served booster's features equal the saved schema (E56 test) | verified |

## 5. Target validity

**Sources:** A4, `tables/a4_target_comparison.csv`.

**What the current target (T43) measures:**
- regional SWS hunger above 11.3% (Balance Luzon, not CALABARZON alone) **and** provincial food-price pressure (food YoY or food-minus-headline above the province's 2021–22 60th percentile);
- in 2024–26 hunger was always above 11.3%, so **its provincial variation is CPI price pressure**;
- 13 of 18 HIGH rows were set by the gap alone, and 7 of 18 were decided by under 0.5 points.

**What it does not measure:**
- household food insecurity, hunger or food access in a province;
- the level of food prices (food CPI is +19% to +25% above 2021-Q1);
- budget pressure when non-food prices rise faster.

**Independent provincial outcomes:** **none exists in the project data.**
- SWS is regional.
- PSA subsistence incidence covers 2021 and 2023 only.
- FNRI FIES is regional, survey years only.
- No CBMS or provincial FIES series.

**Alternatives:**
- ABS4, GAP0, ACC1 and RFP do not track SWS hunger; ABS4 correlates negatively with it (ρ = −0.47, p = 0.03).
- The hunger-gated alternatives track it only because they contain it.
- **None is validated.** None was adopted, and none was used to choose a model.

**Conclusion:**
- The system forecasts an **exploratory food-stress risk indicator** whose skill is in provincial food-price pressure.
- It is **not a validated food-insecurity forecast**.
- The gap-condition defect is documented. Changing the target is an adviser decision, and any change must be scored prospectively.
- This limitation is kept in the dashboard text and must stay in the thesis.

**Supported vs unverified:**
- **Supported:** the reproduction; the timing (truncation test); the negative results above; the price-level and inflation facts (PSA CPI); the hunger level (SWS).
- **Unverified:** that any variant generalizes beyond 2024–26; any causal reading of an attribution; the meaning of the hunger part in a low-hunger regime.

## 6. Was the improved news used?

**No.** Detail is in `NEWS_PIPELINE_USE_AUDIT.md`.
- E60's collector is still running. At 09:00 it was at 61% (through 2024-07), and the follow-up session estimates it finishes around 15:00 PH.
- Its classifier v2 is not frozen, and its annotations are AI-made, not human-verified.
- No features were built, no model trained or evaluated, nothing served.
- The served E56/E58 use the E40 keyword shares (`E40_SWS_CPI_Tiers/runs/triggers/composition.csv`).

## 7. Did news improve prediction?

**Original news:** no measurable value.
- Removing it from the price part (C4): Brier 0.212 vs 0.214 (CI −0.006 to +0.001); 7/10 onsets in both; missed HIGH cases 8 vs 8.
- P(HIGH) changed on only 10 of 50 rows (2025-Q3/Q4); one warning changed (Batangas 2025-Q3, where removing news was correct).
- The hunger part's total-news-volume input makes its hunger forecast slightly worse (H1 vs H0).

**Improved news:** **not evaluated.** The ablation (gov-only / news-only / gov+improved news / +history, same 50 rows) runs in the follow-up session once collection finishes.

**Display vs prediction are separate outcomes:** news articles appear in the dashboard's news list, but that does not mean they improve the forecast.

## 8. Dashboard explanation: implementation and tests

**Design unchanged.** Per your instruction, there is no new UI element.
- The collapsed box I added earlier was **reverted**: `RightAnalyticsPanel.tsx` and `apiTypes.ts` equal HEAD.
- The explanation reaches the dashboard through the **existing summary sentence** (`summary.sentence`, shown in the approved plain-summary paragraph and in the narrative/PDF).
- The backend also returns `components` and `caveat` for API users.
- Active only for an issued two-part forecast (E55/E56/E58 records). Older E43–E53 records and back-test quarters keep their wording.

**Laguna 2027-Q1, as served** (`out/served_sentence_laguna_2027Q1.txt`; read from the live DOM of the local build in E58 mode):

> Food-insecurity risk (high regional hunger together with provincial food-price pressure) in Laguna for 2027-Q1 is forecast LOW (model score 7%: the two parts that follow, multiplied together; not a tested probability): regional hunger is likely to stay above 11.3% (96%) and provincial food-price pressure is unlikely (7%); the target needs both. Within the price part, Market / Prices lowered it and Employment lowered it. No early warning: food-price pressure 7%, HIGH-risk score 7%. Food prices in Laguna were 2.9% higher than a year earlier (latest months to 2026-08); the price condition needs more than 6.05% (this province's usual 2021-2022 level) or food prices rising faster than prices overall. Prices overall rose faster (6.9%), which this target counts as less food-price pressure, although it also means a peso buys less. Regional hunger (SWS, Balance Luzon) was 17.3% in 2026-Q2, above the 11.3% line. Slower food inflation does not mean food has become affordable; it means prices are rising more slowly. The model lowered its estimate while national unemployment rose (+0.90 points); this is a statistical pattern in a short history, not evidence that job losses reduce food stress. Some OFW Remittance figures were not yet published when the forecast was issued; the model's effect for that group partly or wholly reflects how it handles a missing figure, not an observed value. In back-tests, 3 of 11 price-pressure probabilities below 20% were followed by HIGH, so a low value can miss emerging stress; treat it as uncertain. This is an experimental forecast of a food-stress risk indicator (SWS regional hunger and PSA food prices), not a measure of household food insecurity. Data: limited (Some inputs not available at the issue date for OFW Remittance.)

**Every figure comes from the record's own observations:** the parts, food YoY, threshold, headline (= food − gap), hunger and its quarter, the unemployment change and the missing groups. The back-test figure is checked against `out/a2_calibration_joint.json`.

**Tests:**

| Suite | Result |
|---|---|
| `backend/tests/integration/test_e61_forecast_context.py` | **12 passed**: forecast values and timing unchanged; parts equal the record; "model score … not a tested probability" and no "probability" wording for the product; caveat figures equal the record; affordability and proxy wording; missing-input disclosure; employment note only when directions conflict; back-test figure equals the audit; E43/E44/E46/E52/E53 wording unchanged; back-test quarters unchanged; record cache re-reads a changed file |
| Full backend suite | **414 passed, 18 skipped** (402 before E61) |
| `frontend/src/test/summarySentence.test.tsx` | passes: the existing paragraph shows the backend sentence verbatim; no `<details>` |
| Frontend vitest | **46 passed** |
| Production build | passes |

**Known failure:** `tsc --noEmit -p tsconfig.app.json` gives 6 errors, all in untouched `src/data/mockData.ts`. They predate E61.

## 9. Loading performance, before and after (E58 mode, local)

**Setup:**
- **Before:** the same server with the HEAD record loader restored at runtime (re-read and re-hash the 300 KB record on every call; `scratchpad/serve_variant.py before`).
- **After:** the working tree (record cached per file version, re-read when the file changes).
- Same frontend build, same machine, same request list (`measure_api.py`).
- The deployed Render/Vercel dashboard was **not measured**: no deployment URL is available.

| Measure | Before | After |
|---|---|---|
| Dashboard first load, cold server: all 14 API responses in | **15.6 s** | **1.5 s** |
| Dashboard reload, warm server: all API responses in | **10.4 s** | **0.66 s** |
| Cold server, 9 parallel first requests (wall time) | 4.8–8.9 s each | 1.2–1.4 s each |
| Warm median: regional explanation | 3,244 ms | 32 ms |
| Warm median: regional timeseries | 2,540 ms | 77 ms |
| Warm median: province explanation (Laguna) | 736 ms | 13 ms |
| Warm median: province timeseries | 1,541 ms | 42 ms |
| Warm median: provinces list | 169 ms | 12 ms |
| First municipality list (pandas frame build) | 2.4 s | 2.3 s (unchanged) |

**Default E38 mode:** unaffected. Warm requests are 5–50 ms both before and after (measured at the start of the session).

**Checks:**
- **News does not block the forecast.** News requests start at the same moment as the forecast requests (about 810 ms) and run in parallel. Before the fix, every request waited behind the slow explanation calls on the single event loop.
- **Freshness:** the record cache is keyed by file path, modification time and size. A changed record is re-read and re-hash-checked on the next call (test). The dashboard's own lru caches are keyed by serving mode.

**Not changed:**
- **Duplicate requests (5 of 14):** the frontend requests before and after resolving the current quarter. Each now costs ≤ 30 ms; fixing it would change frontend logic.
- **Bundle and static assets:** one 1.93 MB JS bundle (565 KB gzipped), 1 MB of logo PNGs, 600 KB gzipped GeoJSON.

These are **deferred**: they are frontend changes, and you asked for no design changes. Code-splitting would not change the look, but it needs your OK.

**Also observed:** `basemap.pmtiles` in `frontend/public` is a 1.4 KB file that is not a valid archive ("Wrong magic number", about 70 console errors per load). This predates E61 and is not fixed.

## 10. Remaining limitations and next justified steps

**Fixes and their status:**

| Proposed fix | Status |
|---|---|
| Dashboard wording (parts, score label, caveat, missing-input and unemployment notes) | **implemented, tested, verified in the running app**; not committed |
| Record cache (speed) | **implemented, measured, tested**; not committed |
| Calibration (C1), debiasing (C2), current-condition feature (C3), no news (C4), drift D1–D3, combination K1–K2 | **evaluated, rejected** (no supported improvement) |
| Report the parts separately (K3) | **accepted for display** (done through the sentence); combined probability relabelled |
| Hunger part: use the random walk (H2) | **evaluated, accepted as a recommendation**; **deferred** (served-model change needs authorization) |
| Gap-condition target fix | **deferred** to an adviser decision; prospective only |
| Issue date after each SWS release | **deferred** to an adviser decision |
| BSP remittance refresh (2026) | **deferred**; needs a manual download (BSP blocks scripts) |
| Improved-news ablation | **in progress elsewhere**: the follow-up session runs it when E60 collection ends (about 15:00 PH) |
| Frontend duplicate requests, code-splitting, invalid basemap | **deferred**; frontend changes need your OK |

**Evidence still needed:**
- prospective scores (2027-Q1 onward);
- a provincial food-insecurity outcome (CBMS or provincial FIES);
- more evaluation quarters (only 10 now, one hunger regime);
- a human-verified news relevance sample.
