# aiPHeed: final thesis and model report

**Date:** 2026-10-20 · **Branch:** `final-aipheed-thesis-e72` (commits in `FINAL_IMPLEMENTATION_AND_TEST_REPORT.md`)

**Evidence folders** (`aipheed-backend-aligned/experiments/`):
- E70 (model improvement attempt)
- E71 (dimensional target)
- E72 (served-system audit)
- **E73 (objective remediation, independent outcome)**

**Companion documents:**
- `FOOD_INSECURITY_DIMENSIONAL_FRAMEWORK_AND_VALIDATION_PROTOCOL.md` (framework, evidence hierarchy, survey, sealing, expert review)
- `FOOD_INSECURITY_DIMENSIONAL_FRAMEWORK_AND_REDESIGN.md` (E71 detail and references)
- `FINAL_OBJECTIVES_COMPLETION_AND_MODEL_VALIDATION_REPORT.md` (E70)
- `FINAL_IMPLEMENTATION_AND_TEST_REPORT.md`

## Summary

**What aiPHeed estimates.** For each CALABARZON province, aiPHeed estimates an **exploratory, evidence-weighted food-insecurity risk index (FIRI v2)** two quarters ahead.
- Every estimate is split exactly along the food-security dimensions: access, availability and stability; utilization is not observed.
- Vulnerability, observed regional hunger and news are shown as separate roles.
- The index is not a probability and not a validated food-insecurity rate.
- City and municipal values are within-province priorities. Each one shows how stable its priority is under other weightings.

**80% Lead-2: not supported by independent evidence.**

| Target | Lead-2 result | Assessment |
|---|---|---|
| Regional SWS hunger, the outcome FIRI uses as an input | 16/17 (0.94) | Not independent |
| **OCTA hunger, independent: never used to build, tune or weight anything** | **4/8 (0.50)**; rank correlation of the level 0.73 [−0.20, 1.00] | The only genuinely unseen test; fails |
| Provincial price label (T43) | 0.72 | A price label |
| E71 dimensional target | 0.64 | Did not track outcomes |

**Objectives 1–4.** All feasible remediation was carried out (§9). Each objective now stands at "all feasible work completed". The specific external dependencies are human annotation, provincial or LGU food-insecurity outcomes, and prospective quarters. None is marked fully met, because none has the validation evidence its wording requires.

**Production default (E38) unchanged.** Nothing merged, pushed or deployed.

## Thesis readiness update (E74, branch `e74-employment-driver-audit`)

**Driver audit.** Employment is not the top driver. The calculation is correct, but the prominence is structural.
- **Where it is first:** it is the largest of the five *displayed* groups for 2027-Q1 in Cavite, Quezon and Rizal and in the region.
- **Never the largest single push:** in none of the 95 served province-quarters. Observed regional hunger pushes more in every 2027-Q1 province.
- **Reproduced exactly:** raw LFS value, percentile, weight, push, five-bar percentages (100/100 API checks), reconstruction error 5e-7.
- **Why it looks prominent:**
  - it is a national value;
  - it carries the whole household-economy weight because remittances are missing for 2026;
  - that weight is an untested equal default;
  - the five bars exclude the regional-hunger push.
- **Normalisation distortion:** the own-history percentile scored a *still-falling* unemployment rate as risk in 25 province-quarters (2024-Q4 … 2025-Q4). Without employment, 9 province-quarters would change from HIGH to LOW, none of them in 2027-Q1. This is disclosed on the cards. Changing the served index awaits your and your adviser's decision.
- **Opposite sign in the LightGBM:** its employment TreeSHAP is negative (−0.25 log-odds).

Details: `E74_EMPLOYMENT_DRIVER_AND_CALCULATION_AUDIT.md`.

**Wording fixed in thesis mode:**
- "Contributing indicators · Index contribution, not causes" replaces "Why is this province at risk? · Ranked";
- the PDF interpretation and bar text no longer call the index breakdown SHAP or a ranking;
- the ranking API no longer explains FIRI ranks with another model's SHAP;
- cards state national scope, weight basis and direction conflicts.

**Metrics.** All 13 headline confusion matrices reproduce from the sealed artifacts (`E74/out/metrics_reproduction.json`).

**Readiness:**

| Component | Status |
|---|---|
| Software | Ready: backend 574 passed / 0 failed; frontend 53; build passes; 142 LGUs consistent |
| Food-insecurity validation | **Not achieved:** independent OCTA test 4/8 |
| 80% Lead-2 | **Not demonstrated** |
| Objectives 1–4 | All feasible work completed, each with a named external dependency (`E74_OBJECTIVES_1_TO_4_REMEDIATION_REPORT.md`) |

---

## 1. Project audit (verified in code and artifacts)

| Item | Finding |
|---|---|
| Production default | E38 (`AIPHEED_LEAD2_MODEL` unset) |
| Thesis system | `AIPHEED_LEAD2_MODEL=thesis` + `AIPHEED_STRICT_MODEL=1`: FIRI v2 (pre-registered C3), with the E56-TUNED LightGBM price-pressure forecast as indicator A1 |
| Reuse | Every quarter 2021–2026-Q3 was examined in more than 30 experiments (E38–E73). No historical quarter of SWS or PSA data is held-out evidence. |
| Unseen evidence | (a) the OCTA hunger series (E73, never used before); (b) 11 sealed prospective forecast sets for 2026-Q4 / 2027-Q1 |
| Output types | **Direct outcomes:** SWS and OCTA regional hunger. **Proxy label:** T43 (= price pressure). **Contributing factors:** the dimension indicators. **Vulnerability:** poverty and density. **Exploratory estimate:** FIRI v2. **Signal:** news. **Prioritization:** the LGU values. |

## 2. Framework

FAO four dimensions plus cross-cutting vulnerability, exposure and coping. Outcomes are kept separate from contributing factors (IPC 3.1, WFP CARI). Composite construction follows OECD/JRC. Detail and references: the protocol document §1 and the redesign document §1.

## 3. Targets

| Target | Finding |
|---|---|
| T43 | Equals price pressure on 155/155 rows: the hunger gate is constant. Not food insecurity. |
| FIR71 (E71, outcome-free) | Does not collapse to price (48/90). Does not track SWS (ρ −0.21) or subsistence. |
| **FIRI v2 (served)** | Mixed. Its tracking of hunger over time comes from its observed-hunger input (H1). Without H1: ρ with OCTA 0.06 and 2/8 correct. |

**Conclusion.** No measured provincial outcome exists. The defensible output is a named proxy index with an exact dimensional explanation, plus a complete procedure (protocol §5–§7) for obtaining the outcomes it needs.

## 4. Data provenance

- Matrix and coverage: protocol §2 and redesign §2.
- New in E73: OCTA rounds in `E73/inputs/provenance.csv`. Each has URL, outlet, publication and fieldwork dates, value and source sentence: 9 rounds, 8 quarters, 2023-Q4 … 2026-Q3.
- Values available only from a derived calculation (July 2025 = 7 + 6) were not admitted.

## 5. Architecture and model selection

| Layer | Implementation |
|---|---|
| Outcome evidence | SWS (regional, in the text as "no provincial figure exists"); OCTA used for validation only |
| Dimensions | `app/ml/inference/dimensions.py`: exact re-grouping of FIRI v2 pushes; utilization "not observed" |
| Vulnerability | V1 domain; LGU weights 0.6 poverty + 0.4 density |
| Integrated estimate | FIRI v2, unchanged: pre-registered; the only candidate with any outcome agreement; exactly explainable |
| Forecast | Lead-2 FIRI v2 from information published before the issue date; E56 LightGBM inside A1 |
| Validation | E70–E73 + sealed prospective register (`E73/prospective/`) |

**Alternatives considered and not selected** (each failed its pre-registered rule):
- E56 alone (predicts price only);
- E70 A1, A2 and S0 (S0, the CPI projection alone, is as accurate as the LightGBM);
- E71 DIMFUSE, LightGBM, LR and FIR71;
- E58 timing rules (gain = 2024-Q2 only).

**A simpler alternative.** The CPI base-effect projection (S0) matches the LightGBM on the price label. If the thesis keeps the LightGBM as its proposed model, it should report that the trees add no measurable skill.

## 6. Results

### 6.1 Independent outcome: OCTA Balance Luzon hunger (E73, unseen)

The "elevated" rule (> 11%, the median of the first four rounds) was frozen before the values were read.

| Arm | Lead-2 correct / 8 | Balanced | Spearman with OCTA level [95% CI] |
|---|---|---|---|
| **FIRI v2 (served)** | **4 (0.50)** | 0.60 | **+0.73 [−0.20, 1.00]** |
| FIRI v2 without H1 | 2 | 0.27 | +0.06 |
| Latest SWS reading > 11.3 | 6 | 0.80 | +0.13 |
| Always elevated | 3 | 0.50 | — |
| E56 regional mean (n = 6) | — | — | −0.46 |

- **Concurrent SWS vs OCTA:** ρ 0.71 [−0.22, 0.99]. The two surveys agree broadly, but OCTA's area samples (n ≈ 300, ±6 pts) are noisy.
- **Why FIRI fails here:** its 0.5 cut-off calls 7 of 8 quarters HIGH, while OCTA was elevated in only 3.

### 6.2 Regional SWS outcome (non-independent), price label and FIR71

These are unchanged from E70–E72:

| Target | Lead 1 | Lead 2 | Lead 3 |
|---|---|---|---|
| FIRI v2 vs SWS | 16/18 | 16/17 | 13/16 |
| E56 on T43 | 0.85 | 0.72 | 0.62 |
| FIR71 DIMFUSE | 0.58 | 0.64 | 0.43 |

Full metric tables: E70 §6, E71 §6.2, E72 `out/regional_outcome.json`.

### 6.3 Stability across periods (E73 WS4)

| Model / period | Result | Comparators |
|---|---|---|
| FIRI v2, regional SWS, ≤ 2024-Q4 | 9/10 | Hunger reading 5/10; always-elevated 5/10 |
| FIRI v2, regional SWS, ≥ 2025-Q1 | 7/7 | Every arm 7/7 (all quarters elevated) |
| E56, T43, 2024 targets | 7/15 | Majority 7/15 |
| E56, T43, 2025–26 targets | 29/35 | Majority 25/35 |

- E56 per province: Cavite 4/10 … Rizal 10/10.
- Any skill is concentrated in one regime.

### 6.4 Furthest reliable horizon

None, on any target, under the pre-set criterion.

## 7. Leakage, overfitting, bias

- **Leakage:** corruption tests (E57/E70) changed no forecast. Seals were made before labels were read. Clean reproductions are byte-identical (E70, E71). The prospective scorer only admits outcomes published after each seal.
- **Overfitting:** reuse across more than 30 experiments; best-of-k figures (E70 0.74, E71 0.64) were not promoted; over-confidence from Lead 2 on.
- **Bias:**

| Source | Finding |
|---|---|
| News coverage | Cavite 99 vs Rizal 37 articles; Rizal has 0 in 17 quarters |
| Language | 7/695 headlines are Filipino |
| National inputs | Repeated across provinces |
| Remittances | 2026 missing |
| Lucena | Poverty value is a substitute |
| Retrospective corpus | Grows over time, which creates spurious news–price trends |
| Missing data | Missing ≠ low risk (tests) |

## 8. Explanations (E72–E73)

| Check | Result |
|---|---|
| FIRI v2 breakdown | Exact: ≤ 2e-6 internal, ≤ 5e-4 via the API. Labelled "Index contribution breakdown (not SHAP)" in the UI headings, the API (`servingModel.explanationMethod`) and the PDF in thesis mode. "SHAP" is kept where the bars are TreeSHAP (default service). |
| E56 TreeSHAP | Reconstructs the model output (`test_e56_final_model.py`) |
| Factor cards | Name each indicator's food-security dimension, its value, period and status (observed / missing / national / regional). State that contributions are "not what causes food insecurity". |
| Display defect fixed | On the contribution page, the dropdown and the chart showed different quarters in thesis mode. The default is now a quarter the dropdown offers. |
| Browser (2026-10-20) | Region 0.74, Quezon 0.72 = API. Headings, card text, LGU priority note and contribution chart verified. |

## 9. Objective status after remediation (approved wording verbatim)

| # | Approved wording | Remediation performed | Evidence | Remaining dependency | **Status** |
|---|---|---|---|---|---|
| 1 | "To design a two-tier pipeline combining zero-shot XLM-RoBERTa Filipino-English sentiment extraction and BERTopic unsupervised topic modeling to produce the bias-corrected Food Stress Sentiment Index and latent food insecurity risk patterns per province-quarter from a Filipino-English news corpus." | Validated triggers against official records. Tested the bias correction and an EB alternative. Diagnosed the corpus-growth artifact. Tested regional news value. Built the two-annotator human-validation toolkit (κ, weighted P/R/F1, Filipino stratum). Prepared the annotator files. | Climate news tracks PAGASA typhoons (ρ 0.35 [0.06, 0.60]). Market, fish-kill, employment and remittance news fail. Bias correction not validated. No forecast value. 7/695 Filipino. | Human labels for the 300-headline sample (2 annotators); a Filipino-language corpus | **All feasible work completed; external dependency (human annotation)** |
| 2 | "To evaluate the performance of the proposed LightGBM forecasting model using the following metrics: I. Accuracy … II. Precision and Recall … III. F1-Score … IV. AUC-ROC … V. Forecast performance across multiple lead times via walk-forward expanding-window cross-validation to empirically determine the furthest horizon at which reliable forecasting is achievable" | New target (E71). Independent outcome (OCTA). Stability analysis. Prospective register and scorer. Quarterly FIES survey design with scoring and tests. | All metrics on three targets; independent OCTA test fails (0.50); no reliable horizon | Provincial food-insecurity outcome (FIES survey or CBMS); ≥ 20 prospective quarters | **All feasible work completed; external dependency (outcome data, future quarters)**. The 80% goal is not supported. |
| 3 | "To produce spatially disaggregated municipal and city food insecurity risk rankings from validated province-level forecasts, using PSA published poverty incidence and population density as vulnerability weights." | Weight-sensitivity analysis. Per-LGU priority-robustness note on the map. Opt-in province band. Re-verified all 142. | Robust to 0.5/0.5 and 0.7/0.3 (ρ ≥ 0.92). Not robust to 0.8/0.2 (0.82), poverty-only (0.39) or rank normalisation (0.76). 142/142 consistent. | CBMS LGU FIES (local validation); validated province forecasts | **All feasible work completed; external dependency (local outcome)** |
| 4 | "To compare the effectiveness of the proposed LightGBM forecasting model against the following baseline approaches: I. Naive persistence baseline II. PSA-only indicator baseline III. NLP-only sentiment baseline IV. Logistic regression baseline" | Identical-row comparisons on T43 and FIR71. Holm adjustment. Sub-period and province stability. Simpler alternatives tested. | T43: credibly better only than IV. FIR71: better than none (DIMFUSE and LR beat the LightGBM). Skill concentrated in 2025–26. | Prospective quarters to confirm any ranking | **Comparison completed; superiority of the proposed model not supported** |

## 10. The 80% target: honest account

- **Pursuit.** The target was pursued through:
  - target redesign (E71);
  - three candidate arms, seven ablations and six single-group models (E70);
  - six E71 arms;
  - a new independent outcome (E73).
- **Independent result.** On the only independent outcome (OCTA, 8 unseen quarters), the served estimate scored 0.50.
- **Other figures above 0.80** rest on outcomes the model used, or on a price label.
- **Verdict: 80% Lead-2 accuracy on a defensible food-insecurity target is not demonstrated.**
- **What would resolve it:**
  - a provincial outcome measured quarterly (protocol §6: about 904 households per province per quarter);
  - about 20 or more unseen quarters scored with the sealed-forecast procedure (protocol §5).

## 11. Limitations and next steps

1. Conduct or obtain the provincial FIES outcome (protocol §6), or CBMS LGU FIES.
2. Label the 300 headlines (two annotators).
3. Run the expert/DA review (protocol §7) as part of Objective 5.
4. Score the 11 seals when the 2026-Q4 and 2027-Q1 outcomes are published (`e73_prospective.py score`).
5. **Decisions for you and your adviser:**
   - remove H1 from FIRI v2 so that SWS becomes an independent check;
   - turn on `AIPHEED_LGU_BAND=province`;
   - keep or replace the LightGBM, given that S0 performs as well.
