# Data Completeness, Label Timeline and Evaluation Design (2026-10-09)

**This audit was read-only.**

- No dataset was downloaded and no model was run.
- No production code or data, existing report, frozen forecast, thesis chapter or methodology was changed.
- Nothing was committed or deployed.

**New files only:**

- This report.
- Evidence in `evidence/2026-10-09_data_audit/`:
  - `source_completeness_2021_2026.json`
  - `label_publication_timeline.csv`
  - `frame_missingness.json`
  - `openstat_metadata_snapshot_2026-10-09.json` (OpenStat **metadata only**, SHA-256 `1bb12d06…`)
- The companion report `docs/DATA_COMPLETENESS_AUDIT_2026-10-09.md` (OpenStat table details and the news-geocoder check).

**Tags:** **[V]** verified from project files or official metadata · **[A]** assumption · **[U]** unresolved.

---

> **Corrections added 2026-10-09 (later the same day)** — see `docs/PUBLICATION_DATES_AND_RULE_L_2026-10-09.md`. (1) The 2026-Q1 **and 2026-Q2** Balance-Luzon values ARE stored in `docs/provenance/sws_hunger_sources.json` (only `sws_hunger.parquet` lacks them); statements below that they were not stored are wrong. (2) "19/20 correct" is a row-level binomial bound that assumes independent rows; the five provinces of a quarter share most inputs and the SWS term, so 19/20 would NOT by itself establish that true accuracy exceeds 75%. (3) The two 2021-Q2 (and 2022-Q2) values are two separate SWS surveys (May and June), not two articles about one survey.

## Summary

1. **Within 2021–2026 there are 16 labelled quarters (80 province-quarters)**, from 2021-Q2 to 2025-Q4 [V]. No quarter in that range is an untouched test set.
   - **2022-Q4 to 2025-Q4** has been used to compare and select models in earlier studies.
   - **2021-Q2 to 2022-Q3** cannot serve as a forecasting test, because anything before it is outside the window (and the earlier quarters are not labelled).
2. **The only credible independent test is the 2026 quarters**, scored with forecasts frozen before their labels enter the project.
   - A **March 2026 SWS round has been published**: the stored source URL for 2025-Q4 is an article titled "…from 20.1% in November 2025 to 23.2% in March 2026" [V].
   - Its Balance-Luzon value, and the 2026 provincial CPI needed for the label, are **not in the project** [V].
   - **At most 4 quarters (20 rows)** can exist within the window, and fewer if SWS skips rounds.
   - With 20 rows, a confident (one-sided 95%) claim of more than 75% requires **19/20 correct** under a row-independence assumption that does not hold here (see correction 2); even 19/20 would not by itself establish it. With 5 or 10 rows no result can support it [V, computed].
3. **Rule L needs two refinements before any new experiment:**
   - **(a) Two-round quarters.** Where the label averages two SWS rounds, the label is published with the **later** round, not the earlier.
   - **(b) CPI timing.** The label also needs the target quarter's last-month CPI, which is published after SWS in two cases.
   - Neither changes the 40 outer test rows. Both affect training-period folds.
4. **The monthly CPI and rice sources exist and cover 2021–2026** (metadata) [V]. The project holds **no monthly values** [V], and **per-month publication dates cannot be established** from the tables or from automated access to psa.gov.ph, which is blocked by bot verification [V].

## 1. Data completeness, 2021-Q1 to 2026-Q4

**Notes on reading the table:**

- **Span** is the range of quarters the table covers within 2021–2026.
- **Expected** is 5 provinces × the quarters in that span.
- **No source table records publication dates** [V]. **Granularity** is what is stored; the official series' native frequency is in the next note.
- **Strict timing feeds the model quarter t−1** for government series. Typical agency lags are about 1 week to about 2 months [A], so they would be available before the forecast quarter starts. These dates are **not verified per observation** [U].

| Table (`data/processed/`) | Source | Span | Expected | Actual | Missing province-quarters | Dup | Values missing in rows | Varies by province? | Stored as | Fetched |
|---|---|---|---:|---:|---|---:|---|---|---|---|
| `labels` | SWS + PSA CPI (Eq. 3) | 2021-Q2..2025-Q4 | 95 | **80** | 15: all of **2022-Q1, 2025-Q2, 2025-Q3** (no SWS round) | 0 | 0 | SWS no (one regional value); CPI term yes | Quarterly | n/r |
| `psa_indicators` | OpenStat 0012M4ACP23/22, LFS, poverty | 2021-Q1..**2025-Q4** | 100 | 100 | 0 (but **no 2026**) | 0 | 0 | food CPI, rice, poverty yes; unemployment **no** (national) | Quarterly means of monthly values | n/r |
| `psa_rice_prices` | OpenStat 0052M4AWB01 | 2021-Q1..2026-Q3 | 115 | 112 | 3: **Laguna 2022-Q3, Quezon 2024-Q1, Quezon 2024-Q2** | 0 | 0 | Yes | Quarterly mean of monthly values | 2026-09-09 |
| `cpi_full` | OpenStat 0012M4ACP22, **region only** | 2021-Q1..2026-Q2 | 110 | 110 | 0 | 0 | 0 | **No** (region inherited) | Quarterly | 2026-09-04 |
| `oil_prices` | DOE (hand-curated), EIA | 2021-Q1..2026-Q3 | 115 | 115 | 0 | 0 | diesel and gasoline 15 each | No | Quarterly | 2026-09-09 |
| `bsp_macro` | BSP (hand-curated), ECB | 2021-Q1..2026-Q3 | 115 | 115 | 0 | 0 | OFW YoY 35 (2021 has no prior-year base) | No | Quarterly | 2026-09-09 |
| `pagasa_climate` | PAGASA, NOAA ONI | 2021-Q1..2026-Q3 | 115 | 115 | 0 | 0 | 0 | Typhoons yes; ENSO and drought no | Quarterly | 2026-09-09 |
| `province_rainfall` | NASA POWER | 2021-Q1..2026-Q2 | 110 | 110 | 0 | 0 | 0 | Yes | Quarterly | 2026-09-04 |
| `fssi_quarterly` | News, Algorithm 1 (score ≥ 0.30) | 2021-Q1..2026-Q3 | 115 | **34** | **81** (no retained article) | 0 | 0 | Yes | Quarterly | n/r |
| `trigger_proportions` | News, Algorithm 2 | 2021-Q1..2026-Q3 | 115 | 111 | 4 | 0 | 0 | Yes | Quarterly | n/r |

(Dup = duplicate province-quarter rows; n/r = not recorded.)

**Model-input missingness on the corrected 2021+ frame** (rule W, K1–K4, strict timing; `frame_missingness.json`) [V]:

| Period | Share of input cells missing | Province-quarters with FSSI observed |
|---|---:|---|
| 2021–2022 | 26.8% | 10 |
| 2023-H1 | 6.7% | 2 |
| 2023-Q3 to 2025-Q4 | 6.2% | 14 |
| 2026 | 6.7% | 1 |

**Transformations that use information outside the window:**

| Item | Status |
|---|---|
| The approved pipeline (`features_fused`, MODEL-A) | Uses 2020 data and the 2018 poverty survey [V] |
| The window frame (`window2021_study.window_frame`) | Removes them [V] (`tests/unit/test_window2021.py`) |
| Kept reference bases (CPI 2018=100 index, published 2021+ YoY rates, WMO 1991–2020 rainfall normal) | Adviser decision D3 [U] |
| Production MODEL-A as an artifact | Trained on 2020–2025 data with the leaked previous-quarter label. It **cannot be compared fairly as is**; only its *configuration*, refitted under the same rules, can be (Section 5). |

**PSA OpenStat sources** (metadata, 2026-10-09; full detail in `DATA_COMPLETENESS_AUDIT_2026-10-09.md`) [V]:

| Table | Exists / HTTP | Monthly | Range per title | Five provinces | Project holds | Publication date per month |
|---|---|---|---|---|---|---|
| `0012M4ACP22` | Yes / 200 | Yes (Jan–Dec + Ave) | Jan 2018 – **Sep 2026**; folder updated 2026-10-06 | Yes (codes 33–37); Lucena City listed separately | Region only, quarterly | Not in table; psa.gov.ph blocks automation [U] |
| `0012M4ACP23` | Yes / 200 | Yes | Jan 2019 – **Sep 2026** | Yes | Province, quarterly, to 2025-Q4 only | Same [U] |
| `0052M4AWB01` | Yes / 200 | Yes (January–December + Annual) | 2010–2026; end month [U]; folder updated 2026-10-07 | Yes (codes 28–32) | Province, quarterly, to 2026-Q3 | Same [U] |

**News (verified; nothing changed).**

- **Unassigned articles:** 46 articles from 2021 onward pass the 0.30 threshold but have no province.
- **Geocoder results:** it assigns 6, of which 5 are false matches. Three are the surname "Lopez" (Trade Secretary Ramon Lopez ×2, Asst. Sec. Romel Lopez), and two are San Juan **City**, Metro Manila (Greenhills; MMDA).
- **Root causes:** `lopez` is missing from the surname set, and the "city" keyword corroborates San Juan (Batangas), which is a municipality.
- **Minimal fix (tested in memory only):** add `lopez` to `_LGU_SURNAME_OR_WORD`, and do not accept "City" as a cue for an LGU whose `lgu_type` is municipality. This removes all 5 false matches, keeps Calatagan, and changes 0 of 400 existing tags.
- **No genuine province articles are recoverable** from the 46.

## 2. Label publication timeline (`label_publication_timeline.csv`)

**Sources and conventions:**

- **Label source:** SWS total hunger, Balance-Luzon stratum, inherited by all 5 provinces, plus PSA provincial food CPI YoY (Eq. 3).
- **Forecast origin:** the first day of the target quarter (strict Rule 3).
- **Publication evidence:** the SWS article ID `ART-yyyymmdd` in the source URL (a Wayback copy is kept in `docs/provenance/sws_hunger_sources.json`). For four rounds, a date read from the release page is recorded in `scripts/supplementary/timing_audit.py::MANUAL_RELEASES`.
- **No date is inferred from survey dates.**
- **"Eligible labels"** are the labelled quarters whose SWS date is before the origin. This is rule L as implemented: the earliest article for the quarter, and the SWS date only.

| Target | Origin | Label on file | SWS round (as labelled by SWS) | SWS value(s) | SWS publication | Evidence | Eligible training quarters / rows at this origin | Latest eligible |
|---|---|---|---|---|---|---|---|---|
| 2021-Q1 | 2021-01-01 | No | none | none | none | none | 0 / 0 | none |
| 2021-Q2 | 2021-04-01 | Yes | "First Quarter 2021", Apr 28 – May 2 | 15.7; 15.0 (two articles; label uses the **mean 15.35**) | 2021-07-12 and **2021-07-28** | ART id [V] | 0 / 0 | none |
| 2021-Q3 | 2021-07-01 | Yes | Sep 12–16, 2021 | 10.3 | 2021-12-06 | ART id [V] | 0 / 0 | none |
| 2021-Q4 | 2021-10-01 | Yes | Dec 12–16, 2021 | 9.2 | 2022-03-25 | ART id [V] | 1 / 5 | 2021-Q2 |
| 2022-Q1 | 2022-01-01 | **No** | none | none | none | none | 2 / 10 | 2021-Q3 |
| 2022-Q2 | 2022-04-01 | Yes | "First Quarter 2022", Apr 19–27 | 11.7; 11.9 (label **mean 11.8**) | 2022-06-06 and **2022-09-10** | ART id [V] | 3 / 15 | 2021-Q4 |
| 2022-Q3 | 2022-07-01 | Yes | Sep 29 – Oct 2, 2022 | 9.6 | 2022-10-29 | ART id [V] | 4 / 20 † | 2022-Q2 † |
| 2022-Q4 | 2022-10-01 | Yes | Dec 10–14, 2022 | 11.3 | 2023-01-19 | ART id [V] | 4 / 20 | 2022-Q2 |
| 2023-Q1 | 2023-01-01 | Yes | Mar 26–29, 2023 | 8.7 | 2023-05-11 | ART id [V] | 5 / 25 | 2022-Q3 |
| 2023-Q2 | 2023-04-01 | Yes | Jun 28 – Jul 1, 2023 | 11.3 | 2023-08-02 | ART id [V] | 6 / 30 | 2022-Q4 |
| 2023-Q3 | 2023-07-01 | Yes | Sep 28 – Oct 1, 2023 | 10.3 | 2023-11-20 | ART id [V] | 7 / 35 | 2023-Q1 |
| 2023-Q4 | 2023-10-01 | Yes | Dec 8–11, 2023 | 14.3 | 2024-01-22 | ART id [V] | 8 / 40 | 2023-Q2 |
| 2024-Q1 | 2024-01-01 | Yes | Mar 21–25, 2024 | 15.3 | 2024-04-30 | ART id [V] | 9 / 45 | 2023-Q3 |
| 2024-Q2 | 2024-04-01 | Yes | Jun 23 – Jul 1, 2024 | 19.6 | 2024-07-23 | ART id [V] | 10 / 50 | 2023-Q4 |
| 2024-Q3 | 2024-07-01 | Yes | "September 2024" | 18.1 | **≤ 2025-01-14** | Release page; **upper bound** (date of the combined Q4 article) [U] | 11 / 55 | 2024-Q1 |
| 2024-Q4 | 2024-10-01 | Yes | "December 2024" | 25.3 | 2025-01-14 | Release page (shows "Jan 14, 2024", a typo) [V/A] | 12 / 60 | 2024-Q2 |
| 2025-Q1 | 2025-01-01 | Yes | Stratbase-SWS Mar 15–20, 2025 | 24.0 | 2025-03-29 ‡ | Release page, not re-verified [U] | 12 / 60 | 2024-Q2 |
| 2025-Q2 | 2025-04-01 | **No** | none | none | none | none | 15 / 75 | 2025-Q1 |
| 2025-Q3 | 2025-07-01 | **No** | none | none | none | none | 15 / 75 | 2025-Q1 |
| 2025-Q4 | 2025-10-01 | Yes | "November 2025" | 16.7 | **≤ 2026-05-12** | Article reporting March 2026; **upper bound** [U] | 15 / 75 | 2025-Q1 |
| 2026-Q1 | 2026-01-01 | **Not in project** | March 2026 round **exists** (national 23.2% in the article title) [V] | Balance-Luzon value not stored | ≤ 2026-05-12 | Article title [V] | 15 / 75 | 2025-Q1 |
| 2026-Q2 to Q4 | 2026-04-01 / 07-01 / 10-01 | Not in project | Unknown [U] | none | none | none | 15–16 / 75–80 | 2025-Q1 / Q4 |

† **Rule L refinement (a):** the 2022-Q2 label is the mean of two rounds, and the second was published 2022-09-10. It was therefore **not** available at the 2022-07-01 origin, but the implemented rule counted it as eligible. Correct: 3 quarters / 15 rows. The same pattern applies to 2021-Q2 (second article 2021-07-28), but no origin falls between the two articles.

‡ **Rule L refinement (b):** the label also needs CPI for the quarter's last month, which PSA publishes in roughly the first week of the next month [A]. CPI dates are unverified [U]. For 2025-Q1 (SWS 2025-03-29) and 2022-Q2 (first article 2022-06-06), the label is therefore complete only after early April 2025 and early July 2022 respectively.

- **No outer test quarter is affected:** no 2025-Q2 target exists, and every later origin is long after.
- **Proposed fix:** label publication = the later of the SWS publication date (the last round used) and the CPI publication date, with the CPI date treated as unverified. A conservative stand-in would be the quarter end plus 10 days, pending verification.

**Effect of the unverified dates on evaluation:**

- **The three upper-bound dates (2024-Q3, 2025-Q4 and the 2026-Q1 round) are conservative for training eligibility.** They can only exclude a label that may in fact have been available, which lowers rather than inflates scores.
- **For the SWS feature they may understate what was known.** The feature uses the latest round published before the origin, so an earlier true release date would mean fresher SWS information was available.
- **2025-Q1's single page date** is the one date whose error could matter in the inflating direction. It only affects origins from 2025-04-01 on, and there is no labelled target between 2025-04-01 and 2025-10-01.

## 3. Evaluation designs compared

| Design | What it uses | Strengths here | Weaknesses here | Verdict |
|---|---|---|---|---|
| **1. Expanding-window walk-forward** (rule L, inner walk-forward for all choices) | All 16 labelled quarters; each test quarter forecast from earlier eligible labels only | Uses every quarter. Respects publication delays. Keeps provinces together. Matches the operational use. | 2022-Q4 to 2025-Q4 has already been used repeatedly for comparison and selection. Early folds train on 7–9 quarters with many exact ties. | **Use for development and model selection, reported as exploratory** |
| **2. Fixed split** (e.g. train 2021-Q2–2022-Q4, validate 2023, test 2024–2025) | 6 / 4 / 6 quarters | Simple | The "test" quarters 2024–2025 were already used. Training has only 6 quarters (30 rows), fewer under rule L. The 2024 regime shift makes one fixed split unrepresentative. A single fixed split wastes the scarce labels. | **Not recommended** |
| **3. Frozen forecasts scored on later labels** | 2026 quarters whose SWS rounds are published after the forecasts are frozen | **The only untouched outcomes.** Model choice cannot leak into them. | At most 4 quarters / 20 rows within the window. All 2026 origins have passed, so the forecasts are label-blind **retrospective simulations**, not real-time. Labels also need 2026 provincial CPI, which is not yet in the project. | **Use as the final test**, with its small size reported honestly |

**Recommendation: combine designs 1 and 3.**

- **Freeze before scoring:** fix one primary configuration and the comparators using design 1. Freeze their 2026 forecasts **before** any 2026 label (SWS March 2026 onward, or 2026 provincial CPI) enters the project.
- **Score once:** score each 2026 quarter when its label arrives, with no refitting in between.

**What each part of the data is for:**

| Role | Data |
|---|---|
| **Training (fit)** | In each fold, the labelled quarters published before that fold's origin (rule L, refined) |
| **Validation (select features and settings)** | The walk-forward inner folds inside each training set. The outer walk-forward quarters 2023-Q3 to 2025-Q4 serve as *exploratory* validation, because they have already been seen. |
| **Final test** | 2026 quarters with published labels, scored once against forecasts frozen beforehand |
| **Not yet available** | 2026-Q2 to Q4 SWS rounds (existence unknown) and 2026 provincial CPI. Anything after 2026 is outside the window. |

## 4. Proposed split, with exact quarters and counts

| Period | Quarters | Distinct labelled quarters | Province-quarters (labelled) | Usable training labels under rule L | Input missingness and coverage limits | Used before to compare or select models? | Status |
|---|---|---:|---:|---|---|---|---|
| **Development, early** (training only) | 2021-Q2 .. 2023-Q2 | 9 (2022-Q1 has no label) | 45 | Grows from 0 to 6 quarters across these origins; the first two targets have no eligible label | 26.8% of inputs missing in 2021–22 (window edge, OFW YoY, the 2018 poverty vintage removed); FSSI observed in 12 cells | As training and inner validation in all studies; 2022-Q4 to 2023-Q2 were outer tests in the 2020-window studies | Training / inner validation |
| **Development, walk-forward validation** | 2023-Q3 .. 2025-Q4 | 8 (2025-Q2 and Q3 have no label) | 40 | 7, 8, 9, 10, 11, 12, 12, 15 quarters (35–75 rows) at the eight origins | 6.2% missing; FSSI observed in 14 of 40 rows; rice missing for Quezon 2024-Q1/Q2 (monthly) | **Yes, repeatedly** (MODEL-B/B2, E0–E7, P–P4, N1/N2) | **Exploratory only; not an independent test** |
| **Final test** | 2026-Q1 .. 2026-Q4 (those with a published SWS round) | 0 now; at most 4 | 0 now; at most 20 | 15–16 quarters (75–80 rows), latest eligible 2025-Q1 or 2025-Q4 | Labels need the SWS Balance-Luzon value and 2026 provincial CPI (`psa_indicators` ends 2025-Q4). Inputs for 2026-Q3/Q4 forecasts also need 2026 provincial CPI. | No outcomes seen. The national March 2026 figure appears in a stored URL title; the Balance-Luzon value does not. | **Independent, small**; retrospective simulation |
| Outside the window | ≤ 2020, ≥ 2027 | none | none | none | none | none | Excluded |

**A credible independent test of "≥ 75%" cannot be established within 2021–2026.** Even if all four 2026 quarters are labelled, even 19/20 on 20 rows would not, by itself, establish true accuracy above 75% (rows within a quarter are not independent; correction 2). The realistic product is a point estimate on 5–20 untouched rows with a wide interval, plus the exploratory walk-forward results.

## 5. Fair comparison protocol (to be fixed before any new run)

1. **Same information for every model:**
   - Strict Rule 3 timing; window rule W; K1–K4.
   - **Refined rule L:** label publication = the later of the SWS date (the last round used) and the CPI date. The CPI date is unverified; the stand-in is the quarter end plus 10 days, pending verification.
   - Threshold 14.345 (the Eq. 3 global median over 2021–2025, pending adviser decision D2).
2. **Comparators, fixed now:**
   - **Carry forward:** the latest label **published** before the origin under refined rule L, per province.
   - **The Eq. 3 rule:** latest published SWS + 2 × `cpi_rel` at t−1, compared with the threshold.
   - **MODEL-A configuration:** the 12 Eq. 5 features, LightGBM defaults, refitted under the same rules. The production artifact is not comparable (it was trained with pre-2021 data and leaked labels).
   - **MODEL-B2 configuration:** `gov_c`, LightGBM, `scale_pos_weight` from training rows.
   - **Additional candidates:** only the `gov_c` logistic configuration (C = 0.1, balanced), and only as **exploratory**, because it was identified after seeing the walk-forward rows. Nothing else may be added after this protocol is fixed.
3. **Primary candidate:** the governing MODEL-B2 configuration, designated by your prior decision, not by test results. Every other model is a comparator.
4. **Metrics, fixed:**
   - **Primary:** accuracy (mean over quarters; every quarter has 5 rows).
   - **Secondary:** correct/incorrect counts, F1 (weighted), ROC-AUC, Brier score, HIGH recall, missed HIGH rows and quarters, confusion matrix, within-quarter province AUC, and per-quarter and per-province results.
5. **Comparisons:**
   - Paired results against carry-forward and the Eq. 3 rule on identical rows.
   - Exact McNemar test plus a quarter-cluster bootstrap.
   - The one-sided 95% lower bound for the primary candidate.
6. **The 75% target is a performance goal.** It does not justify changing the test period, threshold, labels or selection.
7. **Order of operations:**
   1. Approve this protocol.
   2. Re-freeze the 2026 forecasts for the four comparators under refined rule L, before any 2026 label enters the project.
   3. Collect the labels.
   4. Score once and report everything.

## 6. Limitations and risks

| Risk | Effect | Mitigation |
|---|---|---|
| Few labelled quarters (16), one regional SWS value per quarter | Wide intervals; effective sample about 16 quarters | Report intervals; avoid many candidates |
| The development rows have been reused | The development score is optimistic | Label it exploratory; the final test is 2026 only |
| Final test ≤ 20 rows, possibly 5 | Cannot confirm ≥ 75% with confidence | State this up front; report a point estimate and interval |
| 2026 forecasts are retrospective (origins passed; current data vintages) | Not a real-time test | Label as retrospective simulation; freeze before labels |
| Exposure of the national March 2026 figure (URL title) | Small risk of informal anchoring | Disclosed; the Balance-Luzon value was never stored or used |
| Unverified CPI and rice publication dates | Monthly features cannot be used leakage-free; the CPI part of rule L is approximate | Release-date ledger by hand, or an approved conservative rule |
| SWS release dates: 3 upper bounds, 1 unverified page date | Mostly conservative; 2025-Q1 is unverified | Verify 2024-Q3, 2025-Q1 and 2025-Q4 first-publication dates by hand |
| Two-round quarters (2021-Q2, 2022-Q2): the label uses the mean, the feature uses the first round | Labels need the later date (refinement a) | Apply refinement (a) |
| SWS quarter assignment by fieldwork date (e.g. "First Quarter 2022" survey in April → 2022-Q2) | A naming inconsistency, not leakage | Document |
| The "Quezon" CPI likely excludes Lucena City [A] | A definition caveat, consistent between feature and label | Document |
| FSSI observed in 34 of 115 province-quarters | The NLP layer contributes little | Documented; recovery from re-geocoding is not possible |
| Window and threshold choices (2021–2026 vs Chapter III's 2020–2025; 14.345 vs 14.6) | Changes labels and counts | Adviser decisions D1 and D2 |

## 7. Prioritized next steps (none started; each awaits your approval)

1. **Approve the evaluation design (Section 3) and the comparison protocol (Section 5),** including rule L refinements (a) and (b) and MODEL-B2 as the primary candidate.
2. **Re-freeze label-blind 2026 forecasts under refined rule L** for the four comparators: carry-forward, the Eq. 3 rule, MODEL-A configuration and MODEL-B2 configuration (plus the exploratory logistic). This needs a model run.
3. **Verify the publication dates by hand:**
   - The SWS first publication of the September 2024, March 2025, November 2025 and March 2026 rounds.
   - The PSA CPI release date for the last month of each labelled quarter (16 dates).
   - psa.gov.ph blocks automated access, so these must be read by a person.
4. **Collect the 2026 label inputs after step 2:**
   - The Balance-Luzon SWS value for March 2026 (and later rounds as published).
   - Provincial food CPI for 2026 from `0012M4ACP23`: 5 provinces × 9 months = 45 values.
   - Then score once.
5. **Optional, lower expected gain:** the monthly CPI/rice experiment (`PREREGISTRATION_v4` Stage B). Only after step 3 or an approved conservative availability rule; see `DATA_COMPLETENESS_AUDIT_2026-10-09.md`.
6. **Optional:** the two-line geocoder precision fix (`lopez`; "City" for municipalities). This is a code change that needs approval.

**Stopping here.** No download, experiment, methodology change, production change, commit or deployment will happen without your explicit approval.


---

### Further corrections appended later on 2026-10-09 (original text above preserved)

1. **"2025-Q2 and 2025-Q3 have no SWS round" is wrong.** SWS ran April 2025, June 2025 and September 2025 hunger surveys. They are missing from the project, not from SWS.
2. **The 2026-Q1/Q2 Balance-Luzon values are stored** in `docs/provenance/sws_hunger_sources.json` **and** in `app/ml/corpus/sws_hunger_fetcher.py`. They have been seen by the analyst, so 2026-Q1/Q2 are excluded from blind evaluation.
3. **The recommended final test is now limited to 2026-Q3/Q4,** under the protection plan and prerequisites in `docs/RULE_L_FINAL_AND_PROTECTED_EVALUATION_PLAN_2026-10-09.md`, and it is not yet valid.
