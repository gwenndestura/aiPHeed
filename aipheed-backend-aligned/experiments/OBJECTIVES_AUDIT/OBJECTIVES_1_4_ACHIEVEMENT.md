# Objectives 1–4: achievement against the thesis wording (Objective 5 set aside at your request)

## The standard used

Each specific objective (THESIS 2 (18), §1.5.2) is a **task**: design, evaluate, produce, compare.

- **An objective is achieved** when the task is carried out completely and with evidence.
- **The answers to the research hypotheses (H1–H3)** are **results** of the tasks, whichever way they come out.

A negative result ("H3 not rejected") still achieves the objective, because the objective is to compare, not to win.
This is the standard thesis distinction between an objective and a hypothesis. It is **not** a lowering of the
evidence bar: every result below is reported as measured, with its limitations.

| Obj | Thesis wording (task) | What was done (evidence) | Result (hypothesis answer) | Remaining limitation | **Achieved?** |
|---|---|---|---|---|---|
| **1** | "Design a two-tier pipeline combining zero-shot XLM-RoBERTa Filipino-English sentiment extraction and BERTopic … to produce the bias-corrected FSSI and latent food insecurity risk patterns per province-quarter from a Filipino-English news corpus" | **Tier 1:** XLM-RoBERTa zero-shot scores (verified: real model, no fallback) → bias-corrected FSSI-v3 per province-quarter with sufficiency status (`backend/app/news/pipeline_v3.py`). **Tier 2:** BERTopic, now **issue-date safe**: refitted at each origin, patterns per province-quarter (`out/obj1_topic_proportions_timesafe.csv`). Coverage audit, early-warning test, topic quality (`OBJ1_NLP_RESULTS.md`) | **H1 not rejected:** FSSI is not among the strongest predictors (≈0% SHAP; no early-warning value) | FSSI sufficient in 16.7% of province-quarters; topics descriptive only (coherence and place-name rules failed); classifier/geocoder accuracy **not yet measured** (300-item set prepared, needs the team's labels) | **Yes, as designed and produced**, with the accuracy check pending the team's labelling |
| **2** | "Evaluate the performance of the proposed LightGBM … Accuracy, Precision and Recall, F1, AUC-ROC … forecast performance across multiple lead times via walk-forward expanding-window cross-validation to determine the furthest horizon at which reliable forecasting is achievable" | C-b evaluated walk-forward from 1998, Leads 1–8, publication-date cut-offs; all five metrics plus balanced accuracy, Brier, calibration, confusion matrices, 95% CIs; Algorithm 3 (`NEWS_V2/RESULTS.md`, `OBJ2_MODEL_RESULTS.md`); five further pre-registered candidates evaluated | Lead 1 and Lead 2: accuracy 0.790, F1 0.857, AUC 0.70. **Furthest reliable horizon = 2 quarters** (75% rule). **H2 rejected** under the paper's rule | AUC below the 0.80 Algorithm 4 target; R7 (project rule) fails; Algorithm 4 blind holdout needs 2027 labels; regional, not provincial | **Yes:** the evaluation and the horizon are determined. The Algorithm 4 confirmation follows in 2028 |
| **3** | "Produce spatially disaggregated municipal and city food insecurity risk rankings from validated province-level forecasts, using PSA-published poverty incidence and population density as vulnerability weights" | All 142 LGUs ranked with 0.6 poverty + 0.4 density (PSA SAE 2021, POPCEN 2024); recomputed independently (exact); completeness verified; sensitivity, Monte Carlo rank intervals (`OBJ3_SPATIAL_VALIDATION.md`) | Rankings produced; ρ 0.65 with poverty; median 90% rank interval 51 places | The forecast is regional (validated under Algorithm 3, not per province); the province formula differs from Eq. 6 (adviser D3.1); H4 needs evaluators | **Yes, produced and verified**, subject to the adviser's choice of province formula (D3.1) |
| **4** | "Compare the effectiveness of the proposed LightGBM … against: naive persistence, PSA-only indicator, NLP-only sentiment, logistic regression baselines" | All four required baselines (plus the two LightGBM ablations of RQ3, always-HIGH and CLIM) on identical quarters and cut-offs; every baseline independently re-implemented; paired Brier tests with Holm; CIs and effect sizes (`OBJ4_BASELINE_VERIFICATION.md`, `NEWS_V2/ALIGNMENT_CB.md` §2) | Better than persistence and NLP-only (significant); **not significantly better than PSA-only and logistic regression. H3 not rejected** | 62 quarters give too little power; prospective test built (needs the commit) | **Yes:** the comparison is complete and fair |

## What stays open (and why it cannot be done by code)

| Item | Objective | Who / when |
|---|---|---|
| Labelling the 300 headlines (two annotators) | 1 (accuracy evidence) | Your team; then run `obj1_nlp.py score` |
| Province formula D3.1 and density weight D3.2 | 3 | Adviser |
| Algorithm 4 blind holdout | 2 | Sealed 2027 quarters, about 2028 (needs the commit before 2027-01-15) |
| Statistical superiority over the logistic regressions | 4 (H3) | Prospective record; not required to achieve the objective |
