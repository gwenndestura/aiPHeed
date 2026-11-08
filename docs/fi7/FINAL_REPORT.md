# aiPHeed FI7 — final report: government data, news, methodology and lead-time review

* **What was locked:** every number below comes from files in `backend/data/fi7/out/`. The 12 first-round
  experiments were locked by code hash before they ran (`EXPERIMENT_LOCK.json`).
* **What is post-hoc:** 4 experiments (F1, E12, F2, E13) were registered *after* reading round 1. They are labelled
  post-hoc in the registry and were judged by the same rule.
* **What the evidence is:** all SWS quarters had been used by earlier aiPHeed work, so this is development
  evidence. The sealed forecasts (`SEAL_fi7.csv`) are the only clean test.

## Summary

1. **The biggest gain came from timing, not from a model.**
   * The FI5/FI6 protocol issued on the last day of a quarter, before that quarter's SWS reading and a month of
     CPI were published.
   * FI7 issues on the last day of the current quarter's 2nd month (release-aware), when DA would actually use the
     outlook.
   * For the same next-quarter targets, Brier fell from 0.161 to 0.129 (−0.032, 95 % CI −0.061 to +0.003,
     P(gain) = 0.96) and AUC rose from 0.47 to 0.68.
2. **Government data:** of four new official or institutional indicators, only **world rice and urea prices**
   (World Bank Pink Sheet) passed the adoption rule (next-quarter ΔBrier −0.006, P = 0.92). Typhoon intensity,
   underemployment and fisheries output added nothing measurable.
3. **News:** the FI6-N archive is kept. Using the 90 days before issue instead of the last complete quarter, and
   escalation/persistence features, added nothing.
4. **Model:**
   * The proposed LightGBM (FI7) beats PSA-only, NLP-only and logistic regression significantly at the next
     quarter (ΔBrier −0.06 to −0.07, CIs below 0).
   * It does **not** beat naive persistence or damped persistence. A training-only decision threshold raised its
     next-quarter balanced accuracy from 0.58 to 0.66.
   * The best probabilities came from the simplest models: naive persistence (Brier 0.115) and damped persistence
     (0.118).
5. **Lead time:**
   * On the full test set, naive persistence and damped persistence **pass every pre-declared rule at the next
     quarter**: accuracy 0.871 / 0.823, recall 0.55 / 0.55, precision 0.67 / 0.50, AUC 0.78 / 0.77. LightGBM misses
     precision and recall narrowly. No model passes 2 or 3 quarters ahead, or the current-quarter nowcast.
   * **The next-quarter pass is not robust.** The SWS Balance Luzon series has a survey sawtooth: successive changes
     correlate at −0.56, and −0.80 since 2021. In 2025–26 it coincides with alternating rounds of ~600 and ~300
     Balance Luzon respondents. Removing the 4 rule-flagged sawtooth quarters drops next-quarter recall to 0.44 for
     every persistence-type model, below the 0.50 rule.
   * **The robust maximum reliable lead is therefore none.** The next-quarter outlook is served as **provisional**.
6. **Operational outlook issued 2026-11-03** (current quarter 2026-Q4): **2027-Q1 = HIGH**, P = 0.74, provisional,
   naive persistence. The latest reading, 23.6 % (2026-Q3), is above the significantly-above-normal line of 20.2 %.
   The other quarters are indicative only.

## A. Government-data audit

### Retained

| Indicator | Source | Period | Freq. | Level | Release rule | Missingness / issues | Change in FI7 | Why retained |
|---|---|---|---|---|---|---|---|---|
| Food CPI YoY, rice CPI YoY | PSA OpenSTAT CPI | 1995–2026-09 | monthly | Region IV-A | +10 d | 2018 rebase linked to 2012 base | none | access / affordability |
| Palay production YoY | PSA crops statistics | 1988–2026-Q3 | quarterly | Region IV-A | +45 d | revisions not tracked | none | availability |
| Rainfall z (3 m) | NASA POWER | 1982–2026-09 | monthly | 5 province centroids | +30 d | point data, not station | none | climate shock (sign free) |
| Storms within 200 km (quarter) | NOAA IBTrACS | 1884–2026-10 | event | CALABARZON | real time | best track revised | quarter-so-far at the operational issue date | typhoon exposure |
| ONI | NOAA CPC | 1950–2026-09 | monthly | Niño 3.4 | +10 d | — | none | El Niño drought risk |
| Unemployment rate, YoY | PSA LFS | 2005-04–2026-08 | quarterly→monthly | Philippines | +45 d | no regional series before 2021 | none | income loss |
| Remittances YoY | BSP via World Bank WDI | 1991–2025 | annual | Philippines | 15 Feb | BSP monthly blocked (HTTP 403) | none | household income support |
| Poverty incidence | PSA | 2006–2025 | triennial | Region IV-A | Y+2 / documented | methodology break 2015→2018 | none | vulnerability (constrained to raise risk) |
| **World rice (Thai 5 %) price YoY and 3-month change; urea YoY** | **World Bank Commodity Price Data** | 1961–2026-09 | monthly | world | +10 d | institutional, not PH government | **added** (passed the adoption rule) | the Philippines imports rice; world prices lead domestic food prices |

### Investigated and rejected

| Indicator | Source | Result |
|---|---|---|
| Typhoon intensity (max wind, typhoon-strength passages) | IBTrACS | next-quarter ΔBrier −0.0005, P(gain) = 0.55 |
| Underemployment rate and YoY | PSA LFS 0081B3FKEI8 | next-quarter ΔBrier +0.0015, P(gain) = 0.15 |
| Fisheries production YoY | PSA 2E4GVFP1, Region IV-A | next-quarter ΔBrier +0.0016 |
| BSP monthly cash remittances | bsp.gov.ph | HTTP 403 to automated access |
| Regional unemployment (IV-A) | PSA SDG table | annual, 2021+ only |
| NDRRMC agricultural damage | situation-report PDFs | no consistent machine-readable series |
| DSWD 4Ps counts | PDF reports | irregular, PDF only |
| Regional quarterly GRDP | PSA | not published quarterly for regions |

Release dates are conservative rules where exact historical publication dates are unknown (see
`app/fi5/sources.py` and `app/fi7/extra_sources.py`). No missing value is treated as zero unless zero is its
meaning (for example, no storm). LightGBM handles missing values natively. The ridge model imputes medians fitted on
training rows only.

## B. News/NLP

* **What is unchanged:** the FI6-N archive (62,698 articles, 2008–2026, four sources), its XLM-R labels, event
  deduplication and restated-statistic removal. Nothing was rescored. The human annotation kit was not used.
* **What was tested:**
  * E06: the timely 90-day window (ΔBrier +0.0012 next quarter).
  * E07: escalation and persistence features (+0.0001).
  * Both rejected.
* **Contribution by lead:** FI6-N news improved lead-1 probability quality under the quarter-end protocol (FI6-N
  report). Under the operational protocol, the reference configuration with FI6-N news (E01) and the
  government + latest reading model without news differ by ≤ 0.0001 Brier at the next quarter. The CI includes 0.
* **Why news no longer adds anything:** once the issue date sits after the SWS release, the fresh survey reading
  carries the information that news had partly supplied.

## C. Methodology (in order)

1. **Acquire:** official and institutional series (PSA, NOAA/NASA, BSP/WB, World Bank Pink Sheet) and the FI6-N
   publisher news archive.
2. **Validate:** each value is checked against its source table and release rule. Wherever a release date is
   unverified, a conservative availability rule applies.
3. **Align:** every series is turned into (reference period, value, available-from date).
4. **Issue date:** the last day of the 2nd month of the current quarter. Only values available by then are used.
5. **Government features:** year-on-year and 3-month changes, anomalies against earlier years only.
6. **News features:** domain risk-event shares normalised by collected volume, z-scored against earlier quarters
   only.
7. **Five domains:** market (CPI, palay, world prices, market news), climate, employment, OFW remittances, and
   poverty/vulnerability. News sits inside its domain.
8. **Models:**
   * LightGBM change model with monotone constraints, and a decision threshold chosen on training folds only.
   * Damped persistence and naive persistence as statistical competitors.
9. **Walk-forward validation:** at each origin, train on targets published by the issue date. Test targets run
   2010-Q1 to 2026-Q3 (62 quarters, 11 HIGH).
10. **Baselines:** all required baselines on identical origins.
11. **Lead selection:** the same rules at every lead, plus a sawtooth robustness check.
12. **Forecast:** the served probability is the reliable model with the lowest Brier, labelled provisional when not
    robust.
13. **LGU priority:** 142 LGUs = next-quarter probability × (½ poverty rank + ½ density rank).
14. **API:** read-only routes at `/api/v1/fi7/*`. Not yet the dashboard's served engine (see G).

## D. Performance (operational protocol; 62 targets, 11 HIGH, 51 LOW at every lead)

| h | Model | Acc. | Bal. acc. | Prec. | Rec. | F1 | AUC | Brier | Reliable (full set) |
|---|---|---|---|---|---|---|---|---|---|
| 1 (next quarter) | **LightGBM (proposed)** | 0.790 | 0.659 | 0.417 | 0.455 | 0.435 | 0.738 | 0.123 | no (precision, recall) |
| 1 | Naive persistence | 0.871 | 0.743 | 0.667 | 0.545 | 0.600 | 0.779 | 0.115 | yes |
| 1 | Damped persistence | 0.823 | 0.714 | 0.500 | 0.545 | 0.522 | 0.774 | 0.118 | yes |
| 1 | Government + latest reading | 0.806 | 0.704 | 0.462 | 0.545 | 0.500 | 0.750 | 0.123 | no (precision) |
| 1 | PSA/government-only | 0.758 | 0.496 | 0.167 | 0.091 | 0.118 | 0.517 | 0.186 | no |
| 1 | NLP/news-only | 0.742 | 0.522 | 0.222 | 0.182 | 0.200 | 0.486 | 0.180 | no |
| 1 | Logistic regression | 0.758 | 0.532 | 0.250 | 0.182 | 0.211 | 0.601 | 0.190 | no |
| 1 | Always LOW | 0.823 | 0.500 | — | 0 | 0 | — | 0.149 | no |
| 0 (current quarter) | LightGBM / damped / naive | 0.742 / 0.758 / 0.726 | 0.59 / 0.68 / 0.51 | 0.31 / 0.38 / 0.20 | 0.36 / 0.55 / 0.18 | | 0.56 / 0.63 / 0.65 | 0.162 / 0.146 / 0.187 | no |
| 2 | LightGBM / damped / naive | 0.661 / 0.790 / 0.710 | 0.55 / 0.62 / 0.47 | 0.22 / 0.40 / 0.11 | 0.36 / 0.36 / 0.09 | | 0.47 / 0.50 / 0.58 | 0.163 / 0.151 / 0.200 | no |
| 3 | LightGBM / damped / naive | 0.790 / 0.742 / 0.790 | 0.59 / 0.59 / 0.62 | 0.38 / 0.31 / 0.40 | 0.27 / 0.36 / 0.36 | | 0.49 / 0.67 / 0.65 | 0.157 / 0.138 / 0.163 | no |

LightGBM minus each model, next quarter (Brier, 95 % moving-block CI):

| Compared with | Difference | 95 % CI |
|---|---|---|
| Damped persistence | +0.005 | −0.014 to +0.026 |
| Naive persistence | +0.008 | −0.026 to +0.045 |
| Government + latest reading | +0.000 | |
| PSA-only | −0.063 | −0.095 to −0.018 |
| NLP-only | −0.057 | −0.107 to −0.015 |
| Logistic regression | −0.068 | −0.113 to −0.028 |

LightGBM is clearly better than the indicator-only baselines and logistic regression. It is not better than
persistence.

**Calibration** (next quarter, LightGBM):

| Predicted (mean) | Observed | Quarters |
|---|---|---|
| 0.08 | 0.13 | 48 |
| 0.32 | 0.27 | 11 |
| 0.65 | 0.67 | 3 |

**Overfitting:** in-sample accuracy is 0.87 against 0.79 out of sample. Accuracy by era is 0.75 / 0.89 / 0.75.

## E. Lead-time decision

* **Lead map:**
  * h = 1 is the quarter after the dashboard's current quarter. That is the DA next-quarter outlook, issued about a
    month before that quarter starts.
  * Under FI5/FI6 the same target was "Lead 2", issued at the end of the previous quarter.
* **Rules:** the same rules apply at every lead: accuracy ≥ 0.75, recall and precision ≥ 0.50, AUC ≥ 0.70, Brier
  better than climatology, and accuracy ≥ 0.60 in every era.
* **Full-test-set result:** reliable at h = 1 for naive and damped persistence; reliable nowhere else.
* **Robustness:**
  * The rule-based sawtooth check removes 4 quarters: 2024-Q4, 2025-Q2, 2025-Q3, 2025-Q4.
  * On the remaining 58 targets (9 HIGH), every model's next-quarter recall is 0.44.
  * So no lead is robustly reliable.
* **Is Lead 2 (the next quarter) reliable?** Provisionally, for persistence-type forecasts, not for LightGBM. Does
  LightGBM add value over the baselines there? Over indicator-only and logistic baselines, yes; over persistence,
  no.
* **Why longer leads fail:** with the newest reading two or more quarters old, every method falls below the recall
  and AUC rules. The government and news indicators do not anticipate the timing of hunger surges.
* **Dashboard display:** show **h = 1 (next quarter) as the operational outlook, labelled provisional**. Show the
  other quarters as indicative only.

## F. Reliability assessment

* **Leakage:**
  * Release-aware rules apply to every series.
  * Training uses only targets published by the issue date.
  * News z-scores use earlier quarters only.
  * SWS-survey news reports are removed (FI6-N).
  * Thresholds are chosen on training folds only.
  * E00 reproduces FI6-N exactly, confirming the harness is consistent.
* **Overfitting:** the in/out gap is 0.07–0.08 (FI5 had 0.38). The models are small (stumps or 4 leaves) with
  monotone constraints.
* **Bias:** HIGH is 18 % of quarters. Never-HIGH baselines are reported; the always-LOW reference scores 0.823
  accuracy. News is 95 % from one source.
* **Generalisation:** eras 2010–15, 2016–20 and 2021–26 each have only 4, 1 and 6 HIGH quarters, so recall by era
  is very uncertain.
* **Target uncertainty:**
  * Confidence-weighted accuracy (weights = 1 − label-flip probability) is 0.795 for LightGBM and 0.876 for
    persistence.
  * The sawtooth is the main threat to target validity: an apparent survey-vehicle effect in 2025–26.
* **Data needed to resolve it:**
  * SWS documentation of the survey vehicles and sample designs by round, or Balance Luzon microdata, to adjust
    for vehicle effects.
  * PSA APIS or FNRI FIES series to add independent outcome observations.

## G. Implementation and reproducibility

### Changed files

* **New package** `backend/app/fi7/`:
  * `__init__.py`, `paths.py`
  * `extra_sources.py`, `news_windows.py`, `design.py`
  * `models.py`, `experiments.py`, `serve.py`
* **New API:** `backend/app/api/v1/fi7.py`.
* **New tests:** `backend/tests/unit/test_fi7.py`.
* **Modified:**
  * `backend/app/api/router.py`: mounts `/api/v1/fi7`.
  * `backend/app/fi5/features.py`: optional `issue_date`; default unchanged, FI5/FI6 tests pass.
  * `backend/app/fi5/sources.py`: IBTrACS extract keeps the wind columns; same rows.
  * `backend/app/fi6/models.py`: hook for extra monotone signs.

### New data

* World Bank Pink Sheet extract (`data/fi5/raw/wb`).
* PSA underemployment and labour-force levels (`data/fi5/raw/psa`).
* `data/fi7/news_windows.csv`.
* Outputs in `data/fi7/out`: registry, details, predictions, final evaluation, sensitivity, forecast, seal,
  rankings.

### Commands (from `backend/`)

Experiment round 1, then the post-hoc round:

```bash
python -m app.fi7.experiments run
```

```bash
python -m app.fi7.experiments run --round posthoc
```

Final evaluation and the robustness check:

```bash
python -m app.fi7.experiments final
```

```bash
python -m app.fi7.experiments sensitivity
```

Live forecast as of a date:

```bash
python -m app.fi7.serve issue --as-of 2026-11-03
```

Tests:

```bash
python -m pytest tests/unit/test_fi7.py -q
```

### Tests

FI5–FI7 tests: 56 passed. The full-suite result is reported in the session summary.

### Dashboard

* **Current state:** the approved dashboard serves the P0H4 price-pressure index from
  `backend/data/ch1_engine/rows.csv`. `AIPHEED_CH1_ENGINE` can switch it to other exports in the same schema.
* **What FI7 has instead:** its own read-only API.
* **Not done:** exporting FI7 into the dashboard schema as an `fi7` engine and making it the served model. That
  changes what DA sees, so it needs the owner's approval, and the frontend design must not change. Until then, the
  dashboard and FI7 are separate on purpose.
