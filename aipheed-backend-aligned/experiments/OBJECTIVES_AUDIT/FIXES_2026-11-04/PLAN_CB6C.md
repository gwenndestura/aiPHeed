# C-B6C: C-B6 + one CALABARZON-only news shock signal (pre-registration, fixed before any fit, 2026-11-04)

**Development evidence:** attempt 25 on the same 62 previously examined quarters, disclosed as such. Written after
C-B6N (attempt 24) failed. C-B6 stays the main model unless the rule below is met.

## Design principles

Following the research use of news to fill gaps while official data are late (Balashankar et al., 2023), and the
lessons from C-B6N:

1. **Fill the missing quarter.** At each issue date O(t) (the first day of quarter t+1), SWS has not yet published
   quarter t. News published inside quarter t describes that unreleased quarter.
2. **One signal only.** C-B6N added 7 inputs and over-fitted.
3. **Shocks, measured against normal:** an as-of z-score against earlier quarters.
4. **CALABARZON only.** The signal is attached to Balance Luzon training rows only; NCR, Visayas and Mindanao rows get
   missing. C-B6N had copied its features to all four areas.
5. **Recent news weighs more.** Events in the last 42 days of the quarter count double.

## Data (frozen)

- **Source:** `aipheed_final/backend/data/fi6/news_archive/events.parquet` (FI6-N, commit 6c90dfe4; raw text is
  gitignored and not copied). Its SHA-256 is recorded by the builder in `data/cal_shock_quarterly.csv`'s companion
  `data/cal_shock_build.json`.
- **Denominator:** `articles_calabarzon` from the locked FI6-N feature file (SHA-256 abc0e59c…).

### Feature CAL_SHOCK(t), defined exactly

1. **Events:** `relevant` and not `excluded` and not `restated_statistic`; `geo_level` in {lgu, province, region,
   body_mention} (located in CALABARZON); `direction == increases_risk`; `evidence` in {ongoing_disruption,
   observed_hardship}. One row per `event_id` (earliest published).
2. **Quarter t:** the event's `quarter`, i.e. published inside quarter t.
   - weight 2 if published on or after O(t) − 42 days, else 1.
3. **Rate:** raw(t) = 100 × (sum of weights) / `articles_calabarzon`(t). If `articles_calabarzon` is 0 or missing,
   the rate is missing.
4. **Z-score:** CAL_SHOCK(t) = (raw(t) − mean of earlier raws) / SD of earlier raws, using quarters before t only,
   with at least 8 earlier non-missing quarters; otherwise missing. If SD = 0, the value is 0.
5. **Attachment:** the value is added to the pooled table on t for area BL only; NCR, VIS and MIN are missing.

**Leakage check (before fitting; the fit stops on failure):** randomise raw(·) for quarters after t, recompute, and
require CAL_SHOCK(t) to be unchanged at every origin (5 repetitions, seed 2036). Every counted event is published
before O(t) by construction (published inside quarter t).

## Candidate (exactly one)

- **C-B6C = C-B6 exactly** (`runner/cb6_model._origin`) + CAL_SHOCK: 24 inputs, no monotone constraints, target 11.3%,
  threshold 0.50.
- **Replication gate:** C-B6 must be reproduced first (max difference < 1e-9), or the run stops.
- **No variant** (other weights, windows, event filters, extra features) will be tried after seeing the results.

## Evaluation and decision (as PLAN_CB6N.md)

- **Sample:** 62 verdict quarters, Leads 1–2.
- **Reported:** all metrics, calls changed, R1–R7, Algorithm 3, paired Brier vs C-B6 (also on news-era origins), and
  the 14-test Holm family with PERSIST-P.
- **H9 (primary):** C-B6C Brier < C-B6 at Lead 1, one-sided p < 0.05.
- **Secondary:** Lead 2, p < 0.10.
- **Outcomes:**
  - "CALABARZON news improves the forecast" only if H9 holds;
  - if H9 holds and R1–R7 pass at Leads 1–2, C-B6C is recommended as the main model (owner approval);
  - if H9 holds but R1–R7 fail, news is reported as improving probabilities only;
  - otherwise C-B6 stays and no further news variant is tried.

**Reported whatever the result.**
PLAN-SHA256: 1cb7de04985ca3ff46debb199990c08d8211a2e62ecc5e805f70fc2ef1f25f4c
