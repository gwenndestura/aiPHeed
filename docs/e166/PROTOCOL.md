# E166 protocol: AUTO + temperature shrink (calibration only)

- **Written:** 2026-11-06, before the E166 code was run and before any E166 result existed.
- **Locking:** `python -m app.e166.temperature lock` hashes this file, the code and every input file. `eval` refuses to run if any of them changed since the lock, refuses a second run, and refuses if a file is missing.
- **Owner approval is required before `lock`.**
- **Replaces** the earlier E166 design (drift nowcast + top-5 averaging). That design was written but never locked or run; it is kept unchanged in `docs/e166/paused_drift_average/`.
- **Revision v2, before any lock or run:**
  1. P(HIGH) uses an sd **refitted on the training errors of the shrunk score**, not AUTO's own sd, so probabilities do not collapse toward 0.5.
  2. Held-out rounds go **forward in time**, instead of GroupKFold by round.
  3. The SWS estimate **pools leads ≤ h** when fewer than 20 same-lead pairs exist.

  No test row was read for any of these changes.

## 1. Goal and starting point
**Goal:** make AUTO's score calibrated (E156 criterion **C4**) **without changing any HIGH/LOW class.** Accuracy, precision, recall, F1 and AUC then stay exactly equal to AUTO's.

**AUTO at Lead 1, from existing outputs:**

| Item | Value | Source |
|---|---|---|
| Correct | **57 of 72** (TP 22, FP 12, FN 3, TN 35) | `backend/data/e164/out/results.json` → `leads.1.class.AUTO.confusion` |
| Accuracy | **0.792** | same, `accuracy` |
| Lower 95 % bound at effective n vs majority rule | 0.674 vs 0.653 | `backend/data/e165/out/results.json` → `reliability_AUTO`, Lead 1 |
| C1 C2 C3 C4 C5 C6 | pass pass pass **fail** pass pass | same, `criteria` |
| Calibration slope | 0.734 [0.51, 0.88] | `e164/out/results.json` → `calibration_slope`, `calibration_slope_ci95` |

**C1 at the effective sample size:**
- n_eff = 72 / (1 + 0.8 × 0.726) ≈ 45.6, so C1 needs about **56 of 72**.
- **AUTO has 57, so it reaches C1.**
- **Shrinking cannot change C1**, because C1 depends only on AUTO's correct count, and no class changes.

## 2. Method
For every outer issue (survey × lead) and every row:

```
score_TS = λ · mu_AUTO,            0 < λ ≤ 1
class    = (mu_AUTO ≥ 0)           unchanged; identical to AUTO
P(HIGH)  = Φ(λ · mu_AUTO / sd_λ)
90 % range = score_TS ± half_λ
```

- **sd_λ and half_λ** come from `app.e164.auto.scale`, fitted on the training errors `y − λ · oof`, where `oof` is the inner out-of-fold score of AUTO's chosen configuration. This is the same rule AUTO uses with λ = 1.
- **Why this is needed:** with AUTO's own sd, a shrunk score would pull every probability toward 0.5 and worsen Brier.
- **The score and AUTO's chosen configuration** come from `app.e165.calib.procedure`, a verified copy of `app.e164.auto.run_procedure` that also returns `oof`. It is hashed in the lock, and the reproduction check (section 4) confirms it equals AUTO.

- **No intercept and no level shift:** either would move the 50 line and change classes.
- **Drift (Fix 1) and averaging (Fix 4) are not part of E166.**
- **AUTO itself is run unchanged** (`app.e164.auto.run_procedure`, kind ALL) at Leads 1–8. AUTO was previously run only at Leads 1–4, so at Leads 5–8 its outputs are **new** and have no committed reference.

## 3. Estimating λ without the 72 test rows
**λ is computed per issue date, only from data released before that date** (survey rounds: `M.released`, reference quarter + 6; SWS: `published` date strictly before the first day of the issue quarter).

### (a) Round-held-out refits, where training holds two or more target rounds
- Take **AUTO's chosen configuration** at that issue (anchor, learner, feature set, calibration).
- **Forward in time:** each training target round g after the earliest is scored by refitting the configuration on the **strictly earlier** training rounds only:
  - at the ENNS2021 Lead 1–2 issues, 2015 → 2018, then 2015 + 2018 → 2019;
  - at Leads 3–6, 2015 → 2018.

  This measures directly how confident a fit is when it forecasts a **new, later** round.
- If the configuration uses AUTO's linear calibration, the calibration line is refitted on the earlier rounds only, using their inner out-of-fold scores (region GroupKFold, as AUTO does).
- **λ_a** = the weighted least-squares slope, with intercept and weights 1/(se² + 0.05), of the held-out true outcomes on the held-out scores, pooled over the held-out rounds. Its variance is the usual WLS variance.
- Fewer than 20 held-out rows: no estimate.

### (b) SWS, out of time
- **Series:** SWS quarterly involuntary hunger, four areas, from `app.e144.data.sws_quarterly` (1998–2026, with publication dates).
- **Rows:** area-quarter rows built as in `app.e151.sws.area_table`:
  - government inputs `R150.INPUTS` (area means; national means for Metro Manila, as in E151);
  - SWS state (`sws_last`, `sws_anom`) from readings published before the row's quarter;
  - lead 1–8.
- **Model ("same model type" as AUTO's 2018/2019 choice, OH + ElasticNet + official inputs):** persistence anchor (`sws_last`) plus AUTO's ElasticNet residual learner (`app.e164.auto.ENetRes`) on the government inputs and SWS state.
  - α ∈ {0.001, 0.01, 0.1}, l1 ratio 0.5, chosen by GroupKFold over areas.
  - Equal weights (se set to 0).
- **Expanding window:** forecasts are issued each quarter from 2015-Q1. Each is fitted only on rows whose outcome was published before that SWS issue date, with at least 60 training rows.
- **λ_b** = the slope, with intercept and equal weights, of the realised SWS logit level on the forecast logit level.
  - Uses only pairs whose forecast was issued **and** whose outcome was published **before** the province issue date.
  - Pairs at **the same lead** as the province forecast are used. If fewer than 20 exist, pairs at **all leads ≤ h** are pooled.
  - Still fewer than 20: no estimate.
- **Disclosed:** SWS is a different instrument (a one-item, three-month hunger measure at area level). Assuming its overconfidence factor carries over to provincial HFIAS is an assumption, not a measurement.

### (c) Combination
- **Both available:** inverse-variance weighted mean of λ_a and λ_b.
- **One available:** that one.
- **Neither:** **λ = 1** (no shrink).
- **Then clip λ to [0.3, 1.0].**

| Outer issue | Training target rounds | Sources expected |
|---|---|---|
| ENNS2018 and ENNS2019, Leads 1–8 | one (FNRI2015) | (b) only |
| ENNS2021, Leads 1–2 | three (2015, 2018, 2019) | (a) and (b) |
| ENNS2021, Leads 3–6 | two (2015, 2018) | (a) and (b) |
| ENNS2021, Leads 7–8 | one (2015) | (b) only |

### Expected direction, written before the run
- **λ ≤ 1 by construction**, so the score slope can only rise.
- **λ_b may be close to 1,** because SWS levels are dominated by persistence. In that case the 2018 and 2019 rows (47 of 72) shrink little, and **C4 may still fail.**
- **sd is refitted on the shrunk training errors,** so probabilities move less than the score. Brier may still change in either direction; Brier not worse than AUTO's is part of the pass rule.

## 4. Controls (the run is void if either fails)
- **Reproduction:** E166's AUTO score must equal E164's committed `mu_AUTO` on Leads 1–4 (max absolute difference < 1e-6).
- **Leakage:** at Lead 1, the run is repeated with two things randomised:
  - unreleased survey rounds;
  - every SWS reading published on or after the issue date.

  λ, score and P(HIGH) must change by < 1e-9.
- **Class identity** is checked on every row of every lead.

## 5. Pass rule (fixed now, unchangeable after the lock)
**E166 passes only if all of these hold at Lead 1:**
1. E156 criteria C1, C2, C3, C4, C5 and C6 all pass (unchanged `app.e156.leads.evaluate`);
2. every class is identical to AUTO's;
3. the Brier point estimate is not worse than AUTO's (E166 − AUTO ≤ 0);
4. the reproduction and leakage checks are valid.

**Plain statements:**
- **Shrinking cannot change C1, C3, C5 or C6,** which depend only on classes. AUTO already passes them.
- **E166 can change only C2 (Brier against persistence) and C4.**

**Ceiling, stated before the run:**
- **Leads 3 and 4:** AUTO is correct on 55 of 72, below the about 56 that C1 needs. No shrink can make them reliable.
- **Leads 5–8:** AUTO has not been run there before; C1 is not expected to pass.
- **So the best possible result is a maximum reliable lead of 2** (Leads 1 and 2, where AUTO has 57 of 72), and only if C4 and C2 pass there. "All leads reliable" is not reachable by this method.

**If E166 passes:**
- it becomes the release candidate in place of AUTO, with the same classes and calibrated scores;
- `live` seals its 2027-Q1 forecast;
- it is not deployed until a sealed forecast is scored.

**If it fails:** AUTO stays as the release candidate and E158 stays as the thesis model.

## 6. Always reported, whatever the outcome
- **λ per issue date:** its source (a, b, both or none), λ_a, λ_b, their variances, the number of SWS pairs, the training rounds and AUTO's chosen configuration.
- **Leads 1–8, for E166, AUTO (recomputed) and E158:**
  - accuracy, precision, recalls, F1, AUC, Brier;
  - C1–C6 and the maximum reliable lead;
  - calibration slope **and intercept**, each with a 95 % region-bootstrap interval;
  - 90 % range coverage.
- **The reliability table by probability band** (0–20, 20–40, **40–60**, 60–80, 80–100 %), for E166 and AUTO, at every lead.
- **Brier of E166 minus** AUTO, E158, GNT, **GOV**, NEWS, LR, LR_NEWS, PSA, PERS and the anchor, each with a 95 % region-bootstrap interval, at every lead where the comparator exists.

## 7. Disclosure
**Every earlier attempt on these 72 Lead-1 rows:**

| Experiment | Lead-1 accuracy (correct of 72) |
|---|---|
| E151 required model (GNT) | 72.2 % (52) |
| E151 D5 locked attempt | 75.0 % (54) |
| E152 prices, rainfall, regional drift | 69.4 % (50) |
| E153 tuning with overfitting controls | 69.4 % (50) |
| E154 frozen 11-input model | 72.2 % (52) |
| E155 SunStar headlines | 72.2 % (52) |
| E156 locked calibration candidate | 68.1 % (49) |
| E157 three-group model | 69.4 % (50); sources ranked: farmgate 70.8, wholesale rice 68.1, NASA rainfall 72.2, consumption 73.6, SunStar 72.2 |
| E158 thesis model | 73.6 % (53) |
| E159 ranking test | 73.6 % (E158; ordering only) |
| E160 arms | RP 69.4 %, RP+R 72.2 %, OH+R 77.8 % (56) |
| E161 nested selection | 72.2 % (52) |
| E162 SS priority method | ordering only |
| E163 candidates | C1 69.4 %, C2 70.8 %, C3 69.4 %; nested 70.8 % |
| E164 AUTO | 79.2 % (57) |
| E165 AUTO + shrink-only (training-fold factor) | 79.2 % (57), classes identical; failed C4 |
| E166 first design (drift + averaging) | written, never locked or run |

**The design was chosen knowing:**
- **AUTO's slope is 0.73 [0.51, 0.88].** If a single λ were applied to every row, any λ between **about 0.51 and 0.88** would put 1 inside the slope interval and pass C4. With λ varying by issue date this is approximate.
- **E165's training-fold factor was 0.90–0.95,** too weak.

**λ is never fitted on, or chosen with, the 72 test rows.** The sources (a) and (b), the clip [0.3, 1.0], the minimum of 20 pairs, the SWS model and the combination rule are all fixed here.

**This is the final retrospective attempt on these rows.** If it fails, no further model or calibration is tried on them. Reliability is then claimed only from the prospective scoring of sealed forecasts (`docs/e154/SCORING_PROTOCOL.md`) or from a new provincial survey round.

## 8. Not allowed after the lock
Changing the λ sources, the clip, the minimum pair count, the SWS model, the combination, the HIGH line or the pass rule; dropping rows, rounds, leads or provinces; re-running.
