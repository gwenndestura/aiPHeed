# E168 protocol: the E166 method with the learner fixed to LightGBM (one locked run)

- **Written:** 2026-11-06, before the E168 code was run and before any E168 result existed.
- **Locking:** `python -m app.e168.lgbm lock` hashes this file, the code and every input file. `eval` refuses to run if any of them changed, refuses a second run, and refuses if a file is missing.
- **Owner decision, 2026-11-06:** "it should be LightGBM". The thesis paper specifies a LightGBM forecasting model. E166's automatic selection chose Random Forest (and ElasticNet once) and never LightGBM.

## Method: identical to E166 except the learner
| Part | E166 | E168 |
|---|---|---|
| Survey anchors (H, RP, OH, RSS) | chosen on training rows | same |
| Learner | chosen from NONE, Ridge, ElasticNet, Random Forest, LightGBM | **LightGBM only** (`app.e151.prov.Res2`, the E151/E158 LightGBM settings with its inner tree-count choice) |
| Inputs | official only (GOV) or all incl. news (FULL), chosen on training rows | same |
| Linear calibration (identity or inner linear) | chosen on training rows | same |
| Selection score | inner weighted SSE, region GroupKFold, training rows only | same; 4 anchors × 2 input sets = 8 configurations |
| Temperature shrink λ | (a) forward held-out rounds; (b) SWS out-of-time forecasts with ElasticNet; inverse-variance; clip [0.3, 1] | (a) same; (b) SWS forecasts with **LightGBM** (`app.e151.sws.PAR`, the project's SWS LightGBM settings, random_state 151) on the same rows and inputs |
| sd of P(HIGH) | refitted on the shrunk training errors | same |
| HIGH line | score ≥ 50 | same |

Rows, leads (1–8), surveys (ENNS 2018, 2019, 2021), the as-of release rules and the leakage control are those of E166.

## Pass rule (fixed now)
- **E168 is reliable at a lead** if all six E156 criteria C1–C6 pass (unchanged `app.e156.leads.evaluate`). The maximum reliable lead is the longest run from Lead 1.
- **E168 becomes the thesis model (LightGBM)** if C1–C6 all pass at Lead 1 and the run is valid (the leakage control changes no output by 1e-9 or more).
- **Otherwise** E166 stays the best model, and the thesis reports that the LightGBM-only version was tested once and did not pass.
- Brier against E166 and AUTO is reported but is not part of the rule.

## Always reported
- Leads 1–8: accuracy, precision, both recalls, F1, AUC, Brier, C1–C6, calibration slope and intercept with 95 % intervals, 90 % coverage.
- The configuration and λ chosen at every issue.
- Lead-1 comparison with E166, AUTO, E158 and all RQ3 baselines, including government-only LightGBM and government-only logistic, with Brier differences and 95 % intervals.

## Disclosure
- **Seen before writing this:** E164 scored every fixed configuration on these 72 Lead-1 rows. The LightGBM ones reached 70.8 % to 79.2 % (best: own history + LightGBM + official inputs, 57/72). E168 does **not** pick that configuration: it chooses on training rows only, as E166 did. Because those results were seen, any pass is somewhat optimistic.
- Every earlier attempt on these rows is listed in `docs/e166/PROTOCOL.md` §7 (E151–E166). E168 adds one more.
- Retrospective evidence only. The sealed 2027 forecasts remain the blind test.

## Not allowed after the lock
Changing the learner, menu, settings, λ rule, HIGH line or pass rule; dropping rows, rounds or leads; re-running.
