# Q4 2026 Forecast Correction Report

- **Branch:** `aiPHeed/final-model-completion-20261113`
- **Date:** 14 November 2026
- **Owner decisions (chat, 14 Nov 2026):**
  - Correct the Q4 2026 forecast with strict data-availability rules.
  - "The data updates that will be used for forecast must happen every 10th day of the month."
  - Chosen option: **monthly re-forecast on the 10th**.

## 1. Summary

| | Original | Corrected (active) |
|---|---|---|
| Issue id | `2026-Q4` | `2026-11` |
| Forecast origin (information cut-off, exclusive) | **1 Nov 2026 00:00 PHT** (old quarterly rule) | **10 Nov 2026 00:00 PHT** (monthly rule, the 10th) |
| Generated | 2026-11-13T15:20:58Z | 2026-11-14T00:19:15Z |
| Model | FINAL `final-rate-mind-1.0`, frozen artifact sha256 `e1f8675f…` | same artifact, same 23 inputs, same preprocessing, MIND missing-value handling, calibration and thresholds |
| Data rule actually applied | figures **downloaded by 8 Nov** counted as available on 1 Nov (E168 refresh rule) | strict: only figures online before 10 Nov |
| Status | **superseded** (kept unchanged) | **active, served** |

**Result:** every corrected forecast is identical to the original: Δ = 0.0 in share, P(HIGH), every input value used and every SHAP value. The original issue broke its *stated* rule (data published before 1 Nov). Under the owner's 10th-of-the-month rule, the two late releases (October CPI on 5 Nov; September LFS on 6 Nov) are genuinely available, so the same values enter the same model.

## 2. The late observations, verified

The publication dates below come from PSA releases and press coverage. "Downloaded" is the first date the observation was in this system's download (`app.e168.live_data.first_seen`).

| Observation | Value used (national / Batangas) | PSA release | Downloaded | Available at 1 Nov? | Available at 10 Nov? | Used by |
|---|---|---|---|---|---|---|
| CPI, October 2026 | national headline 7.8%, food 6.4%; Batangas food inflation 2.04% | **5 Nov 2026** | 8 Nov 2026 | **No** | Yes | original and corrected |
| LFS unemployment, September 2026 | 5.4% (model value 5.386) | **6 Nov 2026** | 8 Nov 2026 | **No** | Yes | original and corrected |
| CPI, September 2026 | headline 7.2% | 6 Oct 2026 | 8 Nov 2026 | Yes | Yes | (earlier months of the CPI series) |
| LFS unemployment, August 2026 | 5.3% | 7 Oct 2026 | 8 Nov 2026 | Yes | Yes | (earlier month of the LFS series) |

Sources:
- [PSA September 2026 inflation summary](https://psa.gov.ph/content/summary-inflation-report-consumer-price-index-2018100-september-2026)
- [BusinessWorld, October inflation (5 Nov 2026)](https://bworldonline.com/top-stories/2026/11/05/791633/philippine-inflation-hits-fresh-peak-of-7-8-in-october/)
- [GMA, October inflation](https://www.gmanetwork.com/news/money/economy/1008340/inflation-rises-to-7-8-in-october/story/)
- [PSA, August 2026 unemployment](https://psa.gov.ph/content/unemployment-rate-declined-53-percent-august-2026)
- [Manila Times, September unemployment (6 Nov 2026)](https://www.manilatimes.net/2026/11/06/news/unemployment-rate-rises-to-54-in-september/2463733)
- [BusinessMirror, September unemployment](https://businessmirror.com.ph/2026/11/06/psa-unemployment-rises-to-5-4-in-september/)

**Inputs affected:**
- The October CPI feeds `cpi_food_yoy`, `cpi_food_3m`, `cpi_food_rel_nat`, `cpi_since` and the missing flag `mi_cpi_food_accel`.
- The September LFS feeds `unemp_rate`.
- All five provinces and both target quarters (2027-Q1, 2027-Q2) used them. That is all 10 forecasts.

**Other sources:**
- **Harvests:** use a 45-day publication rule (Q3 2025–Q2 2026); not affected.
- **Rainfall, soil and typhoons (NASA POWER, IBTrACS):** periods end before the cut-off.
- **Local prices:** May–Jul.
- **GRDP:** 2025, released April 2026.
- **News:** stories published 1 Aug–31 Oct.
- **ONI:** context only, not an input.

## 3. How the correction was made

1. **Original preserved.**
   - `data/final/issues/2026-Q4/` is untouched; every file matches its manifest hash (test).
   - Its 10 ledger records are unchanged.
   - The seven input files it was built from are copied to `data/final/corrections/2026-Q4/original_input_files/` (hash-checked against the original manifest).
   - The exact inference rows are in `original_inputs.csv` (10 rows × 166 inputs).
2. **Monthly rule** (`app/final/period.py`, `serving.json → issue_rule {"cadence": "monthly", "day": 10}`).
   - Issue ids are `YYYY-MM`; the issue moment is the 10th at 00:00 PHT, exclusive.
   - Leads count from the quarter containing the issue date: 10 Nov 2026 → targets 2027-Q1 and 2027-Q2; 10 Jan 2027 → 2027-Q2 and 2027-Q3.
   - The legacy id `2026-Q4` keeps its own rule (1 Nov).
3. **Strict panel rebuild at 10 Nov 2026.** The cycle's data steps were run with `AIPHEED_LIVE_ASOF=2026-11-10` and no published-by override:
   - `app.e168.live_refresh.rebuild_panels`, run with 2 workers; with 8 it ran out of memory;
   - then `app.hcw.inputs`.
   - Only the live quarter's rows changed; historical rows are identical (0 columns changed).
   - Changed inputs: `sws_last`, `d_sws`, `vu_dry6`, `vu_rain12`, `vu_tc_wind`, `vu_tc_strong` (their windows are measured from the cut-off), plus typhoon counts for 36 areas outside CALABARZON. **None is among FINAL's 23 selected inputs.**
4. **News not re-collected.** The raw news archive is not in this checkout, so stories from 1–9 Nov 2026 were not collected. The corrected issue uses the original news inputs (stories published 1 Aug–31 Oct, all before 10 Nov). This is stated in its `news_used.json` and `live.json` (`news_window`), and the dashboard shows "News: Aug–Oct 2026". Nothing was filled in for those days.
5. **Corrected issue built** (`python -m app.final.correction run`).
   - `issue.check_information_rule` passed: cut-off 10 Nov, published-by = cut-off.
   - The frozen model's training-row fingerprint matched, so no retraining was needed.
   - The issue folder `data/final/issues/2026-11/` now also stores `inputs.csv` (its own input snapshot).
6. **Ledger.** 10 new forecast records were added, plus one append-only `superseded` record. It names the replacement (`2026-11`), the reason, who decided (owner instruction in chat, 14 Nov 2026) and the evidence. The chain verifies (21 records).
7. **Database mirror.** The new table `final_forecast_supersessions` (Alembic `a7b8c9d0e1f2`) is insert-only. Active forecasts are those whose issue has no supersession row.

## 4. Original vs corrected forecasts

| Province | Target | Original share | Corrected share | Δ | Original P(HIGH) | Corrected P(HIGH) | Class (both) |
|---|---|---|---|---|---|---|---|
| Batangas | 2027-Q1 | 23.2% | 23.2% | 0.0 | 0.0019 | 0.0019 | LOW |
| Cavite | 2027-Q1 | 24.3% | 24.3% | 0.0 | 0.0029 | 0.0029 | LOW |
| Laguna | 2027-Q1 | 23.7% | 23.7% | 0.0 | 0.0022 | 0.0022 | LOW |
| Quezon | 2027-Q1 | 26.8% | 26.8% | 0.0 | 0.0072 | 0.0072 | LOW |
| Rizal | 2027-Q1 | 24.6% | 24.6% | 0.0 | 0.0033 | 0.0033 | LOW |
| Batangas | 2027-Q2 | 23.0% | 23.0% | 0.0 | 0.0017 | 0.0017 | LOW |
| Cavite | 2027-Q2 | 24.1% | 24.1% | 0.0 | 0.0027 | 0.0027 | LOW |
| Laguna | 2027-Q2 | 23.5% | 23.5% | 0.0 | 0.0021 | 0.0021 | LOW |
| Quezon | 2027-Q2 | 26.6% | 26.6% | 0.0 | 0.0068 | 0.0068 | LOW |
| Rizal | 2027-Q2 | 24.4% | 24.4% | 0.0 | 0.0030 | 0.0030 | LOW |
| CALABARZON mean | 2027-Q1 / Q2 | 24.52% / 24.32% | 24.52% / 24.32% | 0.0 | | | LOW |

Unrounded: max |Δ μ| = 0.0 logit; max |Δ P(HIGH)| = 0.0. Every input value used and every SHAP value: max |Δ| = 0.0. The SHAP files are byte-identical.

**What a strict 1 November origin would have meant** (not issued; the owner chose the 10th): removing every affected input entirely moves each province by at most 1.9 points (Batangas 21.4–25.1%), and every class stays LOW (`FULL_SYSTEM_AUDIT_REPORT.md` §4).

## 5. What users and administrators see

- **Dashboard ("About this forecast"):**
  - "forecast issued 10 November 2026";
  - "Data published up to 9 November 2026";
  - Food prices Oct 2026; Unemployment Sep 2026; News Aug–Oct 2026;
  - "next forecast 10 December 2026".
- **Forecast history (newest first, ordered by issue date):**
  - "Issued 10 November 2026 · CURRENT ISSUE";
  - below it, "Issued Q4 2026" struck through, labelled **SUPERSEDED**, with the reason and "Replaced by the forecast issued 10 November 2026. Kept here unchanged for the record; its values are not used on the map."
  - The two versions are never mixed: map, PDFs and explanations read only the active issue.
- **API:**
  - `/final/forecast-history` returns `record_status`, `superseded_by`, `issue_label`, `issue_date`, `issues_newest_first` and `superseded{…}`;
  - `/forecast-period` returns `cadence: monthly` and `served_issue_label`;
  - the outlook returns `data_published_by: 2026-11-10`, with no disclosure needed.
- **Wording:** "updated automatically on the 10th of every month" on the landing page, glossary ("Updated monthly"), About, PDFs and tours.

## 6. Bug found and fixed while verifying

**A scheduled issue would have failed while the dashboard was serving.**
- **Cause:** `app.hcw.serve._rows` read its input panel through `OUT`, which the serving layer re-points at the served issue folder.
- **Effect:** the in-app scheduler runs in the same process, so the 10 December forecast would have stopped with `FileNotFoundError`.
- **Fix:** the input panel is read from its fixed path (`CAND_PANEL`). Covered by `test_corrected_forecast_regenerates_exactly`, which builds while serving.

## 7. Tests

| Command | Result |
|---|---|
| `cd backend; python -m pytest tests/unit/test_final_realtime.py -q` | **55 passed** (3 min 25 s; one test re-runs the full inference) |
| `cd frontend; npx vitest run` | **102 passed** |
| `npx tsc --noEmit -p .` | clean |
| `PYTHONPATH=. python ../research_notes/audit_20261114/trace_end_to_end.py` | **34 / 34** on the served 2026-11 issue (re-prediction exact, ledger 21 records intact, APIs = issue) |

New or changed tests in `backend/tests/unit/test_final_realtime.py`:

| Requirement | Test |
|---|---|
| Publication-date eligibility | `test_publication_date_eligibility` (Oct CPI / Sep LFS refused at 1 Nov, accepted at 10 Nov; an unfinished month never counts) |
| Late CPI/LFS exclusion at the original origin | same, plus `test_an_issue_cannot_use_figures_published_after_its_cut_off` |
| Monthly rule, every quarter transition, year change, PHT | `test_monthly_issue_on_the_10th` (8 cases), `test_legacy_quarterly_ids_keep_their_own_rule` |
| Corrected forecast generation | `test_corrected_issue_uses_only_eligible_data_and_the_approved_model`, `test_corrected_forecast_regenerates_exactly` |
| Original forecast preservation | `test_original_issue_preserved_and_superseded` (issue files, manifest, input files and rows, ledger values) |
| Superseded status, database | `test_supersession_rules`, `test_database_mirror_carries_the_supersession` |
| History ordering, no duplicate active forecasts | `test_no_duplicate_active_forecasts_and_history_order` |
| Corrected API responses | `test_served_api_is_the_corrected_issue` (issue, cut-off, data periods) |
| Frontend rendering | `forecastHistory.test.tsx`: "puts the corrected 10 November 2026 issue first and keeps the original marked superseded" |

## 8. Limitations

- **Validation timing:** FINAL was validated with issues on the 1st of each quarter's second month. Monthly issues on the 10th of other months use the same model and lead definition, but have more or less information than in validation, and have not been validated separately (`serving.json → cadence_caveat`).
- **News gap:** the corrected issue has no news from 1–9 Nov 2026 (not collected). Future monthly cycles collect news up to their cut-off when the raw news archive is present (REMAINING_ISSUES L7).
- **Data stage memory:** with 8 workers the panel rebuild ran out of memory on this PC. It now defaults to 2 (`AIPHEED_DATA_JOBS`); a full scheduled data stage with news collection has not been run end to end since.
- **Production registry:** FINAL is still not the registered production model; the live site serves E196 (REMAINING_ISSUES R2).
