# aiPHeed: final audit of Chapter I Objectives 1–4 and model validation

**Date:** 2026-10-20
**Branch audited:** `final-system-v2` (thesis-mode backend of `final-thesis-system` plus the approved frontend), in `C:\Users\admin\aipheed_final`
**Mode:** `AIPHEED_LEAD2_MODEL=thesis`, `AIPHEED_STRICT_MODEL=1`

**Method.** Every figure below was recomputed in this audit from prediction-level files or from the running backend. Historical reports were used only to locate artifacts. The audit scripts and their outputs are in `audit/2026-10-20_final_validation/` (§10).

---

## 0. Decision summary

| Item | Decision |
|---|---|
| Objective 1: NLP pipeline, FSSI, BERTopic | **PARTIALLY MET.** Implemented and running, but not validated: annotations are AI-generated, the bias correction is untested, coverage is thin, and no predictive value was measured. |
| Objective 2: metrics and lead time | **PARTIALLY MET.** Every metric was reproduced exactly, and the walk-forward multi-lead evaluation was done. The label is food-price pressure in practice, the evidence comes from development data only, and no reliable horizon was established. |
| Objective 3: 142 LGU rankings | **PARTIALLY MET.** All 142 are complete, finite, correctly mapped and consistent across API, map and PDF. The objective's premise, "validated province-level forecasts", is not met. |
| Objective 4: baseline comparison | **PARTIALLY MET.** The comparison is fair, on identical rows. The LightGBM is credibly better than baseline II (PSA-only) and IV (combined LR) only. It is not credibly better than naive persistence or NLP-only, and the evidence is development data only. |
| **At least 75% Lead-2 food-insecurity forecasting accuracy** | **NO.** The requirement of at least 75% Lead-2 food-insecurity forecasting accuracy has not been demonstrated. |
| Overfitting / generalization | **Insufficient data to determine, with warning signs:** the Lead-2 probabilities are over-confident (calibration slope 0.55), the selected configuration is unstable (9 different configurations across 10 origins), and every quarter was reused across about 30 development experiments. |
| Leakage (feature and label timing) | **No leakage found.** All 10 Lead-2 origins were refit from raw data and reproduce the sealed forecasts to about 1e-13. Corrupting every value published after the issue date changes no forecast. |
| Strongest defensible model | E56-TUNED LightGBM, the Lead-2 food-price-pressure forecaster. It is served as one input of FIRI v2, a transparent proxy index. No model change was made (§8). |

---

## 1. Requirement basis: Chapter I, verbatim

The objectives are quoted from `THESIS 2 (11).pdf`, extract `E25_Reliable_Forecasts_2021_2026/thesis_source/CHAPTER_I_verbatim.txt` on `final-thesis-system`.

1. "To design a two-tier pipeline combining zero-shot XLM-RoBERTa Filipino-English sentiment extraction and BERTopic unsupervised topic modeling to produce the bias-corrected Food Stress Sentiment Index and latent food insecurity risk patterns per province-quarter from a Filipino-English news corpus."
2. "To evaluate the performance of the proposed LightGBM forecasting model using the following metrics: I. Accuracy … II. Precision and Recall … III. F1-Score … IV. AUC-ROC … V. Forecast performance across multiple lead times via walk-forward expanding-window cross-validation to empirically determine the furthest horizon at which reliable forecasting is achievable"
3. "To produce spatially disaggregated municipal and city food insecurity risk rankings from validated province-level forecasts, using PSA published poverty incidence and population density as vulnerability weights."
4. "To compare the effectiveness of the proposed LightGBM forecasting model against the following baseline approaches: I. Naive persistence baseline II. PSA-only indicator baseline III. NLP-only sentiment baseline IV. Logistic regression baseline"

Two further points from Chapter I matter here:

- **The label.** Chapter I §1.7 says: "SWS quarterly hunger data and PSA food price data will be used to determine food insecurity risk." T43 implements this.
- **The 75% threshold.** Chapter I states no accuracy threshold. The ≥ 75% Lead-2 requirement comes from this audit's acceptance brief and is applied as such in §4.

---

## 2. The selected model and the exact target

| Output | What it is | Evidence |
|---|---|---|
| **LightGBM (E56-TUNED)**, Objective 2/4 model | P(T43 HIGH at quarter t+2) = P(regional SWS hunger > 11.3%) × P(provincial food-price pressure). The second factor is a LightGBM chosen at each origin from 72 configurations by forward log-loss on training quarters only. | `E56_LightGBM_Optimization/runner/e56_lib.py`; refits in §5.2 |
| **T43 label** | HIGH if SWS Balance Luzon hunger in the quarter > 11.3% AND (province food CPI YoY > its 2021–22 P60, OR food-minus-headline YoY > its P60) | `E40_SWS_CPI_Tiers/label_spec.json`; rebuilt independently in this audit |
| **What T43 measures in practice** | Food-price pressure. On all 205 evaluated rows (Leads 1–3), T43 equals the price-pressure label, because SWS hunger exceeded 11.3% in every evaluated target quarter (minimum 14.3%). | `out/audit_console.txt` ("T43==PS": 50/50 and 155/155) |
| **Served province estimate (map colour)** | FIRI v2 (candidate C3): a 0–1 proxy composite of six domains, with the LightGBM as one affordability indicator. Domains are weighted by their walk-forward correlation with regional SWS hunger. HIGH at ≥ 0.50. | `/api/v1/config` `servingModel`, `indicator` |

**Lead definition, verified on every row.** The origin quarter t is the latest complete data quarter. The issue date is the first day of quarter t+1. **Lead-2 targets quarter t+2**, the quarter after the issue quarter (an estimate issued on 1 October 2026 is for January–March 2027). Lead-1 targets the quarter already under way at issue. Checked on all 205 rows: the issue date is the day after the origin quarter ends, target minus origin equals the lead, there are no duplicate rows, and no target quarter's SWS round was published before its issue date.

---

## 3. Independently reproduced results (from the sealed prediction files)

**Inputs:**
- `E57_E56_Rolling_Origin_Test/sealed/predictions.csv`, sha256 `4d52b1f3…`, matches its seal;
- `E63_Lead_Time_Study/sealed/predictions.csv`, sha256 `7acae3a1…`, matches its seal.

**Labels.** Rebuilt from `psa_cpi_yoy_headline_food_2021_2026.csv`, `sws_rounds.csv` and `label_spec.json`, without the project's label library. They agree with the Objective 4 baseline file on 45/45 rows.

**Leakage.** E57 and E63 Lead-2 forecasts are identical (max difference 0.0). The decision threshold is 0.50 throughout.

### 3.1 LightGBM, Lead-2 (50 province-quarters, 10 target quarters 2024-Q2 to 2026-Q3)

| Model | Correct / n | Accuracy [Wilson 95%] | TP / FP / FN / TN | Prec HIGH | Rec HIGH | F1 HIGH | Rec LOW | Bal. acc | AUC-ROC | Brier |
|---|---|---|---|---|---|---|---|---|---|---|
| **LightGBM E56** | **36/50** | **0.720 [0.583, 0.825]** | 10 / 6 / 8 / 26 | 0.625 | 0.556 | 0.588 | 0.813 | 0.684 | 0.649 | 0.214 |
| Naive persistence | 28/50 | 0.560 [0.423, 0.688] | 8 / 12 / 10 / 20 | 0.400 | 0.444 | 0.421 | 0.625 | 0.535 | 0.535 | 0.440 |
| Majority (always LOW) | 32/50 | 0.640 [0.501, 0.759] | 0 / 0 / 18 / 32 | — | 0 | 0 | 1 | 0.500 | 0.500 | 0.360 |
| Climatology | 32/50 | 0.640 [0.501, 0.759] | 0 / 0 / 18 / 32 | — | 0 | 0 | 1 | 0.500 | 0.214 | 0.305 |

- **Class balance:** 18 HIGH, 32 LOW.
- **Quarter-cluster bootstrap 95% CI for accuracy:** [0.58, 0.84].
- **Within-quarter label correlation (ICC):** 0.29, design effect 2.18, so the **effective sample is about 23 observations**, not 50.
- **Paired comparisons:**

| LightGBM vs | Δ Brier [quarter-bootstrap 95% CI] | Quarter Brier wins/losses (two-sided sign p) | McNemar (LightGBM right only / baseline right only, p) |
|---|---|---|---|
| Persistence | −0.226 [−0.399, −0.059] | 7/3 (p 0.34) | 13/5 (p 0.096) |
| Majority | −0.146 [−0.298, −0.004] | 7/3 (p 0.34) | 10/6 (p 0.45) |
| Climatology | −0.090 [−0.190, −0.001] | 5/5 (p 1.0) | 10/6 (p 0.45) |

- **Calibration, Lead-2:**
  - logistic calibration slope 0.55, intercept −0.34 (over-confident);
  - expected calibration error 0.226;
  - in the 0.1–0.2 probability bin, 6 of 10 rows were HIGH (mean predicted 0.15).
- **By target quarter** (correct of 5):

| Quarter | 2024-Q2 | 2024-Q3 | 2024-Q4 | 2025-Q1 | 2025-Q2 | 2025-Q3 | 2025-Q4 | 2026-Q1 | 2026-Q2 | 2026-Q3 |
|---|---|---|---|---|---|---|---|---|---|---|
| Correct | 1 | 3 | 3 | 4 | 4 | 3 | 5 | 5 | 4 | 4 |

  The 2024-Q2 rise was missed (4 HIGH rows predicted LOW).
- **By province** (correct of 10; HIGH found / HIGH rows):

| Province | Correct | HIGH found |
|---|---|---|
| Batangas | 7 | 1/3 |
| Cavite | 4 | 1/4 |
| Laguna | 7 | 3/5 |
| Quezon | 8 | 5/6 |
| Rizal | 10 | 0 HIGH rows |

### 3.2 LightGBM, Lead-1 (60 rows, 12 quarters 2023-Q4 to 2026-Q3)

| Model | Correct / n | Accuracy [Wilson 95%] | TP / FP / FN / TN | Prec HIGH | Rec HIGH | F1 HIGH | Rec LOW | AUC | Brier |
|---|---|---|---|---|---|---|---|---|---|
| **LightGBM E56** | **51/60** | **0.850 [0.739, 0.919]** | 15 / 3 / 6 / 36 | 0.833 | 0.714 | 0.769 | 0.923 | 0.901 | 0.130 |
| Persistence | 41/60 | 0.683 | 11 / 9 / 10 / 30 | 0.550 | 0.524 | 0.537 | 0.769 | 0.647 | 0.317 |
| Majority / climatology | 39/60 | 0.650 | 0 / 0 / 21 / 39 | — | 0 | 0 | 1 | 0.500 / 0.344 | 0.350 / 0.284 |

- **Paired Brier differences:**
  - vs persistence: −0.187 [−0.289, −0.088], quarters 9/3, sign p 0.146;
  - vs climatology: −0.155 [−0.259, −0.057], quarters 9/3, sign p 0.146.
- **Calibration slope:** 0.97 (good).
- **Effective sample:** about 28 observations.

**Lead-3** (45 rows, 9 quarters):
- accuracy 28/45 = 0.622 [0.476, 0.749], below always-LOW (0.689);
- AUC 0.620, Brier 0.251;
- calibration slope 0.25.

### 3.3 Objective 2 V: furthest reliable horizon

The criterion was pre-registered on 2026-10-19 (E63 §8, protocol sha `5b3ee7e9…`, re-verified by `final_evaluation.py`). It requires a paired Brier better than both persistence and climatology, each with a quarter-cluster CI below 0 and a two-sided quarter sign test p < 0.05.

- **No lead meets it.** Lead-1 comes closest: both CIs are below 0, but the sign p is 0.146 with only 12 quarters.
- **Lead-4** cannot be computed under the CPI cutoff.
- **Furthest reliable horizon: none established.**

---

## 4. The 75% Lead-2 requirement

| Check | Result |
|---|---|
| Lead-2 accuracy, LightGBM | 36 correct / 50 = **0.720**, Wilson 95% [0.583, 0.825]. **Below 0.75.** |
| On the 45 Objective 4 rows (targets 2024-Q3 to 2026-Q3) | 35/45 = 0.778 [0.637, 0.875]. This is a subset chosen because the baselines need 6+ training quarters. Always-LOW scores 31/45 = 0.689 on it (Brier difference CI [−0.299, +0.019] includes 0), so it is not a separate demonstration. |
| Held-out or prospective? | **Neither.** All 10 quarters were examined during development: about 30 experiment rounds (E38–E69, 34 experiment folders since E36) used the same 2023–2026 quarters. The truly unseen forecasts (2026-Q4, 2027-Q1) are sealed: E68 `prospective.csv` sha `79aa6f2a…`, E69 `outlook_forward.csv` `e6b6266f…`, FIRI v2 `firi2_sealed_prospective.csv` `e2bef0b2…` (LF-normalised, matches). Their outcomes are not yet published. |
| What the label measures | Food-price pressure on every evaluated row (§2). By this audit's rule, accuracy against price-pressure labels is not proof of food-insecurity accuracy. |
| FIRI v2, the served risk index | **Against T43**, on the same 50 Lead-2 rows: 19/50 = 0.380 (classifies 94% HIGH). **Against regional SWS hunger > 11.3%:** 16/17 = 0.941 [0.730, 0.990], vs 12/17 = 0.706 for both always-elevated and the regional hunger outlook alone. This is regional, a proxy agreement, and not independent: FIRI's own regional-hunger indicator uses SWS, and its domain weights are fitted to the same SWS outcome walk-forward. The Brier is not better than the hunger outlook alone (Δ +0.027, CI [−0.077, +0.118]). By this audit's rule it does not count. |

**Decision: NO. The requirement of at least 75% Lead-2 food-insecurity forecasting accuracy has not been demonstrated.**

No labels, observations or thresholds were changed to reach this result.

---

## 5. Overfitting, leakage and temporal generalization

### 5.1 Leakage and timing: reproduced from raw data

`repro_leak.py` refits the frozen E56 procedure from raw inputs at all 10 Lead-2 origins.

1. **Reproduction.** Every refit equals the sealed forecasts (max difference 3e-13 to 5e-13), and the same configuration is selected.
2. **Corruption test.** Every raw value not available at the issue date was replaced by random values:
   - CPI months after the cut month;
   - SWS rounds posted on or after the issue date;
   - production and LFS beyond their cuts;
   - news after quarter t;
   - typhoons after t, and ENSO, remittances and rice after t−1;
   - policy events announced on or after the issue date.

   The features and bases were then rebuilt and the model refit. **At every origin the forecast changed by exactly 0.0 and the selected configuration was unchanged.** No future information reaches the forecast.
3. **Labels and baselines.**
   - Persistence labels come only from quarters whose SWS rounds were all published before the issue date (verified on all rows).
   - The baseline training labels end before the target (`t_label` < target on all 45 rows).
   - Training rows are restricted to targets ≤ t−1.
   - Model selection uses forward folds inside the training quarters.

**What the test cannot exclude:**
- **Data revisions.** The files are the latest PSA vintage, not real-time vintages.
- **Retrospective news collection.** 687 of 695 admitted articles were first seen after their quarter's issue date. Publication dates respect the cutoff, but the corpus was assembled later.
- **Research-level selection.** The label percentile, feature groups, search space and the move from E44 to E56 were all designed while these quarters were being examined. This is selection on the evaluation period, and no code test can remove it.

### 5.2 Model complexity vs data

| Item | Value |
|---|---|
| Training rows per Lead-2 origin | 35 to 80 province-quarters (7 to 16 quarters; 20 to 40 HIGH) |
| Features | 9 (market + policy) to 31 (all groups + poverty) |
| Search space | 72 configurations, chosen per origin |
| Configurations actually chosen | 9 different ones across 10 origins (ids 46, 27, 41, 41, 37, 68, 61, 54, 50, 23) |
| Effective independent observations at evaluation | about 23 at Lead-2 (ICC 0.29); 10 quarters |
| Calibration slope | Lead-1 0.97, Lead-2 0.55, Lead-3 0.25 |

**Classification: insufficient data to determine, with warning signs of overfitting.** Lead-2 and Lead-3 probabilities are over-confident, configuration choice is unstable, and accuracy falls with lead (0.85 → 0.72 → 0.62, the last below always-LOW). Performance is also concentrated in time:
- from 2024-Q2 to 2025-Q3, 18/30 correct with 17 HIGH;
- from 2025-Q4 to 2026-Q3, 18/20 correct but only 1 HIGH, a regime where always-LOW is also nearly perfect.

---

## 6. Bias audit (measured)

| Bias | Evidence | Effect | Correctable with existing data? |
|---|---|---|---|
| Class imbalance / HIGH errors | Lead-2: 18 HIGH vs 32 LOW; HIGH recall 0.556; 8 HIGH rows missed, 4 of them in the 2024-Q2 surge | The model misses rising risk, which is costly for a warning tool | Partly. Class weighting was in the search space (`cw` balanced) and did not help on forward folds. |
| Province performance | Lead-2 HIGH recall: Cavite 1/4, Batangas 1/3, Laguna 3/5, Quezon 5/6; Rizal has no HIGH rows | Uneven detection; the five-province sample cannot separate province bias from chance | **Cannot be reliably estimated** (3 to 6 HIGH rows per province) |
| News volume and attribution | Admitted province-attributed headlines: Cavite 99, Batangas 72, Laguna 47, Quezon 41, Rizal 37. Province-quarters with 0 articles: Rizal 17/23, Cavite 10, Quezon 10, Batangas 8, Laguna 8. SUFFICIENT (≥ 5): 20 of 115. | News evidence is missing for most province-quarters and skewed toward Cavite and Batangas | No. More collection is needed. |
| Language and source | 7 of 695 admitted headlines look Filipino (simple keyword test). Top outlets: Inquirer 20%, GMA 19%, DA 12%, Manila Bulletin 12%; 23 outlets in all. | "Filipino-English" is almost entirely English national media, with a government-press share (DA, PIA, PNA about 20%) | No |
| Bias correction | Weight log(1+median n)/log(1+n) ranges 0.28 to 3.70, so a single article can be multiplied by 3.7 | Amplifies noise where coverage is thinnest; not validated | Only by a human-labelled validation set |
| Proxy bias (label) | T43 equals price pressure on all 205 rows; hunger was above 11.3% throughout | The "food-insecurity" label is a CPI rule; a rice-tariff disinflation (2025-Q4 onward) turns it LOW while regional hunger stayed high | No provincial food-insecurity outcome exists |
| Proxy bias (FIRI) | FIRI v2 classifies 94% of the Lead-2 T43 rows HIGH and all 5 provinces HIGH in 2027-Q1; regional hunger (same for all provinces) carries 25–29% weight and national employment 20% | High levels are driven by regional and national series, not provincial evidence | Weights could be changed, but there is no local outcome to test against |
| Repeated national values | E1 (unemployment), E2 (remittances), C1 (El Niño status), H1 (regional hunger) are identical for all five provinces; within-quarter ICC of FIRI v2 classes 0.56 (design effect 3.2) | Inflates the apparent sample: 85 FIRI province rows ≈ 26 effective | Report the effective n (done here) |
| Missing data and substitutes | Lucena uses an unverified province poverty substitute; remittances missing from all 2026 issues; 2026-Q3 typhoon count incomplete | Missing indicators are dropped (never zero), which shifts weight onto the remaining domains | Partly. A verified Lucena value is needed. |
| Label source mixing | T43 averages all SWS rounds, including non-approved ones. 2025-Q2 (17.0, 15.3) and 2025-Q3 (23.8) have only non-approved rounds; T43 on approved rounds only is missing for 10 of 50 Lead-2 rows. | Two evaluated quarters rest on rounds outside the approved definition | A documented choice; report both |
| Temporal / regime | Lead-2 HIGH share: 17/30 rows in targets 2024-Q2 to 2025-Q3 vs 1/20 in 2025-Q4 to 2026-Q3 | Accuracy depends on the regime; the recent "good" quarters are mostly LOW | No; more quarters are needed |
| Threshold choice | T43 uses P60 thresholds picked "after the P60–P85 grid" with gates on development prevalence (label_spec `selection`) | The label definition was tuned on the development period's prevalence | Fixed now; only new quarters can test it |
| LGU display band | LGU index = province index × a 0–1 vulnerability weight (min-max within province), coloured at the province's 0.50 cutoff. In 2027-Q1 all 5 provinces are HIGH but only 4/142 LGUs are | LGUs read systematically "lower risk" than their province | A display decision (user, E45); documented, not changed |

---

## 7. Evidence tables by objective

### Objective 1: NLP pipeline

| Requirement | Implementation evidence | Reproduced result | Limitations | Status |
|---|---|---|---|---|
| Zero-shot XLM-RoBERTa Filipino-English sentiment | `app/news/fssi_v2.py`, `scoring.py`: `joeddav/xlm-roberta-large-xnli`, ten bilingual hypotheses, max entailment | Every admitted article has a stored intensity; `fssi_v3` refuses to run otherwise | Titles only; 7/695 Filipino by a simple test | Implemented |
| Relevance, attribution, de-duplication, cutoff | `pipeline_v3.py`: classifier v2 (hash-frozen), title geocoding, 3-day syndication clustering, `asof(t)` publication-date cutoff | 9,667 headlines in window → 697 relevant → 695 admitted (2 syndicated duplicates); 296 province-attributed, 399 national | Classifier evaluated only against AI annotations; corpus collected retrospectively (687/695 first seen after the issue date) | Implemented |
| Bias-corrected FSSI | `fssi_v3`: Equation 2 weight; SUFFICIENT at ≥ 5 articles | 20 of 115 province-quarters SUFFICIENT; weight 0.28 to 3.70 | Bias correction not validated | Implemented, **not validated** |
| BERTopic latent patterns | `data/news_v3/topic_info.csv`, `article_topics.csv` (152 topics per the report) | Served as the top topics per province-quarter | Mostly geographic topics; descriptive only | Implemented |
| Integration and predictive value | FSSI-v3 is FIRI v2's N1 indicator when SUFFICIENT. The LightGBM uses old E40 trigger-composition counts (not FSSI-v3), and only in the "all" feature set chosen at 4 of 10 Lead-2 origins. | NLP-only baselines on the 45 rows: LR AUC 0.488, LightGBM-NLP AUC 0.450, i.e. no discrimination | No measured predictive value | **No measurable value** |

**Overall: PARTIALLY MET.** The pipeline is built and served. Its scientific validity (human-validated relevance, bias correction, predictive value) is not demonstrated.

### Objective 2: performance and lead time

| Requirement | Implementation evidence | Reproduced result | Limitations | Status |
|---|---|---|---|---|
| I–IV: Accuracy, Precision/Recall, F1, AUC-ROC | Sealed walk-forward predictions; recomputed here | Lead-2: acc 0.720, prec 0.625, rec 0.556, F1 0.588, AUC 0.649, Brier 0.214. Lead-1: 0.850 / 0.833 / 0.714 / 0.769 / 0.901 / 0.130 (§3) | Label = food-price pressure in practice; development data; over-confident at Lead-2 | Computed and reproduced |
| V: walk-forward, expanding window, furthest reliable horizon | E63: expanding window (Lead-1 training 30→85 rows); issue-date cutoffs verified (§5.1) | No lead meets the pre-registered criterion; Lead-4 not computable | 9–12 quarters per lead | Done; outcome **none established** |
| Predicts the system's estimated food-insecurity risk? | The LightGBM predicts T43 (price pressure). The served risk is FIRI v2, a proxy composite, not a supervised forecast. | FIRI v2 vs T43: Lead-2 0.380; vs regional hunger 0.941 (proxy, regional) | No local food-insecurity outcome exists | **No** |

**Overall: PARTIALLY MET.** The metrics and lead-time evaluation are complete and reproducible. The model forecasts food-price pressure, not measured food insecurity, and its results are development evidence.

### Objective 3: 142 LGU rankings

| Requirement | Implementation evidence | Reproduced result | Limitations | Status |
|---|---|---|---|---|
| All 142 complete, finite, mapped | `/api/v1/provinces/{id}/municipalities` (thesis mode) | 142 unique ids and PSGC codes in 2027-Q1, 2026-Q3 and 2025-Q2 (34/23/30/41/14); all finite; all 142 match the boundary file under the map's join rule | — | Met |
| Poverty and density weighting | `lgu_audit.build_ranking`: 0.6 × poverty_norm + 0.4 × density_norm, min-max within province; LGU index = province index × vulnerability | Recomputed independently: max difference 5e-5 (4-dp rounding). Only exception: Lucena 2027-Q1, served 0.4900 vs 0.498595, the documented display rule for a LOW value in [0.495, 0.5). | Lucena poverty is an unverified substitute; with min-max scaling within each province, the least vulnerable LGUs get weights close to 0 (lowest: Tagkawayan 0.0078, Ternate 0.0149) | Met (as defined) |
| Consistency across API, dashboard, map and PDF | Browser end-to-end; PDF text extraction | Region 0.74 and the 5 province values on the map equal the API; the region PDF contains all 5 province scores; the Batangas PDF contains all 34 LGU values exactly (4 dp); province estimates equal FIRI v2 history | — | Met |
| "From validated province-level forecasts" | Every LGU row carries "relative prioritization, not a municipal forecast" | Within-province rank correlation with vulnerability ≥ 0.9998, so the order inside a province is the vulnerability order | Province estimates are not validated | **Premise unmet** |

**Overall: PARTIALLY MET.** These are defensible relative prioritizations, correctly labelled. They are not validated municipal forecasts.

### Objective 4: baseline comparison

The comparison uses 45 identical rows (targets 2024-Q3 to 2026-Q3), with the same issue dates, the same independently rebuilt T43 labels (45/45 agree) and the same lead.

| Model | Correct / 45 | Acc [Wilson 95%] | TP/FP/FN/TN | Rec HIGH | Rec LOW | F1 HIGH | AUC | Brier |
|---|---|---|---|---|---|---|---|---|
| **LightGBM E56** | 35 | 0.778 [0.637, 0.875] | 10/6/4/25 | 0.714 | 0.806 | 0.667 | 0.763 | 0.178 |
| I. Naive persistence | 27 | 0.600 | 8/12/6/19 | 0.571 | 0.613 | 0.471 | 0.592 | 0.400 |
| II. PSA-only LR | 17 | 0.378 | 3/17/11/14 | 0.214 | 0.452 | 0.176 | 0.295 | 0.598 |
| III. NLP-only LR | 30 | 0.667 | 2/3/12/28 | 0.143 | 0.903 | 0.211 | 0.488 | 0.235 |
| IV. Combined LR | 15 | 0.333 | 3/19/11/12 | 0.214 | 0.387 | 0.167 | 0.247 | 0.646 |
| Majority (always LOW) | 31 | 0.689 | 0/0/14/31 | 0 | 1 | 0 | 0.500 | 0.311 |

| LightGBM vs | Δ Brier [95% CI] | Quarter wins/losses (two-sided sign p) | McNemar p | Credible advantage? |
|---|---|---|---|---|
| I. Persistence | −0.222 [−0.409, −0.040] | 6/3 (0.51) | 0.096 | **No** (sign test) |
| II. PSA-only LR | −0.420 [−0.644, −0.199] | 8/1 (0.039) | 0.0009 | **Yes** |
| III. NLP-only LR | −0.057 [−0.122, +0.006] | 7/2 (0.18) | 0.36 | **No** |
| IV. Combined LR | −0.467 [−0.671, −0.266] | 9/0 (0.0039) | 0.0003 | **Yes** |
| Majority | −0.133 [−0.299, +0.019] | 6/3 (0.51) | 0.45 | **No** |

The two baselines the LightGBM beats (II and IV) have AUC below 0.5. They are worse than chance, which makes beating them weak evidence of skill.

**Discrepancy:** the groupmate's report §11 and `final_evaluation.json` give the sign-test p-values one-sided, e.g. "6/3 (p 0.25)" and "8/1 (p 0.02)". Two-sided, they are 0.51 and 0.039. The "established" verdicts are unchanged.

**Overall: PARTIALLY MET.** The comparison is fair and complete. The LightGBM is better on Brier against every baseline, but credibly so only against II and IV, and on development quarters only.

---

## 8. Model improvements: none made, and why

No new model, feature, weight or threshold was tried in this audit:

1. **Every Lead-2 quarter has already been used in model selection**, across about 30 experiment rounds (E38–E69). Any further change would be selected on the same quarters, and no data remains to test it. The brief requires improvements that "can be evaluated properly"; that is not possible until the sealed 2026-Q4 and 2027-Q1 outcomes are published.
2. **Changes already tried and recorded failed their pre-registered rules on these rows:**
   - recalibration (FIRI2 L1 Platt: Brier worse, +0.052, CI [+0.007, +0.109]);
   - a walk-forward threshold (L2: balanced accuracy 0.641 vs 0.684);
   - LightGBM retuning (E53, E56 vs E55: Δ −0.001, CI includes 0);
   - news features (E60/E64: ≤ 0.01 Brier change);
   - climate arms (E65, E68);
   - poverty arms (E54).
3. The strongest defensible configuration is therefore the one already served:
   - the **E56-TUNED LightGBM** for food-price pressure (best Brier of all models on the comparison rows; credible gains only over II and IV);
   - inside **FIRI v2**, a transparent, pre-registered proxy framework that the dashboard explains indicator by indicator, labelled "not a probability" and "not validated".

**Is the proxy framework more defensible than claiming a supervised food-insecurity model?** Yes, under the following conditions:
- FIRI v2 must not be described as validated or as a probability (the API and dashboard say this);
- its regional agreement with SWS (0.94) must be disclosed as non-independent;
- the LightGBM accuracy must be described as food-price-pressure accuracy.

**Framework checks (§5 of the brief):**
- **Observed outcomes vs proxies:** separated.
- **Documentation:** directions, normalization, weights, threshold and missing-data rules are documented and hash-frozen (`FIRI2_PROTOCOL.md`).
- **Issue-date availability:** respected (§5.1).
- **Circularity:** regional hunger is both an input domain and the evaluation outcome, and is disclosed as such.
- **Regional hunger:** never presented as provincial.
- **Calibrated probabilities:** none claimed.
- **Explanations and data sufficiency:** shown per province.

---

## 9. Changes made in this audit

| Change | File | Reason |
|---|---|---|
| Corrected the issue-timing sentences (Methodology note "Forecast lead" and FAQ "How far ahead…") | `frontend/src/pages/Landing.tsx` | The pushed copy said estimates are issued "for the quarter two quarters ahead". The verified rows show an estimate issued on the first day of a quarter is for the **following** quarter, which is two quarters after the latest complete data quarter. |
| Added the audit scripts and outputs | `audit/2026-10-20_final_validation/` | Reproducibility |
| Added this report | `FINAL_OBJECTIVES_AND_MODEL_VALIDATION_AUDIT.md` | Deliverable |

No backend code, model, data, label, threshold or design element was changed.

---

## 10. Tests and reproducible commands

| Check | Result |
|---|---|
| Backend `pytest -q` (final-system-v2, thesis data) | **542 passed, 18 skipped, 0 failed** (102 s) |
| Frontend `vitest run` | **49/49** (12 files) |
| `tsc --noEmit -p tsconfig.app.json` | 6 errors, all pre-existing in `src/data/mockData.ts` (not rendered) |
| `vite build` | passed |
| Browser end-to-end (thesis API + dev UI) | Map page: region 0.74 and all 5 province values equal the API; landing summary card and factors equal `/explainability`; corrected text renders. Console: only the known basemap "Wrong magic number for PMTiles archive" (no local basemap file). |
| Seals | E57, E63, E68, E69 match their sha256; the FIRI v2 seal matches after LF normalisation (the file is committed with CRLF) |

**Commands.** All use `backend/venv` of the `final-thesis-system` checkout at `C:\Users\admin\aipheed`, because the experiment runners and raw label inputs are only complete there. `final-system-v2` holds the sealed predictions and the served backend.

```
# 1. FIRI v2 evaluation files used by audit.py (read-only extraction; create ft\out\firi2 first).
#    audit.py writes audit_results.json beside itself; the committed copy is in out\.
git -C C:\Users\admin\aipheed_final show origin/final-thesis-system:aipheed-backend-aligned/experiments/FINAL_Thesis_System/out/firi2/rows.csv     > audit\2026-10-20_final_validation\ft\out\firi2\rows.csv
git -C C:\Users\admin\aipheed_final show origin/final-thesis-system:aipheed-backend-aligned/experiments/FINAL_Thesis_System/out/firi2/regional.csv > audit\2026-10-20_final_validation\ft\out\firi2\regional.csv
# 2. Metrics, labels, baselines, FIRI v2 (prints the tables in sections 3, 4 and 7)
C:\Users\admin\aipheed\backend\venv\Scripts\python.exe -B audit\2026-10-20_final_validation\audit.py
# 3. Refit and leakage test (about 1 minute per origin)
C:\Users\admin\aipheed\backend\venv\Scripts\python.exe -B audit\2026-10-20_final_validation\repro_leak.py 2023-Q4 2024-Q1 2024-Q2 2024-Q3 2024-Q4 2025-Q1 2025-Q2 2025-Q3 2025-Q4 2026-Q1
# 4. Objective 1 and Objective 3 (cwd = backend; thesis env vars; scratch DATABASE_URL after alembic upgrade head)
cd backend
..\..\aipheed\backend\venv\Scripts\python.exe -B ..\audit\2026-10-20_final_validation\obj1.py ..\audit\2026-10-20_final_validation\out\obj1_results.json
..\..\aipheed\backend\venv\Scripts\python.exe -B ..\audit\2026-10-20_final_validation\obj3.py ..\audit\2026-10-20_final_validation\out\obj3_results.json
```

---

## 11. Data limitations and the next independent evaluation

**Limitations:**
1. **No provincial or municipal food-insecurity outcome** (CBMS, provincial FIES, caseloads). This blocks validation of every province or LGU claim.
2. **The label is price pressure in practice.** SWS hunger stayed above 11.3% throughout, so T43 cannot separate hunger from prices.
3. **Small sample.** 10 Lead-2 quarters, about 23 effective observations. Accuracy 0.72 has a 95% interval of [0.58, 0.83], so even a true 75% could not be confirmed from this sample.
4. **News.** Titles only, collected retrospectively, AI-annotated, thin and English-dominated.
5. **National and regional inputs** repeated across provinces; remittances end 2025-Q4.
6. **Data vintages.** Latest-vintage PSA data, not real-time vintages.

**Next independent evaluation**, without changing anything sealed:
1. Score the sealed 2026-Q4 and 2027-Q1 forecasts (E68, E69, FIRI v2) once PSA CPI for October 2026 to March 2027 and the SWS 2026-Q4 and 2027-Q1 rounds are published.
2. Keep sealing each new quarter **before** its outcome is published. A credible Lead-2 accuracy claim needs roughly 20 or more unseen quarters.
3. Obtain a provincial or LGU food-insecurity outcome (for example CBMS food-insecurity items) to validate FIRI.
4. Build a human-annotated, Filipino-inclusive headline set to validate relevance and FSSI.

---

## 12. Branch and commit

The commit SHA and working-tree state for this report are given in the reply that delivers it, because a file cannot contain its own commit SHA. Nothing was merged or deployed.
