# E57 protocol: rolling-origin test of the frozen E56 model across every eligible quarter (frozen before any E57 score)

**Written:** 2026-10-18 on branch `e46-lead2-policy` at 793ff48.
**Freeze:** the SHA-256 (LF) of this file is in `runner/PROTOCOL_SHA256.txt`, committed before the prediction step.
**No tuning:** the model, search space, seed, selection rule and decision threshold are E56's (`E56_LightGBM_Optimization/PROTOCOL.md`), unchanged.

## 0. Evidence status

- All eligible target quarters (below) were examined in E43–E56.
- E56 already scored 45 of these 50 rows (primary block) and all 50 (supplementary block, accuracy 0.72).
- E57 adds no new outcome. Its contributions are:
  - a sealed, quarter-by-quarter re-execution of the procedure;
  - the evaluation the task asks for: pooled vs quarter-level results, temporal uncertainty, rising vs falling stress, early vs late periods, province discrimination, and consistency against baselines.
- **Independent evidence** can only come from the frozen 2027-Q1..Q4 forecasts.

**Seen before freezing:** only the score-free eligibility check (section 1).

## 1. Eligible origins and targets (score-free check, 2026-10-18)

- **Rolling origins:** O(t) = day 1 of quarter t+1, for t = 2023-Q4..2026-Q1.
- **Targets:** t+2 = **2024-Q2..2026-Q3**: 10 quarters × 5 provinces = 50 province-quarters. All have an observed T43 label (SWS round + complete CPI quarter).

**Unavailable quarters, with reasons:**

| Target quarters | Origins | Reason |
|---|---|---|
| 2022-Q1 | 2021-Q3 | no T43 label (no SWS round) |
| 2022-Q2..2023-Q4 | 2021-Q4..2023-Q2 | labelled, but fewer than 6 price-training quarters exist at the origin (data begin 2021; the E46/E56 minimum is 6) |
| 2024-Q1 | 2023-Q3 | 6 price-training quarters, but fewer than 6 regional hunger training pairs (E44 minimum) |
| 2026-Q4, 2027-Q1 | | outcome not yet observed: earlier forecast and prospective forecast, not scored |

## 2. Procedure at each origin (sealed before scoring)

1. **Inputs:** only data published before O(t) (`Data.cut(t)`, `cut_extra`, policy orders announced before O(t)). Labels are the PS/T43 labels of training targets ≤ t−1.
2. **Selection:** E56 nested selection over its 72 configurations (`e56_lib.tuned_forecast`), unchanged.
3. **Forecast:** p for t+2 and decision p ≥ 0.5.
4. **Seal:** `runner/e57_predict.py` writes every forecast to `sealed/predictions.csv` and its SHA-256 before any label is read. `runner/e57_score.py` refuses to run if the file or hash changed.
5. **Reproduction check:** the sealed forecasts must equal the committed E56 predictions within 1e-9. A difference is reported as a defect; nothing is substituted.

## 3. Outcome and baselines (same 50 rows, same horizon)

**Outcome:** T43 (all SWS rounds, quarter mean; E55 PROTOCOL section 2).

**Baselines and comparators:**

| Model | Specification |
|---|---|
| **Persistence** | latest T43 label known at O(t) for the province (`e55_lib.t43_last`) |
| **Majority class** | majority of all T43 labels known at O(t) (all provinces, quarters ≤ t−1, rounds posted before O(t)) |
| **Climatology** | share of HIGH among those labels, as a probability |
| **Province climatology** (diagnostic for section 5) | the province's own share of HIGH among its known labels |
| **E55-LGBM** | committed E55 predictions, all 50 rows |
| **E38** (production default) | committed E38 predictions. Its target is the thesis Eq. 3 label, **non-equivalent**. Scored against T43 only on the rows where it exists (no 2025-Q2/Q3 forecast) and labelled as such. |

**Decisions:** p ≥ 0.5, except E38, which uses its own threshold.

## 4. Metrics

**Quarter table:** for every target quarter:
- issue quarter and target;
- n;
- actual and predicted HIGH and LOW counts;
- correct and incorrect;
- accuracy and balanced accuracy;
- HIGH and LOW precision and recall;
- Brier and AUC where calculable;
- data status (OFW inputs missing at the issue date, policy, poverty availability) and deviations.

**Pooled:** the same metrics over all 50 rows.

**Quarter-level summary:**
- mean, median, minimum and maximum quarter accuracy;
- the number and share of quarters with accuracy ≥ 0.75.

**Uncertainty:**
- **quarter-cluster bootstrap** (2000 draws, seed 57): resamples whole quarters;
- **moving-block bootstrap** of consecutive quarters (block length 2, 2000 draws): respects temporal dependence.

Both are reported with the caveat that 10 quarters cannot support a dependable interval.

**Strata:**

| Stratum | Definition |
|---|---|
| Province | per province |
| Early vs late | targets 2024-Q2..2025-Q2 vs 2025-Q3..2026-Q3 |
| Food-stress direction | **rising / falling / stable**: number of HIGH provinces in the target quarter vs the latest T43 quarter known at issue (> / < / =) |
| Regional hunger direction | **up / down**: SWS H of the target quarter vs the latest posted H at issue |

These strata use outcomes only to group rows for reporting, never in a forecast.

**Calibration:** CITL, logistic slope, reliability bins.

**Consistency against each baseline:**
- per-quarter Brier wins and losses of E56, with a two-sided sign test;
- paired Brier difference with quarter-cluster CI.

**Province discrimination:**
- within-quarter AUC (pairs within a quarter);
- per-quarter Spearman correlation of p with the outcome;
- the number of quarters where all five decisions are equal;
- province mean p vs observed HIGH share;
- Kendall's W of province ranks across quarters (a high W means a static ordering);
- E56 within-quarter AUC vs the province-climatology diagnostic (does E56 add more than province identity?).

## 5. Reporting rule

**The pooled 50-row accuracy is the headline.** E56's 45-row figure (0.778) excluded 2024-Q2 only for baseline coverage. All 10 quarters are reported, including poor ones.

"Reliable for future forecasting" is stated **only if** all three hold:
- the pooled accuracy ≥ 0.75;
- the cluster-bootstrap lower bound ≥ 0.75;
- at least 75% of quarters reach ≥ 0.75.

Otherwise the report states which condition fails and why.

## 6. Not allowed

- Retuning, a different model, changed labels or thresholds, dropping quarters, or imputing outcomes.
- Data beyond 2026-10-14; pre-2021 data.
