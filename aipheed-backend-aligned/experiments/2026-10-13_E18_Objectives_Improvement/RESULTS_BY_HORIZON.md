# E18 Results by Horizon

**Run:** `runs/20261013T065509Z` (replicate `runs/…` byte-identical). Sealed predictions are in `classification_predictions.csv` and `continuous_predictions.csv`. Every number is in `metrics.json`.

**Horizon h** = the number of quarters between the latest information and the target. **h = 3 is the 2027-Q1 horizon.** h = 1 is **not achievable in real time** for SWS, which publishes 1–15 weeks after fieldwork. It is reported as a diagnostic only.

## 1. Constructed label (HIGH if S1 > 14.6), set A (targets ≤ 2025-Q4; all arms)

| h | Test quarters | HIGH / LOW | Persistence acc / BA | Best Ch. I baseline (acc / BA) | Current LightGBM M (acc / BA / AUC) | New N1–N4 (best) | Selected | Supported? |
|---|---|---|---|---|---|---|---|---|
| 1 | 8 | 31 / 9 | 0.825 / 0.808 | PSA LR 0.850 / 0.824 | 0.825 / 0.848 / 0.824 | N1 = persistence; N4 0.675 / 0.751 | **Persistence** | No |
| 2 | 6 | 27 / 3 | 0.700 / 0.537 | PSA LR, LR-all 0.733 / 0.556 | 0.667 / 0.519 / 0.531 | N4 0.700 / 0.685 | **Persistence** | No |
| **3** | **4** | **18 / 2** | **0.850 / 0.694** | LR-all 0.850 / 0.694 | 0.650 / 0.583 / 0.528 | N1 = persistence 0.850 | **Persistence (insufficient: < 5 quarters)** | No |
| 4 | 2 | 9 / 1 | 0.800 / 0.444 | 0.700 | 0.900 / 0.500 | — | Insufficient | No |
| 5 | 1 | 4 / 1 | 0.600 | 0.800 | 0.600 | — | Insufficient | No |

**Set B** (adds the 2026-Q1 and 2026-Q2 targets; persistence and structural arms only; previously viewed):

| h | Persistence = N1 accuracy | N2 | Quarters |
|---|---|---|---|
| 1 | 0.820 | 0.800 | 10 |
| 2 | 0.775 | 0.750 | 8 |
| 3 | 0.867 | 0.833 | 6 |

**No new candidate satisfied the frozen rule at any horizon.** The **maximum supported lead time under the E18 working criterion is "none".** The binding limit is the number of LOW test cases, not accuracy.

**SOP context (six comparisons):**

- The LightGBM government-only and NLP-only ablations are in `metrics.json`.
- Neither beats persistence on accuracy.
- The NLP-only LightGBM has the highest balanced accuracy and AUC at h = 2–3, resting on 3 and 2 LOW cases.

**Province differentiation:** the mean number of distinct labels per quarter across the 5 provinces is **1.25–1.62** for every arm.

**SHAP** (mean |contribution|, LightGBM `pred_contrib`):

| Model | h = 1 | h = 3 |
|---|---|---|
| Current M | food CPI index level 0.60, commodity_livestock 0.51, rice price 0.41 | food CPI level 1.07, leafy_veg 0.61, ENSO 0.58 |
| N4 | D 1.18, H_last 0.79, F5 0.48 | unemployment 0.68, FSSI 0.40, H_last 0.34 |

**These explain models that do not beat persistence.** They are diagnostics of what the models rely on, not evidence of predictive drivers.

## 2. Continuous targets at h = 3 (2027-Q1 horizon; targets through 2026-Q2)

| Target | Origins | Kept by the frozen rule | MAE of the kept arm | Lowest-MAE arm (not selected) | Note |
|---|---|---|---|---|---|
| Regional hunger H | **9** (≥ 8) | **Carry-forward** | 5.67 | EWMA 5.63 | EWMA meets conditions 1–3 (5 of 9 wins) but fails condition 4: its advantage depends on one quarter |
| Food inflation F | 11 | **Carry-forward** | 2.98 | Ridge AR 2.78 | Beats the two mean baselines but not carry-forward (4 of 11 wins; fails conditions 2–4) |
| Relative pressure D | 11 | **Carry-forward** | 1.75 | Zero 1.21 | The ridge models beat carry-forward but not zero |

**Excluding the 2026 targets** (7–9 origins), the conclusions are the same.

**At h = 1 (diagnostic only),** EWMA (C9) and the indicator ridge (C7) pass the rule for H. **This does not validate h = 3.**

## 3. E17 v3 frozen-candidate holdout (2026-Q1, 2026-Q2; h = 5; descriptive, previously viewed)

| Target | Carry-forward MAE | Best alternative |
|---|---|---|
| H | 4.80 | Ridge H + unemployment 5.01; historical mean 5.90 |
| F | **2.58** (best) | Pooled and province mean 3.02 |
| D | 2.02 | **Zero 0.86** (best); ridge shrink 0.88 |

**The two new quarters agree with the E17 v3 development findings:** carry-forward is best for H and F, and "no difference" is best for D.
