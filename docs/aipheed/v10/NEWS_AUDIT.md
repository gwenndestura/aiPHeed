# v10 Stage 2: Audit of the news data and pipeline

**Reproduce:**

```bash
cd backend && PYTHONPATH=. venv/Scripts/python.exe scripts/v10_news_audit.py --topics
```

Output: `results/news_audit.json`. All figures below are VERIFIED from that file unless tagged. No target is involved.

## Corpus

| Fact | Value |
|---|---|
| Unique articles (E31 + E60 stores) | 9,667 |
| Source | **Google News RSS only** |
| Outlets | 37 domains; Inquirer, GMA, Manila Bulletin lead |
| **Text** | **Headlines only; no body text** |
| Publication range | 2021-01-01 to 2026-10-14 (174 rows are after the development limit and are excluded) |
| Usable publication timestamp | 100 % (`publisher_pubdate`) |
| **Crawl dates** | **All 14–19 Oct 2026; median 672 days after publication** |
| Language | **0.8 % of titles have ≥ 2 Tagalog tokens**, 1.9 % have ≥ 1 (token rule, not a language model) |
| Province assigned | 32.9 %; the other 67 % are broader-area |
| Near-duplicates | 24 exact titles after stripping outlet; 1.6 % of the relevant set |

## Sparsity (the central finding)

Province-quarter cells, 2021-Q1…2026-Q3: **115**.

| Relevant articles (score ≥ 0.30, status OK) | Cells |
|---|---|
| **0** | **68 (59 %)** |
| 1–2 | 33 |
| ≥ 5 | 5 |

- Median per cell: **0**. Total relevant province-tagged articles: 123.
- Per province: Cavite 42, Batangas 42, Laguna 20, Quezon 10, Rizal 9.
- 40 % of them fall in the top 5 cells; 2024-Q3 alone has 31 of 123, with 21 in Cavite.
- Stored FSSI manifest: `NO_USABLE_EVIDENCE` 85 and `LIMITED_SIGNAL` 35 of 120 cells, **none sufficient**.

## Defects and classes

| # | Finding | Evidence | Class | Action |
|---|---|---|---|---|
| N-D1 | **Retrospective corpus.** One harvest in Oct 2026; what Google News still returned. Query lists were written with hindsight | Crawl dates | NEEDS-DATA | Label all development news `RETROSPECTIVE_VINTAGE`; only live collection from Oct 2026 can test real-time value |
| N-D2 | **Headlines only** | Columns | NEEDS-DATA | Body text needs owner authorization |
| N-D3 | **Effectively English** | Token rule | NEEDS-DATA | "Filipino-English" is not demonstrated by this corpus |
| N-D4 | **No human labels.** Only `news_review_human_TEMPLATE.csv` exists; `annotation_key.csv` holds machine scores | File search | NEEDS-DATA | `ANNOTATION_PROTOCOL.md`; **no labels fabricated** |
| N-D5 | **Geographic precision unmeasured** | No labelled sample | NEEDS-DATA | In annotation sample |
| N-D6 | **BERTopic fitted on all years.** Correctly marked descriptive and not a feature | `topics_manifest` | FIXABLE | Per-origin refit required for any feature; guard in `v10/news.py` |
| N-D7 | **BERTopic unstable.** Seed ARI 0.62–0.66; 147–156 topics; outliers 36 %. **Past-only (58 topics) vs full on the same rows: ARI 0.21** | `topic_stability` | Design limit | Topic features use fixed food-relevant seed mapping per origin, or are excluded by the stability rule |
| N-D8 | **Bias weight amplifies thin cells.** Formula exact in 93 of 93 rows, median within the same quarter (no future). But weight reaches 2.81 at one article, and 29 rows have w > 1 | `bias_*` fields | Design limit | Coverage control N7; raw and corrected both reported |
| N-D9 | **Hypotheses misattributed to HungerGist** | `NEWS_LITERATURE.md` | Docs | Comment in `classifier.py` left unchanged (other tests hash `backend/app`); owner to correct the thesis wording |
| N-D10 | Tagalog not in the XLM-R fine-tuning set | Model card | NEEDS-DATA | Only the local sample can validate it |
| N-D11 | Scored share: 18.5 % of province-tagged rows have an OK score; the rest failed the food-nexus guard (2,499 records) | `score_status` | Note | The guard's precision and recall are unmeasured; in annotation sample |

## Timestamps and leakage

The publication date is used, never crawl date; no crawl precedes publication. `app/forecasting/v10/news.py` adds the `as_of` filter, a future-article test and an all-years topic-fit refusal (`tests/unit/test_v10_news.py`).

## Effective sample for the incremental test

10 target quarters at Lead 2, about 17 labelled in all, with news present in 41 % of cells. **An AUC difference of practical size cannot be separated from zero with this sample unless it is very large** (INFERRED; Stage 1 AUC CIs span about 0.3–0.9).

## Gate 2

**PASSED:** every defect is fixed additively with a test or classed NEEDS-DATA.
