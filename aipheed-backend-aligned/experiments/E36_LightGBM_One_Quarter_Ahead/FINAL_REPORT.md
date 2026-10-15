# E36: the best defensible one-quarter-ahead LightGBM, the six Chapter I baselines, PSA 2021 LGU data, and the defects fixed

**Date:** 2026-10-15. **Branch:** `e36-lgbm-one-quarter-ahead` (from `e35-pcfn-hyperparameter-tuning` at `9d867e4`). Nothing pushed or deployed.
**Folder:** `aipheed-backend-aligned/experiments/E36_LightGBM_One_Quarter_Ahead/`. Generated tables are in `docs/TABLES.md`; commands are in `REPRODUCE.md`; deviations are in `DEVIATIONS.md`.

**Commit trail (each step committed before the next)**

| Commit | What |
|---|---|
| `db78e75` | Protocol frozen (sha `c83d11cb…`) before any arm was fitted |
| `372900d` | Runner, leakage tests and deviations D-1/D-2, before the first scoring run |
| `d2eeb12` | Evaluation runs (primary `20261015T023921Z` and a byte-identical repeat), operational model, frozen 2026-Q4 forecast |
| (final commit of this branch) | Integration into `backend/` and `frontend/`, PSA 2021/POPCEN 2024 inputs, defect fixes, tests, this report |

## 0. Verdict

| Question | Answer |
|---|---|
| **Is there a defensible one-quarter-ahead LightGBM?** | **Yes, as an experimental model.** `aiPHeed-E36-LGBM` (13 combined features, depth-limited trees) is chosen by a frozen nested rule. Leakage tests pass. Its served 2026-Q4 forecast is frozen and hashed. |
| **Does it reach 75% accuracy one quarter ahead?** | **Met as a point estimate (53/65 = 0.815), not demonstrated.** The 95% date-bootstrap interval is 0.738–0.892, so its lower end is below 75%. |
| **Is it better than the six Chapter I baselines?** | **No.** Persistence (57/65 = 0.877), LR-combined (0.862), LR-government (0.846) and LightGBM-government (0.846) all score higher, and no paired difference is significant (Holm p ≥ 0.50). It beats the two NLP-only baselines in point estimate. Always-HIGH has the same accuracy (0.815), but the model has a better Brier score and actually detects LOW quarters (specificity 0.833 vs 0). |
| **Do news signals help?** | **No measurable gain.** The government-only LightGBM (B5) matches or beats the combined model on the same rows. News carries 8% of the SHAP weight across the backtests. |
| **Is it reliable?** | **Not established.** All 13 dates are development dates (examined in E9–E35). The first untouched test is the frozen 2026-Q4 forecast, which can be scored only after the SWS December 2026 round is released. |
| **Is PSA 2021 municipal poverty integrated?** | **Yes, verified and tested:** 141 of 142 LGUs use their own PSA 2021 estimate. Lucena City (a highly urbanized city, absent from the supplied no-HUC table) uses a labelled substitute whose source is unverified. |
| **Is POPCEN 2024 integrated?** | **Yes:** 142 of 142 LGUs. The file was supplied separately (Downloads, 2026-10-15 08:45). |
| **Is aiPHeed complete?** | **No.** It is complete as a locally integrated system. It is not validated, not publicly deployed, and the Objective 5 evaluation by DA has not been done (§9). |

## 1. Chapter I requirements used

Source: `E25…/thesis_source/CHAPTER_I_verbatim.txt` (Chapter I only).

- **SOP 3 / H3:** the combined LightGBM against **six** baselines: naive persistence; logistic regression with combined, government-only and NLP-only features; LightGBM with government-only and NLP-only features.
- **Objective 2:** accuracy, precision and recall, F1, AUC-ROC, and walk-forward expanding-window evaluation across lead times.
- **Objective 4:** comparison with persistence, PSA-only, NLP-only and LR baselines. These are covered by the six.
- **Objectives 3 and 5:** LGU rankings from PSA poverty incidence and population density; a dashboard with maps and alerts; ISO 25010 evaluation; NNS face validity.
- Chapter I states no numeric accuracy threshold. The 75% figure is the researcher's goal and is read as pre-declared in `PROTOCOL.md` §7.

## 2. The one-quarter-ahead task and the leakage controls

| Item | Definition (PROTOCOL.md §1) |
|---|---|
| Forecast quarter | t+1 |
| Prediction date (origin) | 00:00 PHT on the first day of quarter t+1 |
| Information cutoff | Published before the origin: SWS rounds by verified posting date; food CPI D up to t−1; food and rice CPI for months 1–2 of t; validated news published in quarter t |
| Target | The Chapter I composite label: S1 = H + 2D, HIGH when S1 exceeds τ, the trailing median of published quarters. Unchanged. |
| Window | 2021-Q1 to 2026-10-14; no row before 2021 |
| Evaluation | Rolling origin, expanding window; every arm is refitted at every origin; nested model selection (§3) |

**Automated timing tests** (`tests/test_e36_timing.py`, 14 tests, all pass):
- Scrambling everything published on or after the origin leaves all features, training rows and the predictions of all 25 arms (including PCF21) at that origin unchanged. Scrambled inputs: SWS rounds, S1, D, Dnow, rice CPI and news counts/FSSI of later quarters. Checked at 4 origins, including the operational one.
- Training targets are ≤ t−1 and posted before the origin.
- The nested selection uses only labels posted before each origin. Falsifying the last outcome changes no earlier selection or prediction.
- No row falls outside the window.
- The 2026-Q4 forecast uses only information published before 2026-10-01: its last label is 2026-Q2, because the September 2026 round was posted on 2026-10-14.

**A high score from an invalid design is not used anywhere.** Earlier pooled multi-lead figures (for example P45's 86.4% over leads 1–6) are not used. Training accuracy is not reported.

## 3. Candidates, tuning and the selected model

**Feature sets** (E32 construction, reused unchanged):
- **GOV** (8): SWS H_last, H_gap, H_trend, H_margin; PSA D_last, Dnow; rice_rel; y_last.
- **NLP** (5): news_n, news_reg, news_direct_share, fssi_v2, fssi_missing.
- **COMB** = 13 features.
- **COMPACT** = 6 features.

**Grid** (small, because training sets have 10–75 rows):
- G1: stumps;
- G4: stumps with balanced class weights;
- G3: depth 2, λ = 5;
- G2: the E32 setting (4 leaves, 150 trees).

**Nested rule:** at each origin, pick the configuration with the lowest mean Brier on the earlier dates whose labels were already published. If fewer than 3 such dates exist, use COMB×G1. Ties go to the simpler configuration.

**Selection path:** COMB×G1 (2023-Q1..Q4), then COMPACT×G1 (2024-Q1..2025-Q1), then COMB×G2 (2025-Q4 onward).
- **Served model:** COMB×G2, chosen at 2026-10-01 from 12 prior dates (mean Brier 0.143, against 0.159 for COMB×G1).
- **Artifact:** `models/E36-LGBM_O2026-10-01.txt`, sha `e2ae6cb0…`. It was trained on 75 rows (targets 2021-Q4..2026-Q2) with LightGBM 4.6.0.

**Existing candidates, judged on their own rows** (`docs/TABLES.md`):

| Candidate | Rows | Result | Why it is not served |
|---|---|---|---|
| E32-LGBM setting (= COMB×G2, fixed) | 65 | 56/65 = 0.862, Brier 0.132 | Best in hindsight; choosing it after seeing these dates is selection on the test. The nested procedure that would have chosen it scores 0.815 / 0.154. |
| P45 (E25, 45 candidates) | 45 (2023-Q4..2026-Q2 only; 41 HIGH / 4 LOW) | 37/45 = 0.822, Brier 0.140. On the same rows E36-LGBM gets 34/45 = 0.756 (0.187) and always-HIGH 41/45 | No predictions exist for the 4 LOW-rich early dates. It cannot be refitted on E36 inputs (its `features_fused` panel is not the E36 input). It cannot issue 2026-Q4 (E31 record: no 2026 government features). |
| F12 (12 features) | 40 | 27/40 = 0.675, Brier 0.245 | Worse than every other LightGBM |
| PCF21 (served until E36; not LightGBM) | 50 (needs ≥ 40 D pairs, so the early dates are skipped) | 44/50 = 0.880, Brier 0.095 | Not the Chapter I model. On its 10 dates the combined LightGBM is worse (paired p = .031). Kept as a diagnostic and as the historical E31 record. |

**Does the model just repeat the last label?**
- Its labels agree with persistence on 53 of 65 rows (81.5%).
- Where they disagree, the model is right 4 times and persistence 8 times.
- Without `y_last`, the stump model scores the same as COMPACT×G1 (0.815): `y_last` adds a little, but it is not the whole model.

**Class imbalance:** 53 HIGH / 12 LOW. The model predicts HIGH on 45 rows, not 65, and catches 10 of 12 LOW.

**Time trend:** the probability rises with the date (Spearman 0.70), faster than the label base rate (0.41). This is a disclosed weakness: part of the signal may be a time proxy.

**Stability:** removing any one quarter moves accuracy only within 0.800–0.833. The two periods behave very differently:
- **P-early** (2023-Q1..Q3; 7 HIGH / 8 LOW): 14/15 correct, Brier 0.106. Persistence 12/15; always-HIGH 7/15.
- **P-late** (2023-Q4..2026-Q3; 46 HIGH / 4 LOW): 39/50 = 0.78, Brier 0.169, against always-HIGH 46/50 and persistence 45/50.

**What drives it** (exact TreeSHAP, all backtests): Dnow 43%, H_last 16%, H_trend 13%, H_margin 8%, y_last 6%, news_reg 4%, D_last 4%, fssi_v2 3%. Government indicators carry 92% and news 8%.

## 4. One-quarter-ahead evaluation: the proposed model and the six baselines

Lead 1; 13 development dates (2023-Q1..2026-Q3); 65 rows (53 HIGH / 12 LOW); identical rows, origins, cutoffs and target for every arm. Complete tables, including per period, per quarter and per province, are in `docs/TABLES.md`.

| Arm | Correct/n | Accuracy (95% CI, date bootstrap) | Bal. acc. | Precision | Recall | Specificity | F1 | ROC-AUC | Brier |
|---|---|---|---|---|---|---|---|---|---|
| **E36-LGBM (proposed, combined, nested)** | **53/65** | **0.815 (0.738–0.892)** | 0.822 | 0.956 | 0.811 | 0.833 | 0.878 | 0.850 | 0.154 |
| B1 Naive persistence | 57/65 | 0.877 (0.800–0.938) | 0.860 | 0.959 | 0.887 | 0.833 | 0.922 | 0.860 | 0.123 |
| B2 LR, combined | 56/65 | 0.862 (0.785–0.938) | 0.818 | 0.940 | 0.887 | 0.750 | 0.913 | 0.840 | 0.120 |
| B3 LR, government only | 55/65 | 0.846 (0.754–0.923) | 0.809 | 0.939 | 0.868 | 0.750 | 0.902 | 0.866 | **0.102** |
| B4 LR, NLP only | 46/65 | 0.708 (0.554–0.846) | 0.692 | 0.905 | 0.717 | 0.667 | 0.800 | 0.658 | 0.198 |
| B5 LightGBM, government only (nested) | 55/65 | 0.846 (0.769–0.923) | 0.841 | 0.957 | 0.849 | 0.833 | 0.900 | 0.870 | 0.145 |
| B6 LightGBM, NLP only (nested) | 44/65 | 0.677 (0.492–0.846) | 0.673 | 0.900 | 0.679 | 0.667 | 0.774 | 0.736 | 0.195 |
| *Diagnostic:* always HIGH | 53/65 | 0.815 (0.677–0.923) | 0.500 | 0.815 | 1.000 | 0.000 | 0.898 | 0.500 | 0.185 |
| *Diagnostic:* climatology | 48/65 | 0.738 | 0.775 | 0.950 | 0.717 | 0.833 | 0.817 | 0.771 | 0.196 |

**Confusion matrix, E36-LGBM** (rows observed, columns predicted):

| | Predicted LOW | Predicted HIGH |
|---|---|---|
| Observed LOW | 10 | 2 |
| Observed HIGH | 10 | 43 |

**Paired tests** (E36-LGBM vs each baseline; per-date Brier sign-flip; Holm over the six):

| vs | Brier gain | p | Holm | McNemar (E36 only right / baseline only right) |
|---|---|---|---|---|
| B1 | −0.031 | .37 | .76 | 4 / 8 |
| B2 | −0.034 | .26 | .76 | 4 / 7 |
| B3 | −0.052 | .08 | .50 | 5 / 7 |
| B4 | +0.043 | .25 | .76 | 12 / 5 |
| B5 | −0.009 | .10 | .51 | 0 / 2 |
| B6 | +0.041 | .16 | .65 | 13 / 4 (p .049 uncorrected) |
| always HIGH | +0.030 | .70 | – | 10 / 10 |

**Calibration:** calibration-in-the-large is −0.148, so the model is under-confident about HIGH. The reliability table is in `runs/…/results.json`. Below p = 0.35, 7 of 13 rows were in fact HIGH.

**Province discrimination:**
- Mean within-date SD of p is 0.21. Predicted labels differ across provinces on 8 of 13 dates.
- On the 7 dates with mixed observed labels, the within-date AUC is 0.84.
- The model does separate provinces, and the differences come from its inputs, mainly Dnow. Nothing was forced.

**Hypothesis 3** (the combined LightGBM will not outperform the six models): **not rejected**.

## 5. The 75% target (PROTOCOL.md §7)

| Statement | Result |
|---|---|
| 1. Point accuracy ≥ 0.75 | **Yes:** 53/65 = 0.815 |
| 2. Date-bootstrap 95% lower bound ≥ 0.75 | **No:** 0.738 (row Wilson: 0.704) |
| 3. Skill vs trivial strategies | Same accuracy as always-HIGH (0.815); below persistence (0.877). Balanced accuracy 0.822 vs 0.500 for always-HIGH. |

**Reading:**
- The target is met only as a point estimate on development data, and a constant forecast reaches the same number.
- It is **not demonstrated** and **not validated**.
- This is a failure to establish the performance target, **not** a failure to implement the objectives: the model, the evaluation and the integration exist and are tested.

**Why the data cannot support more** (E32/E35 diagnosis, unchanged):
- 70% of the label variance is one regional SWS value.
- 81.5% of labels are HIGH.
- There are 13 usable dates, and 2025-Q2/Q3 have no approved label.
- A 0.02 Brier gain over persistence needs about 62 dates to detect.
- More tuning on these dates would be test-set tuning, so none was done.

**The prospective test:**
- `frozen/E36_PROSPECTIVE_2026Q4.json` (sha `9a9b1ebf…`) holds the model's and all six baselines' 2026-Q4 forecasts:
  - E36-LGBM: Cavite 0.98, Laguna 0.99, Quezon 0.99, Rizal 0.98, Batangas 0.17;
  - persistence: HIGH, except Batangas LOW.
- Score it once, after the December 2026 SWS round.

## 6. PSA 2021 municipal poverty and POPCEN 2024 (your 2026-10-15 request)

**Files located (supplied by you, `C:\Users\admin\Downloads`)**

| File | SHA-256 | Source and reference | Coverage | Units |
|---|---|---|---|---|
| `2018 - 2021 SAE_with PSGC_noHUC.xlsx` | `5f3c95bb…` | PSA City and Municipal Level Small Area Estimates of Poverty; sheet `2018-2021_NoHUC`; only the **2021** columns are read | CALABARZON block rows 448–588: **141** LGUs (Batangas 34, Cavite 23, Laguna 30, Quezon 40, Rizal 14). Lucena City is absent: the table excludes highly urbanized cities. | Poverty incidence among population, %; CV %; 90% CI. 2021 range 1.59–30.21 |
| `3_Table B - Population and Annual PGR … rev_0.xlsx` | `80482c27…` | PSA 2024 Census of Population, Table B, sheet `R04A`; only `01-Jul-24` is read | **142/142** LGUs including Lucena (280,331). Province sums equal the published totals; Quezon's total excludes Lucena (footnote). Region total 16,933,234. | Persons |

**Verification**
- Both workbooks were re-read with an **independent** stdlib parser (`scratchpad/xlsx_dump.py`, not the build script).
- Every one of the 141 SAE values, CVs and CIs matches the integrated table (max |Δ| 3.6e-15).
- Codes map 1:1 to the 142-LGU roster, with 0 province mismatches.
- Population matches for all 142, and the province sums check out.

**Before this work, the live pipeline used**
- 16 "LGU-specific" values (hard-coded in `fix_primary_data.py::CURATED_SAE`), none of which matched the PSA 2021 table: Imus 2.8 vs 9.29, Tagaytay 5.6 vs 15.28, Antipolo 3.2 vs 9.29, Lipa 5.1 vs 12.03, Dasmariñas 3.5 vs 8.78.
- 126 province substitutes, so 0 of 141 used values equalled the official 2021 estimate.
- 2020 census population, which is outside the study window.

**Integrated** (a worktree draft, `lgu-psa-sae2021-popcen2024`, was reviewed, then rebuilt here from your workbooks; it was identical apart from the Lucena label):
- `backend/scripts/build_lgu_psa_2021_2024.py` writes:
  - `data/reference/sae2021_calabarzon_municipal.csv` (141);
  - `popcen2024_calabarzon_municipal.csv` (142);
  - `psa_lgu_2021_2024_provenance.json`;
  - `calabarzon_lgus.csv` and `data/inputs/lgu_vulnerability.csv`, with `population_2024` replacing `population_2020`.
- Code paths: `lgu_audit`, `lgu_poverty`, `forecaster_v2`, `disaggregator`, `dashboard`, `reference`, the report texts and `lgu_census_fetcher`. The 2020 rebuild script now refuses to run.

**Result**
- **141 LGUs use their actual PSA 2021 estimate; 1 (Lucena City) uses a substitute.**
- The substitute is the province value stored in the inputs (Quezon 16.8). It is hard-coded with no source workbook in the repository, and it is lower than the population-weighted mean of the municipal SAE (Quezon 19.7). It is therefore labelled **unverified** in the data, the API (`povertyLimitation`) and the record.
- A verified Lucena 2021 estimate would need the PSA HUC table, which was not supplied.
- 25 LGUs have CV > 20% (listed in the provenance file).

**Recalculated and checked end to end** (`backend/tests/integration/test_e36_served_model.py`):
- All 142 rankings were recomputed from the inputs and match the record exactly: risk index, rank in province and poverty value.
- They also match `/quarterly/e31/lgu-ranking` and `/provinces/{id}/municipalities` for all five provinces.
- The PDF Subject hash equals the record hash.
- The dashboard map panel shows the new values (Batangas population 2,994,795 from POPCEN 2024).

**Province `povertyRate` (E35-D7)**
- It is now the population-weighted mean of the 2021 municipal SAE (2024 weights), labelled as derived by aiPHeed and not an official PSA province figure.
- The hard-coded province values (Cavite 4.3, Laguna 4.2, Quezon 16.8, Rizal 3.5, Batangas 7.1) could not be verified against any supplied file.

## 7. Defect register

Status: **FIXED** = changed and covered by a test that passed in this run. **OPEN** = not fixed, with the reason. **LIMITATION** = the data or the method, not a defect.

| ID | Defect | Root cause | Affected files | Correction | Test | Status |
|---|---|---|---|---|---|---|
| E36-01 | The served engine was not a LightGBM, although Chapter I's proposed model is | E31/E34 served PCF21 because P45 could not issue 2026 forecasts, and no LightGBM was rebuilt on the E31 inputs | `e31_engine.py`, `api/v1/quarterly.py`, `dashboard.py` | E36 LightGBM built on the E32 inputs and served from `data/e36/e36_record.json`. The E31 record is kept (`AIPHEED_E31_RECORD` reverts). | `test_e36_served_model.py` (13) | FIXED |
| E36-02 | 16 wrong "LGU-specific" poverty values and 126 province substitutes | Curated values never checked against the PSA table; the PSA site blocks automated download | `data/inputs/lgu_vulnerability.csv`, `lgu_audit.py`, `lgu_poverty.py`, `dashboard.py` | PSA 2021 SAE integrated (141/142) | `test_psa_2021_sae_reaches_all_142_lgus…`, E31 `test_e28_lgu_ranking` | FIXED |
| E36-03 | Density from the 2020 census (pre-window) | Roster built from CPH 2020 | `calabarzon_lgus.csv`, `reference.py`, `disaggregator.py`, `forecaster_v2.py`, `lgu_census_fetcher.py` | POPCEN 2024 (142/142); the 2020 builder refuses to run | same | FIXED |
| E36-04 | The Lucena substitute was labelled "PSA 2021 province value" | Constant from `fix_primary_data.py` with no source | `build_lgu_psa_2021_2024.py`, `dashboard.py` | Labelled unverified | `test_lgu_ranking_in_record_api…` | FIXED (label); the value stays OPEN until the HUC table is supplied |
| E35-D1 | "High risk / Low risk" band shown for an unvalidated estimate | Display band from p ≥ 0.50 named as a classification | `status-badge.tsx`, `LeftPanel.tsx`, `data/types.ts`, `Visualization.tsx`, `GlossaryPanel.tsx`, `schemas/public.py` | Renamed "Estimated high/low (model estimate, not validated)" (E35's second option); `riskLevelBasis` now serialized | E35 `test_D1…` (rewritten), vitest `e35Claims`, `e36Brief` | FIXED |
| E35-D2 | SWS n = 300 round weighted as n = 600 | `n_respondents` not carried into the PCF21 input | `data/inputs/sws_rounds.csv`, `pcf_engine.py` | None. PCF21 is no longer served; LightGBM does not use n. Apply at the next PCF21 cycle. | E35 `test_D2` (strict xfail) | OPEN |
| E35-D3 | Quarter-on-quarter change mixed modes and crossed gaps | Compared with the previous listed quarter | `dashboard.py` (`_comparable`) | Only consecutive quarters of the same lead and mode | E35 `test_D3`, `test_D3_qoq…` | FIXED |
| E35-D4 | "Positions across provinces mostly reflect the province estimate" (false) | Min-max scaling inside each province | `lgu_audit.py` | Sentence corrected (ρ = 0.60 with the within-province index vs 0.26 with p). The formula is unchanged (adviser). | E35 `test_D4` (rewritten), `test_D4_cross_province…` | FIXED (claim); formula = LIMITATION L8 |
| E35-D5 | Panel note claimed "PSA production data already published for that quarter" | Leftover legacy text | `LeftPanel.tsx` | Note states the cutoff rule | E35 `test_D5`, vitest | FIXED |
| E35-D6 | Landing FAQ: "finest reliable signal", "region-agnostic" | Unsupported claims | `Landing.tsx` | Reworded to the evidence | E35 `test_D6`, vitest | FIXED |
| E35-D7 | Province poverty was an unweighted mean mixing substitutes | Mean over `poverty_value_used` | `dashboard.py` | Population-weighted 2021 SAE, with a basis text | E35 `test_D7` (rewritten), `test_D7…` | FIXED |
| E36-05 | Main backend tests opened the production `backend/aipheed.db` | `test_api_dashboard.py` used `TestClient(app)` without a DB override | `backend/tests/conftest.py` | Global in-memory `get_db` override. Verified by running every suite with `DATABASE_URL` pointing at a non-existent path. | all backend suites | FIXED (exposure logged, §10) |
| E36-06 | Right panel printed raw feature keys (`Dnow`, `y_last`) | `driverCopy` fell back to the key | `lib/driverCopy.ts` | Falls back to the server's plain label | screenshot check | FIXED |
| E36-07 | Municipal list said "derived from the validated province forecast" | Unsupported claim | `LeftPanel.tsx` | Says "not validated … not municipal forecasts" | vitest `e35Claims` | FIXED |
| E36-08 | Indicator text: "global median (Equation 3)", "lead 0", "GDELT … 2020-2025" | Outdated text | `dashboard.py` | Describes the served model and window | backend suite | FIXED |
| E36-09 | `/model-performance` and the reports read PCF21-only record fields | Code tied to the e31 record schema | `dashboard.py::e31_model_performance` | Schema-aware (e36/1) | `test_api_admin` rate-limit test (reports) | FIXED |
| E36-10 | Explanation note described the PCF21 decomposition | Text not tied to the served engine | `api/v1/insights.py` | TreeSHAP note when e36 is served | backend suite | FIXED |
| E36-11 | New driver labels used the banned acronym "FSSI" in plain reports | Technical names | `build_record_e36.py` (PLAIN labels) | Plain labels | `test_plain_report` | FIXED |
| E36-12 | E35's independent LGU recomputation read `population_2020` | Input vintage changed | `E35_Scoring_Audit/runner/e35lib.py` | Uses `population_2024` when present | E35 suite | FIXED |
| E36-13 | Protocol §2 date list conflicted with §2/§3 rules; LOW counts in its text were wrong | Enumerated before the missing-value rule | `PROTOCOL.md` | `DEVIATIONS.md` D-1, D-3 | `test_development_dates…` | FIXED (documented) |
| E36-14 | The quarterly pipeline still produces PCF21, not E36, forecasts | E36 features live in the experiment library | `app/quarterly/cycle.py`, `update.py` | Port the E32/E36 as-of feature builder into `backend/app` before the 2027-01-01 origin | – | OPEN (follow-up) |
| E36-15 | `public/basemap.pmtiles` missing; console "Wrong magic number" | Gitignored file not present locally | `frontend/public/` | Re-download needs your approval; province and LGU polygons still render | – | OPEN |
| E36-16 | `.claude/launch.json` entry `aipheed-api-aligned` serves the old aligned backend with its default DB | Stale configuration | `.claude/launch.json` | Added `aipheed-e36-api` (scratch DB). The old entry was left untouched (yours). | – | MITIGATED |

## 8. News data (brief §5)

**No new collection was done in E36; this part is not completed here.** The state verified in E34 still holds:
- Google News RSS titles, 2021-01-01..2026-10-14: 8,320 articles, 0 duplicate keys or links, dates recomputed with 0 mismatches.
- 140 articles admitted to FSSI-v2. Only 7 of 120 province-quarters have sufficient evidence.
- Coverage decays with age (2025/2021 = 3.4×).

**What E36 did:**
- Checked that the forecast uses only news of the previous quarter (window test).
- Measured the value of news: the NLP-only arms are at or below climatology, and news adds nothing over the government features.
- The dashboard `/news` page (validated articles with filters and pagination) works on the E36 record (vitest).

**Blocked sources:**
- GDELT rate-limits this host.
- Google News robots.txt disallows `/rss` for automated clients.
- Lead text is not obtainable compliantly (E31).

A larger, genuinely relevant corpus needs a licensed source or your decision on the source policy (E29 N-TEXT).

## 9. Chapter I objectives: status

| Objective | System (implemented and tested) | Scientific evidence |
|---|---|---|
| General: develop, validate, deploy | Developed and integrated locally | Not validated; not deployed |
| 1. Two-tier NLP → FSSI per province-quarter | Implemented (E31); unchanged | **PARTIAL:** 7/120 province-quarters sufficient; news adds no predictive value |
| 2. LightGBM metrics I–V, furthest reliable lead | **ACHIEVED** for lead 1: every metric, walk-forward, leakage-tested | **NOT ACHIEVED:** no lead is shown reliable; the furthest reliable horizon is not determinable (E25–E36) |
| 3. LGU rankings from validated province forecasts, PSA poverty and density | **ACHIEVED** (mechanics and in-window inputs: 141 SAE 2021, 142 POPCEN 2024) | **PARTIAL:** province forecasts not validated; Lucena substitute unverified; cross-province order not comparable |
| 4. Comparison with the baselines (six per SOP 3) | **ACHIEVED** | Result negative: no baseline beaten significantly; H3 not rejected |
| 5. Dashboard, alerts, ISO 25010, NNS anchor | **PARTIAL:** dashboard and alert workflow work locally | **NOT ACHIEVED:** no DA evaluation, no public deployment, NNS anchor unresolved |

## 10. Tests actually run (final state)

| Suite | Result |
|---|---|
| E36 timing/leakage (`tests/`) | 14 passed |
| Main backend (`backend/tests`, with `DATABASE_URL` pointing at a non-existent path) | 163 passed, 18 skipped (the 18 superseded tests listed in `conftest.py`, unchanged since E34) |
| E31 suite on `backend_dev` | 138 passed, 16 skipped (live E2E) |
| E31 suite on `backend/` (E31 record pinned) | 138 passed, 16 skipped |
| E35 scoring audit (E31 record pinned) | 28 passed, 1 xfailed (D2, open) |
| E32 model tests | 16 passed |
| Frontend vitest | 51 passed |
| Frontend build / TypeScript | Build OK; 11 TS errors, the same pre-existing ones (`mockData.ts`, E29 brief) |
| Evaluation reproducibility | The repeat run is byte-identical (`runs/20261015T024133Z`) |
| Visual | `/dashboard` and `/da-brief` loaded in the browser pane against the promoted backend (scratch DB). Every value matched the record. |

**Exposure log**
- The first two runs of the main backend suite in this session ran before the conftest fix, so `test_api_dashboard.py` will have executed read-only `SELECT`s on `review_records` in the production `backend/aipheed.db`, as E34 also recorded. No row was printed or stored, and the file is unchanged (mtime 2026-10-06 20:16).
- All later runs used the in-memory override. They were confirmed by pointing `DATABASE_URL` at a non-existent path.

## 11. Remaining limitations and unavailable data

1. **Target structure:** one regional SWS value drives about 70% of the label; 81.5% of labels are HIGH; τ is relative, with no SDG 2.1.2 anchor (E35 L1–L4). This is the adviser's decision.
2. **Too few dates:** 13 usable development dates; 2025-Q2/Q3 have no approved label. Only time adds evidence.
3. **Development dates were all seen before.** The 2026-Q4 forecast is the first untouched test (from January 2027).
4. **Time-trend proxy:** p correlates with the date (0.70).
5. **News:** titles only, thin and decaying with age; relevance labels made by the AI assistant (re-review pending).
6. **Lucena poverty:** substitute of unverified source; the PSA HUC 2021 table is needed.
7. **Land area:** still the old roster value (not re-sourced).
8. **PCF21 D2** (SWS per-round n): open.
9. **Quarterly pipeline:** not yet producing E36 forecasts (E36-14).
10. **Objective 5:** no ISO 25010 data; NNS anchor unresolved; no public deployment.

## 12. Decisions for you

1. **Keep the E36 LightGBM as the served model** (done locally; `AIPHEED_E31_RECORD=data/e31/e31_record.json` reverts), or revert to PCF21.
2. **Lucena City:** supply the PSA 2021 HUC poverty table, or accept the labelled substitute.
3. **Commit `E35_Scoring_Audit/`:** another session's untracked folder; its tests were updated here (D1, D3–D7 markers) but not committed.
4. **Port the E36 feature builder into the quarterly pipeline** before 2027-01-01 (proposed as a follow-up).
5. Merge, push or deploy: nothing has been pushed or deployed.
6. **Adviser:** target design, the 75% wording, and whether a model that ties always-HIGH on accuracy may be described as meeting the goal.
