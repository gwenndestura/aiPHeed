# Supplementary diagnostics — NOT part of the approved methodology

Nothing in this directory is specified by the approved thesis proposal, and
nothing here is used by the pipeline, served by the API, printed in the PDF
report, or reported in Chapter IV.

Section 3.4.4 and Specific Objective 2 define the evaluation approach: accuracy,
precision, recall, F1-score, AUC-ROC, walk-forward expanding-window
cross-validation, and the thresholds of 75% accuracy, F1 >= 0.75 and
AUC-ROC >= 0.80. That is the approved evaluation, and the thesis reports exactly
it.

These scripts were written during verification to check whether the reported
figures were fragile. They answer questions the proposal does not ask, using
methods it does not specify:

| Script | What it does | Why it is not in the thesis |
|---|---|---|
| `seed_stability.py` | Re-runs Algorithm 4 across eight random seeds | The methodology fixes one seed; multi-seed analysis is not approved |
| `significance_tests.py` | McNemar exact test and paired bootstrap against two baselines | The proposal compares metrics directly; no significance test is specified |
| `power_analysis.py` | Required sample size and minimum detectable effect | Not an approved procedure |
| `label_reference_points.py` | Majority-class rate, single-feature rules, label decomposition | The proposal names six baselines; these are not among them |
| `compare_feature_sets.py` | Model on the selection output vs on Equation 5's vector | Equation 5 fixes the model input; comparing alternatives is not approved |

They are kept because they were run and their results are real. If a reviewer
asks how much weight a single reported figure carries, the answers are here.
Using them to change a reported result, or to restate a hypothesis verdict,
would be a change to the approved evaluation methodology.

Run them from the project root, for example:

```bash
python -m scripts.supplementary.significance_tests
```
