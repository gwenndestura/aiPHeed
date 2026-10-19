# Data-to-dashboard workflow (e64 mode)

This describes the path `AIPHEED_LEAD2_MODEL=e64` serves. **The production default (unset, or `e38`) is unchanged.**

```
SOURCES (2021-01 .. 2026-10-14, nothing earlier)
  PSA CPI food / headline YoY (OpenStat)            E40 data_acquired/psa_cpi_yoy_headline_food_2021_2026.csv
  SWS hunger rounds + posting dates                 backend/data/inputs/sws_rounds.csv
  PSA production, LFS, BSP/ECB, typhoons, ENSO,     E41/E53 loaders (E56 library chain, read-only)
  rice wholesale, policy orders
  Google News RSS titles                            backend/data/news_e31/articles.jsonl  (8,320, E31)
                                                    backend/data/news_e60/articles.jsonl  (2,132 admitted by E60 policy;
                                                                                          1,347 new keys)
        |
        v
NEWS PIPELINE v3  (backend/app/news/pipeline_v3.py)
  corpus()        unique article_key, window check, PH date and quarter from the publisher date (GMT+8)
  classify        app/news/classifier_v2.py (E60 freeze 327f9431..., verified at load): relevant + 1 of 5 triggers
  province        collector geocoder attribution (geo_province_code); unattributed relevant = "national"
  admitted()      relevant, earliest copy of each syndication cluster (same title within 3 days)
  intensities()   XLM-RoBERTa-large-XNLI score per admitted article (data/news_e31 + data/news_v3/scores.jsonl;
                  current classifier source only, D-E64-1)
  asof(t)         admitted articles of quarter t published before O(t) = day 1 of quarter t+1
  fssi_v3()       Equation 2 on asof(t) per province; status SUFFICIENT / LIMITED_SIGNAL / NO_USABLE_EVIDENCE;
                  None when there is no evidence (never 0)
  n3_features(t)  12 columns + article keys (coverage, recency-weighted trigger counts, national trigger signals,
                  outlets, FSSI-v3)
  BERTopic        scripts/fit_topics_v3.py -> data/news_v3/topic_* (descriptive latent patterns only)
        |
        v
MODEL (E64 final candidate D = government indicators + N3; E56 procedure family)
  per origin t: frame(d, X+N3, B, t) -> nested selection over 72 configurations on training targets only
               -> LightGBM price part (structural CPI offset, intercept-free) x I7 regional hunger part
  experiment:  E64 runner/c1_candidates.py -> sealed/candidates.csv (+sha256), sealed/selections.json
        |
        v
RECORD  backend/scripts/build_record_e64.py -> backend/data/e64/e64_record.json (+content_sha256), data/e64/model/*
  for every origin: refit, assert = sealed (< 1e-9); exact TreeSHAP grouped by trigger (N3 -> trigger group,
  coverage/outlets/FSSI -> other); newsEvidence (N3 values + article IDs + issue cutoff); E58 early-warning level;
  lowPriceBacktest (the candidate's own); 2027-Q1 prospective seal (write-once) in the experiment's sealed/
        |
        v
API  (FastAPI, backend/app/api/v1/*; record cached per file version, E61)
  /provinces, /forecast, /forecast/timeseries   record probabilities (region = mean of the five provinces)
  /explainability                               record TreeSHAP + summary.sentence (two parts, model score, caveats)
  /news                                         pipeline v3 feed (e64): evidence quarter = t (Lead-2), before O(t)
  /provinces/{id}/municipalities                142 LGUs: index = P x (0.6 poverty_norm + 0.4 density_norm),
                                                with provinceEstimate / provinceEstimateSource / rankingRowsSha256
        |
        v
DASHBOARD (approved frontend, unchanged): map, province panel, trigger bars, plain summary, news list, LGU list
```

## Traceability of one forecast: Laguna, 2027-Q1, issued 2026-10-01

| Step | Where |
|---|---|
| Inputs at issue | `e64_record.json → provinces.PH040200000.newsEvidence.features` (N3 values) and `.articles[]` (article key, title, outlet, PH time, trigger) |
| News published before the issue date | every `publishedPH` is before `issueCutoffPH` (test) |
| Model configuration and output | `.modelConfig`, `.forecast.probability`, `.forecast.components` (hunger and price parts) |
| Explanation | `.fiveTriggerContributions` (TreeSHAP, adds up to the price part, test) |
| Dashboard | `/api/v1/explainability?...laguna...2027-Q1` (equal to the record, test) and the live local preview (e64 stack, port 8094) |
| Prospective seal | `experiments/E64_Objectives_1_3_Completion/sealed/prospective_2027Q1.json` (+sha256), with feature values and news IDs |
