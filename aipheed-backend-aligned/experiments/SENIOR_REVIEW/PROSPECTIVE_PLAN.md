# Prospective protocol: scoring sealed 2027+ forecasts of the food-insecurity model with R1–R7

**Written:** 2026-11-03, before any 2027+ target quarter has an SWS round. Fixed now. The SHA-256 of this file is computed
over every byte before its last line, which begins `PLAN-SHA256:`; the scoring script refuses to run if it changed.

**Why this exists.** On development evidence (2010-Q1..2026-Q3, every quarter examined during development), REF+news
fails R3, R5 and R7 at Leads 1–2. No pipeline error explains it (`AUDIT.md`), and the planned improvement attempts
failed (`../RELIABLE_L12/`, `../RELIABLE_NEWINFO/`). **The only clean test left is prospective:** forecasts sealed before
their outcome exists, scored with the unchanged rules.

## 1. What is forecast and sealed

| Item | Fixed rule |
|---|---|
| **Model** | REF+news, **the procedure frozen, not the fitted trees**: at each new origin t, the walk-forward refit of OPTION_1 (`OPTION_1/runner/run_option1.py` `_origin`, columns `iv2_lib.cols(False, True)`, the IMPROVE_V2 grid, inner selection, LightGBM settings and seed), run on all data published before O(t) under the same release rules (`HISTORY_RETRAIN` PLAN §1; SWS rounds only if `published < O(t)`; CPI, ONI and Pink Sheet to month 2 of quarter t; production to quarter t−1; E112 news only if `last_published < O(t)`). Code commit and input-file hashes are recorded in every seal. **No change to the code, columns, settings, threshold (0.50) or release rules is allowed.** Data refreshes from the same sources are allowed; a source that disappears makes its columns NaN, recorded in the seal |
| **Comparator, sealed beside it** | REF (no news), the same procedure without the news columns, reported, never used for the verdict |
| **Issue dates** | O(t) = the first day of each quarter, from **2027-01-01** |
| **Leads** | 1 and 2 (target = origin quarter + 1 and + 2). Target quarters 2027-Q1 onward |
| **Baselines sealed with each forecast** | PERSIST-SI = 1 if the latest BL reading published before O(t) is > 11.3, else 0. CLIM = the share of HIGH among BL quarters whose every non-commissioned round was published before O(t), 1998-Q3 onward (both exactly as in IMPROVE_V2) |
| **Sealing** | One **new** file per issue date, `prospective/sealed_<issue date>.csv`, with: issue date, origin, lead, target, P(HIGH) for REF+news and REF, class at 0.50, PERSIST-SI, CLIM, the newest SWS round used and its publication date, the code commit and input hashes. Its SHA-256 is appended to `prospective/SEAL_LEDGER.md` and the file and ledger are committed **within 14 days of the issue date and always before any SWS round of the target quarter is published**. A sealed file is never edited |
| **Missed seals** | A forecast not sealed in time is **missing** for that lead: never back-filled or re-issued. The count of missed seals is reported at every scoring |
| **The 2027-Q1 Lead-2 forecast already sealed** | `OPTION_1/sealed_prospective_REFNEWS.csv` (SHA-256 `cc1ff11b…5216`, issued 2026-10-01, P 0.869, HIGH; sealed after the development results were known, before its outcome). **It counts** as the first Lead-2 row. It carries PERSIST-SI (1.0) but no CLIM: CLIM for it is computed by the §1 rule from labels published before 2026-10-01, a deterministic quantity |

## 2. Labels (exactly the development definition)

- y(q) = 1 when the mean of SWS Balance Luzon involuntary hunger over the **non-commissioned** rounds of q is **> 11.3**,
  else 0 (11.3 exactly is LOW).
- A round belongs to the quarter in which its **fieldwork starts** (SWS's survey-quarter name; `AUDIT.md` A3/A6).
- Values are SWS's **first published** figures; later revisions are not used.
- A quarter is labelled only when **all** its non-commissioned rounds are published. A quarter with no round has **no
  label and is skipped**, never imputed.
- **No quarter is excluded** for survey mode, sample size or methodology changes (e.g. a larger BL sample). Such changes
  are listed in each report as notes and may be shown as sensitivity, never used for the verdict.

## 3. Scoring

- **Code:** the frozen R1–R7 (`P0H4_LEAD12_REVIEW/runner/reproduce.py` `rules()` through `HISTORY_RETRAIN/runner/hr_lib.py`
  `evaluate`), unedited, at the commit recorded in the first prospective report. Its behaviour must match `AUDIT.md`
  D1 (an independent recomputation is run each time and must agree, or nothing is reported).
- **Rows:** prospective sealed rows only, each lead separately. **One row per target quarter** (the forecast is
  regional; the five province copies are never counted as rows).
- **Reported at every scoring:** n labelled quarters per lead; accuracy, balanced accuracy, precision, recall, F1,
  AUC (when both classes occur), Brier; every R1–R7 value; the paper's 75% rule (Algorithm 3, mean of one-quarter folds
  = accuracy) with a 90% Wilson interval; REF beside REF+news; missed seals.
- **Scoring dates:** once a year, on **1 March** from 2028 (after the Q4 round is usually published), using every
  quarter labelled by then.

## 4. Minimum number of quarters (fixed by the unchanged rules)

- **R1 requires ≥ 10 quarters and ≥ 40 rows.** With one row per quarter, this means **≥ 40 labelled prospective quarters
  per lead**. With every quarter labelled, Lead 1 reaches 40 with target 2036-Q4 and Lead 2 with target 2036-Q4 as well
  (its first row is 2027-Q1). SWS skips some quarters (5 of 67 in 2010–2026), so expect **2037–2038**.
- **R7** splits the quarters into thirds, so at 40 quarters each third holds 13–14.
- No interim R1–R7 verdict is possible before that; this is stated in every report.

## 5. Decision rule (fixed now)

1. **Before 40 labelled prospective quarters at a lead:** status **"insufficient prospective evidence"**. The model is
   never called reliable or unreliable under R1–R7 on fewer quarters. The paper's 75% rule is reported descriptively
   with its interval.
2. **Single look.** The R1–R7 verdict is taken **once**, at the first annual scoring date at which **both** Lead 1 and
   Lead 2 have ≥ 40 labelled prospective quarters, on all quarters labelled by then.
   - **Lead 1 reliable** if all of R1–R7 pass at Lead 1.
   - **Lead 2 reliable** only if all of R1–R7 pass at Lead 2 **and** Lead 1 is reliable (the Maximum Reliable Lead
     Time definition, protocol §7).
   - Otherwise **"not reliable on prospective evidence"** at that lead.
   - Later scorings are reported but **do not change the verdict**; a new verdict would need a new protocol.
3. **Review trigger (not a verdict, never early success).** At any annual scoring with ≥ 20 labelled quarters at a lead,
   if REF+news accuracy is **below PERSIST-SI accuracy** and its Brier is worse than PERSIST-SI with one-sided
   cluster-bootstrap p < 0.05 (seed 2036, 5000 draws), the report flags **"underperforming persistence: review the
   served model"**. Serving decisions remain the team's and the adviser's; this protocol does not change the served
   model.
4. **REF (no news)** is scored the same way and reported beside REF+news. It **cannot** replace REF+news in the verdict;
   a switch would need a separate decision, stated as such.

## 6. What is not allowed

Retuning, new inputs, a different threshold, recalibration, dropping or re-labelling quarters, changing any R1–R7
rule, changing the scoring dates or the single look, and re-issuing or editing a sealed forecast. Any departure makes the
result exploratory and must be labelled so.

## 7. Files

| File | Content |
|---|---|
| `prospective/SEAL_LEDGER.md` | Ledger: one row per sealed file with its SHA-256 (started at the first 2027 issue) |
| `prospective/sealed_<issue date>.csv` | One file per issue date |
| `prospective/score_<YYYY-03-01>.json` + `.md` | Annual scoring report |

The sealing and scoring scripts implement §1–§5 exactly. They are written before the first 2027 issue date and
committed with their hashes in the ledger; they do not change this protocol.
PLAN-SHA256: 194ecb725113908eb58b26d5e37c7f96d9bd5235a2ce8183ce618c0544b6224c
