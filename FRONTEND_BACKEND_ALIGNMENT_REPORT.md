# Frontend–Backend Alignment Report

- **Branch:** `aiPHeed/final-model-completion-20261113`
- **Date:** 14 November 2026
- **Served issue:** 2026-Q4, cut-off 1 November 2026, model `final-rate-mind-1.0`, artifact sha `e1f8675f…`

## How alignment was checked

Each value was traced from the layer below it, never from another API:

**frozen model → issue files → ledger → API → rendered page.**

The automated trace is `research_notes/audit_20261114/trace_end_to_end.py`, with results in `trace_results.json` (**34 / 34 checks pass**). It does the following:

1. Re-runs the frozen FINAL model on the current data. The 10 stored forecasts are reproduced exactly: max |Δ share| 0.0000 points; max |Δ P(HIGH)| 0.000000.
2. Checks the issue's internal rules (leads, provinces, targets, class threshold, cut-off).
3. Compares the hash-chained ledger with the issue.
4. Compares every dashboard API with the issue file.
5. Recomputes the town priority for all 142 cities and municipalities from the displayed inputs and the published formula.

The rendered pages were then read in the browser: dashboard, province card, town card, quarter switch, forecast history, About modal, Data page, Visualization page, admin route, and phone width.

## Traceability table

| Dashboard component | Frontend field | API endpoint | Backend source | Data / model source | Alignment status |
|---|---|---|---|---|---|
| Region card "Food insecurity risk" | `useShareRows(quarterId)` mean of `score_pct` | `/final/food-insecurity/outlook` | `app.final.serving._outlook_final` | `issues/2026-Q4/live.json` ← frozen model | ALIGNED. Q1 24.5%, Q2 24.3% = mean of the 5 issue shares. |
| Province list (highest → lowest) | `RegionData.riskScore` (selected quarter) | `/provinces?quarter=` | `services.dashboard.province_summary` → `HS.row` | `dashboard_rows_served.csv` | **FIXED.** It used Lead-1 outlook rows for every quarter; Q2 showed Q1 values. |
| Province card value and class | `shareRow.score_pct`, `riskLevel` | outlook + `/provinces` | as above | issue rows | ALIGNED. Class is HIGH iff share ≥ 50% on both sides. |
| Map colours | `riskLevel` per province | `/provinces?quarter=` | `province_summary` | issue `class` | ALIGNED (trace: riskLevel = issue class, both quarters). |
| Town card (priority, rank, population, poverty) | `riskIndex`, `rankInProvince`, `population`, `povertyRate` | `/provinces/{id}/municipalities` | `serving._muni_pct` over `municipality_summary` | `data/e143/out/issue/lgus_next_quarter.csv` × province share | **FIXED.** Lucena showed a 16.8% "province substitute"; its rank used PSA's 2021 city figure (10%). Priority = share × vulnerability, max \|Δ\| 5e-5. |
| Town colour | `riskLevel` | same | province class | issue class | ALIGNED. Every town carries its own province's class. |
| "Why is this at risk?" (left bars, right cards) | `groups[].pct`, `plainEvidence` | `/final/shap/province` | `app.final.shap_api.factor_groups` | `shap_live_features.csv` (exact TreeSHAP) | ALIGNED. Groups sum with "Other" to 100; Poverty and Vulnerability only when used. |
| Visualization "Why is this at risk?" | `triggers[].pct` | `/explainability` | `serving._final_groups` → `shap_api` | as above | ALIGNED (fixed in `8986e840`; it showed another model's grouping). |
| Visualization "Risk over time" | `riskScore` per quarter | `/forecast/timeseries` | `HS` rows | issue rows | ALIGNED (trace: Quezon Q1 0.268, Q2 0.266). |
| Visualization PDF | `ReportPayload.blocks` | `/report/data` | `app.final.report_data` | issue rows, `shap_api`, `municipality_summary` | ALIGNED. **FIXED:** population now equals the dashboard (Quezon 2,260,669, not 1,980,338). |
| Server PDF | — | `/report` | `app.final.report` | same | ALIGNED (same fix). |
| "News reports used" | `articleCount` | `/news` | `services.dashboard._e168_news_page` | `issues/2026-Q4/news_used.json` (307 stories, 1 Aug–31 Oct 2026) | ALIGNED with the live site (fixed in `579eb041`). |
| Data page "Local news reports" | `articleCount` | `/provinces` | `article_count(local_only)` | same file | **FIXED** label. The column is local-only stories; it was headed "News reports". |
| Data page "Food insecurity risk" | `riskScore` | `/provinces` | `province_summary` | issue share | **FIXED** label. It was headed "Chance of high risk" while showing the share. |
| "About this forecast" data periods | `data_used[].when` | outlook | `serving._data_used_final` | `hcw_system.data_used` + served facts | **FIXED.** Harvest showed Oct 2025–Sep 2026; the inputs used Q3 2025–Q2 2026. CPI Oct 2026 and LFS Sep 2026 are truthful, now with a disclosure (see C1). |
| Issue disclosure note | `issue_note` | outlook, `/forecast-period`, `/final/forecast-history` | `period.issue_note` | `serving.json` → `issue_notes` | NEW. Shown in About this forecast, Forecast history and both PDFs. |
| Forecast period lines | `current_quarter`, `issue_quarter`, `next_issue_date` | `/forecast-period` | `period.period(now)` in Asia/Manila | `serving.json` issue rule | ALIGNED. Q4 2026; issued Q4 2026; next 1 February 2027. |
| Forecast history | `forecasts[]` | `/final/forecast-history` | `history.with_outcomes` | `history/ledger.jsonl` (10 records, chain intact) | ALIGNED (ledger = issue rows). |
| About modal accuracy table | `risk.leads[k]` | `/final/risk/evaluation` | `serving._evaluation_final` | `data/final/meta` | ALIGNED. **FIXED** stale text: "probability", "0.50/0.60", "holds to 4", "left out, not counted". |
| About modal regional hunger text | `overview.localEvidence` | `/final/overview` | `services.final_engine` | SWS | **FIXED** ("model forecast probabilities" → "forecast shares"). |
| `/final/risk/rows` horizon note | `horizon.why_not_longer` | `/final/risk/rows` | `HS.horizon` | — | **FIXED.** Setup H's "Lead 7 … Lead 18" text was replaced by FINAL's. No component uses this endpoint. |
| Glossary | static | — | — | — | ALIGNED (updated in `1ec32764` and this audit). |
| Landing page | static + `data/final/meta` | — | — | — | ALIGNED. No raw FINAL input names. E196 is named only as the comparison model. |

## Units and formats

- **Shares:** the API sends shares as fractions (0.268) on `/provinces` and as percentages (26.8) on the outlook. The UI shows one decimal (`fmtPct`).
- **Chance of High:** shown only in the Forecast history ("<1%", "1%"), from `p_high`.
- **Dates:** formatted in Asia/Manila (`en-GB`). The cut-off is exclusive.

## Contract notes (not changed, recorded)

- Served rows carry the share in a field named `probability`, with the real P(HIGH) in `p_high`. This is a legacy contract shared by E168 and Setup H. Every consumer was checked and reads it as the share, but the name is misleading (REMAINING_ISSUES L5).
- Unused hooks and endpoints: `useFinalEvaluation`, `useFinalRiskRows`, `useFinalArchive`, `useAudit`. The components `NextQuarterOutlook` and `ProvincialOutlook` are never rendered; they read admin-only `/fi9`, `/fi10`. This is dead code and does not reach the screen (REMAINING_ISSUES L3).
