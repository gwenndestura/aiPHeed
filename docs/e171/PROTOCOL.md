# E171 protocol: Lead-2 improvement candidates (EXPLORATORY)

- **Written:** 2026-11-07, before any E171 code was run and before any E171 result existed.
- **Status:** exploratory. The 72 evaluation rows per lead (ENNS 2018, 2019, 2021) were already used in E151-E169, and the E168
  error pattern (false HIGHs near 50, concentrated in ENNS 2018 after the 2015-2018 national decline) was seen before this was written.
  No E171 result on those rows is confirmatory evidence. Confirmation needs new survey rows (2023 NNS provincial) or the 2027 outcomes.
- **Owner request:** "E171: Improve Lead 2 forecast accuracy and strict C1-C6 reliability" (2026-11-07).
- **Not changed:** E168, E169, the served model, the sealed 2027-Q1 forecast (28f2c918), the target, the HIGH line (score >= 50,
  P(HIGH) >= 0.5), the rows, C1-C6 (`app.e156.leads.evaluate`, unchanged), the effective-n and interval method.
- **Locking:** `python -m app.e171.candidates lock` hashes this file, the code and the inputs; `eval` runs once.

## 1. Root cause addressed
E168's LightGBM adjustment has no food-insecurity trend input: SWS hunger is used only for the temperature shrink, never as a
predictor. The E171 candidates add the one timely, published-dated trend signal in the repository.

## 2. New inputs (Candidate features)
All from `data/fi5/raw/sws/` via `app.e144.data.sws_quarterly()` (SWS quarterly hunger, 4 areas: Metro Manila, Balance Luzon,
Visayas, Mindanao; 1998-Q3 onward; each quarter has its SWS publication date). For a row with issue quarter i, anchor survey reference
quarter a and SWS area s; only SWS quarters **published before the start of quarter i** are used:

| Input | Definition | Level |
|---|---|---|
| `sws_now` | mean hunger (%) of area s over its last 4 quarters published before i | area (shared by the area's provinces) |
| `sws_since` | `sws_now` minus mean hunger of area s over quarters a-3..a (the anchor survey's year) | area |
| `sws_nat_since` | the same change averaged over the 4 areas | **national** (shared by all provinces; labelled national) |

Monotone constraint in LightGBM: +1 for all three (more hunger, higher food insecurity), fixed now.
Leakage control: as E168, unreleased survey rounds and SWS quarters after the cut-off are randomised; every output must change by < 1e-9.

## 3. Candidates (all use E168's anchors H, RP, OH, RSS and E168's temperature shrink, sd and HIGH line)
| Family | Learner | Inputs |
|---|---|---|
| E168-TA | LightGBM (`Res2`) | GOV, FULL (E168's inputs) |
| A: trend inputs | LightGBM (`Res2`) | GOV+S, FULL+S (S = the three SWS inputs) |
| B: lead-band | LightGBM trained only on training rows within one quarter of the forecast's own lead | GOV+S |
| C: alternative statistical | Ridge, ElasticNet (`app.e163`/`app.e164`) | GOV+S |
| D: hybrid trend | weighted linear trend on `sws_since` and `sws_nat_since`, then LightGBM on what remains | GOV+S |
| **E171 (pre-declared final)** | the best of all 32 configurations above | |

## 4. Time-aware selection (training rows only)
Each configuration's training score is its weighted squared error **forward in time over whole survey rounds**: every later training
round is predicted by a fit on strictly earlier rounds (all provinces of a round together). When the training rows hold only one
survey round (the ENNS 2018 and ENNS 2019 forecasts: only the NNS 2013 -> FNRI 2015 transition exists), forward scoring is impossible
and the score falls back to E168's region-grouped folds; the report states this per issue. Within each family and for E171, the
configuration with the lowest score is used; identity vs linear calibration is chosen the same way. Nothing is chosen on the 72 rows.

## 5. Decision rule (fixed now)
- Reported for every family at Leads 1, 2, 3: C1-C6 with the exact `leads.evaluate` numbers, accuracy, balanced accuracy, precision,
  recall, F1, ROC-AUC, PR-AUC, Brier, calibration slope and intercept with 95 % intervals, per survey round and per province.
- **"Lead 2 genuinely improved (exploratory)"** only if the pre-declared E171 (not the best family after the fact) passes C1-C6 at
  Lead 2, keeps C1-C6 at Lead 1, the run is valid, and its Lead-2 Brier is not worse than E168's (paired 95 % interval).
  Even then it is exploratory, is not served, and E168 stays the thesis model until confirmed on new survey rows.
- Families other than E171 are diagnostics; one passing alone is not a claim.

## 6. Not allowed
Changing the menu, inputs, constraints, rule or HIGH line after the lock; dropping rows, rounds, ENNS 2018 or provinces; adding cities;
re-running; serving E171; changing E168, E169 or the sealed forecast.

## 7. Run log
- 2026-11-07, first locked eval: **crashed before producing any output** (worker processes did not register the new inputs:
  `KeyError: 'GOV_S'`). No E171 result was produced or seen. Fix: `_install()` registers inputs and learners inside every job, with an
  assertion. The same defect means **E169's seed bagging was never applied** in its worker processes (verified: workers used `Res2`);
  E169's "identical to E168" result is therefore not a test of seed bagging. E169's files are left unchanged.
  Re-locked after the fix; nothing else changed.
- 2026-11-07, second locked eval: **crashed before producing any output** (forward-in-time calibration had no earlier held-out round
  for the first one: empty concatenate). Fix: that round uses identity calibration (protocol section 4 unchanged in intent).
  Both paths smoke-tested on ENNS 2021 Lead 2 without printing any accuracy or label. Re-locked; nothing else changed.
- 2026-11-07, third locked eval: all forecasts written (`oof.csv`, `all_rows.csv`), then the scoring step stopped on a missing E169
  interval column. Scored by `app.e171.score`, which only reads the saved forecasts (no forecast recomputed); arms without an interval
  get NaN intervals (coverage not reported for them). Results in `RESULT.md`.
