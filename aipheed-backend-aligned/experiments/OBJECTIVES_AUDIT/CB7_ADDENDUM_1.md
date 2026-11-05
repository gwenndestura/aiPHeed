# CB7 Addendum 1: news source switched to the teammate's FI6-N publisher archive (2026-11-04, before any scoring)

`CB7_PREREGISTRATION.md` (f616407e…) is unchanged except for the source in "Index" step 1.

- **Before this addendum:** only 10 weekly GDELT files were fetched, and none was classified, scored or used.
- **Why:** GDELT throttles this computer (about 1.5 days for the fetch), and a paid BigQuery scan was declined.

## New source

**File:** `news_g/teammate/aiPHeed_Best_News_Dataset_FI6N.xlsx`, SHA-256
`36aee994ab3d8af6d23f1ec78a3dbfae376407e6ce127eacd45833422b50ff79`, sheet `Articles`. Shared by a team member; credit
in the report.

**What it holds:**
- 2,641 articles that the teammate's XLM-R relevance step kept, from a 62,698-article publisher archive (Rappler 95%,
  VERA Files, NewsBytes, PCIJ);
- 2012–2026;
- 500 articles restating official statistics (including 107 SWS hunger reports, the target) already removed.

**Fields used:** `published` (publication time), `title`, `link`, `site`.

**One source across both eras,** as the plan requires; it replaces the GDELT DOC query.

## Everything else unchanged

- Our classifier v2 on titles, then de-duplication.
- Our XLM-RoBERTa FSSI-v2 scorer.
- G(t) = mean over quarter t (n ≥ 5, else NaN); `z_G` as `add_news_anomaly`.
- The leakage check.
- C-B7 = C-B6 + `z_G`.
- Evaluation and acceptance.

## Disclosed limitations

- Selection by the teammate's relevance model: 2,641 of 62,698 kept.
- Source concentration: 95% Rappler.
- Their labels are AI-generated, not human-verified.
- Few articles before 2012: those quarters are NaN.
PLAN-SHA256: 99dc56d77a64fd91c18bef9548cb400f0bdaaef941e344a566f792e043be408b
