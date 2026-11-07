# E173 protocol: independent validation of the SIMPLE LightGBM hypothesis

- **Written:** 2026-11-07 (Asia/Manila), before any E173 code was run and before any independent label existed or was opened.
- **Comparison:** SIMPLE (from E172) vs E168, both frozen. E166-E172 artifacts, the sealed E168 2027-Q1 forecast (28f2c918), the served
  model and the four modified service files are not touched. `app.e156.leads.evaluate` (C1-C6, effective n, interval) is unchanged.

## 1. SIMPLE, frozen exactly as E172 defined it (`app/e172/lgbm_only.py`, locked hash fc407f6f1281)
Per issue quarter, on training rows only:
1. Anchor: best of E168's 8 configurations (anchors H, RP, OH, RSS x E168 LightGBM x GOV, FULL) by the survey-round-aware training
   score (`app.e171.candidates.score_all`: forward over whole survey rounds when the training rows hold 2+ rounds, else region folds).
2. Learner: best by the same score among the 24 low-complexity LightGBM variants: settings R1 (2 leaves, depth 1, min child 20, L2 10),
   R2 (3 leaves, depth 2, min child 20, L2 10), R3 (E168 settings with min child 30, L2 20), R4 (2 leaves, depth 1, min child 40, L2 20,
   column fraction 0.5); x pooled or lead-exact training rows; x inputs GOV, FULL, GOV_S (GOV + SWS hunger trend, published-before-issue).
   Other settings are `app.e150.model.PARAMS` (learning rate 0.02, row/column fraction 0.8); trees 100/300/600 chosen inside training
   rows; seed 151; monotone constraints as E168 (+1 for the SWS inputs); missing values left to LightGBM (as E168).
3. Identity vs linear calibration chosen on the same folds (cross-fitted).
4. E168's temperature shrink (lambda from round-held-out refits and SWS out-of-time forecasts), sd, and HIGH at P(HIGH) >= 0.5.
The rule and the hashes of every code file it runs are written to `data/e173/out/simple_config.json`; its SHA-256 is the config hash.

## 2. Independent data: verified status on 2026-11-07
- Repository: 2023 values exist only at regional level (FNRI 2023 NNS, CALABARZON 19.1 %), measured with **FIES**, not HFIAS. Not usable:
  different instrument and no provincial rows.
- DOST-FNRI Hunger and Malnutrition Heat Map API (live, 124 areas): latest provincial round is 2021 (Batangas, Cavite), 2019 (Quezon,
  Rizal), 2018 (Laguna). No 2023 provincial values.
- Therefore **no independent observations exist today**. E173 cannot confirm or reject SIMPLE now.
- The 72 ENNS 2018/2019/2021 rows are not independent (E151-E172 used them); E172's 59/72 for SIMPLE remains exploratory.

## 3. Prospective design (fixed now)
- C6 requires >= 40 rows, so a 5-province test can never pass C1-C6. The independent test is the **next DOST-FNRI provincial HFIAS
  round** (any year after 2021) for every province it covers that the panel can forecast.
- When that round is published, both frozen models are run with this repository's code at Leads 1, 2 and 3 before its reference
  quarter, as of each issue date, using only data published before that date (the rolling-origin rule of E168). Labels are loaded only
  after both models' forecasts are written and hashed.
- Now: both frozen models issue sealed forecasts as of 2026-10-01 (issue 2026-Q4) for **every panel province**: Lead 1 (2027-Q1) and
  Lead 2 (2027-Q2). These can be scored only if a provincial HFIAS round with a matching reference quarter is published.

## 4. Acceptance rule (fixed now)
SIMPLE is recommended for adoption only if, on independent rows (>= 40 at Lead 2), all hold: (1) C1-C6 pass at Lead 2; (2) more correct
than E168 at Lead 2 on the same rows (paired); (3) Lead-2 Brier not significantly worse than E168 (paired 95 % interval low end <= 0) and
calibration slope interval includes 1; (4) target, threshold, rows and evaluation unchanged; (5) per-province results reported.
Otherwise: reject (if it fails on independent rows) or **insufficient independent evidence** (if the rows do not exist or are < 40).

## 5. Leakage controls
Sealed forecasts: SWS quarters published on or after 2026-10-01 are randomised and every output must be unchanged (< 1e-9).
E168 is re-run inside the same job and must reproduce its served 2027-Q1 values for the five CALABARZON provinces.
