# E9: Model Selection and Justification

## 1. What the frozen rule selected

**Rule** (`03_FROZEN_PROTOCOL.md` §7; selection quarters 2023-Q4 to 2024-Q4 only): move from the simplest arm to the next only if its MAE is ≤ 0.90 × the current arm's and it is better in ≥ 3 of 5 quarters.

**Result: M1 core LightGBM** (`last_published_stress`, `sws_hunger`, `sws_change`).

| Comparison | MAE ratio | Quarters better |
|---|---|---|
| M1 vs carry-forward (B1) | 0.858 | 4/5 |
| M2 vs M1 | 1.179 | 2/5 |
| M3 vs M1 | 1.008 | 2/5 |

M2 and M3 did not qualify.

## 2. What the evidence supports

| Question | Answer | Evidence |
|---|---|---|
| Does M1 beat carry-forward? | **Yes, consistently but modestly** | MAE −0.68 points (bootstrap 95% interval −1.11 to −0.20; 7 quarter clusters); lower in 6 of 7 quarters, including both final quarters |
| Does M1 beat the simple regional rule (B2) or the Equation 3 origin rule (B3)? | **No** | M1 − B2 = +0.07 [−1.10, 1.78]; M1 − B3 = −0.01 [−1.09, 1.53]. **In the final period M1 is worse** (5.87 vs 4.10 and 4.25). |
| Do provincial indicators (M2) or national indicators (M3) add value? | **No reliable incremental value** | M2 is worse than M1 overall. M3 ties M1 in selection and is worse in the final period. Both overfit (training MAE 1.3–1.5 vs test 4.9–5.2). |
| Does ML differentiate provinces? | **No.** It collapses provincial differences. | M1 spread 0–2 points vs true 6.5–14.7 from 2024-Q2. Ranking agreement: M1 0.536 vs B1/B3 0.614. |
| Is the HIGH/LOW accuracy informative? | **No** | 33/35 outcomes are HIGH; "always HIGH" scores 0.943. Balanced accuracy rests on 2 Quezon rows. |

## 3. Decision and recommendation

1. **Protocol-selected forecaster: M1 core LightGBM** for the next-quarter S1 *regional stress level*. This is consistent with LightGBM as the primary model family. **Its demonstrated value is limited to beating carry-forward.** It shows **no advantage over the simple Equation 3 origin rule** (latest published SWS + 2 × latest published provincial gap).
2. **No ML advantage is claimed.** The evidence says ML, at this sample size (7 test quarters, about 7 independent observations), does not improve on the transparent S1 rule.
3. **Provincial differences should be shown from the S1 provincial component** (relative food-price pressure, as published), as E6 designed ("supporting indicators"). They should not come from the ML forecast, which does not preserve them.
4. **No model is promoted.**
   - The served M6 artifact, production `backend/`, thresholds, dashboard classifications and deployment are **unchanged**.
   - Any change of the served model, or of the threshold displayed (τ0 vs 14.345), is a separate decision for you and your adviser.
5. **The status of M1 is exploratory.** The test quarters were reused across E1–E7, and the inputs are proxy-dated.
