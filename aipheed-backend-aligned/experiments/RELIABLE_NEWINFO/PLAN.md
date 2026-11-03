# RELIABLE_NEWINFO: the last attempt to pass R1–R7 at Leads 1 and 2 (EXPLORATORY)

**Written:** 2026-11-03, after Step 0 (`STEP0_SOURCES.md`, commit `b256279`) and before any rainfall value was
downloaded or any candidate was fitted or scored.

**Label: EXPLORATORY.**

**Evidence status, stated plainly.**
- Every target quarter scored here (2010-Q1..2026-Q3) was examined before. This is **development evidence**.
- **This is the last attempt.** Exactly two candidates are tried, and nothing is added later.
- Any pass must be confirmed on sealed 2027+ forecasts before it is called reliable.

**Target, unchanged:** y(q) = 1 when SWS Balance Luzon involuntary hunger H(q) > 11.3% (the quarter mean of
non-commissioned rounds), else 0. It uses the same labels (`iv2_lib.area_labels`, BL) and the same verdict window as
IMPROVE_V2, OPTION_1 and RELIABLE_L12.

**What this does not change:**
- the frontend, `backend/`, the served model;
- every existing result, seal and ledger;
- IMPROVE_V2, IMPROVE_V2_LEADS, OPTION_1, RELIABLE_L12 and every P0H4 file.

They are read or imported read only. New files go under `aipheed-backend-aligned/experiments/RELIABLE_NEWINFO/`.
Nothing is pushed to GitHub; commits are local only.

**Hash.** The SHA-256 of this file is computed over every byte before its last line, which begins `PLAN-SHA256:`.
`runner/run_newinfo.py` refuses to run if the file changed after hashing.

**What was seen before this plan:**
- every published result of IMPROVE_V2, IMPROVE_V2_LEADS, OPTION_1 and RELIABLE_L12;
- the Step-0 diagnosis: 8 of REF's 9 errors in 2015-Q2..2020-Q4 are readings within SWS's ±5.7-point sampling margin of
  11.3%, and R7 needs one more correct quarter in that third;
- one test request of 2026 CHIRPS daily values from ClimateSERV, checking the service only (not used, not kept);
- the coverage of `pi_H4L`: no missing value in the verdict window;
- the SWS `mode` column (2020-Q2..Q4 are mobile-phone rounds).

**A blend computed before this plan, reported here: 0.5 × REF + 0.5 × the 0/1 PERSIST baseline.** PERSIST is 0 or 1,
so this blend's call equals persistence's call in 62 of 62 quarters at both leads. Its accuracy is therefore 0.661,
and it **fails R2 and R4 by construction**. It is not a candidate. C1 uses the probability form `pi_H4L` instead,
which was **not** computed in any blend before this plan.

## 1. Candidates (exactly two)

| | Definition | Fitted? |
|---|---|---|
| **C1 BLEND** | p = 0.5 × p_REF + 0.5 × `pi_H4L`, at the same origin and lead. p_REF is the stored REF walk-forward forecast (`IMPROVE_V2_LEADS/out/forecasts_leads.csv`). `pi_H4L` is the IMPROVE_V2 persistence probability: P(H(t+k) > 11.3) from the latest published BL reading, with σ the four-area pooled random-walk RMSE at that horizon. It is read from `IMPROVE_V2/out/table_pooled.csv` (BL, same t and lead). The weight is fixed at 0.5/0.5 | No |
| **C2 REF + rainfall** | REF (no news), refitted walk-forward with **two added columns**, `RF_z3` and `RF_z6` (§2). Same training rows, eligibility rule, 8-setting grid, inner chronological selection (`hr_lib.lgbm_select`), LightGBM settings and seed as IMPROVE_V2 REF. It uses IMPROVE_V2's code (`iv2_lib`, `run_iv2`, `hr_lib`), imported read only. Origins 1998-Q3..2026-Q3 (`iv2_lib.ORIGINS`); training rows stack leads 1–15, as served; test Leads 1–2 | Yes |

**Machinery check before C2 is scored.** The same refit code with the REF column list (no rainfall) must reproduce the
stored REF Lead-1 and Lead-2 forecasts (max |Δp| ≤ 1e-12, the same configuration at every origin). Otherwise C2 is not
scored.

## 2. CHIRPS rainfall (C2's new information)

**Source.** CHIRPS daily rainfall (the Climate Hazards Center UCSB product, as served by SERVIR ClimateSERV,
`climateserv.servirglobal.net/api`, datatype 0). Requested as the area average over the box **120.6–122.5°E,
13.6–14.9°N**, which approximates CALABARZON.
- The box leaves out Quezon's Bondoc Peninsula, south of 13.6°N.
- It includes southern Metro Manila, Laguna de Bay and part of Polillo.
- Sea cells are NaN in CHIRPS and do not count.

**Download.** Daily values 1981-01-01..2026-09-30, fetched once by `runner/fetch_chirps.py`.
- The raw JSON responses and a monthly-total CSV are stored with their SHA-256.
- The CHIRPS version reported by the service is recorded.
- The values are **today's vintage**, not what was available at each past issue date (the same caveat as the other
  inputs). This is disclosed.

**Publication rule** (only data published before each issue date). The final CHIRPS monthly product appears after
about the 20th of month m+1. Month m is therefore usable at issue date O(t) only if **O(t) ≥ the first day of month
m+2**. For O(t) on the first day of quarter t+1, the newest usable month is the second month of quarter t (the same rule
as PSA CPI in IMPROVE_V2).

**Features, fixed now.** Let M be the newest usable month at O(t).
- `RF_z3` = (rainfall total of months M−2..M − its mean) / its SD, ddof = 1.
- `RF_z6` = the same for months M−5..M.
- The mean and SD are those of the same calendar window in the **base years 1981–1997**, all before the first origin
  (1998-Q3), so no later data enters the standardization.
- A month with no data makes the feature NaN (LightGBM handles NaN as IMPROVE_V2 does).
- The values are the same for every lead of an origin, as for the other non-hunger columns.

## 3. Scoring

The frame is the OPTION_1 / RELIABLE_L12 one: `run_iv2.frame` with BL labels and the PERSIST-SI, CLIM and ALWAYS-LOW
baselines from `IMPROVE_V2_LEADS`.
- **Rules.** The frozen R1–R7 through `hr_lib.evaluate`, unedited, at threshold 0.50, on each candidate's own
  probabilities.
- **Window.** Targets 2010-Q1..2026-Q3, labelled quarters only, Leads 1 and 2.
- **Reported per candidate and lead:**
  - accuracy, balanced accuracy, precision, recall, F1, AUC, Brier, TP/FP/FN/TN;
  - each of R1–R7 with its values;
  - REF at 0.50 beside them as the reference.
- For C2, the SHAP share of the two rainfall columns.

**Sensitivity only (never used for the decision).** The same metrics and R1–R7 without the target quarters whose SWS
rounds were mobile-phone surveys: 2020-Q2, Q3 and Q4, from the SWS `mode` column. The decision uses the full window.

## 4. Selection rule (fixed now)

1. A candidate passes only if **all of R1–R7 pass at both Lead 1 and Lead 2** (full window).
2. If both pass, the lower Brier (the mean of Leads 1 and 2) wins. If they tie, C1 wins, as the simpler one.
3. If neither passes, nothing changes: REF+news stays the main model under the paper's 75% rule. This closes the
   attempts to pass R1–R7. No further variant is tried.

A passing candidate is a finding, not a deployment. Serving it needs a separate plan and your approval.

## 5. Seal (only if a candidate passes)

**What is sealed.** The chosen candidate's forecasts issued 2026-10-01 (origin 2026-Q3): 2026-Q4 at Lead 1 and
2027-Q1 at Lead 2, each with its probability, class and the newest SWS round used.

**Where.** A **new** file, `RELIABLE_NEWINFO/sealed_prospective_NEWINFO.csv`, with its SHA-256 in a new
`RELIABLE_NEWINFO/SEAL_LEDGER.md`. No existing seal is touched.

**Labels.** Both files are labelled "sealed after the development results were known; prospective, not an independent
test".

**If nothing passes,** nothing is sealed.

## 6. Outputs

| File | Content |
|---|---|
| `runner/fetch_chirps.py` | `data/chirps_raw/*.json`, `data/chirps_monthly.csv`, hashes |
| `runner/run_newinfo.py` | `features`, `fit`, `score`, `seal` |
| `out/rain_features.csv` | `RF_z3` and `RF_z6` per origin, with the newest usable month |
| `out/forecasts_c2.csv` | C2 forecasts, plus the REF reproduction rows |
| `out/checks.json` | Reproduction, hashes, publication-rule checks |
| `out/results.json` | §3 and §4 |
| `RESULTS.md` | In plain words |
PLAN-SHA256: ffb69ae23899608e0697333a3551cc3adec5f2bc09eaa5005b3c8d1ba1c12cb3
