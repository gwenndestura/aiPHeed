# LEAD2_MIDQUARTER_UPDATE: plan (fixed before any result)

**EXPLORATORY.** This tests the method behind the unofficial 2026-11-01 update (about 0.34) on the closed 2023–2026 Lead-2 rows. Those rows were examined before, and this is the fifth Lead-2 variant scored on them. The result is development evidence only: it cannot make Lead 2 reliable. It also changes nothing that is served, sealed or pre-registered.

## Method (M3, "mid-quarter update")

**Issue date.** For origin quarter t, the issue date is D(t) = the first day of the **second** month of quarter t+1. For example, t = 2026-Q3 gives D = 2026-11-01.

**Hunger part.** H4 at D(t): the newest SWS round published before D(t) (`LEAD2_POST_SWS_ISSUE/runner/score.h4_at`).

**Price part.** The served P0 arm, refitted walk-forward exactly as M2 (`LEAD2_POST_SWS_PRICE/runner/price_refit.py`), with one change: every origin's CPI cutoff, test and training, is the newest month available at D(t) (month M from the first day of M+2). That is month 3 of quarter t. The World Bank columns and every other input stay as served.

**Forecast.** M3 = hunger part × price part. HIGH at 0.50 (no other cutoff is tried).

## Evaluation

| Item | Rule |
|---|---|
| Rows | The 65 official Lead-2 rows, target T43c |
| Baselines | Recomputed at D(t): persistence (newest SWS and CPI), climatology, always-LOW |
| Rules | R1–R7 as frozen |
| Metrics | Accuracy, balanced accuracy, precision, recall, AUC, Brier |
| Leakage checks (stop on failure) | The CPI cutoff is available at D(t); `Data.cut` holds no later month; the SWS round used was published before D(t) |
| Compared with | P0H4, M0 and M2 on the same rows |

PLAN-SHA256: 6b5bff745874a32f1726f0cf1f86f84172ce59f81df9452e61744c752f88545d
