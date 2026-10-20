# E74: Objectives 1–4 remediation report

**Date:** 2026-10-20 · **Branch:** `e74-employment-driver-audit` · **Governing protocol:** `FOOD_INSECURITY_DIMENSIONAL_FRAMEWORK_AND_VALIDATION_PROTOCOL.md`

**Status categories used below:**
- Fully fulfilled.
- All feasible work completed, external dependency outstanding.
- Still unmet after documented remediation.

None is marked fully fulfilled because code or tests exist. **Software tests show that the implementation is correct; they do not show predictive validity.**

## Objective 1

> "To design a two-tier pipeline combining zero-shot XLM-RoBERTa Filipino-English sentiment extraction and BERTopic unsupervised topic modeling to produce the bias-corrected Food Stress Sentiment Index and latent food insecurity risk patterns per province-quarter from a Filipino-English news corpus."

| Item | Content |
|---|---|
| Implemented | Relevance classifier v2; XLM-RoBERTa zero-shot intensity; syndication de-duplication; publication-date cutoff `asof(t)`; FSSI-v3 with Equation 2 bias weight; BERTopic topics per province-quarter; served in the dashboard and PDF |
| Passed independent validation | **Climate news counts vs PAGASA typhoon records:** ρ 0.35 [0.06, 0.60]; it survives normalising by corpus size (ρ 0.36) |
| Unvalidated or failed | **Market news vs PSA food CPI:** a corpus-growth time artifact; within a quarter ρ ≈ 0. **Fish-kill vs fisheries production:** fails. **Employment vs LFS:** fails. **Remittance vs BSP:** fails. **Bias correction:** Δρ +0.08 [−0.06, +0.20]; the EB alternative is not better. **No forecast value:** ablation Δ Brier ±0.002; regional news test 4/4 quarters better/worse. **Filipino coverage:** 7/695. **Corpus is retrospective:** 687/695 headlines were first seen after their issue date, so it is not real-time-available information. |
| Remediation this run | E73 independent-reference validation and its diagnosis. Two-annotator human workflow (κ, weighted P/R/F1, Filipino stratum, consensus) with a synthetic-label unit test. E74: news is described as a signal, and the employment and remittance news channels are flagged as unvalidated. |
| Remaining dependency | **Human labels** for the 300-headline sample (two annotators); a Filipino-language corpus |
| **Status** | **All feasible work completed; external dependency (human annotation)** |

## Objective 2

> "To evaluate the performance of the proposed LightGBM forecasting model using the following metrics: I. Accuracy … II. Precision and Recall … III. F1-Score … IV. AUC-ROC … V. Forecast performance across multiple lead times via walk-forward expanding-window cross-validation to empirically determine the furthest horizon at which reliable forecasting is achievable"

| Item | Content |
|---|---|
| Implemented | Walk-forward evaluation of E56 at Leads 1–3; sealed predictions; leakage tests; clean reproduction; dimensional target (E71); independent outcome (E73); prospective register and scorer |
| Reproduced in E74 | `out/metrics_reproduction.json`: all **13 headline confusion matrices** were recomputed from the sealed files and independently rebuilt labels, and equal the recorded figures. They are listed below. |

The four result families are kept separate:

| Family | Lead 1 | Lead 2 | Lead 3 |
|---|---|---|---|
| **Food-price pressure** (E56 on T43) | 51/60 = 0.850 | **36/50 = 0.720** [0.58, 0.83]; TP/FP/FN/TN 10/6/8/26 | 28/45 = 0.622 |
| **Regional hunger outcome** (FIRI v2 vs SWS > 11.3%; not independent) | 16/18 | 16/17 = 0.941 | 13/16 |
| **Dimensional proxy** (FIR71 DIMFUSE) | 32/55 | 29/45 = 0.644 | 17/40 |
| **Independent outcome** (FIRI v2 vs OCTA > 11%) | — | **4/8 = 0.500** [0.22, 0.79]; 3/6 using only directly reported rounds | — |

| Item | Content |
|---|---|
| Furthest reliable horizon | **None** under the pre-set criterion |
| Unvalidated | No provincial food-insecurity outcome exists. OCTA values are press reports, because the primary OCTA pages could not be accessed. The quarters are reused. |
| Remediation this run | Metrics reproduced independently. The price-pressure, regional, proxy and independent results are kept apart. Employment's role in both explanation methods was audited. |
| Remaining dependency | A provincial FIES outcome (protocol §6) or CBMS; about 20 prospective quarters scored by `e73_prospective.py` |
| **80% Lead-2** | **Not demonstrated** |
| **Status** | **All feasible work completed; external dependency (outcome data, future quarters)** |

## Objective 3

> "To produce spatially disaggregated municipal and city food insecurity risk rankings from validated province-level forecasts, using PSA published poverty incidence and population density as vulnerability weights."

| Item | Content |
|---|---|
| Implemented | 142 LGUs (0.6 poverty + 0.4 density, min-max within province); map, API, PDF; a per-LGU priority-robustness note; opt-in province band |
| Passed checks | 142/142 unique, finite and mapped; ranks monotone; served values unchanged after E74 (`obj3.py`, three quarters) |
| Unvalidated | No municipal outcome. Robust to 0.5/0.5 and 0.7/0.3 (ρ ≥ 0.92), not to 0.8/0.2, poverty-only or rank normalisation. The Lucena poverty value is a substitute. Province estimates are unvalidated. |
| Remediation this run | E74: the ranking API's reasons now use the served index's dimensions instead of another model's SHAP |
| Remaining dependency | CBMS 2022/2024 FIES by LGU |
| **Status** | **All feasible work completed; external dependency (local outcome)** |

## Objective 4

> "To compare the effectiveness of the proposed LightGBM forecasting model against the following baseline approaches: I. Naive persistence baseline II. PSA-only indicator baseline III. NLP-only sentiment baseline IV. Logistic regression baseline"

| Item | Content |
|---|---|
| Implemented | Identical-row comparisons on T43 (E70) and FIR71 (E71); Holm adjustment; sub-period and province stability (E73) |
| Result | **On T43:** credibly better only than IV (combined LR, AUC < 0.5). **On FIR71:** no credible advantage over any baseline; DIMFUSE and LR beat the LightGBM. **Stability:** skill is concentrated in 2025–26. **Simpler model:** the CPI projection alone matches the LightGBM. |
| Remediation this run | E74 shows that the LightGBM's employment input has a negative TreeSHAP (−0.25 log-odds) while the index's employment indicator is positive: a coherence issue to report beside the comparison |
| Remaining dependency | Prospective quarters to confirm or overturn the comparison |
| **Status** | **Comparison completed; the proposed model's superiority is not supported** |

## What this run changed (E74)

| Area | Change |
|---|---|
| Driver language | Neutral wording in the left panel ("Contributing indicators · Index contribution, not causes"), the PDF interpretation, the PDF bar text and the ranking API |
| Factor cards | National scope, weight basis and direction-conflict notes |
| Province summary | The largest single push is named |
| Served values | None changed. Thesis-mode default unchanged; production default (E38) unchanged. |
