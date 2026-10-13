# Publication-Date Verification and Rule L Refinement (2026-10-09)

**Authorized scope:** manual verification of SWS and CPI publication dates, and refinement of Rule L.

- **Not done:** no model was run, no dataset was downloaded, and no production code or data, existing evidence, frozen forecast or thesis text was changed. Nothing was committed or deployed.
- **New files:**
  - this report;
  - `evidence/2026-10-09_data_audit/sws_round_publication_dates_verified.csv`;
  - `cpi_release_dates_verified.csv`;
  - `rule_L_refined_vs_implemented.csv`.
- **Corrections:** a correction note has been added at the top of `DATA_AND_EVALUATION_DESIGN_AUDIT_2026-10-09.md`.

Tags: **[V]** verified · **[S]** secondary source (news) · **[A]** assumption · **[U]** unresolved.

---

## 0. Outcome exposure (read this first)

- **2026 outcome values are already in the project.** `docs/provenance/sws_hunger_sources.json` (last modified 2026-09-23, before any frozen forecast) contains **Balance-Luzon hunger values for 2026-Q1 and 2026-Q2**. My earlier statement that they were "not stored" was wrong: I had checked only `sws_hunger.parquet`, which ends at 2025-Q4.
- **I have now seen those values.** They appeared while I listed the file to verify publication dates. Web search summaries also showed **national** SWS figures for March and June 2026.
- **No model used them [V].** `scripts/supplementary/timing_audit.py` is the only code that reads that file, and it reads quarter keys and URL dates only. The 2026 URLs have no `ART-` timestamp and no manual date, so no 2026 round entered any feature or label.
- **Consequences for the 2026 test (Section 4):**
  - Both 2026-Q1 and 2026-Q2 Balance-Luzon values lie above the 14.345 threshold. 2026-Q1 is far above it, so its labels are close to determined before scoring.
  - Any re-freeze for 2026-Q1 or Q2 can still be computationally label-blind and pre-specified, but **not analyst-blind**.
- **What remains unexposed:** to my knowledge, the September 2026 round (2026-Q3) and any 2026-Q4 round. Nothing about them has been read.

## 1. SWS publication dates

**Method:**

- **ART-dated rounds:** each round's archived SWS article was opened in the built-in browser (web.archive.org), extracting only the title and the "by Social Weather Stations | date" line.
- **Other rounds:** SWS media-release filenames (`prYYYYMMDD…`) and dated news coverage.
- **Dates are publication dates, never survey (fieldwork) dates.**
- **Blocked sources:** psa.gov.ph and rsso04a.psa.gov.ph show Cloudflare bot checks, which were **not** bypassed. WebFetch cannot reach web.archive.org.

| Label quarter | SWS round | Publication date | Evidence | Status |
|---|---|---|---|---|
| 2021-Q2 | First Quarter 2021 (survey in May 2021) | 2021-07-12 | Page shows "Jul 12, 2021 01:36:04 PM" = ART-20210712133604 | [V] |
| 2021-Q2 | **Second Quarter 2021 (June 2021): a separate survey** | 2021-07-28 | "Jul 28, 2021 10:00:35 AM" = ART-20210728100035 | [V] |
| 2021-Q3 | Third Quarter 2021 (Sept) | 2021-12-06 | "Dec 06, 2021 10:54:01 AM" | [V] |
| 2021-Q4 | Fourth Quarter 2021 (Dec) | 2022-03-25 | "Mar 25, 2022 06:48:13 AM" | [V] |
| 2022-Q2 | First Quarter 2022 (Apr) | 2022-06-06 | "Jun 06, 2022 10:23:27 AM" | [V] |
| 2022-Q2 | **Second Quarter 2022: a separate survey** | 2022-09-10 | "Sep 10, 2022 03:36:23 PM" | [V] |
| 2022-Q3 | Third Quarter 2022 | 2022-10-29 | "Oct 29, 2022 12:37:38 PM" | [V] |
| 2022-Q4 | Fourth Quarter 2022 | 2023-01-19 | "Jan 19, 2023 06:28:33 AM" | [V] |
| 2023-Q1 | March 2023 | 2023-05-11 | "May 11, 2023 07:37:00 AM" | [V] |
| 2023-Q2 | June 2023 | 2023-08-02 | "Aug 02, 2023 10:03:29 AM" | [V] |
| 2023-Q3 | September 2023 | 2023-11-20 | "Nov 20, 2023 02:38:38 PM" | [V] |
| 2023-Q4 | December 2023 | 2024-01-22 | "Jan 22, 2024 10:07:15 AM" | [V] |
| 2024-Q1 | March 2024 | 2024-04-30 | "Apr 30, 2024 10:57:05 AM" | [V] |
| 2024-Q2 | June 2024 | 2024-07-23 | "Jul 23, 2024 05:57:30 AM" | [V] |
| 2024-Q3 | September 2024 | **2024-10-17** (was 2025-01-14) | Daily Tribune article dated 2024-10-17; an Inquirer column citing the SWS release of 17 Oct 2024. The SWS PDF was not located. | [S] |
| 2024-Q4 | December 2024 | 2025-01-14 | SWS media release `pr20250114-SWR2024-IV-Hunger-in-Families` | [V] (filename date) |
| 2025-Q1 | Stratbase-SWS, March 15–20, 2025 | 2025-03-29 | SWS media release `pr20250329-Stratbase-SWS-Mar-2025-Hunger…`; news coverage 2025-03-30 | [V] |
| 2025-Q2 | **June 2025 round: exists, not in project** | n/a | News coverage gives the national figure; Balance-Luzon value and date not collected | [U] |
| 2025-Q3 | **September 2025 round: exists, not in project** | n/a | Same | [U] |
| 2025-Q4 | November 2025 | **2026-01-14** (was 2026-05-12) | News reports of the SWS release on Wednesday 14 January 2026. The SWS PDF was not located. | [S] |

**Checks on method:**

- **All 14 ART-dated rounds checked [V]:** the archived page date matches the ART timestamp to the second, so the article-ID method used in `timing_audit.py` is confirmed.
- **Media-release filenames:** the `prYYYYMMDD` convention is consistent with known dates (pr20250329 matches the March 2025 release reported on 2025-03-30).

**New data gap.** The project's claim that **2025-Q2 and 2025-Q3 have "no SWS round" is wrong**: SWS ran June and September 2025 surveys. Their Balance-Luzon values are simply missing from the project. Early-2025 monthly Stratbase-SWS rounds (January and February) also exist. Whether rounds exist for 2021-Q1 and 2022-Q1 is [U].

## 2. CPI publication dates

A label also needs the target quarter's last-month provincial food CPI.

| Label quarter | CPI month | National release | Evidence | Status |
|---|---|---|---|---|
| 2022-Q2 | June 2022 | 2022-07-05 (Tuesday) | ABS-CBN 2022-07-05; a PSA regional release is dated 2022-07-06 | [S] |
| 2025-Q1 | March 2025 | **2025-04-04** (Friday) | Philstar, GMA and DZRH, 2025-04-04 | [S] |

**What remains unverified:**

- **Whether provincial CPI tables appear on the national release day** is [U]. One example shows the regional release one day later. OpenStat's folder timestamp (2026-10-06) matches the timing of the September 2026 national release.
- **Other CPI months:** I did not verify them individually. In every other labelled quarter, the SWS publication date is at least 23 days after the quarter ends, while PSA national CPI comes out in the first week of the following month [S, from the two cases above and PSA's monthly QuickStat practice]. So **SWS is the binding date** wherever the CPI release falls within about 3 weeks of quarter end [A].

## 3. Rule L, refined

**Rule L (refined).** A label for quarter *q* may be used as a **training label** (or an inner-validation target) for a forecast of quarter *T* only if

> **label_published(q) < start of T**, where
> **label_published(q) = the later of:**
> - the publication date of the **last** SWS round averaged into *q*'s label;
> - the provincial-CPI publication date for *q*'s last month.
>
> The CPI date is the verified national release where known. Otherwise it is assumed to be the quarter end + 10 days, an [A] to be confirmed.

**Companion rule for inputs.** The SWS **feature** for target *T* is the latest **round** (each round separately) whose verified publication date is before the start of *T*. If a round's date is only a secondary-source date [S], it is used as stated. If no date is documented, the round is excluded.

**Refined label publication dates:**

- 2025-Q1: **2025-04-04**, set by the CPI release (verified).
- 2022-Q2: **2022-09-10**, set by the second SWS round.
- 2021-Q2: **2021-07-28**, set by the second round.
- 2024-Q3: **2024-10-17** [S].
- 2025-Q4: **2026-01-14** [S].
- All other labels: their single verified SWS date.

**Effect versus the implemented rule** (`rule_L_refined_vs_implemented.csv`; date arithmetic only):

| Forecast target (origin) | Training labels: implemented → refined | SWS feature round: implemented → refined | Role in earlier studies |
|---|---|---|---|
| 2022-Q3 (2022-07-01) | 4 → **3** (2022-Q2 removed: its second round was published 2022-09-10) | 2022-Q2 → 2022-Q2 | Training / inner validation |
| 2025-Q1 (2025-01-01) | 12 → **13** (2024-Q3 added: published 2024-10-17) | **2024-Q2 → 2024-Q3** | **Outer test fold.** It used a stale SWS value and one fewer label than was actually available. |
| 2025-Q2 (2025-04-01) | 15 → **14** (2025-Q1 removed until 2025-04-04) | 2025-Q1 → 2025-Q1 | No label (no target) |
| 2025-Q4 (2025-10-01) | 15 → 15 | 2025-Q1 → 2025-Q1 | **Outer test fold.** The true latest round (June or September 2025) is **missing from the project**, so this fold is under-informed. |
| 2026-Q1 (2026-01-01) | 15 → 15 | 2025-Q1 → 2025-Q1 | Frozen 2026 forecasts. The true latest round is September 2025, which is missing. |
| 2026-Q2 (2026-04-01) | 15 → **16** (2025-Q4 added) | **2025-Q1 → 2025-Q4** | Frozen 2026 forecasts used a stale SWS value and lacked the 2025-Q4 label |
| All other origins | Unchanged | Unchanged | none |

**Correction to the earlier finding.** The origin-information study said that in the 2025-Q1 fold, *two* training labels (2024-Q3 and 2024-Q4) were unreleased at the origin. With verified dates, only **2024-Q4** was unreleased. 2024-Q3 was published on 2024-10-17, so it was legitimately available. The leak finding for the other six folds stands, since their dates are verified [V].

**What still needs verifying:**

- **SWS PDFs** for the September 2024 and November 2025 releases. These dates rest on news coverage [S]. psa.gov.ph and the SWS PDF index were not reachable, or were not attempted beyond search.
- **Provincial-CPI release timing** relative to the national release [U].
- **June and September 2025 SWS rounds:** their Balance-Luzon values and publication dates are not in the project. Collecting them is a data download and needs approval.

## 4. Can the existing 2026 forecasts be validly re-frozen without outcome information?

**The existing frozen 2026 forecasts should not be used as the final test:**

1. **They used the wrong information sets (verified above).**
   - 2026-Q1 used the March 2025 SWS value, although the September 2025 round had been published (it is missing from the project).
   - 2026-Q2 used March 2025 instead of November 2025, and lacked the 2025-Q4 training label.
   - These are not leaks, but they don't simulate what was knowable at each forecast date.
2. **Outcome information for 2026-Q1 and Q2 is in the project and has been seen.**

**A valid re-freeze is possible only in a limited sense:**

- **2026-Q1 and 2026-Q2:** a re-freeze could be made computationally label-blind, using a procedure fixed before exposure (Section 5 of the evaluation-design report was written before I read the file). But it **cannot be analyst-blind**, and 2026-Q1's labels are close to determined by the stored SWS value. **Recommendation:** report any 2026-Q1/Q2 result only as a disclosed, non-independent check, not as the final test.
- **2026-Q3 (September 2026 round) and 2026-Q4:** **not yet exposed** to my knowledge. These are the only remaining candidates for an outcome-blind final test within the window. Two safeguards:
  - No one should open SWS pages or files about September/December 2026 hunger until forecasts are frozen.
  - The frozen forecasts need inputs that are missing: provincial CPI for 2026-Q1/Q2 from OpenStat `0012M4ACP23`, plus the June and September 2025 and November 2025 SWS rounds with verified dates.
- **Size caveat:** even then, the final test is 1–2 quarters (5–10 rows). As the correction notes, such a test cannot establish true accuracy above 75%. It can only provide an untouched point estimate.

## 5. Proposed next steps (each awaits your approval)

1. **Adopt Rule L (refined) and its input companion rule** (Section 3) as the timing standard for all future runs.
2. **Authorize collection of the missing pre-2026 data within the window:**
   - SWS Balance-Luzon values for June and September 2025, with publication dates, and the early-2025 Stratbase rounds if they are to be treated as rounds;
   - first-publication confirmation for September 2024 and November 2025.
3. **Decide the final-test policy:**
   - designate 2026-Q3 (and Q4) as the protected final test;
   - restrict access to their outcomes until forecasts are frozen;
   - treat 2026-Q1/Q2 as disclosed, non-independent checks.
4. **Only then** authorize the pre-specified comparison:
   - walk-forward under refined Rule L as exploratory development;
   - the frozen 2026-Q3/Q4 forecasts as the final test, using MODEL-B2 (primary), MODEL-A configuration, the Eq. 3 rule and the latest-published-label baseline.
5. **Monthly CPI and rice data** after the timing rules are settled (`DATA_COMPLETENESS_AUDIT_2026-10-09.md`).

**Stopping here for your review.**

---

### Sources consulted (read-only)

- SWS archived articles (via web.archive.org, built-in browser), for example the [March 2023 report](https://web.archive.org/web/2024id_/https://www.sws.org.ph/swsmain/artcldisppage/?artcsyscode=ART-20230511073700) and the 13 other ART-dated rounds listed above (URLs in `docs/provenance/sws_hunger_sources.json`)
- SWS media releases: [pr20250114 (Q4 2024 hunger)](https://sws.org.ph/wp-content/uploads/2026/06/pr20250114-SWR2024-IV-Hunger-in-Families-media-release-1.pdf); [pr20250329 (Stratbase-SWS March 2025)](https://sws.org.ph/wp-content/uploads/2026/07/pr20250329-Stratbase-SWS-Mar-2025-Hunger-in-Families-media-release.pdf)
- September 2024 release: [Daily Tribune, 2024-10-17](https://tribune.net.ph/2024/10/17/229-of-filipinos-experienced-3q-hunger); [Inquirer opinion](https://opinion.inquirer.net/177856/backsliding-in-hunger); [GMA](https://gmanetwork.com/news/topstories/nation/924100/filipinos-involuntary-hunger-up-22-9-in-september/story)
- November 2025 release (14 Jan 2026): [Inquirer Plus](https://plus.inquirer.net/?p=365020); [GMA](https://www.gmanetwork.com/news/topstories/nation/981981/sws-survey-pinoys-scores-november/story/); [Manila Bulletin (SWS tag)](https://mb.com.ph/tag/sws)
- March 2025 Stratbase-SWS: [Inquirer, 2025-03-30](https://newsinfo.inquirer.net/2048156/sws-hunger-rate-at-27-2-highest-since-pandemic)
- CPI releases: [ABS-CBN, June 2022 inflation, 2022-07-05](https://news.abs-cbn.com/business/07/05/22/inflation-rises-again-hits-61-percent-in-june); [Philstar, March 2025 inflation, 2025-04-04](https://www.philstar.com/business/2025/04/04/2433478/inflation-eases-18-march-2025/amp/); [GMA](https://gmanetwork.com/news/money/economy/941627/inflation-eases-further-to-1-8-in-march-2025/story); [DZRH](https://www.dzrh.com.ph/post/ph-inflation-rate-slowed-down-to-18percent-in-march-2025-psa)
- PSA OpenStat table metadata (`evidence/2026-10-09_data_audit/openstat_metadata_snapshot_2026-10-09.json`)
- psa.gov.ph and rsso04a.psa.gov.ph: blocked by bot verification; not bypassed


---

### Corrections appended later on 2026-10-09 (original text above preserved)

See `docs/RULE_L_FINAL_AND_PROTECTED_EVALUATION_PLAN_2026-10-09.md`.

1. **September 2024** is now **[V]** on the original SWS page (`ART-20241017131004`, "Oct 17, 2024 01:10:04 PM"), no longer [S].
2. **November 2025** (2026-01-14) is confirmed by SWS's own listing [L], in addition to news.
3. **2025-Q2 has two missing rounds, not one:** April 23–28, 2025 (published 2025-06-27 [V]) and June 2025 (2025-08-15 [L]). September 2025 was published 2025-11-05 [L]. January and February 2025 Stratbase-SWS hunger readings also exist (dates [U]).
4. **The 2026-Q1/Q2 values are also in production code:** the hand-curated table in `app/ml/corpus/sws_hunger_fetcher.py` (`SWS_COVERAGE_END = (2026, 2)`), not only in the provenance JSON.
5. **Rule L is final in the new document.** L3/L4 now treat **unverified** CPI and other input dates as **not available**, superseding the "quarter end + 10 days" assumption stated above.
