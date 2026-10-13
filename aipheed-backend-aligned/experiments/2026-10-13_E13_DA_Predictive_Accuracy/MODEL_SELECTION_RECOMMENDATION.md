# Model Selection Recommendation (E13; updated with Amendment 1)

**Rule used.** The frozen v1 four-condition rule (`EXPERIMENT_PROTOCOL.md` §4). Amendment 1 re-applied it with added trend baselines, which can only make it stricter.

**What may be selected.** Candidates added in Amendment 1 (LightGBM) cannot be selected. The v1 version of this file is in commit `5f7765f`.

## 1. Decision by target

| Target | Best baseline | Models tested | Result | Recommendation |
|---|---|---|---|---|
| **Regional hunger** (verified timing) | Latest published value, MAE 4.77 (drift 4.89; mean 6.74) | Ridge AR(1); + regional food inflation | Both **worse** (6.57–6.58; the interval excludes 0) | **No model selected.** Use the latest published value, with its date. **No verified improvement.** |
| **Provincial food inflation F** (timing exploratory) | Carry-forward, MAE 2.44 (drift 2.47) | Ridge (2), tree, LightGBM | None better. LightGBM 2.54. No feature adds value. Under conservative timing the training mean is best. | **No model selected.** Report the latest official value. **No verified improvement.** |
| **Relative price pressure D** (timing exploratory) | Carry-forward, MAE 1.355 ("no difference" 1.369) | Ridge D; ridge D + province mean; tree; LightGBM | **B2_ridge_DP meets all four conditions** (−0.175, interval −0.287 to −0.049; Holm p 0.038; LOQO 11/11). Unchanged after Amendment 1. | **Recorded as a candidate for prospective testing, not selected for use.** It is pre-registered in E15's frozen protocol (needs at least 12 new quarters). |
| **Provincial food insecurity** | — | — | **Not evaluable** (no independent outcome) | **No model can be recommended.** |

## 2. Why B2_ridge_DP is still not selected

1. **It does not beat the simplest relative baseline from 2023-Q4 onward.** "No difference" (0) has MAE 1.287 there; B2_ridge_DP has 1.288.
2. **It is not robust to conservative timing.** With inputs at T−3 the zero baseline is best, and no model beats it.
3. **Reused quarters, and the idea came from E12** on overlapping data.
4. **Small practical gain:** 3 of 55 sign calls changed. Almost all of its gain comes from shrinking the latest deviation; the province-mean term adds −0.01 (−0.15 to +0.13).

## 3. The simplest defensible approach

| Layer | Approach |
|---|---|
| Regional | Latest published SWS value, with its date and age |
| Provincial | Latest provincial F and D, with D's size. Any forecast of D should be at most a shrinkage toward 0, labelled exploratory. |
| Accuracy claims | None about food insecurity |

**LightGBM and the 45-feature model are not recommended for any target.** With fixed settings, LightGBM was no better than ridge (D) or carry-forward (F).

## 4. Summary of the four kinds of evidence

| Kind | Status |
|---|---|
| Verified improvement in regional hunger forecasting | **No** |
| Verified improvement in provincial food-price forecasting | **No** for F. **Exploratory only** for D (meets the rule against carry-forward, but not robust). |
| Descriptive consistency with official indicators | **Limited and mixed** (6 of 8 distinguishable pairs; not validation) |
| Provincial food-insecurity prediction accuracy | **Not evaluated** (no outcome) |

**Production, the served model, the dashboard and the thesis methodology were not changed.**
