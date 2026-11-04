# E145: province-level news against measured provincial food insecurity. Protocol E145-P1

Written and locked before any E145 news feature was compared with a survey outcome. The lock file is `backend/data/e145/out/PROTOCOL_LOCK.json`.

**Status of the data.** Every HFIAS row used here has been seen by E137 to E143. E145 therefore cannot be an untouched test. Its results are development evidence, and they are labelled that way. What is new is the news panel: no earlier experiment gave the provincial model news, because news covered only the five CALABARZON provinces.

## 1. Question

Does province-level news, built only from articles published before the issue date, improve a LightGBM forecast of measured provincial food insecurity beyond government data and the province's earlier surveys?

**H-N145.** At lead 1, adding bias-corrected news lowers the expected Brier score (EB) of the E143 model. The check is the difference FULL minus C4, with a Holm-corrected 95 % interval below zero across leads 1 to 4.

## 2. Target

* **Measure.** HFIAS moderate-or-severe prevalence by province (FNRI NNS 2013, FNRI 2015, ENNS 2018 and 2019). The relative logit `y` and the survey standard error `se_y` come unchanged from `app.e141.panel`.
* **HIGH.** The province's prevalence is above the national reference, the owner's decision D-1 (2026-11-03). `q` is the probability of this given sampling error. Decisive rows have status ELEVATED or LOWER.
* **Not used as a target:** food prices, CPI, poverty, news sentiment, SWS hunger or FIES.

## 3. Forecast timing

Convention: the issue date of lead h is the first day of the quarter h quarters before the target quarter. Lead 1 for target 2015-Q3 is issued on 2015-04-01. A value enters only if published before the issue date.

Survey reference quarters are taken as Q3 of the survey year (as in E141). This is an assumption, because fieldwork spans several months. E143 found the result insensitive to a shift of up to 2 quarters.

## 4. News panel (no outcome is used in this section)

**Collection.** Rappler public WordPress archive, 2012 to the last evaluated issue date (2019-04-01), with the same exact phrases for every province (`app/e145/collect.py`). Articles from later years are collected only if news passes this test. Rappler caps a query at 10,000 hits, so a very large province phrase may stop before 2019. Each capped phrase is recorded in the log and reported.

**Text.** Title and excerpt, which is the same text FI6-N used. Articles that report a hunger or food-security survey are removed, so the label cannot leak in: titles or excerpts matching `SWS`, `Social Weather`, `FNRI`, `hunger survey`, `food insecurity survey`, `National Nutrition Survey`. Duplicates are removed by article id within a province and by normalised title across ids.

**Gate.** Title or excerpt must match the food-security term list in `app/e145/news.py`, in English and Filipino. Only gated articles are scored.

**Tier 1, sentiment.** Zero-shot XLM-RoBERTa (`joeddav/xlm-roberta-large-xnli`), with the FI6-N hypotheses unchanged. An article is a stress event if max(p_harder, p_hardship) ≥ 0.5 and p_response < 0.5. These cut-offs are fixed here and are not tuned.

**Tier 2, topics.** BERTopic with `paraphrase-multilingual-MiniLM-L12-v2` embeddings, place names masked, fitted once per test origin and lead, on a seeded sample of at most 8,000 gated articles published before that issue date, then reduced to 6 topics. Other articles published before that date are assigned with `transform`. Training and test rows of an origin therefore share one topic space, and that space never sees the future.

**Province features, window W = the 4 quarters ending before the issue date:**

| Feature | Arm | Definition |
|---|---|---|
| `nr_volume` | raw | log(1 + articles mentioning the province) |
| `nr_count` | raw | log(1 + stress events) |
| `nr_mean` | raw | mean of max(p_harder, p_hardship) over gated articles |
| `nb_fssi` | corrected | logit((r + k·ρ)/(n + k)) − logit(ρ), with r stress events, n articles, ρ the national stress rate in the same window, k = 10 (the E142 value) |
| `nb_attention` | corrected | log(1 + n) minus the cross-province mean of log(1 + n) in the same window |
| `nb_fssi_delta` | corrected | `nb_fssi` minus its value at the same lead for the province's previous survey round (within-province variation, after Mueller and Rauh) |
| `nb_topic_0..5` | corrected | topic share among the province's gated articles, shrunk to the national share with k = 10, minus the national share |

The correction compares each province with all others in the same window. It therefore needs no long province history, which matters because the archive starts in 2012.

## 5. Models and arms

All arms use the E143 rolling origins and rows: O1 (train 2013, test 2015, 78 rows), O2 (train 2013 and 2015, test 2018, 22 rows), O3 (train all earlier, test 2019, 25 rows).

| Arm | Learner | Inputs |
|---|---|---|
| G | LightGBM (E140 `LGBAuto`, no history features) | Government indicators |
| N | LightGBM | Corrected news only |
| GN | LightGBM | Government + raw news |
| GNB | LightGBM | Government + corrected news |
| C4 | E143 hierarchical anchor + cross-fitted LightGBM | Government + earlier surveys |
| FULL | Same as C4 | Government + corrected news + earlier surveys |
| B1 PERS | Naive persistence | Previous round's `y` and its uncertainty |
| B2 LR-PSA | Soft logistic | Poverty indicators (E137 `PSA_ONLY`) |
| B3 LR-NLP | Soft logistic | Corrected news only |
| B4 LR-ALL | Soft logistic | Government + corrected news |

LightGBM settings are inherited from E140 and are not tuned. News columns are added to both the `LT` and `GBC` candidates. Monotone constraints are not used.

## 6. Evaluation

**Leads.** 1 to 8. A model is refitted at each lead with that lead's features. Labels do not change with the lead.

**Metrics, per lead and arm, on decisive rows unless stated:** accuracy with Wilson interval, precision, recall, F1, AUC-ROC with region-bootstrap interval, false-alarm rate, confusion matrix. On all rows: EB, ECE. Also by origin and by province for CALABARZON.

**Inference.** Region-cluster bootstrap (16 regions), 2000 draws, seed 145. Holm across leads 1 to 4.

**Reliability at lead h (all required):**

| Check | Requirement |
|---|---|
| R1 | Accuracy ≥ 0.75 |
| R2 | AUC ≥ 0.70 and interval lower bound > 0.50 |
| R3 | Recall ≥ 0.50 and precision ≥ 0.50 |
| R4 | EB below persistence, with the 95 % interval of the difference below 0 |
| R5 | ECE ≤ 0.10 |
| R6 | Predicts change: Spearman between predicted and measured change from the previous round, interval lower bound > 0 |

**Maximum reliable lead:** the largest h such that every lead up to h passes. It is 0 if lead 1 fails.

**Controls.**

* *Wrong-province placebo.* News columns are shuffled across provinces within each survey round, 30 draws, at lead 1. Real news must beat at least 95 % of draws before any news claim is made.
* *Coverage.* The news gain is reported by terciles of province coverage.
* *Missing data.* 20 % of input values are masked at prediction, seed 145, and the change in EB is reported.
* *Overfitting.* Training EB versus test EB per origin.

## 7. Decisions

| Result | Wording |
|---|---|
| H-N145 passes and the placebo passes | "Province-level news improved the forecast of measured provincial food insecurity at lead h." |
| Otherwise | "News was tested on measured provincial food insecurity and did not measurably improve the forecast." |
| R1 to R6 pass at h | "Reliable to lead h on development rows", never "validated" |

**Hard limits on the claim.**

* A pass here is about survey quarters only. It does not establish skill for quarters with no survey.
* Results use rows already seen by earlier studies.
* A validated forecast needs an unseen provincial round.
* The production pointer and the dashboard are not changed by E145.

## 8. External checks

* **Face validity (agreement only, never pooled).** The verified anchors are in `backend/data/e145/calabarzon_face_validity_anchors.csv`. They were read from the FNRI decks, with instrument and page. The test is direction: is each province's forecast on the same side of the national level as the measurement of the same instrument and year? HFIAS and FIES are never pooled, and FIES is never used for training.
* **No regional 2019 figure.** The national 2018-2019 ENNS deck prints no CALABARZON figure. The 2019 evidence is provincial: HFIAS and FIES for Quezon and Rizal.
* **No blind test from 2021.** The 2021 decks (Batangas, Cavite, Lucena) use FIES with 12-month recall, not HFIAS, and their values were seen on 2026-11-04 before this lock. They are agreement evidence only.
* **Later rounds.** The 2021 and 2023 rounds reviewed use FIES. An HFIAS provincial round after 2019 has not been found, so a future confirmation test for an HFIAS-trained model may have to be a FIES agreement test unless FNRI publishes HFIAS again.
