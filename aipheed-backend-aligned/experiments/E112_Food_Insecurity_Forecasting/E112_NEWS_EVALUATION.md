# E112 News evaluation

**Sources:** `out/results.json` (keys `validity`, `advance`, `bl.*.N1`, `bl.*.N2`, `N3`, `panel`), `out/news_quarterly_*.csv`. Protocol: `PROTOCOL.md` §2, §4.1–4.3, frozen before scoring.

## 1. Pipeline (collect → identify → categorize → measure → date → cut off)

| Stage | Implementation | Result |
|---|---|---|
| Collect | Project RSS corpus (E31 + E60 stores, `pipeline_v3.corpus`). GDELT GKG CALABARZON-located documents (E85) as an independent source. | 9,485 headlines (corpus) and 58,388 GDELT documents, 2021-Q1..2026-Q3 |
| De-duplicate | Same normalised title within 3 days, any outlet (`pipeline_v3.dedupe`) | Syndicated copies counted once |
| Identify / categorize | Fixed title lexicon, English and Filipino (`news_indicators.CATEGORIES`). GDELT uses fixed theme lists. | Corpus headlines with at least one food-related event: 31.6% (disaster 1,220; agri_supply 811; assistance 529; price 367; jobs_income 302; shortage 129) |
| Measure: volume | Headlines per quarter | 147–193 per quarter in 2021, rising to 667–881 in 2026 (corpus coverage grows) |
| Measure: intensity | Category share of all headlines | Coverage-normalised |
| Measure: direction | YoY change of the share | Removes the typhoon calendar |
| Measure: severity | XLM-R intensity (FSSI-v3, family N1) is retained unchanged | Missing at 56% of Lead-1 origins, so too sparse to use as a severity series; no new severity score was invented |
| Date / cut off | Quarter t is used at O(t) only if its last headline was published before O(t) | Asserted in code; tested with an injected on-issue-date headline (`test_news_after_issue_date_is_refused`) |

This replaces the old route, in which a relevance classifier admitted 695 of 9,667 headlines (2–7 per quarter in 2021–22). The new indicators have **no missing values** at any evaluated origin.

## 2. Do the news indicators measure what they claim? (concurrent validity, no hunger data)

| Comparison (Spearman, one-sided) | Corpus ρ (p) | GDELT ρ (p) | Valid (p < .05)? |
|---|---|---|---|
| disaster share vs typhoon count C2 | **0.81 (< .001)** | **0.73 (< .001)** | **Yes, both** |
| price share vs headline inflation A2 | −0.13 (.72) | −0.03 (.56) | No |
| price YoY vs rice price YoY A3 | −0.29 (.88) | −0.48 (.98) | No |
| agri_supply YoY vs crop drop C3 | 0.16 (.27) | 0.14 (.29) | No |
| agri_supply YoY vs fisheries drop C4 | 0.38 (.059) | 0.36 (.070) | No (borderline) |
| jobs_income YoY vs unemployment change E1 | 0.28 (.13) | 0.34 (.087) | No |

**Reading.**
- **Disaster coverage is a valid, measurable signal.** Both sources track the typhoon record closely.
- **Price headlines do not track measured inflation.** Their direction is even negative, consistent with price stories peaking around policy events (rice tariff cuts, price caps) rather than with inflation.
- Production and jobs news point the right way but are not significant with 18 quarters.

## 3. Does news give advance warning of hunger? (association, §4.2)

**Test.** News YoY of quarter s vs Balance Luzon hunger YoY change D(s+j), with Holm correction within source over 18 tests.

| Finding | Corpus | GDELT |
|---|---|---|
| Concurrent (j = 0) | **disaster: ρ = 0.76, Holm p = .009** | none (disaster ρ = 0.27, p = .16) |
| One quarter ahead (j = 1) | **agri_supply: ρ = 0.65, Holm p = .074** (n = 15) | none (agri_supply ρ = 0.26, p = .17) |
| Two quarters ahead (j = 2) | none (agri_supply ρ = 0.48, raw p = .04, Holm .68) | none |

**Reading.**
- By the frozen rule, the corpus shows **one advance-warning association**: agricultural-supply news leading hunger by one quarter. It is weak evidence, for three reasons:
  - it is 1 of 36 tests;
  - it is not replicated in GDELT;
  - the agri_supply category itself failed the concurrent-validity check.
- **The disaster association is concurrent, not leading.** It appears in the corpus but not in GDELT.

## 4. Does news improve forecasts? (§4.3; Balance Luzon, walk-forward, true horizons)

| Test | Lead 1 (9 q) | Lead 2 (7 q) | Lead 3 (6 q) | Lead 4 (5 q) |
|---|---|---|---|---|
| RW MAE | 3.72 | 4.77 | 4.08 | 3.25 |
| **N1 news-only (corpus) NEWS-C** MAE (DM p) | **3.52** (.36) | 4.86 (.55) | 4.55 (.59) | 5.69 (.77) |
| N1 news-only (GDELT) NEWS-G | 3.94 (.67) | 5.75 (.83) | 5.05 (.81) | 4.12 (.59) |
| LGBM12 (no news) | 4.04 | 5.62 | 4.49 | 4.04 |
| **N2 ablation LGBM12N** (with news) | 4.05 | 5.67 | 4.79 | 4.08 |
| N2 LGBM12N − LGBM12, mean per-quarter difference (p) | +0.01 (.51) | +0.05 (.54) | +0.30 (.67) | +0.03 (.57) |
| News share of LGBM12N mean \|SHAP\| | 73% | 40% | 47% | 16% |
| Panel news ridge NEWS-CP vs RW (4 areas) | 4.85 vs 4.84 | 6.32 vs 5.53 | 6.57 vs 5.98 | 8.53 vs 6.37 |

- **Holm-corrected:** every N1 and N2 test has p = 1.0.
- **N3 contribution (leads 1–2).** No removal of news, of a news category or of a family significantly worsens LGBM12N (all Holm p = 1.0). At Lead 1:
  - removing price news raises MAE from 4.05 to 4.43 (raw p = .19);
  - removing jobs news *lowers* it to 3.80.

**Reading.**
- **News is measurable but adds no demonstrated predictive value.** The news-only corpus model has the lowest Lead-1 MAE of any method (3.52 vs 3.72, also lower under the ALL and HH rules), but the difference is small and not significant. It fails P1 (p = .36), P3 (worse after 2025-Q2), P4 (leave-one-quarter-out), P5 (worse in the last 4 quarters) and P8 (80% coverage 0.67).
- **High SHAP share, no gain.** Inside LightGBM, news takes up to 73% of the attribution with no accuracy change. The trees use news *instead of* other columns, not *in addition to* them. SHAP share is therefore not evidence of value.
- **News did not generalise across the four SWS areas** (NEWS-CP is worse than RW from Lead 2).

## 5. Surges and false alarms

**Lead 1** (2 sharp increases: 2024-Q4 and 2025-Q3):

| Method | Sharp increases missed (miss rate) | Warnings | False alarms |
|---|---|---|---|
| RW | both (1.00) | 0 | 0 |
| NEWS-C | 1 (0.50) | 2 | 1 |
| LGBM12N | 1 (0.50) | 1 | 0 |
| LGBM12 | both (1.00) | 2 | 2 |
| NEWS-G | both (1.00) | 2 | 2 |

**Lead 2** (3 sharp increases):

| Method | Hits | False alarms |
|---|---|---|
| NEWS-C | 2 | 2 |
| LGBM12N | 1 | 3 |
| MA2 | 2 | 1 |

With 2–3 events per lead, these counts cannot support a claim. The 2025-Q3 surge was missed by every news and indicator model. Only MA2 flagged it, because it averaged in the earlier 25.3 peak.

## 6. Answer

**Is news measurable?** Yes.
- The dense, de-duplicated, de-seasonalised indicators exist for every quarter with no missing values.
- Disaster news is a validated measure of typhoon shocks, and is concurrent with hunger changes in the corpus.
- One unreplicated association of agricultural-supply news with the next quarter's hunger change meets the pre-registered rule.

**Does news improve hunger forecasts?** **No demonstrated gain** on any news-only, ablation or contribution test, at any lead.

**What news can honestly provide to DA IV-A:** a dated, auditable record of disaster, supply, price and assistance coverage, shown as context beside the regional outlook. It is not a forecast driver.
