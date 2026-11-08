# aiPHeed: consolidated report against the Master Directive (2026-11-03)

Branch `pfi/survey-anchored-final` (head `21e3ec7b`). Every number below comes from a locked, already executed study
in this repository. The evidence path is cited with each table. No model was retrained or re-tuned for this report.

> **Final deployment decision: NOT APPROVED. Nothing is integrated into the dashboard.**
>
> Gates 1, 3, 4 and 6 fail. Gate 5 passes only in part. The failure is not caused by a missing component. All the
> components the directive lists exist and were run: LightGBM, walk-forward evaluation, four baselines, XLM-R +
> BERTopic FSSI, five groups, SHAP, and the 142-LGU ranking.
>
> The binding cause is that **no repeated food-insecurity measurement exists at province level**. The public record
> has HFIAS once (2015, all five provinces), ENNS 2018/2019 for a few IV-A provinces, and regional FIES (2023).
> Without a repeated provincial outcome, a provincial HIGH/LOW forecast cannot be trained, validated or tested.
> Every quarterly provincial label that could be built would be one of three things:
> * a price index, which the directive forbids;
> * the regional hunger series copied into each province, which the directive also forbids;
> * an interpolated or invented series ("never manufacture ground truth").

---

## 1. Selected methodology and justification

The design that the data can support, built in FI5 (`app/fi5`, `docs/fi5/`) and refined in FI6–FI9:

* **Outcome.** A measured, experience-based food-insecurity outcome, used at the level where it is actually measured.
* **Inputs.** Driver groups, each of which carries its own news features.
* **Model.** One regularised LightGBM per lead.
* **Evaluation.** Expanding-window walk-forward, with release-date (as-of) alignment.
* **Comparison.** Every candidate against persistence and the other three required baselines, on the same origins.

This follows FEWS NET/GIEWS practice (anomaly against the five-year norm), Westerveld et al. 2021 (every lead under
one rule, compared with persistence) and Balashankar et al. 2023 (news inside driver domains). The verified references,
including the 2021–2026 forecasting studies, are in `docs/fi5/RESEARCH_EVIDENCE.md` (16 DOIs checked on Crossref)
and `docs/release/RESEARCH_EVIDENCE_REGISTER.md` (9 DOIs; one wrong DOI was removed).

**Rejected alternatives and why.**

| Alternative | Why rejected |
|---|---|
| Price-pressure label (CH1/P0H4, PS, T43c) | It is a price target. Its high accuracies (0.84–0.91) belong to evidence class B (proxy), not to food insecurity (`docs/audit/FORENSIC_MODEL_AUDIT_20261103.md`). |
| Survey-anchored provincial FIES (PFI v1.0) | Gate REJECTED. No provincial FIES series exists for chronological testing. Calibration error 0.18 (limit 0.10). |
| Provincial HFIAS panel (hfias-1.0) | Gate REJECTED. Ridge MAE 10.4 vs 7.9 for no-change (below). |
| SWS hunger copied into each province | This is one regional prediction given to all five provinces, which the directive forbids. |

## 2. FAO framework and operationalisation

| FAO dimension | Quarterly proxies available | Group | Coverage limit |
|---|---|---|---|
| Availability | Palay production YoY (PSA), typhoon exposure ≤200 km (IBTrACS), rainfall z and Tmax anomaly (NASA POWER, 5 province centroids), ENSO | Climate and agricultural stress | Palay is regional |
| Access | Food/rice CPI YoY and food minus all-items (PSA); unemployment (LFS); remittances (BSP via WDI); poverty incidence (PSA) | Market; Employment/purchasing capacity; Poverty | LFS and remittances are national; poverty is a survey-year value |
| Utilization | None | — | **Not covered.** No quarterly nutrition or WASH series exists. This is stated, not claimed. |
| Stability | Anomaly and volatility features of all the above; news FSSI | All groups | — |

The outcome measures food-insecurity *experience* (SWS involuntary hunger, the severe end of the FIES scale). It is
not PoU, poverty or prices. The model output is a **risk estimate**, not a measurement of food insecurity.

## 3. Data sources and data-quality findings

* **Sources and coverage.** 20 files, each with sha256 and origin, listed in `backend/data/fi5/raw/MANIFEST.csv`.
  Coverage per series and the release rules are in `docs/fi5/FINAL_REPORT.md` §D and `app/fi5/sources.py`:
  * SWS 1998–2026;
  * CPI 1994+;
  * palay 1987+;
  * NASA POWER 1981+;
  * IBTrACS;
  * LFS 2005+ (one definition only);
  * poverty 2006–2025, with the methodology break 2015→2018 disclosed.
* **Timing.** Reference period, publication date and issue date are separated in code. As-of tests are in
  `tests/unit/test_fi5.py`.
* **Leakage.**
  * Label permutation (20 shuffles) gives out-of-sample AUC 0.498 (Lead 1) and 0.470 (Lead 2), so the harness does
    not leak.
  * The E122 cutoff audit passed with warnings: 30 of 34 publication dates are provisional (`docs/` E122 record).
* **Corpus issues.**
  * The FI5 news corpus is headlines only, Google News, collected retrospectively in October 2026, and volume grows
    from 193 to 882 articles per quarter.
  * The FI6-N archive is 95 % from one outlet (Rappler).
* **Data errors found.** The owner workbook's ENNS "moderate-to-severe" values are FNRI's HFIAS *moderate*
  category, a mislabel (`docs/hfias/METHODOLOGY_AND_RESULTS.md`). HFIAS and FIES are never pooled.

## 4. Target construction and validation

| Role | Data | Status |
|---|---|---|
| Training / walk-forward label | SWS involuntary hunger, Balance Luzon, HIGH = above the mean of the preceding 20 quarters (≥8 readings). 98 labelled quarters, 51 % HIGH. | Regional, not provincial |
| Provincial validation labels | FNRI 2015 HFIAS (5 provinces, once); ENNS 2018/2019 (national 52-province panel); PSA subsistence incidence 2015/18/21/23 (poverty, used as a reference only) | Survey years only |
| Independent test | Sealed forecasts 2026-Q4 to 2027-Q3 (FI5 seal `350ffe4f…`), to be scored when SWS publishes | Not yet observable |
| External face validity | FNRI NNS CALABARZON 2019/2023, PSA FIES IV-A 2023 = 19.1 % (CI 17.0–21.1) | Anchor only, never a quarterly label |

**Label-noise finding (root cause of the regional failure).** 74 % of evaluated quarters (46 of 62) differ from the
five-year average by less than SWS's margin of error (±4–6 pp, n ≈ 300 per area). Most HIGH/LOW labels are sampling
noise. The best achievable accuracy is estimated at 0.58–0.64 (`memory: FINAL FI LightGBM`).

**Provincial label finding.** FNRI 2015 provinces cannot be told apart statistically (Cochran Q p = 0.46). The PSA
subsistence ordering is unstable between rounds (2021 vs 2023, Spearman ρ = −0.70). Only Quezon is significantly
above the region in both 2018 and 2021 (`docs/fi12/`).

## 5. LightGBM architecture and features

* **Features.** 32 features (`app/fi5/features.py`) in five domains: market, climate, employment, remittance and
  poverty, plus outcome history. News is inside each domain.
* **Model.** One LightGBM per lead. The configuration is selected inside each training window from
  {stumps, small, medium}; the most constrained one (stumps) is chosen most often.
* **Validation.** Expanding window. Training starts in 1998; evaluated targets run from 2010-Q1 on (62 origins per
  lead).

## 6. NLP and FSSI

* **Sentiment.** XLM-RoBERTa zero-shot (`joeddav/xlm-roberta-large-xnli`, Filipino + English).
  * Hypothesis set hash `aa356c2831ac`.
  * 3,794 of 9,628 headlines pass the relevance gate.
  * Evidence types are separated: risk factor 626, background 291, government response 202, actual hunger report 28.
    So a negative article is not automatically counted as food insecurity.
* **Topics.** BERTopic fitted on 2021–22 only and then frozen: 11 topics (typhoon, flooding, rice/farmers,
  inflation, fishing livelihoods, ayuda/DSWD, …).
* **FSSI bias correction.**
  * each event counted once;
  * outlet weight 1/√n;
  * share of all collected events;
  * province cells shrunk toward the region (k = 10);
  * z-scores computed from past quarters only.
* **Limits.** No human-labelled validation set exists. The 200-article annotation kit is excluded by owner rule.

**Three-way comparison required by §7 of the directive.**

| Variant | Harness | Lead 1 result | Source |
|---|---|---|---|
| LightGBM without NLP | FI6-N government-only | acc 0.839, HIGH recall 0.273, AUC 0.702, Brier 0.129 | `docs/fi9n/NEWS_VALUE_REASSESSMENT.md` |
| LightGBM + existing NLP (FI5 Google News corpus) | FI5 ablation | Brier change from removing news: 0.000 / 0.000 / +0.004 / 0.000 at Leads 1–4, i.e. **no gain** | `docs/fi5/RESULTS.md` |
| LightGBM + improved NLP (FI6-N publisher archive, 2012+) | FI6-N | acc 0.839, recall 0.273, AUC 0.765, Brier 0.119; **Brier −0.0099 [−0.0211, −0.0016]** vs no NLP; recall unchanged; McNemar p = 1.00 | same |
| Naive persistence (reference) | FI6-N | acc 0.871, recall 0.545, AUC 0.743, Brier 0.116 | same |

**Verdict.**
* The improved news gives a small, statistically supported probability gain at Lead 1 only, and none at Lead 2 (Brier
  −0.0013 [−0.0051, +0.0023]).
* It does not improve classification, and it does not beat persistence.
* The existing and improved variants were scored in two harnesses (FI5 and FI6). They were never compared inside one
  harness.

## 7. Performance by lead (FI5 LightGBM, walk-forward, 62 origins per lead, 28 HIGH / 34 LOW)

| Lead | Acc | Prec | Rec | F1 | Bal. acc | AUC | Brier | BSS | TP / FP / TN / FN |
|---|---|---|---|---|---|---|---|---|---|
| 0 | not separately evaluated (see §11) | | | | | | | | |
| 1 | 0.532 | 0.483 | 0.500 | 0.491 | 0.529 | 0.483 | 0.309 | −0.170 | 14 / 15 / 19 / 14 |
| 2 | 0.548 | 0.500 | 0.357 | 0.417 | 0.532 | 0.540 | 0.287 | −0.078 | 10 / 10 / 24 / 18 |
| 3 | 0.597 | 0.571 | 0.429 | 0.490 | 0.582 | 0.579 | 0.264 | +0.015 | 12 / 9 / 25 / 16 |
| 4 | 0.565 | 0.514 | 0.679 | 0.585 | 0.575 | 0.529 | 0.292 | −0.079 | 19 / 18 / 16 / 9 |

* **Train vs test.** In-sample accuracy is 0.87–0.93; out-of-sample is 0.53–0.60.
* **Stability across eras.** Accuracy in 2021–26 is 0.35–0.60, against 0.56–0.78 in 2016–20.

## 8. Baselines (same origins, same target)

| Lead | LightGBM acc / Brier | Persistence | PSA-only | NLP-only | Logistic |
|---|---|---|---|---|---|
| 1 | 0.532 / 0.309 | **0.677** / 0.323 | 0.532 / 0.300 | 0.516 / 0.262 | 0.597 / **0.254** |
| 2 | 0.548 / 0.287 | 0.629 / 0.371 | 0.581 / 0.286 | 0.500 / 0.260 | **0.661 / 0.230** |
| 3 | 0.597 / 0.264 | **0.613** / 0.387 | 0.565 / 0.280 | 0.452 / 0.272 | 0.597 / 0.274 |
| 4 | 0.565 / 0.292 | 0.565 / 0.435 | 0.516 / 0.297 | 0.419 / 0.268 | 0.484 / 0.350 |

* LightGBM does **not** beat all four baselines at any lead. No McNemar test favours it.
* Its Brier win over persistence at Leads 3–4 comes only from persistence's 0/1 probabilities. Its accuracy at those
  leads is equal or lower.
* **Sudden transitions.** On the 16 clearly non-noise quarters, persistence scores 0.56–0.69 and LightGBM
  0.38–0.56.
* **Release-aware harness (FI9-Z).** The production candidate catches only 6 of 11 HIGH quarters (recall 0.55, fails
  ≥ 0.60). Cost-sensitive persistence meets every class rule but is not significantly better than naive persistence
  (balanced accuracy +0.018, CI −0.06 to +0.11).

## 9. Overfitting, bias, leakage and generalisation audit

| Check | Result |
|---|---|
| Train–test gap | 0.87–0.93 vs 0.53–0.60: **overfits noise** |
| Label permutation | AUC 0.498 / 0.470: no leakage, and the model is no better than shuffled labels |
| Geographic transfer (to the other SWS areas, Lead 1) | NCR 0.548 vs that area's persistence 0.661; Visayas 0.597 vs 0.710; Mindanao 0.532 vs 0.710 |
| Spurious association | The record-low 2025 poverty rate raises predicted risk, a regime artefact of 2021–26 |
| Provincial generalisation (hfias-1.0, 52 provinces nationally, test 2019 scored once) | Lead 1 ridge MAE 10.37 vs no-change 7.87; acc 0.67; ECE 0.22; no lead passes |
| Served model, provincial independence | The dashboard engine (CH1/P0H4) gives the identical 0.9521 to Cavite, Laguna, Rizal and Quezon for 2027-Q1. That is effectively one regional value. |

## 10. Five contributor groups

* **FI5 LightGBM.** Importance is **not** concentrated. Sum of mean |SHAP| at Lead 1:
  * climate 0.478;
  * market 0.461;
  * poverty 0.263;
  * employment 0.238;
  * outcome history 0.222;
  * remittance 0.111.
* **FI5 ablations.** Removing any single domain changes Brier by −0.031 to +0.024, with no consistent sign. No group
  gives a stable gain, so none of the shares is evidence of skill.
* **Served dashboard (measured today through `GET /api/v1/explainability`).**
  * For every province, "Market / Prices" is 100 % and climate, fish kill and employment are 0 % with status
    `no_model_input`. OFW remittance is `no_data`.
  * **Cause.** The served model has price inputs only. This is a model-structure fact, not a SHAP error, so it must
    not be "rebalanced" by adjusting attributions.
  * Its groups also differ from the directive's five: poverty and news are not separate groups.
  * This is the contributor-dominance defect named in §8 of the directive. It is resolved only by serving a
    gate-approved multi-group model, and none exists.

## 11. Maximum reliable lead time

* **Rule (locked before evaluation).** All of the following must hold:
  * accuracy ≥ 0.75;
  * recall ≥ 0.50 and precision ≥ 0.50;
  * AUC ≥ 0.70;
  * Brier skill > 0;
  * accuracy ≥ 0.60 in every era.
* **Results.**
  * Leads 1–4 fail.
  * The FI9-Z class rule also fails at every lead.
  * The provincial HFIAS study fails at every lead.
* **Lead 0** was not evaluated as its own horizon. After the SWS mid-quarter release (20 of 23 quarters), the
  current quarter is an observation, not a forecast. Before the release, no evaluated horizon passed.
* **Maximum validated reliable lead: none.**
* The dashboard must not display a validated lead. The public route
  `/api/v1/final/food-insecurity/outlook` already returns `status: validation_pending`.

## 12. Provincial forecasting results

* **No provincial food-insecurity forecast is validated.**
* FI12 matched every model family against measured provincial labels:
  * P0H4 Lead 1 against PSA 2023: ρ = 0.55, p = 0.17, n = 5.
  * FI10 price forecasts rank provinces **opposite** to food poverty (pooled ρ = −0.43).
* **The only survey-supported provincial distinction is Quezon.** It sits highest in HFIAS 2015 and in subsistence
  2015/18/21/23, and is significantly above the region in 2018 and 2021. This is a structural, survey-year
  vulnerability statement, not a quarterly forecast.

## 13. Municipal disaggregation

* **Coverage and inputs.** All 142 LGUs are present, with correct provincial assignment: Batangas 34, Cavite 23,
  Laguna 30, Quezon 41, Rizal 14. Inputs are PSA SAE 2021 poverty (Lucena from the PSA HUC table) and POPCEN 2024
  density.
* **Reproduction.** The ranking was reproduced independently (max difference 7e-15) (`backend/data/fi5/out/lgu_rankings.csv`).
* **Not a forecast disaggregation.** The directive requires disaggregating *validated provincial forecasts*, and
  none exists. So the ranking is a **vulnerability priority**, not a forecast.
* **Weights.** The ½ poverty / ½ density weights are a DA policy choice. Changing them moves 11–24 LGUs in or out of
  the top third.

## 14. SHAP explanations

* **Implementation.** Explanations are generated from per-row SHAP and actual feature values (`app/fi5/explain.py`),
  in one or two plain sentences. A group with negligible contribution is shown as `no_model_input` or
  `not influential`, never as a driver.
* **What is served today.** The served dashboard text comes from the legacy CH1 engine and describes a price-pressure
  index. Its labels were corrected to say so on 11-03.

## 15. Backend tests and acceptance gates

**Tests run 2026-11-03.** `python -m pytest tests/unit` (backend venv). The result is recorded in §15a below.

| Gate | Status | Evidence |
|---|---|---|
| 1 Methodology | **FAIL** | Passed: LightGBM, FI outcome (not price), FAO mapping with utilization declared absent. Failed: provincial forecasting has no valid provincial target. |
| 2 Data quality | **PASS WITH WARNINGS** | Manifest, as-of rules, permutation test, E122 audit. Warnings: 30/34 publication dates provisional; corpus collected retrospectively. |
| 3 Predictive performance | **FAIL** | Does not beat persistence or logistic regression; no McNemar win; unstable across eras. |
| 4 Generalisation and reliability | **FAIL** | Train/test gap 0.3+; geographic transfer below persistence; max reliable lead none. |
| 5 NLP | **PARTIAL** | XLM-R + BERTopic + FSSI implemented. Improved news: Brier gain at Lead 1 only (−0.0099), no classification gain, and the three-way comparison spans two harnesses. |
| 6 Spatial and explainability | **FAIL** | No independent validated provincial forecasts. The served model gives 4/5 provinces the same score and Market = 100 %. LGU list is a vulnerability priority only. |
| 7 Backend integrity | **PASS** (818 tests) | Public FI route answers `validation_pending`; registry: `production: null`, pfi-1.0 and hfias-1.0 rejected, ch1-p0h4 `legacy_incumbent`. |

### 15a. Test result

* `python -m pytest tests/unit -q -x` (venv `C:\Users\admin\aipheed\backend\venv`): **818 passed**, 6 warnings, 0 failed
  (4 min 8 s).
* Live checks through `TestClient(app.main.app)`:
  * `/api/v1/final/food-insecurity/outlook`: 200 with `status: validation_pending` and `forecast: null`;
  * `/api/v1/final/model-registry`: `production: null`;
  * `/api/v1/explainability?scope=province&id=<province>`: 200 for all five provinces.
* **Gate 7: PASS.**
  * The suite is green.
  * Outputs are reproducible from their locks.
  * No unvalidated food-insecurity forecast is presented as validated.
  * The legacy CH1 price-pressure map is labelled as a price-pressure index.

## 16. Files modified in this session

* `docs/release/MASTER_DIRECTIVE_REPORT_20261103.md` (this report, new).
* No code, model, data, registry or frontend file was changed.

## 17. Final deployment decision

* **Not approved for dashboard integration.**
* No model is promoted. `registry.json` keeps `production: null`.
* The public food-insecurity route stays `validation_pending`.
* **What would make Gates 1, 3, 4 and 6 evaluable.** A repeated provincial food-insecurity measurement (at least 4
  waves for CALABARZON's provinces), for example:
  * the FNRI ENNS/NNS household public-use files (the site is blocked from this network);
  * PSA's 2026 FIES (expected 2027).
* The sealed FI5 forecasts for 2026-Q4 to 2027-Q3 become the first clean regional test when SWS publishes those
  quarters.
* **Open owner decision.** The current map and left panel still run the legacy CH1/P0H4 price-pressure engine, which
  shows the 100 % market contribution and near-identical provincial scores described above. It has never passed the
  gate. Keeping it, with its corrected price-pressure labels, or withdrawing it changes the approved dashboard, so it
  is the owner's call.
