# E61 protocol: candidate fixes for E58's low forecasts (frozen before any candidate is scored)

**Written:** 2026-10-19, branch `e60-accuracy-optimization` (working tree; nothing committed).
**Freeze:** the SHA-256 of this file (LF line endings) is written to `runner/PROTOCOL_SHA256.txt` before `c1_predict.py` runs. Candidate forecasts are written once to `sealed/` with a SHA-256 before `c2_score.py` reads any outcome.

## 0. Evidence status (read this first)

- The audit steps A1–A4 (`runner/a1`–`a4`) were run before this protocol. **They read the outcomes of all 50 rolling-origin rows** (targets 2024-Q2..2026-Q3), which E43–E60 had also examined.
- The candidates below were motivated by that diagnosis (A2: probability spread; A3: the 2024-Q4 misses; A1: projection bias). **Every E61 result is therefore development evidence.** No historical quarter is untouched.
- The only independent test is the frozen prospective record: E56/E58 2027-Q1 (sealed 2026-10-18) and later quarters.
- E61 does not change E56–E60 files, `backend/data/`, the served model or the production default (E38).

## 1. Target, horizon, rows (unchanged from E56/E57)

- **Target:** T43 (SWS Balance Luzon hunger > 11.3% AND provincial food-price pressure PS). A4 found no alternative target with an independently observed provincial outcome. No alternative target is used as a model target here (section 6).
- **Horizon and timing:** issue date O(t) = 00:00 on day 1 of quarter t+1; target t+2; inputs published before O(t) (`d.cut(t)`, E56 rules).
- **Rows:** the 50 E57 rows, origins 2023-Q4..2026-Q1 × 5 provinces.
- **Splits (E60's, adopted unchanged):** DEV = targets 2024-Q2..2025-Q3 (30 rows); TEST = 2025-Q4..2026-Q3 (20 rows, 1 HIGH). TEST is nearly uninformative about HIGH detection; this is stated with every TEST figure.

## 2. Candidates

All use the unchanged I7 regional hunger component. P(HIGH) = P_hunger × P_price. Warning form (E58-EW) = P_price ≥ 0.5.

| ID | Change to the price part P_price | Fitted on |
|---|---|---|
| **C0** | none: E56 (sealed E57 values) | — |
| **C1** | **online recalibration.** Logistic recalibration of logit P_price (E53 `fit_calibrator` "C2" form: slope prior N(1, 0.5²), intercept prior N(0, 1)), fitted on the earlier C0 forecasts whose PS outcome was published before O(t). Identity when fewer than 10 such rows or one class. | earlier issued forecasts only |
| **C2** | **debiased projection.** Before the bivariate-normal step, the projected food YoY and gap are shifted by their mean projection error on the fitting rows; the error scale becomes the SD (not RMSE) of those errors. Full E56 nested tuning (72 configurations). | training rows only |
| **C3** | **current-condition feature.** Adds `ps_margin_now` = max(F_now − food threshold, gap_now − gap threshold) (latest published months, distance to the PS condition) to both feature sets. Full E56 nested tuning. | training rows only |
| **C23** | C2 and C3 together. Full E56 nested tuning. | training rows only |
| **C4** | **government indicators without news:** E56 procedure with every news column removed (`news_*`, `news_n`). Full E56 nested tuning. | training rows only |

- **Verified-news candidate (gov + verified news):** not run. E60's classifier v2 was never frozen, and its news store was never scored. The only news available is the E40 keyword shares that E56 already uses. So **C0 vs C4 is the news test.**

**Baselines (identical rows):**
- B-PROJ: sealed E58 projection;
- persistence (latest known T43);
- majority (always LOW);
- climatology;
- always HIGH;
- **B-NOW:** the PS condition on the latest published months at O(t) (F_now > food threshold or gap_now > gap threshold), as a 0/1 forecast.

## 3. Metrics

**Per candidate, all 50 rows plus DEV and TEST separately:**
- accuracy, balanced accuracy, HIGH recall/precision, LOW recall;
- Brier and log loss of P(HIGH);
- calibration intercept and slope;
- ONSET recall (E58 events) for the warning form;
- per quarter and per province;
- counts.

**Paired Brier difference vs C0:**
- quarter-cluster bootstrap (4000 draws, seed 61), 95% CI;
- quarter-level sign test.

**75% accuracy:** reported as found, pooled and per quarter.

## 4. Selection rule (one rule, DEV only)

1. Among C1, C2, C3, C23 and C4, the **candidate** is the one with the lowest DEV Brier of P(HIGH).
2. It counts as an **improvement over C0** only if all of these hold:
   - (a) DEV Brier lower than C0's by ≥ 0.005;
   - (b) on all 50 rows, the paired Brier CI upper bound is < 0;
   - (c) on all 50 rows, balanced accuracy ≥ C0's − 0.02;
   - (d) warning-form ONSET recall ≥ C0's.
3. **Calibration claim:** C1 is reported as improving calibration only if its 50-row slope CI covers 1 while C0's does not, **and** its Brier is not worse.
4. **News claim:** news adds measurable value only if C0's Brier is lower than C4's with a paired CI upper bound < 0.
5. Whatever the outcome, no served model changes in E61. A passing candidate is **recommended** for prospective scoring from the next origin. Switching requires the user's authorization.

## 5. Not allowed

- Changing candidates, rows, splits, thresholds, priors or the rule after the freeze.
- Using any outcome published on or after O(t) in a forecast.
- Data before 2021 or after 2026-10-14.
- Editing E56–E60 artifacts or the sealed E57/E58 files.

## 6. Alternative targets

A4 compared T43 with six price-based definitions and four hunger-gated ones:
- PS, ABS4, GAP0, ACC1, RFP;
- H&ABS4, H&GAP0, H&ACC1, H&RFP.

**None has an independently observed provincial food-insecurity outcome.** SWS hunger is the only independent food-insecurity measure in the data, and it is regional:
- the price-only definitions do not track it, and ABS4 is negatively correlated with it;
- the hunger-gated ones track it only because they contain it.

**So no alternative passes the validity review as a forecasting target.** They are reported descriptively, and as dashboard evidence (absolute food inflation, headline inflation, price level). Choosing among them is an adviser decision.
