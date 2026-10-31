# E130 SHAP explanations

## Status: not produced

SHAP explains a trained model's predictions. **E130 trained no LightGBM model:**
- the gate is BLOCKED, because no quarterly provincial reference exists;
- on the survey-year reference there are only 5 training rows, below the protocol minimum of 20.

SHAP values for an untrained or invalid model would explain nothing real, so none were computed. The brief's SHAP items cannot be produced:
- global importance;
- provincial summaries;
- group summaries;
- the Lead 1 versus Lead 2 comparison;
- examples of predicted increases and decreases;
- explanations of major errors.

## What the evidence does say (no SHAP needed)

| Question | Evidence |
|---|---|
| Is a model likely to rely on food CPI? | Yes. Provincial food CPI is the only frequent, genuinely provincial predictor. Its province deviations stay informative for about two quarters (autocorrelation 0.54). Across provinces it ranked the 2021→2023 PFDR changes (Spearman 0.90, N = 5), partly because the food threshold is priced with provincial food prices. |
| Is a model likely to rely on period markers? | Yes. 14 of 27 provincial predictors have more than 70 % of their variance in the common quarter effect. On the regional target, E128's SHAP found ONI acting as a period marker. |
| Would the other groups show? | Barely. Remittances and ONI are national. Typhoon counts are identical across provinces in 82 % of quarters. News covers Cavite four times as often as Rizal. LFS is annual. |

## Plain-language note for DA staff

When a model is trained on a valid provincial target, SHAP will show which inputs pushed each province's forecast up or down. **It shows association, not cause.** A large SHAP value for food prices would mean the model leaned on prices, not that prices caused the change.

## Fixed for a future run (protocol §5)

- TreeExplainer on every outer-fold model.
- Mean |SHAP| by feature and by trigger group, with rank stability across folds.
- Per-province summaries.
- Lead 1 against Lead 2.
- The largest predicted increases and decreases.
- The largest errors, each with its top contributors.
- A check of how much importance falls on the common-quarter features.
