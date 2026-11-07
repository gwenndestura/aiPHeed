# E168 model verification (read-only; 2026-11-07)

## Identity and integrity: VERIFIED
- **Code:** `backend/app/e168/lgbm.py` (procedure, forecast, task, evaluate), `backend/app/e166/temperature.py`, `backend/app/e151/prov.py` (Res2).
- **Lock:** `data/e168/out/lock.json`, locked 2026-11-06T13:56:03Z, 12 files; **0 changed since lock** (hashes recomputed now).
- **Decision record** (`results.json`): leakage 0.0, void false, Lead-1 correct 56, Lead-1 C1-C6 all true, max reliable lead (strict) 1.
- **Sealed live forecast** `sealed_2027-Q1.json` (SHA-256 prefix 28f2c918) is identical to `history/2027-Q1.json` forecasts.
- **No serialized model file exists.** E168 is reproduced by deterministic refit (seed 151); served values are precomputed history JSON. Reproduction is exact (max difference 0.0 in E171, E172, E173).

## Algorithm and settings: VERIFIED
- Survey-error LightGBM `Res2`: `app.e150.model.PARAMS` = 4 leaves, depth 2, min child 10, learning rate 0.02, L2 5.0, row and column
  fraction 0.8; random_state set to 151 (`Pv.SEED`); trees chosen from {100, 300, 600} by weighted region-fold error inside training
  rows; monotone constraints from `Pv.SIGN`; sample weight 1/(se² + 0.05).
- Menu: anchors {H, RP, OH, RSS} × LightGBM × inputs {GOV (32), FULL (68)}, chosen per issue by region-fold weighted SSE on training
  rows; identity vs linear calibration chosen the same way.
- Temperature shrink: lambda from round-held-out refits (a) and SWS out-of-time forecasts with LightGBM (b; `app.e151.sws.PAR`,
  seed 151), inverse-variance combined, clipped to [0.3, 1]; sd refitted on shrunk training errors; P(HIGH) = Phi(lambda·mu / sd); HIGH if P >= 0.5.

## Configuration by issue (from results.json)
| Survey | Lead 1 | Lead 2 | Lead 3 |
|---|---|---|---|
| ENNS 2018 | OH, FULL, lambda 0.357 | OH, FULL, 0.382 | OH, FULL, 0.300 |
| ENNS 2019 | OH, FULL, 0.360 | OH, FULL, 0.407 | OH, FULL, 0.300 |
| ENNS 2021 | RSS, GOV, 0.878 | RSS, GOV, 0.893 | RSS, FULL, 1.000 |
| Live 2027-Q1 (issue 2026-10-01, 732 training rows, rounds 2013-2021) | RSS, FULL, 0.751 | | |

## Leads and periods: VERIFIED
Issue quarter = survey reference quarter (Q3 of the survey year) minus lead; training uses only rounds released `ANCHOR_LAG`
quarters before the issue; Leads 1-8 evaluated (Leads 7-8 have 50 rows).

## Served path: VERIFIED locally, NOT deployed (F01)
`app/e168/history.py` writes per-quarter JSON; `app/services/e166_serving.py` (AIPHEED_THESIS_MODEL default e168) feeds
`app/services/dashboard.py`. Under the Render environment the overlay is disabled and the Chapter I system is served.

## Results (recomputed; STATISTICAL_RECALCULATION.csv)
Lead 1 56/72, C1-C6 pass; Lead 2 55/72, C1 fails (low bound 0.6405 vs 0.6528), C2-C6 pass; Lead 3 54/72; 75 % rule met at Leads 1-3.
