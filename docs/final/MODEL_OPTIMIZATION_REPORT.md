# Model optimisation report

The full experiment log, with each hypothesis, result and decision, is in `docs/EXPERIMENT_REGISTRY.md` (E151–E167).

## 1. Configurations
| Model | Anchor | Learner and hyperparameters | Selection |
|---|---|---|---|
| E158 | `Hier2`: national level of the last released round + structural level + shrunk province deviation | LightGBM residual: num_leaves 4, max_depth 2, learning rate 0.02, λ 5, row/col subsample 0.8, min leaf 10, monotone signs; trees {100, 300, 600} by inner region CV | Fixed before testing |
| E164 AUTO | {H, RP, OH, RSS} | NONE / Ridge α {1, 10, 100, 1000} / ElasticNet α {0.001, 0.01, 0.1}, l1 0.5 / RF 300 trees, depth 3, leaf 20, max_features 0.3 / LightGBM as above | Inner region GroupKFold(5) on training rows, logit SSE |
| E165 | as E164 | as E164, without the test-selected consumption inputs | Inner Brier, calibration {id, lin, platt} |
| **E166** | as E164 | as E164; feature sets {GOV, FULL} × {none + 5 sources} | Inner SSE; **source chosen from training only** |
| E167 | as E166 | as E166 | Round-held-out folds when 2+ training rounds; inner Brier; calibration options |

**Training rows:**
- about 700 as-of error rows per origin;
- 1 target round (2015) at the 2018/2019 origins, and 3 at 2021.

**Class weighting:** not used. Sample weight is 1/(se² + 0.05). The HIGH line is a fixed definition. Recall was 0.84–0.92 without weighting.

## 2. What the nested selection chose
| Origin | E164 | E166 | E167 |
|---|---|---|---|
| 2018 / 2019 | OH + ElasticNet + official inputs | OH + ElasticNet + official inputs **+ consumption** | OH + Ridge + official inputs + consumption |
| 2021 | RSS + ElasticNet + all inputs | RSS + RandomForest + official inputs + palay | OH + LightGBM + official inputs + consumption |

- **Simple, regularised learners (ElasticNet, Ridge, shallow RF) won the inner validation more often than LightGBM.** Complexity did not earn its place.
- **The survey-history anchors (OH, RSS) carry most of the gain.** With E158's anchor alone (E165 S-H), the Brier is 0.163.

## 3. Why E166 improved and E167 worsened
- **E166:** consumption + ElasticNet on the own-history anchor improved 2018 and 2019 (72.7 % and 76.0 % vs E158's 63.6 % and 68.0 %). Real inputs beat shuffled ones: −0.035 [−0.063, −0.009].
- **E167:** changing only the selection score (Brier) and the fold rule moved the choice to Ridge and LightGBM. Real inputs then did **worse** than shuffled (+0.032), and consumption-only shuffling also did better (+0.021).
- **Conclusion:** the provincial signal in the inputs is **weak and selection-sensitive.** Different but equally defensible selection rules give different answers.
  - That consumption was selected in E166 is evidence it is plausible.
  - E167 shows its contribution is **not robust.**

## 4. Overfitting controls applied
- chronological rolling origin;
- inner-only selection;
- corruption leakage tests;
- shuffled-province controls;
- per-round reporting;
- nested selection (E161 72.2 %; E165 73.6 %);
- removal of test-selected features (E165);
- no tuning against the test rows after E165;
- **every protocol committed before its run.**
