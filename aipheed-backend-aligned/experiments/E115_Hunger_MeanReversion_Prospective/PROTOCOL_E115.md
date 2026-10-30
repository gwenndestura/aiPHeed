# PROTOCOL_E115: prospective mean-reversion outlook for SWS hunger levels (frozen 2026-10-30, before any forecast is issued)

**Hash.** This file's SHA-256 goes in `runner/PROTOCOL_SHA256.txt`, and both are committed before the first forecast is sealed.

**What is unchanged.**
- **E114.** Its frozen protocol (c3e5624), its results on the untouched 2013-2020 period (de05c5d), its data and its code are reused read-only and never re-scored or reinterpreted.
- **Everything else.** The production dashboard, model outputs, API responses, map colours and approved design are not touched.

## 1. Question and scope

**Question.** Does mean reversion give a useful and reliable *prospective* outlook for the **level** of SWS Total Hunger at Lead 1 and Lead 2?

**Areas.**
- **Primary:** Balance Luzon (BL).
- **Separate:** NCR, Visayas and Mindanao.

**Out of scope (no claim made).**
- HIGH/LOW classification and event probabilities.
- Any contribution of the five aiPHeed trigger groups (E114 found none).
- Any provincial outcome. The forecast is a regional hunger level, not provincial food insecurity or vulnerability.

## 2. Methods (all parameters fixed here)

### Notation

| Symbol | Meaning |
|---|---|
| a | area |
| t | origin quarter |
| C | information cut-off (§3) |
| S_a(C) | quarterly means of the area-a readings whose SWS publication date is strictly before C |
| h | the newest reading in S_a(C) |
| μ | the mean of all readings in S_a(C), back to 1998-Q3 |
| k | lead: the target is quarter t+k |

### Forecasts

| Code | Role | Point forecast ŷ_k |
|---|---|---|
| **DAMP** | primary method, exactly as tested in E114 | μ + φ^k · (h − μ), φ = 0.5 |
| **DAMP-POST** | pre-declared variant | as DAMP, but μ is the mean of the readings from 2025-Q2 onward (the adult-respondent base) when at least 2 of them are in S_a(C). Otherwise μ as DAMP. Same φ. |
| RW (persistence) | comparator | h |
| MEAN (climatology) | comparator | μ |
| ULGBM | comparator | E114's unified LightGBM, refitted at the issue exactly as in `E114_Final_Run/runner/run_e114.py`: same features, grid, inner-fold selection and seed 114. Trained on rows whose target was published before C. |

### Why each method, and what each assumes

- **DAMP** assumes hunger is a stationary series around a long-run level. Departures from that level decay geometrically, with a decay of 0.5 per lead.
  - This is the forecast of an AR(1) model with mean μ and coefficient 0.5.
  - It is used here exactly as specified in E114. It beat persistence there on the untouched 2013-2020 period: Lead 2 MSE 27.0 vs 37.8.
  - No parameter is estimated from post-2020 data.
- **DAMP-POST** is declared now, before any outcome, for one reason: from 2025-Q2 SWS interviews adults instead of household heads.
  - Since then the area means are 20.0 (BL), 22.8 (NCR), 20.8 (VIS) and 22.3 (MIN), against all-history means of 14.2-16.5.
  - DAMP's anchor may therefore be biased low.
  - Neither variant is chosen later from results. Both are reported.

### Uncertainty intervals

- **Error spread.** σ_k is the root-mean-square of the method's own out-of-sample errors at lead k, pooled over the four areas.
  - The errors come from the E114 backtest procedure (origins from 1999-Q1).
  - Only targets published before C are used, with at least 8 of them.
- **Primary intervals:** 80% ŷ ± 1.2816 σ_k; 95% ŷ ± 1.9600 σ_k.
- **Secondary interval (empirical 80%):** [ŷ + q10, ŷ + q90] of the same errors.
- **Variant.** DAMP-POST uses DAMP's error history, because it has no separate history before the break.

## 3. Issue schedule and point-in-time rules

**Origin and cut-off.**
- Origin t has nominal issue date O(t) = day 1 of quarter t+1 (E114).
- A forecast for origin t is issued at the seal time T.
- Its information cut-off is **C = min(O(t), T)**.
- SWS readings count only if their recorded publication date is before C.

**Covariates (ULGBM only).**
- They follow the E114 availability rules.
- Quarter-t values (typhoon count, GDELT news) are set to NaN if quarter t has not ended before C.

**Which targets may be forecast.** A forecast may be sealed only for target quarters with **no SWS reading in the data file** at seal time.

**Sealing.**
- Each issue writes `out/forecasts/E115_<origin>_<UTC timestamp>.csv`, which is never overwritten.
- A manifest records the SHA-256, the seal time, the cut-off, the protocol hash and the newest reading used for each area.
- A ledger line is appended to `out/forecast_ledger.csv`.
- The files are committed to git at once, so the commit time is a second timestamp.

**What counts as prospective.** A sealed forecast counts only if every SWS round of its target quarter was published **after** the seal time. Otherwise it is flagged and excluded.

**At this freeze:**

| Origin | Cut-off | Lead 1 target | Lead 2 target |
|---|---|---|---|
| 2026-Q3 | O = 2026-10-01; newest reading 2026-Q2 | 2026-Q4 | 2027-Q1 |
| 2026-Q4 | the seal time, 2026-10-30; newest reading 2026-Q3 | 2027-Q1 | 2027-Q2 |

Later origins are issued with `runner/issue.py --origin <quarter>` before their targets are published.

## 4. Evaluation (computed by `runner/score.py` as outcomes are added to the data file by the owner)

**Measures.** For each method, lead and area (BL separately; NCR, VIS and MIN separately; and pooled, labelled as pooled):
- mean error (bias);
- MAE and RMSE;
- coverage and mean width of the 80% and 95% intervals;
- the number of scored target quarters.

**Comparisons.** DAMP against RW, MEAN, ULGBM and DAMP-POST, by MAE and RMSE difference.
- A Diebold-Mariano test (Newey-West, lag k, by target quarter, areas averaged) is computed only once at least 8 target quarters are scored at that lead.

**No early verdict.** Nothing is claimed until **at least 8 BL target quarters are scored at a lead** (about two years of SWS rounds).

**Reliability rule at that point, per lead and per method.** "Useful and reliable" requires all three:
1. BL RMSE below RW;
2. area-averaged squared error below RW, with DM p < 0.10;
3. pooled 80% coverage between 0.70 and 0.90.

Until then the status is **"accumulating"**.

**Not allowed.**
- Changing φ, μ, σ rules, intervals or the schedule after seeing an outcome.
- Choosing between DAMP and DAMP-POST from outcomes.
- Back-filling a forecast after its target is published.
- Presenting regional levels as provincial outcomes.
