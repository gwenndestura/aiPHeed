# Y16: preregistered prospective comparison, Kalman vs hunger persistence (Lead-2 food insecurity)

**Status.** Frozen before any implementation or comparative run in Y16. The SHA-256 is in `PLAN_SHA256.txt` and the UTC time in `PLAN_FROZEN_AT.txt`. This plan is never edited. Any later change is a separately hashed addendum, and the change must be justified without reference to prospective outcomes.

## 1. Hypothesis

**H-Y16.** On future, sealed Lead-2 forecasts, the Kalman model that accounts for SWS sampling error (challenger) has a lower Brier score than hunger persistence (baseline) for the probability that Balance Luzon involuntary hunger exceeds 11.3%.

**Prior evidence, and its limits (Y14, Y15):**

| Source | Result |
|---|---|
| Y15, 2001–2020, 77 quarters | Kalman Brier 0.192 vs persistence 0.216. Raw p 0.091; **Holm-adjusted p 0.455** over five candidates; block p 0.25. |
| Y14, 46 quarters | −0.009, p 0.29 |
| Phase 2 (Y2), four-area pooled test | **Lost** to persistence: 0.165 vs 0.151 |
| 2021–2026 | Kalman **never predicted LOW** (12/5/0/0) |

The prior evidence is therefore weak. This study is a fair test, not an expected pass.

## 2. Target, horizon, outcome

| Item | Definition |
|---|---|
| Target | TFI-2: observed Balance Luzon (BL) involuntary hunger in target quarter q > 11.3% (y = 1, HIGH) |
| Horizon | Lead 2. Issue date O(t) = first day of quarter t + 1; target q = t + 2. |
| Issue schedule | Issue 2027-01-01 → **2027-Q2**; 2027-04-01 → 2027-Q3; 2027-07-01 → 2027-Q4; 2027-10-01 → 2028-Q1; and so on, every quarter. |
| Outcome | Mean of the BL hunger figures of every SWS round assigned to quarter q. This is the same convention as the FIRI target R and Y14/Y15 (`rlib.observed`). It includes commissioned rounds where SWS publishes a BL figure (e.g. 2025-Q1 Stratbase-SWS). |
| Outcome resolution | A target quarter resolves **120 days after it ends**. Rounds published after that are ignored. With no round by then, the outcome is *missing*: excluded from both models equally and counted. |
| Outcome source | Rounds already in the project series (read-only). New rounds are entered into `y16_kalman_prospective/data/sws_rounds_overlay.csv`, append-only: area, quarter, H, published date, MoE, source URL, entry time. |

**Erratum (recorded here; Y14 is not edited).** Y14 `RESULTS.md` says the 2027-01-01 issue targets 2027-Q3. Under the convention above (origin 2026-Q4, target t + 2) it targets **2027-Q2**. Verified with `rlib.issue`.

## 3. The two forecasts

These are exactly the specifications evaluated historically.

| Name | Role | Specification |
|---|---|---|
| **PERS (H1)** | baseline | `rlib.forecast("BL", t, 2, (NCR, BL, VIS, MIN))["RW"]` = Φ((x_last − 11.3) / σ_h). x_last = mean of the newest BL quarter with ≥ 1 round published before O(t). σ_h = RMS of horizon-h changes over all four areas' quarterly series published before O(t), at the true horizon h = q − (newest known quarter). |
| **KAL** | challenger | `hmodels.kalman("BL", t, 2, (NCR, BL, VIS, MIN))` |

**Kalman details:**

- latent AR(1) around each area's mean of known quarters;
- φ and τ² by maximum likelihood (Nelder–Mead, 3 fixed starts), pooled over areas with ≥ 8 known quarters, refitted at every issue;
- each quarter's sampling variance = mean (MoE/1.96)² of its rounds / number of rounds, with a missing MoE = 6.0;
- quarters with no round are bridged by prediction steps;
- the predictive variance adds the newest known quarter's sampling variance.

Both models use only SWS rounds with published date < O(t), from the project series plus the overlay. Neither model is retuned. If a future code change alters either output, the change is an addendum and the old specification stays the primary one.

**Threshold.** Class HIGH if probability ≥ 0.50. Note that PERS = 0.50 exactly when x_last = 11.3, which gives HIGH.

## 4. Issuance and sealing

- Script: `y16_kalman_prospective/runner/issue.py --issue YYYY-MM-DD`.
- A seal is valid only if written within the window [O(t), O(t) + 7 days], local date Asia/Manila. The information cutoff stays "published < O(t)", whenever in the window it is written.
- Outside the window the script refuses, unless `--dry-run`, which writes to `dry_runs/`, never to `prospective/`.
- **Each seal records:**
  - issue date, origin, target;
  - UTC and Manila write times;
  - window validity;
  - newest SWS round used (quarter, value, published date);
  - both probabilities and classes;
  - model identifiers and model version (SHA-256 of `hmodels.py`, `rlib.py` and `issue.py`);
  - plan hash, git HEAD;
  - SHA-256 of every input file, overlay included.
- Seals are append-only: files are named by issue date and UTC time, and existing files are never overwritten. A new line in `prospective/SEALS.txt` holds each file's SHA-256.
- **A missed window is recorded as missed and never backfilled.**
- Y14's `issue_forecast.py` and its outputs are not modified.

## 5. Evaluation

**Script:** `runner/evaluate.py`. It reads valid seals and resolved outcomes only, and pairs both models on the same issue dates.

**Per model:** n, prevalence, confusion matrix, accuracy, balanced accuracy, precision, recall, specificity, F1, AUC (if both classes), Brier score, calibration (bins; slope when n ≥ 10 and both classes).

**Paired comparison:**

- d_i = Brier_KAL,i − Brier_PERS,i;
- mean d with a bootstrap 95% CI (quarters resampled, B = 5000, seed 2036);
- one-sided bootstrap p (H0: mean d ≥ 0);
- exact one-sided sign test on the non-zero d_i.

Each quarter is one independent observation. No provincial replication.

**Primary analysis:** once, when **20 target quarters** have resolved (2027-Q2 .. 2032-Q1, expected about 2032-07-29). Superiority is claimed only if:

- one-sided bootstrap p < 0.05;
- the 95% CI excludes 0;
- the sign test p < 0.10.

A lower mean Brier alone is never reported as superiority.

**Interim looks:**

- after 8 resolved quarters: descriptive only, for data integrity, no hypothesis test;
- after every new outcome: an integrity check (resolution, overlay entries), with no metric reported.

**No early stopping for efficacy. No model change after seeing outcomes.**

**Seven reliability rules.** R1–R7 as applied to regional Lead-2 targets by `FIRI_LEAD2_FEASIBILITY/runner/score_firi_l2.rules`, unchanged:

| Rule | Definition |
|---|---|
| R1 | ≥ 10 quarters and ≥ 40 rows |
| R2 | accuracy ≥ 0.75 |
| R3 | balanced accuracy ≥ 0.70 |
| R4 | accuracy > always-LOW and > PERSIST |
| R5 | Brier < H1 and < CLIM, one-sided p < 0.10 |
| R6 | precision and recall ≥ 0.60 |
| R7 | each third ≥ 0.60, and leave-one-quarter-out min ≥ 0.70 |

They are reported for **both** models at the primary analysis, and again at 40 resolved quarters (secondary, about 2037).

- **R1 cannot pass before 40 resolved quarters.** It is reported as FAIL until then and not reinterpreted.
- PERS is itself the H1 comparator in R5, so R5 for PERS is undefined and reported as such.
- CLIM = the expanding share of BL quarters > 11.3 among outcomes published before O(t).
- Nothing in this plan changes R1–R7 or the 0.50 threshold.

**Missing data:**

- a missed issuance: excluded from both, counted;
- a model returning NaN: recorded as no forecast; the quarter is excluded from the paired comparison, counted;
- a missing outcome: excluded, counted.

None is ever imputed.

**Integrity.** Every seal's SHA-256 must match `SEALS.txt` before evaluation. The overlay is append-only: each evaluation hashes it and checks that earlier rows are unchanged against the copy recorded in each seal.

## 6. Tests (before the first valid issue)

`y16_kalman_prospective/tests/` covers:

- **issue → target mapping**;
- **no future data:** rounds published on or after O(t) leave both forecasts unchanged;
- **missing observations:** gaps still give finite probabilities in (0, 1);
- **reproducibility:** identical outputs on repeated runs;
- **historical parity:** with an empty overlay, the issuance code gives the same values as Y15's `dev_rows.csv` (KAL, H1);
- **output integrity:** required fields, hash recorded, no overwrite, refusal outside the window, dry runs isolated;
- **evaluation:** pairing, exclusion and sign-test arithmetic on synthetic inputs.
