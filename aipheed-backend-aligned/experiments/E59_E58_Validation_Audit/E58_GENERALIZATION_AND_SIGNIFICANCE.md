# E58 generalization and statistical significance

**Sources:**
- `runner/a3_evaluate.py` → `out/evaluation.json` (paired tests, bootstraps);
- `runner/a5_sensitivity.py` → `out/sensitivity.json`.

**How dependence is handled:**
- Quarter-cluster bootstrap with 4000 draws: whole quarters are resampled.
- Paired tests are reported both at row level (McNemar) and at quarter level (sign test).
- Row-level tests overstate the evidence, because the 5 provinces of a quarter share regional hunger and national inputs.

## 1. Paired comparisons (same 50 rows)

| Comparison | Row level (McNemar exact) | Quarter level (sign test on quarter accuracy) | Paired Brier, EW − other [95% CI] |
|---|---|---|---|
| E58-EW vs E56 | 4 vs 1 discordant, **p = 0.375** | 1 better, 0 worse, 9 ties, **p = 1.0** | −0.032 [−0.102, +0.006] |
| E58-EW vs price projection rule | 3 vs 1, p = 0.625 | 2 better, 1 worse, 7 ties, p = 1.0 | −0.006 [−0.037, +0.025] |
| E58-EW vs persistence | 17 vs 6, p = 0.035 | 6 better, 3 worse, 1 tie, p = 0.51 | – (persistence has no probability) |
| E58-EW vs majority class | – | 4 better, 2 worse, 4 ties, p = 0.69 | −0.178 [−0.353, −0.009] |
| E58-EW vs climatology | – | – | −0.123 [−0.256, −0.002] |

**Reading:**
- **Against E56 and the projection rule:** no difference is statistically supported.
- **Against persistence:** the row-level McNemar result (p = 0.035) is not confirmed at quarter level (p = 0.51), so it should not be claimed as significant.
- **Against majority class and climatology:** the Brier advantage just excludes 0 under the quarter bootstrap. This is the only supported comparative claim, and its upper bounds sit close to 0.

## 2. Uncertainty of the headline figures (quarter-cluster bootstrap 95%)

| Model | Accuracy | HIGH recall | Onset recall |
|---|---|---|---|
| E58-EW | 0.70–0.86 | 0.50–1.00 | 0.14–1.00 |
| E56 | 0.58–0.86 | 0.20–0.89 | 0.00–0.86 |
| Price projection rule | 0.68–0.80 | 0.50–1.00 | 0.14–1.00 |

**Onsets at episode level:**

| Episode | E58-EW warned | E56 warned | Projection warned |
|---|---|---|---|
| 2024-Q2 | 4 of 4 | 0 of 4 | 4 of 4 |
| 2024-Q4 | 1 of 3 | 1 of 3 | 1 of 3 |
| 2025-Q2 | 2 of 2 | 2 of 2 | 2 of 2 |
| 2026-Q2 | 0 of 1 | 0 of 1 | 0 of 1 |

E58-EW differs from E56 in **one episode**. With 4 episodes, no rate of early-warning detection can be estimated with useful precision.

## 3. Robustness checks requested

| Check | Result |
|---|---|
| 2024-Q2 separately | EW 0.8 (4/4 onsets) vs E56 0.2 (0/4). Excluding 2024-Q2: **EW = E56 = 0.778**, 3 of 6 onsets each. |
| Each province | EW accuracy 0.5 (Cavite) to 0.9 (Quezon, Rizal); 10 rows each, too few for province-level inference. |
| Rising vs stable / falling | Rising: EW 0.733 vs E56 0.533 (the difference is the 2024-Q2 rows). Stable / falling: EW = E56 (0.80); always-LOW reaches 0.84 in falling quarters. |
| **Data timing (S1)** | If E56 had been issued just after the next SWS round was posted (e.g. 2024-01-23 instead of 2024-01-01), its hunger gate at 2024-Q2 would have been 0.89 instead of 0.21. **E56 alone would score 0.78 with 7/10 onsets, identical to E58-EW.** EW's gain is what a three-week-later issue date gives the existing model; it is not new predictive information. |
| Missing data / round definition (S2) | A hunger gate from all SWS rounds (approved + supplementary): 0 decisions change. Remittances are complete at all evaluated origins (missing only at the 2026 issue dates). |
| EW vs the simpler projection rule | Indistinguishable (above). The projection rule uses no LightGBM. |

## 4. Generalizability

**The evidence covers one hunger regime.** All 10 evaluable quarters fall after the 2023-Q4 hunger regime change, with hunger above the threshold in every one.

**Behaviour in a low-hunger regime is untested on outcomes.** In 2021–2023, 24 of the 29 price-pressure province-quarters were not T43 HIGH, so EMERGING warnings would mostly be false alarms in such a period.

**Every evaluated quarter was used in model and rule design** (E43–E58). No untouched historical period exists. The only independent evidence will be the frozen 2027 forecasts.

**Sample size needed:** about 16 quarters if the true accuracy were 0.85, or about 62 quarters at 0.80 (E55 `tables/sample_size.json`, per-quarter SD 0.20).

## 5. Verdicts

| Claim | Verdict |
|---|---|
| Statistical support for "E58-EW is better than E56 / the projection rule" | **Not supported** |
| Statistical support for "better than majority class / climatology" | **Partially supported** (Brier only, CI upper bound close to 0) |
| Generalizability beyond 2024-Q2..2026-Q3 | **Not supported** (one regime; design-informed quarters); **Pending** prospective scoring |
