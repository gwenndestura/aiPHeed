# Final forecasting architecture: report

**Branch:** `aiPHeed/final-architecture` (**local only, not pushed**), from `aiPHeed/bias-audit` `309d610`.

**Protocol:** `PROTOCOL_FINAL_ARCHITECTURE.md`, sha `a41dc709…`, committed (`0f90744`) before any new feature was scored.

**P0H4 stays served.** Nothing pushed, merged or deployed.

**Evidence status.** All quarters 2021–2026-Q3 informed earlier designs, so every result is **development evidence**. The first untouched outcome is SWS 2026-Q4 (seal `a498b5ef` for P0H4).

## 1. Baselines and commits

| Branch | Commit | Content |
|---|---|---|
| main | `0239273` | – |
| aiPHeed/lead2-optimization | `a1ce8ce` | served P0H4 export (seal `a498b5ef`) |
| aiPHeed/lead2-one-model | `40ea4d9` | S3 |
| aiPHeed/bias-audit | `309d610` | – |
| This branch | protocol `0f90744`; explanations `c563ffe`; experiment and report: next commits | – |

**Reproduced from saved outputs** (re-run from code where noted):

| Model | Lead 1 | Lead 2 | Max reliable lead |
|---|---|---|---|
| P0H4 | accuracy 0.843, Brier 0.132 | accuracy 0.769, recall 0.35, Brier 0.194 | 1 |
| S3 = candidate C (re-run reproduces S3 to 5e-7) | 0.857, Brier 0.112 | 0.738, recall 0.41, Brier 0.232 | 1 |

**Evaluation rows.**
- Lead 1: 70 province-quarters = 14 independent target quarters, 17 HIGH.
- Lead 2: 65 rows = 13 quarters, 17 HIGH.

All intervals are 90% cluster bootstraps by target quarter.

## 2. Why Market dominates (diagnosis)

| Cause | Evidence |
|---|---|
| **Target construction** | Since 2023-Q4, BL hunger was above 11.3 in every quarter, so T43c equals the provincial price condition in 80–92% of rows. The price condition is a threshold on the same PSA CPI series that the A1 projection extrapolates. |
| **Market carries genuine predictive information** | In the single model, removing the price columns **and** the structural price baseline: Lead-1 Brier +0.083 [0.044, 0.128], accuracy 0.857 → 0.714; Lead-2 +0.045 [0.022, 0.070] (`out/market_full_removal_C.json`). Removing only the columns changes nothing, because the information also enters through the baseline. |
| **Other families are thin** | Climate: one El Niño episode in the window (§3). E1, E2, C1: national, one value per quarter. V1: static per province. News: 17% coverage. |
| **Few events** | 13–14 independent hunger outcomes; 2 hunger onsets |

**Verdict.** Market's dominance is real and partly structural (by target design). It is not a display artefact. Its *displayed* size was also inflated by the 9-column grouping (bias audit).

## 3. Climate and El Niño audit

**Sources:**
- PAGASA ENSO items with their issue dates (`backend/app/ml/inference/enso_context.py`; 2023-03-24 Watch … 2024-06-07 Final Advisory; 2026-03-25 Watch … 2026-10-07 Advisory No. 5);
- NOAA CPC ONI (`FINAL_FOOD_INSECURITY_LIGHTGBM/data/long/cov_oni.csv`), seasons ending ≤ month 2 of quarter t;
- IBTrACS typhoon tracks; PSA production.

**Original representation (C).**
- C1 = 1 when an El Niño Alert or Advisory is in force before the issue date.
- That is true at only 4 issue dates before the evaluation targets (2023-Q2..2024-Q1 origins) and 2 at the end (2026-Q2, 2026-Q3).
- The trees never split on C1 or C2 (bias audit).

**Improved representation (D)** (all issue-time):

| Feature | What it adds |
|---|---|
| ONI at m0; 12-month maximum; months ≥ 0.5 | severity and accumulated exposure |
| PAGASA level 0–3 and quarters in force | official status and duration |
| Typhoons in t−1 and over t + t−1 | lag and accumulation |
| Production drop at t−1 | lag |

The ONI values are plausible: they peak at 1.99 in 2023-Q4/2024-Q1 and reach 1.80 at the 2026-Q3 origin.

**Leakage check.** The 6-origin audit also perturbed ONI after m0 and injected fake PAGASA items dated on or after the issue date. Every forecast was identical.

**Result.**

| Check | Finding |
|---|---|
| D vs C, Lead-2 Brier | −0.0034 [−0.0061, −0.0012]; development Brier 0.2257 vs 0.2259; HIGH/LOW calls unchanged |
| **Placebo**, climate columns shuffled across issue dates (20×) | Lead-2 Brier 0.2272 on average vs 0.2282 real: **permutation p = .55** |
| Placebo, climate columns displaced 4 quarters | 0.2312 |
| SHAP | The model *uses* climate in El Niño quarters (60% of tree attribution then, 5% otherwise) |

**Verdict.** The gain is **not specific to correctly timed climate information**. The data do not show that climate improves forecasts of this target. One El Niño episode in the window is too few to learn from. The 2026 episode will be the first real test.

**Needed:**
- untouched outcomes over the 2026–27 El Niño (seal before);
- provincial agricultural loss data (DA or PSA), dated as published;
- a longer climate–hunger history (only as a sensitivity analysis, per your study-window decision).

## 4. Experiment matrix (identical rows; single changes vs C; `out/results.json`)

| Id | Change | Lead 1 accuracy / recall / Brier | Lead 2 accuracy / balanced / recall / Brier | Lead 3 Brier | Dev Brier (Leads 1–3) | vs C | Verdict |
|---|---|---|---|---|---|---|---|
| A: P0H4 | served hybrid | 0.843 / 0.65 / 0.132 | 0.769 / 0.635 / 0.35 / 0.194 | 0.183 | 0.1917 | – | Lead 1 reliable |
| C (= S3) | single LightGBM, all 12 families | 0.857 / 0.65 / 0.112 | 0.738 / 0.633 / 0.41 / 0.232 | 0.256 | 0.2259 | – | Lead 1 reliable |
| D | + climate representation | 0.857 / 0.65 / 0.111 | 0.738 / 0.633 / 0.41 / 0.228 | 0.254 | 0.2257 | Lead 2 −0.0034 [−0.0061, −0.0012] | **failed placebo** |
| E | + lags and changes | 0.857 / 0.65 / 0.111 | 0.738 / 0.633 / 0.41 / 0.231 | 0.257 | 0.2257 | n.s. | no gain |
| F | + climate interactions | 0.857 / 0.65 / 0.112 | 0.738 / 0.633 / 0.41 / 0.234 | 0.258 | 0.2259 | Lead 2 +0.0021 [0.0004, 0.0042] **(worse)** | rejected |
| G | C + D + E + F | 0.857 / 0.65 / 0.111 | 0.738 / 0.633 / 0.41 / 0.233 | 0.255 | 0.2256 | n.s. | no gain |

**All C–G are eligible** (Lead 1 passes R1–R7 and the later-block check; Lead-1 Brier not worse than P0H4).

**Selected: C.** The development Brier differences are within 0.002, and ties go to fewer columns.

**Maximum reliable lead = 1 for every model.** Lead 2 fails R3, R5 and R6 for all of them.

## 5. Ablations of the selected single model C

`out/ablation_C.json`: refit at every origin; Brier change = full − ablated (positive = the model is better *without* it).

| Removed | Lead 1 | Lead 2 | Reading |
|---|---|---|---|
| Market (columns only; the baseline keeps A1) | −0.004 [−0.009, 0.000] | 0.000 | price information remains in the baseline |
| **Market columns + structural baseline** (diagnostic) | **−0.083 [−0.128, −0.044]** | **−0.045 [−0.070, −0.022]** | **essential** |
| Climate C1–C4 | 0.000 | −0.002 [−0.005, −0.000] (Holm 1.0) | at most marginal |
| Employment + remittances | +0.001 [0.000, 0.002] | +0.001 [0.000, 0.002] (Holm < .01) | slightly *better without* |
| News | +0.001 | +0.001 | none |
| Poverty | 0.000 | 0.000 | none |
| Regional hunger inputs | +0.001 | +0.001 | none as columns. In this design hunger is learned jointly; removing all hunger inputs from P0H4 was decisive (−0.14 accuracy), but here the price baseline and its interaction with the latest hunger reading remain. |
| Families individually | A1 columns +0.018 at Lead 2 (Holm < .01, better without: the baseline already holds A1); E2 +0.001 at Lead 1 (Holm .03); all others n.s. | | |

**Each family's role and what it shows** (scientific relevance from the bias-audit sources; predictive value from these tables):

| Family | Role | Predictive value here |
|---|---|---|
| A1–A3 Market | access | demonstrated |
| C1–C4 Climate | availability, stability | not demonstrated (placebo) |
| E1–E2 | access | none; slight noise |
| N1 | early warning | none (coverage 17%) |
| V1 | vulnerability | none, static |
| H1 | outcome measure | decisive in the hybrid; jointly learned in the single model |

All 12 families stay in the pipeline as required, each reported as found.

## 6. P0H4 vs the single model

**Brier difference, single model − P0H4** (two-sided p):

| Lead | Difference | p |
|---|---|---|
| 1 | −0.020 | .43 |
| 2 | +0.037 | .25 |
| 3 | +0.073 | **.003** |

| | P0H4 | Single model C |
|---|---|---|
| Rizal calibration (Lead-1 mean p vs observed 0) | 0.19 | **0.05** |
| Over-prediction source | hybrid artefact: price spikes coincided with low hunger | not present |
| Design | Hybrid (closed-form hunger probability × LightGBM) | **One LightGBM.** Hunger enters only as inputs; documented structural price baseline as `init_score` (a fixed formula with σ from the training window, not a second model) |

**Recommendation (frozen rule).** The single model is recommended as the thesis architecture: it is eligible and not significantly worse than P0H4 at Leads 1–2. **Disclosed trade-off:** it is significantly worse at Lead 3, an experimental horizon for both.

**Leakage.** Single-model hunger inputs come only from SWS rounds published before the issue date; the label is used only when complete. Audited (6 origins) and replayed (3 origins, ≤ 5e-7; `out/historical_replay_C.json`).

## 7. Target validity and leakage

**Target and labels.**
- The target is unchanged (T43c, verified from raw data in earlier audits; `LEAD2_OPTIMIZATION/out/target_verification.txt`, `hunger_label_reconstruction.txt`).
- No alternative target was used for selection.

**Threshold sensitivity** (descriptive, `LEAD2_ONE_MODEL/out/timing_audit.txt`):
- 15 of 65 Lead-2 price conditions are decided within 0.5 points of a threshold;
- 6 of the 11 P0H4 Lead-2 misses are such borderline cases;
- 2023-Q2 hunger sits exactly at 11.3.

**Leakage tests (all passed):**
- future perturbation of SWS, CPI, regional CPI, Pink Sheet, news, ONI, and PAGASA items injected after the issue date;
- historical replay;
- training labels only once published.

**Remaining timing exception.** V1 uses poverty data published in 2025; it is static, and no earlier vintage is in the repository.

**Proxy, not observation.** One regional SWS value per quarter is shared by the five provinces. LGU values are priority rankings.

## 8. Explanations: old vs new (commit `c563ffe` + report-name fix)

| | Before | After |
|---|---|---|
| Rows | Market, Climate Stress, Fish Kill, Employment, OFW Remittance | + **Poverty & vulnerability**, **News signals**, **Regional hunger (indicator)**; "Fish Kill" → **Fisheries production** |
| Hidden share | V1 + N1 + H1 in an undisplayed `otherPct` (mean 23%) | none (`otherPct` 0) |
| Statuses | from another model (135 wrong, fixed earlier) | from the served model's inputs, including the new rows |
| Note | – | relative model influence on the price part; hunger condition (value) and horizon not in the bars; not causes |
| Glossary and report | "Fish Kill" defined as mass fish mortality | "Fisheries production" (PSA production; earlier mislabelled); the PDF report uses the same names as the panel |

**Unchanged:**
- the served probabilities;
- the seal (the exporter now refuses to rewrite a frozen seal);
- colours and layout.

**If the single model is adopted**, its bars must add the structural baseline's deviation to Market (§2), or prices would look unimportant. This is not implemented, because the model is not served.

**Dead code found.** `frontend/src/data/quarterData.ts` holds hard-coded trigger percentages, but no component imports them.

## 9. Bias findings revisited

| Finding | Status |
|---|---|
| 135 wrong statuses | fixed, and still effective (tests) |
| Hidden families | fixed |
| Regional FIRI note | fixed |
| Causal wording | fixed |
| LGU priority wording | fixed |
| Fish Kill label | **fixed** |
| Rizal over-prediction | **explained:** a hybrid artefact (the single model gives 0.05 vs 0.19) |
| 2025-Q2 change | the later period has no onsets and higher hunger volatility (6.4 vs 3.5 points per quarter); the hybrid over-predicts there (+0.16) |

**Remaining concerns:**
- shared regional hunger observations;
- national E1/E2;
- V1 vintage;
- utilization not measured.

**Not labelled unbiased.**

## 10. References (verified; what each supports)

See `../BIAS_AUDIT/BIAS_AUDIT_REPORT.md` §10:
- TRIPOD+AI (BMJ 2024;385:e078378): reporting discrimination, calibration and validation;
- PROBAST (Ann Intern Med 2019;170:51–58) and PROBAST+AI (BMJ 2025;388:e082505): structure of the leakage, target and analysis checks;
- Lundberg & Lee 2017 (SHAP): relative influence, not causation;
- scikit-learn permutation-importance guide: held-out importance, correlated features;
- FAO 2006: the four dimensions;
- FAO SOFI 2025 (doi 10.4060/cd6008en): the food-price channel;
- FAO SOFIA 2026 (doi 10.4060/cd8357en): fisheries role;
- Balashankar et al. 2023 (Sci Adv, doi 10.1126/sciadv.abm3449): news as early warning;
- IBTrACS (doi 10.25921/82ty-9e16).

**Added here:** NOAA CPC Oceanic Niño Index, the repository copy `cov_oni.csv` (source recorded in `covariates_fetch_log.json`). It is used for ENSO severity; not re-verified online today.

## 11. Findings by confidence

**Confirmed:**
- Market information is essential (−0.083 Lead-1 Brier without it).
- The single model and P0H4 are equivalent at Leads 1–2 and the single model is worse at Lead 3.
- The maximum reliable lead is 1.
- Climate as represented, including the improved representation, shows no demonstrated predictive value (placebo p = .55).
- The explanation defects are corrected.

**Promising but unverified:**
- The single model's better calibration (Rizal; Lead-1 Brier 0.112 vs 0.132, n.s.).
- The climate signal during the 2026–27 El Niño, testable only on untouched outcomes.

**Not testable with these data:** provincial or municipal hunger; utilization; new-onset detection beyond the information available at issue.

## 12. Recommendation

1. **Thesis architecture: the single LightGBM (C = S3)**, if you approve.
   - It meets the one-model requirement.
   - It is equivalent to P0H4 where the system is reliable (Lead 1).
   - It is better calibrated across provinces.
   - It is worse at Lead 3, which stays experimental.
   - **Adopting it needs:** your approval; an export with Market bars that include the structural baseline; a new seal before SWS 2026-Q4.
2. **Until then, P0H4 stays served**, and is described in the thesis as a **hybrid**.
3. **Climate:** keep the 12-family pipeline (D's representation can stay documented). State honestly that 2021–26 contains one El Niño episode and that its predictive value is untested until the 2026–27 outcomes arrive.
