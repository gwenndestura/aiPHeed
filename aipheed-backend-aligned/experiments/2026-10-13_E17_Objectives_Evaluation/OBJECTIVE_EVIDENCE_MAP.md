# Objective-to-Evidence Map (E17)

**Status:**

- **Section 1** was written **before** any E17 evaluation, as the brief requires. It is frozen together with the protocol (hash in `runner/PROTOCOL_SHA256.txt`).
- **Section 2** records the outcomes. It is added after the runs and does not change Section 1.

## 1. Pre-evaluation mapping

| # | Objective (Chapter I wording, shortened; full text in `OBJECTIVES_EXTRACTION.md`) | What must be shown to fulfil it | Evidence needed | Evaluation method in E17 | Success criterion stated in Chapter I | Status before E17 |
|---|---|---|---|---|---|---|
| G | Develop, validate and deploy aiPHeed | A working system whose forecasts are validated and which is deployed | Results for Objectives 1–5 | Synthesis | None | To be determined |
| 1 | Two-tier pipeline (XLM-RoBERTa sentiment + BERTopic) producing the bias-corrected FSSI and latent risk patterns per province-quarter | The pipeline exists and produces FSSI and topic outputs for each province-quarter | Code; the produced FSSI, trigger and topic tables (eligible quarters only) | Inspect the code. Count coverage of FSSI, trigger and topic outputs per province-quarter, 2021–2025. **No accuracy test exists** (no ground truth for sentiment). | **Unspecified** | Implementation evidence exists (E1–E13 records); effectiveness unknown |
| 2-I–IV | Evaluate the proposed LightGBM model with accuracy, precision and recall, F1, AUC-ROC for HIGH/LOW province-level classification | Measured values of the four metrics for the proposed model on its province-level target | Walk-forward predictions of the current implementation's model on eligible data | Expanding-window walk-forward; confusion matrices; per-quarter results | **Unspecified** (metrics listed; no thresholds) | Earlier records (governing config: 0.818 accuracy) used a training rule that did not respect label publication, plus 2020 data. Needs re-evaluation under timing-valid rules. |
| 2-V | Performance across several lead times; the furthest horizon at which reliable forecasting is achievable | The metrics for each lead time, and a reliability judgement | Same, for lead times k = 1…8 where data permit | Same, for each k | **Unspecified.** "Reliable" is not defined. | Undetermined |
| 3 | Municipal and city rankings from **validated** province-level forecasts, using PSA poverty and population density weights | The rankings are produced as specified **and** the province forecasts they rest on are validated | Disaggregation code; LGU poverty and census inputs; Objective 2 result | Inspect the code. Analyse what drives the within-province ranking. Check the "validated" precondition against Objective 2's outcome. | **Unspecified** | Implemented (code); precondition unknown |
| 4 | Compare the proposed LightGBM model with naive persistence, PSA-only indicator, NLP-only sentiment and logistic regression baselines | The proposed model's metrics beside each baseline, on identical test origins | Walk-forward predictions of all five | Same folds; differences with quarter-cluster bootstrap intervals | **Unspecified** | Not done under these four baselines with timing-valid rules |
| 5 | Deploy a public dashboard with forecast maps and early-warning alerts; ISO/IEC 25010 evaluation with DA IV-A evaluators; face validity against FNRI NNS 2019 and 2023 CALABARZON prevalence | Deployment; survey results; comparison with NNS 2019 and 2023 figures | Deployment records; survey responses; NNS figures | Inspect records. Check whether NNS 2019 and 2023 values exist in the project. **No new survey or deployment is done.** | **Unspecified** | Unknown |

## 2. Outcomes

See `THESIS_FINDINGS_SUMMARY.md` and `REMAINING_OBJECTIVES_EVIDENCE.md`, which are written after the runs.
