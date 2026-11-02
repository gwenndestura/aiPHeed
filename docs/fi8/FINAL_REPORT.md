# aiPHeed FI8 — why no model beats persistence, and what would change that

This report supersedes the conclusions of the FI7 report. The FI7 numbers are unchanged and reproduce exactly.

* **What was reused:** FI7 is frozen at commit `6a8b114`; `backend/data/fi8/FI7_FROZEN_REFERENCE.json` holds the
  file hashes. All results use the FI7 operational protocol and the 62 evaluated next-quarter targets (2010-Q1 to
  2026-Q3, 11 HIGH and 51 LOW).
* **Lead convention:** the forecast is issued on the last day of the 2nd month of the dashboard's current quarter.
  "Next quarter" is the following quarter (FI7 h = 1; called "Lead 2" in FI5/FI6). Example: current quarter
  2026-Q4, issued 2026-11-30 (live: 2026-11-03), target 2027-Q1.

## One consistent conclusion

| Question | Answer |
|---|---|
| Does any model reliably forecast the next quarter? | **No, robustly.** Naive and damped persistence pass every pre-declared rule on all 62 targets, but fail when the 4 rule-flagged survey-sawtooth quarters are removed (recall 0.44 < 0.50). The next-quarter outlook is therefore **provisional**. |
| Furthest reliable lead | **None, robustly.** Provisionally the next quarter, for persistence-type forecasts only. |
| Does the proposed LightGBM beat every required baseline? | **No.** It beats PSA/government-only, NLP/news-only and logistic regression, with Brier differences −0.06 to −0.07 and CIs below 0. It does **not** beat naive persistence (Brier +0.008, CI −0.026 to +0.045) or damped persistence (+0.005, CI −0.014 to +0.026). The central acceptance objective is **not met**. |
| Can government or news information improve on persistence at all? | **Not with the available data.** Three correction models were tested. Even an upper bound that picked its inputs by looking at the test quarters gains only 0.0004 Brier (P = 0.42). |
| Served forecast (2027-Q1) | HIGH, P = 0.74, naive persistence, provisional. The latest reading (2026-Q3, 23.6 %) is above the significantly-above-normal line (20.2 %). |

## A. Root-cause diagnosis (in order of importance)

1. **The outcome is dominated by measurement noise.** *Confirmed.*
   * 56 % of the variance of quarter-to-quarter changes in SWS Balance Luzon hunger (17.1 of 30.5) is exactly what
     the published sampling errors produce.
   * Only about 13 of 31 variance points can be true change, and that is what any model would have to predict.
2. **There is an extra measurement effect beyond sampling error.** *Probable, not proven.*
   * Successive changes correlate at −0.56. Sampling error alone would give −0.28.
   * In the 2021–26 rounds with ~600 Balance Luzon respondents, hunger is 3.6 points higher than in the
     neighbouring rounds (permutation p = 0.05). The same pattern appears in the national figure (+2.7, p = 0.015)
     but not in the Visayas or Mindanao.
   * In 2025 the respondent base also changed, from household heads to adults.
   * SWS documents the varying sample sizes (300/600/1,080 in Balance Luzon) but states that its methodology is
     "standard and consistent over time"; no source documents a different survey vehicle. The cause therefore
     cannot be confirmed or corrected without SWS design notes or microdata.
3. **Too few independent outcome observations.**
   * 98 labelled quarters in total, 62 evaluated, 11 HIGH at the next quarter.
   * With 11 positives, a single quarter moves recall by 0.09.
   * The 95 % interval for persistence's recall is about 0.28–0.79.
4. **The indicators carry little forward information about changes.**
   * Across 23 government and news indicators, only news-reported displacement in CALABARZON correlates with
     persistence's errors (ρ = 0.48, p = 0.001).
   * It is non-zero in few quarters and exists only from 2012, so it cannot move enough HIGH/LOW calls to beat
     persistence.
5. **Model complexity is not the cause.** Simpler models (ridge, lasso on persistence errors) did not do better than
   LightGBM against persistence, and the label-permutation and planted-signal controls work. The data, not the
   learner, are the constraint.

## B. Target reliability

* **Labels:** all 98 labels reproduce independently from the published SWS values.
* **Uncertainty:** the target already accounts for sampling error (HIGH = above the five-year average by more than
  the round's published margin). Mean label-flip probability is 0.067 (FI5's definition: 0.142).
* **Flagged quarters:** a fixed rule flags runs of alternating changes larger than both rounds' margins. It flags
  2024-Q4, 2025-Q2, 2025-Q3 and 2025-Q4.
* **Release timing:** the pre-2021 release-date rule (fieldwork month end + 60 days) is 27–68 days *later* than the
  dated evidence in all 4 checked rounds, so it is conservative (no leakage).
* **Geography:** Balance Luzon is the SWS area containing CALABARZON. It also covers the rest of Luzon outside
  Metro Manila. The forecast is not a CALABARZON measurement, and province or LGU outputs are vulnerability-
  adjusted priorities, never measured hunger.
* **Independent outcomes:** DOST-FNRI FIES (≤ 3 provincial points), PSA APIS (regional, about annual, microdata on
  request) and SWS microdata are not obtainable in this work, and no quarterly series exists. Nothing was
  interpolated.
* **Verdict:** the target is valid as a measure of the experience of hunger. It is **not precise enough** at the
  quarter-to-quarter scale for any model to show gains over persistence on 62 test quarters.

## C. Government data (FI7 audit unchanged; see docs/fi7/FINAL_REPORT.md section A)

* **Retained:** food and rice CPI, palay, rainfall, storms, ONI, unemployment, remittances, poverty, and World Bank
  rice/urea prices.
* **Rejected with evidence:** typhoon intensity, underemployment, fisheries output, BSP monthly remittances
  (blocked), regional unemployment (annual 2021+ only), NDRRMC damage (PDF only), 4Ps counts (PDF only).
* **FI8 reassessment:** the walk-forward correction models selected world rice prices most often (59 of 62 windows)
  and unemployment second (55). Neither improved Brier, so the FI7 decisions stand. No indicator was retested with
  new transformations.

## D. News (FI6-N archive retained, nothing rescored)

* **What showed up:** the news-reported displacement signal (`na_displaced`) is the strongest single correlate of
  persistence errors.
* **Why it doesn't help in the walk-forward:** the lasso rarely selected it, because training windows before 2012
  have no news. Forcing it in (the upper-bound model) gave no gain.
* **Unchanged FI7 findings:** source concentration (95 % Rappler) and the body-mention geography limit remain.

## E. Methodology (final, simplest defensible)

1. Release-aware data, with each value used only from its publication date.
2. Issue on the last day of the current quarter's 2nd month.
3. Target: SWS Balance Luzon hunger significantly above its five-year normal.
4. Served forecast: the method that passes the reliability rules at a lead, with the lowest Brier score. At the next
   quarter that is naive persistence, whose probability is computed from the latest reading and the spread of past
   changes.
5. LightGBM's five-domain SHAP contributions are shown as context, labelled as the conditions the model weighed.
6. Walk-forward validation with all baselines, and a fixed-rule robustness check.

## F. Full comparison, next quarter (62 targets, 11 HIGH)

| Model | Acc. | Recall | Precision | AUC | Brier | Passes rules (all 62) |
|---|---|---|---|---|---|---|
| Naive persistence | 0.871 | 0.55 | 0.67 | 0.779 | 0.115 | yes (not robust) |
| Damped persistence | 0.823 | 0.55 | 0.50 | 0.774 | 0.118 | yes (not robust) |
| LightGBM (FI7) | 0.790 | 0.45 | 0.42 | 0.738 | 0.123 | no |
| Government + latest reading | 0.806 | 0.55 | 0.46 | 0.750 | 0.123 | no |
| C1 damped + lasso correction | 0.694 | 0.55 | 0.30 | 0.772 | 0.132 | no |
| C2 damped + ridge correction | 0.726 | 0.64 | 0.35 | 0.708 | 0.137 | no |
| U1 upper bound (not adoptable) | 0.742 | 0.73 | 0.38 | 0.793 | 0.117 | no |
| PSA/government-only | 0.758 | 0.09 | 0.17 | 0.517 | 0.186 | no |
| NLP/news-only | 0.742 | 0.18 | 0.22 | 0.486 | 0.180 | no |
| Logistic regression | 0.758 | 0.18 | 0.25 | 0.601 | 0.190 | no |
| Always LOW | 0.823 | 0 | — | 0.439 | 0.149 | no |

**Other leads:** no model passes at the current quarter or 2–3 quarters ahead (FI7 section D;
`data/fi8/study_results.json` has every lead).

**Statistics:** confidence intervals use a moving-block bootstrap (block 4 quarters) on paired per-quarter Brier
differences. Forecast windows at the next quarter do not overlap, but neighbouring quarters are correlated, which
the blocks account for.

## G. Lead-time decision

* **Robust maximum reliable lead:** none.
* **Next quarter:** provisional, for persistence-type forecasts only. Not for LightGBM.
* **Display:** 2027-Q1 as "provisional", the current quarter and later quarters as "indicative only".

## H. Reliability and generalisation

* **Leakage:** no leakage found.
  * Every value is used only from its release date.
  * Training uses only targets already published at the issue date.
  * Thresholds are fitted on training folds.
  * SWS-report news is removed.
  * Pre-2021 release rules are conservative.
* **Overfitting:** in-sample vs out-of-sample accuracy is 0.87 vs 0.79 for LightGBM. The correction models shrink
  to persistence when the predictors carry no signal (tested).
* **Weak spots:**
  * Recall by era rests on 4 / 1 / 6 HIGH quarters.
  * Results depend on 4 flagged survey quarters.
  * News is 95 % one source.

## I. Minimum additional evidence that could change the result

1. **SWS round-level design information or Balance Luzon microdata.** This would establish whether the ~600-
   respondent rounds differ systematically and allow a correction. It is the most direct fix for cause 2.
2. **A second, independent outcome series.** For example, the PSA APIS hunger item by region and year, or FNRI FIES
   rounds, to test whether the forecasts track food insecurity rather than one survey's noise.
3. **More quarters.** Each quarter adds one test observation. The sealed forecasts (`data/fi7/out/SEAL_fi7.csv`)
   are the first clean test, starting with 2026-Q4 when SWS publishes it.
4. **A CALABARZON-specific outcome** (from the same sources) to remove the Balance Luzon mismatch.

## Reproducibility

### Files

* **New:** `backend/app/fi8/__init__.py`, `backend/app/fi8/study.py`, `backend/tests/unit/test_fi8.py`.
* **Outputs:** `backend/data/fi8/FI7_FROZEN_REFERENCE.json`, `STUDY_LOCK.json`, `study_predictions.csv`,
  `study_results.json`.

### Commands (from `backend/`)

```bash
python -m app.fi8.study run
```

```bash
python -m pytest tests/unit/test_fi8.py tests/unit/test_fi7.py -q
```

### Tests

The FI7 and FI8 tests pass (8 tests). The FI7 full-suite run passed 1,405 tests; the 2 tests that failed only on
uncommitted work pass after commit.

### Not changed

The API, the served model and the dashboard. The approved dashboard still serves the P0H4 index. Switching it to the
FI7 provisional outlook needs the owner's approval.
