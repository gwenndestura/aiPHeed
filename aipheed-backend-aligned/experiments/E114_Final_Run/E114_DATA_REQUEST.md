# E114: data needed before the protocol can be frozen (Phase 1, step 4)

**Status (2026-10-25).** E114 is paused at Phase 1. No protocol has been written and nothing has been scored. The one input that E114 depends on, the pre-2021 SWS hunger series by area, could not be obtained from any reachable primary source.

## 1. What was tried

| Source | Result |
|---|---|
| sws.org.ph, current WordPress site (REST API) | Reachable. Hunger releases go back only to 2023-08. |
| Old SWS release pages (`sws.org.ph/swsmain/artcldisppage/?artcsyscode=…`) | No longer served by SWS |
| Wayback Machine copies of those pages | The index listed 1,708 archived article codes, including about 600 re-posted in 2015 that likely cover 1998–2014. Page fetches were then refused as suspected bot traffic (HTTP 429). Not circumvented. |
| Mangahas & Torres (2024), "The SWS Surveys of Philippine Hunger, 1998–2024", AJAD 21(2) (PDF on sws.org.ph) | Downloaded and read. The area series appears **only as a chart** (Figure 3), not as a table. Digitising a chart would be estimation, not data, so it was not used. The paper states SWS raw datasets "are open to academic researchers". |
| Inquirer columns by M. Mangahas | HTTP 403 |

**Reachable, so not needed from you:**
- PSA OpenStat API: CPI by commodity group, monthly from January 1994 (table 0012M4ACP28); all-items CPI from 1957; regional YoY;
- NOAA ONI;
- IBTrACS;
- GDELT DOC API (2017 onward; slow, rate-limited).

## 2. File needed (required)

**`sws_area_rounds_1998_2020.csv`** is one row per SWS national hunger survey round, from July 1998 to December 2020: about 88 rounds. Please also confirm or extend 2021+ if SWS's figures differ from ours. Place it in `aipheed-backend-aligned/experiments/E114_Final_Run/data/`.

It uses **the same columns as the existing** `E110_Hunger_Generalization/data/sws_area_rounds.csv`:

| Column | Content | Example |
|---|---|---|
| quarter | Calendar quarter of fieldwork | `2015-Q3` |
| fieldwork | First/last fieldwork date | `2015-09-02/2015-09-05` |
| published | **Date SWS released the result** (needed for real-time vintages) | `2015-10-21` |
| respondent_base | `household heads` / `adults` | `household heads` |
| commissioned | True if sponsored (e.g. Stratbase) | `False` |
| national, metro_manila, balance_luzon, visayas, mindanao | Total Hunger, % of families | `15.7` |
| bl_n | Balance Luzon sample size, if known | `600` |
| area_moe_bl, area_moe_other | Sampling error margins (± points) | `4`, `6` |
| source_type, source | Where each row came from (release title/URL, or "SWS data library") | — |

Optional extras, used if present:
- a `mode` column, `face-to-face` or `mobile phone` (Q1–Q3 2020 were phone surveys);
- moderate and severe hunger by area.

**Where to get it, in order of preference:**
1. **SWS Survey Data Library.** Request "Total, moderate and severe hunger by area (NCR, Balance Luzon, Visayas, Mindanao), all national surveys July 1998 – 2020, with survey and release dates". Contact via https://sws.org.ph (Contact page). The paper above confirms the data are available to academic researchers. A ready-to-adapt request letter is in `E87_Outcome_Gap/DATA_REQUESTS.md` (request C).
2. **The SWS Social Weather Report hunger releases, saved from a normal browser.** Search https://web.archive.org/web/*/sws.org.ph/swsmain/artcldisppage/* for hunger releases, and save each page (Ctrl+S, HTML or PDF) into `E114_Final_Run/data/sws_releases_raw/`. I will parse them and record every value with its source. Each release states the area values and its release date.
3. If neither is possible, tell me whether to compile the series from **news reports** of each release (GMA, Philstar, Rappler, Inquirer), as was done for 2021+ in E110. Expect gaps before about 2010 and secondary-source risk. Every value would carry its article URL.

## 3. What happens when the file arrives

1. **Write and hash `PROTOCOL_E114.md` before any scoring.** It pre-registers both primary analyses:
   - (a) 2021+ only;
   - (b) the full history with the 2025 break handled by a level shift, a break-adjusted series, and with/without-post-break sensitivity. The 2020 phone surveys are flagged as a second mode break.
2. **Collect the reachable covariates with release dates:**
   - PSA CPI food and rice, national and Calabarzon, from 1994;
   - ONI;
   - IBTrACS;
   - PSA palay and unemployment;
   - GDELT DOC news volumes from 2017.
3. **Run the E113 baselines and candidates on both samples**, plus the seasonal state-space model. Then the leakage audit, Holm-corrected DM and MCS, surges (expected 10+ events), conformal coverage with n, and seals.
4. **Deliver the E114 reports listed in the brief:**
   - the reconciled E112–E114 numbers table;
   - adviser decisions;
   - the Objective 5 evaluation package, with the SUS questionnaire and scenarios;
   - the defence Q&A.
