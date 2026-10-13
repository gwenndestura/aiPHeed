# Reliable Lead-Time Assessment (Objective 2-V)

**What Chapter I asks for:** "to empirically determine the furthest horizon at which reliable forecasting is achievable". **It does not define "reliable."** No reliability threshold is invented here.

## 1. Lead time by lead time

| k | Test quarters | Accuracy | ≥ 0.75? (from your earlier brief; **not in Chapter I**) | Outperforms all four Chapter I baselines and the majority reference? (protocol F2) | Evidence status | Reliability |
|---|---|---|---|---|---|---|
| 1 | 7 | 0.629 | No | **No** (below persistence, PSA-only and LR on all inputs) | Evaluated; 5 LOW cases | Not determinable |
| 2 | 5 | 0.680 | No | **No** (below persistence and LR on all inputs) | Evaluated; 2 LOW cases | Not determinable |
| 3 | 3 | 0.333 | No | — | **Insufficient** | — |
| 4 | 1 | 0.600 | No | — | **Insufficient** | — |
| 5 | 1 | 0.800 | Yes, on 5 rows from one quarter | — | **Insufficient** | — |
| 6, 7, 8 | 0 | — | — | — | **Not evaluable** | — |

## 2. The three conclusions, kept separate

1. **The longest lead time reaching 0.75 accuracy.**
   - Only k = 5, with **one test quarter** (4 of 5 correct).
   - That is not evidence; it is the result of a single quarter.
   - **Among the evaluable lead times (k = 1, 2), none reaches 0.75.**
2. **The longest lead time that outperforms the relevant baselines:** **none.** At k = 1 and k = 2 the model is at or below naive persistence.
3. **The longest lead time with a defensible reliability claim:** **none can be identified**, for two independent reasons:
   - **Chapter I defines no reliability criterion.**
   - **Even with a reasonable one, the evidence is too thin.** The evaluable horizons have 7 and 5 test quarters and 5 and 2 LOW cases. Above all, the target is a **constructed label**, not a measurement of food insecurity (`TARGET_VALIDITY_AND_LIMITATIONS.md`).

**Does no horizon qualify? Yes.** On the available evidence, no lead time qualifies as reliably forecast, and none outperforms simple baselines.

## 3. What a reliability criterion would need (for your adviser)

| Element | Why it matters |
|---|---|
| A stated metric and threshold | For example: balanced accuracy or F1 ≥ a value, **and** better than persistence by a margin |
| A minimum number of independent test quarters | Provinces in a quarter share one regional value, so quarters are the unit. Each lead time needs the minimum separately. |
| A minimum number of cases in each class | With 2–5 LOW cases, LOW recall moves by 20–50 points per case |
| A target that measures what is claimed | A reliable forecast of the composite label is not a reliable forecast of food insecurity |
| New quarters | All 2021–2025 quarters have been examined. A credible claim needs quarters after 2025-Q4, scored under a separately approved protected-data procedure. |
