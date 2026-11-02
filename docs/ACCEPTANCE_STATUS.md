# aiPHeed acceptance status (2026-11-03)

This is the single status page for Objectives 1–4. Each item is classified as **verified**, **provisional**,
**failed** or **external limitation**. Evidence lives in `docs/fi6/`, `docs/fi7/` and `docs/fi8/`. The FI7 code is
frozen at commit `6a8b114`; FI8 results are in `backend/data/fi8/`.

## Why no further experiments were run for the 2026-11-03 "one controlled rebuild" directive

The directive's central question is whether government and news information can improve on the latest SWS reading.
FI8 had already answered it with three distinct formulations on the same walk-forward origins:

| Formulation | Next-quarter Brier vs damped persistence | P(gain) |
|---|---|---|
| Lasso correction, inputs chosen inside each training window | +0.014 (worse) | 0.21 |
| Ridge correction | +0.019 (worse) | 0.03 |
| Upper bound with inputs chosen using the test quarters | −0.0004 | 0.42 |

The upper bound is the best that any feature selection, transformation or model could reach with these
indicators, and it is about zero. Re-running feature or model variants cannot change that, so they were not run, per
the directive's stop rule ("if a hypothesis is disproved, stop that path").

## Status by criterion

| # | Criterion | Status | Evidence |
|---|---|---|---|
| 1 | Forecast actual food insecurity, not price pressure | **verified** | SWS involuntary hunger (experience of going hungry), significantly above its five-year normal (docs/fi6/DECISION_RECORD.md) |
| 2 | Target and its uncertainty documented | **verified** | 98 labels reproduce independently. Label-flip probability is computed per quarter (mean 0.067). Sampling error explains 56 % of the change variance; a sample-size effect is probable (docs/fi8 §A–B) |
| 3 | Government data correctly sourced and release-aware | **verified** | Every value is used from its release date. The pre-2021 SWS rule is 27–68 days conservative. The World Bank price indicator was adopted by the locked rule; four other candidates were rejected with evidence (docs/fi7 §A) |
| 4 | FI6-N preserved and fairly evaluated | **verified** | Archive of 62,698 articles, nothing rescored. Gain at lead 1 under the quarter-end protocol (Bonferroni CI < 0); no gain under the operational protocol (docs/fi6/NEWS_RESULTS.md, docs/fi7 §B) |
| 5 | Exactly five domains, news inside them | **verified** | Code and tests (`test_five_domains_and_no_news_group`, FI6/FI7 feature maps) |
| 6 | Chronological validation, no leakage | **verified** | Expanding walk-forward; training only on published targets; training-only thresholds; permutation and planted-signal controls; frozen-reference reproduction |
| 7 | Model surpasses every required baseline | **failed** | LightGBM beats government-only, news-only and logistic regression (CIs below 0), but not naive or damped persistence. No tested correction beats persistence either (docs/fi8 §F) |
| 8 | Reliable probabilities and HIGH detection | **provisional** | Persistence (next quarter): accuracy 0.871, recall 0.55, precision 0.67, AUC 0.78, Brier 0.115. This does not survive removing the 4 rule-flagged survey-sawtooth quarters (recall 0.44) |
| 9 | Maximum reliable lead determined | **verified (the answer is "none, robustly")** | The same rules were applied at every lead. The next quarter is provisional, for persistence only |
| 10 | Next-quarter outlook for DA | **provisional** | 2027-Q1 HIGH, P = 0.74 (`/api/v1/fi7/forecast`), labelled provisional |
| 11 | 142 LGUs, vulnerability-adjusted (not measured hunger) | **verified** | All 142 LGUs, no missing poverty (Lucena from the PSA HUC table), sensitivity reported, scores independently reproduced |
| 12 | Backend serves the model; no retraining on page load | **verified for the FI7 API**; **not done for the dashboard** | `/api/v1/fi7/*` serves the stored artifacts. The approved dashboard still serves the P0H4 price-pressure index. Switching what DA sees needs the owner's approval |
| 13 | Tests pass, reproducible | **verified** | 1,405 backend tests pass; the FI5–FI8 suites pass; reproduction commands are in each report |

## External limitations (what would actually change criterion 7)

1. **SWS round-level design notes or Balance Luzon microdata.** These would confirm and correct the effect of
   rounds with ~600 respondents.
2. **An independent outcome series:** the PSA APIS hunger item by region and year (microdata on request), or
   DOST-FNRI FIES rounds.
3. **A CALABARZON-specific outcome** instead of Balance Luzon.
4. **New quarters.** The sealed forecasts (`backend/data/fi7/out/SEAL_fi7.csv`) are scored when SWS publishes
   2026-Q4 and later quarters.

## The one decision that belongs to the owner

* **Whether the dashboard should show the FI7 food-insecurity outlook** (provisional next quarter), instead of or
  next to the current P0H4 price-pressure index.
* **How it would be done:** an opt-in engine export in the dashboard's existing data format, so the frontend design
  is unchanged.
* **Until then:** the dashboard and the FI7 API are deliberately separate.
