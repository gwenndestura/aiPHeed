# NLP pipeline and FSSI validation (Objective 1), for the E168 system

Written 2026-11-07. Everything below was measured from existing outputs; no NLP model was refitted.

**Sources:**
- Topic quality: `python -m app.e151.topic_quality` → `backend/data/e151/out/topic_quality.json`
- FSSI audit: `backend/data/e151/out/fssi/fssi_audit.json`
- No-NLP ablation of E168: independent audit, section 5

## 1. Tier 1: XLM-RoBERTa zero-shot

| Item | Finding |
|---|---|
| Pure zero-shot output | `app/e151/score.py` runs `joeddav/xlm-roberta-large-xnli` against 10 bilingual food-event hypotheses (food access, purchasing power, supply, agricultural loss, income, climate, displacement, OFW, assistance, recovery). It stores the raw entailment logits in `data/e151/raw/events.parquet`. **This file is the pure zero-shot output.** |
| What the features use | `app/e151/labeler.py` combines three readers: the zero-shot logits, embedding similarity to an event description, and bilingual seed phrases. This is documented deviation D3. **The province-quarter event shares in E168 come from this combined reader, so they must not be described as pure zero-shot.** |
| Food stress, not general sentiment | Yes. Hypotheses are food events, and problem reporting (e.g. shortage) is kept separate from response reporting (aid, price caps). |
| Duplicates | Near-duplicate stories (cosine ≥ 0.93 within 7 days) count once (`topics.py embed`). |
| Province and date | Places are matched to PSGC; quarter assignment uses the publication date, and only stories published before the issue date are used. When a province has too few stories, an area-level value is used instead (32.5% of CALABARZON province-quarters). |
| Label check | 69% top-event agreement (Wilson 58–78%), 84% on relevant stories, 80% problem-vs-response agreement. **The reader was the system author, so this is not an independent annotation.** A second annotator is still needed: the instrument is `annotator_selection_guide.md`, and the rows are `label_check_rows.csv`. |

## 2. Tier 2: BERTopic

One BERTopic model is fitted per forecast origin, using only stories published before that origin (14 origins, 2014–2026). Each origin's topics are scored against that origin's earlier stories only.

| Metric | Mean over origins | Range | What it means |
|---|---|---|---|
| NPMI coherence (top-8 keywords) | **0.256** | 0.131–0.386 | Above 0 means the keywords co-occur more than chance; 0.1–0.3 is typical of interpretable topics. 83% of topics are above 0. |
| Topic diversity | **0.872** | 0.84–1.00 | Little keyword repetition across topics |
| Stability vs previous origin (best keyword Jaccard) | **0.476** | 0.18–0.74 | Moderate. Topics change with yearly refits, and become more stable after 2024 (0.61–0.74). |
| Off-topic topics removed | 4.2% | 0–17% | Removed by the pipeline's own XLM check |
| Outlier stories (topic −1) | about 37% | 26–45% | High, as usual for HDBSCAN on short news. Outliers still carry their Tier-1 event shares. |

**Interpretability** is not scored automatically. The keywords for each origin are in `topic_report.csv` for human review; an example is topic 0 at 2014: "typhoon, yolanda, relief, haiyan".

## 3. FSSI (Food Stress Sentiment Index)

**Definition.** FSSI = 50 + 10·z.
- z standardises bias-corrected problem stress against all province-quarters issued before 2016.
- Problem stress is the five trigger groups' event shares, weighted by how strongly each story reports a current problem.
- Each outlet is centred on its own earlier mean; values are shrunk toward the outlet norm when stories are few; each story counts once.

**Generated:** 4,368 province-quarters (`fssi_province_quarter.csv`).

**Is it an E168 input? No.** E168 uses the group-level event and topic shares (36 news columns inside the five groups), not the composite FSSI. The FSSI is a descriptive Objective 1 output.

### Why the FSSI points the wrong way in two rice shocks (diagnosis; nothing overridden)

| Quarter | Market-stress z | FSSI z | CALABARZON stories per province | Area fallback |
|---|---|---|---|---|
| 2018-Q4 rice surge | **+3.26** | −1.0 | 58 | 2 of 5 |
| 2023-Q4 rice crisis | +0.49 | −1.3 | **2.4** | 0 of 5 |

1. **The market reading did detect the 2018 surge** (z = +3.26). The composite then **averages it with four other groups**, which moved little or the other way (for example, climate −0.04 the quarter before). That cancels it out. A single-shock event is diluted by design.
2. **In 2023-Q4 coverage collapsed**, to 2.4 stories per province. Shrinkage then pulls the index toward each outlet's norm, so the crisis cannot show.
3. **Each outlet is centred on its own earlier mean.** A shock already reported in the previous quarter (the 2023 rice crisis began in Q3) is partly absorbed into that outlet's baseline.
4. The weak correlation with food CPI (within-province ρ = 0.03) is consistent with points 1–3. Food stress and food prices are related but different constructs, so a high correlation is not required.

**No correction was applied.** Re-weighting the groups or removing shrinkage now, after seeing which crisis quarters look wrong, would tune the index to known events. The brief rules that out ("do not artificially improve FSSI during known crisis periods").

A corrected FSSI needs both of these:
- a weighting rule fixed in advance (for example, the maximum group z);
- an independent reference, such as the human-annotated label set.

It would then be checked on events not used to design it.

## 4. Does NLP information help the forecast?

| Test (Lead 1, the same 72 forecasts) | Result |
|---|---|
| E168 with all news columns removed from the search (run in the audit) | Brier change 0.0000 [−0.0015, +0.0015]; accuracy 75.0% → 73.6% (1 row); AUC 0.891 → 0.889 |
| Training-only selection, 2018/2019 origins | Chose the government-only feature set (news not selected) |
| Training-only selection, 2021 origin and the 2026-Q4 issue | Chose the full set including news |
| News-only logistic baseline | Accuracy 0.639, AUC 0.703 (below E168's 0.750 and 0.891) |

**Conclusion.** The NLP signals are in the production LightGBM, inside their trigger groups. No measurable predictive gain is demonstrated on the available survey rounds. They are therefore reported as **connected but not shown to contribute**, not as a proven predictor.

## 5. Status for Objective 1

| Component | Status | Why |
|---|---|---|
| XLM-RoBERTa sentiment and events | PARTIAL | Pure zero-shot logits exist, but features use the combined reader (D3); no independent annotation |
| BERTopic | PASS (metrics now computed) | Coherence 0.26, diversity 0.87, stability 0.48; fitted before each origin only |
| Bias-corrected FSSI | PARTIAL | Produced and documented; descriptive only; fails two event face-checks, for the reasons diagnosed above |
| Province-quarter NLP indicators in LightGBM | PASS (connected); contribution not demonstrated | 36 columns in the served configuration; ablation shows no measurable gain |
