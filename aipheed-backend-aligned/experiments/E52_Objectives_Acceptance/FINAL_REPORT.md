# E52 final report: Chapter 1 acceptance tests for the food-price-pressure candidate

**Date:** 2026-10-17. **Branch:** `e46-lead2-policy`, not pushed. **Production default:** unchanged (E38). E52 is served only with `AIPHEED_LEAD2_MODEL=e52`.

The protocol was frozen and committed before any E52 score (`PROTOCOL.md`, sha in `runner/PROTOCOL_SHA256.txt`, commit 892ecaa). The Chapter 1 objective-to-test mapping is in `OBJECTIVES.md`.

## 1. Answer per criterion

| Criterion | Result | Status |
|---|---|---|
| ≥ 75% accuracy at the thesis horizon (Lead-2) | 0.760 on the PS target (95% CI 0.66–0.88); 0.709 or lower on the thesis Eq.3 label (E38/E51) | **Met on PS as development evidence only.** Not met on the thesis label. The CI's lower bound is below 0.75. |
| Beats all Objective 4 baselines on identical rows | Lowest Brier (0.190) and highest balanced accuracy (0.752) of all 11 arms, on 50 rows across 10 quarters | **Met** (development evidence) |
| Meaningful HIGH/LOW discrimination | HIGH recall 0.722, LOW recall 0.781, AUC 0.797, precision 0.65 | **Met** |
| Reliable probabilities | Brier 0.190; calibration-in-the-large −0.094 (forecasts about 9 points too high on average) | **Partly met:** best of all arms, but over-predicts |
| Consistent per quarter | Leave-one-quarter-out minimum 0.733; per-quarter accuracy 0.6 to 1.0 (4 of 10 quarters at 0.6) | **Partly met:** consistent across held-out quarters, not uniform |
| Generalization | All 10 quarters were examined while the model was designed in E46/E47 | **Not established.** The independent test is the frozen 2027-Q1..Q4 forecasts (20 province-quarters). |
| Five triggers aligned and used | All five groups have inputs. Market drives every one of the 60 explanations; Climate contributes in 21, Employment in 15, OFW in 5, Fish Kill in 0. | **Aligned and used as inputs.** Only Market has a large effect. |
| Explanations faithful and simple | Each group's effect is the log-odds change of the served probability when its inputs are set to their training mean. Reconciliation checks pass within 1e-8 on all 60 entries. The dashboard shows one sentence plus the top reasons with evidence and period. | **Faithful and simple.** This is a SHAP-style grouped attribution, not TreeSHAP. |
| Useful to DA | Province food-price pressure one quarter ahead of the dashboard's next quarter, with result, probability, reasons, evidence and data status | **Useful as an early price-pressure signal.** It is not a food-insecurity forecast. |

**Bottom line:**
- E52 meets the frozen development criteria A1–A5 on the provincial food-price-pressure target (PS).
- It does not meet the 75% requirement on the thesis Eq.3 label, which is saturated by the SWS level shift (E51).
- Using PS as the provincial target needs the **adviser's approval**.
- Independent acceptance waits for the 2027 outcomes.

## 2. Baseline comparison (identical rows: 2024-Q2..2026-Q3, 5 provinces, 18 HIGH)

Source: `tables/metrics.csv`, run `runs/20261017T132935Z`. The repeat `runs/20261017T134130Z` is byte-identical apart from its timestamp.

| Arm | Acc | Bal acc | Recall H | Recall L | Prec | F1 | Brier | AUC |
|---|---|---|---|---|---|---|---|---|
| **E52-PS** | **0.760** | **0.752** | 0.722 | 0.781 | 0.650 | 0.684 | **0.190** | **0.797** |
| B1 naive persistence | 0.620 | 0.630 | 0.667 | 0.594 | 0.480 | 0.558 | 0.380 | 0.630 |
| B2 PSA-only, logistic | 0.500 | 0.597 | 0.944 | 0.250 | 0.415 | 0.576 | 0.417 | 0.661 |
| B3 PSA-only, LightGBM | 0.440 | 0.562 | 1.000 | 0.125 | 0.391 | 0.562 | 0.354 | 0.595 |
| B4 NLP-only, logistic | 0.420 | 0.535 | 0.944 | 0.125 | 0.378 | 0.540 | 0.337 | 0.731 |
| B5 NLP-only, LightGBM | 0.520 | 0.601 | 0.889 | 0.312 | 0.421 | 0.571 | 0.325 | 0.678 |
| B6 logistic, combined | 0.500 | 0.561 | 0.778 | 0.344 | 0.400 | 0.528 | 0.365 | 0.684 |
| B7 E38 LightGBM procedure | 0.460 | 0.578 | 1.000 | 0.156 | 0.400 | 0.571 | 0.333 | 0.601 |
| Climatology | 0.360 | 0.500 | 1.000 | 0.000 | 0.360 | 0.529 | 0.309 | 0.682 |
| Always HIGH | 0.360 | 0.500 | 1.000 | 0.000 | 0.360 | 0.529 | 0.640 | n/a |
| Always LOW | 0.640 | 0.500 | 0.000 | 1.000 | n/a | n/a | 0.360 | n/a |

Confusion for E52-PS: TP 13, TN 25, FP 7, FN 5.

## 3. Per-quarter results (`tables/per_quarter.csv`)

| Target | HIGH | E52 acc | E52 Brier | Persistence acc | Persistence Brier |
|---|---|---|---|---|---|
| 2024-Q2 | 4 | 0.8 | 0.204 | 0.8 | 0.200 |
| 2024-Q3 | 1 | 1.0 | 0.082 | 0.6 | 0.400 |
| 2024-Q4 | 3 | 0.6 | 0.350 | 0.4 | 0.600 |
| 2025-Q1 | 4 | 0.6 | 0.175 | 1.0 | 0.000 |
| 2025-Q2 | 3 | 0.6 | 0.220 | 0.6 | 0.400 |
| 2025-Q3 | 2 | 0.6 | 0.240 | 0.8 | 0.200 |
| 2025-Q4 | 0 | 1.0 | 0.096 | 0.2 | 0.800 |
| 2026-Q1 | 0 | 1.0 | 0.073 | 0.4 | 0.600 |
| 2026-Q2 | 1 | 0.6 | 0.250 | 0.4 | 0.600 |
| 2026-Q3 | 0 | 0.8 | 0.210 | 1.0 | 0.000 |

**Where E52 does worse:** persistence beats it in 2025-Q1, 2025-Q3 and 2026-Q3, the quarters where the price state did not change. E52's advantage comes from the turning points: 2024-Q3, 2025-Q4 and 2026-Q1.

## 4. Before and after

| | Target | Lead-2 accuracy | Balanced acc | HIGH recall | Beats every baseline |
|---|---|---|---|---|---|
| Production E38 (default) | thesis Eq.3 label (saturated) | 0.709 | n/a (label 40/45 HIGH in 2024–26) | n/a | no |
| E44 I2 (five-trigger) | T43 | 0.686 | 0.716 | n/a | no |
| E46 I7 (five-trigger component model) | T43 | 0.800 | n/a | 0.44 | no (discrimination fails) |
| **E52-PS** | **PS (food-price pressure)** | **0.760** | **0.752** | **0.722** | **yes (development)** |

E38, E44 and E46 figures are from their own reports on their own rows. Only the E52 row is on the identical E52 rows.

## 5. Five-trigger audit (`tables/trigger_audit.csv`; 60 province-quarters = 11 past quarters + 2027-Q1, × 5)

| Trigger | Inputs in the model (period at issue) | Contributes | No effect | Largest effect (pts) | Ranked first |
|---|---|---|---|---|---|
| Market / Prices | PSA provincial food and headline CPI, base-effect projections, wholesale rice, rice-policy orders (CPI through the month before the origin) | 60 | 0 | 5.58 | 58 |
| Climate Stress | typhoon tracks within 300 km (origin quarter), ENSO ONI, PSA palay production (previous quarter) | 21 | 39 | 0.82 | 1 |
| Fish Kill | PSA fisheries and aquaculture production (previous quarter); no official fish-kill event series exists | 0 | 60 | 0.08 | 0 |
| Employment | PSA LFS national unemployment (previous quarter) | 15 | 45 | 0.47 | 1 |
| OFW Remittance | BSP national cash remittances, ECB USD/PHP (previous quarter) | 5 | 55 | 0.14 | 0 |

**Status rule (E47):** a group "contributes" when it moves projected food inflation or the gap by at least 0.1 points. No group was "insufficient_data" at any issue date. Employment, OFW and ENSO are national, so they shift every province equally.

**Reading:**
- The five triggers are aligned with Chapter 1 §1.7 and are all real inputs.
- Food-price pressure is mostly explained by the price series themselves.
- The other four triggers make small corrections.

## 6. Explanation examples (`tables/explanation_examples.md`)

Quezon, 2027-Q1 (issued 2026-10-01): probability of food-price pressure 0.152, LOW.
- **Market / Prices:** lowers it (log-odds −2.34). Food inflation was 3.6% in the latest two months (through 2026-08), against the province's reference of 6.24%. Food minus headline was −2.5 points (PSA CPI).
- **Employment:** lowers it slightly (−0.04). National unemployment was 4.79% in 2026-Q2 (PSA LFS).
- **Climate, Fish Kill, OFW:** no measurable effect.

The dashboard shows this as one sentence:
> "Food-price pressure in Quezon for 2027-Q1 is forecast LOW (15% probability), mainly because Market / Prices lowered it."

The trigger cards carry the evidence and period. Data status is shown: sufficient, limited or unavailable.

## 7. System validation (live, `aipheed-e52-api` on port 8001 + frontend on port 8082, clock 2026-10-17)

**Map and probabilities:**
- The map, ranking and province cards show the E52 probabilities for 2027-Q1, matching the frozen file to 1e-9.
- The timeline marks 2024-Q2..2026-Q3 as backtests and 2026-Q4/2027-Q1 as forecasts.
- 2025-Q2/Q3 are now served: PS is CPI-only, so they no longer need an SWS round.

**Plain-language summary:**
- The right panel shows the summary sentence and data status.
- **Region:** "Food-price pressure in CALABARZON for 2027-Q1 is forecast LOW (7% probability)…".
- **Past quarter:** "The backtest estimate … for 2026-Q3 was HIGH (90% probability; observed LOW)…".
- **Earlier forecast:** "The earlier Lead-2 forecast … for 2026-Q4 … outcome not yet published…".

**Display defects found and fixed during the check** (logic only; no colour or design change):
1. The province card kept the score from the moment the province was clicked. After changing the quarter it showed 0.15 (2027-Q1) while the right panel showed 0.90 (2026-Q3). The selection now follows the quarter, and the same fix applies to municipalities.
2. The province card's note described the 2027-Q1 forecast on every quarter. It now says "backtest estimate … made as of 2026-04-01 … observed outcome" or "Lead-2 forecast … issued 2026-07-01 … not yet published", as appropriate.

**Other checks:**
- **News, archive and municipalities:** the endpoints return 200 for every candidate quarter, including 2025-Q2/Q3.
- **Municipalities:** labelled as relative prioritisation from the province forecast; a municipality's summary names its province ("Quezon (province of Infanta)").
- **Dynamic target:** `/quarters` gives target 2027-Q1, origin 2026-10-01.
- **Console:** the only errors are from the offline basemap tile archive ("Wrong magic number for PMTiles archive"). They are unrelated to E52 and pre-existing.

**Tests:**

| Suite | Result |
|---|---|
| Backend | 374 passed, 18 skipped (before the frontend-only fixes; backend unchanged since) |
| E52 serving tests | 6 passed |
| E52 experiment tests | 4 passed |
| Frontend | tsc clean, eslint clean, 45 vitest passed |

## 8. Objective status (Chapter 1)

| # | Objective | Status | Why |
|---|---|---|---|
| 1 | NLP pipeline → FSSI and topics | **Partial** | Built; the relevance filter has precision 0.85 but recall 0.40 (E31); the FSSI rests on a small corpus (E28: 49 articles, titles only; rebuilt as FSSI-v2 in E31) |
| 2 | Evaluate LightGBM with the listed metrics, walk-forward, 75% reliable lead | **Partial** | All metrics reported. 75% at Lead-2 is met only on PS, in development evidence; not on the thesis label. The served E52 model is a ridge component model, not LightGBM; LightGBM baselines (B3, B5, B7) are worse on PS. |
| 3 | Municipal rankings from validated province forecasts | **Partial** | All 142 LGUs ranked from PSA SAE 2021 and POPCEN 2024, as prioritisation. "Validated" depends on objective 2's prospective test. |
| 4 | Compare against persistence, PSA-only, NLP-only and logistic baselines | **Complete** (development) | E52 beats every baseline on Brier and balanced accuracy on identical rows |
| 5 | Dashboard, alerts, ISO/IEC 25010 evaluation, FNRI face validity | **Partial / blocked** | Dashboard built and live-verified. The ISO/IEC 25010 survey needs the 50 DA Region IV-A respondents; the FNRI check needs the NNS 2019/2023 figures. Both are external. |

## 9. Limitations

- **Hindsight:** the candidate was designed on the same quarters it is scored on. The historical result is confirmation, not independent validation.
- **Sample size:** 50 rows from 10 quarters, with an accuracy CI of 0.66–0.88. A 75% level cannot be distinguished statistically from about 66%.
- **What PS measures:** food-price pressure, not hunger or household food insecurity. SWS hunger stays a separate regional indicator.
- **Calibration:** forecasts are about 9 points too high on average.
- **Trigger effects:** Market dominates. Fish Kill has no measurable effect because there is no official fish-kill series, and production proxies barely move prices.
- **National inputs:** Employment, OFW, ENSO and policy inputs are national.
- **Model family:** E52 is not LightGBM. Chapter 1 names LightGBM, so this is a deviation the adviser must accept or reject.

## 10. Decisions for the adviser

1. **Target:** approve PS (provincial food-price pressure) as the provincial forecasting target, with SWS hunger shown separately. Or keep the thesis Eq.3 label and report that 75% is not reached.
2. **Model family:** accept a ridge component model (E52) in place of LightGBM for the served forecast, with LightGBM kept as a compared baseline.
3. **Production switch:** whether to make `e52` the dashboard default after approval. It currently stays E38, and nothing has been switched or pushed.
4. **Prospective acceptance:** confirm the 2027-Q1..Q4 rule (A1, A2, and A3 against persistence and always-HIGH/LOW, on 20 province-quarters) as the independent test.

## 11. Artifacts and hashes

| Artifact | SHA-256 |
|---|---|
| `backend/data/e52/e52_record.json` | 3e557a43588f017ffc7ef7ab5108eb74fb5660f9273e8b70e3d9f5149ce4f05c |
| `frozen/E52_PS_PROSPECTIVE_2027Q1.json` | dc01bb84b3c4e03e3d038f40bcc7904ab15cc48c2cb346ff000a86d3016fabaf |
| source `E46_I7_PROSPECTIVE_2027Q1.json` | 5592d53e… (verified by the build and the tests) |
| `PROTOCOL.md` | in `runner/PROTOCOL_SHA256.txt` |

**Frozen 2027-Q1 P(food-price pressure):** Cavite 0.064, Laguna 0.053, Quezon 0.152, Rizal 0.031, Batangas 0.040. All are LOW.

## 12. Modified and added files

**Backend:**
- `app/ml/inference/e41_lead2.py`: e52 mode and record.
- `app/api/v1/insights.py`: E52 note and summary.
- `app/schemas/public.py`: `PlainSummary`.
- `app/services/dashboard.py`: `plain_summary`; candidate quarters served when the base engine lacks them.
- `app/api/v1/forecast.py`: timeseries uses the candidate's quarters.
- `scripts/build_record_e52.py`.
- `data/e52/e52_record.json`.
- `tests/integration/test_e52_food_price_pressure.py`.

**Frontend** (text and logic only):
- `src/lib/apiTypes.ts`;
- `src/components/RightAnalyticsPanel.tsx`: the summary sentence;
- `src/components/MapDashboard.tsx`: the selection follows the quarter;
- `src/components/LeftPanel.tsx`: the estimate-kind note.

**Experiment:**
- `runner/e52_baselines.py`, `runner/e52_tables.py`;
- `runs/` (2 runs), `tables/`, `frozen/`, `tests/`;
- `OBJECTIVES.md`, `PROTOCOL.md`, this report.

**Local only:** the launch configuration `aipheed-e52-api`, in the gitignored `.claude/launch.json`.
