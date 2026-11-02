# HISTORY_RETRAIN: does a longer historical record improve the forecast? (EXPLORATORY)

**Written:** 2026-11-02, after data acquisition and before any model, baseline or label in this folder was computed.

**Label: EXPLORATORY.**

**2023–2026 is a development test, not unseen data.** Every quarter through 2026-Q3 has already been examined by
earlier experiments (LEAD2_OPTIMIZATION protocol `88ee80bc`, "Evidence status"). Holding it out here prevents tuning
*within this experiment*, but its score is still development evidence. **The only clean test is 2027+.** If a model
passes here, its Lead-1 and Lead-2 forecasts for 2027+ issue dates must be sealed under a new preregistration and
scored prospectively. **A pass here does not replace the served model or any seal.**

**What this does not change:**
- the served model (P0H4), the dashboard, the frontend, `backend/`;
- `backend/seals/PREREG_LEAD2.md`, its addenda, and every sealed forecast;
- any file outside `aipheed-backend-aligned/experiments/HISTORY_RETRAIN/`.

The runners read other experiment folders read-only, with `sys.dont_write_bytecode = True`.

**Hash.** The SHA-256 of this file is computed over every byte before its last line, which begins `PLAN-SHA256:`. The
runner refuses to run if the file changed after hashing.

**Disclosure of what was seen before this plan:**
- In Step 1 (`DATA_INVENTORY.md`): the share of quarters with Balance Luzon (BL) hunger above 11.3%, which was 0.663 for
  1998–2020 and 0.650 for 2021–2026.
- The hunger-only label counts for 2023–2026 are public in `LEAD2_FOODINSECURITY/RESULTS.md`.
- The acquired input series were checked for coverage and for equality with the held 2021+ files.
- **No T1 or T2 label before 2021 was computed, and no model or baseline was scored before this plan was committed.**

## 1. Data (acquired 2026-11-02 by `runner/acquire.py`; log in `data/fetch_log.json`)

**User decisions of 2026-11-02, as applied:**
1. The provincial CPI history was acquired.
2. Option (b) is primary and option (c) is secondary.
3. Rice and production history was acquired, and typhoon counts were recomputed.
4. 2023–2026 is a development test.
5. R1 for T2 is counted in quarters.

No gap was filled: missing PSA cells stay missing.

| File | Source | Coverage (five provinces + Region IV-A) | Check against held data | SHA-256 |
|---|---|---|---|---|
| `data/cpi_backcast_ACP28.csv` | PSA OpenSTAT 0012M4ACP28, CPI **2018=100 back-casted**, all items + 01.1 FOOD | 1994-01..2017-12, no missing month | — | `88f5726f…` |
| `data/cpi_ACP22.csv` | PSA OpenSTAT 0012M4ACP22, CPI 2018=100 | 2018-01..2026-09, no missing month | 690/690 values equal to `E41_Lead2_Audit/data_acquired/cpi_index_ACP22.csv` (max diff 0.0) | `0dc2e79f…` |
| `data/rice_wholesale_AWB01.csv` | PSA 0052M4AWB01, regular-milled rice, wholesale, monthly | 2010-01..2026-09. Missing months: 3 Cavite, 5 Laguna, 9 Quezon (2023-09..2024-05), 2 Rizal, 3 Batangas, 0 Region | — | `513e81ad…` |
| `data/palay_corn_EVCP0.csv` | PSA 0012E4EVCP0, palay and corn production | 1987-Q1..2026-Q3, no gaps | 264/264 equal to E41 (max diff 0.0) | `baba74a1…` |
| `data/fisheries_GVFP1.csv` | PSA 0132E4GVFP1, fisheries production | 1993-Q1..2026-Q2, no gaps (cells before 1993 are empty at PSA) | 132/132 equal to E41 | `d659f61a…` |
| `data/typhoons_province_quarter.csv` | Held IBTrACS v04r01 WP file. Storms with a fix ≤ 300 km from the area-weighted province centroid, using FIRI_V2 `typhoons.py` `centroids()` and `haversine()` | 1993-Q1..2026-Q3. A count of 0 is an observed zero. | All 2021+ rows equal to `FIRI_V2_DATA_AUDIT/out/typhoons_recomputed.csv` | `2f91b30f…` |
| `data/pinksheet_monthly_1960.csv` | Held World Bank Pink Sheet workbook (`FINAL_UNIFIED_LGBM/data/raw`) re-parsed from 1960 with the served column map | 1960-01..2026-09 | — | `cb6daa88…` |

**Held files used read-only:**
- SWS: `FINAL_FOOD_INSECURITY_LIGHTGBM/data/long/sws_area_rounds_full.csv`, 1998-Q3..2026-Q3, four areas.
- ONI: `long/cov_oni.csv`.
- LFS: `long/cov_lfs.csv`, 2005-04+.
- 2021+ CPI published YoY: `E40_SWS_CPI_Tiers/data_acquired/psa_cpi_yoy_headline_food_2021_2026.csv`.
- Static vulnerability V1: `backend/data/inputs/lgu_vulnerability.csv`, via `FI.vulnerability()`.
- 2021+ news columns: `FIRI_V2_DATA_AUDIT/out/training_table_lead1.csv`.
- Price thresholds: `E40_SWS_CPI_Tiers/label_spec.json`.
- Headline P60: `E68 HEADLINE_P60`.

**Not acquired: BSP remittances (E2).** `www.bsp.gov.ph/Statistics/External/*.xlsx` returned HTTP 403 to automated
requests (4 URLs tried, 2026-11-02). Rebuilding 30 years from press clippings would amount to filling, so it was not
done. **Conditional rule, fixed now:**
- If, **before Step 3 starts**, the user places a BSP monthly OFW cash remittance file in `data/raw/` and its SHA-256
  is recorded in `data/fetch_log.json`, E2 enters option (c) as defined in §4.
- Otherwise option (c) runs without E2, and RESULTS.md says so.

**Disclosed assumptions and known breaks:**
- **Back-cast CPI.** Pre-2018 provincial and regional CPI are PSA's later recalculation on the 2018 basket. They are
  **not** the figures published at the time, which used the 1994, 2000, 2006 and 2012 bases. Both labels and features
  before 2018 therefore use a later vintage of the price data.
- **YoY source.** Months before 2021-01 use YoY computed from the index: 100 × (I_m / I_{m−12} − 1). From 2021-01 the
  label uses the PSA-published YoY, unchanged from the served label (FIRI_V2 found these equal to recomputed YoY within
  0.05).
- **Pre-2021 SWS release dates** are estimated as label month end + 60 days. This is a disclosed assumption; ten spot
  checks found it never earlier than the real release.
- **Known SWS breaks:**
  - mobile-phone rounds in **2020-Q2 and 2020-Q3**;
  - respondent base changed from household heads to adults in **2025-Q2** and all later quarters.

  These are reported as sensitivities (§7).
- **Release rules** where no release date is stored:

  | Input | Usable at O(t) |
  |---|---|
  | CPI | month ≤ m0 = month 2 of quarter t (PSA releases about day 5–10 of the next month) |
  | ONI | season ending ≤ m0 |
  | Pink Sheet | month ≤ m0 |
  | Production, fisheries, rice wholesale | quarter ≤ t − 1 |
  | LFS | round ≤ t − 1 |
  | Typhoons | quarter t, which is complete at O(t) |

## 2. Targets (both reported; neither chosen after results)

| | Definition | Unit |
|---|---|---|
| **T1** | Current Chapter I label (T43c), definition unchanged: BL hunger(q) > 11.3 AND (province food YoY quarter mean > food P60 OR food − headline > gap P60). The thresholds are the frozen 2021–22 P60 values in `label_spec.json`, never recomputed. | province-quarter |
| **T2** | Food insecurity only: BL hunger(q) > 11.3 | quarter (region-wide) |

BL hunger(q) is the mean of the non-commissioned rounds of q. A quarter with no round (1999-Q3, 2001-Q2, 2016-Q1,
2020-Q1, 2021-Q1, 2022-Q1, 2025-Q1) has no label. Labels are never zero-filled.

## 3. Leads, issue date, windows

| Item | Definition |
|---|---|
| Leads | 1 and 2 |
| Issue date | O(t) = the first day of quarter t+1. Target q = t + lead (as served). |
| Information | Only data published before O(t), using the rules in §1. SWS rounds count only if `published < O(t)`. |
| Feature origins | t = **1998-Q3** (the first origin with a published SWS reading) to 2026-Q2. Option (c) starts at origin **2011-Q2** (§4). |
| Walk-forward | At every origin t, each model is refitted using only rows whose target q′ ≤ t − 1 and whose label was known before O(t): every BL round of q′ published, and the CPI quarter complete for T1. |

**Evaluation windows** (fixed now; forecasts for every target in 2010-Q1..2026-Q3 come from one run):

| Target | Verdict window | Also reported (no verdict) |
|---|---|---|
| **T1** | Lead 1: targets 2023-Q1..2026-Q3 (14 q, 70 province-rows). Lead 2: 2023-Q2..2026-Q3 (13 q, 65 rows). These are the same rows as P0H4; R1 is counted in province-rows. | 2010-Q1..2022-Q4 development walk-forward |
| **T2** | Targets **2010-Q1..2026-Q3** at both leads, one row per quarter, 62 labelled quarters at most; R1 is counted in quarters (≥ 10 and ≥ 40) | the 2010-Q1..2022-Q4 and 2023-Q1..2026-Q3 sub-blocks separately |

**No tuning on any evaluation quarter.**
- The only hyperparameter search is the LightGBM inner validation (§4).
- It uses only the training rows at each origin.
- Nothing else is chosen by the runner.

## 4. Models (fixed list; nothing is added later)

Three models per target: **PERSIST**, **LOGIT** and **LGBM**. LOGIT and LGBM are run under two input sets:
- **(b), primary:** long-history inputs only.
- **(c), secondary sensitivity:** (b) plus the shorter inputs.

The verdict is reported for (b) and (c) separately. **Option (a)** (all 12 families with NaN before they exist) **is not
used.**

### Feature sets

Every value is computed at O(t) with the rules in §1.

**F_b(T1), one row per (origin t, province, lead k):**

| Column | Definition |
|---|---|
| A1_food, A1_gap | Projection as served (E107 `projection`): the latest published index (month m0) held flat to the target months of t+k; mean YoY against the same months a year earlier (base months ≥ 1994-01, ≤ m0); minus the province's food P60, or the gap (food − headline) minus the gap P60 |
| A_mom | 100 × (log food index m0 − log food index m0−3) |
| A2 | Mean headline YoY of months m0−1 and m0, minus the province's headline P60 |
| R_rice_yoy | Region IV-A rice CPI YoY at m0 (it stands in for A3 in (b)) |
| V1 | Static poverty and density index (FIRI Amendment 1). Disclosed: it is constant over time. |
| ONI_last, ONI_max12 | Newest ONI season ending ≤ m0, and the maximum over the 12 seasons ending ≤ m0. **These replace PAGASA C1.** |
| C2 | Province typhoon count in quarter t |
| C3 | −min(palay YoY, corn YoY), province, quarter t−1 vs t−5 |
| C4 | −fisheries YoY, province, quarter t−1 vs t−5 |
| W_rice_yoy, W_rice_mom, W_cereal_yoy, W_crude_yoy, W_urea_yoy | Pink Sheet, served definitions (`uni_lib.world_features`) |
| H1 | π_H4L (below) |
| h_last | The newest BL reading known at O(t) (LOGIT only) |
| lead | LGBM only |

**F_c(T1)** = F_b(T1) plus:
- **E1**: national unemployment, quarter mean of t−1 minus quarter mean of t−5. Before 2021 a quarter's mean is its one
  LFS round.
- **A3**: province regular-milled rice wholesale YoY. Quarter mean of the available months, t−1 vs t−5. A quarter with
  no published month is NaN; nothing is filled.
- **N1, G_pri_yoy, NG_gap_price**: the audited 2021+ values from `FIRIV2 training_table_lead1.csv`, by (origin,
  province). **They are NaN for every origin before 2021-Q1**, as the user decided ("news left blank"). This is the one
  place where missing values mark an era, and RESULTS.md says so.
- **E2**: −(national remittance YoY, t−1 vs t−5), **only under the conditional rule in §1**.

**Option (c) starts at origin 2011-Q2.** This is the first origin at which A3 and E1 exist for all five provinces:
- the first provincial rice wholesale quarter is 2010-Q1, so its first YoY is 2011-Q1;
- E1 exists from 2006-Q3.

This is later than the "~2005" in the decision, because PSA's provincial wholesale series starts in 2010-01. The old
1990–2021 series covers only Batangas and Quezon among the five provinces.

**F_b(T2), one row per (origin t, lead k), region-wide:**

| Column | Definition |
|---|---|
| h_last, h_change, h_mean4, true_h | The existing hunger-model (HG) definitions in `uni_lib.hunger_features`, on BL readings published before O(t) |
| π_H4L | See below |
| Region IV-A food and headline YoY | Mean of months m0−1 and m0 |
| Region IV-A rice CPI YoY | At m0 |
| Region IV-A food A_mom | 100 × (log food index m0 − log food index m0−3) |
| ONI_last, ONI_max12 | As in F_b(T1) |
| Typhoon count | Mean over the five provinces in quarter t |
| Region IV-A C3 and C4 | As in F_b(T1), on Region IV-A production |
| Pink Sheet columns | The five world-price columns above |
| lead | LGBM only |

**F_c(T2)** = F_b(T2) plus:
- E1 (national);
- Region IV-A rice wholesale YoY (t−1 vs t−5);
- regional news: G_pri_yoy, and N1 as the mean of the provinces' non-missing N1, both NaN before 2021-Q1;
- E2 under the conditional rule.

It also starts at origin 2011-Q2.

### π_H4L: the P0H4 hunger term, retrained on the longer history

This is H4 (LEAD2_OPTIMIZATION Addendum 3, `a3.h4`) with **one change: the error sample is not limited to 2021+**.

π_H4L = Φ((h_last − 11.3) / max(σ, 0.5)), where:
- σ is the RMSE of the latest-reading errors H(q+h) − H(q) pooled over all four SWS areas (NCR, BL, Visayas,
  Mindanao), at the same true horizon h;
- the errors use all quarters from 1998-Q3 whose rounds were published before O(t);
- with fewer than 8 pooled errors, σ falls back to H0 (BL errors only, at least 4, else 4.0), as served.

### The models

| ID | T1 | T2 |
|---|---|---|
| **PERSIST** | PERSIST-SI as served (`ch1_lib.persist_si`): hunger on the newest BL reading AND price condition on the mean of the newest three published CPI months (m0−2..m0) | 1 if h_last > 11.3, else 0 |
| **LOGIT** | One model per lead, on the T1 label. Features: F(T1) + h_last. | One model per lead, on the T2 label. Features: F(T2) (h_last is included). |
| **LGBM** | **The existing P0H4 setup retrained:** P = π_H4L × π_P. π_P is the P0 price LightGBM (below), trained on the T1 price condition | **The existing LightGBM setup** (P0's model class, grid and inner validation; HG's hunger features), trained directly on the T2 label, BL rows only, no monotone constraints |

**LOGIT** (the LEAD2_FOODINSECURITY specification, unchanged):
- scikit-learn `LogisticRegression(penalty="l2", C=1.0, solver="lbfgs", max_iter=5000)`, no class weights;
- training-median imputation and standardization, both fitted on the training rows only;
- a column with no training value, or with sd 0, is dropped at that origin;
- no tuning and no feature selection.

**P0 LightGBM**, as in `uni_lib.UniPrice` and `uni_lib.select`, unchanged:
- `objective=binary`, learning rate 0.05, `reg_lambda` 5.0, `min_child_samples` 15, seed 2027, deterministic,
  `n_jobs=1`;
- the 8-configuration grid `B.GRID`: depth {1, 2}, leaves 2^depth, trees {50, 150}, class weight {none, balanced};
- the configuration is chosen at each origin by inner chronological validation: each of the last 4 training origins is
  held out in turn, trained on rows whose target precedes it, scored by log-loss, with ties going to the lower id;
- rows of leads 1–15 are stacked, with `lead` as a column, as served;
- for T1 π_P, monotone +1 on A1_food, A1_gap and A_mom (U2).

**Eligibility and fallbacks** (as served, `B.eligible`):
- A model is fitted only if its training rows have ≥ 6 target quarters, ≥ 5 HIGH and ≥ 5 LOW.
- Otherwise it predicts the training HIGH share, or CLIM if there are no rows.
- The runner reports the number of fallback origins per model.

**Decision rule:** HIGH when P ≥ 0.50 (the approved dashboard rule).

## 5. Baselines

| Baseline | T1 | T2 |
|---|---|---|
| ALWAYS-HIGH | 1 | 1 |
| ALWAYS-LOW | 0 | 0 |
| Persistence (PERSIST-SI in R4 and R5) | PERSIST (T1) | PERSIST (T2) |
| CLIM (R5) | Share of HIGH among T1 labels known before O(t), all provinces, 1998+ | Share of HIGH among BL quarters known before O(t), 1998+ |

## 6. Reliability (unchanged rules)

**R1–R7** are FINAL_THESIS_OBJECTIVES §7 as frozen for LEAD2_OPTIMIZATION protocol `88ee80bc`. The runner imports
`P0H4_LEAD12_REVIEW/runner/reproduce.py` `rules()` and swaps in the forecast, target and baseline columns; it does not
re-implement it. That means:
- the same thresholds;
- the same thirds (`np.array_split`) and leave-one-quarter-out;
- the same one-sided paired cluster bootstrap by target quarter (seed 2036, 5000 draws).

**R1 by target** (user decision 5):
- **T1:** counted in province-rows (≥ 10 quarters and ≥ 40 rows), as before.
- **T2:** counted in quarters (≥ 10 and ≥ 40 quarters). T2 is evaluated with one row per quarter, so rows = quarters.

**Reliable** = passes all of R1–R7 **AND** has a lower Brier score than ALWAYS-HIGH and than persistence (point
estimates; the one-sided cluster-bootstrap p is reported beside each).

By construction, PERSIST is the persistence baseline. It cannot beat itself on R4, R5 or the Brier criterion, but it is
reported in full anyway.

## 7. Reporting (RESULTS.md)

**For every model × input set × target × lead, on the verdict window:**
- n (rows and quarters);
- accuracy, balanced accuracy, precision, recall, AUC (undefined for a constant forecast) and Brier;
- the confusion matrix;
- R1–R7, pass or fail, with values;
- the Brier comparisons with ALWAYS-HIGH and persistence, with p;
- the verdict;
- the number of fallback origins.

**Also reported:**
- the same metrics on the secondary windows in §3;
- every row's forecast in `out/rows.csv`.

**Comparison with current numbers:**
- **T1 against P0H4, on identical rows:**
  - Lead 1: accuracy 0.843, balanced 0.776, precision 0.688, recall 0.647, AUC 0.867, Brier 0.132; passes R1–R7.
  - Lead 2: accuracy 0.769, balanced 0.635, precision 0.600, recall 0.353, AUC 0.625, Brier 0.194; fails R3, R5 and
    R6.
  - Source: `P0H4_LEAD12_REVIEW/out/reproduce.json`.
- **T2 2023–2026 block against `LEAD2_FOODINSECURITY/RESULTS.md`**, the same hunger-only target.

**Known-break sensitivities.** These change only the evaluation set, not training, and never change the verdict:
- **S1:** without target quarters 2020-Q2 and 2020-Q3 (phone rounds);
- **S2:** without target quarters 2025-Q2 and later (adult respondents);
- **S3:** without both.

S1 affects only T2 and the T1 development window.

**Failures are reported the same way as passes.** RESULTS.md ends with the Step-4 verdict in plain words:
1. Did the longer history improve accuracy on 2023–2026?
2. Does any model pass at Lead 2?
3. Does any model beat copying the latest SWS reading?
4. Which models, if any, are candidates for a new preregistration on 2027+?

## 8. Checks (assertions, before any scoring; the runner stops if one fails)

1. **Implementation fidelity on 2021+:**
   - (a) T1 labels built here for 2021-Q1..2026-Q3 equal `ch1_lib.labels()` (`y`, `price` and `hunger`) exactly.
   - (b) π_H4L computed with the error sample restricted to 2021+ equals `pi_H4` in `FINAL_ARCHITECTURE/out/predictions.csv`
     for every Lead-1 and Lead-2 row (|diff| < 1e-9).
   - (c) PERSIST (T1) equals `PERSIST-SI_p` on the same rows.
   - (d) The 2021+ SWS rows of `sws_area_rounds_full.csv` equal the verified series `FM.rounds("primary")` (value and
     publication date).
   - (e) The Region IV-A CPI acquired here equals `long/cov_cpi.csv`.
2. **Leakage perturbation** at origins 2000-Q2, 2005-Q2, 2010-Q1, 2015-Q3, 2020-Q2, 2023-Q4 and 2026-Q2:
   - every input value published on or after O(t) is randomized (SWS rounds, CPI, rice wholesale, production,
     fisheries, typhoons of later quarters, ONI, Pink Sheet, LFS, news);
   - the feature rows and the training labels at that origin must be identical to those built without randomization.
3. **Training rows:** every training row has target q′ ≤ t − 1, and its label was known before O(t).
4. **Evaluation rows:** every evaluation row has target = t + lead, and every SWS input to it was published before O(t).
5. **Counts:**
   - T1 verdict windows have 70 and 65 rows.
   - The T2 verdict window counts are printed and asserted to be ≥ 40 quarters per lead for (b). For (c), the count is
     reported whatever it is.

## 9. Outputs

| File | Contents |
|---|---|
| `runner/acquire.py` | Done; data in `data/` |
| `runner/hr_lib.py`, `runner/run_hr.py` | Features, models and scoring |
| `out/rows.csv` | Every forecast row |
| `out/results.json` | All metrics |
| `out/checks.json` | The §8 results |
| `RESULTS.md` | Results and the Step-4 verdict |

The full backend test suite is run at the end, and `git diff --stat` is shown to confirm that nothing outside
`HISTORY_RETRAIN/` changed.

PLAN-SHA256: 6b9f17fb317c3afdea441d49723dd817b3e35f625517b6715102da08019a59bb
