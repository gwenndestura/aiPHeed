# E64 final report: completing Objectives 1–3 (2026-10-19)

**Branch:** `e62-final-audit` (local). E64 work is **uncommitted**. Nothing was pushed or deployed, and **E38 remains the production default**. The new candidate is served only with `AIPHEED_LEAD2_MODEL=e64`.

**Freeze records:**
- `PROTOCOL.md`: sha `2a37c236…`, frozen 10:18:41Z, before any E64 feature or score.
- `PROTOCOL_ADDENDUM_1.md`: sha `f0b59396…`, 10:26Z, before the feature table and candidates existed.
- Sealed candidates: `sealed/candidates.csv` (+ sha256).
- Prospective seal: `sealed/prospective_2027Q1.json` (+ sha256).

**Protected evidence:** E56–E62 unchanged (21/21 freeze records; git clean). E63 (lead-time study) ran in its own session and branch and is cited here.

## 0. Direct answers

| Question | Answer |
|---|---|
| **Is Objective 1 fully met, including integration of improved news?** | **Partially.** The improved pipeline (classifier v2, de-syndication, XLM-RoBERTa FSSI-v3, BERTopic, as-of features) is now in the backend. It feeds the served e64 model and its dashboard feed, and training/serving parity is tested. It is not *fully* met: relevance is validated only on AI annotations, BERTopic topics on titles are mostly geographic, and the corpus is retrospective and titles-only. |
| **Did improved news improve forecasting, or only classification?** | **Only classification is supported.** D (government + improved news) has the best 50-row Brier of the probability candidates (0.204 vs 0.212 government-only), but the difference is not supported: −0.008, CI [−0.029, +0.013], sign p = 0.75. At the 2027-Q1 origin the selected configuration uses **no** news input, so the served 2027-Q1 forecast equals E56's. |
| **Is the two-quarter-ahead forecast correctly implemented?** | **Yes.** Predictor quarter t, issue date = day 1 of t+1, target t+2 (2026-10-01 → 2027-Q1). Tested at every origin (`test_lead2_alignment`). News, CPI and SWS cutoffs are tested. |
| **Have several lead times been evaluated?** | **Yes (E63).** Leads 1–3 were evaluated; lead 4 cannot be computed under the cutoffs. **No lead meets the pre-registered reliability rule.** Skill falls with lead: Brier 0.130 / 0.214 / 0.251; accuracy 0.85 / 0.72 / 0.62. |
| **Does the best model meet 75% under a fair evaluation?** | **No** for probability forecasts: D 0.72 [0.56, 0.86]; the best, A and E, reach 0.74. Warning forms (decision on the price part) reach 0.78–0.80, but that is the accuracy of a warning rule, not of the probability. |
| **Does it beat the baselines, and is that supported?** | D beats persistence (ΔBrier −0.236 [−0.415, −0.056]), majority (−0.156 [−0.314, −0.007]) and province climatology (−0.089 [−0.180, −0.001]) on bootstrap CIs. **Not supported by the frozen rule**, which also requires a quarter sign test p < 0.05; the p-values are 0.11–0.34 with 10 quarters. Against climatology the CI includes 0. |
| **Are the 142 LGU rankings complete, reproducible and correctly described?** | Complete (142/142, identity checks pass), reproducible (identical hash), formula replicated exactly, now traceable to the province estimate and run. Described as relative prioritization, not municipal forecasts. **Open issue:** 4-dp rank ties at small province scores (W-E64-1). |
| **Are the results valid for the thesis claims?** | Valid for an **exploratory food-stress risk indicator** (regional SWS hunger and provincial food-price pressure) with development evidence. **Not** valid for a claim of validated provincial food-insecurity forecasting, or of a reliable horizon. |
| **What is still needed for prospective or expert validation?** | Score the sealed 2027-Q1 forecast (E64, E56) when the 2027-Q1 SWS round and March 2027 CPI are out. A provincial outcome (CBMS or provincial FIES). Human verification of the news annotations. Prospective news collection. The DA IV-A ISO/IEC 25010 evaluation and ranking survey. |
| **Production recommendation** | **Keep E38 as production.** e64 is an experimental, traceable candidate. It is not better than E56/E58 by any supported test. Do not switch without your decision. |

## 1. Objective 1: what was built and what news does

**Pipeline** (`backend/app/news/pipeline_v3.py`, `DATA_TO_DASHBOARD_FLOW.md`):

| Stage | Result |
|---|---|
| Corpus | 9,667 unique titles (E31 8,320 + E60 1,347), 2021-01-01..2026-10-14; PH date = GMT + 8 h; quarters checked |
| Classifier v2 (E60 freeze `327f9431…`, verified at load) | 697 relevant |
| De-syndication | 695 kept |
| Province-attributed | 296; the rest are national |
| XLM-RoBERTa-large-XNLI intensity | 225 new scores (`data/news_v3/scores.jsonl`); 5/5 stored E31 scores reproduced exactly |
| FSSI-v3 (115 province-quarters to 2026-Q3) | SUFFICIENT 20, LIMITED_SIGNAL 42, NO_USABLE_EVIDENCE 53. A value in 62 cells, against 23 for FSSI-v2. Never zero-filled; article keys per cell. |
| BERTopic (titles, multilingual MiniLM, fixed seeds) | 152 topics, 40% outliers. Interpretable food-stress clusters exist (rice farmers and programmes, food supply, habagat and typhoon events, flood-control funds), but most topics are place names. Descriptive only. |

**FSSI validity (descriptive, `r1_fssi_audit.json`):** Spearman with same-quarter food YoY 0.07, with PS 0.10, with regional hunger 0.09.
- FSSI is a news-tone index. **It is not shown to measure food insecurity.**
- Equation 2 inflates single-article cells (W-E64-3).

**Why news adds little forecast value** (`r2_news_diagnostics.json`):
1. **Coverage drift.** Admitted provincial articles by year: 2021: 11, 2022: 20, 2023: 32, 2024: 114, 2025: 46, 2026: 68. Training years are nearly empty (retrospective search index).
2. **Sparse features.** 34% of evaluation province-quarters have no admitted article. Trigger counts are zero in 56–88% of rows.
3. **Weak and redundant signals.** Only national employment news is associated with price pressure two quarters ahead (AUC 0.71, quarter-permutation p = 0.043, 1 of 10 features, so not significant after multiplicity). Outlet diversity duplicates coverage (ρ = 0.99), and climate tracks volume (ρ = 0.80).
4. **Timing.** The median article is 49 days old at the issue date, and the target is 4–6 months later.

**Live feed quality (W-E64-2):** 40 of 49 e64 feed items for 2026-Q3 are Climate, mostly weather bulletins naming a CALABARZON place.

## 2. Objective 2: rolling-origin evaluation (Lead-2, T43, 50 rows, 10 quarters, 18 HIGH)

Source: `tables/c2_model_comparison_50rows.csv`. CIs are a quarter-cluster bootstrap (4000 draws).

| Model | Correct | Accuracy [CI] | Balanced | HIGH recall / precision | LOW recall | F1 HIGH | Brier [CI] | Log loss | AUC | Calibration slope | Onsets | Quarters ≥ 0.75 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **E64-D (final)** | 36 | 0.72 [0.56, 0.86] | 0.684 | 0.556 / 0.625 | 0.812 | 0.588 | **0.204** [0.133, 0.293] | 0.596 | 0.660 | 0.62 | 3/10 | 5 |
| E64-A government only | 37 | 0.74 [0.60, 0.86] | 0.700 | 0.556 / 0.667 | 0.844 | 0.606 | 0.212 | 0.619 | 0.656 | 0.56 | 3/10 | 7 |
| E64-C + original news (= E56) | 36 | 0.72 | 0.684 | 0.556 / 0.625 | 0.812 | 0.588 | 0.214 | 0.623 | 0.649 | 0.55 | 3/10 | 6 |
| E64-E + news + history | 37 | 0.74 | 0.700 | 0.556 / 0.667 | 0.844 | 0.606 | 0.211 | 0.614 | 0.682 | 0.55 | 3/10 | 6 |
| E64-A-S stable selection | 34 | 0.68 | 0.665 | 0.611 / 0.550 | 0.719 | 0.579 | 0.219 | 0.623 | 0.679 | 0.59 | 3/10 | 5 |
| E64-D-S stable selection | 35 | 0.70 | 0.681 | 0.611 / 0.579 | 0.750 | 0.595 | 0.214 | 0.613 | 0.661 | 0.60 | 3/10 | 4 |
| E64-B improved news only | 19 | 0.38 | 0.443 | 0.667 / 0.324 | 0.219 | 0.436 | 0.507 | 2.240 | 0.443 | −0.06 | 4/10 | 1 |
| E56 (sealed reference) | 36 | 0.72 | 0.684 | 0.556 / 0.625 | 0.812 | 0.588 | 0.214 | 0.623 | 0.649 | 0.55 | 3/10 | 6 |
| Price projection only | 37 | 0.74 | 0.748 | 0.778 / 0.609 | 0.719 | 0.683 | 0.188 | 0.554 | 0.788 | 0.95 | 7/10 | 7 |
| Persistence | 28 | 0.56 | 0.535 | 0.444 / 0.400 | 0.625 | 0.421 | 0.440 | 6.08 | — | — | 0/10 | 3 |
| Majority as of the issue date | 32 | 0.64 | 0.500 | 0 / — | 1.000 | 0 | 0.360 | 4.97 | — | — | 0/10 | 5 |
| Climatology as of the issue date | 32 | 0.64 | 0.500 | 0 / — | 1.000 | 0 | 0.305 | 0.94 | — | — | 0/10 | 5 |
| *Warning forms (decision on the price part)* | | | | | | | | | | | | |
| E58-EW | 39 | 0.78 | 0.780 | 0.778 / 0.667 | 0.781 | 0.718 | 0.182 | 0.562 | 0.786 | 0.75 | 7/10 | 7 |
| E64-D warning | 39 | 0.78 | 0.780 | 0.778 / 0.667 | 0.781 | 0.718 | 0.172 | 0.539 | 0.793 | 0.81 | 7/10 | 6 |

**Confusion matrix and calibration bins:** `out/c2_score.json`, `tables/c2_reliability.csv`.

**By quarter:** D accuracy ranges from 0.2 (2024-Q2, the stale-hunger quarter) to 1.0 (2025-Q1, 2025-Q4, 2026-Q1).

**By province:** Batangas 9/10, Rizal 9/10, Quezon 8/10, Laguna 6/10, Cavite 4/10.

**TEST quarters** (20 rows, 1 HIGH; uninformative about HIGH detection): D 0.85, E56 0.90, majority 0.95.

**Frozen claims** (`out/c2_score.json`):

| Claim | Result | Verdict |
|---|---|---|
| Improved news helps (D vs A) | ΔBrier −0.008 [−0.029, +0.013]; quarters 6 better, 4 worse; p = 0.75 | **not supported** |
| Improved news helps (D-S vs A-S) | −0.005 [−0.021, +0.013] | **not supported** |
| Original news (C vs A) | +0.002 | no value. The E40 news inputs were never split on. |
| Stable selection | Switches cut from 9 to 2 (D-S). Mean \|ΔP\| between origins 0.223 → 0.208 (D) and 0.201 → 0.191 (A). Brier +0.010 [−0.007, +0.030]. | Meets the protocol's letter (fewer jumps, Brier not significantly worse), but the reduction is small and Brier is a little worse. **Not adopted.** |
| Final (D) vs E56 | −0.010 [−0.032, +0.013] | **not supported** |
| Hunger component | Served ridge Brier 0.204 vs random walk 0.192 (on D) | Component result only (E61 recommendation stands). Not part of the selection. |

**Lead times (E63):** see §0. The served horizon remains Lead-2, unchanged.

**Target** (`r4_targets.py`, descriptive, never used for selection):

| Target | HIGH on 50 rows | Note |
|---|---|---|
| T43 (served) | 18 | — |
| T43-F (food condition only) | 5 | — |
| T43-HL (headline condition added) | 25 | marks 2026-Q2 and Q3 HIGH in 4 provinces each |

So whether 2026–27 reads as "low" depends on the gap rule (E62 W1). That is an adviser decision. The served target is unchanged, and no provincial hunger label was built.

## 3. Objective 3: LGU rankings (`out/r3_lgu_audit.json`)

| Check | Result |
|---|---|
| Completeness and identity | 142/142 LGUs; per-province counts 23/30/34/41/14; PSGC prefixes, names, populations and areas consistent; one province substitute (Lucena) disclosed |
| Formula | vulnerability = 0.6 × min-max(poverty) + 0.4 × min-max(density) within province; index = province estimate × vulnerability (4 dp). Replica difference 0.0. |
| Reproducibility | Identical `rows_sha256` (`fe77da4f…`) on rebuild; API identical on repeat calls (test) |
| Drivers within province | Poverty dominates: Spearman 0.70–0.91 (Laguna 0.39). Density second. Population size weak (−0.18 to 0.40). |
| Weight sensitivity | 50/50 and 70/30 keep the order: Spearman ≥ 0.92, top-5 overlap about 4.2 of 5. Poverty-only or density-only orders differ widely. Rank normalisation: Spearman ≥ 0.75. |
| Stability | Within-province order is fixed by construction (the forecast only rescales). The region-wide order moves with the province estimates (Spearman 0.26–0.98 between consecutive quarters). |
| Traceability (new) | Every row carries the province estimate, its source run, the vulnerability index, the formula and the ranking hash (test) |
| Independent municipal outcomes | **None exist.** SAE 2021 poverty is an input, so it cannot validate the ranking. |
| Open | 4-dp rank ties (W-E64-1). Your decision is needed to rank on the unrounded index. |

## 4. Feature audit: what the served candidate actually uses

Source: `tables/c3_feature_use.csv`, split counts over 12 origins.

| Group | Features used | Splits |
|---|---|---|
| Improved news (national) | `n3_nat_employment_rw`, `n3_nat_ofw_remittance_rw`, `n3_nat_market_rw` | 189, 104, 36 |
| FSSI-v3 | `n3_fssi` | 65 |
| Improved news (provincial triggers) | fish kill, climate | 1 each |
| Prices | `rice_whsl_yoy` 97, `F_hat_M1` 94, `gap_now` 60, `F_now` 48, `D_now` 24 | — |
| Remittances, employment | `remit_php_yoy` 50, `ur_yoy` 45 | — |
| Climate and production | typhoon lag 49, palay 43, corn 25, ENSO × momentum 31 | — |

**At the 2027-Q1 origin, configuration 23 uses no news column.**

The original E40 news shares are never used by any candidate.

## 5. Original vs final candidate, same rows

| Measure | E56 | D | Difference |
|---|---|---|---|
| Brier | 0.214 | 0.204 | not supported (CI [−0.032, +0.013]) |
| Accuracy | 0.72 | 0.72 | the decisions differ in **6 rows**, 3 for each model (below) |
| 2027-Q1 forecasts | 0.109 / 0.070 / 0.146 / 0.050 / 0.043 | identical | — |

**Where D's and E56's decisions differ:**

| Better model | Rows |
|---|---|
| D | 2025-Q1 Batangas (HIGH caught); 2025-Q3 Cavite and Batangas (false alarms avoided) |
| E56 | 2025-Q2 Rizal and 2026-Q3 Cavite (D false alarms); 2025-Q3 Laguna (D misses a HIGH) |

The 2026-Q4 forecasts differ (D 0.02–0.44, E56 0.005–0.29).

## 6. Lead-2 production evidence

| Item | Evidence |
|---|---|
| Record | `backend/data/e64/e64_record.json` (content sha checked at load). Origin 2026-10-01, predictor 2026-Q3, target 2027-Q1, lead 2. |
| Reproduction | Every refit reproduces the sealed probability within 1e-9 (assertion in the builder). |
| Attribution | Adds up within 2e-3 (test). |
| News behind each forecast | Stored with IDs, all published before the issue date (test). |
| Prospective seal | `sealed/prospective_2027Q1.json`: inputs, outputs, components, contributions, news IDs. To be scored, never edited. |
| API equals record (`out/r6_api_consistency_e64.json`) | provinces, region mean, series, explanations, sufficiency. The remaining FAIL lines are the documented non-defects (clock fields, genuine 4-dp ties, a check that expected unrounded figures in the sentence). |
| Live dashboard (local e64 stack, ports 8064/8094) | region 0.08 LOW, two-part "model score" sentence, classifier-v2 feed (49 items, latest 2026-09-27), approved layout unchanged |

## 7. Tests and build

| Suite | Before E64 (57e663f) | After E64 |
|---|---|---|
| Backend pytest (all) | 423 passed, 18 skipped | **447 passed, 18 skipped**. The 3 warnings are scikit-learn unpickle warnings on the legacy report model (E62 W9). |
| New: `test_e64_news_pipeline.py` | — | 14 passed |
| New: `test_e64_record.py` | — | 10 passed |
| Frontend vitest | 46 passed | 46 passed (frontend unchanged) |
| `tsc --noEmit` | 6 errors, all in `src/data/mockData.ts` | same (pre-existing) |
| Production build | passes | passes |

## 8. Files changed (all uncommitted)

**Backend code:**
- `app/news/classifier_v2.py` (new; byte-identical E60 freeze);
- `app/news/pipeline_v3.py` (new);
- `app/news/scoring.py` (D-E64-1);
- `app/services/dashboard.py` (e64 feed pool, feed note, record-specific back-test count, LGU traceability fields, e64 event wording);
- `app/ml/inference/e41_lead2.py` (e64 mode);
- `app/ml/inference/e31_engine.py` (LGU traceability);
- `app/api/v1/insights.py` (e64 explainability note);
- `app/schemas/public.py` (LGU fields).

**Scripts:**
- `scripts/score_news_v3.py`, `scripts/fit_topics_v3.py`, `scripts/build_record_e64.py`.

**Tests:**
- `tests/integration/test_e64_news_pipeline.py`, `tests/integration/test_e64_record.py`.

**Data:**
- `data/news_e60/articles.jsonl` (copy of the E60 store, sha `cbf28149…`);
- `data/news_v3/*` (scores, topics);
- `data/e64/*` (record, model artifacts).
- `models/bertopic_v3` is git-ignored.

**Other:**
- `.claude/launch.json`: `aipheed-e64-stack` entry.
- This experiment folder.

**Mixed with another session's uncommitted work:**
- `e41_lead2.py` and `insights.py` also carry the E46 D-1 hunks of another session. A commit would need to separate them, as was done for E61.

**Deployment:** none. E38 is the default. The deployed configuration (Render/Vercel) was not checked; no URL is available here.

## 9. Remaining blockers

1. **Validation.** No provincial food-insecurity outcome exists. Score the 2027-Q1 seals when outcomes are published.
2. **Target.** The gap rule treats non-food inflation as relief (adviser decision; prospective only).
3. **News.** The corpus is retrospective and titles-only, and its coverage drifts. It needs prospective collection with timestamps, lead text (needs your OK for token resolution), and human-verified annotations.
4. **Reliability rule.** It is unmet at every lead with 9–12 quarters. More quarters are needed.
5. **LGU rank ties** (W-E64-1) and the ranking-weights justification: adviser decision.
6. **The DA IV-A ISO/IEC 25010 evaluation and ranking survey** (H4, H5).
