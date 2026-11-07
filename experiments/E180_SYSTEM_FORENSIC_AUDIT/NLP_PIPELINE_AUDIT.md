# E180: NLP pipeline audit

| Item | Status | Evidence |
|---|---|---|
| News enters the served model | **VERIFIED** | `data/e151/out/news_panel.parquet` (streams prov/area/national; quarters 2013-Q1 to 2026-Q4); 36 news inputs in the 2027-Q1 E168 configuration (RSS, LightGBM, FULL); news = **23.6 %** of absolute attribution at 2027-Q1 |
| H1 (FSSI among top-10 drivers) | VERIFIED | E168 SHAP: FSSI family rank 9, food-CPI deviation rank 10 (`data/e168/out/objectives/shap_results.json`) |
| Classifier validated by humans | **UNVERIFIED (HIGH, I05)** | `backend/data/fi6/nlp_validation/validation_result.json`: `n_annotated 0`, "zero-shot labels remain unverified"; `annotation_sheet.csv` is a blank 200-item template. The two annotators' completed 300-headline annotations are not in the repository, so inter-annotator agreement and classifier precision/recall cannot be checked |
| Volume | PARTIALLY VERIFIED | Recent counts are thin: 3-12 articles per province per quarter in the model's panel |
| Two corpora | VERIFIED (MEDIUM, I10) | Dashboard news feed counts differ from the model's panel counts for the same province-quarter |
| Missing-news encoding | VERIFIED (LOW, I15) | Tone/share features set to 0.0 when a province has no news row (`app/e151/prov.py` lines 118/124) |
| Retrospective availability / leakage | PARTIALLY VERIFIED | Panel uses lagged quarters (`lag_m`) and issue-date cut-offs; corruption tests show no future-label leakage. Retrospective collection (articles gathered in 2026 for 2013-2021) may suffer survivorship bias (deleted or unindexed articles): not quantifiable from the repository |
| Importance vs value | VERIFIED | E164 / E168: removing news did not change accuracy materially; attribution share is not added predictive value |

**Conclusion:** NLP is integrated (it moves the forecasts and passes H1), but its labels are not validated in the repository, so claims
about classification quality must wait until the 300-headline annotations and their agreement statistics are added.
