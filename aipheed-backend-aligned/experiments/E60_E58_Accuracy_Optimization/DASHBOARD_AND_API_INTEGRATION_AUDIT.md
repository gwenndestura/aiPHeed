# Dashboard and API integration audit (E60)

**Inspected:**
- `backend/app/api/v1/{insights,lead2,provinces}.py`;
- `backend/app/services/dashboard.py`, especially `_news_pool`, `_e31_news`, `e31_news_evidence` and `plain_summary`;
- `backend/app/ml/inference/e41_lead2.py`.

**In-process API calls** (FastAPI TestClient, `AIPHEED_LEAD2_MODEL=e58`, clock 2026-10-17). The local preview server was not running.

**Production default:** the code default is still `e38`. `origin/e46-lead2-policy` is at 88d5266 (pushed on 2026-10-18 per project memory); the Render environment setting was not visible to this audit.

## 1. What the existing serving path can already supply

| Requirement | Status in the e58 path | Evidence |
|---|---|---|
| Province probability and class | yes: P(HIGH) per province; band; decision at 0.5 | `/provinces`, `/lead2/summary` |
| Target quarter and lead | yes: target 2027-Q1, issued 2026-10-01, two quarters ahead; `dataFreshness` | `/lead2/summary` (E56/E58) |
| Municipal / city prioritization | yes, labelled "relative prioritization …; not validated municipal forecasts" | `/provinces/{id}/municipalities` |
| Model explanations | yes: exact TreeSHAP grouped by trigger; hunger gate separate | `/explainability` |
| Relevant news with source links | yes: title, outlet, date, URL, province, trigger tags, "collected retrospectively" flag | `/news` |
| Trigger categories and evidence | yes: five cards with status and evidence notes | `/explainability` |
| Data sufficiency | yes: dataStatus (sufficient / limited), thin-news flag | `/explainability` summary |
| E58 early-warning status | yes: ALERT / EMERGING / NONE, direction, latest hunger reading | `/explainability` summary `earlyWarning` |
| Historical records | yes: as-of backtests per past quarter (labelled backtest); frozen prospective files | E56/E58 records |

## 2. Defects and weaknesses found

1. **News evidence uses the deployed v1 keyword classifier.**
   - On the EVAL annotation half, v1 relevance precision is **0.28** (23 false positives in 77 titles: weather bulletins, flood-control politics, and similar) and recall 0.56.
   - The feed's `FOOD_CONTEXT` filter removes some of these, but titles such as generic typhoon bulletins can still appear as "trigger keyword match".
   - v2 (E60): precision **0.92**, recall 0.75.
2. **Thin provincial news.** For the 2027-Q1 forecast, Quezon has 3 qualifying articles. The feed extends back to 2025-Q4 to reach its minimum of 5. The note says so, but the reader sees older items beside a 2027-Q1 forecast.
3. **Timing note for Lead-2 backtests.**
   - For a past quarter (for example 2026-Q3, a Lead-2 backtest issued 2026-04-01), the feed note reads "its one-quarter-ahead estimate was made with the previous quarter's news". That describes the E31 Lead-1 convention.
   - Under e56/e58 the estimate used news of quarter t = 2026-Q1, two quarters earlier.
   - This is a **wording defect**. No timing leak: the forecast window itself (2026-Q3 news for the 2027-Q1 forecast, nothing published after 2026-10-01) was checked and is correct.
4. **News is shown as evidence, but the served model barely uses it.** In E56/E58, news reached a tree split at 2 of 12 origins (E59). In E60 the news-enhanced candidate C did not improve the forecast. The dashboard should not imply that the listed articles drove the probability.

## 3. Integration decision

**No new forecasting model is integrated.**
- The E60 final candidate (A, government-only) does not meet the pre-registered improvement criterion over E58-EW: paired Brier CI [−0.006, +0.001].
- A and E58-EW differ in one of 50 province-quarters.
- News did not add measurable value (C vs A).

**Proposed changes** (not applied; each needs your OK, and none changes the approved visual design):
- **P1:** switch the news-feed relevance filter in `_news_pool` from v1 keywords to classifier v2, and add the E60 trigger corpus as a source. This changes which articles are listed, not how they look. EVAL precision rises from 0.28 to 0.92.
- **P2:** correct the Lead-2 backtest note text (defect 3).
- **P3:** add one sentence to the e58 explanation note: "News articles are shown as context; the forecast is driven mainly by provincial CPI."

**Rollback:** E38 remains the code default. E56 and E58 remain selectable by environment variable.
