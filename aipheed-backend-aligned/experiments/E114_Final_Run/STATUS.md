# E114 status (paused 2026-10-25, usage limit)

Done (no scoring yet; no protocol frozen):
- Phase 1 outcome: SWS Total Hunger by area, Jul 1998 - Sep 2026, from SWS's own tables (media release 14 Oct 2026),
  runner/collect_sws.py -> data/sws_rounds_1998_2026.csv; checks in data/sws_extraction_checks.csv (1 table conflict,
  6 rounding notes); 36/36 news values match (data/sws_news_crosscheck.csv); 2021+ identical to E110.
- data/sws_area_rounds_full.csv (115 rounds, 106 quarters; pre-2021 release = month end + 60 days, evidence in
  data/sws_release_date_evidence.csv; lag-100 sensitivity file too).
- Covariates (runner/collect_covariates.py): PSA CPI national/Calabarzon food, rice, all items 1994+; palay 1987+;
  LFS unemployment 2005+; ONI; IBTrACS PAR counts. GDELT DOC news: collection was still running (rate-limited).
- runner/e114_lib.py written (models, state-space, tests) - not yet run or tested.
- E114_OBJECTIVE5_EVALUATION_PACKAGE.md (SUS, scenarios, plan) - complete.

Next: check data/cov_gdelt_doc.csv; write + hash PROTOCOL_E114.md; leakage audit; run_e114.py; reports; tests.
