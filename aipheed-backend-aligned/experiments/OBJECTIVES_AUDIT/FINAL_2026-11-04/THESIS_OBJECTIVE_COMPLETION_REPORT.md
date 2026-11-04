# Thesis objective completion report (2026-11-04)

**Statuses:** NOT STARTED · IN PROGRESS · PARTIALLY ACHIEVED · COMPLETED · BLOCKED.

Nothing was committed, pushed, deployed or sealed. C-b remains the main model.

| Objective | Required evidence | Status |
|---|---|---|
| 1. NLP | Validated NLP, annotations, FSSI and topic results | **PARTIALLY ACHIEVED.** Human validation **BLOCKED** on annotators |
| 2. Forecasting | Validated model and forecast performance | **PARTIALLY ACHIEVED.** Prospective validation **IN PROGRESS** (prepared; awaits the seal and 2027 data) |
| 3. Geospatial | Complete 142-LGU implementation and approved weighting | **PARTIALLY ACHIEVED.** Implementation complete; approved weighting **BLOCKED** on the adviser |
| 4. Baselines | Fair comparison against all seven baselines | **PARTIALLY ACHIEVED.** The comparison is complete and fair; superiority is proven against 4 of 7 at both leads |
| 5. System | Working dashboard, alerts and 50-person evaluation | **IN PROGRESS.** System and alerts work; the evaluation is **BLOCKED** on the ongoing survey |

---

## Objective 1: NLP (XLM-RoBERTa, BERTopic, FSSI). PARTIALLY ACHIEVED

**Already completed** (`OBJ1_NLP_RESULTS.md`, `NLP_VALIDATION_REPORT.md`):
- XLM-RoBERTa (`joeddav/xlm-roberta-large-xnli`) outputs verified as real.
- Issue-date cut verified by perturbation.
- Time-safe BERTopic refitted at 19 origins.
- FSSI with Eq. 1 bias correction and province-quarter aggregation.
- Coverage: 296 of 695 relevant headlines name a province; Cavite has 2.7× Rizal's coverage; 46% of province-quarters
  have no articles.

**Implemented this round:** none needed for the pipeline. The annotation tooling (`obj1_annotation_v2.py`:
adjudication, κ, F1, confusion matrices) was completed and self-tested earlier today.

**Evidence:**

| Item | Result |
|---|---|
| BERTopic NPMI | −0.47 (rule > 0) ❌ |
| Place-name topics | 53% (rule < 50%) ❌ |
| Topic stability (ARI) | 0.44 ✅ |
| FSSI in forecasting | C-E2 vs C-E2-NONEWS: Brier +0.0014 / +0.0011, 0 of 62 calls changed |
| FSSI vs hunger | ρ 0.45 (p 0.19, n 10); redundant with oil and rice prices (ρ 0.76–0.78) |
| Early warning | No signal (Holm p ≥ 0.60) |

**Unfinished:** the human validation. 0 of 300 headlines are labelled, so relevance, sentiment and geocoding accuracy
are unmeasured.

**Annotation check (2026-11-04, later the same day):** you reported that both annotators had finished. The files were
checked:
- `annotation/labels_annotator_A.csv` and `labels_annotator_B.csv`: 0 of 300 labels filled; last modified 2026-11-03.
- Older workbooks in Downloads, read only:
  - `Annotation_reviewer.xlsx` (370 rows) and `annotation_reviewer_A (1).xlsx` (311 rows): blank.
  - `Annotation_reviewer_DRAFT_v2.xlsx`: Q1 filled for 370 rows, but it is **one annotator**, a **different sample** (only
    42 headlines overlap the 300) and different questions, and is marked DRAFT. Its origin (human or pre-filled) is
    unknown.
- **No agreement or XLM-R validation was computed, and no label was created.** Objective 1 human validation stays
  **BLOCKED** until the two completed 300-headline files are placed in `annotation/` (or their location is given).

**Exact actions:**
1. Two team members label `annotation/labels_annotator_A.csv` and `_B.csv` independently, following
   `ANNOTATION_GUIDE.md`.
2. Run `python runner/obj1_annotation_v2.py disagreements`.
3. A third member adjudicates.
4. Run `python runner/obj1_annotation_v2.py score`.
5. Report κ and P/R/F1 in Chapter 4.

## Objective 2: forecasting. PARTIALLY ACHIEVED

**Already completed:**
- Expanding-window walk-forward from 1998-Q3, with labels known at O(t).
- All metrics, R1–R7 and Algorithm 3 for C-b, C-E2, C-E6 and C-B6, kept as separate models.

**Best development results (62 quarters; `METRICS_REPORT.md`, every value recomputed from the forecasts):**

| | C-b (main) | C-E6 | C-B6 |
|---|---|---|---|
| Accuracy L1 / L2 | 0.790 / 0.790 | 0.774 / 0.758 | 0.806 / 0.806 |
| Balanced accuracy | 0.717 | 0.690 / 0.679 | 0.743 |
| AUC L1 / L2 | 0.702 / 0.704 | 0.720 / 0.695 | 0.723 / 0.712 |
| Brier L1 / L2 | 0.187 / 0.184 | 0.184 / 0.186 | 0.183 / 0.181 |
| ECE L1 / L2 | 0.169 / 0.152 | 0.175 / 0.108 | 0.184 / 0.169 |
| R1–R7 | R7 fails | R3, R7 fail | all pass |
| Reliable lead | 2 | 3 | 2 |

**Implemented this round: why C-B6's improvement depends on one forecast** (`runner/obj2_cb6_fragility.py` →
`out/obj2_cb6_fragility.json`):
- **The only changed call:** at origin 2018-Q3, C-b gave 0.530 and C-B6 0.458. Its targets were LOW: 2018-Q4
  (observed 9.7%) and 2019-Q1 (10.3%).
- **The rice stocks did NOT cause it:**
  - At that origin, ST1 (total stocks −8.2% y/y) has SHAP 0.000 and ST2 (NFA share −7.9 points) has −0.011.
  - Adding the two inputs changed which grid setting C-b's inner-fold selection chose: **setting 1 → setting 5**. That
    happened at 8 of 67 origins, and changed the call at only this one.
  - **The R1–R7 pass is therefore a model-selection effect, not evidence that rice stocks predict hunger better.**
- **Label noise decides R7:**
  - 13 of 62 labels lie within SWS sampling error.
  - Flipping any one of 3 (Lead 1: 2018-Q1, 2018-Q3, 2019-Q1) or 4 (Lead 2) of them would break C-B6's R7.
  - Flipping any one of 4 others would make C-b pass.
- **Conclusion:** on historical data, C-B6 and C-b cannot be told apart reliably.

**Implemented: prospective validation of C-B6** (`CE_PROSPECTIVE_ADDENDUM_1.md`, SHA-256 3cf7930e…):
- C-B6 is added to the C-E sealing procedure, registry and scorer (families P4: vs 7 baselines; P5: vs C-b).
- **Tests:** 11/11 pass, including:
  - the seal dry run at 2026-10-01, which replays C-B6 (and C-E2, C-E6) exactly;
  - the scorer's replay, which reproduces C-B6's and C-E6's historical 14-test families exactly.

**Unfinished:**
- independent prospective validation (no 2027 label exists yet);
- adoption of any candidate.

**Exact actions:**
1. Commit the code.
2. Authorize the seal (`prospective_ce/AUTHORIZATION_2027-01-01.txt`).
3. Refresh the inputs, then run `seal_ce.py --issue 2027-01-01 --seal` and `seal_next.py` (C-b) between 1 and 15
   Jan 2027.
4. Repeat every quarter. Score with `score_ce_prospective.py` once labels exist. The families need about 20 quarters.

## Objective 3: geospatial. PARTIALLY ACHIEVED

**Already completed** (`GEOSPATIAL_VALIDATION.md`):
- **Five provinces:** score = regional P × PSA 2023 poverty weight; the class always comes from the regional P;
  recomputation difference 0.
- **142/142 LGUs:** PSA 2021 SAE poverty and 2024 population density, recomputation difference 1e-16.
- Municipal scores are consistent with the provincial forecasts (each LGU = province score × within-province
  weighting).
- Every output is labelled as modelled vulnerability, not measured hunger.

**Implemented this round:** nothing new; the evidence is complete. C-B6's demo export uses the same served weighting.

**Evidence** (`LGU_WEIGHTING_ADVISER_DECISION.md`):
- **Four options compared:** served 0.6/0.4 density; poverty only; poverty + poor-people exposure; two separate
  dimensions.
  - Kendall τ vs served: 0.69–0.71.
  - Top-10 mean poverty: 19.3% (served) vs 25.3% (poverty only).
- **Uncertainty:** the median 90% rank interval is 51 places.

**Unfinished:**
- **The approved weighting:** the adviser decision D3.2 (and D3.1, the province formula).
- **Displaying the LGU rank intervals on the dashboard:** this needs a frontend change. Not done, because the dashboard
  must stay unchanged without approval.

**Exact actions:**
1. The adviser chooses option A, B, C or D.
2. If it is not A, re-export with the chosen formula and update the thesis text.
3. Approve, or decline, a rank-band display.

## Objective 4: the seven baselines. PARTIALLY ACHIEVED

**Already completed:**
- **Fair comparison:** identical origins, labels and availability rules.
- **Statistics:** paired Brier, one-sided cluster bootstrap (seed 2036), Holm over 14, CIs, effect sizes and power
  analysis.

**Evidence (proven = Holm p < 0.05):**

| Baseline | C-E6 L1 / L2 | C-B6 L1 / L2 |
|---|---|---|
| Persistence | ✅ / ✅ | ✅ / ✅ |
| LGBM government-only | ✅ / ✅ | ✅ / ✅ |
| Logistic NLP-only | ✅ / ✅ | ✅ / ✅ |
| Always-HIGH | ✅ / ✅ | ✅ / ✅ |
| LGBM NLP-only | ❌ / ❌ | ✅ / ❌ |
| Logistic government-only | ❌ / ❌ | ❌ / ❌ |
| Logistic combined | ❌ / ❌ | ❌ / ❌ |
| **Proven** | 8 of 14 | **9 of 14** |

- **All differences favour the candidates.** Better average ≠ proven.
- **Power** (`CE6_PROSPECTIVE_PREPARATION_REPORT.md` §8): proving all seven needs a Brier of about 0.07 with 62
  quarters. That is severely underpowered, though not impossible.
- **Additional data** investigated in `CE6_MODEL_IMPROVEMENT_REPORT.md` §4: rice stocks were the only valid new source.

**Unfinished:** superiority over the two logistic regressions (and LGBM NLP-only at Lead 2).

**Exact actions:**
1. Run the prospective seals every quarter from January 2027 (Objective 2, actions 1–4).
2. Score families P1/P4 at about 20 prospective quarters.
3. Do not refit on the 62 historical quarters again.

## Objective 5: system and ISO/IEC 25010 evaluation. IN PROGRESS

**Already completed:**
- **Dashboard and backend work:** 1,022 backend tests passed. The API reports the served model, plan hash and lead
  from its evaluation file.
- **Five driver groups preserved,** with contributions reflecting actual inputs. Non-inputs show "not a model input"
  (C-b, C-B6).
- **Review workflow:** forecasts are STAGED until an administrator approves.
- **Early-warning alerts (Rule 7):**
  - A regional HIGH alert is staged per forecast quarter, plus province news flags, for human confirmation.
  - No notification is ever sent automatically.
  - Tests pass (5 targeted), and the C-B6 export yields 4 staged candidates for 2027-Q1.
- **Questionnaire:** `OBJ5_ISO25010_INSTRUMENT.md`; analysis plan `OBJ5_ANALYSIS_PLAN.md` (851ea697…, fixed before
  any response).
- **Local demos:** 8081 (C-E2), 8082 (C-E6), 8083 (C-B6).

**Implemented this round:**
- **`runner/obj5_analysis.py`:** the full analysis plan.
  - validity rules (consent, DA IV-A, ≥ 80% answered);
  - item and characteristic statistics with verbal interpretation;
  - Cronbach's α and item–total r;
  - H5 one-sided Wilcoxon vs 3.40 with Holm over 3, and effect size r = Z/√n;
  - H4 province Spearman ρ, sign test and Kendall's W, plus the LGU top-10 overlap vs chance (Wilcoxon).
  - The self-test passed (random answers, temporary folder, nothing saved).
- **`obj5/item_map.json`, `RESPONSES_TEMPLATE.csv`, `RESPONDENT_TRACKING_TEMPLATE.csv`:** no personal data. The
  ongoing questionnaire was not modified.

**Unfinished:**
- the 50 DA Region IV-A responses and their analysis;
- which build the survey evaluates (deployed FIRI v2 site vs the C-b build);
- integration of a new model into the main dashboard. Not done, because no candidate meets its adoption rule.

**Exact actions:**
1. Confirm `obj5/item_map.json` against the deployed form.
2. When the survey closes, export the responses into the template.
3. Run `python runner/obj5_analysis.py score RESPONSES.csv --model-dir <served export> --quarter <survey quarter>`.
4. Code the open-ended answers with two members (κ).

---

## Files created this round

**Created:**
- `CE_PROSPECTIVE_ADDENDUM_1.md`;
- `runner/obj2_cb6_fragility.py`, `runner/obj5_analysis.py`;
- `obj5/item_map.json`, `obj5/RESPONSES_TEMPLATE.csv`, `obj5/RESPONDENT_TRACKING_TEMPLATE.csv`;
- `out/obj2_cb6_fragility.json`;
- this report.

**Updated (backups in `backup/ce_prospective_before_addendum1/`):**
- `runner/ce_prospective.py`, `seal_ce.py`, `score_ce_prospective.py`, `ce_registry.py`, `test_ce_prospective.py`;
- `prospective_ce/REGISTRY_CE.json`, rebuilt with 4 models; no seal exists.

## Verification

- **Protected files:** 200/200 unchanged.
- **Model artifacts unchanged:** C-b, C-E2, C-E6 and C-B6.
- **C-b protocol ledger:** b22faf62…, unchanged.
- **Demos:** still serving C-E2 / C-E6 / C-B6.
- **Git:** HEAD `3e15c3e`; the 14 tracked modifications are the same as before.

## Who must act

| Action | Who |
|---|---|
| Label 300 headlines; code the open-ended answers | 2–3 team members |
| D3.1 / D3.2 weighting; adoption of any candidate | Adviser |
| Commit; authorize the January 2027 seals; approve any dashboard change | You |
| Answer the ISO/IEC 25010 questionnaire | 50 DA Region IV-A personnel |
