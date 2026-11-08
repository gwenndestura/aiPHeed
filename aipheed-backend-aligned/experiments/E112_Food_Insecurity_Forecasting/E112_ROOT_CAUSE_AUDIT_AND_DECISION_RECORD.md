# E112 Root-cause audit of E107–E111 and decision record

**Sources:**
- E107 `EXPERIMENT_REPORT.md`; E108 `ROOT_CAUSE.md`, `MAX_LEAD_DECISION.md`;
- E109 / E110 / E111 reports and `out/*.json`;
- E85 (GDELT) and E83–E87 (news) reports;
- the corpus statistics measured in E112 (`out/news_quarterly_*.csv`).

All numbers are cited from those files.

## 1. Root causes

| Symptom | Root cause (verified) | Fixable now? |
|---|---|---|
| **Models do not beat the latest reading** | (a) **20 regional outcome quarters.** Every learned model trains on 8–17 pairs and is tested on 5–13 quarters (E109–E111). (b) SWS's **publication delay** makes "Lead 1" two quarters past the newest reading at 19 of 21 issue dates (E111). (c) **Survey noise:** ±4–6 points per reading, a substantial (not precisely estimable) share of each change (E111). | (b) is now handled by reporting true horizons. (a) and (c) are not fixable with 2021+ data. |
| **2024 surge not anticipated** | No predictor available at the issue dates moved ahead of the surge: food inflation was falling, national indicators did not lead (E110 NAT-R worse), and news shares follow the typhoon calendar (E85). The surge also began in a quarter whose SWS reading sat exactly on the 11.3% line (E108). | Tested again in E112 with de-seasonalised news; see the news report |
| **Weak performance across quarters** | Two regimes in 20 quarters: a low, stable 2021–23; a surge in 2024; an oscillating 2025–26 after a respondent-base and design change (E110, E111). A method fitted to one regime fails in the other. | Not fixable by modelling; needs more quarters |
| **No reliable horizon** | Follows from the rows above. E111 Lead 1: surge-protected smoothing passes everything except the falling-hunger check. Lead 2: smoothing passes everything except the ±4-point Balance Luzon bound. | Prospective quarters needed |
| **12-family LightGBM no better** | Depth-1 trees on 8–17 pairs. CALABARZON-specific families describe one region whose outcome is a single Balance Luzon number. Four families are national (C1, E1, E2, H1) and act as period markers (E107). V1 is constant over time. | Not fixable by tuning; kept as the required candidate |
| **News contributes nothing measurable** | (a) **Sparse relevant news:** the relevance classifier admits 695 of 9,667 headlines, only 2–7 per quarter in 2021–22, and only 379 headlines have XLM-R scores (E112 measurement). FSSI-v3 exists for 17% of province-quarters. (b) **The relevance filter is noisy:** off-topic admissions such as "A Growing Shortage: Why Fewer Men Are Choosing Priesthood". (c) **Seasonality and coverage drift:** raw shares follow the typhoon calendar (E85), and the corpus grows about 4× from 2021 to 2026. (d) Titles only, collected retrospectively. | (a)–(c) **are addressed in E112:** a lexicon over all headlines, coverage-normalised shares, year-over-year de-seasonalising, and the gap-quarter timing. (d) is a disclosed limitation. |
| **Regional measurement vs municipal predictions** | SWS publishes Balance Luzon only. No provincial or municipal hunger, FIES or CBMS series exists in the project for 2021+. LGU rankings were province scores × fixed vulnerability weights (E107, E109). | **Not fixable without new authoritative data.** Municipal forecasts are not claimed. |

## 2. Decision record

| Method or component | Decision | Reason |
|---|---|---|
| T43 composite (hunger × provincial price) as the "food-insecurity" target (E106–E108) | **Discontinued as the outcome** | Since 2023-Q4 its variation has been price pressure only (E108). It is not observed food insecurity. |
| PS food-price-pressure LightGBM (E56, E108 factored) | **Discontinued as a hunger forecast**; kept only as a price-pressure context indicator | It forecasts prices, not hunger |
| FIRI v2 composite as the headline risk | **Not a forecast.** It remains the served dashboard index (unchanged, per the user's design rule) and is described as a composite proxy | It was never validated against an observed outcome at the province level |
| SWS Total Hunger (Balance Luzon) as the outcome | **Retained (final)** | It is the only repeated, directly observed hunger measure for the area, 2021+ |
| Latest-reading forecast (RW) | **Retained as the reference and the default forecast** | Never beaten by any learned model under the rules |
| Smoothing (LLR / COMB, E110) | **Retained only as an exploratory prospective candidate** (Lead 2) | Fails the ±4 bound; consistent gain otherwise (E111) |
| Surge-protected smoothing (ASYM, E111) | **Retained only as an exploratory prospective candidate** (Lead 1) | Designed after seeing the data; fails the falling-hunger check |
| National-indicator ridge (NAT-R, E110) | **Discontinued** | Clearly worse (E110) |
| Momentum (DT, E111) | **Discontinued** | φ̂ ≈ 0 |
| Break restart (BRK, E111) | **Discontinued** | No gain over LLR |
| 12-family LightGBM | **Retained as the required candidate**, now with improved news indicators (E112) | Required by the thesis |
| News: FSSI-v3 per province-quarter | **Retained in the N family**, not as a standalone forecast signal | Too sparse (17% coverage) |
| News: E112 event-category indicators (regional, de-seasonalised) | **New; tested in E112** | Addresses root causes (a)–(c) |
| GDELT themes (E85) | **Retained as an independent cross-check source** for the news test | Dense, but seasonal in raw form |
| Binary LOW/HIGH thresholds (11.3 / 15 / 20) | **Discontinued as targets** | No official SWS threshold; one-class evaluation sets (E109) |
| Retrospective "reliable" claims on seen quarters | **Discontinued** | Every quarter through 2026-Q3 has been examined. Reliability now requires sealed prospective scoring. |

**What will no longer be repeated:**
- re-tuning learners on the same 20 quarters;
- new thresholds;
- new composite targets;
- adding model complexity.

The remaining gap is **data** (outcome quarters, local outcomes), not algorithms.
