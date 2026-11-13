# FINAL (RATE + MIND): why it is unstable across survey rounds

Date: 2026-11-13. Every finding below uses **training rows or FINAL's own forecasts without outcomes**, unless it is marked "evaluation". Evidence files are in `evidence/` here and in `../aiPHeed_final_standalone_20261113/evidence/`.

## 1. Baseline: what FINAL is (verified in code, reproduced exactly)

| Element | Exact implementation |
|---|---|
| Code | `aiPHeed_hcw_final_optimization_20261112/scripts/engine_final.py` → `engine_opt.fit_predict` → `app.hcw.engine`. Project port: `app/hcw/final_engine.py` (version `final-rate-mind-1.0-experimental`, H_cw branch) |
| Call | `fit_predict(tr, te, AN, seed, rate="lin", miss="mind", cw="balanced")`; seeds 168, 1, 2, 3, 4; forecast = mean of the five probabilities |
| Target | y = logit(HFIAS moderate+severe prevalence); HIGH when y ≥ 0 (prevalence ≥ 50 %). Survey SE gives q = P(HIGH) |
| Candidate inputs | 77 inputs in 4 feature sets (GOV, FULL, GOV+cons, FULL+cons): market 15, climate 16, employment 10, poverty and social vulnerability 14, agriculture/fish 7, news aggregates 13, timing 2 (gap, lead). **No remittance input** |
| Anchors | All three are "national level of the latest released round + the province's shrunk deviation". **H:** hierarchical level. **OH:** level + reliability-weighted own history (`app/e160/arms.py`). **RSS:** level + Kalman state-space deviation whose variance grows with time (`app/e163/model.py`). One is chosen per fit by inner out-of-fold error: OH in every 2018 and 2019 fit, RSS in every 2021 fit |
| Inner validation | GroupKFold by region (≤ 5 folds) on training rows; full grid of 3 anchors × 4 feature sets × 16 settings |
| Feature selection | Top 25 inputs by absolute Spearman correlation with the residual, near-duplicates (ρ > 0.95) pruned; inside each fit |
| Monotone constraints | Sign per input from `Pv.SIGN` / `H.NEW_SIGN` |
| RATE | Target e = (y − anchor) ÷ (gap ÷ g₀), where g₀ = mean training gap. Weights × (gap ÷ g₀)². Prediction = anchor + (gap ÷ g₀) × predicted rate. **gap = target quarter − reference quarter of the province's own anchor survey** |
| MIND | Inputs missing in some training rows get a training-median fill plus a missing flag; other missing values get the training median |
| Class weights | Balanced (training HIGH share: 0.69 in the 2018 and 2019 folds, 0.52 in 2021) × survey precision weights |
| Probability | p = Φ(mu ÷ sd). sd comes from regressing squared inner residuals on gap, evaluated at the test gap (`A4.scale`). Raw, linear or Platt calibration chosen by inner Brier against q; **raw in every fit** |
| Class rule | HIGH when p ≥ 0.50. The engine's training threshold exists but is unused |
| Origin, target and lead | Target = the survey's reference quarter. Origin = target − lead. Survey rounds are usable 6 quarters after their reference quarter (`app/e150/model.py released`) |
| Reproduction | All 45 stored Lead 1–3 fits re-run identically (difference 0.0); the 110 all-lead fits of this study re-run Leads 1–3 again (see the lead report). 26 pipeline as-of, leakage and reproduction tests pass |
| Locked rules | PROTOCOL_SA (sha `15202d27`). FINAL at Lead 1: 6 of 7, failing Rule 7c (2021 HIGH recall 1 of 4) |

## 2. Survey-anchor gap versus forecast lead

- **Forecast lead:** origin → target quarter (1–8 here).
- **Survey-anchor gap:** the province's own survey → target quarter.

ENNS 2018, 2019 and 2021 surveyed **different provinces**, so every test province is anchored on its 2015 survey (2013 if not surveyed in 2015). Its gap is therefore fixed by the round: 12, 16 and 24 quarters, whatever the lead. In this design **gap and round cannot be separated**: each round has exactly one test gap.

## 3. Findings, by the questions asked

### (1) Is RATE's per-quarter assumption valid across gaps? No (training only)

Training rows available at the 2021 origin (`../aiPHeed_final_standalone_20261113/evidence/D1_rate_gap_training_only.json`):

| Training gap (quarters) | Per-quarter logit change |
|---|---|
| 8 | −0.011 |
| 12 | −0.035 |
| 16 | −0.016 |
| 20 | −0.019 |

The 16-quarter transition fell less than the 12-quarter one. Change follows period-specific national movements, not accumulated time.

The 2018 and 2019 folds have a **single** training gap (8), so how change scales with time cannot be estimated from their training data at all. Their test gaps (12, 16) are extrapolations.

### (2) Do the anchors carry a trend that RATE extrapolates again? Yes. This is the main cause.

- **The anchors are refreshed to the latest released round**, even when that round did not survey the province (code: `last_n` = national level of the last released round).
- **When the gap and the time since the latest round coincide, nothing is counted twice** (`evidence/D4_gap_vs_staleness_by_fold_lead.csv`). That holds in every training row of every fold-lead, and in the 2018 and 2019 test rows.
- **They differ only in the ENNS 2021 test rows at Leads 1–6.** The gap is 24 quarters, but the anchor's information is only 8 quarters old (Leads 1–2) or 12 (Leads 3–6), because the 2018 and 2019 rounds had been released. **This condition never occurs in training.**
- **RATE multiplies by 24 ÷ g₀ on top of an anchor already moved to the 2019 national level.**
  - Anchors alone: about −12 points for provinces starting at 60 % or more.
  - RATE: about −12 more.
  - Total: −23.6 points, against −9.4 for such provinces in training, where 77 % stayed HIGH (`D3_anchor_vs_rate_outcome_free.json`).

### (3) Are long-gap forecasts biased or overconfident? Biased downward and over-confident (outcome-free)

`evidence/D5_spread_shift_balance_outcome_free.json`:

| | 2018 | 2019 | 2021 |
|---|---|---|---|
| Forecasts beyond 0.2 / 0.8 | 38 % | 38 % | **76 %** |
| Median implied spread (logit) | 0.46 | 0.53 | 0.45 |

The spread does not grow at the 24-quarter gap. The spread regression is fitted on training gaps up to 20 and does not widen enough, while the mean has moved about twice as far. The result is confident LOW calls.

Evaluation (descriptive only): FINAL's confident wrong calls at Lead 1 include Masbate 0.15 and Occidental Mindoro 0.21.

### (4) Does training represent the forecast conditions? Not in 2021 (outcome-free)

- **Gap:** test 24 against training at most 20 (2018: 12 against 8; 2019: 16 against 8).
- **Anchor freshness:** the gap ≠ freshness condition never occurs in training.
- **Employment inputs in 2021:** unemployment rate, year-on-year change and change since the anchor sit **5.6–7.9 SD** from their training means (the 2020–21 COVID spike).
- **2018 and 2019:** national news indices lie far outside their training range (|SMD| up to 70), so national news inputs are not comparable across periods.
- **Anchor levels:** 2021 test anchors run down to 16.5 % against a training minimum of 25.5 %. This is irrelevant to the HIGH misses.

### (5) Where does the instability come from?

| Source | Evidence | Role |
|---|---|---|
| Anchor + RATE interaction (double counting at stale gaps) | D3, D4 | **Primary.** Only in 2021; explains the size of the projected fall |
| Gap extrapolation beyond training | D1, D4 | Contributes in every fold; unidentifiable in 2018 and 2019 |
| Spread not widening with gap | D5 | Turns a biased mean into confident LOW calls |
| Input distributions (employment, COVID) | D5 | Out of support in 2021. Employment barely affects the forecasts (see the trigger audit), so it is not the driver |
| Missingness | `R1_missingness_L1.csv`: test 7.4 % against training 9.3 %; no input missing in test but never in training | Not a cause |
| Class imbalance | Training HIGH share 0.52 in 2021 against 0.69 earlier. Balanced weights make LOW rows count more in 2018 and 2019 (12 November evidence) | Secondary; not specific to 2021 |
| Information | The cause of Masbate's and Occidental Mindoro's persistence is not observed by any input (12–13 November reports) | Limits any fix |

### (6) Do probabilities stay reliable as the gap grows?

Not as built. At gap 24 the mean shifts while the spread does not, so calibration degrades exactly where the gap exceeds the anchor's freshness.

Evaluation (descriptive only): the 2021 round has FINAL's lowest HIGH recall but a low Brier (0.09), because 21 of its 25 rows are LOW.

### (7) Why FINAL-SA fixed stability but broke calibration

- **FINAL-SA caps the RATE multiplier at the longest *training* gap:** 8 in the 2018 and 2019 folds, 20 in 2021.
- **That cuts the change applied to *every* test row in 2018 and 2019** (12 and 16 quarters treated as 8). In those folds the gap was not stale, so FINAL's linear projection was internally consistent there.
- **The probabilities rose across the board:** mean probability minus HIGH rate +0.097, slope 1.52, Cox p 0.036.
- **The inner calibration never saw capped rows,** because training rows are always within the training gaps.
- **FINAL-SA corrected the wrong quantity:** it shortened the time span everywhere instead of removing the double count where it occurs.

### What can be justified without the 72 outcomes

- **Using the anchor's information age as RATE's elapsed time** is justified by the anchor's construction. In training it equals the current gap, so training, selection and calibration are untouched. Only the 2021 test rows at Leads 1–6 change. This is FINAL-ET (`FINAL_IMPROVEMENT_PROTOCOL.md`).
- **Not justifiable now:**
  - capping or damping chosen to suit the 2018 and 2019 extrapolations (unidentifiable from training);
  - recalibration for capped rows (no training rows exist);
  - threshold, weight or feature changes chosen against these rows;
  - displacement or other inputs identified from test provinces.
