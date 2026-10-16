# E45: news feed restored, every city and municipality coloured, model diagnostics

> **Correction (2026-10-17, user instruction):** the purple "vulnerability" colour scale and the extra legend that E45 first added were **removed**. `PhilippineMap.tsx`, `MapLegend.tsx`, `MapDashboard.tsx`, `data/types.ts` and `lib/adapters.ts` are byte-identical again to the approved frontend (`2c45882`). Every LGU is now coloured with the **approved** palette: the backend gives each LGU the approved display band (`ref.risk_level` of its index, cutoff 0.50), and the approved map paints it yellow (low) or red (high). A null index stays null, which the approved map shows as its gray "No data available". The LGU index is still the relative prioritization from the province forecast and PSA poverty/density (`riskLevelBasis`); it is not a municipal forecast. Live check: Quezon 41/41 LGUs coloured approved yellow (#eab308), approved legend. Section 2 below describes the superseded first version.

**Date:** 2026-10-16.
**Branch:** `e43-five-trigger-risk` (local, not pushed).
**Builds on:** E44 (`9745340`).
**Preserved:** E41–E44 artifacts are unchanged. The production default model (E38) is unchanged.

## Acceptance status

| Requirement | Status | Evidence |
|---|---|---|
| News articles appear on the dashboard, can be opened, API = UI | **MET** | Live check below; `backend/tests/integration/test_e45_news_and_map.py` (6 news tests) |
| Every in-scope city and municipality (142) has a visible, honestly labelled colour | **MET** | Live fill counts for all 5 provinces (142 coloured, 0 gray or transparent); backend and frontend tests |
| All five triggers in the model's training and inference | **MET** (E44 final candidate I2) | E44 report §5; E44 tests |
| **≥ 75% Lead-2 accuracy with balanced HIGH/LOW discrimination** | **NOT MET** | Best five-trigger candidate I2: 0.686 accuracy, 0.716 balanced (7 quarters, 35 rows). Diagnostics below. |

**The forecasting acceptance requirement remains open.** It is not marked complete.

## 1. News feed

**Root cause** (traced from store to UI):
- **Over-strict filter.** The dashboard served only the 140 articles validated by rule R1.1, out of 8,320 collected (2,820 province-attributed).
- **Strict window.** A forecast showed only its single evidence quarter (2026-Q3). Several provinces had 0 articles there, so the panel read 0.
- **Frontend hid it.** The panel was collapsed by default, had no loading or error state, and showed none of the province, trigger or relevance fields.

**Fix (backend, `app/services/dashboard.py`):**
- **Pool:** validated R1.1 articles plus province-attributed titles that match a food-stress trigger keyword **and** name a food, farm, fisheries, livelihood or remittance context.
  - The `FOOD_CONTEXT` filter excludes politics and transport stories caught by generic words like "flood" or "price surge".
  - Restaurant and "food trip" titles that only passed the generic food filter are excluded.
  - Result: 147 articles (140 validated, 7 keyword matches).
- **Window:** the forecast's evidence quarter, extended back by up to 3 quarters when it holds fewer than 5 articles. It is **never extended forward**: every shown article was published before the forecast origin.
- **Each article carries:** headline, publisher, publication date, link, province, trigger categories, relevance status (validated / keyword match), and the retrospective-collection flag.
- **The response carries:** `windowQuarters`, `validatedCount`, `triggerMatchCount` and a plain `feedNote`.
- **One count everywhere:** the explainability `articleCount` uses the same feed window.

**Fix (frontend):**
- The panel is open by default, with loading, error (with retry) and explained empty states.
- Each article shows province, a Validated / Keyword match badge and trigger tags.
- The dialog states the relevance status and that the collection was retrospective.

**Live check** (E44 API + approved UI with the E45 edits):

| Scope | Articles | Example |
|---|---|---|
| CALABARZON | 10 | "Over 20,000 kg of fish die in latest Laguna de Bay fish kill" · newsinfo.inquirer.net · 2026-09-01 · Laguna |
| Quezon | 3 | – |
| Laguna | 7 | – |
| Cavite | 5 | – |
| Rizal | 8 | – |
| Batangas | 5 | – |

- **A link opened:** "Higher fuel costs lead to smaller catches for Cavite fisherfolk" resolved to `gmanetwork.com/news/topstories/regions/983292/cavite-fisherfolk-catch/story/`.
- **Limitation:** headlines only (the source supplies no lead text), collected retrospectively in October 2026.

## 2. City and municipality map

**Root cause:**
- Every LGU row has `riskLevel: null`, on purpose since E28: the province estimate is not validated, so no LGU gets a HIGH/LOW band.
- The map coloured LGUs with `RISK_COLORS[muni.riskLevel]`, so **all 142 fell back to gray**. The tooltip would also crash on a null index.
- The geometry-to-record join was **not** the problem: the normalized-name join covers 142/142 (tested).

**Fix (following the brief's decision logic):**
1. **No municipal forecast exists**, so none is shown or implied.
2. **Each LGU is coloured by its real vulnerability / prioritization index.** It is PSA 2021 poverty (60%) plus POPCEN 2024 density (40%), min-max within the province, the index the LGU ranking already uses.
   - Bands: Lower < 1/3 ≤ Middle < 2/3 ≤ Higher.
   - It uses a distinct purple scale so it cannot be confused with forecast risk colours.
3. **Insufficient data** (no index computable) gets a visible neutral gray (#9ca3af). None of the 142 needs it today.

**Code:**
- Backend: `lgu_map_status()`; `mapStatus`, `mapCategory`, `mapLabel`, `mapNote`, `vulnerabilityIndex` on every row. The disaggregator now passes the vulnerability index.
- Frontend: `lguMapColor`, `LGU_MAP_COLORS`.
- **Tooltip:** LGU name, band and index, "Vulnerability / prioritization indicator, not a forecast".
- **Legend:** province risk, plus "City/municipality vulnerability (not a forecast): Lower · Middle · Higher · Insufficient data".
- **Panel text:** the LGU list no longer says "validated province forecast".

**Live check, all provinces** (fills read from the rendered SVG):

| Province | LGUs | Lower | Middle | Higher | Gray / transparent |
|---|---|---|---|---|---|
| Laguna | 30 | 27 | 3 | 0 | 0 |
| Quezon | 41 | 11 | 29 | 1 | 0 |
| Batangas | 34 | 12 | 18 | 4 | 0 |
| Rizal | 14 | 2 | 11 | 1 | 0 |
| Cavite | 23 | 6 | 17 | 0 | 0 |
| **Total** | **142** | | | | **0** |

## 3. Model: diagnostics of the 75% failure (no new candidate; nothing selected)

**Comparable protocol** (E43 primary vs E44 final candidate):
- On the same 5-quarter subset: E43 five-trigger LightGBM 0.56 accuracy (Brier 0.275) vs E44 I2 0.68 (Brier 0.179).
- On S44 (7 quarters, 35 rows, 9 HIGH), I2 scores:

| Metric | Value |
|---|---|
| Accuracy | 24/35 = **0.686** (CI 0.46–0.89) |
| Balanced accuracy | 0.716 |
| HIGH recall | 0.78 |
| LOW recall | 0.65 |
| Confusion matrix | TP 7, TN 17, FP 9, FN 2 |
| Brier | 0.181 (always-LOW 0.220, persistence 0.457) |

**Error cases** (`evidence/model_diagnostics.json`; the longer 8-quarter history: 15 errors in 40 rows):

| Error type | Count | Cause | Policy shocks in the period |
|---|---|---|---|
| False positives | 9 | **All 9 had observed food inflation below the province reference while I2 forecast it above.** Examples: Batangas 2025-Q4 forecast 2.8%, observed −0.5%; Laguna 2024-Q3 forecast 6.9%, observed 3.6%. | Rice tariff reduction in mid-2024 and the import suspension in late 2025. No official feature represents them. |
| False negatives | 6 | **4 are 2024-Q2.** Regional SWS hunger jumped from 10.3% (latest round at the origin) to 19.6%, a surge no available signal anticipated two quarters ahead. | – |

**Temporal windows:**

| Window | I2 accuracy | Notes | Baselines |
|---|---|---|---|
| 2024-Q2..2025-Q1 (12 HIGH / 20) | 0.60 | HIGH recall 0.58 | 0.40–0.55 |
| 2025-Q4..2026-Q3 (1 HIGH / 20) | 0.65 | – | always-LOW 0.95 |

- **Not stable across periods.**
- **By province:** Quezon 0.75, Rizal 0.75, Batangas 0.625, Cavite 0.50, Laguna 0.50.

**Missing-trigger sensitivity** (2027-Q1 raw probability when a group is set to missing):
- **Employment** moves every province by about +0.19 to +0.21. The national employment change still dominates the hunger component, so it is a fragile, time-proxy-like dependence.
- Climate: −0.01 to −0.05.
- Market, fish, OFW and news: under 0.04.

**Why 75% is still not met:**
- **Discrimination is the blocker.** Even with a hindsight-optimal threshold, no model meets accuracy ≥ 0.75 with both recalls ≥ 0.60. The gates need AUC ≈ 0.78; the five-trigger candidates reach 0.27–0.63 (E44 `runs/blocker`).
- **The errors come from two concrete gaps:**
  1. Rice-policy price shocks, not represented in the features.
  2. Unanticipated regional hunger surges.

**Why it was not "fixed" here:** adding a rice-policy feature now would be designed from the test-set errors (hindsight), and tuning further on the same 7 quarters would break your own no-test-tuning rule. The defensible routes are:
- **(a)** pre-register a rice-policy-aware price component (official tariff and import-ban dates, known at issuance) and evaluate it **prospectively** from 2027-Q1;
- **(b)** obtain provincial hunger/FIES and provincial labour/remittance series, so the hunger component stops leaning on national data;
- **(c)** accumulate more outcome quarters.

## 4. Files changed (E45)

**Backend:**

| File | Change |
|---|---|
| `app/services/dashboard.py` | `_news_pool`, `_feed_window`, `FOOD_CONTEXT`, rewritten `_e31_news`; `article_count` uses the feed; `lgu_map_status` with map fields on LGU rows |
| `app/ml/inference/e31_engine.py` | disaggregator passes `vulnerability_index` |
| `app/schemas/public.py` | Article: relevanceStatus/Label, province, triggers, quarter, collectedRetrospectively. NewsResponse: windowQuarters, validatedCount, triggerMatchCount, feedNote. MunicipalitySummary: map fields. |
| `tests/integration/test_e45_news_and_map.py` | 9 tests |

**Frontend:**

| File | Change |
|---|---|
| `src/components/RightAnalyticsPanel.tsx` | news panel |
| `src/components/PhilippineMap.tsx` | LGU colours and tooltips |
| `src/components/MapLegend.tsx` | municipal legend |
| `src/components/MapDashboard.tsx` | passes `municipal` to the legend |
| `src/components/LeftPanel.tsx` | text fix |
| `src/lib/apiTypes.ts`, `src/lib/adapters.ts`, `src/data/types.ts` | types, adapter, `lguMapColor` |
| `src/test/lguMapColor.test.ts` | 2 tests |

**Experiment folder:** `aipheed-backend-aligned/experiments/E45_News_Map_Fix/` (this report, `e45_model_diagnostics.py`, `evidence/`).

## 5. Tests and commands

| Suite | Result |
|---|---|
| Backend | **346 passed, 18 skipped** (the long-standing superseded tests) |
| Frontend | vitest **38/38**; `vite build` OK; `tsc` shows the same 6 errors as the approved baseline, none in the changed files |
| E44 | 16 passed (unchanged) |

```
cd backend && venv/Scripts/python.exe -B -m pytest -q -p no:cacheprovider tests
cd frontend && npx vitest run && npx vite build
backend/venv/Scripts/python.exe -B aipheed-backend-aligned/experiments/E45_News_Map_Fix/e45_model_diagnostics.py
```

**Live:**
- `.claude/launch.json` configurations `aipheed-e44-api` (port 8001) and `aipheed-e41-frontend` (port 8082).
- Screenshots of the Laguna, Quezon and Cavite views (coloured LGUs and legend) were captured in the session.
- Fill counts are recorded in `evidence/live_verification_20261016.json`.

## 6. Decision

- **News feed:** fixed and verified.
- **Municipal map:** fixed and verified.
- **Software:** ready for a controlled demonstration behind `AIPHEED_LEAD2_MODEL=e44`. The production default is unchanged.
- **Forecasting:** acceptance (75% Lead-2 accuracy with balanced discrimination) **NOT met**. The blocker and the concrete paths above are documented.
- **DA validation:** not done and not claimed.
