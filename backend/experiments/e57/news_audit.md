# News card audit (E53 record, lead 2 served)

## Where the card's number and list come from (read-only)

- **Frontend:** `frontend/src/components/RightAnalyticsPanel.tsx`, `NewsArticlesCardBody` (line ~213). It calls `useNews(scope, id, quarterId, 1, 20, "published")`, i.e. `GET /api/v1/news?scope=region|province&id=calabarzon|<province>&quarter=<q>&page=1&pageSize=20&view=published`. The number is `articleCount` (falling back to the province's `/provinces` `articleCount`); the list is `data` (first page only, 20 rows).
- **Backend:** `app/api/v1/insights.py` `get_news` -> `app/services/dashboard.py` `news` -> `_e31_news`. With `view=published` it returns the record's validated articles (`news.articles`, relevance rule R1.1) of the quarter itself; a quarter that has not started returns none, with a note.
- **Other counts of the same thing:** `/provinces` `articleCount` (Data page, card fallback), `/explainability` `articleCount`, and `limitedSignal` (`/provinces`, `/forecast` region `provinceCounts.limited`, LGU rows; the left panel's 'Limited data' chip and the badges).

Columns: **card** = `articleCount` of the card's own call; **list** = articles returned over all pages; **true** = record articles of that province (region: the five, de-duplicated) whose Philippine publication date is inside the quarter; **geocoded** = all province-geocoded articles in `data/news_e31/articles.jsonl` (before the relevance rule; for reference); **explain** = `/explainability` `articleCount`; **limited** = `limitedSignal`; dates = min/max publication date of the listed articles.

## Phase A: before the fix

| Quarter | Subject | card | list | true | geocoded | explain | limited | first date | last date | outside quarter | dup URL/title | region = union |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2026-Q1 | calabarzon | 5 | 5 | 5 | 164 | 5 | no | 2026-01-20 | 2026-03-31 | 0 | 0/0 | yes |
| 2026-Q1 | cavite | 2 | 2 | 2 | 30 | 2 | yes | 2026-03-12 | 2026-03-16 | 0 | 0/0 | – |
| 2026-Q1 | laguna | 2 | 2 | 2 | 24 | 2 | no | 2026-01-20 | 2026-03-31 | 0 | 0/0 | – |
| 2026-Q1 | batangas | 1 | 1 | 1 | 40 | 1 | yes | 2026-02-11 | 2026-02-11 | 0 | 0/0 | – |
| 2026-Q1 | rizal | 0 | 0 | 0 | 35 | 0 | no | – | – | 0 | 0/0 | – |
| 2026-Q1 | quezon | 0 | 0 | 0 | 35 | 0 | no | – | – | 0 | 0/0 | – |
| 2026-Q2 | calabarzon | 15 | 15 | 15 | 190 | 15 | no | 2026-04-08 | 2026-06-26 | 0 | 0/0 | yes |
| 2026-Q2 | cavite | 3 | 3 | 3 | 53 | 3 | yes | 2026-04-09 | 2026-06-17 | 0 | 0/0 | – |
| 2026-Q2 | laguna | 2 | 2 | 2 | 27 | 2 | yes | 2026-04-16 | 2026-05-25 | 0 | 0/0 | – |
| 2026-Q2 | batangas | 3 | 3 | 3 | 32 | 3 | yes | 2026-05-22 | 2026-06-26 | 0 | 0/0 | – |
| 2026-Q2 | rizal | 5 | 5 | 5 | 29 | 5 | no | 2026-04-08 | 2026-04-13 | 0 | 0/0 | – |
| 2026-Q2 | quezon | 2 | 2 | 2 | 49 | 2 | no | 2026-04-24 | 2026-05-17 | 0 | 0/0 | – |
| 2026-Q3 | calabarzon | 9 | 9 | 9 | 262 | 9 | no | 2026-07-14 | 2026-09-11 | 0 | 0/0 | yes |
| 2026-Q3 | cavite | 0 | 0 | 0 | 57 | 0 | yes | – | – | 0 | 0/0 | – |
| 2026-Q3 | laguna | 7 | 7 | 7 | 52 | 7 | yes | 2026-07-14 | 2026-09-01 | 0 | 0/0 | – |
| 2026-Q3 | batangas | 0 | 0 | 0 | 73 | 0 | yes | – | – | 0 | 0/0 | – |
| 2026-Q3 | rizal | 2 | 2 | 2 | 40 | 2 | no | 2026-07-23 | 2026-09-11 | 0 | 0/0 | – |
| 2026-Q3 | quezon | 0 | 0 | 0 | 40 | 0 | yes | – | – | 0 | 0/0 | – |
| 2026-Q4 | calabarzon | 3 | 3 | 3 | 55 | 9 | no | 2026-10-09 | 2026-10-13 | 0 | 0/0 | yes |
| 2026-Q4 | cavite | 0 | 0 | 0 | 13 | 0 | no | – | – | 0 | 0/0 | – |
| 2026-Q4 | laguna | 0 | 0 | 0 | 8 | 7 | no | – | – | 0 | 0/0 | – |
| 2026-Q4 | batangas | 2 | 2 | 2 | 17 | 0 | no | 2026-10-09 | 2026-10-09 | 0 | 0/0 | – |
| 2026-Q4 | rizal | 0 | 0 | 0 | 7 | 2 | yes | – | – | 0 | 0/0 | – |
| 2026-Q4 | quezon | 1 | 1 | 1 | 10 | 0 | no | 2026-10-13 | 2026-10-13 | 0 | 0/0 | – |
| 2027-Q1 | calabarzon | 0 | 0 | 0 | 0 | 9 | no | – | – | 0 | 0/0 | yes |
| 2027-Q1 | cavite | 0 | 0 | 0 | 0 | 0 | no | – | – | 0 | 0/0 | – |
| 2027-Q1 | laguna | 0 | 0 | 0 | 0 | 7 | no | – | – | 0 | 0/0 | – |
| 2027-Q1 | batangas | 0 | 0 | 0 | 0 | 0 | no | – | – | 0 | 0/0 | – |
| 2027-Q1 | rizal | 0 | 0 | 0 | 0 | 2 | yes | – | – | 0 | 0/0 | – |
| 2027-Q1 | quezon | 0 | 0 | 0 | 0 | 0 | no | – | – | 0 | 0/0 | – |

## After the fix (Phase B)

| Quarter | Subject | card | list | true | geocoded | explain | limited | first date | last date | outside quarter | dup URL/title | region = union |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2026-Q1 | calabarzon | 5 | 5 | 5 | 164 | 5 | yes | 2026-01-20 | 2026-03-31 | 0 | 0/0 | yes |
| 2026-Q1 | cavite | 2 | 2 | 2 | 30 | 2 | yes | 2026-03-12 | 2026-03-16 | 0 | 0/0 | – |
| 2026-Q1 | laguna | 2 | 2 | 2 | 24 | 2 | yes | 2026-01-20 | 2026-03-31 | 0 | 0/0 | – |
| 2026-Q1 | batangas | 1 | 1 | 1 | 40 | 1 | yes | 2026-02-11 | 2026-02-11 | 0 | 0/0 | – |
| 2026-Q1 | rizal | 0 | 0 | 0 | 35 | 0 | yes | – | – | 0 | 0/0 | – |
| 2026-Q1 | quezon | 0 | 0 | 0 | 35 | 0 | yes | – | – | 0 | 0/0 | – |
| 2026-Q2 | calabarzon | 15 | 15 | 15 | 190 | 15 | no | 2026-04-08 | 2026-06-26 | 0 | 0/0 | yes |
| 2026-Q2 | cavite | 3 | 3 | 3 | 53 | 3 | yes | 2026-04-09 | 2026-06-17 | 0 | 0/0 | – |
| 2026-Q2 | laguna | 2 | 2 | 2 | 27 | 2 | yes | 2026-04-16 | 2026-05-25 | 0 | 0/0 | – |
| 2026-Q2 | batangas | 3 | 3 | 3 | 32 | 3 | yes | 2026-05-22 | 2026-06-26 | 0 | 0/0 | – |
| 2026-Q2 | rizal | 5 | 5 | 5 | 29 | 5 | no | 2026-04-08 | 2026-04-13 | 0 | 0/0 | – |
| 2026-Q2 | quezon | 2 | 2 | 2 | 49 | 2 | yes | 2026-04-24 | 2026-05-17 | 0 | 0/0 | – |
| 2026-Q3 | calabarzon | 9 | 9 | 9 | 262 | 9 | no | 2026-07-14 | 2026-09-11 | 0 | 0/0 | yes |
| 2026-Q3 | cavite | 0 | 0 | 0 | 57 | 0 | yes | – | – | 0 | 0/0 | – |
| 2026-Q3 | laguna | 7 | 7 | 7 | 52 | 7 | no | 2026-07-14 | 2026-09-01 | 0 | 0/0 | – |
| 2026-Q3 | batangas | 0 | 0 | 0 | 73 | 0 | yes | – | – | 0 | 0/0 | – |
| 2026-Q3 | rizal | 2 | 2 | 2 | 40 | 2 | yes | 2026-07-23 | 2026-09-11 | 0 | 0/0 | – |
| 2026-Q3 | quezon | 0 | 0 | 0 | 40 | 0 | yes | – | – | 0 | 0/0 | – |
| 2026-Q4 | calabarzon | 3 | 3 | 3 | 55 | 3 | yes | 2026-10-09 | 2026-10-13 | 0 | 0/0 | yes |
| 2026-Q4 | cavite | 0 | 0 | 0 | 13 | 0 | yes | – | – | 0 | 0/0 | – |
| 2026-Q4 | laguna | 0 | 0 | 0 | 8 | 0 | yes | – | – | 0 | 0/0 | – |
| 2026-Q4 | batangas | 2 | 2 | 2 | 17 | 2 | yes | 2026-10-09 | 2026-10-09 | 0 | 0/0 | – |
| 2026-Q4 | rizal | 0 | 0 | 0 | 7 | 0 | yes | – | – | 0 | 0/0 | – |
| 2026-Q4 | quezon | 1 | 1 | 1 | 10 | 1 | yes | 2026-10-13 | 2026-10-13 | 0 | 0/0 | – |
| 2027-Q1 | calabarzon | 0 | 0 | 0 | 0 | 0 | yes | – | – | 0 | 0/0 | yes |
| 2027-Q1 | cavite | 0 | 0 | 0 | 0 | 0 | yes | – | – | 0 | 0/0 | – |
| 2027-Q1 | laguna | 0 | 0 | 0 | 0 | 0 | yes | – | – | 0 | 0/0 | – |
| 2027-Q1 | batangas | 0 | 0 | 0 | 0 | 0 | yes | – | – | 0 | 0/0 | – |
| 2027-Q1 | rizal | 0 | 0 | 0 | 0 | 0 | yes | – | – | 0 | 0/0 | – |
| 2027-Q1 | quezon | 0 | 0 | 0 | 0 | 0 | yes | – | – | 0 | 0/0 | – |

## Flags

| Check | Before | After |
|---|---|---|
| (a) future / not-started quarter (2027-Q1) with articles or a non-zero count | 5: 2027-Q1|calabarzon: card 0, explain 9; 2027-Q1|laguna: card 0, explain 7; 2027-Q1|laguna: explain/provinces articleCount 7 vs card 0; 2027-Q1|rizal: card 0, explain 2; 2027-Q1|rizal: explain/provinces articleCount 2 vs card 0 | 0 |
| (b) a count that differs from the card's list (card, list, true, explain, /provinces) | 4: 2026-Q4|batangas: explain/provinces articleCount 0 vs card 2; 2026-Q4|laguna: explain/provinces articleCount 7 vs card 0; 2026-Q4|quezon: explain/provinces articleCount 0 vs card 1; 2026-Q4|rizal: explain/provinces articleCount 2 vs card 0 | 0 |
| (c) listed articles published outside the selected quarter | 0: none | 0 |
| (d) region count != de-duplicated union of the five provinces | 0: none | 0 |
| (e) limitedSignal inconsistent with the province's article count (< 5) | 14: 2026-Q1|laguna: 2 articles, limited=False; 2026-Q1|quezon: 0 articles, limited=False; 2026-Q1|rizal: 0 articles, limited=False; 2026-Q2|quezon: 2 articles, limited=False; 2026-Q3|laguna: 7 articles, limited=True; 2026-Q3|rizal: 2 articles, limited=False; 2026-Q4|batangas: 2 articles, limited=False; 2026-Q4|cavite: 0 articles, limited=False ... | 0 |
| (f) duplicates (same URL or title) counted more than once | 0: none | 0 |

### Findings

- **(a)** The card itself was already right for 2027-Q1 (0 articles, note "2027-Q1 has not started; no news yet. The 2027-Q1 forecast was built on 2026-10-01 from 2026-Q3 news."). But `/explainability` and `/provinces` `articleCount` for 2027-Q1 (and 2026-Q4) counted the forecast's *evidence* quarter (2026-Q3): CALABARZON 9, Laguna 7, Rizal 2. The Data page and the card's fallback show that number. **Fixed.**
- **(b)** Card = list = true count in every cell; only the other two count fields disagreed (as in (a), for the two forecast quarters). **Fixed**: all count fields now use the card's own count.
- **(c)** None: every listed article is inside its quarter (the record's `quarter` field agrees with the publication date for all 140 articles). The count now filters on the publication date itself.
- **(d)** None: the region count already equals the de-duplicated union (each article has one province). The explainability region count now uses the union instead of the sum.
- **(e)** Confirmed: `limitedSignal` came from the record's stored status of the forecast's **evidence quarter** (the previous quarter), and a status of 0 articles (`NO_USABLE_EVIDENCE`) was never flagged. E.g. 2026-Q3 Laguna 7 articles flagged limited; Rizal 2 articles not flagged; 2026-Q1 Rizal and Quezon 0 articles not flagged. **Fixed**: limited = fewer than 5 articles on the card's own count, for every province, the region's `provinceCounts.limited` and every LGU of the province.
- **(f)** None (0 duplicate URLs or titles in any list). The count now de-duplicates by key, link and title anyway, and a test injects duplicates.
- **Definition note.** The paper's limited signal is "fewer than 5 geocoded articles". The record's own status, and now the dashboard, count *validated* articles (relevance rule R1.1, the ones the card lists); the geocoded counts (column 'geocoded') are 7-262 per cell and would almost never be limited. Using the card's count follows the instruction 'computed from the same counts'; the manuscript should say "fewer than 5 validated (relevant) geocoded articles".
- **Frontend only (not changed):** the card fetches page 1 with `pageSize` 20 and has no "more" control, so a quarter with more than 20 articles would list only 20 under a larger count. No quarter exceeds 20 today (maximum 15), so nothing is wrong yet. Change needed: `frontend/src/components/RightAnalyticsPanel.tsx:224`, either `useNews(scope, id, quarterId, 1, 100, "published")` (the API allows up to 100) or a 'Show more' button that increments `page`.
- Unchanged on purpose: `view=used` (the articles the forecast was built from) and the record's articles; nothing the model used changed.

