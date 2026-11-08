# PROTOCOL_LEAD2_FINAL_SIGNAL (frozen 2026-10-29, before any new fit)

**Branch.** `aiPHeed/lead2-rootcause-research`, continuing from c5906a9.
**Directory.** `experiments/LEAD2_FINAL_SIGNAL/`. Nothing earlier is overwritten.
**Hash.** The SHA-256 of this file goes in `runner/PROTOCOL_SHA256.txt`. Both are committed before `runner/final_signal.py` runs.

**Unchanged:**
- the served P0H4 model (a498b5ef) and the dashboard;
- the target T43c and its labels;
- the 65 Lead-2 evaluation rows;
- R1-R7 and `final.adoption_rule`;
- the sealed forecasts (dd293e2e, 07c99e56, b1edb799).

## 0. Data split (fixed)

**Development (DEV).**
- Rows whose target quarter is ≤ 2024-Q4 (`fr_lib.DEV_LAST`): 35 Lead-2 rows in 7 quarters, and the matching Lead-1 rows.
- Each origin is one chronological fold. The model is refitted at each origin on rows whose outcomes were known before it.
- Selection uses DEV only.

**Confirmation (CONF).** Targets 2025-Q2 to 2026-Q3. CONF is reported, never used to select.

**The 65-row Lead-2 set (DEV + CONF).**
- It has been inspected repeatedly. Its R1-R7 / adoption result is a **post-selection audit**, not independent confirmation.
- No candidate is chosen, changed or added because of it.

**Timing.** Every feature uses the base cut-off: CPI through month 2 of quarter t at O(t). That cut-off is archive-verified for 35 of 36 releases. The unverified CPI refresh is not used by any new candidate.

**Uncertainty.** Quarter-block bootstrap (4000 draws, seed 2031). The number of independent HIGH quarters is reported with every result.

## 1. Price predictability study (no candidate)

**Data.** The quarterly price margins of the official label: mf = F − TH_F and mg = F − HL − TH_G. Price HIGH iff mf > 0 or mg > 0.

**Questions answered by calculation.**
1. Share of the price-part error due to the series versus LightGBM (method comparison below).
2. Crossing rate: how often the price condition of the target quarter differs from the last condition known at issue (quarter t−1), at Leads 1 and 2.
3. Where crossings concentrate:
   - near the threshold: |realised max margin| < 1 pp;
   - by year (regime);
   - by province.
4. Patterns:
   - autocorrelation of mf at the issue-to-target distance;
   - quarter-of-year means (seasonality);
   - year means (structural breaks).
5. Attainable improvement with issue-time information: the best issue-time method below.
6. Continuous-then-classify vs direct binary.
7. Threshold-adjacent vs clearly separated rows, reported separately.

**Methods (forecasts of the target-quarter margins at Lead k, origin t; information known at O(t) only).**

| Method | Forecast |
|---|---|
| M0 projection | the existing A1_food / A1_gap |
| M1 last observation | mf, mg of quarter t−1 |
| M2 last condition | the price label of t−1 (binary) |
| M3 seasonal naive | the margins of quarter t+k−4 (known only if t+k−4 ≤ t−1) |
| M4 damped trend | M1 + 0.5·(k+1)·(m_{t−1} − m_{t−2}) |
| M5 ridge | lead-specific ridge (α = 10, standardized within the fold). Inputs: A1_food, A1_gap, mf/mg of t−1 and t−2, A_mom, W_rice_yoy, W_cereal_yoy, W_crude_yoy. Fitted at each origin on rows of that lead with outcomes known before O(t). |
| M6 LightGBM | the B0 price part (existing predictions) |
| Climatology | the price-HIGH share in outcomes known at O(t) |

**Probability for the continuous methods (M0, M1, M3, M4, M5).**
- P(price HIGH) = 1 − Φ₂(−m̂f/σf, −m̂g/σg; ρ).
- σ and ρ come from **that method's own earlier out-of-sample errors whose outcomes were known at O(t)**, with at least 6.
- The evaluation period's error distribution is never used.

**Reported.**
- **Price label:** margin RMSE, Brier, accuracy, balanced accuracy and recall.
- **Converted to the unchanged T43c through π_H:** Brier, accuracy, balanced accuracy, precision, recall, F1, false alarms and missed HIGH.
- **Splits:** Lead 1 / 2, DEV / CONF, by year, by province, and near-threshold vs separated.

## 2. Indicator availability audit (all 12)

For each indicator:
- source and definition;
- whether it varies by province, by quarter, or both;
- missingness by year;
- availability lag (verified / assumed);
- observed / derived / carried-forward / imputed;
- information beyond the others: the refitted ablation already measured;
- generalization: the sign of the ablation difference by development year.

**Specific checks.**
- **News (N1).** Is it NaN exactly when admitted headlines < 5 (the definition), and how is coverage spread by year?
- **Poverty (V1).** Which figures were published before each origin. A province-constant column enters LightGBM only through the province ordering, so the impact of the timing violation is bounded by the poverty ablation.
- **Employment / remittances.** Whether they vary by province.
- **Climate.** Signal by season and lead from the ablation.

## 3. Point-in-time sensitivities (on B0; and on a selected candidate, if any)

**S-EARLY.**
- The 600 training rows issued before 2023-01-06 are removed from training. Their thresholds were not computable at issue, and the 375 pre-2018=100 rows are a subset of them.
- Training restarts with the remaining rows, under the same eligibility rule.

**S-LAG.**
- A3, C3, C4, E1 and E2 are shifted one more quarter (the value of origin t−1 is used at t). This tests their assumed lag.

**S-V1.** Bounded by the poverty ablation. No refit.

Each is reported on DEV and CONF.

## 4. Candidates (unified LightGBM, U2 columns and recipe unchanged; fitted only if their gate passes)

| Candidate | Hypothesis | Change | Gate (DEV, computed in step 1 before fitting) | Abandon if |
|---|---|---|---|---|
| **K-A** (A/C: magnitude of recent price dynamics) | Binary lagged labels (C2) discard magnitude. Recent realised margins and the seasonal analogue carry level and persistence information that the flat projection lacks. | B0 + LM_f, LM_g (margins of t−1) and SM_f, SM_g (margins of t+k−4, NaN if not yet known) | M1 or M3 has a lower Lead-2 DEV price Brier than M0 | gate fails |
| **K-B** (B: continuous forecast then classify) | A regularized continuous forecast of the target margins, made point-in-time at each row's own origin, summarizes the price information better than the raw inputs. | B0 + RF_f, RF_g = the M5 ridge forecasts for the row's target, from the ridge fitted at that row's origin | M5 has a lower Lead-2 DEV price Brier than both M0 and M6 | gate fails |
| **K-E** (E: availability-aware news) | N1 missingness is informative if it is not driven by the collection calendar. | B0 + N1_articles (count of admitted headlines at issue) | N1 DEV-period coverage ≥ 30% **and** missingness not concentrated before a collection start | either fails (expected: coverage is 0-35% by year, so it is abandoned without a fit) |
| **D** (simpler model, comparator only) | — | M5 above. It is not a thesis candidate and does not replace LightGBM. | — | — |

## 5. Selection rule (DEV only; all conditions)

1. Lead-2 DEV T43c Brier ≤ B0 − 0.005.
2. Lead-2 DEV balanced accuracy ≥ B0's.
3. Lead-1 DEV Brier ≤ B0 + 0.005.
4. Lead-2 DEV price-part Brier < B0's.
5. Per-quarter Lead-2 DEV Brier is better than B0 in ≥ 4 of the 7 DEV quarters.
6. Lead-2 DEV Brier is below both persistence and climatology.
7. Every point-in-time test passes, and the candidate uses only base-cut-off features.

If several candidates qualify, the one with the lowest Lead-2 DEV Brier is selected. If none qualifies, B0 is the reference.

## 6. Post-selection audit (once)

- **Applies to:** the selected candidate only.
- **What is reported:** R1-R7 and `final.adoption_rule` vs B0 on the 65 rows, including:
  - confusion matrix and predicted HIGH rate;
  - calibration;
  - quarter-cluster CIs and the R6 pass rate;
  - by province and by quarter.
- **Labelled:** post-selection audit.
- **If it fails:** the failure is reported, and nothing else is tried on these rows.

## 7. Trigger contributions

- **Model:** the selected candidate, or B0 if none qualifies.
- **Method:** each of the five groups is removed and the model is refitted at every origin.
- **Measures:**
  - ΔBrier on DEV and CONF, Leads 1-2;
  - quarter-block 90% CI;
  - one-sided p, with Holm correction across the 5 groups;
  - Δ recall and Δ false alarms.
- **Reading:**
  - positive = adds value under this design;
  - near zero = not established;
  - negative = possible noise.

## 8. Decision (exactly one)

- **A. Defensible improvement found.** Requires all of §5, every leakage test passing, R1-R7 at Leads 1-2, and the adoption rule.
- **B. Improvement not established.**
- **C. Inconclusive.** For example, a candidate passes §5 but its post-selection audit shows the R6 pass rate under cluster resampling below 0.8.

Lead 2 is not called reliable without new prospective outcomes.
