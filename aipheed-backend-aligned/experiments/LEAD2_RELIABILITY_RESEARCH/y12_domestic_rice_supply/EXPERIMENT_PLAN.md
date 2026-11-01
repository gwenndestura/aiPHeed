# Y12: domestic rice supply and the Lead-2 price condition. Experiment plan

**Status.** This plan was written on 2026-10-29 and frozen before any supply feature was compared with any outcome. The SHA-256 and time are in `runner/PLAN_SHA256.txt` and `runner/PLAN_FROZEN_AT.txt`.

**Data looked at before freezing** (`DATA_AUDIT.md`):

- coverage tables;
- the 2021 overlap between the 2012-based and 2018-based provincial CPI;
- price-condition prevalence by province and period.

These use CPI and the frozen E40 thresholds only. No supply indicator was related to any outcome before freezing.

## 1. Question and hypothesis

**H-Y12.** National rice stocks (total, commercial, NFA) and farmgate palay prices published before a Lead-2 issue date contain a leading signal for the provincial CALABARZON price condition 5–7 months ahead. That signal goes beyond what persistence of food inflation provides.

**Fixed (not changed by this plan):**

- R1–R7;
- the 0.50 threshold;
- the T43c definition;
- the official 65-row Lead-2 test;
- the E40 provincial thresholds (θ_food, θ_gap).

## 2. Origins, targets and outcome

| Item | Definition |
|---|---|
| Origin t | Issue date O(t) = first day of quarter t+1. Lead 2: target quarter q = t + 2. CPI months of q = m0(t)+5 .. m0(t)+7, where m0(t) = month 2 of quarter t. |
| **Development outcome** (independent years) | Provincial price condition, 2012-base analogue: c(p,q) = 1 if F(p,q) > θ_food[p] or F(p,q) − A(p,q) > θ_gap[p]. F and A are the 3-month means of PSA 2012=100 food and all-items YoY for province p (`cpi2012_yoy_*`). Defined only when all 3 months exist. |
| Development rows | 5 provinces × targets 2002-Q1 .. 2020-Q4 (76 quarters, 380 rows) |
| Clustering | Rows from the same target quarter form one cluster. Effective n is reported. |
| Known limitation (audit) | In 2021, 2012-based and 2018-based provincial food YoY differ by 1.3–2.6 points on average. The condition agrees in 14/20 province-quarters. The development outcome is therefore an analogue of the official 2018-based condition, not identical to it. Values before 2018 are PSA backcasts or rebased series, not the vintages published at the time. |

## 3. Information available at O(t)

Each indicator uses only the newest reference period allowed by its rule below:

| Indicator | Newest reference period allowed | Basis |
|---|---|---|
| Provincial CPI YoY (food, all items, rice) | m0(t) | The project's existing CPI rule (E41) |
| Rice stocks inventory as of the 1st of month M (total, household, commercial, NFA; national) | **M ≤ m0(t) − 2**, i.e. the stock date is ≥ 4 months before O(t) | Longest verified PSA release lag: 92 days after the reference date (Jan 2023 inventory, released 3 Apr 2023). Nine releases were verified, 2022–2026, with lags of 31–92 days. **Pre-2021 release dates could not be verified**: psa.gov.ph and the Internet Archive refused automated access. The rule is a bound, not a set of verified historical dates. |
| Farmgate palay, other variety (province; IV-A if the province value is missing). Old series ≤ 2009-12, new series from 2010-01. | **M ≤ m0(t) − 1**: the reference month ended ≥ 2 months before O(t) | Verified releases: September 2026 data on 13 Oct 2026; December 2023 data on 24 Jan 2024 (about 24 days). The same pre-2021 limitation applies. |
| Rice imports (monthly, 2015+) | – | **Excluded from all models.** It starts in 2015, which is too short to develop on 2002–2020. It is reported descriptively only. |
| World prices (Pink Sheet, Y10 vintage) | m0(t) | Comparator only |

**Lag sensitivity (required).** Every candidate is rerun with stocks at M ≤ m0 − 5 and farmgate at M ≤ m0 − 4 (3 extra months each).

**Missing data.** A missing supply value at the allowed month is replaced by the newest earlier value within 3 months, else by the training-row mean (in-fold). The count is reported. A row's outcome is never imputed.

## 4. Features

Monthly values are aligned to the quarterly target by taking each feature at its newest allowed month at O(t). No monthly row is ever an extra target row.

| Group | Feature | Definition |
|---|---|---|
| Persistence | xF, xG | F3 − θ_food[p] and G3 − θ_gap[p]. F3 and G3 are the means of months m0−2..m0 (G = food − all items). |
| Domestic price | F_last | Newest month's food YoY |
| | dF3, dF6 | Change in food YoY over 3 and 6 months |
| | F_base, G_base | Food YoY and gap in the target months minus 12 (base effects; known at O(t)) |
| | rice_yoy, rice_d3 | Provincial rice YoY at m0, and its 3-month change |
| **Supply** | S1 stocks_yoy | log(total[M] / total[M−12]) |
| | S2 stocks_d3 | log(total[M] / total[M−3]) |
| | S3 nfa_share | NFA[M] / total[M] |
| | S4 commercial_yoy | log(commercial[M] / commercial[M−12]) |
| | S5 farmgate_yoy | log(fg[M] / fg[M−12]) |
| | S6 farmgate_d3 | log(fg[M] / fg[M−3]) |

## 5. Models (predeclared; pooled over provinces; refitted at every origin)

**Training rows at O(t):** origins t′ ≤ t − 3, so every target month of t′ is ≤ m0(t) and its outcome was published. All provinces are used. A fit needs at least 40 rows and at least 5 of each class.

| Name | Role | Definition |
|---|---|---|
| B0 PERS-BIN | baseline | 1{F3 > θ_food or G3 > θ_gap} |
| **B1 PERS-PROB** | **primary comparator** | Logistic on [xF, xG], C = 100 |
| B2 CLIM | baseline | Expanding share of c = 1 in the province's training rows |
| **M1 SUPPLY-SIMPLE** | candidate | Logistic, C = 1, on [xF, xG, S1, S5] |
| **M2 SUPPLY-REG** | candidate | L2 logistic on [xF, xG, F_last, dF3, dF6, rice_yoy, rice_d3, S1–S6]. C ∈ {0.01, 0.03, 0.1, 0.3, 1, 3}, chosen on the last 25% of training origins by log-loss. Standardisation is in-fold. |
| **M3 SUPPLY-CONT** | candidate | OLS F_tgt ~ 1 + F3 + F_base + S1 + S5, and OLS G_tgt ~ 1 + G3 + G_base. Gaussian predictive with training residual σ. P = 1 − (1 − P_F)(1 − P_G). The target definition is unchanged; the continuous food YoY is forecast first. |
| M2-0, M3-0 | ablations | M2 and M3 without supply features. They measure the supply contribution. |
| WAR-P | comparator | M3-0 plus the top 3 world features chosen in-fold (Y11 design at provincial level) |

## 6. Primary outcome, metric, test and acceptance

**Primary metric:** Brier score of P(c = 1) on the 380 development rows.

**Primary test:** one-sided quarter-cluster bootstrap of the mean Brier difference (candidate − PERS-PROB), B = 5000, seed 2036. H0: the candidate is not better. A moving-block bootstrap (4 consecutive quarters) is also reported.

**Price-side acceptance.** A candidate is **credible** only if all four hold:

| | Condition |
|---|---|
| A1 | Brier < PERS-PROB, with **Holm-adjusted** cluster p < 0.10 across M1, M2 and M3 |
| A2 | Balanced accuracy at 0.50 ≥ PERS-PROB's |
| A3 | The supply features help: Brier < its own no-supply ablation (M1 vs PERS-PROB, M2 vs M2-0, M3 vs M3-0), cluster p < 0.10 |
| A4 | Lag robustness: under the sensitivity lags, Brier is still below PERS-PROB (point estimate) |

**Also reported** (not gates):

- accuracy, balanced accuracy, precision, recall, specificity, F1, AUC;
- calibration (5 bins, calibration slope and intercept);
- per-province Brier;
- the **leading test**: correlation of each supply feature at O(t) with (F_tgt − F3), against the same feature measured concurrently with the target months, with 90% cluster-bootstrap CIs.

## 7. Step 4 (only if at least one candidate is credible)

- The credible candidate with the lowest development Brier replaces P0_price in an **isolated copy** of the P0H4 Lead-2 calculation. That means the official 65 rows, π_H4 unchanged, the product, threshold 0.50, and R1–R7 from the frozen implementation (`P0H4_LEAD12_REVIEW/runner/reproduce.py`).
- For 2021+ origins:
  - the model is fitted on all rows whose outcome was published before O(t) (2012-based through 2020; for 2021+ targets, the official 2018-based quarters known at O(t));
  - features come from the official 2018-based provincial CPI and the same supply tables.
- Reported alongside: served P0H4 and PERSIST-SI on identical rows, with every rule and metric.
- **Status of any pass:** "passes on the historical test (2021–2026 quarters already used by earlier configurations); reliability requires prospective sealed quarters". It is never called reliable without them.

**If no candidate is credible,** step 4 is not run. Step 5 then requires a new, separately frozen addendum and a materially different hypothesis justified by the step-3 results.

## 8. Data (pinned SHA-256; `data_acquired/manifest.json`)

| File | SHA-256 prefix | Fetched (UTC) |
|---|---|---|
| stocks_national_monthly.csv | aaa6073c | 2026-10-29T12:48:53Z |
| farmgate_palay_old.csv | d4bda7b2 | 2026-10-29T12:48:55Z |
| farmgate_palay_new.csv | db8642d6 | 2026-10-29T12:48:56Z |
| cpi2012_yoy_1995_2011.csv | f06a943a | 2026-10-29T12:49:00Z |
| cpi2012_yoy_2012_2021.csv | fca48969 | 2026-10-29T12:48:58Z |
| imports_rice_monthly_2015_2026.csv | 3b1465d2 | descriptive only |
| Pink Sheet (Y10) | bd89b83e | comparator only |
