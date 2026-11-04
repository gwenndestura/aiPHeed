# C-E6 pre-registration: C-E2 + national rice stock inventory (food availability) (fixed before any fit, 2026-11-04)

**Development evidence;** the 22nd historical attempt, on the same 62 previously examined quarters. C-b stays the main
model, and C-E2 the demo model, unless C-E6 passes the adoption rule and the team and adviser approve.

## Research problem

C-E2's inputs measure hunger persistence, prices (affordability), climate, production, national employment and
remittances. **No input measures food availability (supply on hand).**
- LOW-quarter recall is 0.47.
- 2015–2020 accuracy is 0.524.
- 9 of 14 Lead-1 errors are near the line (`FINAL_2026-11-04/FORECASTING_FAILURE_ANALYSIS.md`).

## Why this is new information (prompt §3–4)

- **Source:** PSA OpenSTAT 2E/CS/0032E4ECNV0, "Rice and Corn: Monthly Total Stocks Inventory by Sector"
  (household, commercial, NFA). Acquired for Y12 (`LEAD2_RELIABILITY_RESEARCH/y12_domestic_rice_supply/data_acquired/
  tidy_stocks_national.csv`, from `stocks_national_monthly.csv` aaa6073c). Coverage 1980-01..2026-09, national,
  monthly, stock as of the 1st of the month.
- **Never used for the SWS hunger target.** Y12 tested it only for the provincial food-price condition (no gain:
  +0.0003 Brier).
- **Mechanism:** large household and public (NFA) rice stocks buffer households against price and supply shocks, so
  they may separate quarters where high prices do or do not translate into hunger.

## Availability rule (Y12 DATA_AUDIT, fixed)

- **Verified release lags:** 31–92 days.
- **At origin t with issue date O(t):** use the stock month M = (issue month) − 4 or earlier.
- **Revisions:** OpenSTAT serves only the current vintage. Early values may differ from first releases. This is
  recorded as a limitation and cannot be quantified.

## Features (two, fixed; no selection)

- `ST1` = (total stock at M / total stock at M − 12 − 1) × 100: year-on-year % change in total rice stocks.
- `ST2` = NFA share of total stock (%) at M minus the same share at M − 12: change in the public buffer, in points.
- **Missing** when either month is absent (no imputation beyond LightGBM's native handling, as in C-E2).
- **Leakage check:** replacing every stock month after M with random values must leave ST1 and ST2 unchanged at every
  origin.

## Model

- **Exactly C-E2** (`ce2_model.py`): 23 inputs + ST1 + ST2 = 25; the same table, labels known at O(t), stacked leads,
  walk-forward from 1998-Q3, the mean of the 8 `hr_lib.GRID` settings, seed, fallback.
- **SHAP:** mean TreeSHAP. ST1 and ST2 are reported as their own group ("supply"), not one of the five dashboard groups.
- Target 11.3% and threshold 0.50 unchanged.

## Evaluation (as C-E2)

- **Sample:** 62 verdict quarters, Leads 1–2 (Leads 3–8 for Algorithm 3).
- **Metrics and rules:** all metrics, R1–R7, ECE.
- **Statistics:** the 14-test Holm family (paired Brier, one-sided cluster bootstrap, seed 2036, B 5000); paired Brier
  vs C-b and vs C-E2.

## Acceptance (all required)

1. **H6, the supply information helps:** Brier < C-E2 at both leads, one-sided p < 0.10.
2. **Rules and lead:** R1–R7 pass at Leads 1 and 2, and MRLT ≥ 2.
3. **Accuracy:** ≥ 0.75 at both leads.
4. **Leakage:** the check passes.
5. **For "beats all seven":** all 14 Holm comparisons significant at 0.05. Reported separately; not required for
   development adoption.
6. **Plus team and adviser approval.**

**Failure:** any of 1–4 fails, and C-E6 is reported as a failed attempt. **No variant (other lags, other stock
features, other weights) will be tried after seeing the results.**

**Reported whatever the result.**
PLAN-SHA256: 6e07ee14ecfd7925561c20e7774593d15c69d1d0501f0ee5227854e604af5ac8
