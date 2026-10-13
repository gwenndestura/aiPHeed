# Rule L (Final Specification) and the Protected 2026 Evaluation Plan (2026-10-09)

**Authorized scope:** finalize the timing rules, document missing source data and outcome exposure, and prepare a read-only protection plan.

- **Not done:** no model was trained or run, no dataset was downloaded, no missing outcome value was retrieved, and no production code or data, frozen forecast, thesis chapter or methodology was changed. Nothing was committed or deployed.
- **Nothing about the September or December 2026 SWS rounds was searched for, opened or retrieved.**
- **New files only:**
  - this report;
  - `evidence/2026-10-09_data_audit/sws_round_publication_dates_v2.csv` (supersedes, but preserves, `sws_round_publication_dates_verified.csv`);
  - `evidence/2026-10-09_data_audit/origin_eligibility_timeline.csv`.
- **Corrections:** appended correction notes to the two earlier audit reports. Their original text is preserved.

**Evidence classes:**

| Tag | Meaning |
|---|---|
| **[V]** | Verified on an original SWS or agency document: the archived SWS article page's own date line, or the SWS media-release filename |
| **[L]** | SWS's own site listing date ("posted …"), seen through the search index. The page itself was not opened, because SWS hunger listing pages also list 2026 releases. |
| **[S]** | Secondary source (news) |
| **[U]** | Unverified |

---

## 1. Rule L: final specification

**L1. Training-label eligibility.** The label for quarter *q* may be used to fit a model, or as an inner-validation target, for a forecast of quarter *T* only if **label_published(q) < start of T**, where

- label_published(q) = **the later of**:
  - (i) the publication date of the **last** SWS round contributing to *q*'s label;
  - (ii) the publication date of the **final-month provincial food CPI** for *q*.
- Both dates must be **verified** ([V] or [L]; [S] only where noted and approved). A label with any unverified contributing date is **not eligible** (L4).

**L2. SWS inputs.** A forecast of *T* may use only SWS rounds whose **verified** publication date is before the start of *T*. Each round is treated separately, so the latest such round is the "known SWS". A round with no verified date is not used.

**L3. Other inputs.** Every input value must have a documented publication date before the start of *T*. Two acceptable ways to establish it:

- **(a)** the value's own release date; or
- **(b)** a documented **agency release calendar** showing that the series' release lag is shorter than the margin between the value's reference period and the forecast date.

Values meeting neither are **unverified** and may not be used until verified. This replaces the earlier practice of assuming typical lags.

**L4. Unknown dates.** An unknown or unverified date is never assumed available. The value or label is marked *unverified* and excluded, or the run is deferred.

**L5. Composition of a quarter's label (adviser decision; current convention recorded, not changed).** The approved data assign SWS rounds by **fieldwork quarter**, and average two rounds when two fall in one quarter (2021-Q2, 2022-Q2; see the header of `sws_hunger_fetcher.py`). Two cases are open:

- **2025-Q1:** the stored label uses only the **March 2025** Stratbase-SWS round. SWS also measured hunger in **January and February 2025** (cited in the March release). Their own release dates are [U].
- **Comparability:** for January–April 2025, SWS's hunger respondents were registered voters (Stratbase-SWS), not household heads (per the April 2025 release).

Whether those rounds belong in the label is a methodology decision. Under the current convention (March only), 2025-Q1's label date is **2025-04-04** [V].

**L6. Forecast origin.** The forecast origin is 00:00 on the first day of *T* (strict Rule 3). A forecast generated after that date, from data fetched later, is a **retrospective simulation**. It must be labelled as such.

## 2. Publication dates by source

### 2.1 SWS hunger rounds, 2021 onward (`sws_round_publication_dates_v2.csv`)

| Fieldwork quarter | Round | Published | Class | In project? |
|---|---|---|---|---|
| 2021-Q2 | May 2021 ("First Quarter 2021") | 2021-07-12 | [V] | Yes |
| 2021-Q2 | June 2021 ("Second Quarter 2021") | 2021-07-28 | [V] | Yes |
| 2021-Q3 | September 2021 | 2021-12-06 | [V] | Yes |
| 2021-Q4 | December 2021 | 2022-03-25 | [V] | Yes |
| 2022-Q2 | April 2022 ("First Quarter 2022") | 2022-06-06 | [V] | Yes |
| 2022-Q2 | June 2022 ("Second Quarter 2022") | 2022-09-10 | [V] | Yes |
| 2022-Q3 | Sep–Oct 2022 | 2022-10-29 | [V] | Yes |
| 2022-Q4 | December 2022 | 2023-01-19 | [V] | Yes |
| 2023-Q1 | March 2023 | 2023-05-11 | [V] | Yes |
| 2023-Q2 | June–July 2023 | 2023-08-02 | [V] | Yes |
| 2023-Q3 | Sep–Oct 2023 | 2023-11-20 | [V] | Yes |
| 2023-Q4 | December 2023 | 2024-01-22 | [V] | Yes |
| 2024-Q1 | March 2024 | 2024-04-30 | [V] | Yes |
| 2024-Q2 | June–July 2024 | 2024-07-23 | [V] | Yes |
| 2024-Q3 | September 2024 | **2024-10-17** | **[V]**: archived SWS page `ART-20241017131004`, "Oct 17, 2024 01:10:04 PM". This upgrades the earlier [S]. | Yes |
| 2024-Q4 | December 2024 | 2025-01-14 | [V]: `ART-20250114210615` ("Jan 14, 2025 09:06:15 PM") and `pr20250114` | Yes |
| 2025-Q1 | January 2025 (Stratbase-SWS) | [U] | Cited in the March 2025 release | **No** |
| 2025-Q1 | February 2025 (Stratbase-SWS) | [U] | Same | **No** |
| 2025-Q1 | March 15–20, 2025 (Stratbase-SWS) | 2025-03-29 | [V] `pr20250329` | Yes |
| **2025-Q2** | **April 23–28, 2025** | **2025-06-27** | **[V]**: `ART-20250627174857` ("Jun 27, 2025 05:48:57 PM") | **No** |
| **2025-Q2** | **June 2025** | **2025-08-15** | [L] "posted Aug 15, 2025" | **No** |
| **2025-Q3** | **September 24–30, 2025** | **2025-11-05** | [L] "posted Nov 05, 2025" | **No** |
| 2025-Q4 | November 24–30, 2025 | **2026-01-14** | [L] "posted Jan 14, 2026", plus [S] news | Yes |
| 2026-Q1 | March 2026 | 2026-05-12 | [V] `pr20260512`. **Outcome exposed (Section 4).** | Yes, in code and provenance |
| 2026-Q2 | June 2026 | [U] | **Outcome exposed (Section 4)** | Yes, in code and provenance |
| 2026-Q3 / Q4 | Sept / Dec 2026 | Not examined | **Protected (Section 5)** | No |

**Notes:**

- Four `ART-` IDs found while searching (Jan 30, Feb 11, Mar 26 and Oct 15, 2025) were checked and are **not hunger releases** (Stratbase political items). They are excluded.
- **No missing Balance-Luzon value was retrieved or inferred.** National figures appeared incidentally in search summaries and are not recorded or used.

### 2.2 Other sources

| Source | Values used for a forecast of *T* | Margin to the forecast date | Per-observation release date | Calendar evidence | Status under L3 |
|---|---|---|---|---|---|
| Provincial food CPI (OpenStat 0012M4ACP23) | Quarter T−2 (strict timing) | ≥ about 92 days after the reference quarter ends | **2 verified** [S]: June 2022 → 2022-07-05; March 2025 → 2025-04-04 | PSA Advance Release Calendar **not accessed** (psa.gov.ph bot check) | **Unverified (L3b pending)** |
| Final-month CPI for **labels** (L1-ii) | Each labelled quarter's last month | none | 2 of 17 verified | none | **Unverified for 15 labels** |
| Regional CPI (`cpi_full`, 0012M4ACP22) | T−2 | ≥ about 92 days | none | none | Unverified |
| Wholesale RMR (0052M4AWB01) | T−2 | ≥ about 92 days | none | none | Unverified |
| Unemployment (PSA LFS, national) | T−2 | ≥ about 92 days | none | none | Unverified |
| OFW remittances (BSP, hand-curated) | T−2 | ≥ about 92 days | none | none | Unverified |
| FX (ECB) | T−2 | ≥ about 92 days | Daily (immediate) | ECB publishes the reference rate the same day [A] | Unverified (low risk) |
| Diesel / gasoline (DOE weekly), Brent (EIA) | T−2 | ≥ about 92 days | none | none | Unverified (low risk) |
| ENSO ONI (NOAA), typhoons / drought (PAGASA) | T−2 | ≥ about 92 days | none | none | Unverified |
| Rainfall (NASA POWER) | T−2 | ≥ about 92 days | none | none | Unverified |
| Poverty incidence (PSA) | Latest survey published before *T* | n/a | 2021 survey: 2022-08-15 (recorded in `timing_audit.py`, not re-verified); 2023 survey: "Aug 2024" (day [U]) | none | **Unverified** (re-verify both) |
| News (FSSI, triggers) | Quarter T−1 (articles dated inside it) | Articles predate the forecast date | `published` timestamp on each article [V] | n/a | **Verified** (article dates). Scoring is a model step applied later and uses no future text. |
| SWS hunger | Latest round published before *T* | n/a | Section 2.1 | n/a | Verified where [V]/[L] |

**Consequence.** Under the strict L3/L4, the government inputs and 15 of 17 labels are currently **unverified**, despite margins of about 3 months. **No model experiment can be called Rule-L-compliant until CPI release dates (and a release calendar for the other series) are documented** (Section 6).

## 3. Eligible training labels and inputs for each forecast origin (`origin_eligibility_timeline.csv`)

Labels use the current L5 convention. **"Pending CPI"** means the SWS date is verified but the final-month CPI date is not (L1-ii), so the label becomes eligible only once that date is verified.

| Target (origin) | Labels fully verified | Labels pending a CPI date | Eligible labels **not in the project** | Latest SWS round published before the origin (L2) | That round in project? | Government inputs from | News from |
|---|---|---|---|---|---|---|---|
| 2023-Q3 (2023-07-01) | 2022-Q2 | 6 (2021-Q2 … 2023-Q1) | none | March 2023 (2023-05-11) | Yes | 2023-Q1 | 2023-Q2 |
| 2023-Q4 (2023-10-01) | 2022-Q2 | 7 | none | June–July 2023 (2023-08-02) | Yes | 2023-Q2 | 2023-Q3 |
| 2024-Q1 (2024-01-01) | 2022-Q2 | 8 | none | Sep–Oct 2023 (2023-11-20) | Yes | 2023-Q3 | 2023-Q4 |
| 2024-Q2 (2024-04-01) | 2022-Q2 | 9 | none | December 2023 (2024-01-22) | Yes | 2023-Q4 | 2024-Q1 |
| 2024-Q3 (2024-07-01) | 2022-Q2 | 10 | none | March 2024 (2024-04-30) | Yes | 2024-Q1 | 2024-Q2 |
| 2024-Q4 (2024-10-01) | 2022-Q2 | 11 | none | June–July 2024 (2024-07-23) | Yes | 2024-Q2 | 2024-Q3 |
| 2025-Q1 (2025-01-01) | 2022-Q2 | 12 (**includes 2024-Q3**) | none | **September 2024 (2024-10-17)** | Yes | 2024-Q3 | 2024-Q4 |
| 2025-Q2 (2025-04-01) | 2022-Q2 | 13 | none | March 2025 (2025-03-29) | Yes | 2024-Q4 | 2025-Q1 |
| 2025-Q3 (2025-07-01) | 2022-Q2 | 13 (+ 2025-Q1, verified 2025-04-04, under L5 March-only) | none | **April 2025 (2025-06-27)** | **No** | 2025-Q1 | 2025-Q2 |
| 2025-Q4 (2025-10-01) | 2022-Q2 | 14 | **2025-Q2** | **June 2025 (2025-08-15)** | **No** | 2025-Q2 | 2025-Q3 |
| 2026-Q1 (2026-01-01) | 2022-Q2 | 15 | **2025-Q2, 2025-Q3** | **September 2025 (2025-11-05)** | **No** | 2025-Q3 | 2025-Q4 |
| 2026-Q2 (2026-04-01) | 2022-Q2 | 16 | 2025-Q2, 2025-Q3 | November 2025 (2026-01-14) | Yes | 2025-Q4 | 2026-Q1 |
| **2026-Q3 (2026-07-01)** | 2022-Q2 | 17 (incl. **2026-Q1**, published 2026-05-12) | 2025-Q2, 2025-Q3; **2026-Q1 provincial CPI** | March 2026 (2026-05-12). June 2026 [U]: if published before 2026-07-01 it would be the latest. | Yes | **2026-Q1: provincial CPI not in project** | 2026-Q2 |
| **2026-Q4 (2026-10-01)** | 2022-Q2 | 17 (+ 2026-Q2 if its dates are verified) | 2025-Q2, 2025-Q3; 2026-Q1/Q2 provincial CPI | June 2026 (date [U]) or March 2026 | Yes | **2026-Q2: provincial CPI not in project** | 2026-Q3 |

**How this differs from what earlier studies used:**

- **2025-Q1 test fold:** used June 2024 SWS (should be September 2024) and lacked the 2024-Q3 label.
- **2025-Q4 test fold:** used March 2025 SWS (should be June 2025, not in project) and lacked the 2025-Q2 label.
- **Frozen 2026-Q1/Q2 forecasts:** used March 2025 SWS (should be September and November 2025) and lacked the 2025-Q2, 2025-Q3 and 2025-Q4 labels.

None of these is a leak. All of them under-inform the model.

## 4. Existing exposure of 2026-Q1 and 2026-Q2 outcomes (excluded from blind claims)

| Where | What | Since |
|---|---|---|
| `app/ml/corpus/sws_hunger_fetcher.py` (production code; the hand-curated table) | Balance-Luzon total, moderate and severe for 2026-Q1 and 2026-Q2, plus national figures; `SWS_COVERAGE_END = (2026, 2)` | Table "extended 2026-09-23" (file header) |
| `docs/provenance/sws_hunger_sources.json` | Balance-Luzon totals for 2026-Q1 and Q2, and source URLs | Modified 2026-09-23 |
| This analysis (2026-10-09) | The analyst read the 2026-Q1/Q2 Balance-Luzon values (provenance listing). Search summaries showed national March and June 2026 figures. | 2026-10-09 |
| Not exposed in model code | `sws_hunger.parquet` ends at 2025-Q4 (the fetcher defaults to `end_year=2025`). `timing_audit.py` reads only URL dates. No 2026 round entered any feature, label or frozen forecast. | n/a |

**Determination.** **2026-Q1 and 2026-Q2 are excluded from any claim of blind or independent evaluation.**

- Any result for them may be reported only as a disclosed, non-independent check.
- Because both stored values exceed the 14.345 threshold, most of their labels are close to determined. 2026-Q1 is far above it.

## 5. Protecting 2026-Q3 and 2026-Q4 (plan only; nothing executed)

**Current state (as far as known):**

- The September 2026 and December 2026 SWS results have **not** been searched for, opened, stored or seen.
- The September 2026 round may already be published, or soon will be; the September 2025 round was posted 2025-11-05.
- December 2026 results would be published in 2027.

**Protection steps (for approval):**

1. **Seal.** No one working on the model opens SWS releases, news or files about September or December 2026 hunger until forecasts are frozen. No web searches on SWS 2026 hunger.
2. **Code freeze on the outcome table.** Do not extend `sws_hunger_fetcher.py`'s table or `SWS_COVERAGE_END` beyond (2026, 2), and do not run `scripts/refresh_all_sources.py` for SWS, until the freeze is complete.
3. **Freeze before collection.**
   - Produce the 2026-Q3/Q4 forecasts under final Rule L (after all prerequisites in Section 6).
   - Record SHA-256 hashes of the forecasts, configuration, inputs and code in a dated manifest.
   - Hand the hashes to you, or the adviser, **before** any 2026-Q3/Q4 outcome is collected.
4. **Separate custody.** Ideally a person other than the modeller collects the September/December 2026 Balance-Luzon values and 2026 provincial CPI into a separate file, recording the URL and publication date.
5. **Score once.** Run a single pre-written scoring script against the frozen file and report every quarter, with no refitting.
6. **Disclosure.**
   - **Retrospective:** both forecast dates (2026-07-01 and 2026-10-01) have passed, so the forecasts are label-blind retrospective simulations from current data vintages, not real-time forecasts.
   - **Window:** the 2026-Q4 label would be published in 2027. Whether a 2027 publication of a 2026 observation is within the approved window is an adviser decision.

**Assessment.** **2026-Q3/Q4 are not yet a valid protected evaluation:**

- the inputs (2026 provincial CPI; the missing 2025 rounds) are not in the project;
- the CPI and other input publication dates are unverified under L3/L4;
- the June 2026 round's date is [U];
- the freeze has not been performed.

They **can become** an outcome-blind (retrospective) evaluation if every prerequisite in Section 6 is met **before** any 2026-Q3/Q4 outcome is seen. Even then the test is **at most 10 rows in 2 quarters**, whose five provinces share most inputs. It can give an untouched point estimate, **not** evidence that true accuracy exceeds 75%.

## 6. Prerequisites before any model experiment can be authorized

1. **Approve Rule L (L1–L6),** including the L5 decisions:
   - whether January/February 2025 Stratbase rounds belong in 2025-Q1;
   - how respondent-base changes in early 2025 are handled;
   - how two-round quarters are averaged.
2. **Verify CPI release dates** for the final month of every labelled quarter: 17 dates for 2021-Q2 to 2026-Q1, 2 already done. Confirm whether provincial tables appear on the national release day. psa.gov.ph blocks automated access, so this needs a person, or approval for a documented substitute such as PSA's published Advance Release Calendar.
3. **Document release calendars** (L3b) for regional CPI, wholesale rice, LFS unemployment, BSP remittances, DOE fuel, NOAA ONI, PAGASA, NASA POWER and poverty (re-verify 2022-08-15 and the August 2024 day).
4. **Collect, with approval, the missing pre-2026 SWS rounds:**
   - April 2025 and June 2025 (2025-Q2), and September 2025 (2025-Q3): Balance-Luzon values from the original releases;
   - January and February 2025 only if L5 includes them.

   Their dates are already established (Section 2.1); [L] dates should be confirmed on the pages themselves.
5. **Collect, with approval, 2026 provincial food CPI** (`0012M4ACP23`, January–June 2026) for the 2026-Q3/Q4 inputs and the 2026-Q1 training label.
6. **Verify the June 2026 round's publication date** without recording its value (it is already exposed). This is needed only to settle the 2026-Q3/Q4 SWS input.
7. **Carry out the protection steps** (Section 5, steps 1–2) immediately, and approve steps 3–6 as the evaluation procedure.
8. **Then** authorize the pre-specified comparison (MODEL-B2 primary; MODEL-A configuration, Eq. 3 rule, latest-published-label baseline):
   - development walk-forward under final Rule L, reported as **exploratory**;
   - the frozen 2026-Q3/Q4 forecasts as the only protected evaluation.

**Stopping here for your approval.** No model training or data collection will start without it.
