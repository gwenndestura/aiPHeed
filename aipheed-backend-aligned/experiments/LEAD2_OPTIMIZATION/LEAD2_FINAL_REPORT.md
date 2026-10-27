# Lead-2 optimisation and system validation: final report

**Branch:** `aiPHeed/lead2-optimization`, from `c18008f`. Not merged; not deployed. The final commit is given in the closing message.

**Evidence status.** Every quarter 2021–2026-Q3 was examined by earlier experiments, so every result here is **development evidence**. No untouched outcome exists until SWS 2026-Q4, expected about January 2027.

**Freezing.**

| Document | Commit | sha |
|---|---|---|
| Protocol | `9615b6e` | `88ee80bc` |
| Addendum 1 | `b897723` | `38da518a` |
| Addendum 2 | `c80124e` | `9ee1cf87` |
| Addendum 3 | `3708572` | `4d85aa6d` |
| Addendum 4 | `eaba027` | `b6c2dd63` |

Each was frozen and committed **before** its arms were scored. Addenda 2–4 were frozen before the previous addendum's results existed.

---

## 1. Verdicts

| Question | Verdict | Evidence (§) |
|---|---|---|
| Is Lead 2 reliable? | **No: not reliable.** It fails R3 (balanced accuracy 0.635), R5 and R6 (HIGH recall 0.35) in every adoptable configuration. | 4, 5 |
| Maximum reliable lead | **1 quarter**, the quarter that starts on the issue date. Its verdict is *promising, not yet verified*: R1–R7 and the later-block check pass, but no untouched outcome exists. | 4 |
| What was served | **P0H4**, replacing UNI-FINAL under the frozen serve rule. It is the same unified LightGBM, with a hunger term whose uncertainty comes from all four SWS areas. Lead 1: 0.843 (UNI-FINAL 0.829). Lead-2 Brier: 0.194 (0.206). New seal `a498b5ef`. | 4, 9 |
| Is aiPHeed a food-insecurity forecaster? | **Partially validated, for the combined Chapter I proxy.** The target and its implementation are correct, leakage-free and reproducible. The hunger part adds real value: without it, Lead 1 falls to 0.686. But the hunger information is a regional "latest SWS reading" term that cannot anticipate surges, and provinces differ only through food prices. | 7 |
| Is there one unified model? | **Yes.** One LightGBM, refitted at each issue date on the stacked rows of every lead, all 12 families plus `lead`, produces every horizon. Its output is multiplied by a fixed hunger-probability formula (no second model is trained). The stricter all-in-one alternative, U-ONE, was built and scored; it fails Lead-1 recall. | 6 |

---

## 2. Baseline reproduced independently (`runner/reproduce.py`; no project metric code)

**UNI-FINAL at Lead 2:**
- **Rows:** 65 = 13 target quarters (2023-Q2..2026-Q3) × 5 provinces; issue dates 2023-01-01..2026-04-01 (origins 2022-Q4..2026-Q1). 17 HIGH (26%).
- **Classification:** accuracy 0.769; balanced 0.635; precision 0.60; recall 0.353; F1 0.444. Confusion: TP 6, FP 4, **FN 11**, TN 44.
- **Probabilities:** AUC 0.588; PR-AUC 0.413; Brier 0.206.
- **Baselines:** always-LOW 0.738; PERSIST-SI 0.677; climatology Brier 0.228.
- **Integrity:** no duplicated rows. All numbers match the earlier report exactly.
- **From code:** a rerun of the frozen arm P0H0 reproduces 0.769.

**Timing.**
- A Lead-2 forecast is issued on the first day of quarter t+1 for quarter t+2.
- The newest SWS reading at issue is for quarter t−1, so the true horizon is **3 quarters**.
- The newest CPI month is month 2 of quarter t, 5–7 months before the target months.

---

## 3. Why Lead 2 fails (`LEAD2_ERROR_ANALYSIS.md`, `out/component_analysis.txt`, `out/lead2_cases.csv`)

### Missed HIGH cases by component

| Arm | Hunger only | Price only | Both | Total |
|---|---|---|---|---|
| P0H0 | 4 | 4 | 3 | 11 |
| P4H0 | 4 | 3 | 3 | 10 |

### Three groups of misses

| Group | Issue date | Rows | What happened | Fixable with issue-time data? |
|---|---|---|---|---|
| A | 2023-07-01, target 2023-Q4 | 3 | Newest SWS was 8.7, and the price projection was strongly below threshold (A1 −5 to −8). The rice surge started after the issue date. | **No.** Information was unavailable. |
| B | 2024-01-01, target 2024-Q2 | 4 | The price part flagged risk (π_P 0.68–0.80). The hunger term was 0.29 because the surge reading (14.3, 2023-Q4) was published 2024-01-22, **21 days after issue**. | **Only with pre-2021 hunger history (sample b).** No 2021+ onset existed to learn from. |
| C | Later | 4 | 2024-Q3 Quezon: the structural gap projection was +0.6 and the fitted model overrode it (fixable). 2024-Q4 Cavite/Laguna: the price rise followed the Oct–Nov 2024 typhoons. 2026-Q2 Cavite: rice turned from −13% to inflation. | 1 fixable; 3 unavailable |

### Ceilings (oracle diagnostics; values plugged in, not forecasts)

| Hunger term × price term | Lead 2 at 0.50 |
|---|---|
| Served π_H × **oracle price** | recall 0.59 (fails R6) |
| **Oracle hunger** × P4 | accuracy 0.738, recall 0.65, precision 0.50 |
| **Oracle hunger** × P4, cutoff 0.70 (chosen in-sample, so optimistic) | passes accuracy, balanced accuracy, precision and recall |

**The binding limit is the hunger onset, an information limit.** Price-condition discrimination within hunger-HIGH quarters is about 0.73–0.76 AUC for every price model.

### Other diagnosed mechanisms

| Mechanism | Evidence | File |
|---|---|---|
| **M5: the LightGBM price part discards the structural signal** | Price-condition AUC of the plain projection max(A1): 0.93 / 0.81 / 0.87 at Leads 1/2/3. Fitted P0: 0.67 / 0.67 / 0.62. At Lead 1, A1 alone gets the price condition right 91% of the time vs 61% for P0. | `out/diag_price_signal.txt` |
| **Calendar-time confounding** | E1 has Spearman correlation +0.95 with time and within-year AUC 0.35 / 0.76 / 0.17. W_cereal and W_crude (ρ ≈ −0.75) and A2 are similar. E1 holds **17.6%** of the served model's mean absolute SHAP, the second-largest family. E1 is a shared national value (16–17 distinct values), with no coding error and no sign reversal. | `out/e1_investigation.txt`, `out/time_confound_check.txt` |

---

## 4. All candidates on identical rows (65 Lead-2 rows; 70 Lead-1 rows)

**Columns.** Accuracy, balanced accuracy (bal), precision (P), recall (R), Brier, and the rules failed at Lead 2.

| Candidate | Lead 1 | Lead 2: acc / bal / P / R | Lead-2 Brier | Lead-2 dev Brier | Fails at Lead 2 | Max reliable lead |
|---|---|---|---|---|---|---|
| A: P0H0 (UNI-FINAL, previous served) | 0.829 | 0.769 / 0.635 / 0.60 / 0.35 | 0.206 | 0.2467 | R3 R5 R6 | 1 |
| P1 engineered dynamics | 0.871 | 0.723 / 0.604 / 0.46 / 0.35 | 0.208 | 0.2620 | R2–R6 | 1 |
| P2 wide tuning grid | 0.857 | 0.708 / 0.593 / 0.43 / 0.35 | 0.211 | 0.2606 | R2–R7 | 1 |
| P3 distributional regressors | 0.786 | 0.631 / 0.579 / 0.35 / 0.47 | 0.251 | 0.2579 | R2–R7 | none |
| H1 (2021+ hunger regression) × P0 | 0.800 | 0.738 / 0.576 / 0.50 / 0.24 | 0.207 | 0.2491 | R2–R6 | none |
| B: P5 A1-only structural (diagnostic) | 0.886 | 0.723 / 0.623 / 0.47 / 0.41 | 0.217 | – | R2–R6 | 1 |
| C: P4 structural prior + corrections | 0.871 | 0.754 / 0.643 / 0.54 / 0.41 | 0.217 | 0.2687 | R3 R5 R6 | 1 |
| C: P6 prior + engineered | 0.871 | 0.754 / 0.643 / 0.54 / 0.41 | 0.215 | 0.2620 | R3 R5 R6 | 1 |
| D: P7 prior + strongly regularised | **0.900** | 0.723 / 0.623 / 0.47 / 0.41 | 0.217 | 0.2524 | R2–R6 | 1 |
| E: P8 regularised, no prior | 0.771 | 0.677 / 0.591 / 0.39 / 0.41 | 0.223 | 0.2474 | R2–R7 | none |
| F1: calibrated P0 (Platt, inner folds) | 0.771 | 0.600 / 0.425 / 0.09 / 0.06 | 0.237 | 0.2625 | all | none (not applied: worse) |
| **P0H4 (adopted, served)** | **0.843** | 0.769 / 0.635 / 0.60 / 0.35 | **0.194** | **0.2346** | R3 R5 R6 | **1** |
| P4H4 | 0.871 | 0.769 / 0.654 / 0.58 / 0.41 | 0.203 | 0.2527 | R3 R5 R6 | 1 |
| H3a × P0 (2021+ logistic hunger) | 0.843 | 0.723 / 0.509 / 0.33 / 0.06 | 0.196 | 0.2498 | R2–R7 | none |
| U-ONE-P (hunger inside one LightGBM, offset) | 0.843 (recall 0.53) | 0.769 / 0.635 / 0.60 / 0.35 | 0.200 | – | R3 R5 R6 | **none** (fails R6 at Lead 1) |
| U-ONE-0 | 0.814 | 0.692 / 0.602 / 0.41 / 0.41 | 0.233 | – | R2–R7 | none |
| *Sample b: P4H3b (1998+ hunger history), sensitivity only* | 0.857 (R 0.59, fails R6) | **0.800 / 0.751 / 0.61 / 0.65** | 0.187 | – | **R5 only** | none |
| *Sample b: P0H3b* | 0.771 | 0.800 / 0.694 / 0.67 / 0.47 | 0.166 | – | R3 R6 | none |
| always-LOW | 0.757 | 0.738 / 0.500 / – / 0 | 0.262 | | | |
| PERSIST-SI | 0.743 | 0.677 / 0.591 / 0.39 / 0.41 | 0.323 | | | |

**Multiplicity.** About 20 configurations were scored on the same quarters. The adoption used only the frozen development rule (Lead-2 Brier on targets ≤ 2024-Q4). Lead-1 gains of P4, P5 and P7 (0.871–0.900) are **post-hoc observations**: they were not selected, are not claimed, and are not served.

**The adopted model, P0H4, by lead.**

| Lead | Rows (quarters, HIGH) | Accuracy [90% CI] | Bal | P / R | F1 | AUC / PR-AUC | Brier | Always-LOW / PERSIST-SI | Verdict |
|---|---|---|---|---|---|---|---|---|---|
| **1** | 70 (14, 17) | **0.843** [0.76, 0.93] | 0.776 | 0.69 / 0.65 | 0.67 | 0.87 / 0.65 | 0.132 (< persistence p = .018; < climatology p = .037) | 0.757 / 0.743 | **promising, not yet verified** |
| 2 | 65 (13, 17) | 0.769 [0.65, 0.88] | 0.635 | 0.60 / 0.35 | 0.44 | 0.62 / 0.42 | 0.194 (vs climatology p = .16) | 0.738 / 0.677 | not reliable (R3 R5 R6) |
| 3 | 60 (12, 17) | 0.717 | 0.571 | 0.50 / 0.24 | 0.32 | 0.69 / 0.48 | 0.183 | 0.717 / 0.567 | not reliable |
| 4 | 55 (11, 17) | 0.673 | 0.503 | 0.33 / 0.06 | 0.10 | 0.41 | 0.259 | 0.691 | not reliable |
| 5 | 50 (10, 14) | 0.720 | 0.544 | 0.50 / 0.14 | 0.22 | 0.46 | 0.227 | 0.720 | not reliable |
| 6–15 | 45 → 5 | 0.63–0.65 and lower | ≤ 0.49 | recall ≤ 0.07 | – | – | – | – | not reliable; R1 fails (< 10 quarters) |

**Horizons:**

| Horizon | Value |
|---|---|
| Generated | 15 |
| Testable (R1) | 5 |
| **Maximum reliable lead** | **1** |

**Lead 1 in operational terms.** It is the quarter that starts on the issue date, 1–2 quarters after the newest published SWS survey.

---

## 5. Generalisation (P0H4)

| Check | Lead 1 | Lead 2 |
|---|---|---|
| Thirds of the test period | 0.88 / 0.76 / 0.90 | 0.72 / 0.70 / 0.90 |
| Leave-one-quarter-out minimum | 0.83 | 0.75 |
| **Surge block** 2023-Q4..2024-Q4 (11 HIGH) | 5/11 caught; accuracy 0.72 (always-LOW 0.56) | **1/11 caught**; 0.56 (always-LOW 0.56) |
| **Later block** 2025-Q2..2026-Q3 (6 HIGH; seen before, not untouched) | 6/6; 0.87 (0.80) | 5/6; 0.87 (0.80) |
| Household-head SWS base (< 2025-Q2) vs adult base (≥ 2025-Q2) | 0.825 vs 0.833 (UNI-FINAL) | 0.686 vs 0.867 |
| Rising / falling hunger quarters | 0.78 / 0.96 | 0.75 / 0.80 |
| New HIGH onsets (LOW → HIGH) | 4/10 | **0/10** |

**Reading.**
- Lead 2 works in sustained-hunger periods and fails at onsets.
- The better later-period result coincides with the respondent-base change and the end of onsets. It cannot be separated from them with 6 quarters.

---

## 6. One unified model (your correction)

**In code:**
- `uni_lib.fit_predict` fits **one** `LGBMClassifier` per issue date on the stacked rows of every lead, with `lead` as a column, and predicts every lead from it.
- The served rows (`backend/data/ch1_engine/rows.csv`) are that model's output times the hunger probability H4.
- H4 is a closed-form formula (latest reading, normal error with pooled σ). It has no trained parameters.
- No per-lead models, no ensemble.
- `export_l2.py` refuses to export unless every served Lead-1 probability equals the evaluated one (|Δ| < 1e-5) and the served π_P equals the evaluated P0.

**The all-in-one alternative (Addendum 4: U-ONE, hunger inputs inside one LightGBM trained on T43c).**
- Scored on identical rows and audited; replay identical.
- **It is not reliable at any lead.** At Lead 1 its HIGH recall is 0.53 (8 of 17 missed).
- It is not served. If you require the hunger term to be inside the LightGBM, the honest consequence is **no reliable horizon** with 2021–2026 data.

---

## 7. Is it a food-insecurity forecaster? (system validation)

### Target (`out/target_verification.txt`, `out/hunger_label_reconstruction.txt`)

**Mathematical meaning.** HIGH = [BL hunger(q) > 11.3] AND [province food YoY(q) > its 2021–22 P60, OR food minus headline YoY(q) > its 2021–22 P60].
- 11.3 = P60 of the 6 BL quarters of 2021–22, identical under every percentile method.
- All 10 provincial thresholds recompute exactly.

**Hunger labels.**
- Rebuilt from the raw SWS rows, they match the model's labels in all 20 quarters (13 HIGH).
- They also match a separate extraction from SWS tables (E114).
- Commissioned rounds are excluded.
- Respondent base: household heads until 2025-Q1, adults from 2025-Q2.

**Independence.** The hunger label is **one regional value per quarter**: 100 T43c rows = 20 independent hunger outcomes × 5 provinces. At Lead 2: 13 independent hunger outcomes.

**What is measured, and what is a proxy.**
- **Measured hunger:** SWS Balance Luzon. It is **regional**, the same for all five provinces.
- **Price pressure:** provincial PSA CPI.
- **The target:** a **combined proxy**, not a provincial food-insecurity measurement.

### Does the model forecast the proxy or just prices? (`out/validation_ablations.json`; identical rows)

| Variant (Lead 1 / Lead 2) | Accuracy | Bal | Recall | Brier |
|---|---|---|---|---|
| Full (UNI-FINAL) | 0.829 / 0.769 | 0.767 / 0.635 | 0.65 / 0.35 | 0.131 / 0.206 |
| Without A1–A3 market families | 0.714 / 0.569 | 0.651 / 0.442 | 0.53 / 0.18 | 0.188 / 0.242 |
| Without the H1 *feature* (π_H kept) | 0.843 / 0.754 | 0.816 / 0.643 | 0.76 / 0.41 | 0.125 / 0.214 |
| **Without any hunger information** (π_P alone) | **0.686 / 0.631** | 0.752 / 0.636 | 0.88 / 0.65 | 0.191 / 0.224 |
| Without market and without hunger | 0.543 / 0.477 | 0.598 / 0.513 | 0.71 / 0.59 | 0.247 / 0.260 |
| Price-only structural rule | 0.714 / 0.523 | 0.811 / 0.563 | 1.00 / 0.65 | 0.249 / 0.307 |
| Price-only persistence | 0.543 / 0.523 | – | – | 0.457 / 0.477 |
| Hunger-only (latest SWS > 11.3) | 0.514 / 0.431 | 0.619 / 0.482 | 0.82 / 0.59 | 0.486 / 0.569 |
| Always-LOW | 0.757 / 0.738 | 0.500 | 0 | 0.243 / 0.262 |

**Reading:**
- **Hunger information contributes substantially.** Removing it turns 0.829 into 0.686 at Lead 1, with 20 false alarms in hunger-LOW quarters.
- **That hunger information is the regional latest-reading multiplier.** The H1 *feature* inside the LightGBM adds nothing.
- **The market families are essential** (0.829 → 0.714).
- **Since 2023-Q4 hunger has been above 11.3 in every quarter.** T43c then equals the price condition in 80% (Lead 1) to 92% (Lead 3) of rows.
- **Across the 95 served rows, 95% of the variation in log P(HIGH) comes from the price term** (contributor audit, after the fix).

**Components separately.**

| Component | Lead 1 | Lead 2 |
|---|---|---|
| Hunger condition (per quarter) | π_H correct in 12/14 quarters (AUC 0.96), the same as the latest reading | 10/13 |
| Price condition: served LightGBM π_P | accuracy 0.614, AUC 0.67 | AUC 0.67 |
| Price condition: A1 structural rule | accuracy 0.914, AUC 0.93 | AUC 0.82 |

### Answers to the validation questions

| Question | Answer |
|---|---|
| 1. Does the implementation represent the approved target? | **Yes**, exactly (verified twice, from raw data). |
| 2. Proxy or price stress? | **The combined proxy.** Its hunger part is a regional persistence term. Since 2023-Q4 the proxy has reduced to provincial price stress, because hunger stayed high. |
| 3. Value beyond price-only baselines? | **Yes, at Lead 1:** 0.843 vs 0.70–0.71 for price-only (model or rule) and 0.757 for always-LOW. The gain comes from the hunger multiplier. |
| 4. Does it detect emerging HIGH risk? | **Poorly.** Onsets: 4/10 at Lead 1, 0/10 at Lead 2. It mainly recognises sustained HIGH periods. |
| 5. Is the accuracy supported? | Chronologically, yes: walk-forward, thirds, leave-one-quarter-out, both SWS respondent bases. **Not independently:** no untouched outcomes yet. |
| 6. Is the maximum reliable lead established? | **1 quarter, as development evidence.** |
| 7. NLP contribution? | **Not demonstrated** (§8). |
| 8. Province and LGU outputs? | **Province:** a forecast of the proxy. **LGU:** a priority ranking (province probability re-weighted 60% poverty / 40% density), labelled "not a measured or official municipal food-insecurity rate"; unvalidated. The map colours LGUs with the 0.50 band (your 10-17 decision), which could still be read as a local probability. |
| 9. What remains unvalidated? | Provincial and municipal hunger (none exists 2021–2026 except FNRI FIES 2021 for 2 provinces plus Lucena); hunger-onset forecasting; any untouched outcome. |
| 10. What is needed to claim food-insecurity forecasting defensibly? | Provincial outcome data (FNRI FIES by province, CBMS 2024 LGU tables); the prospective SWS 2026-Q4+ scoring of seal `a498b5ef`; describing the output as "Chapter I combined food-insecurity-risk proxy" (as the dashboard does), not measured provincial hunger. |

**Conclusion: partially validated.**
- The pipeline is correct, leakage-free and reproducible.
- It forecasts the defined combined proxy at Lead 1 better than price-only and hunger-only baselines.
- It cannot anticipate hunger onsets.
- It has no provincial or local hunger outcome to validate against.

---

## 8. Indicator families and news (`out/ablation_P0H0.json`; identical rows; Holm across families × Leads 1–3)

| Family | Effect of removing it from the served price model (Lead 1 / 2 / 3 accuracy; Brier change) | Holm significant? |
|---|---|---|
| A1 food-price projection | 0.829→0.700 / 0.769→0.615 / 0.750→0.600; Brier worse by 0.058 / 0.031 / 0.045 | **Yes: Lead 1 and Lead 3 (p < .001)** |
| A3 rice | Lead 2 Brier worse by 0.018 | p = .002 raw, Holm .07 |
| C4 fisheries | Lead 3 Brier worse by 0.005 | Holm < .001 |
| C3 palay/corn | **Removing it improves** Lead 3 (Brier better by 0.005) | Holm < .001 (it hurts) |
| E1 unemployment | Lead 1 Brier worse by 0.006 | Holm 1.0 (time-confounded, §3) |
| N1 news | Lead 1 0.829→0.786, Brier worse by 0.012 | raw p = .026, **Holm .86** |
| A2, V1, H1 (feature) | none significant; removing V1 or H1 slightly *improves* Lead 1 | no |
| C1 El Niño, C2 typhoons, E2 remittances | exactly zero (the model never splits on them) | no |

**Shuffled-news control** (20 refits with news permuted across issue dates):
- Lead 1: permutation p = .05 (real Brier 0.131 vs shuffles 0.139).
- Lead 2: p = .95.
- Lead 3: p = .05.
- With the structural-prior model the Lead-1 gap is only 0.0013 Brier.

**News conclusion: suggestive at Lead 1, not demonstrated.** It does not survive the family-wise correction and adds nothing at Lead 2.

All 12 families remain in the pipeline. Their contributions are reported as found; none is forced.

---

## 9. Leakage and reproducibility evidence

| Test | Result |
|---|---|
| Future-data perturbation, 6 origins, frozen arms P0–P3, H1, H2 (`out/leakage_audit.json`) | identical: 375 values per origin |
| Same for Addendum 1 (P4–P6), Addendum 2 (P7, P8, calibration P4c/P8c), Addendum 3 hunger terms, Addendum 4 U-ONE | all identical (`leakage_audit_addendum1..4.json`) |
| Positive control: CPI published **before** O(t) changed by 5% → forecast changes by up to 0.10 | passes: the audit is not vacuous |
| Historical replay: rebuilt from a table with no later origin (P0, P4, U-ONE-P) | max difference ≤ 5e-7, CSV rounding (`historical_replay*.json`) |
| Export = evaluated predictions (70 Lead-1 rows); served π_P = evaluated P0 | asserted in `export_l2.py`; tested |
| Target leakage | T43c labels enter training only when every SWS round of the quarter was published before O(t) and the CPI quarter was complete (`known_t43c`, `known_ps`); covered by the perturbation audit |
| Hyperparameters, calibration, threshold | Chosen inside each training window by inner chronological validation. The research threshold τ was selected on development rows only, reported and not served. |
| Remaining timing exception | **V1** uses PSA SAE 2021 and POPCEN 2024, both published in 2025, at every origin (documented static profile). It is constant per province (5 values), so it acts as a province identifier and carries no outcome information. Removing it does not hurt. |
| Stale documentation | The E2 inventory note "NaN after 2025-Q4" is outdated: the series now has published values through 2026 |

---

## 10. Defects corrected (separate commit, regression tests)

| # | Defect | Before | After | Test |
|---|---|---|---|---|
| D1 | Trigger statuses came from the FIRI record, not the served model: **135 of 135** "insufficient data (no published value)" statuses were false for the served model | 135 wrong | 0 wrong (`out/contributor_audit_after_fix.txt`) | `test_trigger_statuses_follow_the_served_models_own_inputs` |
| D2 | The province and region notes did not say that the bars explain only the price part. The region note said "risk index (FIRI v2)" while showing the served model's SHAP. | – | Each note states: the bars are model influence on the price estimate, rescaled to 100%; not shares of hunger; the hunger condition (with its value) is left out; the share held by poverty, news and the hunger indicator is given | `test_trigger_note_says_the_bars_explain_only_the_price_part` |

Five-contributor findings that are documented but **not** changed (no UI design changes): `FIVE_CONTRIBUTORS_AND_DIMENSIONS_AUDIT.md`.

---

## 11. Remaining limitations and the evidence needed

1. **No untouched outcome.** Score seal `a498b5ef` (P0H4, issued 2026-10-01, Leads 1–15) when SWS publishes 2026-Q4 (about Jan 2027), 2027-Q1, and so on. The UNI-FINAL seal `fcc4130d` is kept for comparison.
2. **Lead 2 needs a hunger-onset signal.**
   - The only one found is pre-2021 SWS hunger history with rice CPI (sample b). It lifts Lead 2 to 0.800 / bal 0.751 / recall 0.65 (fails only R5), but breaks Lead-1 recall.
   - Using it requires **your formal scope revision** (2021+ is the study window) and a new frozen protocol tested on untouched outcomes.
3. **No provincial or municipal hunger outcome.**
   - FNRI FIES by province, CBMS 2024 LGU tables, or a PSA data request.
   - The PSA FIES 2023 (income and expenditure) file supports only an indirect check of the province ordering.
4. **The price LightGBM underuses its strongest input.** The structural prior (P4/P7) improves Lead 1 to 0.871–0.900, but it was not selected under the frozen Lead-2 rule. A new protocol could adopt it prospectively.

---

## 12. Tests and build

- **Backend:** full suite, results in the closing message.
- **Frontend:** 75 / 75 passed; production build OK (no frontend file changed).
- **Nothing merged or deployed.**
- **Protected artefacts.** The frozen experiments (FINAL_UNIFIED_LGBM and earlier) are unmodified. The UNI-FINAL served export is preserved in `out/previous_served/`, and its seal file is unchanged.
