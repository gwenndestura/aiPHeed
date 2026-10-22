# E96: target validity, formulation, false alarms, signal availability and news (report)

**Branch.** `e96-target-formulation`, from `e95-root-cause-breakthrough` (115be91). Not pushed. Production is
unchanged; the dashboard stays on FIRI v2 by the user's decision (§7).

**Evidence.**
- Protocol: `PROTOCOL.md` (Q1–Q4, frozen at 9120a62 before scoring).
- News audit: `runner/news_audit.py`, `news_audit.json`, `news_audit_quarters.csv`.
- Run: `runs/20261022T073838Z/` (`metrics.json`, `predictions_k{1..4}.csv`).
- Tests: `backend/tests/integration/test_e96_target_formulation.py`.

This is the thirteenth experiment on the same 13 quarters (2023-Q1..2026-Q3), so the results are development evidence.
Only the sealed 2026-Q4..2027-Q2 quarters are unseen.

## 1. Target validity: what can be measured

| Variable | Kind | Geography | Usable as a forecasting target? |
|---|---|---|---|
| SWS involuntary hunger | **Measured** food insecurity | Balance Luzon. Provincial rows are the regional value repeated (`stratum_inherited`). | Yes, **regional only**: 19 quarters |
| FNRI FIES | **Measured** food insecurity | 2021: 3 areas; 2023 and 2025: region only | No: 5 values, no time series |
| CBMS 2024 | Measured (household items) | LGU | Not in the repository |
| Food CPI, rice, world prices | Contributing condition (affordability) | Province | No: a proxy if used as an outcome |
| Climate, employment, remittances, poverty, news | Contributing conditions | Mixed | No |

**Conclusion.** No measured provincial food-insecurity series exists in the data. A provincial measured target cannot
be built without fabricating observations, which was not done.
- **T43 is kept** as the original target. It is a proxy: provincial price pressure under elevated regional hunger.
- **The measured alternative is regional SWS hunger,** evaluated separately (Q1).

## 2. Q1: forecasting the measured outcome (SWS hunger, regional, 13 quarters)

| K | RMSE: model / random walk / climatology | Holm p vs random walk | Threshold accuracy (H > 11.3): model / persistence | Deterioration events (rise ≥ 3 points): events / hit / false |
|---|---|---|---|---|
| 1 | 4.98 / **3.91** / 6.81 | 0.83 | **0.923** / 0.846 | 5 / 2 / 3 |
| 2 | 8.88 / **5.75** / 7.09 | 1.0 | 0.615 / 0.692 | 7 / 2 / 3 |
| 3 | 7.78 / **6.14** / 7.26 | 1.0 | 0.615 / 0.538 | 6 / 1 / 3 |
| 4 | 8.72 / **6.65** / 7.40 | 1.0 | 0.692 / 0.462 | 6 / 1 / 3 |

**The continuous formulation does not beat the random walk at any K.** The linear-tree regressor learned the 2024
surge's momentum and projected it forward. It forecast 28.7, 29.3 and 31.0 for 2025-Q4, 2026-Q1 and 2026-Q3, against
observed values of 16.7, 22.4 and 23.6.
- The **threshold** reading is better than persistence at K = 1 (12 of 13 quarters correct).
- The **level** forecast is not.
- Two of the five K = 1 deteriorations were caught: 2024-Q4 and 2025-Q1. The onsets in 2023-Q4, 2024-Q1 and 2024-Q2
  were missed.

**Decision.** No change to the target. The hunger component is kept as a threshold probability, not a level forecast.

## 3. Q2: the false-alarm mechanism (T43)

DECAY replaces the raw 4-quarter inflation sum with a decaying, direction-gated inflation memory. Its half-life is
chosen by inner validation on training data only.

| K = 1 | Accuracy | Balanced | HIGH caught | Brier | 2025–26 accuracy / Brier |
|---|---|---|---|---|---|
| POV (E94 + poverty) | **0.846** | **0.814** | **12/16** | 0.142 | 0.76 / 0.168 |
| DECAY | 0.754 | 0.668 | 8/16 | **0.140** | 0.72 / **0.143** |

DECAY reproduces E95's trade-off. Fewer false alarms after 2025, but 4 of the 2023–24 detections are lost.
- The frozen selection (mean Brier K = 1..3, 2023–24) keeps POV: 0.1562 vs 0.1598.
- POV is identical to E94, because poverty changes nothing (§4).

## 4. Q3: signal availability, five required groups

Change in K = 1 / K = 2 Brier when a group is dropped from the selected arm (negative = the group helped):

| Group | K = 1 | K = 2 | K = 3 | Reading |
|---|---|---|---|---|
| Market / food prices | **+0.066** (accuracy 0.846 → 0.631) | +0.010 | +0.043 | **The only group with signal** |
| Climate stress | 0.000 | −0.001 | +0.001 | None |
| Employment, remittances, OFW | 0.000 | −0.005 | −0.011 | None. Slightly harmful at K ≥ 2. |
| News / NLP | −0.000 | **−0.015** | **−0.012** | None at K = 1; slightly harmful at K ≥ 2 |
| Poverty / vulnerability | 0.000 | 0.000 | 0.000 | None: static, and known only from 2025 |

## 5. Q4: does news contribute?

**Why news has not helped** (audit):
- **The training years have almost no news.** In 2021–22, only 2–21 admitted articles per quarter (of 150–320
  collected); 664 admitted in total.
- **Titles only:** 87.5% of articles have no lead text.
- **Weak geography:** 44% are attributed to a province.
- **Changing volume:** collection grows about 5× over the period, so rates per collected article are needed.
- **Deduplication works:** 558 events from 664 articles.
- **The single visible lead:** adverse supply events peaked in 2023-Q2 (13), two quarters before the 2023-Q4 onset. One
  episode cannot be learned.

**Controlled comparison** (all else equal): paired per-quarter Brier gain over the no-news arm.

| K | N3 (selected) | + event-based food-access news with novelty (IMP) | + news interactions (INT) |
|---|---|---|---|
| 1 | +0.0005 (5 better / 7 worse, p = 0.45) | −0.0064 (p = 0.90) | −0.0096 (p = 0.98) |
| 2 | −0.0146 (5 / 6, p = 0.96) | −0.0140 | −0.0151 |
| 3 | −0.0123 | −0.0136 | −0.0155 |
| 4 | 0.0000 | −0.0043 | −0.0018 |

**News does not add net predictive value** in any representation, by a leakage-free paired comparison.

**News can change individual forecasts** (counterfactual: news set to its training median, everything else observed):

| Case | With news | News at median | Outcome |
|---|---|---|---|
| 2024-Q2, K = 1, Cavite | **0.580** | 0.533 | HIGH ✓ (both call HIGH) |
| 2024-Q2, K = 1, Batangas | **0.554** | 0.504 | HIGH ✓ |
| 2024-Q2, K = 1, Laguna | **0.501** | 0.483 | HIGH: **news moves the call from LOW to HIGH** ✓ |
| 2025-Q4, K = 1, Quezon | **0.451** | 0.556 | LOW: **news prevents a false alarm** ✓ |
| 2025-Q4, K = 1, Cavite | 0.796 | 0.771 | LOW: news slightly worsens a false alarm ✗ |
| 2023-Q4 and 2024-Q2, K = 2 | changes ≤ 0.01 | — | No effect at the early-warning horizon |

**What this establishes.** News is integrated and can move a forecast across the decision threshold; it did so
correctly in two of the cases above. But its net effect is zero to slightly negative, and it does nothing at K = 2.
- **The likely cause is coverage, not modelling:** sparse, title-only news in the years the model learns from.
- **The credible route** is a fuller archive for 2021–2023 with lead or full text and better province attribution. That
  is new collection, which was out of scope by the user's deadline instruction.

## 6. Outcome

| K | Selected model (= E94 framework + poverty, N3 news): accuracy / balanced / HIGH caught / Brier | Unmet criteria |
|---|---|---|
| 1 | 0.846 / 0.814 / 12/16 / 0.142 | Brier significance only (Holm 0.105 / 0.177) |
| 2 | 0.692 / 0.564 / 5/16 / 0.215 | all four |
| 3 | 0.646 / 0.513 / 4/16 / 0.191 | all four |
| 4 | 0.585 / 0.493 / 5/16 / 0.255 | all four |

**Validated K = 0.** No E96 candidate improves on E94 under the frozen rules.

**What E96 adds is evidence.**
1. No measured provincial outcome exists.
2. The continuous measured-hunger formulation loses to the random walk.
3. Inflation memory is simultaneously the 2023–24 detection signal and the 2025 false-alarm source.
4. Only the market group carries signal.
5. News is integrated and occasionally decisive, but adds no net value with the current coverage.

## 7. Thesis text: the dashboard and the forecasting model (user decision 2026-10-22)

> The deployed aiPHeed dashboard presents FIRI v2, an evidence-weighted food-insecurity risk index for two quarters
> ahead. It combines affordability (including the E56 LightGBM food-price-pressure forecast), vulnerability,
> climate/production, household economy, news and regional hunger indicators, with SHAP attributions.
>
> The forecasting experiments in this chapter (E83–E96) evaluate a separate unified LightGBM forecasting framework
> against the pre-registered criteria. Its strongest result is one quarter ahead (84.6% accuracy, 12 of 16 high-risk
> cases), and no horizon was validated (K = 0).
>
> The dashboard index and the forecasting framework are therefore not the same model and do not share a horizon. The
> dashboard's values should be read as an indicator-based risk index, not as validated forecasts. Replacing the index
> with the unified forecasting model was deferred.
