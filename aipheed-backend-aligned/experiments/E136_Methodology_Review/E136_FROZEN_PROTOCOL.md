# E136 frozen protocol: independent methodology review

**Freeze.** Written and hashed before any E136 computation (`runner/PROTOCOL_SHA256.txt`).

**Scope.** Branch `aiPHeed/corrected-data-pipeline`, start `8f5f611`. Offline only.

**Unchanged:**
- target: SWS hunger, 4 areas, 2021+;
- tolerance 1.645 × SE; 75 %; leads (`target.py`); N1–N7;
- P-DASH; sets S-U (n_obs ≥ 8) and S-E132;
- point-in-time rules.

**Disclosure.** The E131–E135 numbers of every existing candidate are known. E136's experiments are deliberately few, each answering one question. The new candidate's feature set is chosen from E133–E135 ablations on the same rows, so it is **hindsight on development data**. Its development numbers are therefore non-confirmatory, and it can only be confirmed prospectively.

## Experiments (one question each)

| # | Question | Candidate | Definition |
|---|---|---|---|
| Q1 | How hard is the task? | PERSIST | Latest published SWS value |
| Q2 | Do recent changes carry information? | **TREND-D** (new, fixed, no fitting) | y_latest + 0.5 × (y_latest − previous published quarter's value) |
| Q3 | Does a simple regularized regression generalize? | RIDGE-ALL (E131/E132) | Ridge α = 10 on history + five groups, predicting the change |
| Q4 | Is LightGBM's complexity justified? | LGBM-ALL (E131/E132) | As E131 |
| Q5 | Do the existing state-space candidates hold up? | HFM-X, SEAS-LLM | E133 / E132 |
| Q6 | Does reduced influence generalize better? | X-RED | E135 (prospective hypothesis) |
| Q7 | Does the simplest evidence-based driver model work? | **SIMPLE** (new) | HFM-NS-DES (pooled measurement-aware level, documented 2025 break, design effect) + drivers A (rice CPI q/q), E (unemployment change), N (shortage news) at prior SD 0.5. Drops C, V, aR and aP (weak or harmful in E133–E135). |
| Q8 | Is the model stable to the training start? | SIMPLE-T22 and HFM-X-T22 | Same models with training from 2022-Q1 instead of 2021-Q2 |

**Not run, with reasons:**
- **More algorithms:** E131–E135 already show that learned models overfit on 40–100 rows.
- **Regime switching:** one surge in the window.
- **Adaptive weighting:** E135 showed it fails.

## Evaluation

- **Per candidate × lead (1–4), per set:** MAE, RMSE, bias, within, coverage (where defined), terciles, sharp increases, by area, by period, with row counts. N1–N7 as in E133–E135.
- **Ridge and LightGBM** are defined only on S-E132 (≥ 20 training rows), so they are compared there.

## Recommendation rule (fixed here; E136's own, it does not replace earlier frozen selection rules)

1. **Eligibility:** the candidate must beat PERSIST on Lead-2 MAE on **both** S-U and S-E132.
2. **Ranking:** lowest mean of its Lead-2 within ranks on S-U and S-E132.
3. **Ties:** fewer estimated parameters, then lower mean Lead-2 MAE.
4. **Status:** the recommended methodology is a **prospective primary**. It is validated only by N1–N7 on ≥ 10 unseen Lead-2 quarters.
5. **Simplicity:** a more complex candidate is preferred over a simpler eligible one only if it beats it on both sets.
