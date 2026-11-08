# Objective 1: two-tier news pipeline, FSSI and latent risk patterns

> Objective 1 (Chapter I): to design a two-tier pipeline combining zero-shot XLM-RoBERTa Filipino-English sentiment extraction and BERTopic unsupervised topic modeling to produce the bias-corrected Food Stress Sentiment Index and latent food insecurity risk patterns per province-quarter from a Filipino-English news corpus.

**Status: produced. The pipeline exists and its outputs exist for every province-quarter. Their quality is limited, and they add no measurable forecast skill.** Both facts belong in the thesis.

## What was built

| Requirement | What exists | Where |
|---|---|---|
| Filipino-English news corpus | 141,513 articles from 43 sites, 2013 to 2026; 17,121 relevant texts scored; 16,974 stories after duplicates; 1.5 % Filipino-dominant | `backend/app/e151/corpus.py`, `data/e151/out/corpus_audit.json` |
| **Tier 1:** zero-shot XLM-RoBERTa extraction | XLM-RoBERTa-large-XNLI on 13 hypotheses (10 food-insecurity events, problem now, plan or warning, not relevant), problem kept apart from response. After the label check, combined with multilingual embedding similarity and seed phrases | `score.py`, `labeler.py`, `topics.event_probs` |
| **Tier 2:** BERTopic | 14 fits, each on stories before its origin; latest fit 29 topics; 42 of 257 topic rows removed as irrelevant by a fixed keyword rule | `topics.py`, `data/e151/out/topic_report.csv` |
| **Bias correction** | Each outlet centred on its own earlier mean (Rappler is 61 % of stories); shrinkage toward the outlet norm when a province has few stories; one count per story; area or national stream used, and flagged, when a province has no stories | `features.py`, `fssi.py` |
| **FSSI per province-quarter** | 4,368 province-quarters, 78 provinces, 2013 to 2026-Q4. FSSI = 50 + 10 z of problem stress against pre-2016 province-quarters. Response index (RSI) reported separately | `data/e151/out/fssi/fssi_province_quarter.csv` |
| **Latent risk patterns per province-quarter** | 1,130 province-quarters with their top 3 topics, keywords and trigger group shares (146 in CALABARZON) | `data/e151/out/fssi/topic_patterns_province_quarter.csv` |

## How good it is

| Check | Result |
|---|---|
| Label check, fresh 80 stories, rule fixed first | Top event agrees 69 % (Wilson 58 to 78 %); 84 % on relevant stories; current-problem 80 %. Reader is the system's author, not an independent annotator |
| Off-topic filter | Catches 7 of 23 off-topic stories |
| National market news against food inflation | Spearman 0.39 (E151 validation) |
| National remittance news against remittances | 0.50 |
| **Province FSSI against province food inflation, within province** | **0.03, no relation** |
| Market stress at the 2018-Q4 rice surge | **+3.3 standard deviations, detected** |
| Market stress at the 2023-Q4 rice crisis | +0.5, weak |
| **FSSI at the 2018 and 2023 rice shocks** | **-1.0 and -1.3, missed** |
| Province coverage | 63 % of all province-quarters use the area fallback (33 % in CALABARZON); median 2 to 4 relevant stories per quarter in CALABARZON |
| Forecast value | None measurable one quarter ahead, at area or province level, including with the latest quarter's news |

**Design note.** The first FSSI subtracted response reporting from problem reporting. Aid coverage rises in the same quarters as shocks, so the two cancelled. Problem and response were then split. That was a construct fix made against known events and prices, with no food-insecurity outcome. It did not recover the rice shocks in the combined index, and the index was not adjusted further, because that would fit it to the events.

## What can be claimed

> "A two-tier pipeline (zero-shot XLM-RoBERTa extraction with BERTopic topic modeling) produced a bias-corrected Food Stress Sentiment Index and latent risk patterns for 78 provinces per quarter, 2013 to 2026. National indicators tracked food prices and remittances, and market stress detected the 2018 rice price surge. At province level, coverage was thin (median 2 to 4 relevant stories per quarter in CALABARZON), and the index did not track local food inflation. The indicators added no measurable forecast skill beyond government data."

**Not supported:** that the FSSI measures provincial food insecurity, or that it improves the forecast.
