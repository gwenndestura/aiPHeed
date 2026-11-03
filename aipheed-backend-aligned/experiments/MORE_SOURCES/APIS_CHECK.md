# APIS hunger question, 2014–2020: did PSA keep it, and is there a Region IV-A table? (report only)

**Checked:** 2026-11-03. No data was added to any model.

**Access.** psa.gov.ph and the PSA data archive (psada.psa.gov.ph) reject automated access: a Cloudflare challenge,
HTTP 403. The Internet Archive holds every APIS final report, but it blocked repeated downloads as bot traffic after the
first two. **Only the 2019 report was read in full.**

## Findings

| Round | Hunger question asked? | Published hunger table? | Region IV-A value | Evidence |
|---|---|---|---|---|
| **2011** | **Yes**: "During the past three months, did you or any member of your family experience hunger because you did not have money to buy food?" | **Yes**, by region | **Not obtained** (the table exists; the page and PDF were blocked). National: **6%** of families (6.3% in a press column); Eastern Visayas **16%** (highest); poor families 15%, non-poor 3% | [PSA APIS 2011 page](https://psa.gov.ph/statistics/income-expenditure/apis/node/41305); archived [2011 statistical tables 1–35](https://web.archive.org/web/20220520002155/https://psa.gov.ph/sites/default/files/attachments/hsd/article/APIS%202011_Statistical%20Tables%201%20to%2035.pdf) (not downloadable here); [Inquirer column](https://opinion.inquirer.net/79930/two-views-on-poverty-from-the-top-and-the-hungry) |
| 2013 | Not checked (blocked) | Not checked | — | [archived final report](https://web.archive.org/web/20170926161256/http://psa.gov.ph/sites/default/files/2013%20APIS%20Final%20Report.pdf) |
| 2014 | Not checked (blocked) | Not checked | — | [archived final report](https://web.archive.org/web/20170926164552/http://psa.gov.ph/sites/default/files/2014%20APIS%20Final%20Report.pdf) |
| 2016 | Not checked (blocked); PSA's first multidimensional poverty index used a **hunger** indicator from APIS 2016/2017, so an item existed | Not checked | — | [archived report](https://web.archive.org/web/20200628001756/https://psa.gov.ph/sites/default/files/APIS%202016%20Inside%20Pages.pdf); [MPI technical notes](https://www.mppn.org/wp-content/uploads/2018/11/Philippines-mpi-technical-notes.pdf) |
| 2017 | Same MPI evidence: a hunger item existed | Not checked (blocked) | — | [archived final report](https://web.archive.org/web/20181105072550/http://www.psa.gov.ph:80/sites/default/files/2017%20APIS%20FINAL%20REPORT.pdf); PSADA study 257 (variable browser, blocked) |
| **2019** | **Yes, collected**: the report's questionnaire description says the "Other relevant information" section "determines if a family member experienced hunger because he or she did not have food to eat" (p. 4 of the report, p. 24 of the PDF). The wording differs from 2011 ("did not have food to eat", not "no money to buy food") | **No.** None of the report's 33 tables (housing, water, sanitation, education, health, social protection, disaster kits, loans, internet, safety) is a hunger table | — | [archived 2019 final report](https://web.archive.org/web/20220106224249/https://psa.gov.ph/sites/default/files/2019%20APIS_signed.pdf), read in full (151 pages) |
| 2020 | Not checked (download truncated, then blocked) | Not checked | — | [archived final report](https://web.archive.org/web/20210928122954/https://psa.gov.ph/sites/default/files/%5BONSrev-cleared%5D%202020%20APIS%20Final%20Report_rev1%20wo%20comments_ONSF3_signed.pdf) |

**Supporting signal.** A press column found 2011 to be the latest year with a published government (PSA) hunger figure
([Inquirer](https://opinion.inquirer.net/79930/two-views-on-poverty-from-the-top-and-the-hungry)). No news coverage of
APIS hunger figures for 2014–2020 was found.

## Reading

- **What is confirmed.** APIS kept a hunger item in at least 2016, 2017 and 2019. In 2019 its wording changed to "did
  not have food to eat", and **PSA stopped publishing it as a table**: no 2019 regional hunger table exists in the
  report.
- **What a Region IV-A 2014–2020 series would need.** Computing it from the **public-use microdata** (PSADA; free
  registration; PSA terms). It would be one value per APIS year (2014, 2016, 2017, 2019, 2020), with the wording change
  in 2019, and only for the surveyed half-year reference period.
- **What it cannot do.** It cannot be a quarterly label or fix the 2015–2020 R7 failure (one reading per year at
  most). At best it is an annual, CALABARZON-specific face-validity check on the SWS Balance Luzon pattern.
- **Rank in SOURCES.md.** Rank 12 stays where it is, not "near the top": a published Region IV-A series for 2014–2020
  does not exist. A microdata-derived series is possible but annual and inconsistent in wording.
- **To finish the check (manual, in a browser):**
  - download the 2014, 2016, 2017 and 2020 final reports from the archived links above and search them for "hunger";
  - open PSADA study 257 (APIS 2017), and the 2019 and 2020 studies, and search the variable list for "hunger";
  - read the Region IV-A row of the 2011 tables 1–35.
