# OLD_NEWS: REF + GDELT news categories, the last attempt to pass R1–R7 at Leads 1 and 2 (EXPLORATORY)

**Written:** 2026-11-03, after `FEASIBILITY.md` (commit `b087b4e`) and **before** the 2015–2020 GDELT scan, before any
2015–2020 feature value exists, and before the candidate is fitted or scored.

**Label: EXPLORATORY.**

**Evidence status, stated plainly.**
- Every target quarter scored here (2010-Q1..2026-Q3) was examined before. This is **development evidence**.
- **This is the last attempt:** one candidate, nothing added later.
- Any pass must be confirmed on sealed 2027+ forecasts (`../SENIOR_REVIEW/PROSPECTIVE_PLAN.md`) before it is called
  reliable.

**What is already known:**
- E85 found no predictive value for GDELT event signals on 2021–2026.
- News inside REF+news is 2.8% of SHAP influence.
- REF fails only R7, and its 2015-Q2..2020-Q4 third is 12/21 correct. R7 needs 13.
- The 2015–2020 errors are mostly readings within the SWS sampling margin of 11.3% (`../RELIABLE_NEWINFO/STEP0_SOURCES.md`).

**What this does not change:**
- the frontend, `backend/`, the served model;
- every existing result, seal and ledger;
- E85, IMPROVE_V2, IMPROVE_V2_LEADS, OPTION_1, RELIABLE_* and SENIOR_REVIEW.

They are read or imported read only. New files go under `OLD_NEWS/`, plus the git-ignored raw file of §2. Nothing is
pushed to GitHub; commits are local only.

**Hash.** The SHA-256 of this file is computed over every byte before its last line, which begins `PLAN-SHA256:`. Every
runner refuses to run if the file changed after hashing.

## 1. The candidate (exactly one)

| Item | Fixed |
|---|---|
| **Model** | **REF + G**: IMPROVE_V2 REF (no news; `iv2_lib.cols(False, False)`) with the **15 regional E85 GDELT columns** added before `lead`: `g_logn`, `g_tone`, `g_affected`, `g_share_{PRICE, FOODSEC, DISASTER, AGRI, LIVELIHOOD, RESPONSE}`, `g_d_{the same six}` (`e85_features.G_REGIONAL`). The province `gp_*` columns are not used, because the target is regional |
| **Settings** | Unchanged from IMPROVE_V2 REF: training rows (BL), eligibility, the 8-setting grid, inner chronological selection (`hr_lib.lgbm_select`), LightGBM settings, seed. Training rows stack leads 1–15; origins 1998-Q3..2026-Q3 (`iv2_lib.ORIGINS`); test Leads 1–2. The fit is OPTION_1's `_origin` with the column list swapped (as `RELIABLE_NEWINFO/runner/run_newinfo.py`) |
| **GDELT feature span** | Origins **2015-Q2..2026-Q3**. Before 2015-Q2 the 15 columns are **NaN**, as news is before 2021 in IMPROVE_V2. 2015-Q1 is NaN too, because GKG 2.1 starts on 2015-02-19 and that quarter is partial |
| **Machinery check before scoring** | The same refit code with REF's columns must reproduce the stored REF Lead-1 and Lead-2 forecasts: max \|Δp\| ≤ 1e-12, the same configuration at every origin. Otherwise nothing is scored |

## 2. The GDELT data (the scan you approved)

| Item | Fixed |
|---|---|
| **Query** | E85's **actual** query, `E85_GDELT_Events/runner/gdelt_query_v1.sql` (V1 `Themes`/`Locations` columns aliased as V2), with only the partition bounds changed to `_PARTITIONTIME >= '2015-02-18' AND < '2021-01-01'`. Stored as `data/gkg_v1_2015_2020.sql`; its SHA-256 is checked before running |
| **Bytes** | Dry run **995,515,666,287 bytes (0.905 TiB)**. The run sets `--maximum_bytes_billed=1000000000000`, so BigQuery refuses rather than bill more. The billed bytes are recorded from the job |
| **Retrieval** | Into a destination table in a new dataset `aipheed_old_news` (US) of your GCP project, then read with `bq head` pages (tabledata.list, **no rescan, no cost**). The rows are saved to `backend/data/gdelt_e85/gkg_calabarzon_2015_2020.parquet` (git-ignored, like E85's raw file), with the row count and SHA-256 recorded. The dataset is deleted after the hash is recorded. **If anything fails after the scan, the destination table is reused; the scan is never repeated without asking you** |
| **2021+ rows** | E85's stored file `gkg_calabarzon_2021_2026.parquet`, unchanged; its SHA-256 is recorded |

## 3. Features (E85 code unchanged, with one disclosed exception)

- `e85_features.features()` and `_agg()` are imported **unchanged**, with E85's families, κ = 20, tone and affected
  counts, the timing cut O(t) − 1 day, and the PHT conversion.
- **The one exception: `load()`.** It contains `assert d["ts"].min() >= pd.Timestamp("2021-01-01")`, E85's approved
  window.
  - The 2021+ file is loaded with E85's `load()` unchanged.
  - The 2015–2020 file is loaded with a **verbatim copy of `load()` without that one assertion**, reading the new file.
  - **Check, before any feature is built:** on the 2021+ file, the copy and the original return identical frames.
  - The two frames are concatenated and E85's de-duplication rule is re-applied across them (one record per
    `DocumentIdentifier`, the earliest).
- Features are computed for every origin 2015-Q2..2026-Q3 with `origin_of = e41_lib.origin` (O(t) = the first day of
  quarter t+1, as E85).
- **The values for 2021-Q2..2026-Q3 must equal E85's stored `gdelt_features_k1.csv`** (max |Δ| ≤ 1e-9). That checks
  that the added old rows do not change any 2021+ value. 2021-Q1, where `g_d_*` uses 2020-Q4, is reported, not
  required.
- **No volume adjustment** (E85's code is unchanged).
  - GDELT monitored about 3 times more articles per quarter in 2017–2020 than in 2021+, so `g_logn` and `g_affected`
    carry a volume shift. This is disclosed, not corrected.
  - The six share columns are the comparable ones (FEASIBILITY §4).

**Coverage checks, reported and never used to change anything:**
- records per quarter;
- each family's share of all CALABARZON-located records per year;
- the 2018-Q1..2019-Q2 level;
- the number of origins whose quarter has fewer than 20 records.

## 4. Scoring and decision (fixed now)

**Scoring.**
- The OPTION_1 frame (`run_iv2.frame`, BL labels, PERSIST-SI, CLIM and ALWAYS-LOW from IMPROVE_V2_LEADS).
- The frozen R1–R7 via `hr_lib.evaluate`, unedited, at 0.50.
- Targets 2010-Q1..2026-Q3, labelled quarters only, Leads 1 and 2.
- **Reported per lead:**
  - accuracy, balanced accuracy, precision, recall, F1, AUC, Brier, TP/FP/FN/TN;
  - every R1–R7 value;
  - REF beside it;
  - the SHAP share of the 15 GDELT columns;
  - the number of calls that differ from REF;
  - the middle-third (2015-Q2..2020-Q4) accuracy.

**Decision.**
1. **REF + G passes only if all of R1–R7 pass at both Lead 1 and Lead 2.**
2. If it passes: a finding, not a deployment. Its forecasts issued 2026-10-01 (2026-Q4 at Lead 1, 2027-Q1 at Lead 2)
   are sealed in a **new** file, `OLD_NEWS/sealed_prospective_OLDNEWS.csv`, with its SHA-256 in a new
   `OLD_NEWS/SEAL_LEDGER.md`, labelled "sealed after the development results were known". Serving it would need a
   separate plan and your approval.
3. If it fails: nothing changes. REF+news stays the main model under the paper's 75% rule. **The attempts to pass R1–R7
   on development data are closed;** only the prospective protocol remains.

## 5. Outputs

| File | Content |
|---|---|
| `runner/fetch_gkg.py` | The scan (after your OK), the destination table, paging, parquet, hashes |
| `runner/run_refg.py` | `features`, `fit`, `score`, `seal` |
| `out/gdelt_features_2015_2026.csv` | 15 regional columns per origin |
| `out/checks.json` | Plan, query and file hashes; billed bytes; the load-copy check; the 2021+ equality check; REF reproduction |
| `out/coverage.json` | §3 checks |
| `out/forecasts_refg.csv` | REF + G and the REF reproduction rows |
| `out/results.json` | §4 |
| `RESULTS.md` | In plain words |

## 6. Order of work

1. This plan is committed with its hash. **Stop for your OK.**
2. After your OK: the scan (§2), the features and checks (§3), the fit and machinery check (§1), scoring (§4), and the
   seal only if it passes. Then `RESULTS.md`, a local commit, and stop.
PLAN-SHA256: 0914a649b3c19158b08d36099a5092db14a9995eb9e67a0f35fa6521e0c97d61
