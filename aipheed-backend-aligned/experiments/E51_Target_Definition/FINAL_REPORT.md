# E51: target-label saturation and a defensible Lead-2 target

**Branch:** `e46-lead2-policy`, from 8def3a3.
- **Protocol** (frozen before scoring): commit c3f8334.
- **Deviation D-1:** commit 8f166c4, made after a run error and before any metric.
- **Run:** `runs/20261017T131027Z`, plus a repeat.

**Unchanged:** production default (E38), frozen forecasts, serving code.

## Direct answers

| Question | Answer |
|---|---|
| Why does the thesis target become overwhelmingly HIGH? | **A real level shift in SWS hunger, judged against one threshold.** S1 = H + 2D, and D averages zero across the five provinces, so each quarter's mean S1 is exactly the SWS hunger value. 70% of S1's variance is between quarters (regional hunger), 30% between provinces. Hunger roughly doubled in 2024–2026 (mean S1 about 11 → 20–21). Any single threshold, whether the global median (15.47) or E38's trailing median, makes almost every recent row HIGH: global 40/45 rows in 2024–2026 vs 7/50 in 2021–2023; trailing 92.5% HIGH since 2024. There is no calculation or alignment defect: S1 − 2D equals the published SWS H in all 19 quarters. |
| Which target is most defensible? | By the score-free criteria, two targets meet all five (relevance, provincial content, recent balance, as-of computability, ≥ 8 evaluation quarters): **PS** (provincial food-price pressure, observed from PSA CPI) and **RQ** (relative composite stress: S1 above the other provinces' median that quarter). Both need adviser approval. **PS is the recommended exploratory target:** an absolute, observable condition with fixed 2021–2022 reference thresholds. RQ is relative by construction (always 2 of 5 HIGH) and no model forecasts it well. Regional hunger (SWS) should be reported as its own observed indicator, not folded into a provincial label. |
| Does the best candidate meet 75% Lead-2 with meaningful discrimination? | **On PS, yes in development:** E46's price component (I7's P(price signal) ≥ 0.5) scores **0.760** accuracy (date CI 0.66–0.86), balanced **0.752**, HIGH recall **0.72**, LOW recall **0.78**, Brier **0.190**, AUC **0.797**. That is on **10 independent quarters, 50 rows**, and it beats persistence (Brier 0.380), always-LOW (0.360) and always-HIGH (0.640). **No candidate meets it on the thesis label, T43, RQ or YW.** |
| Does it outperform the baselines on genuinely held-out quarters? | **No held-out evidence exists.** E46's price component was designed in E46/E47 while examining these same quarters (PRICE label diagnostics), so 0.760 is development evidence, not independent validation. The frozen 2027-Q1..Q4 forecasts are the only held-out test. |
| Ready for experimental decision support? | **Only as an experimental indicator of food-price pressure, after adviser approval of PS as a target,** and labelled as such: it is not food insecurity and not hunger. Its probability (I7's P(price signal)) already exists in the E46 record. It needs further work before any production use: prospective scoring, adviser sign-off. |

## 1. Label audit

| Check | Result |
|---|---|
| S1 composition | quarterly mean of S1 = SWS H exactly (D sums to zero across provinces) |
| Alignment | S1 − 2D = published SWS H, 19/19 quarters, difference 0.0 |
| Variance | 70% between quarters (regional), 30% within quarters (provincial price deviation) |
| Level shift | mean S1: 2021 11.6, 2022 10.9, 2023 11.2, 2024 19.6, 2025 20.4, 2026 21.1 |
| Cause of imbalance | a real indicator change plus a single threshold across a level shift; not a defect |

## 2. Candidate targets and temporal prevalence

HIGH rows / rows by year:

| Target | Meaning of HIGH | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 | HIGH share 2024–26 | Within-quarter variance share |
|---|---|---|---|---|---|---|---|---|---|
| EQ3-G (thesis, global median) | composite above the whole-period median | 2/15 | 3/15 | 2/20 | 17/20 | 9/10 | 14/15 | 0.889 | 0.34 |
| EQ3-T (thesis, trailing, E38) | composite above the recent median | 3/15 | 7/15 | 11/20 | 19/20 | 9/10 | 9/10 | 0.925 | 0.58 |
| T43 (E43/E46) | hunger > 11.3 AND provincial price stress | 2/15 | 0/15 | 3/20 | 8/20 | 4/10 | 1/15 | 0.289 | 0.47 |
| **PS** | provincial food-price pressure (CPI only) | 11/20 | 6/20 | 17/20 | 8/20 | 9/20 | 1/15 | 0.327 | 0.45 |
| **RQ** | composite above the other provinces' median that quarter | 8/20 | 8/20 | 8/20 | 8/20 | 8/20 | 6/15 | 0.400 | 1.00 |
| YW | composite worse than a year earlier | – | 7/15 | 8/15 | 20/20 | 5/10 | 4/5 | 0.829 | 0.56 |

**Criteria** (C1 relevance, C2 within-quarter share ≥ 0.25, C3 recent balance between 0.25 and 0.75, C4 as-of computable, C5 ≥ 8 evaluation quarters):

| Target | Result | Failing criteria |
|---|---|---|
| EQ3-G | fails | C3, C4 (the global median uses future quarters) |
| EQ3-T | fails | C3 |
| T43 | fails | C5 (7 quarters) |
| **PS** | **passes all** | – |
| **RQ** | **passes all** | – |
| YW | fails | C3, C5 |

**Approvals needed:** adviser approval of PS (and/or RQ) as the provincial forecasting target, and of presenting SWS hunger as a separate regional observed indicator.

## 3. Reproductions (section 6)

All from committed predictions, exact:

| Result | Accuracy | AUC | Brier | Baselines |
|---|---|---|---|---|
| E36, **lead 1** | 53/65 = 0.815 | 0.850 | 0.154 | persistence 57/65 = 0.877 (Brier 0.123); always-HIGH 0.815 |
| E38, **lead 2** | 39/55 = 0.709 | 0.655 | 0.200 | persistence 0.800; always-HIGH 0.891 (Brier 0.109) |
| E46 I7, lead 2, T43 | 0.800 (28/35; 9 HIGH) | | | |

- **E36** is a lead-1 (one-quarter-ahead) result and does not beat persistence. Its protocol is nested and uses prior dates only.
- **E38** is the thesis horizon. Same nested protocol, but worse than both baselines.
- **E46 I7** was designed after examining those quarters.
- **Horizon:** one-quarter-ahead results are not used for the Lead-2 objective.

## 4. Lead-2 comparison per target

Identical rows within each target. Accuracies are not comparable across targets.

**PS** (with E46: 10 quarters 2024-Q2..2026-Q3 including 2025-Q2/Q3, 50 rows, 18 HIGH):

| Arm | Accuracy | Balanced | Rec H | Rec L | Prec | F1 | Brier | AUC | TP/TN/FP/FN |
|---|---|---|---|---|---|---|---|---|---|
| **E46 price component** | **0.760** (0.66–0.86) | **0.752** | 0.72 | 0.78 | 0.65 | 0.68 | **0.190** | 0.797 | 13/25/7/5 |
| LGBM (E38 procedure on PS) | 0.460 | 0.578 | 1.00 | 0.16 | | | 0.333 | 0.601 | 18/5/27/0 |
| LR | 0.440 | 0.538 | 0.89 | 0.19 | | | 0.402 | 0.639 | 16/6/26/2 |
| Persistence | 0.620 | 0.630 | 0.67 | 0.59 | | | 0.380 | 0.630 | 12/19/13/6 |
| always-LOW | 0.640 | 0.500 | | | | | 0.360 | | 0/32/0/18 |
| always-HIGH | 0.360 | 0.500 | | | | | 0.640 | | 18/0/32/0 |

E46 by quarter: 2024-Q2 0.8, 2024-Q3 1.0, 2024-Q4 0.6, 2025-Q1 0.6, 2025-Q2 0.6, 2025-Q3 0.6, 2025-Q4 1.0, 2026-Q1 1.0, 2026-Q2 0.6, 2026-Q3 0.8. It meets the PROTOCOL §5 rule.

On all 13 PS quarters (65 rows; E46 is not available before 2024-Q2): LGBM 0.446, LR 0.400, persistence 0.600, always-LOW 0.600.

**RQ** (13 quarters, 65 rows, 26 HIGH):

| Arm | Accuracy | Balanced | Rec H | Rec L | Brier | AUC |
|---|---|---|---|---|---|---|
| LR | 0.631 | 0.590 | 0.38 | 0.80 | 0.252 | 0.59 |
| LGBM | 0.600 | 0.571 | 0.42 | 0.72 | 0.253 | 0.59 |
| Persistence | 0.538 | | | | | |
| always-LOW | 0.600 | | | | 0.400 | |

Not accepted.

**EQ3-T** (thesis, 11 quarters, 55 rows, 49 HIGH):

| Arm | Accuracy | Balanced | Rec H | Rec L | Brier |
|---|---|---|---|---|---|
| LR | 0.818 | 0.752 | 0.84 | 0.67 (4/6) | 0.189 |
| LGBM (E38) | 0.709 | 0.544 | | | |
| Persistence | 0.800 | | | | |
| always-HIGH | 0.891 | | | | 0.109 |

LR's Brier (0.189) is worse than always-HIGH's (0.109), and there are only 6 LOW rows, so LR is not accepted.

**EQ3-G** (11 quarters, 42/55 HIGH):

| Arm | Accuracy | Balanced |
|---|---|---|
| Persistence | 0.673 | 0.706 |
| LGBM | 0.545 | |
| LR | 0.509 | |
| always-HIGH | 0.764 | |

Not accepted.

**T43** (7 quarters, 35 rows, 9 HIGH):

| Arm | Accuracy | Balanced | Rec H | Brier |
|---|---|---|---|---|
| E46 | 0.800 | 0.684 | 0.44 | 0.174 |
| LGBM | 0.371 | | | |
| LR | 0.257 | | | |
| always-LOW | 0.743 | | | |

Not accepted.

**YW** (6 quarters, 24/30 HIGH): every model is below always-HIGH (0.800).

## 5. Data availability and leakage

| Source | As-of rule |
|---|---|
| Features | E38's (SWS posted before the origin; CPI months 1–2 of t; E47 audit for E46) |
| Labels | PS/T43 use only CPI and SWS published before the origin (exported with `available_labels` / CPI cut); RQ and YW from S1 and D of quarters ≤ t−1 |
| Training rows | E38's posting rule (a limitation for the CPI-only targets) |
| EQ3-G | its global median uses future quarters (fails C4) |

Thresholds are chosen inside training only:
- E38's nested inner rule, with deviation D-1 (a symmetric guard when prior dates hold fewer than 3 HIGH rows);
- LR at 0.5;
- E46 at its frozen 0.5.

## 6. Changes implemented

- **New in the E51 folder:** protocol, deviation D-1, label export, comparison script, tests, runs, this report.
- **No serving, model, frontend or frozen-artifact change.** E50's market attribution is untouched; its consistency tests still pass.

## 7. Tests and live system

| Suite | Result |
|---|---|
| E51 tests (`tests/test_e51.py`: protocol freeze, CPI labels and as-of persistence, S1 = SWS H + 2D alignment, RQ 2-of-5 balance, label override, metrics and acceptance rule) | **4 passed** |
| Backend | **368 passed, 18 skipped** (unchanged code since E50) |
| Frontend | **45 passed** |
| Live system | unchanged from E50 (`e46` API on 8001, dashboard on 8082) |

## 8. Limitations and decisions for the adviser / DA IV-A

1. **Approve a provincial target:**
   - PS (food-price pressure, observed);
   - RQ (relative stress);
   - or keep the thesis label, accepting that it is saturated in 2024–2026.
2. **Report SWS hunger** as a separate regional observed indicator.
3. **Accept** that the only independent test is prospective (2027-Q1..Q4), and that every historical figure here is development evidence.
4. **The non-market triggers** remain national or sparse (E47), so province-specific signal comes almost only from prices.

## 9. Files and hashes

**Folder:** `aipheed-backend-aligned/experiments/E51_Target_Definition/`
- `PROTOCOL.md`, `DEVIATIONS.md`
- `runner/e51_export.py`, `runner/e51_compare.py`
- `data/labels_cpi.csv`, `data/persistence_cpi.csv`
- `tests/test_e51.py`
- `runs/` (`aborted_20261017T130911Z`, `20261017T131027Z`, plus the repeat)

**Inputs:**
- E36 predictions `runs/20261015T023921Z`;
- E38 predictions `8fdfd027…`;
- I7 predictions `0486e3ed…`.

**Commits:** c3f8334, 8f166c4, plus the report commit.
