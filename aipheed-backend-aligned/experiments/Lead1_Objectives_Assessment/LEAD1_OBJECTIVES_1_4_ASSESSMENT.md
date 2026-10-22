# Lead-1 Assessment of aiPHeed Against Specific Objectives 1–4 of Chapter I

**Scope.** This report covers Specific Objectives 1–4 only, for Lead 1. Objective 5 (dashboard deployment, ISO/IEC 25010
evaluation, DA evaluators, FNRI anchors) is excluded.

**Objective wording.** Taken from Chapter I §1.5.2 of `THESIS 2 (11).pdf` (13 October 2026, the latest version in the
researchers' files; SHA-256 prefix 88dd0b62). The extract is in `chapter1_1_5_2_extract.txt`. Chapter I is not
modified.

**Evidence.**
- Verified on 2026-10-21 against the committed E83 final run
  (`aipheed-backend-aligned/experiments/E83_Deep_Reconstruction/runs/20261021T084802Z/`) and the served data.
- Every figure below was recomputed from those files for this report.

### Definitions used throughout

**Lead 1.** A forecast issued on the first day of quarter t+1 for quarter t+1 itself: the quarter in which it is
issued, about one to three months before that quarter ends. It is therefore a near-term forecast or nowcast, not a
two-quarter-ahead forecast.

**Target (T43).** HIGH when Balance Luzon SWS involuntary hunger is above 11.3% **and** the province's food CPI
year-on-year (or food minus headline) is above that province's 2021–22 60th percentile. It is a **constructed proxy**.
Since 2023-Q4, hunger exceeded 11.3% in every evaluated quarter, so T43 was identical to the provincial food-price
condition on 100% of those rows (E83 `T43_VALIDITY_AUDIT.md`). Lead-1 accuracy on T43 is therefore **proxy-target
accuracy**, not demonstrated accuracy in predicting household food insecurity.

**Evaluation set.**
- 13 target quarters (2023-Q1..2026-Q3) × 5 provinces = 65 Lead-1 forecasts; 16 HIGH (24.6%).
- Walk-forward expanding-window validation: each forecast is trained only on labels published before its issue date,
  and every input is cut by its publication date.

**Models.**
- **"LightGBM"** below is the proposed combined model (`M-GB-ALL`): constrained LightGBM on news plus government
  indicators.
- **S-SIM** is a structural simulation added in E83. It is *not* LightGBM.

---

## Objective 1 — NLP pipeline, FSSI and latent patterns

**Objective (Chapter I).** "To design a two-tier pipeline combining zero-shot XLM-RoBERTa Filipino-English sentiment
extraction and BERTopic unsupervised topic modeling to produce the bias-corrected Food Stress Sentiment Index and latent
food insecurity risk patterns per province-quarter from a Filipino-English news corpus."

**Answer.** The pipeline was designed, implemented and run, and it produces both outputs. The outputs are sparse, and
they do not improve the Lead-1 forecast.

**Evidence (verified).**

- **Corpus.** 9,667 unique news records, 2021-01-01 .. 2026-10-14 (`backend/data/news_e31/`, `news_e60/`).
  - Collected through English and Filipino query banks. Filipino-language queries account for 212 records.
  - Titles only for most records. Lawful lead text was recovered for 730 records; the rest are blocked or disallowed
    by publishers (E83 `LEAD_TEXT_REPORT.md`).
- **Tier 1: relevance and driver tagging.** Classifier v2 (`backend/app/news/classifier_v2.py`) admits 697 relevant
  records, 695 after syndication de-duplication (`app/news/pipeline_v3.py`).
- **Tier 2: zero-shot XLM-RoBERTa intensity.** `joeddav/xlm-roberta-large-xnli`. 3,199 stored scores; every
  province-attributed admitted article (296) is scored (`data/news_e31/scores.jsonl`, `data/news_v3/scores.jsonl`).
- **Bias-corrected FSSI (FSSI-v3).** Coverage bias weight log(1 + median n) / log(1 + n) (`pipeline_v3.fssi_v3`).
  - Of 120 province-quarters: **20 SUFFICIENT** (at least 5 articles), 45 limited signal, 55 no usable evidence.
- **BERTopic latent patterns** (`data/news_v3/topic_info.csv`, `topics_manifest.json`):
  - 152 topics plus an outlier topic (39.7% of titles), 120 province-quarter topic rows;
  - multilingual MiniLM embeddings;
  - manifest label: "descriptive latent patterns; not a forecast feature". E75 found many topics are place names
    (48/152) and weak coherence.
- **Forecasting usefulness at Lead 1** (E83 ablation, identical rows):

  | Model on 30 rows | Accuracy | Brier |
  |---|---|---|
  | LightGBM without news | 0.867 | 0.076 |
  | LightGBM with news | 0.867 | 0.086 |

  The NLP-only baseline scores 0.167. No news representation gave a significant gain: lead text, event clusters
  (E83), GDELT (E85).

**Status: Partially Achieved.**

**Justification.**
- The two-tier pipeline, FSSI-v3 and BERTopic patterns exist, are reproducible and are tested.
- FSSI is supported in only 17% of province-quarters.
- The corpus is mostly English titles, collected retrospectively.
- The outputs carry no demonstrated forecasting value. They are descriptive warning signals, not validated predictors.

**Sources.**
- Code: `backend/app/news/classifier_v2.py`, `pipeline_v3.py`, `events.py`, `lead_extractor.py`.
- Data and reports: `data/news_v3/`, E83 `REPORT.md` §4, E85 `REPORT.md`.

---

## Objective 2 — LightGBM performance and the reliable forecast horizon (Lead 1)

**Objective (Chapter I).** To evaluate the proposed LightGBM model using:
1. Accuracy;
2. Precision and Recall;
3. F1-Score;
4. AUC-ROC;
5. forecast performance across lead times via walk-forward expanding-window cross-validation, to determine the
   furthest horizon at which reliable forecasting is achievable.

**Answer.** The proposed LightGBM performs well on the forecasts it can issue, but it can issue only 30 of the 65
Lead-1 forecasts. Its walk-forward evidence does not establish a reliable horizon.

**Verified Lead-1 metrics, proposed LightGBM** (`M-GB-ALL`, E83 run 20261021T084802Z):

| Evaluation | n | Correct | Accuracy | Precision | Recall (HIGH) | F1 | AUC-ROC | Balanced acc. | Brier |
|---|---|---|---|---|---|---|---|---|---|
| Rows it issued (targets 2024-Q4..2026-Q3, 6 quarters, 8 HIGH) | 30 | 26 | **0.867** | 0.667 | **1.00** (8/8) | 0.800 | 0.955 | 0.909 | 0.086 |
| All 65 rows, unissued counted as wrong (pre-registered rule) | 65 | 26 | 0.400 | 0.205 | 0.50 | 0.291 | — | 0.434 | 0.578 |

**Why 35 rows are unissued.** The walk-forward rule requires at least 6 labelled quarters and at least 5 HIGH labels
before training. T43 had only two HIGH quarters before 2023-Q4, so LightGBM could first be trained for target 2024-Q4.

**The 84.6% figure belongs to S-SIM, not LightGBM.** For comparison:

| Model | Rows | Accuracy | Balanced acc. | Precision | Recall (HIGH) | F1 | AUC | Brier |
|---|---|---|---|---|---|---|---|---|
| S-SIM (structural simulation, pre-registered E83 arm) | 65 | **0.846** (55/65) | 0.751 | 0.750 | 0.562 (9/16) | 0.643 | 0.889 | 0.118 |
| HYB-GBA-SIM (LightGBM where it can be trained, S-SIM elsewhere; post-hoc) | 65 | 0.877 | 0.834 | — | 0.75 | — | — | 0.101 |

The hybrid met every E83 criterion (Holm p = 0.098), but it was chosen after seeing results, so it is exploratory.

**Reliable horizon (walk-forward, Leads 0–3).**
- Under the pre-registered E83 rule, **no lead qualified**. The rule requires:
  1. accuracy > 0.75 counting unissued rows as wrong;
  2. balanced accuracy above every baseline;
  3. Brier better than persistence, climatology and always-HIGH (Holm p < 0.10);
  4. HIGH recall ≥ 0.5.
- At Lead 1, S-SIM missed only criterion 3 (Holm p = 0.105).
- At Lead 2 the best arm scored 0.738 against always-LOW at 0.754.

**What this establishes about Lead 1 as a nowcast.**
- Once enough labels exist, LightGBM ranks provinces well on the proxy target (AUC 0.955 on 30 rows) and caught every
  HIGH quarter in that period.
- The evidence covers 6 quarters after one HIGH episode. In that period T43 equals food-price pressure, so this is
  evidence of a good **price-pressure nowcast** on 30 forecasts, not of a reliable food-insecurity nowcast.

**Status: Partially Achieved.**

**Justification.**
- All five evaluation elements were computed with walk-forward expanding-window validation.
- The proposed LightGBM issues only 46% of Lead-1 forecasts.
- Its strong issued-row metrics rest on 6 quarters.
- No horizon met the pre-registered reliability rule.
- The target is a proxy.

**Sources.**
- `E83_Deep_Reconstruction/PROTOCOL.md` (§3–6), `runs/20261021T084802Z/predictions_r2_k1.csv`, `RESULTS.json`,
  `RESULTS_TABLES.md`, `predictions_d4_k1.csv`.
- `runner/run_e83.py`, `runner/e83_lib.py`.

---

## Objective 3 — municipal and city risk rankings

**Objective (Chapter I).** "To produce spatially disaggregated municipal and city food insecurity risk rankings from
validated province-level forecasts, using PSA published poverty incidence and population density as vulnerability
weights."

**Answer.** Rankings are produced for all 142 cities and municipalities with the specified weights. The
province-level forecasts they start from are not validated (Objective 2), so the rankings are indicative.

**Evidence (verified on the served API, thesis mode, 2026-10-21):**
- **Coverage.** 142/142 LGUs, 142 unique PSGC codes, correct province assignment, 0 invalid rows. Bands for 2027-Q1:
  138 low, 4 high.
- **Method** (`backend/app/services/dashboard.py`, `municipality_summary`):
  - LGU index = the province estimate re-weighted by PSA 2021 small-area poverty incidence (60%) and 2024 POPCEN
    population density (40%) within the province;
  - each row carries "Indicative, relative ordering … not a measured municipal food-insecurity rate";
  - each row also carries `evidenceStatus = EXPERIMENTAL`.
- **Poverty data actually used** (`backend/data/inputs/lgu_vulnerability.csv`):
  - **141 LGUs use their own PSA 2021 City and Municipal Small Area Estimate.**
  - **1 LGU (City of Lucena)** uses a substitute, because PSA's no-HUC table has no estimate for this highly
    urbanised city. That substitute is the province value stored in the inputs, whose source workbook is unverified.
  - **Correction.** The premise of 126 province-average substitutes is out of date. It comes from an older note in
    `backend/config/forecast_period.json`, from before the PSA SAE integration (E36). The served file has 141 real
    estimates and 1 substitute.
- **Precision of the poverty input.** 25 LGUs have a PSA coefficient of variation above 20%. They are flagged as
  "low-confidence poverty input" in `povertyLimitation`.
- **Lead 1 versus the served product.**
  - The served ranking is computed from the province estimate the dashboard serves: FIRI v2 for target 2027-Q1, issued
    2026-10-01.
  - No separate Lead-1 ranking is published. The method is the same for any province forecast, so its validity
    follows the forecast it is fed.

**Interpretation for local risk.**
- **Within a province,** LGU order comes only from poverty and density.
- **Between provinces,** order follows the province estimate.
- **Not a measured outcome.** No municipal food-insecurity observation exists in the project to check the order. CBMS
  2024 is the missing source (request drafted, E87 `DATA_REQUESTS.md`).
- **Face validity.** FNRI 2021–2023 shows poor households are about twice as food-insecure as non-poor ones (for
  example 46.2% vs 22.5% in Batangas, 2021). This supports a poverty-weighted ordering, but it does not validate the
  specific ranks.

**Status: Partially Achieved.**

**Justification.**
- The rankings are produced for every LGU, with the specified PSA weights and transparent labelling.
- The objective requires *validated* province-level forecasts, which Objective 2 did not establish.
- The rankings have no local outcome validation.

**Sources.** `backend/app/services/dashboard.py`, `data/inputs/lgu_vulnerability.csv`,
`tests/integration/test_e36_served_model.py`, E83–E87 consolidated report §G.

---

## Objective 4 — comparison against the four baselines (Lead 1)

**Objective (Chapter I).** To compare the proposed LightGBM model against:
1. a naive persistence baseline;
2. a PSA-only indicator baseline;
3. an NLP-only sentiment baseline;
4. a logistic regression baseline.

**Answer.**
- The proposed LightGBM clearly outperforms the NLP-only and logistic regression baselines.
- It is better than persistence in point estimates, but not significantly.
- It does **not** outperform the PSA-only baseline.

**Comparison on the identical 30 rows LightGBM issued** (6 quarters, 8 HIGH):

| Model | Accuracy | Balanced acc. | Precision | Recall (HIGH) | F1 | AUC | Brier | Paired Brier gain of LightGBM (per quarter) | One-sided p (Holm) |
|---|---|---|---|---|---|---|---|---|---|
| **LightGBM (proposed)** | **0.867** | **0.909** | 0.667 | **1.00** | **0.800** | **0.955** | **0.086** | — | — |
| Naive persistence | 0.567 | 0.545 | 0.308 | 0.50 | 0.381 | 0.545 | 0.433 | +0.347 | 0.094 (0.188) |
| PSA-only indicator (L2 logistic, price features) | 0.867 | 0.830 | 0.750 | 0.75 | 0.750 | 0.875 | 0.105 | +0.019 | 0.125 (0.188) |
| NLP-only sentiment (L2 logistic, news features) | 0.167 | 0.153 | 0.053 | 0.13 | 0.074 | 0.176 | 0.592 | +0.506 | 0.016 (0.078) |
| Logistic regression (all features) | 0.367 | 0.369 | 0.176 | 0.38 | 0.240 | 0.364 | 0.509 | +0.423 | 0.016 (0.078) |
| Climatology (reference) | 0.733 | 0.500 | — | 0.00 | 0.00 | — | 0.220 | +0.134 | 0.016 (0.078) |

**On all 65 rows** (baselines that issue every row):
- persistence: 0.723 accuracy, balanced 0.627, recall 0.44, Brier 0.277;
- climatology / always-LOW: 0.754, balanced 0.500;
- the PSA-only, NLP-only and logistic regression baselines share LightGBM's eligibility limit (30 issued rows).

**Statistical note.** With 6 independent quarters, the smallest attainable one-sided sign-flip p is 1/64 = 0.016.
Holm correction across the five comparisons gives the bracketed values. Only the NLP-only, logistic regression and
climatology differences are below 0.10 after correction.

**Status: Partially Achieved.**

**Justification.**
- All four required comparisons were run on identical walk-forward rows.
- LightGBM's advantage is clear against two baselines.
- It is not statistically established against persistence.
- It is absent against the PSA-only baseline, which matches LightGBM's accuracy with fewer inputs. This is consistent
  with T43 having become a price label.

**Sources.** `E83_Deep_Reconstruction/runs/20261021T084802Z/predictions_r2_k1.csv` (columns M-GB-ALL, B-PERSIST,
B-PSA, B-NLP, M-LR-ALL, B-CLIM), `runner/run_e83.py` (`specs`, `evaluate`), `runner/e83_lib.py` (`sign_flip`,
`holm`).

---

## Overall assessment of Objectives 1–4 for Lead 1

| Objective | Status | What is demonstrated | What remains unproven |
|---|---|---|---|
| 1. Two-tier NLP pipeline, FSSI, BERTopic | Partially Achieved | Implemented end to end: XLM-RoBERTa zero-shot scores, bias-corrected FSSI-v3, 152 BERTopic topics per province-quarter | FSSI supported in 20/120 province-quarters; no forecasting value from news |
| 2. LightGBM metrics and reliable horizon | Partially Achieved | On the 30 Lead-1 forecasts it can issue: accuracy 0.867, recall 1.00, F1 0.80, AUC 0.955, walk-forward | Covers 6 quarters; 35/65 forecasts not issuable; no lead met the reliability rule; proxy target |
| 3. 142-LGU rankings | Partially Achieved | All 142 LGUs ranked with PSA SAE poverty (141 own estimates, 1 substitute) and POPCEN density; labelled indicative | Province forecasts not validated; no municipal outcome to validate ranks |
| 4. Baseline comparisons | Partially Achieved | Beats the NLP-only and logistic regression baselines (Holm p 0.078) | Not significantly better than persistence (0.188); no better than the PSA-only baseline (0.867 vs 0.867) |

**Conclusion.** For Lead 1, aiPHeed **implemented** everything Objectives 1–4 require, and the proposed LightGBM
shows strong discrimination on the forecasts it can issue.

What is **not yet proven**:
- that these are accurate **food-insecurity** nowcasts, rather than food-price-pressure nowcasts;
- that LightGBM improves on a simple price-indicator baseline;
- that any horizon is reliable under the pre-registered rule;
- that the municipal rankings match observed local food insecurity.

The sealed prospective forecasts (seals 1331d498… and ad402660…) and the drafted CBMS, FNRI and SWS data requests
are the routes to closing these gaps.
