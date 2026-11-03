# OLD_NEWS: can the news inputs be rebuilt for 2015-Q1..2020-Q4? (feasibility, report only)

**Written:** 2026-11-03. Metadata only: no article text was downloaded, no model or feature was changed, nothing was
retrained. **No BigQuery query was run**: only `bq --dry_run` cost estimates, which read no data and bill nothing.

**Files:**
- `runner/counts.py` → `out/counts_quarterly.csv` and `out/counts_summary.json`;
- `data/gdelt_doc_timeline_2017_2026.json`: the GDELT DOC 2.0 response, SHA-256 `3a04943a…`;
- `runner/cdx_counts.py` → `data/wayback_cdx_counts_partial.json`;
- `data/gkg_v1_2015_2020_DRYRUN_ONLY.sql`: the query that was estimated, not run.

## 1. Which news inputs exist, and what each would need

| Input | Used where | Built from | Exists before 2021? |
|---|---|---|---|
| `N1R` (regional FSSI-v3) | REF+news model input | Project RSS/news corpus, classified and scored with XLM-RoBERTa | **No**: the corpus starts in 2021-Q1 (0 articles before) |
| Six E112 category shares | REF+news model input | The same corpus (title lexicon) | **No** |
| `G_pri_yoy` (GDELT price news, year on year) | REF+news model input | GDELT (FIRI_V2 table) | No (2021+ only) |
| E85 GDELT categories (`g_*`, `gp_*`) | Explanation sentences and the staged news flag only | GDELT GKG 2.1 via BigQuery | No (the query covered 2021-01..2026-10) |

So "rebuilding news for 2015–2020" means two different jobs:
- **(A) GDELT categories**, from the GKG archive, which starts 2015-02-19;
- **(B) FSSI-v3 and the corpus shares**, which need old article pages, i.e. the Wayback Machine.

## 2. Available CALABARZON food-related articles per quarter (metadata)

**GDELT DOC 2.0 API** (the same instrument in both eras; free; covers 2017-01 onward). The query is Philippine
sources matching (Batangas OR Cavite OR Laguna OR Rizal OR Calabarzon) AND (rice OR food OR hunger OR prices).
"Monitored" is the total number of articles GDELT processed that quarter.

| Period | Matching articles per quarter (median) | Monitored per quarter (median) | Matching per 100k monitored (median) |
|---|---|---|---|
| **2017-Q1..2020-Q4** | **780** (range 658–1,837) | 45.6 M | **2.23** |
| **2021-Q1..2026-Q3** | **358** (range 197–887) | 15.2 M | **2.22** |

Quarter detail (2017–2020; full table in `out/counts_quarterly.csv`):

| Year | Q1 | Q2 | Q3 | Q4 |
|---|---|---|---|---|
| 2017 | 1,705 | 1,837 | 1,587 | 1,520 |
| 2018 | 684 | 735 | 751 | 658 |
| 2019 | 665 | 684 | 808 | 939 |
| 2020 | 1,246 | 1,145 | 752 | 724 |

Per 100k monitored, 2017 is about 2.5–3.2, then **2018-Q1..2019-Q2 drops to about 1.4–1.5**, and 2020 is back at
2.1–3.2. Only 7 of the 1,458 days in 2017–2020 have zero matches.

**GDELT GKG, 2021+** (E85's stored rows, E85's de-duplication and province rule):

| Measure | Median per quarter |
|---|---|
| All records | 2,541 |
| Food, price or farm themed | 1,725 |
| Batangas | 954 |
| Rizal | 868 |
| Cavite | 556 |
| Laguna | 439 |
| Quezon | 153 |

**GKG for 2015–2020 cannot be counted without the scan.** DOC suggests about 2.2 times the 2021+ volume, i.e. very
roughly 5,000–6,000 records a quarter (an inference, not a count).

**Project corpus (FSSI-v3 / E112), 2021+:**
- collected articles: median **391** a quarter, rising from about 150–190 in 2021 to 700–880 in 2025–2026;
- admitted (classifier-relevant): median **26** a quarter, range 2–100.

N1R needs at least 5 admitted articles, which is not met in 2021-Q4 (2).

**Wayback Machine,** archived article URLs whose path names a CALABARZON place **and** a food word (one capture per
URL; status 200). Only **10 of 26 requests answered**; the CDX index returned 504/502 errors on the rest, and the run
was stopped to avoid loading the archive:

| Outlet | 2015 | 2016 | 2017 | 2018 | 2019 | 2020 | 2021 | 2022 | 2023 |
|---|---|---|---|---|---|---|---|---|---|
| newsinfo.inquirer.net | 31 | 31 | 75 | — | 110 | 172 | — | 194 | — |
| mb.com.ph | 6 | — | **0** | — | — | 32 | — | — | 132 |
| gmanetwork.com/news | — | — | — | — | | | | | |

"—" = request failed. URL-slug matching misses articles whose slug lacks the words, so these are lower bounds.

## 3. Time and cost

| Job | Steps | Cost | Time | Risk |
|---|---|---|---|---|
| **(A) GDELT categories 2015-02..2020-12** | (1) Run E85's actual query (`gdelt_query_v1.sql`, V1 `Themes`/`Locations` columns) with the partitions moved to 2015-02-18..2020-12-31. (2) Rebuild the features with `e85_features.py` unchanged. (3) Report the coverage checks below | **Dry run: 995,515,666,287 bytes = 0.905 TiB.** Calibration: the same dry run for E85's 2021+ query gives 597,196,318,972 bytes, exactly what E85 was billed. **Free** if the account's 1 TiB/month free tier is unused that month, otherwise about **US$5.7** (on-demand US$6.25/TiB). Under E85's approved cap of 1.2 × 10¹² bytes | Query minutes; rows about 130 k (est.); features under an hour; plan, checks and report about one working day | Low. **Needs your approval before the scan** |
| (A′) A count-only GKG query (to see 2015–2016 volume first) | `COUNT(DISTINCT …)` by month | **Dry run 1.74 TB.** It is costlier than (A) as written because it uses the V2 columns; a V1 count would be about the same as (A) | Minutes | Not worth it: (A) gives the counts as a by-product |
| **(B) FSSI-v3 and corpus shares 2015–2020** | (1) Build article lists: DOC API article lists for 2017–2020 (250 per call, about 500 calls at 1 per 5 s, about 45 min); for 2015–2016 nothing except Wayback URL enumeration. (2) Fetch the text of about 15,000 candidate pages from Wayback, politely (1 every 3–5 s, about 12–21 h). (3) Relevance classifier v2 and XLM-RoBERTa scoring (CPU, hours) | US$0 | **2–4 days** of run time plus checking | **High.** The Wayback Machine blocked this machine as bot traffic after a handful of downloads today (APIS check) and its CDX index timed out on 16 of 26 count queries |

## 4. Would archive gaps bias the index?

**GDELT categories (A): moderate, and checkable.**
- **Volume.** GDELT processed about 3 times more articles per quarter in 2017–2020 than in 2021+ (45.6 M vs 15.2 M).
  The count features (`g_logn`, `gp_logn`) and the province shrinkage (κ = 20 articles) would therefore read
  "more news" before 2021 for reasons unrelated to food. The **share** features are much less affected: the
  normalized rate is the same in both eras (2.23 vs 2.22 per 100k).
- **Source mix.** The 2018-Q1..2019-Q2 dip to about 1.4–1.5 per 100k, against about 2.2 otherwise, fits a change in
  the outlets GDELT followed, not in the news itself. Category shares shift when the outlet mix shifts.
- **Taxonomy.** GKG 2.1 began on 2015-02-19, so **2015-Q1 is partial (about 6 weeks)**. Theme lists were extended over
  time, which can move a family's share. Both are checkable after the scan by tracking each family's share against
  all CALABARZON-located records.
- **2015–2016** cannot be checked before the scan (the DOC API starts in 2017).

**FSSI-v3 via Wayback (B): high, and not correctable.**
- **Capture is not random.** What the Wayback Machine holds depends on which pages were crawled. Its captures grow
  steeply over time (Inquirer: 31 a year in 2015–2016 vs 172–194 in 2020–2022; Manila Bulletin: 0 in 2017 vs 132 in
  2023), and differ by outlet and by page popularity.
- **A different selection process.** A Wayback-rebuilt 2015–2020 corpus would be selected unlike the 2021+ corpus
  (live RSS and DOC collection). Its level, its variance and the N1R ≥ 5-article rule would mean different things in
  the two eras.
- **Uncorrectable inside the frozen model.** It has no era indicator, and adding one would be a model change.
- **Drift even within 2021+.** The corpus itself grows about fivefold from 2021 to 2026, and admitted counts are often
  below N1R's 5-article floor in 2021.

## 5. Conclusion

1. **(A) is feasible:** about 0.9 TiB, free or about US$6, under a day of work, with E85's code unchanged.
   - Its count features need care: GDELT's volume changed threefold.
   - Its share features look comparable after normalizing (2.23 vs 2.22).
   - The 2018–2019 source-mix dip and the partial 2015-Q1 must be reported.
   - Expectation remains low: E85 found no predictive value for 2021–2026, and news is 2.8% of the model's SHAP
     influence.
   - It would rebuild the **explanation and flag** features, and could rebuild a GDELT version of the E112 shares.
     It **cannot** rebuild `N1R` or the corpus shares that REF+news actually uses.
2. **(B) is not recommended:** 2–4 days of throttled archive downloads with a high block risk, for an index whose
   2015–2020 values would come from a selection process unlike 2021+. That would bias it in a way the frozen model
   cannot absorb.
3. **To proceed with (A):**
   - a short sealed plan first (features, checks and use fixed in advance);
   - then **your explicit approval of the 0.905 TiB BigQuery scan**.
   - I will not run it without that.
