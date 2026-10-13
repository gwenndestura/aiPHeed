# Model Results

Every figure is read from the approved pipeline's artifacts by
`scripts/build_results_docs.py`; nothing is typed by hand. Only the five metrics
named in Specific Objective 2 are reported.

```bash
python -m scripts.run_quarterly_pipeline --skip-collect
python -m scripts.shap_attribution
python -m scripts.face_validity
python -m scripts.build_results_docs
python -m scripts.verify_consistency
```

Data: 95 labelled province-quarters, 2020-Q2 to 2025-Q4,
class split 47 HIGH / 48 LOW (Equation 3). Model: LightGBM on Equation 5's
twelve features, tuned by 100 Optuna TPE trials on mean weighted F1 (Algorithm 4).

## 1. Maximum Reliable Lead Time (Algorithm 3)

| k (quarters ahead) | Folds | Accuracy | Precision | Recall | F1 | AUC-ROC | Meets 75%? |
|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | 7 | 0.6286 | 0.7962 | 0.6286 | 0.6652 | 0.4792 | No |

Maximum Reliable Lead Time: **0**.

## 2. Holdout evaluation (Algorithm 4)

| Metric | Value | Section 3.4.4 target |
|---|---:|---|
| Accuracy | 0.3000 | |
| Precision | 0.9125 | |
| Recall | 0.3000 | |
| F1-Score | 0.3495 | 0.75, not met |
| AUC-ROC | 0.7222 | 0.80, not met |

Cross-validation mean weighted F1 of the selected parameters: 0.7416.

## 3. Baselines (Objective 4)

| Approach | Accuracy | Precision | Recall | F1 | AUC-ROC |
|---|---:|---:|---:|---:|---:|
| **aiPHeed LightGBM (NLP + government)** | 0.5818 | 0.7453 | 0.5818 | 0.5518 | 0.6302 |
| Naive persistence | 0.8000 | 0.8080 | 0.8000 | 0.8016 | 0.8030 |
| Logistic regression, government indicators only | 0.5818 | 0.5787 | 0.5818 | 0.5801 | 0.5702 |
| Logistic regression, NLP features only | 0.5455 | 0.6029 | 0.5455 | 0.5415 | 0.6309 |
| Logistic regression, combined features | 0.5455 | 0.5489 | 0.5455 | 0.5470 | 0.5399 |
| LightGBM, government indicators only | 0.6000 | 0.6320 | 0.6000 | 0.6032 | 0.7121 |
| LightGBM, NLP features only | 0.6000 | 0.6222 | 0.6000 | 0.6040 | 0.6680 |

## 4. SHAP attribution (Research Question 1)

| Rank | Feature | Share of total attribution |
|---:|---|---:|
| 1 | Unemployment Rate | 21.9% |
| 2 | FSSI (2 Quarters Prior) | 19.9% |
| 3 | Food Stress Sentiment Index | 19.9% |
| 4 | Food CPI Growth vs Province's Recent Average | 11.7% |
| 5 | Rice Price Change | 10.8% |
| 6 | FSSI (Prior Quarter) | 9.6% |
| 7 | Climate & Hazard News Signal | 6.3% |
| 8 | FSSI Acceleration | 0.0% |
| 9 | OFW Remittance News Signal | 0.0% |
| 10 | Employment News Signal | 0.0% |
| 11 | Market & Price News Signal | 0.0% |
| 12 | Fish Kill / Aquaculture News Signal | 0.0% |

NLP features 55.7%; government indicators 44.3%;
7 of 12 features used by the model.
