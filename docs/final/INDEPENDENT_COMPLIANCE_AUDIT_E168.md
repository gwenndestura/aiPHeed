# Independent compliance and validity audit of the current aiPHeed model (E168)

Audited 2026-11-07. This was verification only: no model, data, endpoint or interface was changed.

**What was audited:** branch `aiPHeed/e158-thesis-model` in `C:\Users\admin\aipheed_e145`, HEAD `61f894a5`. The production registry pointer is `e168-lgbm-1.0`.

**Standard:**
- The five research objectives and the ten system requirements given in the audit brief.
- **Reliability rule:** the project acceptance standard (owner decision 2026-11-07). A lead is reliable when pooled accuracy is ≥ 75 % **and** Brier is significantly better than reusing the latest survey (95 % CI < 0).
- The thesis document's Algorithm 3, its target label and its Chapter III procedures are **not** used as criteria (owner instruction).

**Statuses:**
- **PASS:** verified here by running code or reading data.
- **FAIL:** the implementation or its results violate the requirement.
- **PARTIAL:** some elements are met, important ones are not.
- **BLOCKED:** necessary evidence does not exist.

## A. Overall verdict: **NOT COMPLIANT**

The current model is a real, leakage-tested, one-quarter-ahead LightGBM forecast of provincial HFIAS food insecurity.
- It beats naive persistence and the four required baselines on the same rows.
- **Under the project reliability rule, its maximum reliable lead time is 3 quarters** (75.0 / 77.8 / 75.0 %, each significantly better than the latest survey).

Even so, it fails several requirements:

1. **Lead-time evidence is thin.**
   - The 75 % is met exactly at Leads 1 and 3. One more wrong forecast out of 72 drops it to 73.6 %.
   - All rows come from 3 survey rounds.
2. **Only one of the five contributor groups (market) adds demonstrable information.**
   - Removing employment, remittances or poverty does not lower accuracy.
   - The model is not better than the same model with all trigger inputs shuffled between provinces.
3. **The NLP objective is only partly met.**
   - The FSSI exists but is not an input to E168.
   - The FSSI barely tracks food prices (within-province ρ = 0.03).
   - The FSSI points the wrong way on two known rice shocks.
   - Tier 1 is not pure zero-shot XLM-RoBERTa (deviation D3).
4. **The dashboard is inconsistent.**
   - Only the status card uses E168.
   - The map, provincial summary, explanations, LGU ranking and alerts come from a different model (the CH1 price-pressure index) and a different quarter (2026-Q4, against E168's 2027-Q1).
   - Several texts still say the forecast is "validation pending".
5. **E168 is not deployed.** The public API serves FIRI v2 and has no outlook route.
6. **The ISO/IEC 25010 evaluation has not been run.** No evaluator responses exist.
7. **The FNRI 2023 face-validity comparison is not implemented.**
8. **The target is survey-based (HFIAS rounds 2018, 2019, 2021), not quarterly.** Of the 72 validation rows, only 5 are CALABARZON provinces, and all 5 are LOW.

## B. Mandatory requirement results

| Requirement | Result | Evidence |
|---|---|---|
| Five CALABARZON provinces | **PARTIAL** | The live forecast covers all five (`serve._forecast`; outlook returns 15 rows at Leads 1–3). Validation rows: 72 provinces nationwide, of which only 5 are CALABARZON (all observed LOW), so HIGH detection in CALABARZON is untested. |
| Quarterly forecasting | **PARTIAL** | Forecasts are indexed by quarter (issue 2026-Q4, targets 2027-Q1 to Q3). Labels exist only at survey rounds, so validation covers 3 survey quarters, not consecutive quarters. `live_2027.json` is a one-off export; no quarterly job regenerates it. |
| LightGBM is the actual model | **PASS** | `app/e168/lgbm_only.py` `LGBRes` (`lgb.LGBMRegressor`) predicts the change from a statistical survey baseline. LightGBM is the only learned predictor; the baseline and calibration are fixed formulas chosen on training rows. |
| Genuine one-quarter-ahead forecast | **PASS (with caveat)** | Origin 2026-Q4 (`qindex("2026-Q4")`), target `T = issue + lead`, so Lead 1 = 2027-Q1 is the next quarter. In validation, origin `i = RQ[survey] − lead`. Survey rounds are gated by `M.released` (6-quarter publication lag). The leakage test corrupts unreleased rounds and changes no forecast (`leakage_max_abs_change` 0.0). Reproduction: re-run from code matches the served 2027-Q1 values for all 5 provinces (F). |
| Five contributor groups connected | **PASS** | All five groups are in `FS["GOV"]` and `FS["FULL"]` (66 columns). The served configuration `RSS\|FULL\|prune=False` uses them. |
| Meaningful contributor evidence | **FAIL** | Group ablation (`data/e168/out/results.json` `ablation`, Lead 1):<br>• Only market's removal worsens Brier with a CI excluding 0 (−0.0073 [−0.0154, −0.0001]).<br>• Climate: CI includes 0.<br>• Accuracy without employment 77.8 %, without remittances 76.4 %, without poverty 79.2 %, all at or above the full model's 75.0 %.<br>• Shuffled-input control: E168 − shuffled Brier −0.0003 [−0.0151, +0.0178], not better.<br>• NLP removal (run in this audit): Brier change 0.0000 [−0.0015, +0.0015], accuracy 75.0 → 73.6 %. |
| Valid NLP pipeline | **PARTIAL** | Code exists for XLM-RoBERTa (`app/e151/score.py`), BERTopic per origin (`app/e151/topics.py`) and FSSI (`app/e151/fssi.py`); outputs exist. Weaknesses are in section 6. |
| Valid target construction | **PARTIAL** | HFIAS moderate+severe from FNRI provincial estimates, measured, not synthetic. HIGH at ≥ 50 %. 25 HIGH / 47 LOW across 72 rows. Survey rounds only. |
| No temporal leakage | **PARTIAL** | Survey labels are verified by the corruption test, and inner selection uses training rows only. Feature publication rules are coded (`app/e147/features.py` header: PSA poverty +2 years, SWS by published date, NASA soil +2 months, news by publication date) but were not verified series by series in this audit. |
| Walk-forward validation | **PARTIAL** | Chronological, as-of origins with expanding training (2018 → 2019 → 2021). There are only 3 survey-round folds, not quarterly folds advancing one quarter. |
| All five evaluation metrics | **PASS** | Recomputed here (`app/e168/thesis_metrics.py`). Lead 1: accuracy 0.750, precision 0.595, recall 0.88, F1 0.710, AUC 0.891. Confusion: TP 22, FP 15, FN 3, TN 32. |
| Maximum reliable lead time | **PASS: 3 quarters** | Project rule: Leads 1–3 have accuracy 75.0 / 77.8 / 75.0 % and Brier better than the latest survey (CI < 0). Lead 4 has 73.6 %, so the search stops. Skill over persistence holds to Lead 6 (`data/e168/out/lead_horizon.json`, `horizon_75pct_and_beats_persistence` = 3).<br>**Caveats:**<br>• The rule was fixed on 2026-11-07, after E168's results were known.<br>• Leads 1 and 3 meet 75 % exactly. |
| Four baseline comparisons | **PASS** | Same 72 rows, labels, origins and leads (`data/e151/out/prov_oof.csv`; label agreement 1.000). Table in section 9. |
| Municipal and city disaggregation | **FAIL** | `/api/v1/final/lgus` and the map start from the CH1 price-pressure index and indicator scores, not from E168. `app/e168` has no LGU code. Some LGUs have no poverty value (for example Lucena: "No PSA 2021 municipal poverty estimate"). |
| Backend consistency | **FAIL** | `/final/food-insecurity/outlook` = E168, 2027-Q1, all LOW. `/provinces`, `/forecast` and `/explainability` = CH1 price-pressure index for 2026-Q4. `/explainability` statusNote says "validation-pending" (`app/services/dashboard.py:1038`). |
| Frontend consistency | **FAIL** | `FoodInsecurityStatus.tsx` renders only E168's summary text. The map colours, ranking and CALABARZON summary come from the other endpoints. `Landing.tsx:112, 547, 676` hard-code "validation pending". Seen in the browser: the E168 card says all LOW while the summary showed "High risk / Active alert" (that run used the FIRI map setting). |
| Public deployment | **FAIL (for E168)** | `https://aipheed-api.onrender.com/api/v1/final/food-insecurity/outlook` returns 404, as does `/final/model-registry`. `/provinces` returns FIRI v2 for 2027-Q1. The frontend URL returns 200. E168 commits are local only (no remote branch contains `0e1cb961`). |
| ISO/IEC 25010 evaluation | **BLOCKED** | Only an instrument package exists (`E114_OBJECTIVE5_EVALUATION_PACKAGE.md`, which says "it needs the respondents"). No responses or results. |
| FNRI face-validity comparison | **PARTIAL / FAIL** | 2019: the CALABARZON provinces in ENNS 2019 (Quezon, Rizal) are back-test rows; Lead-1 errors are +0.8 and −4.8 points (`results.json` bias rows). 2023: no comparison is implemented. The only 2023 figure is regional FIES 19.1 % (`app/e169/fies_bridge.py`), a different measure and level. |

## 3. The model actually in use

| Item | Finding |
|---|---|
| Production pointer | `backend/data/registry/registry.json` → `e168-lgbm-1.0`. Approval `approvals/e168-lgbm-1.0.json` (owner, 2026-11-07); gate `gate_results/e168-lgbm-1.0.json` (owner gate O1–O7). |
| Serving | `app/api/v1/registry.py` `PRODUCTION_SERVERS["e168-lgbm-1.0"] = ("app.e168.serve", "outlook")`. `outlook()` reads `data/e168/out/live_2027.json`, whose hash is verified by `R.production()`. |
| Training and prediction | `app/e168/serve.py` `_forecast()` calls `app.e168.lgbm_only.run_proc` (the same function used in validation) at issue 2026-Q4 for Leads 1–3. |
| Target | HFIAS moderate+severe %, logit scale (`y_true`). HIGH if P(HIGH) ≥ 0.5. |
| Served configuration | `RSS\|FULL\|prune=False\|leaves=3,minchild=10,lambda=20.0,trees=400\|cal=raw`, re-selected on training rows at the new origin (validation origins chose `OH\|GOV\|prune=True` in 2018/2019 and `RSS\|FULL\|prune=True` in 2021). |
| Hard-coded predictions | None found. Values come from `run_proc` output written to JSON; the class is `p ≥ 0.5`. |
| Rejected models still connected | `PRODUCTION_SERVERS` and `CANDIDATES` still list e139–e143 and pfi, but they are served only if the registry approves them; candidates are admin-only. The **map and LGU endpoints still serve CH1**, an un-gated model with a different target. |
| Version traceability | Registry, artifact sha256, approval record and seals (`f8228fae` ENNS 2022). |
| Reproducibility | **PASS.** `_forecast(1)` re-run gives identical 2027-Q1 values for all five provinces and the same configuration. |
| Production vs validation features | **Medium risk.** Production adds `E154.add_income` before `N.add_sources`; validation `task()` calls only `N.add_sources`. This can change the `+cons` feature-set candidates during selection. The selected set (FULL, no consumption) is unaffected, but selection could differ. Not verified to be identical. |

## 5. Contributor-group traceability (Lead 1)

**Common to all groups:**
- All are reached through `Pv.add_inputs`.
- Used by LightGBM: yes, in the served FULL configuration.
- Empirical contribution is the change in Brier when the group is removed (E168 minus without). A negative value means the group helps.

| Group | Actual indicators | Geography | Empirical contribution | Status |
|---|---|---|---|---|
| Market and prices | food CPI YoY, rice CPI YoY, 3-month food CPI change, acceleration, CPI relative to national, change since survey | province CPI | −0.0073 [−0.0154, −0.0001]; accuracy without: 69.4 % | **Meaningful (marginal)** |
| Climate stress | soil and rainfall anomalies, cyclones (4 quarters), agricultural and fisheries YoY, ONI, changes since survey | province, national (ONI) | −0.0044 [−0.0111, +0.0014]; without: 72.2 % | **Not demonstrated** |
| Employment | unemployment rate, YoY change, change since survey, regional unemployment | **national/regional** | +0.0003 [−0.0004, +0.0011]; without: 77.8 % | **Not meaningful** |
| OFW remittances | remittance YoY, since survey, quarterly YoY | **national** | +0.0001 [−0.0002, +0.0003]; without: 76.4 % | **Not meaningful** |
| Poverty and vulnerability | PSA poverty incidence, subsistence incidence, poverty gap, density (+2-year release rule) | province | +0.0008 [−0.0128, +0.0125]; without: 79.2 % | **Not meaningful** |
| NLP-derived (36 columns) | XLM-R event shares and BERTopic topic shares at province, area and national level; net, hunger, intensity | province, area, national | 0.0000 [−0.0015, +0.0015]; accuracy without: 73.6 % (−1 row); AUC 0.891 → 0.889. Forecasts identical in 2018 and 2019 (news not selected); max change 0.08 in 2021 | **Not meaningful** |

## 6. NLP objective

| Component | Finding | Status |
|---|---|---|
| XLM-RoBERTa zero-shot | `app/e151/score.py`: `joeddav/xlm-roberta-large-xnli`, 10 food-event hypotheses (food access, purchasing, supply, agricultural loss, income, climate, displacement, OFW, assistance, recovery). These are food events, not generic sentiment. Problem and relief reporting are separated. Output `data/e151/raw/events.parquet` exists. | **PARTIAL.** Tier 1 was changed (deviation D3) to combine XLM-R with embedding similarity and seed phrases (`app/e151/labeler.py`), so it is not pure zero-shot. The labeler output `data/e151/raw/labels.parquet` is missing from this checkout. The label check shows 69 % top-event agreement (Wilson 58–78 %), and the reader was the system author, so it is not independent. |
| BERTopic | `app/e151/topics.py`: one BERTopic per origin, fitted on earlier stories only, near-duplicates removed (cosine ≥ 0.93 within 7 days). `topic_report.csv`: 257 topics over 14 origins; 3.9 % flagged off-topic. | **PARTIAL.** No coherence or stability metric is computed in the code. |
| Bias-corrected FSSI | `app/e151/fssi.py`: FSSI = 50 + 10z, outlet-centred, shrinkage for few stories, one count per story. `fssi_province_quarter.csv` has 4,368 rows. | **PARTIAL.** It is generated but **not an input to E168**. Within-province ρ with food CPI is 0.03. Event z-scores are −1.0 at the 2018-Q4 rice surge and −1.3 at the 2023-Q4 rice crisis (wrong direction). CALABARZON province-quarters: 32.5 % use area fallback. The audit file states "no measurable gain one quarter ahead". |
| Province-quarter NLP indicators into LightGBM | 36 news columns in `FS["FULL"]`, used by the served configuration. Training selection rejected news for the 2018 and 2019 origins (GOV chosen). | **PARTIAL** |

## 7. Target

| Item | Finding |
|---|---|
| Variable | Provincial HFIAS moderate+severe household food insecurity (%), from FNRI NNS/ENNS (2013, 2015, 2018, 2019, 2021; 2021 from the FNRI provincial heat map). |
| Classes | HIGH at ≥ 50 % (`y_high = y_true ≥ 0` on the logit scale). |
| Counts (Lead 1) | 2018: 8 HIGH of 22. 2019: 13 of 25. 2021: 4 of 25. Total 25 of 72. Always-LOW accuracy would be 65.3 %. |
| Measured or derived | Measured survey estimates with standard errors; not interpolated, not regional copies. |
| Quarterly support | **Not supported.** Labels exist only in survey quarters; between rounds the system forecasts what a survey would show. |
| Risk vs prevalence | The output is a forecast prevalence plus HIGH/LOW class, labelled as a forecast on the card. It is not presented as a measurement. |
| Complexity vs information | About 46 effective rows from 3 rounds against 66 candidate inputs and a 384-configuration grid. The inner selection always picked the most constrained LightGBM (3 leaves). |

## 8. Validation and lead time (72 rows; 50 at Leads 7–8)

| Lead | Accuracy | Precision | Recall | F1 | AUC | Persistence accuracy | Better than latest survey (Brier CI < 0) | Project rule |
|---|---|---|---|---|---|---|---|---|
| 1 | 75.0 % | 0.595 | 0.88 | 0.710 | 0.891 | 62.5 % | yes | **pass** |
| 2 | 77.8 % | 0.629 | 0.88 | 0.733 | 0.893 | 62.5 % | yes | **pass** |
| 3 | 75.0 % | 0.600 | 0.84 | 0.700 | 0.873 | 62.5 % | yes | **pass** |
| 4 | 73.6 % | 0.588 | 0.80 | 0.678 | 0.860 | 62.5 % | yes | fail (stop) |
| 5 | 72.2 % | 0.571 | 0.80 | 0.667 | 0.849 | 62.5 % | yes | – |
| 6 | 69.4 % | 0.541 | 0.80 | 0.645 | 0.837 | 62.5 % | yes | – |

**Maximum reliable lead time (project rule): 3 quarters.**

- **Per round, Lead 1:** 68.2 / 76.0 / 80.0 %.
- **Bias:**
  - Overall +3.0 points [0.8, 5.1].
  - Luzon +4.7 [1.3, 8.2].
  - Observed-LOW +4.9 [1.9, 7.8].
  - The bias changes sign across rounds (+6.8, +3.9, −1.3).
- **Calibration slope:** 0.76 [0.55, 0.90].
- **Accuracy is not inflated by predicting LOW:** 37 of 72 predictions are HIGH, against 25 actual HIGH.

## 9. Baselines (Lead 1, the same 72 rows)

| Model | Accuracy | Precision | Recall | F1 | AUC |
|---|---|---|---|---|---|
| **LightGBM (E168)** | **0.750** | **0.595** | 0.88 | **0.710** | **0.891** |
| Naive persistence | 0.625 | 0.480 | 0.96 | 0.640 | 0.827 |
| PSA-only (logistic on PSA poverty) | 0.556 | 0.436 | 0.96 | 0.600 | 0.762 |
| NLP-only (logistic on news) | 0.639 | 0.487 | 0.76 | 0.594 | 0.703 |
| Logistic regression (all inputs + baseline) | 0.611 | 0.467 | 0.84 | 0.600 | 0.803 |

**Notes:**
- E168 beats every baseline on point estimates at Leads 1–3.
- Only the persistence comparison has a significance test (Brier CI < 0 at Leads 1–6).
- The other baselines come from the E151 run (`prov_oof.csv`) on identical rows, origins and leads.

## 10–13. Rankings, backend, frontend, deployment
- **LGU rankings (`/final/lgus`):**
  - 142 LGUs, labelled "Priority score (indicator-based; not a measured or forecast hunger rate)".
  - Built from the dashboard's CH1/indicator scores with PSA poverty and density, not from E168.
  - Correctly not described as measured prevalence.
  - Objective 3 requires rankings from the *validated province forecasts*, which they are not.
- **Alerts:** `/api/v1/alerts` returns `{"data": [], "total": 0}` locally. No early-warning alert is generated from E168.
- **Frontend data flow:**
  - `useFoodInsecurityStatus` → `/final/food-insecurity/outlook` → `FoodInsecurityStatus.tsx`, which shows E168 text only.
  - The map, ranking and summary come from `/provinces`, `/forecast` and `/explainability` (CH1).
  - So the province examples cannot be traced end to end from E168 to the map, ranking and alert.
- **Deployment:**
  - Render API live, serving FIRI v2.
  - Vercel frontend live (200).
  - The E168 routes are 404 on production.

## C. Critical failures

| # | Problem | Where | Objective | Severity | What must be done to pass |
|---|---|---|---|---|---|
| 1 | Lead-time result rests on 72 rows from 3 survey rounds; Leads 1 and 3 meet 75 % exactly | `data/e168/out/lead_horizon.json` | 2 | High | Score the sealed ENNS 2022 forecasts (`f8228fae`) when FNRI publishes provincial results |
| 2 | Four of five contributor groups add no demonstrable information; inputs not better than shuffled | `results.json` `ablation`, `shuffle` | 2, system req. 6 | Critical | Province-level employment and remittance data, or report these groups as non-contributing |
| 3 | Map, LGU ranking, explanations and alerts are not driven by E168 | `app/api/v1/final.py` `final_lgus`; `app/services/dashboard.py`; `ch1_system.py` | 3, 5 | Critical | Serve E168 province outputs to map, ranking and alerts, with LGU weights applied to E168 (backend only) |
| 4 | E168 not deployed | Render 404 on `/final/food-insecurity/outlook` | 5 | Critical | Push and deploy (owner decision) |
| 5 | ISO/IEC 25010 not conducted | E114 package only | 5 | Critical | Run with DA IV-A evaluators |
| 6 | FSSI not used by the model and fails event face-checks | `app/e151/fssi.py`, `fssi_audit.json` | 1 | High | Feed the FSSI into the model and revalidate, or report it as descriptive only |
| 7 | FNRI 2023 face validity missing | none | 5 | High | Compare E168 outputs with the published CALABARZON 2023 figure, stating that the measure differs (FIES regional vs HFIAS provincial) |
| 8 | Stale "validation pending" texts contradict the served model | `Landing.tsx:112,547,676`, `dashboard.py:1038`, `final.py:40` fallback | 5 | Medium | Update texts (backend fields first; frontend copy only with owner OK) |
| 9 | Possible production/validation feature-path difference | `serve.py` `E154.add_income` | 2 | Medium | Reproduce selection with the identical feature path |
| 10 | Validation contains no CALABARZON HIGH case | `oof.csv` | 2, 5 | High | Only new survey rounds fix this |

## D. Methodological decisions

**Scientifically invalid if presented as validation:**
- The project reliability rule was fixed after E168's results were known. It is used as the standard here (owner instruction), and the timing should be disclosed.
- The cutoff or bias fixes evaluated on the test rows. These were not adopted (E172).

**Technically incorrect implementation:**
- Map, LGU and alert outputs come from a model other than the approved one.
- Stale status texts.

**Reasonable but insufficiently validated:**
- HFIAS (survey-year labels) as the forecasting target.
- Survey-round folds instead of quarterly folds.
- National employment and remittance inputs.
- Deviation D3 in Tier 1.
- The FSSI construction.
- The 6-quarter survey publication lag.

**Valid and supported:**
- As-of survey gating (corruption test 0.0).
- Training-only nested selection.
- Monotone constraints.
- Same-row baseline comparison.
- Sealed ENNS 2022 forecasts.

## E. Required corrections (priority order)

1. **To satisfy objectives:**
   - Drive the map, LGU ranking and alerts from E168.
   - Deploy.
   - Run ISO/IEC 25010.
   - Implement the FNRI 2019/2023 comparison.
2. **For methodological validity:**
   - Disclose that the reliable lead (3 quarters) rests on 3 survey rounds and sits at the 75 % line.
   - Disclose non-contributing groups and FSSI weakness.
3. **For production reliability:**
   - Unify the feature path in `serve.py`.
   - Schedule quarterly regeneration of `live_2027.json`.
   - Remove the stale pending texts.
4. **Beneficial:**
   - Topic coherence and stability metrics.
   - An independent second annotator for the NLP label check.

## F. Reproducibility evidence (all run in this audit)

| What | How | Result |
|---|---|---|
| Metrics by lead | `python app/e168/thesis_metrics.py` | Output `data/e168/out/thesis_metrics.json` (pooled values used) |
| Baselines | scratchpad `baselines.py` | Reads `data/e151/out/prov_oof.csv`; output `baselines.json` |
| Ablation and controls | Read from `data/e168/out/results.json` | Produced by `python -m app.e168.lgbm_only eval` |
| NLP ablation | scratchpad `abl_nlp.py` | E168 procedure with news columns removed, Lead 1 |
| Live-forecast reproduction | `app.e168.serve._forecast(1)` | Re-ran the full training and selection at issue 2026-Q4. All 5 provinces reproduce `live_2027.json` exactly (score, P(HIGH), class), with the same selected configuration |
| API | FastAPI TestClient, thesis settings | `/final/food-insecurity/outlook` 200 (E168, 2027-Q1, all LOW); `/provinces`, `/forecast` 200 (CH1 price-pressure index, 2026-Q4); `/final/lgus` 200 (142, indicator priority); `/alerts` 200 (empty); `/explainability` 200 (CH1, "validation-pending" note) |
| Production | `curl https://aipheed-api.onrender.com/api/v1/...` | `/final/model-registry` 404; `/final/food-insecurity/outlook` 404; `/provinces` 200 (FIRI v2, 2027-Q1); frontend 200 |
| E172 cutoff check | `python -m app.e172.cutoff run/eval` | Lower accuracy than E168; not adopted |

**Not executed:** the series-by-series check of feature publication dates, and topic coherence and stability.
