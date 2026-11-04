# C-B6N: C-B6 + FI6-N archive news (pre-registration, fixed before any fit, 2026-11-04)

**Development evidence:** attempt 24 on the same 62 previously examined quarters, disclosed as such. C-B6 stays the
main model unless the rule below is met.

## Why this test, and why it is not a repeat

- C-B6's only news input is `z_N1R` (Google News, 2021+). It exists at about 20 of 62 verdict quarters and changes no
  call.
- FI6-N rebuilt the news from publisher archives (Rappler, VERA Files, NewsBytes.PH, PCIJ) with headline plus lead
  paragraph, from 2012-Q3: 62,698 articles, 2,879 relevant. 500 restated official statistics were removed, including
  107 SWS hunger reports (the outcome).
- On the FI6 target, FI6-N news improved LightGBM Brier at Lead 1: −0.0099, Bonferroni 98.75% CI (−0.025, −0.0006);
  AUC 0.70 → 0.77. It changed no class, and Lead 2 was borderline (−0.0052, CI to +0.0006)
  (`aipheed_final/docs/fi6/NEWS_RESULTS.md`).
- **Never tested:** FI6-N news inside C-B6, on the 11.3% Balance Luzon target.

## Data (frozen)

- **File:** `data/fi6n_news_features_quarterly.csv`, copied unchanged from `aipheed_final`
  `backend/data/fi6/news_archive/news_features_quarterly.csv`, commit 6c90dfe4.
- **SHA-256:** abc0e59c5cc5265ccb0dcec181057632d3f0bb04cc11bd9b526e81cb1ff88d3e. This equals the FI6-N method lock
  (`METHOD_LOCK_NEWS.json`), so the features are unchanged since FI6-N was locked.
- **Seven features, exactly as FI6-N's `asof_news()`:**
  - risk-event shares: na_market, na_climate, na_employment, na_remittance, na_poverty;
  - na_climate_damage = climate_damage_log; na_displaced = displaced_families_log;
  - each z-scored against the same feature's earlier quarters only (at least 8 earlier non-missing quarters, else
    missing).
- **Timing:** news published inside quarter t. C-B6's issue date for origin t is O(t) = the first day of quarter t+1,
  so quarter t's news is complete at issue. Origin t uses the news row for quarter t, merged on t, like ST1/ST2.
- **Leakage check (run before fitting; the fit stops if it fails):** randomise every raw feature value for quarters
  after t, recompute, and require origin t's seven values to be unchanged (all origins, 5 repetitions, seed 2036).

## Candidate (exactly one)

- **C-B6N = C-B6 exactly** (`runner/cb6_model._origin`: same table, labels known at O(t), walk-forward from 1998-Q3,
  `hr_lib.lgbm_select` inner-fold grid, seed, fallback, test leads 1–8), plus the seven news inputs.
- **30 inputs:** C-B6's 23 + 7.
- **Unchanged:** no monotone constraints (C-B6 uses none); target 11.3%; threshold 0.50.
- **Replication gate:** before fitting C-B6N, the copied procedure must reproduce the stored C-B6 forecasts
  (`out/cb6_fits.csv`, maximum difference < 1e-9), or the run stops.
- **No variant** (other features, lags, weights, settings or subsets) will be tried after seeing the results.

## Evaluation

- **Sample:** 62 verdict quarters, Leads 1–2, same frame (`run_iv2.frame`) and labels.
- **Reported:** all Objective 2 metrics (accuracy, precision, recall, F1, AUC, Brier), calls changed vs C-B6, R1–R7,
  and Algorithm 3 (Leads 1–8).
- **Paired Brier vs C-B6** with `phase_c._paired` (one-sided cluster bootstrap, seed 2036). Also on the news era
  (origins with at least one non-missing news feature).
- **Objective 4:** the 14-test Holm family with PERSIST-P (`PLAN_PERSIST_P.md`) for C-B6N.

## Decision rule (fixed)

- **H8 (primary, Lead 1):** C-B6N Brier < C-B6 Brier at Lead 1, one-sided p < 0.05. Lead 1 is primary because the
  only prior evidence (FI6-N) located the gain there.
- **Secondary (Lead 2):** the same test at Lead 2, p < 0.10. Reported, not used for H8.
- **"News improves the forecast" is claimed only if H8 holds.** If it does and R1–R7 still pass at Leads 1–2, C-B6N
  becomes the recommended main model (team/owner approval). If H8 holds but R1–R7 fail, news is reported as improving
  probabilities only, and C-B6 stays.
- If H8 fails, the thesis reports that archive news did not improve C-B6, and nothing else is tried.

**Reported whatever the result.**
PLAN-SHA256: 976076dcf26e38e5cc7bef49d48c6975450f86f5111c9cb29e03c57af48a98a5
