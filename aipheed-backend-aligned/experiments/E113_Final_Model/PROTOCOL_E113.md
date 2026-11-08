# PROTOCOL_E113: the final aiPHeed hunger forecast (pre-registered; frozen before any E113 scoring)

**Base.** Branch `aiPHeed/e113-final-model`, from E112 `efe8a24`.

**Disclosure.** Every SWS quarter through 2026-Q3 was examined in E109–E112, so every E113 retrospective result is **development evidence**. This protocol fixes:
- the E113 features, models, folds, metrics, tests, reliability criterion and selection rule;
- all of it before any E113 model is scored.

Later changes go in hashed addenda.

**Standing constraints.**
- **Study window 2021+:** no pre-2021 SWS back series is used. This is the user's hard rule, and it overrides the brief's "longer SWS history" item, which is noted for the adviser.
- **No new data collection:** only data already in the repository.

## 1. Outcome, panel, timing

- **Outcome:** SWS Total Hunger (%) for the four SWS areas, from E110 `data/sws_area_rounds.csv`:
  - NCR, BL = Balance Luzon (primary, contains CALABARZON), VIS, MIN;
  - non-commissioned rounds, 2021-Q2..2026-Q3;
  - quarter value = mean of the quarter's rounds.
- **Observation variance:** R = (margin / 1.96)², from each round's published margin.
- **Issue date:** O(t) = day 1 of quarter t+1.
- **Vintage:** rounds published before O(t).
- **Latest reading:** h_last(t, a), the newest known quarter of area a, with quarter q_last.
- **True horizon:** t + k − q_last.
- **Leads:** k = 1..6.
- **Regimes:**
  - *post-break* = target quarter ≥ 2025-Q2 (respondent base changed from household heads to adults);
  - *surge* row = sharp increase (§6);
  - *falling* row = y < h_last.

## 2. Features (all dated; zero means "nothing unusual", so a zero feature vector gives persistence)

| Id | Definition at O(t) | Available because |
|---|---|---|
| MR (mean reversion) | h_last − anchor_a. **Anchor** = mean of the area's known readings in the target's regime: if the target ≥ 2025-Q2 and ≥ 2 post-break readings are known, the post-break mean; otherwise the mean of all known readings before the target's regime boundary (all known if the target is pre-break). | SWS rounds published before O(t) |
| N-DIS (disaster) | YoY change of [disaster share + severe-disaster share]. Severe headlines count twice (severity lexicon §3). | Headlines of quarter t−L, all published before O(t) (asserted) |
| N-SUP (supply shock) | YoY change of [agri_supply share + shortage share] | same |
| N-PRI (price news) | YoY change of the price share | same |
| N-AST (assistance) | YoY change of the assistance share | same |
| P-FOOD (food inflation) | Calabarzon food CPI YoY (5-province mean), mean of the CPI months available at O(t), minus 3.0 (BSP target midpoint, fixed) | CPI month m is available from day 10 of month m+1. At O(t) that is months 1–2 of quarter t (E41 rule). |
| P-DFOOD (food-inflation direction) | The same 2-month food YoY minus the food YoY of the 2 months 3 months earlier | same |
| P-RICE (rice) | PSA wholesale regular-milled rice YoY %, quarter t−1 vs t−5 (E107 A3, provincial mean) | Quarterly release; quarter t−1 is published before O(t) |

**News lag.**
- L ∈ {0, 1}: 0 = the gap quarter t; 1 = quarter t−1.
- Chosen **inside each training fold** (§4).

**Sources.**
- News: the E112 de-duplicated corpus (`news_indicators.corpus_frame`).
- GDELT composites use E112's theme tags. GDELT has no severity term, so N-DIS(G) = YoY disaster share.

**What is not available, documented rather than imputed:**
- national CPI;
- the rice/cereals CPI sub-index;
- the CPI for regions other than Calabarzon.

P-* therefore enter every area as the **Calabarzon** food-price environment. For BL this is a direct regional signal; for NCR, VIS and MIN it is a proxy.

## 3. Severity lexicon (fixed)

`state of calamity | super ?typhoon | signal (no\.? ?|#)?[345] | death toll | dead | killed | patay | nasawi | missing | evacuat | lumikas | damage | pinsala | destroy | wiped out | billion`, matched on titles already tagged "disaster".

## 4. Models (one family for candidates: shrinkage to persistence)

**Training pairs at origin t, lead k.** For every area a and every earlier origin t′ < t:
- the target quarter q = t′+k must have been published before O(t);
- h_last(t′, a) must exist;
- dy = y_q − h_last(t′, a);
- features are computed at O(t′) exactly as at O(t).

**Eligibility.** An origin is eligible when it has at least 12 pairs from at least 3 distinct origins, and every area has at least 2 known readings.

**Candidate family: SH-x, ridge shrinkage to persistence.**
- forecast = h_last + Σ β_j x_j / s_j, with no intercept;
- s_j = root-mean-square of x_j in training: scale only, no centring;
- β by ridge.
- **Chosen inside the fold:**
  - α ∈ {1, 3, 10, 30, 100, 300, 1000};
  - the news lag L ∈ {0, 1}, for models with news.
- **Selection method:** leave-one-origin-out over the training pairs, minimising the sum of absolute errors.
- **Ties:** larger α, then L = 0.

| Candidate | Features |
|---|---|
| SH-MR | MR |
| SH-N (NLP-only baseline) | N-DIS, N-SUP, N-PRI, N-AST |
| SH-P (PSA-only baseline) | P-FOOD, P-DFOOD, P-RICE |
| SH-MRN | MR + news (5) |
| SH-MRP | MR + PSA (4) |
| SH-FULL | MR + news + PSA (8) |

**Baselines.**

| Id | Definition |
|---|---|
| RW | h_last (naive persistence) |
| MA2 | mean of the last two known readings |
| DAMP | Damped trend: h_last + slope × φ(1 − φ^g)/(1 − φ). slope = (h_last − previous reading)/gap; g = true horizon. φ ∈ {0, .25, .5, .75} by pooled training MAE in-fold. |
| AR1 | anchor + ρ^g (h_last − anchor), with the regime anchor of §2. ρ ∈ [0, 1] by pooled least squares on consecutive known readings in-fold. |
| ETS | Local-level state space (simple exponential smoothing with the published margins), E110 `llr` with pooled Q |
| LR | **Linear-regression baseline:** OLS with intercept on dy, features of SH-FULL, news lag 0, same pairs |

**Replication arms (§7.4).**
- REP-C: SH with the single feature corpus agri_supply YoY, lag 0.
- REP-G: the same with GDELT agri_supply YoY.

**Appendix.** The E112 12-family LightGBM results are cited, not re-fitted; they are not a candidate.

**Evaluation rows.** At lead k, every (area, target quarter ≤ 2026-Q3) whose origin is eligible and for which every model gives a forecast. Evaluation is rolling-origin with an expanding window, at the maximum number of origins. The number of evaluable quarters and rows is reported for every lead.

## 5. Intervals (80%)

**Conformal-style band.** The 80% band is the point forecast ± q80 of the absolute errors of the same model and lead, under these conditions:
- the errors come from earlier out-of-sample forecasts whose targets were published before O(t);
- they are pooled over areas;
- at least 8 such errors are needed;
- q80 = the ⌈0.8(n+1)⌉-th smallest.

**Fallback.** With fewer than 8 errors, use ±1.2816 × RMS(training dy).

**Reported per lead and model:**
- empirical coverage;
- the Winkler interval score at 80%.

## 6. Metrics and surge definition

**Accuracy metrics.**
- MAE, RMSE, bias (forecast − y).
- **MASE:** |e| / scale_a, where scale_a = mean |H_q − H_q−1| over the area's consecutive quarters 2021–2026. This is a fixed constant per area that only rescales.
- **Directional accuracy:** sign(f − h_last) = sign(y − h_last), over rows where |f − h_last| ≥ 0.5. Not defined for RW.
- **Interval score.**

**Surge (sharp increase).** y − h_last > 1.96 × sqrt(R_last + R_target), using the published margins: the rise exceeds the sampling noise of the two readings.

**Surge probability.** P(surge) = 1 − Φ((thr − (f − h_last)) / σ), with σ = band half-width / 1.2816.

**Surge metrics.**
- Brier score against two references:
  - climatology = the training surge rate;
  - RW, i.e. the same formula with f = h_last and RW's σ.
- Precision and recall at P ≥ 0.5.
- Number of events.

**Alert-skill claim** requires all of:
- ≥ 10 events;
- precision ≥ .5 and recall ≥ .5;
- Brier below both references with paired quarter-bootstrap p < .10.

## 7. Tests

**General method.**
- All DM tests use the E111 Newey–West HLN one-sided test (lag k−1), applied to per-quarter differentials of scaled loss |e|/scale_a, averaged over the quarter's areas.
- Raw and Holm-adjusted p are always both reported.

**7.1 Reliability family.** At each lead, the six SH candidates vs RW, Holm across the six. Leads are tested in fixed sequence (§8).

**7.2 News ablation family.**
- Comparisons: SH-MRN vs SH-MR; SH-FULL vs SH-MRP; SH-N vs RW.
- Leads 1–6; Holm over the 18 tests.
- Also reported:
  - per area;
  - per regime (surge / falling / post-break / other);
  - the news lag chosen in-fold.

**7.3 CPI covariate family.**
- Comparisons: SH-MRP vs SH-MR; SH-FULL vs SH-MRN; SH-P vs RW.
- Leads 1–6; Holm over the 18 tests.

**7.4 Agri-supply replication (BL primary, panel secondary).**
- REP-C and REP-G vs RW at Leads 1–2.
- Holm over the 4 BL tests.
- "Replicated out of sample" requires REP-G BL Holm p < .10.

**7.5 CPI validation (no hunger data).**
- Spearman ρ between the quarterly Calabarzon food CPI YoY (3-month mean) and:
  - corpus and GDELT price share;
  - corpus and GDELT price YoY.
- Lags −2..+2: news leads CPI at negative lags. The YoY pairing uses the change in CPI YoY.
- Holm over all 40 tests.
- "Price news validated" requires lag-0 or news-leading ρ > 0 with Holm p < .10.
- Also: the severity-weighted vs the plain disaster share against typhoon counts (C2).

**7.6 Inflation regime check.**
- High-inflation quarters = target quarters whose actual Calabarzon food YoY is in the top tercile of 2021-Q1..2026-Q3.
- Compare scaled |e| of RW and of the adopted model, high vs other.
- Two-sided Mann–Whitney, descriptive.

**7.7 Model Confidence Set.**
- Hansen MCS at each lead over all models, on per-quarter scaled losses.
- α = .10, T_max statistic, moving-block bootstrap (block = max(k, 2), B = 2000, seed 113).

**7.8 Survey-break sensitivity.**
- All metrics without post-break targets (S-PRE).
- The regime-anchor assumption is flagged for adviser approval. No bridging estimate exists: no overlapping old/new-design round.

**7.9 Spatial check (Objective 3).** No provincial or LGU food-insecurity series exists in the repository. The PSA provincial **subsistence incidence** (food poverty; 2021 and 2023, with CVs) is used for a consistency check only:
- Spearman of the served provincial vulnerability score V1 vs subsistence incidence, n = 5 per year;
- no forecast-validation claim.

## 8. Reliability criterion and maximum reliable lead

Lead k is **reliable (development)** for a model if all of the following hold.

| | Requirement |
|---|---|
| R1 | ≥ 8 evaluable quarters at lead k |
| R2 | Panel MASE below RW, and Holm-adjusted DM p < .10 (§7.1) |
| R3 | Empirical 80% coverage in [0.70, 0.90] |
| R4 | Mean scaled-loss difference vs RW ≤ 0 in each of: surge rows, falling rows, post-break rows. BL MAE ≤ RW BL MAE. |

**Maximum reliable lead.**
- It is the largest k such that leads 1..k are all reliable for the adopted model, using fixed-sequence testing.
- Otherwise it is "none established".
- Any reliable result is labelled development, not confirmed, until sealed forecasts are scored on unseen quarters.

**Calibrated-persistence horizon (secondary).** The largest k such that RW meets R1 and R3 at leads 1..k. It describes the honest error band of the adopted outlook. It is not a skill claim.

## 9. Selection rule (adopted forecast)

| Tier | Condition | Adopted forecast |
|---|---|---|
| 1 | Some SH candidate passes R1–R4 at lead 1 | The one with the lowest lead-1 panel MASE (ties: fewer features). Status "beats persistence (development)". |
| 2 | Otherwise: the SH candidate with the lowest lead-1 panel MASE has MASE < RW and meets R4 at lead 1 | That candidate, labelled "shrinkage forecast; not significantly better than persistence" |
| 3 | Otherwise | **RW** |

**Per-lead fallback.** At any lead where the adopted model's panel MASE ≥ RW or R4 fails, the output is RW.

**Every output carries:**
- point forecast;
- 80% band (§5);
- true horizon;
- status.

## 10. Leakage audit (run before scoring; it must pass)

1. **Future-data test.** At 5 origins, every input published on or after O(t) is replaced by extreme values:
   - SWS rounds +40;
   - news quarters > t (and quarter t's headlines dated on or after O(t));
   - CPI months not yet available.

   Every model's forecast must be unchanged (tolerance 1e-9).
2. **Shuffle placebo.**
   - 200 permutations (seed 113) of the news-feature rows across quarters, on SH-MRN at lead 1 (panel MASE); permutation p reported.
   - The same for PSA features on SH-MRP.
3. **In-fold fitting audit.**
   - Scales, α, L, φ, ρ and Q are computed only from training pairs or vintages.
   - The test asserts that the training targets' publication dates are before O(t).

## 11. Seals

- **Seal A.** Origin 2026-Q3, issue 2026-10-01, leads 1–6, 4 areas, every model:
  - point, band, true horizon;
  - adopted flag.
- **Seal B (operational vintage).** Issue 2026-10-25:
  - SWS rounds published before 2026-10-25 (newest 2026-Q3);
  - news quarters ≤ 2026-Q3;
  - CPI months available by the day-10 rule;
  - same models; leads counted from 2026-Q3.
- Both are hashed. The E107–E112 seals are verified unchanged.
- `runner/score_prospective.py` scores E109–E113 seals as rounds are published.

## 12. Reproduction

`python runner/run_e113.py all` runs:
1. news composites;
2. leakage audit;
3. scoring;
4. analyses;
5. seals;
6. export.

Seed 113. The run refuses to proceed if this file's hash differs from `runner/PROTOCOL_SHA256.txt`.
