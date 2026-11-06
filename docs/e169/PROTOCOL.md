# E169 protocol: E168 with seed-bagged LightGBM (one locked run)

- **Written:** 2026-11-06, before the E169 code was run and before any E169 result existed.
- **Locking:** `python -m app.e169.bag lock` hashes this file, the code and every input file. `eval` refuses to run if any of them changed, refuses a second run, and refuses if a file is missing.
- **Owner decision, 2026-11-06:** the thesis model should reach at least Lead 2 under the strict criteria C1-C6, with higher accuracy, and stay LightGBM.

## Why this change, and only this change
E168's LightGBM models sample 80 % of rows and 80 % of columns per tree with **one** random seed (151), so part of each forecast is seed noise.
Averaging the same model over several fixed seeds ("seed bagging") is the standard way to remove that noise. It adds no setting and tunes nothing:
the learner, its settings, the menu, the selection rule, the calibration rule and the temperature shrink are E168's.

| Part | E168 | E169 |
|---|---|---|
| Survey-error LightGBM (`app.e151.prov.Res2`) | one fit, random_state 151 | **mean of 5 fits, random_state 151, 152, 153, 154, 155**, in the inner tree-count choice, the out-of-fold errors and the final fit |
| SWS LightGBM for the temperature shrink (`app.e151.sws.PAR`) | one fit, random_state 151 | **mean of 5 fits, random_state 151-155** |
| Everything else (anchors, inputs, menu of 8, inner selection, calibration, lambda rule, sd, HIGH line at 50, rows, leads 1-8, as-of rules, leakage control) | E168 | same |

The number of seeds (5) and the seeds are fixed here and are not changed after any result.

## Pass rule (fixed now)
- **Reliable at a lead:** all six E156 criteria C1-C6 pass (unchanged `app.e156.leads.evaluate`). Maximum reliable lead = longest run from Lead 1.
- **E169 replaces E168 as the thesis model** only if C1-C6 all pass at **Lead 1 and Lead 2** and the run is valid (the leakage control changes no output by 1e-9 or more).
- **Otherwise E168 stays the thesis model**, and the thesis reports that E169 was tested once and did not pass.
- Accuracy, Brier and the rest against E168, E166 and all RQ3 baselines are reported but are not part of the rule.

## Disclosure
- **Seen before writing this:** E168's locked results: Lead 1 56/72 (C1-C6 pass), Lead 2 55/72 (fails C1 only, by about one row), Lead 3 54/72. E166 (not LightGBM) passes C1-C6 at Leads 1-2.
  E169 was proposed *because* E168 fell one row short at Lead 2, so any pass is optimistic. It is one more attempt on the same 72 rows (earlier attempts listed in `docs/e166/PROTOCOL.md` and `docs/e168/PROTOCOL.md`).
- Retrospective evidence only. The sealed 2027 forecasts remain the blind test.

## Not allowed after the lock
Changing seeds, number of seeds, learner, menu, settings, lambda rule, HIGH line or pass rule; dropping rows, rounds or leads; re-running.
