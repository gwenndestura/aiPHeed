# Did the improved news pipeline improve the model? (E61 follow-up, 2026-10-19)

**Short answer: no. The improved pipeline (E60) has not reached any model, so its effect on accuracy is not evaluated.**
- Its collection is still running.
- Its classifier was never frozen.
- No features were built from it.
- No model was trained on it.
- The dashboard serves models whose news features come from the older E40 keyword table.

The only measurable question today is whether the **original** news features help. They do not: removing them leaves accuracy and Brier unchanged within noise.

## 1. Step-by-step trace (evidence)

| Step | Status | Evidence |
|---|---|---|
| News collection improved (E60 N2: six trigger-specific queries per province, English and Filipino) | **Partially done, still running** | Process `n2_collect_triggers.py` (PID 32852), started by another session on 2026-10-18 23:35 and still writing at 08:5x on 10-19. `data/news_e60/windows.jsonl`: 1,234 windows COMPLETE, through 2024-Q2 only (the plan runs to 2026-09). `articles.jsonl`: 901 articles, 317 province-attributed. `runs.jsonl`: run `20261018T233535_23fbe6` has no "end" event. |
| Relevance and trigger classification improved (classifier v2) | **Code written; not frozen, not evaluated** | `runner/n4_classifier.py` exists. `runner/CLASSIFIER_V2_SHA256.txt`, which E60's protocol requires before scoring, does not exist. No `NEWS_CLASSIFICATION_EVALUATION.csv`. |
| Annotation for developing and checking the classifier | **Done by AI; not human-verified** | `annotation/sample_ACD.csv`: 110 items (57 DEV, 53 EVAL). Annotator `claude-ai` on all 110; `human_verified` empty on all 110. |
| Province attribution and deduplication | **Partially** (project geocoder at collection) | 317 of 901 E60 articles carry a province code. No E60 deduplication output. |
| News features generated from the improved corpus | **Not done** | `runner/n5_features.py` exists. `out/news_feature_summary.json` and any feature table: absent. |
| Features used in training | **Not done** | E56/E58 news inputs come from `E40_SWS_CPI_Tiers/runs/triggers/composition.csv` (2026-10-15), loaded by `E41_Lead2_Audit/runner/e41_lib.py` (`NEWS_FILE`). No code reads `news_e60`. |
| New model trained with improved news | **None trained** | E60 `runner/c1_candidates.py`, `c2_score.py` and `c3_cases.py` exist, but no sealed predictions or score outputs exist. |
| New model evaluated | **Not evaluated** | No E60 results. E60 `NEWS_PIPELINE_AUDIT.md` section 3 still says "Filled in from the runs". |
| Selected for production / deployed | **No** | `grep news_e60\|E60` in `backend/app` and `backend/data`: no matches. The served record is E58 (`backend/data/e58/e58_record.json`), news inputs from E40. The production default is E38 (`AIPHEED_LEAD2_MODEL` unset). |
| Earlier "improved" news (E31 FSSI-v2, relevance rule R1.1) | **Displayed, not in the E56/E58 model** | `backend/data/e56/model/feature_schema.json` has no `fssi` feature. FSSI-v2 articles feed the dashboard news list (E45 pool), not the forecast. |

## 2. Before / after on comparable cases

Same target (T43), same 50 rolling-origin rows (targets 2024-Q2..2026-Q3, 18 HIGH, 10 onsets), same issue dates, same E56 nested tuning. Source: E61 `tables/c2_model_comparison.csv`, `out/c2_score.json` (sealed candidates, frozen protocol).

| Model | News pipeline | News in training | News at inference | Rows | Correct | Accuracy | Balanced acc. | HIGH recall / precision | Onsets detected | Brier | Δ vs E56 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| E56 (original) | E40 keyword shares (old corpus) | yes (price part, when the "all" set is selected), plus `news_n` in hunger | yes | 50 | 36 | 0.72 | 0.68 | 0.56 / 0.63 | (warning form) 7/10 | 0.214 | — |
| E58-EW (E56 warning form) | same | same | same | 50 | 39 | 0.78 | 0.78 | 0.78 / 0.67 | **7/10** | 0.220 (P_price) | — |
| **A. Government indicators only (E61 C4)** | none in the price part (`news_n` kept in hunger) | no | no | 50 | 37 | 0.74 | 0.70 | 0.56 / 0.67 | (warning form) 7/10 | 0.212 | **−0.002 [CI −0.006, +0.001]** |
| A, warning form | — | — | — | 50 | 40 | 0.80 | 0.80 | 0.78 / 0.70 | 7/10 | 0.200 (P_price) | +1 correct vs EW |
| B. Government + original news | = E56 | | | | | | | | | | |
| **C. Government + improved news (E60)** | E60 v2 | — | — | — | **not evaluated** | | | | | | |
| **D. Improved news only** | E60 v2 | — | — | — | **not evaluated** | | | | | | |
| Price projection (B-PROJ) | none | — | — | 50 | 34 | 0.68 | 0.65 | 0.56 / 0.56 | — | 0.228 | +0.014 |
| Persistence | none | — | — | 50 | 28 | 0.56 | 0.54 | 0.44 / 0.40 | 0/10 | 0.440 | — |
| Majority (always LOW) | none | — | — | 50 | 32 | 0.64 | 0.50 | 0 / — | 0/10 | 0.360 | — |

**What removing the original news changed:**
- P(HIGH) changed on **10 of 50 rows**, in two quarters only (2025-Q3, 2025-Q4), by at most 0.079.
- One warning decision changed: Batangas 2025-Q3, observed LOW. With news it was a false warning (P_price 0.544); without news it was correct (0.465).

**Statistics:**
- Paired Brier difference: CI includes 0; quarters better/worse 1/1; sign test p = 1.0.
- **The original news adds no measurable value, and does no measurable harm.**
- Calibration: slope 0.55 with news, 0.56 without (both CIs include 1).
- Rising stress: 7 of 10 onsets with and without news.
- Missed HIGH: 8 with and 8 without.

**Caveat on A:** it removes news from the price part only. The I7 hunger component's `news_n` input (worth +5.1 points of predicted hunger at 2027-Q1) was kept, because the protocol fixed C4 that way. A full no-news hunger component was **not evaluated**.

## 3. Why the original news features did not help (E61 A5, E59)

- **Mostly zero:**

  | Feature | Zero share on the 50 back-test rows |
  |---|---|
  | `news_ofw_remittance` | 100% |
  | `news_employment` | 98% |
  | `news_fish_kill` | 98% |
  | `news_market` | 96% |
  | `news_climate` | 46% |

- **Titles only, retrospective collection, about 34% province-attributed** (E60 corpus audit). Most price and rice-policy stories are national and cannot be attributed to a province.
- **Rarely selected:** E56 chose the "all" feature set (the only set containing news) at 5 of 11 origins. The trees split on news volume at 1 origin (E59 `trigger_use_by_origin.csv`).
- **Redundant with official data:** the target's provincial variation is CPI-driven (E60 target audit: T43 = PS on all evaluation rows). CPI is already in the model.
- **Small sample:** 10 evaluation quarters and 4 onset episodes. Even a real news effect would be hard to detect.

## 4. What is still missing or broken

1. **E60 collection unfinished.** It ran about 9.5 hours for 1,234 windows. At that rate the remaining windows (to 2026-09) need several more hours.
2. **Classifier v2 is not frozen**, and its annotations are AI-made (`claude-ai`) with no human verification. Any "relevance improved" claim needs at least a human-verified sample.
3. **Source compliance is unresolved.** E31 found that news.google.com's robots.txt disallows `/rss` for generic crawlers (E31 `FINAL_REPORT.md` §4, "Decision for the researcher"). The E60 collector still queries Google News RSS. This needs your decision.
4. **No feature table, no candidate run, no evaluation, no serving** for the improved news.

## 5. Next justified action

When the E60 collection finishes, and only then (a partial corpus would give later origins no improved-news features, an unfair comparison):

1. Human-verify the 57 DEV annotations, or a sample of them.
2. Freeze `n4_classifier.py` (sha256).
3. Run `n5_features.py` with the truncation test, so only articles published before each issue date are used.
4. Run E60's frozen protocol: A gov-only, B news-only, C gov + improved news, D + history. Use the same 50 rows, DEV/TEST split and the Q-news criteria (paired Brier CI upper bound < 0 **and** onset recall not lower).

Report the result whatever it is. No model is switched without your authorization.
