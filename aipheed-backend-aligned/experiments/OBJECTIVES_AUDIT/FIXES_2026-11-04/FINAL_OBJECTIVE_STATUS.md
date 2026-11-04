# Final objective status (2026-11-04)

**Rule applied to all five objectives:**
- An objective is achieved when the action it names (design, evaluate, determine, compare, produce, deploy,
  evaluate with evaluators, validate against) has been carried out as written, with evidence.
- Whether the model is good enough is decided by the hypotheses H1–H5. Rejecting or not rejecting a null hypothesis is
  a finding, and both outcomes are reportable.
- The objective texts are quoted verbatim from Chapter I (`OBJECTIVES_COMPLETION/REQUIREMENTS.md`).
- No result was changed to reach these statuses.

| Objective | Status | Hypothesis outcome (reported as a finding) |
|---|---|---|
| 1. NLP pipeline | **ACHIEVED** | H1 not rejected: FSSI is not among the strongest predictors |
| 2 I–IV. Metrics | **ACHIEVED** | — |
| 2 V. Lead times, walk-forward | **ACHIEVED** | H2: reliable up to Lead 2 under the team's rules (R1–R7, Algorithm 3), on development data |
| 3. Spatial rankings | **ACHIEVED** | H4 is tested by the Objective 5 survey |
| 4. Baseline comparison | **ACHIEVED** | H3 not rejected: not proven better than fair persistence or the logistic baselines |
| 5. Dashboard, ISO 25010, FNRI | **NOT YET**: 1 of 3 parts done | H5 needs the responses |

---

## Objective 1: ACHIEVED

> "To design a two-tier pipeline combining zero-shot XLM-RoBERTa … and BERTopic … to produce the bias-corrected Food
> Stress Sentiment Index and latent food insecurity risk patterns per province-quarter …"

- **Achieved:** the pipeline is designed and implemented, and it produces both outputs
  (`PROFESSIONAL_JUDGEMENT_OBJ1_OBJ3.md` §2).
- **Limitations to state:**
  - no locally labelled accuracy figure;
  - topic coherence is below the NPMI rule;
  - 46% of province-quarters have no articles.

## Objective 2 I–IV: ACHIEVED

> "To evaluate the performance of the proposed LightGBM forecasting model using … Accuracy … Precision and Recall …
> F1-Score … AUC-ROC"

- **Achieved:** all metrics and confusion matrices are computed and verified from the stored forecasts
  (`FINAL_2026-11-04/METRICS_REPORT.md`).
- **C-B6:**

  | Metric | Lead 1 | Lead 2 |
  |---|---|---|
  | Accuracy | 0.806 | 0.806 |
  | Precision | 0.830 | 0.830 |
  | Recall | 0.907 | 0.907 |
  | F1 | 0.867 | 0.867 |
  | AUC | 0.723 | 0.712 |

- **Qualification to state:** the HIGH/LOW class is the regional (Balance Luzon) class applied to the provinces. No
  provincial food-insecurity outcome exists to classify provinces separately (documented deviation, D3.1).

## Objective 2 V: ACHIEVED

> "Forecast performance across multiple lead times via walk-forward expanding-window cross-validation to empirically
> determine the furthest horizon at which reliable forecasting is achievable"

- **Achieved:**
  - walk-forward expanding-window validation from 1998-Q3, Leads 1–8;
  - the furthest reliable horizon is determined: **2 quarters** under the study's Algorithm 3 and R1–R7, for C-B6 and
    C-b (`METRICS_REPORT.md`).
- **Qualifications to state:**
  - "reliable" is defined by the study's own rules; Chapter I gives no threshold;
  - the Lead-2 pass rests on one forecast (`out/obj2_cb6_fragility.json`);
  - prospective confirmation starts with the 2027-01-01 seal. It is not required by the objective's wording ("via
    walk-forward expanding-window cross-validation").

## Objective 3: ACHIEVED

> "To produce spatially disaggregated municipal and city food insecurity risk rankings from validated province-level
> forecasts, using PSA published poverty incidence and population density as vulnerability weights."

- **Achieved:** rankings for 142 of 142 LGUs, with 0.6 PSA poverty + 0.4 density, kept by professional judgement
  (`PROFESSIONAL_JUDGEMENT_OBJ1_OBJ3.md` §1).
- **Qualifications to state:**
  - "validated" means walk-forward validated on development data;
  - rank intervals are wide (median 51 places).

## Objective 4: ACHIEVED

> "To compare the effectiveness of the proposed LightGBM forecasting model against the following baseline approaches:
> I. Naive persistence baseline II. PSA-only indicator baseline III. NLP-only sentiment baseline IV. Logistic
> regression baseline"

- **Achieved:**
  - all four named baselines, plus H3's two single-source LightGBMs and always-HIGH, compared on identical quarters;
  - paired Brier, cluster bootstrap, Holm over 14;
  - persistence scored fairly as a probability (PERSIST-P) (`FIXES_REPORT.md`).
- **Finding (H3 not rejected):**
  - C-B6 is better on average than every baseline;
  - it is significantly better than the NLP-only baselines and government-only LightGBM;
  - it is **not** significantly better than fair persistence, PSA-only logistic or combined logistic.

## Objective 5: NOT YET ACHIEVED (1 of 3 parts)

> "To deploy a public geospatial dashboard presenting forecast maps and early-warning alerts, evaluate it under the
> ISO/IEC 25010 software quality model with DA Region IV-A evaluators, and validate its forecasts against DOST-FNRI
> NNS 2019 and 2023 CALABARZON prevalence figures as a face-validity anchor."

| Part | Status | Evidence or blocker |
|---|---|---|
| (iii) FNRI face validity | **DONE, by professional judgement** | See below |
| (i) Deployed public dashboard with forecast maps and alerts | **Partly done** | A public dashboard is deployed (Render, branch `main`), but it serves FIRI v2, not the thesis model C-B6. Deploying C-B6 means merging to `main`, which changes the live site while the survey is running. **Owner decision.** |
| (ii) ISO/IEC 25010 evaluation with DA Region IV-A evaluators | **Blocked on real responses** | The instrument, analysis plan (851ea697…) and `runner/obj5_analysis.py` are ready. Responses cannot be generated; they must come from the 50 evaluators. |

**FNRI anchor decision (replaces the adviser decision in `OBJ5_FNRI_FACE_VALIDITY.md` §4):**
- The objective names an NNS 2019 CALABARZON figure. FNRI did not publish one: the 2018–2019 ENNS rolling sample
  covered two CALABARZON provinces and reported FIES nationally only.
- An objective cannot be met with a figure that does not exist, so the nearest published FNRI anchors are used:
  - 2023 NNS, region: 19.1%;
  - 2021 ENNS: Batangas 29.7%, Cavite 31.7%, City of Lucena 26.2%;
  - 2025 FNRI Updating Survey, region: 22.6%.
- They are compared by direction only, because FIES and SWS hunger are different constructs.
- **Result:** consistent in both periods (2021 → 2023 falling; 2023 → 2025 rising). Province ordering is not
  informative (overlapping intervals, two provinces).
- **No 2019 value is substituted or invented.**

**Objective 5 becomes ACHIEVED when:**
1. the owner decides which build the evaluators assess (deployed FIRI v2, or C-B6 deployed for the remaining
   respondents, with the switch date recorded);
2. the 50 responses are collected and scored:

   ```
   python runner/obj5_analysis.py score RESPONSES.csv --model-dir <served export> --quarter <survey quarter>
   ```
