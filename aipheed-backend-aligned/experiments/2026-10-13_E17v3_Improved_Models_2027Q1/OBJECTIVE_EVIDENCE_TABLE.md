# Objective-to-Evidence Table (E17 v3)

**Basis:**

- **Objectives:** Chapter I, exact text in `OBJECTIVES_EXTRACTION.md`. No other chapter was used.
- **Earlier evidence:** E13, E16 and E17 reports. Their results are **cited, not regenerated**.
- **New evidence:** E17 v3 adds required-horizon (h = 5) backtests and a 2027-Q1 research forecast.

**No numerical success criterion is invented.** Chapter I states none, and the 75% figure is not used.

| Objective | Required behaviour or result | Existing implementation and evidence | Additional experiments in E17 v3 | Status after E17 v3 |
|---|---|---|---|---|
| **General:** develop, validate and deploy aiPHeed | A working, validated, deployed system | Runs locally. Not validated (E17). Current version not publicly deployed. | None changes this | **Partially achieved** |
| **1.** Two-tier NLP pipeline → FSSI and latent risk patterns per province-quarter | Pipeline outputs per province-quarter | FSSI 96/100 and topics 96/100 province-quarters (2021–2025). Two of five triggers never fire. 69 articles behind the FSSI (E17, project record). | None | **Partially achieved** (implemented; no criterion; no validity test) |
| **2-I–IV.** Accuracy, precision and recall, F1, AUC-ROC of the proposed LightGBM model | Measured classification metrics | E17: k = 1 accuracy 0.629, F1 0.745, AUC 0.667; k = 2 accuracy 0.680 | None. The classifier cannot be run at the 2027-Q1 horizon without 2026 news inputs. | **Measured; not better than baselines** |
| **2-V.** Furthest horizon of reliable forecasting | Performance by lead time and a reliability judgement | E17: classifier evaluable at k = 1–2 only | **H, F and D at h = 5** (the 2027-Q1 horizon): 3–5 origins, exploratory; no model beats the baselines (§BACKTEST) | **Inconclusive.** "Reliable" is undefined, and no horizon is evidenced. |
| **3.** Municipal rankings from **validated** province forecasts | Rankings plus validated province forecasts | Rankings implemented; precondition unmet; static, density-driven within provinces (E17) | None | **Partially achieved** |
| **4.** Comparison with the four baselines | Model against the baselines on identical origins | E17: the LightGBM classifier does not beat persistence or the PSA-only baseline | E17 v3 compares **new continuous candidates** with carry-forward, means and zero at h = 5. None is better under the frozen rule. | **Comparison achieved; no improvement shown** |
| **5.** Public dashboard, ISO/IEC 25010 evaluation, NNS 2019 and 2023 face validity | Deployment, survey, anchor | Not deployed publicly; survey not collected; NNS 2019 and 2023 unavailable | None | **Not achieved** |

## What each kind of evidence shows

| Kind of evidence | Status |
|---|---|
| **Successful implementation** | Pipeline, classifier, disaggregation, dashboard (local), the E15 two-layer prototype, E17 v3 candidates |
| **Measured out-of-sample performance** | Yes, on previously explored 2021–2025 quarters (E13, E17, E17 v3) |
| **Improvement over a baseline** | **None established** under any frozen rule at the required horizon |
| **Evidence for the required horizon (h = 5)** | **Insufficient** (3–5 origins) |
| **Evidence for real provincial food-insecurity claims** | **None.** No independent outcome exists. |
| **Readiness for operational use** | **Not ready.** Unvalidated, with an unverified CPI timing and no reliability criterion. |
