# E195: lagged-average forecasting (LAF) of E194. Fixed before the combined result was computed. Local only.

Written 2026-11-10 at the owner's request ("improve it more").

## Honesty note
- **Already seen:** the per-lead accuracies of E194, E184 and E193 at Leads 1–6.
- **Not computed before this file was written:** any lead-combined forecast.
- The rule below was fixed in advance and is applied once. No other window or weighting will be tried.

## Method
- **Same target, three issue dates.** A survey target T is forecast at Lead 1 (issued at T−1), Lead 2 (T−2) and
  Lead 3 (T−3). When the Lead-L forecast is issued, the forecasts of the same target issued 1 and 2 quarters earlier
  (Leads L+1 and L+2) already exist. Each came from a model trained only on outcomes released by its own, earlier,
  issue date.
- **No future information.** Averaging them uses nothing from the future. This is lagged-average forecasting, a
  standard ensemble technique in weather prediction (Hoffman and Kalnay, 1983).
- **E195 at Lead L** = the equal-weight mean of E194's probabilities for the same (province, survey) at Leads L, L+1
  and L+2.
- **Evaluated at Leads 1–4.** Leads 5–6 would need Leads 7–8, which have only 50 rows.
- **E184-LAF** (the same rule applied to E184 official) is reported for reference.

## Decision
- **E195 is preferred to E194 only if all three hold, at Leads 1–3:**
  - accuracy ≥ E194's at each lead;
  - Brier ≤ E194's at each lead;
  - accuracy higher at at least one lead.
- **Also reported:** McNemar and Brier CIs against E194 and against E184, the owner rule, and false alarms.
- **Scope.** Nothing is committed, pushed or staged.
