# E163: master model correction. Candidates and success criteria fixed before results.

Written 2026-11-06, before any E163 candidate was run.

## Already seen (honesty statement)
- All E151–E162 results on the same 72 Lead 1 rows (2018, 2019 and 2021): E158, PERS, RP, OH, RP+R, OH+R, SS and FH.
- **No untouched evaluation period exists.** Every new result is retrospective, and any adopted candidate must be sealed for prospective scoring.
- The design below responds to diagnosed causes, not to scores:
  - E158's cross-region structural level overrides each province's observed position.
  - Survey rounds are weighted equally regardless of age.
  - The LightGBM residual adds noise and carries a common negative intercept (E161).
  - SS ignored the national decline (+10 bias).
  - Batangas 2021 was missed by −13.7: anchor 33.8 → residual −7.6 points.

## Candidates (fixed; three only)
All use only rounds released at issue `i` (RQ + 6 ≤ `i`) and the E160 `Cache` (`Hier2` fit on released rounds).

**C1 RSS (relative state space, hierarchical).** For province `k` in region `R`:
- **Relative position:** `rel = y − N[round]`, where `N` is the national level of each round.
- **Prior:**
  - Mean: the precision-weighted mean of the *other* provinces' mean `rel` in `R`. This is partial pooling to the region, not a cross-region covariate mapping. If `R` has no other province, the mean of all provinces.
  - Variance: `τ²_w + τ²_w / n_others`. `τ²_w` is the within-region between-province variance of province means, net of sampling error and floored at 0.005. Without another province, use the all-province variance.
- **Observations:** the province's own `rel`, with variance `se² + σ²`, where σ² is round noise estimated as in `Hier`.
- **Kalman local level in years:** `q` is chosen from {0, 0.005, 0.01, 0.02, 0.05, 0.1} by one-step predictive likelihood over released rounds only. Older surveys therefore carry more uncertainty, and the newest observation weighs most.
- **Forecast:** `N[last released] + m(T)`, carried flat, with state variance `v(T)`.
- **Probability:** `Φ(mu / sd)`, with `sd` = RMSE of the training as-of errors.

**C2 RSS + LightGBM residual.** C1 + `Res2(E158.COLS)` fitted on C1's training as-of errors, with the same settings as E158.

**C3 RSS + ridge residual.** C1 + weighted ridge on `E158.COLS`:
- inputs standardised with the training median and sd, missing values set to 0 after standardising;
- weights `1/(se² + 0.05)`;
- alpha from {1, 10, 100, 1000} by region GroupKFold inside the training rows;
- interval by the `Res2.scale` method on inner out-of-fold errors.

This is a regularised regression, suited to about 700 correlated training rows.

## Five-group mapping (news distributed inside groups; no sixth group)
| Group | Columns |
|---|---|
| Market | `M.GROUPS` market, plus news columns named `*_market*` |
| Climate | climate, plus `*_climate*` |
| Employment | employment and `income_growth`, plus `*_employment*` |
| Remittances | remittance, plus `*_remittance*` |
| Poverty and social vulnerability | poverty and `income_rel`, plus `*_poverty*`, plus general food-stress news (`hunger`, `net`, `intensity`, `since`, `response`, `tg_*`), plus `h2` (the SWS hunger signal) |

General food-stress and hunger signals describe food access, which belongs to social vulnerability. `gap_q` and `lead` are timing columns and belong to no group.

## Validation
- The E158 chronological protocol: ENNS2018, 2019 and 2021 at leads 1–4. **Lead 1 is primary.**
- Measures:
  - **Class:** accuracy, balanced accuracy, HIGH and LOW precision and recall, F1, AUC, Brier, calibration slope (with CI), mean absolute error in points, false-alarm rate, missed-HIGH rate, and E156 C1–C6.
  - **Ranking:** the E162 measures (concordance, Spearman, Kendall, top-1 hit, position error), the spread ratio, and per-province errors for the five CALABARZON provinces.
- **Effective sample size:** class about 46 of 72 rows (E156); ranking uses 40 pairs in 25 clusters.

## Controls (Lead 1)
1. **Province evidence held out:** C1 with the province's own observations removed (prior only).
2. **Trigger groups:** C3 with each group dropped, and with each group shuffled (seeds 1–3, permuted within survey-lead in training and test).
3. **NLP:** C3 without any news column, and with only the news columns shuffled.
4. **C2 and C3 together:** all residual inputs shuffled (seeds 1–3).
5. **Nested selection:** among {E158, C1, C2, C3}, choose by lowest Brier on 2 rounds and score on the 3rd.
6. **Leakage:** the E160 corruption test (unreleased-round `y` set to random values). Forecasts must change by < 1e-9.

## Success criteria for adopting a candidate over E158 (Lead 1)
| ID | Criterion |
|---|---|
| S1 | Brier ≤ E158's 0.1344, and the interval of the difference is not entirely above 0 |
| S2 | Calibration slope CI includes 1, **or** the slope point estimate is closer to 1 than E158's |
| S3 | False alarms ≤ E158's 15 + 2, **and** missed HIGH ≤ E158's 4 |
| S4 | Within-region concordance > 0.60 (E158), **and** its 95 % lower bound > 0.5 |
| S5 | Absolute mean signed error overall ≤ 3.9 (E158's 2.9 + 1), Luzon ≤ 5.5, and no island newly flagged BIAS |
| S6 | Concordance ≥ 0.5 in each round |
| S7 | Real − province-evidence-held-out concordance, 95 % lower bound > 0 |

**Adoption:**
- Of the candidates passing S1–S7, adopt the one with the lowest Brier.
- If none passes, **E158 remains.** The best honest candidate is reported for each objective, and nothing is deployed.
- A candidate may claim that the five groups add information only if the all-inputs shuffle for C2/C3 gives an interval of real − shuffled Brier entirely below 0. Otherwise the groups are kept in the system (the objective requires them) but reported as **contribution not demonstrated.**
- Nested selection is reported. If the nested accuracy is more than 5 points below the adopted arm's accuracy, adoption is labelled "selection-sensitive".

## 2027-Q1 display (the E162 rule, unchanged)
- Province rank 1 is shown only if the method passed S4, S6 and S7 **and** P(highest) ≥ 0.80. Otherwise the display reads "most likely highest X %", or lists provinces without ranks.
- P(highest) comes from the state variance `v(T)`, 10,000 draws, seed 163.

## LGU
LGU-v2 with the owner's 0.6/0.4 weights (decision 2026-11-06). The project holds no LGU-level climate or agricultural exposure data, and **none is invented.**

## Not allowed
- Adding candidates after results, or changing criteria, grids or seeds.
- Province-specific adjustments.
- Changing the threshold.
- Mixing HFIAS and FIES.
- Production, dashboard or API changes.
