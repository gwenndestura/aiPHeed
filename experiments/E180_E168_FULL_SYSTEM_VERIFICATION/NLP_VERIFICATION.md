# NLP verification (E168)

| Item | Status | Evidence |
|---|---|---|
| NLP outputs reach E168 as inputs | **VERIFIED** | `data/e151/out/news_panel.parquet` (province / SWS-area / national streams, 2013-Q1 to 2026-Q4, lagged `lag_m`) joined by `app/e151/prov.add_inputs`; E168 FULL input set has 36 news inputs; at 2027-Q1 news = 23.6 % of |attribution| |
| Operational vs retrospective | PARTIALLY VERIFIED | Panel extends to 2026-Q4 (operational for the live issue); 2013-2021 history was collected retrospectively |
| H1 (FSSI among the top drivers) | VERIFIED | FSSI family rank 9 of all inputs |
| Human annotation (300 headlines, 2 annotators) | **UNVERIFIED (F05)** | not in the repository; `backend/data/fi6/nlp_validation/validation_result.json`: n_annotated 0; `annotation_sheet.csv`: 200 blank rows. No kappa or disagreement resolution is computed anywhere |
| Classifier quality | UNVERIFIED | zero-shot labels never scored against human labels in the repository |
| Volume | VERIFIED (limitation) | 3-12 articles per CALABARZON province per quarter in the panel (2026) |
| Missing-news encoding | VERIFIED (F16) | absent news → 0.0 tone/share (`prov.py` 118 / 124) |
| Two corpora | VERIFIED (F13) | dashboard feed counts ≠ model panel counts |
| Leakage | PARTIALLY VERIFIED | issue-date cut-off and lag; corruption tests 0.0; survivorship bias of retrospective scraping not measurable |
| Added predictive value | VERIFIED (limited) | earlier ablation (E164) found no accuracy change without news; attribution ≠ added accuracy |

**Conclusion:** NLP is genuinely integrated and influential in E168, but the classification layer is not validated in the
repository. Until the 300-headline annotations and their agreement statistics are added, NLP quality claims are unverified.
