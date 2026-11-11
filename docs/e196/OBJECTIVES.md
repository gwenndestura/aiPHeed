# aiPHeed specific objectives (Chapter I §1.5.2) against the E196 system — local only

Evidence below is from files in this repository, checked on 2026-11-11.

## Objective 1 — two-tier NLP pipeline → bias-corrected FSSI and latent risk patterns per province-quarter: **MET**

Objective wording: *"to design a two-tier pipeline … to produce the bias-corrected Food Stress Sentiment Index and latent
food insecurity risk patterns per province-quarter."*

| Required output | Evidence |
|---|---|
| Tier 1 (relevance and trigger tagging) and tier 2 (zero-shot XLM-RoBERTa scoring) | `data/news_v3/scores.jsonl`; news tagged into the five trigger categories |
| Bias-corrected FSSI and trigger signals per area-quarter | `data/e151/out/news_panel.parquet`: **8,036** stream-quarter rows (province 4,744, area 665, regional 84, national 167), with e_market … e_net, intensity and trigger shares |
| Latent risk patterns per province-quarter (BERTopic) | `data/news_v3/topic_proportions.csv`: **120 CALABARZON province-quarters × 20+ topics**; `topic_info.csv` lists the topics (e.g. rice farmers/harvest, food supply, coastal Quezon) |
| Used by the forecasting model | The live E196 model chooses the **news-inclusive feature set in all 15 of its configurations** (Leads 1–3). In the ENNS 2021 back-test, 2–5 of the 5 configurations do. These choices were made by training-side cross-validation only. |

**Honest note for the results chapter.**
- **What is not shown.** The extra accuracy from news over government data alone has not been shown to be
  statistically significant on the 72 test outcomes: shuffled-input controls scored about the same.
- **Where it belongs.** That finding is reported under Objective 4 (the NLP-only baseline). It does not change Objective
  1, which asks for the pipeline and its outputs.

## Objective 2 — evaluate LightGBM (accuracy, precision, recall, F1, AUC; furthest reliable lead): **MET**

| Lead | Accuracy | Precision (HIGH) | Recall (HIGH) | **Weighted F1** (target ≥ 0.75) | F1 (HIGH class) | AUC (target ≥ 0.80) |
|---|---|---|---|---|---|---|
| 1 | 81.9 % | 0.69 | 0.88 | **0.823** ✓ | 0.772 | 0.90 ✓ |
| 2 | 80.6 % | 0.67 | 0.88 | **0.810** ✓ | 0.759 | 0.90 ✓ |
| 3 | 79.2 % | 0.65 | 0.88 | **0.797** ✓ | 0.746 | 0.89 ✓ |
| 4 | 76.4 % | 0.63 | 0.80 | **0.769** ✓ | 0.702 | 0.88 ✓ |

- **Which F1 the target refers to.**
  - The thesis's F1 target is **weighted F1**. Algorithm 4's LightGBM target is `lightgbm_weighted_f1_target: 0.75` in
    `backend/app/ml/training/evaluator.py`, committed in the E168 release on 2026-11-08, before E196.
  - `docs/final/THESIS_MRLT_EVIDENCE_E168.md` also names weighted F1 as the objective in Algorithm 4.
  - E196 meets it at Leads 1–4. The source is `backend/data/e196/out/thesis_metrics.json`, computed as sklearn
    `f1_score(average="weighted")`.
- **Correction.**
  - Earlier E196 notes, including the E197 protocol, compared the HIGH-class F1 with the 0.75 target.
  - On that stricter, non-thesis measure, Lead 3 is 0.746.
  - Both figures are reported. No model, cut-off or prediction was changed.

- **Maximum reliable lead time: 4 quarters.** At Leads 1–4, accuracy is ≥ 75 % and significantly better than
  persistence. Sources: `data/e196/out/lead_horizon.json`, `REPORT.md`, `RELIABILITY.md`.

## Objective 3 — municipal/city rankings from validated province forecasts, weighted by PSA poverty and density: **MET**

- **How the rankings are made.** The dashboard's municipality summary reweights E196's validated provincial
  probabilities by poverty (60 %) and density (40 %) for CALABARZON's 142 cities and municipalities.
- **Labelling.** Each ranking is labelled as a reweighted provincial estimate. No municipal food-insecurity survey exists
  to validate the rankings directly.

## Objective 4 — compare with persistence, PSA-only, NLP-only and logistic regression: **MET**

| Lead | Persistence | PSA-only | NLP-only | Logistic regression | **E196** |
|---|---|---|---|---|---|
| 1 | 62.5 % | 55.6 % | 66.7 % | 61.1 % | **81.9 %** |
| 2 | 62.5 % | 55.6 % | 68.1 % | 65.3 % | **80.6 %** |
| 3 | 62.5 % | 51.4 % | 66.7 % | 54.2 % | **79.2 %** |

## Objective 5 — public dashboard, ISO/IEC 25010 evaluation with DA IV-A, NNS face validity: **IN PROGRESS**

| Part | Status |
|---|---|
| Dashboard with forecast maps and early-warning alerts | ✓ Built; serving E196 locally (http://localhost:8080) |
| Face validity against DOST-FNRI NNS 2019 / 2023 CALABARZON | ✓ Done (`FACE_VALIDITY.md`): 15/15 within the 90 % range and 15/15 correct class; 2023 direction consistent |
| ISO/IEC 25010 evaluation by DA Region IV-A personnel | ⬜ Needs real respondents. The scoring kit is ready: `docs/e196/iso25010_template.csv` and `python -m app.e196.iso25010 <responses.csv> --out docs/e196/ISO25010_RESULTS.md`. It produces item and section means, SD, verbal interpretation and a Wilcoxon test against neutral, and **refuses synthetic responses**. |
| Public (online) deployment | ⬜ Owner decision: hosting and publishing are outside the local-only rule |

**Synthetic survey responses** (e.g. `50_synthetic_aipheed_responses-1.docx` in Downloads) must not be reported as the
ISO/IEC 25010 evaluation. The objective requires an evaluation by DA Region IV-A personnel.
