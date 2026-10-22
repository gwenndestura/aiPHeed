# E97: validation and completion of the served aiPHeed system (thesis evidence report)

**Branch.** `e97-validation-completion`, from `e96-target-formulation` (8a62693).
**Protocol.** `PROTOCOL.md` (SHA-256 `dfda2052…7782`), frozen and committed (01bf4c7) before any E97 scoring.
**Runs.**
- `runs/20261022T080842Z/`: FIRI v2 (Q1–Q4)
- `runs/*_objective4/`: T43 baselines (Q5)
- `runs/*_lgu/`: LGU rankings (Q6)
- `runs/*_fnri/`: DOST-FNRI (Q7)
- `iso25010/`: ISO/IEC 25010 (Q8)

**Scripts.** `runner/*.py`. Run from `backend/`.
**Tests.** `backend/tests/integration/test_e97_validation.py` (10 tests).

## 1. Executive summary

- **The dashboard model is FIRI v2**: an evidence-weighted 0–1 risk index, two quarters ahead (Lead 2). The E56 LightGBM
  food-price-pressure forecast is one of its affordability inputs.
- **Its stored evaluation is reproducible and leakage-free.** E97 recovered the original runner from commit 151887c (it
  had not been carried into this branch) and re-derived every number from the served history. On all 90 rows:
  - the hunger input uses only SWS rounds posted before each issue date;
  - the walk-forward evidence weights match exactly;
  - every issue date and target lead is correct.
- **Against the measured outcome** (SWS involuntary hunger > 11.3%, Balance Luzon, 15 quarters), FIRI v2 is correct in
  **14 of 15 quarters (93.3%)**:

  | Baseline | Accuracy |
  |---|---|
  | FIRI v2 | **93.3%** (14/15) |
  | Latest-reading persistence (H1) | 66.7% (10/15) |
  | Always-HIGH | 66.7% (10/15) |

  - Its balanced-accuracy advantage over H1 has a quarter-bootstrap 95% CI above zero (+0.35 [0.08, 0.59]).
  - The advantage rests on 4 discordant quarters (all in FIRI's favour): sign test p = 0.125.
- **This is development evidence on a regional outcome**, not independent provincial validation. Every one of these
  quarters was examined before the index was selected.
  - The first independent test is the SWS 2026-Q4 round, against the forecasts sealed on 2026-07-01 and 2026-10-01.
  - **The 75% Lead-2 goal is met on the regional measured outcome (development evidence) and not independently
    validated.**
- **FIRI v2 cannot yet be read as a probability.** A walk-forward calibration was pre-registered. It has too few
  past quarters with both outcomes to learn from, so it is worse than H1 and is **not served** (decision rule 2).
- **The provincial LightGBM framework on T43** (a price-pressure proxy, not food insecurity) is unchanged from E96.
  - Lead 1: 84.6%, best Brier score.
  - Lead 2: 69.2%, no better than the strongest simple baseline.
  - On the rows where it can issue a forecast, the PSA-only baseline beats it at Lead 1.
- **Dashboard defect fixed.** From 1 January 2027 the thesis dashboard would have gone blank. The served record targets
  2027-Q1, and the dynamic target moves to 2027-Q2 that day. It now keeps showing the 2027-Q1 forecast under its own
  quarter, and says that the 2027-Q2 forecast has not been issued.
- **Objective 3.** All 142 LGUs are present and join a map shape. 141 use PSA 2021 municipal poverty. Lucena uses an
  unverified province value. The ranking is robust to modest weight changes, but sensitive to Lucena's density in Quezon.
- **Objective 5.**
  - **ISO/IEC 25010: no evaluator responses exist.** The scoring package is ready. 50 DA Region IV-A responses are
    needed.
  - **DOST-FNRI** supports only a direction check, which agrees: FIES, SWS hunger and FIRI all rose from 2023 to 2025.

## 2. Final system architecture (served, thesis mode)

| Component | What it is | Status |
|---|---|---|
| FIRI v2 (`thesis_system.py`, `firi.py`, `data/thesis/firi2_*`) | 6-domain index: A affordability, V vulnerability, C climate/production, E national household economy, N news FSSI-v3, H regional hunger outlook. Expanding-window percentile scoring; walk-forward evidence weights. HIGH at ≥ 0.5. | Served map/province score |
| E56-TUNED LightGBM (`data/e58/e58_record.json`) | Lead-2 food-price-pressure probability (T43 label) | Served as indicator A1 and as `price_pressure_score` |
| Regional hunger outlook | Latest SWS round posted before the issue date ± its own past Lead-2 error | Served (H domain) |
| E69 outlook tier | Convergence-of-evidence rule (hunger AND affordability or El Niño exposure) | Served, labelled "not a probability" |
| News pipeline v3 | XLM-RoBERTa classifier v2 (frozen SHA), de-duplication, FSSI-v3 (≥ 5 articles), BERTopic topics | Served as evidence; low-news quarters flagged |
| LGU ranking | Province FIRI × (0.6 poverty_norm + 0.4 density_norm) within province | Served, labelled "indicative, not a measured municipal rate" |
| Forecast target | Next calendar quarter, Asia/Manila (`app/quarterly/target.py`), never hard-coded | Verified (§13) |

## 3. Targets (kept separate)

| Construct | Variable | Geography | Role |
|---|---|---|---|
| Household hunger (measured) | SWS involuntary hunger > 11.3% (R) | Balance Luzon only | **Primary outcome** for the dashboard index |
| Food-price pressure | T43 = R AND provincial price pressure; on every evaluated row it equals price pressure | Province | Proxy label of the LightGBM framework |
| Food insecurity (FIES) | DOST-FNRI moderate/severe FIES | 2021: 2 provinces + Lucena; 2023 and 2025: region | Descriptive comparison only |
| Poverty / vulnerability | PSA 2021 SAE, POPCEN 2024 | LGU | Predictor (V1) and ranking weight |
| Climate, employment/remittances, news | PAGASA, IBTrACS, PSA, LFS, BSP, news | Mixed | Predictors |

- No measured provincial or municipal food-insecurity series exists for 2021–2026 in the available data (E87, E96).
- None was manufactured. Provincial FIRI values are scored only against the regional outcome, and are reported as such.

## 4. Data and availability (as used by the served system)

- **SWS rounds** (`data/inputs/sws_rounds.csv`): 24 rounds, 2021-Q2..2026-Q3, each with its posting date.
  - R uses `definition_A` rounds only.
  - 2025-Q2 and 2025-Q3 have only supplementary rounds, so they are not scored under the E97 protocol. The stored FIRI2
    evaluation included them (all rounds); both readings are reported.
- **LGU table** (`data/inputs/lgu_vulnerability.csv`): 142 LGUs; no missing population or area.
- **FNRI**: `E87_Outcome_Gap/data_acquired/fnri_fies_observations.csv` (10 values, from the DOST-FNRI decks).
- **No new data was collected** (deadline instruction, 2026-10-22). No pre-2021 data was used.

## 5. Validation design

- **Origins.** Each FIRI row has an issue date: the first day of origin quarter + 1. The target is origin + 2 quarters
  (Q1d: 0 violations in 90 rows).
- **Information cutoff.**
  - The H domain equals the served `regional_hunger(origin)`, built from SWS rounds posted before the issue date
    (Q1b: 0 mismatches).
  - Evidence weights use only outcome rounds posted before the issue date (Q1c: max difference 5.6e-17).
- **Normalisation.** Indicator percentiles use strictly earlier origins (FIRI2 protocol C1).
- **Uncertainty.**
  - Quarter-cluster bootstrap (5,000 draws, seed 97) and two-sided sign tests on per-quarter differences.
  - Provincial rows that share one regional outcome are never counted as independent quarters.
- **Evidence status.** Every quarter scored here was examined in earlier experiments. Nothing in this report is an
  unseen-quarter result.

## 6. Model selection rationale

- **No new model was selected.**
  - The FIRI2 protocol selected C3 mechanically (20 Oct 2026). E97 confirms that the selection is reproducible and its
    inputs are leakage-free.
  - The only pre-registered change (a calibrated probability) failed its rule.
- **No new search was run.** E83–E96 already searched the same 13 T43 quarters thirteen times. A further search would
  only fit those quarters more closely.

## 7. Lead-2 results on the measured regional outcome (FIRI v2, dashboard model)

**E97 protocol R (definition_A rounds), 15 quarters (5 LOW / 10 HIGH):**

| Score | Accuracy (Wilson 95%) | Balanced accuracy | Precision (HIGH) | Recall (HIGH) | AUC | Brier | Confusion TP/FP/FN/TN |
|---|---|---|---|---|---|---|---|
| **FIRI v2** | **0.933** [0.70, 0.99] | **0.950** | 1.00 | 0.90 | **0.92** | 0.190 | 9/0/1/5 |
| H1 (latest reading, persistence) | 0.667 | 0.600 | 0.73 | 0.80 | 0.75 | **0.183** | 8/3/2/2 |
| Always HIGH | 0.667 | 0.500 | 0.67 | 1.00 | 0.50 | 0.333 | 10/5/0/0 |
| Climatology | 0.400 | 0.400 | — | 0.40 | 0.58 | 0.409 | 4/3/6/2 |
| FIRI, walk-forward calibrated | 0.400 | 0.400 | — | 0.40 | 0.58 | 0.406 | 4/3/6/2 |

**Paired FIRI − H1, quarter bootstrap 95% CI:**

| Difference | Estimate (95% CI) | Notes |
|---|---|---|
| Accuracy | +0.267 [0.07, 0.47] | FIRI alone correct in 4 quarters, H1 alone in 0; sign p = 0.125 |
| Balanced accuracy | +0.350 [0.08, 0.59] | |
| AUC | +0.17 [0.00, 0.42] | |
| Brier (calibrated FIRI − H1) | +0.223 [0.09, 0.37] | Worse, so the calibrated probability is not served |

**Stored-evaluation reading (all rounds, 17 quarters):** FIRI 0.941 (16/17) vs H1 0.706 and always-HIGH 0.706. This
reproduces `firi2_evaluation.json`: same confusion matrix, Brier within 3e-8.

**Per quarter (Lead 2):**

| Target | Hunger % | R | FIRI | H1 | Latest posted reading |
|---|---|---|---|---|---|
| 2022-Q3 | 9.6 | 0 | 0.177 | 0.30 | 9.2 |
| 2022-Q4 | 11.3 | 0 | 0.430 | 0.54 ✗ | 11.7 |
| 2023-Q1 | 8.7 | 0 | 0.454 | 0.55 ✗ | 11.8 |
| 2023-Q2 | 11.3 | 0 | 0.449 | 0.34 | 9.6 |
| 2023-Q3 | 10.3 | 0 | 0.470 | 0.50 ✗ | 11.3 |
| **2023-Q4** | 14.3 | 1 | 0.403 ✗ | 0.07 ✗ | 8.7 |
| 2024-Q1 | 15.3 | 1 | 0.519 | 0.50 | 11.3 |
| **2024-Q2** | 19.6 | 1 | 0.566 | 0.27 ✗ | 10.3 |
| 2024-Q3..2026-Q3 (7 quarters) | 16.7–25.3 | 1 | 0.531–0.641 | 0.86–0.995 | 14.3–24.0 |

**Rising stress (Q4).**
- Onsets, where persistence calls LOW (2023-Q4, 2024-Q1, 2024-Q2): FIRI caught 2, H1 caught 1.
- Recoveries (2022-Q4, 2023-Q1): FIRI correct in 2, H1 in 0.
- The first surge, 2023-Q4, is missed by both.

**Windows.**
- 2022-Q2..2024-Q1: FIRI 0.857 (6/7), H1 0.429.
- 2024-Q2..2026-Q3: FIRI 1.000 (8/8), H1 0.875. Every quarter in this window is HIGH, so it shows that FIRI stays HIGH
  during a high-hunger regime, not that it can discriminate.

**What drives the discrimination (Q3, domain ablation; reported only, weights unchanged):**

| Index | Accuracy | Balanced | AUC |
|---|---|---|---|
| Served | 0.933 | 0.950 | 0.92 |
| without C (climate/production) | **0.600** | 0.550 | 0.76 |
| without H (regional hunger) | 0.733 | 0.800 | 0.90 |
| without E (national economy) | 0.800 | 0.850 | 0.86 |
| without A, V or N | 0.933 | 0.950 | 0.92–0.96 |
| C alone | 0.667 | 0.750 | **0.94** |
| H alone | 0.667 | 0.600 | 0.75 |

**Reading.**
- The climate/production domain carries most of the separation, and from 2024 the walk-forward weights gave it about
  five times the weight of each other domain (for example 2.50 vs 0.50 at 2024-Q2, `weights_lead2`). It reflects the 2023–24 El Niño and production losses, which coincided with the hunger surge: **one
  episode**, which is the main generalisation risk.
- Affordability (including the LightGBM forecast) and news add nothing to regional discrimination.
- Margins at the 0.5 threshold are small (LOW maximum 0.470, HIGH minimum 0.519 apart from the 0.403 miss).

## 8. Objective 4: baseline comparisons on the T43 proxy (same 13 target quarters, 65 province rows per lead)

Unissued rows count as wrong (E83 rule 6.1). Strongest simple baseline = climatology (lowest Brier score) at both leads.

| Arm | K=1 accuracy [quarter-bootstrap CI] | K=1 balanced | K=1 Brier | K=2 accuracy | K=2 balanced | K=2 Brier |
|---|---|---|---|---|---|---|
| Naive persistence | 0.723 [0.55, 0.88] | 0.627 | 0.277 | 0.646 | 0.555 | 0.354 |
| Majority (always LOW) | 0.754 | 0.500 | 0.246 | 0.754 | 0.500 | 0.246 |
| Climatology | 0.754 | 0.500 | 0.208 | 0.754 | 0.500 | 0.219 |
| PSA-only LR (issues 30 / 25 rows) | 0.400 | 0.392 | 0.587 | 0.200 | 0.217 | 0.715 |
| News-only LR (issues 30 / 25 rows) | 0.077 | 0.072 | 0.812 | 0.215 | 0.185 | 0.761 |
| **LR-ALL** (regularised LR, all framework features; new in E97) | 0.677 | 0.638 | 0.192 | 0.615 | 0.513 | 0.267 |
| **Selected LightGBM framework** (E94 + poverty) | **0.846** [0.71, 0.95] | **0.814** | **0.142** | 0.692 | 0.564 | 0.215 |
| … without market/prices | 0.631 | 0.482 | 0.208 | 0.677 | 0.533 | 0.225 |
| … without climate | 0.846 | 0.814 | 0.142 | 0.692 | 0.564 | 0.214 |
| … without employment/remittances | 0.831 | 0.804 | 0.142 | 0.692 | 0.564 | 0.210 |
| … without news | 0.846 | 0.814 | 0.142 | 0.723 | 0.585 | 0.200 |
| … without poverty | 0.846 | 0.814 | 0.142 | 0.692 | 0.564 | 0.215 |

**Selected framework − climatology, per-quarter Brier:**
- K=1: −0.066 [−0.20, 0.06], 7 quarters better / 6 worse.
- K=2: −0.005 [−0.11, 0.09].
- Neither CI excludes 0.

**Fair reading of PSA-only and news-only.** They can issue only the later rows (30 at K=1, 25 at K=2), so the table
above penalises them for coverage. On exactly the rows they issue:

| Rows | PSA-only | Selected framework | LR-ALL | Climatology | News-only |
|---|---|---|---|---|---|
| K=1, 30 rows: accuracy / Brier | **0.867 / 0.105** | 0.767 / 0.168 | 0.733 / 0.194 | 0.733 / 0.220 | 0.167 / 0.592 |
| K=2, 25 rows: accuracy / Brier | 0.520 / 0.259 | 0.680 / 0.199 | 0.640 / 0.289 | **0.800 / 0.178** | 0.560 / 0.378 |

**Reading.**
- On T43 the LightGBM framework is the best full-coverage arm at Lead 1, but its gain over climatology is not
  significant.
- At Lead 2 nothing beats climatology.
- Where price data are available, a price-only logistic regression is at least as good at Lead 1. The market group is
  the only group with signal (removing it drops K=1 accuracy to 0.631).
- News, climate, employment and poverty add nothing to T43. Removing news slightly improves K=2.
- LightGBM beats the regularised logistic regression at both leads.

## 9. News pipeline (Objective 1) and its contribution

- **Classifier v2.** F1 0.83 on its own test set (E60), with a frozen SHA verified at start-up. FSSI-v3 is shown only
  when at least 5 articles exist. BERTopic topics are served per province-quarter.
- **Forecast contribution (E96, all else equal).**
  - None at K=1 (+0.0005 Brier gain, p = 0.45).
  - Slightly negative at K=2 (−0.015).
  - In FIRI v2, dropping N changes no regional classification (§7).
- **Likely cause:** coverage. 2021–22 has 2–21 admitted articles per quarter, 87.5% of articles are titles only, and 44%
  are attributed to a province.
- **Kept as an evidence display.** Low-news quarters are marked LIMITED_SIGNAL and never set to zero stress.

## 10. Objective 3: LGU rankings

**Audit:**
- 142 LGUs (Batangas 34, Cavite 23, Laguna 30, Quezon 41, Rizal 14), with unique PSGC codes consistent with their
  provinces.
- Through the API, all 142 join a map shape (test `test_every_lgu_joins_a_map_shape`).
- 141 carry the PSA 2021 municipal SAE.
- **Lucena** (HUC, outside the no-HUC table) uses a stored province value of 16.8%, labelled unverified.

**Weights.** 0.6 / 0.4 are the approved heuristic weights from Chapter I and Backend Guide v3, not learned. The PSA SAE
and POPCEN inputs cannot validate them: no LGU outcome exists.

**Which term dominates.** Share of within-province variance of the served index:

| Province | Poverty | Density | Density skew |
|---|---|---|---|
| Batangas | 0.68 | 0.32 | 0.6 |
| Cavite | 0.80 | 0.20 | 1.6 |
| Laguna | 0.49 | 0.51 | 2.5 |
| Quezon | 0.84 | 0.16 | **5.3** |
| Rizal | 0.69 | 0.31 | 1.2 |

Poverty generally leads. In Quezon the density term is compressed by one extreme value (Lucena).

**Sensitivity of the within-province ranking** (Spearman ρ with served; minimum over provinces):

| Variant | Minimum ρ | Largest rank shift | Reading |
|---|---|---|---|
| 0.5 / 0.5 | 0.92 | 9 | Robust |
| 0.7 / 0.3 | 0.96 | 9 | Robust |
| 0.8 / 0.2 | 0.82 | 19 | Moderate |
| log density | 0.82 | 16 | Moderate (Laguna, Cavite) |
| percentile normalisation | 0.76 | 18 | Moderate (Laguna) |
| poverty only | 0.39 | 29 | Large |
| density only | 0.14 | 33 | Large |
| Lucena excluded (Quezon) | 0.85 | 25 | **Large: min-max density is dominated by Lucena** |

**Conclusion.**
- The ranking is stable under nearby weightings.
- It is not stable under single-indicator rankings, or when Lucena is excluded from Quezon.
- It remains a relative planning order, not a validated probability. The dashboard label already says so.

## 11. Objective 5: ISO/IEC 25010

- **Responses found: none.**
  - The database holds 3 SUS-v1 feedback rows (2026-09-18). They have no agency, and two have every answer at 3, so
    they look like test entries.
  - They are not ISO/IEC 25010 responses and are not used.
- **Instrument.**
  - `frontend/meeting-materials/aiPHeed_PostTesting_Questionnaire_Draft.docx`. Items 1–5 are accuracy and relevance,
    6–9 functional suitability, 10–15 the usability sub-characteristics.
  - **The draft still names DOST Region IV-A and must be retargeted to DA Region IV-A** before it is sent.
- **Package.**
  - `iso25010/item_map.json`: item mapping, interpretation bands, and the favourable rule (weighted mean ≥ 3.41),
    stated before collection.
  - `iso25010/response_template.csv`
  - `iso25010/score_iso25010.py`: computes only from real rows, rejects invalid values, reports PARTIAL below 50.
  - Current output: `NO_RESPONSES` (0 of 50).
- **Remaining requirement:** 50 completed DA Region IV-A responses to items 1–15.

## 12. Objective 5: DOST-FNRI comparison (descriptive only)

- **NNS 2019 CALABARZON.** Not published. ENNS 2019 covered 2 provinces, and no regional estimate exists (E22). It is
  stated, not imputed.
- **2021 provincial FIES.** Batangas 29.7% [27.3, 32.2] and Cavite 31.7% [27.0, 36.4] (90% CIs).
  - The intervals overlap, so FIES cannot order these provinces.
  - FIRI has no 2021 target quarter. No ordering check is possible.
- **2023 → 2025, region.**
  - FIES rose from 19.1% (households) to 22.6% (population basis; not strictly comparable).
  - The SWS annual mean rose from 11.15 to 20.35.
  - Regional FIRI v2 rose from 0.444 to 0.577.
  - **All three agree in direction.** This is a face-validity check on one pair of years, not validation.

## 13. Deployment and software testing

**Defect found and fixed (`e41_lead2.governs`, `dashboard.forecast_target`).**
- Thesis-mode outputs require the served record's target to equal the dynamic target.
- From 2027-01-01 the target becomes 2027-Q2 while the record is for 2027-Q1, so `/provinces` returned `data: []` and
  the map went blank.
- In thesis mode the record now also governs while its target is the current calendar quarter. It is still served under
  its own quarter.
- `/config` → `quarterRange.forecastTarget.issuedForecast` says whether the target's forecast has been issued:

| Simulated date (`AIPHEED_NOW`) | Target | Issued? | 2027-Q1 provinces served |
|---|---|---|---|
| 2026-10-22 | 2027-Q1 | yes | 5 |
| 2027-01-15 | 2027-Q2 | no ("has not been issued yet …") | 5 (was 0) |
| 2027-04-15 | 2027-Q3 | no | 0 (a passed target is not shown as a forecast) |

- **Not fixed, needs a run each quarter.** The FIRI record for a new target must be produced by the quarterly run with
  newly published data (CPI, rice, SWS, PAGASA). That cannot be run now (no new data), so automatic regeneration of
  the forecast itself is not verified. Only the target clock and the honest fallback are.
- **Tests.**
  - `test_e97_validation.py`: 10 passed.
  - Full backend suite after the fix: **592 passed, 18 skipped, 0 failed** (backend venv, 98 s).
  - No frontend file changed (approved UI rule), so no frontend build was needed.
- **Production.** Render/Vercel deploy `final-system-v2`. **This branch is not deployed**, and production was not
  changed or checked.

## 14. Objective-by-objective status

| Objective (Chapter I) | Status | Evidence |
|---|---|---|
| 1. NLP pipeline (XLM-RoBERTa + BERTopic → FSSI, risk patterns per province-quarter) | **Met** (built and served); forecast contribution not supported | E60/E64 pipeline; E96 news tests; §9 |
| 2. LightGBM performance (accuracy, P/R, F1, AUC, horizon) | **Partially met.** Metrics reported at both leads (§8). No horizon is reliable on T43 (E63/E96, K = 0). On the measured regional outcome, the served index meets 75% at Lead 2 (development evidence only, §7). | §7, §8 |
| 3. LGU rankings from PSA poverty and density | **Met** as a relative ranking (142/142, sensitivity done); not validatable as a rate | §10 |
| 4. Comparison with persistence, PSA-only, NLP-only and logistic regression | **Met as a comparison.** Superiority not shown: LightGBM best at Lead 1 on full coverage but not significant vs climatology; PSA-only better on its own rows; nothing beats climatology at Lead 2. On R, FIRI beats persistence in balanced accuracy (CI > 0), not significant by sign test. | §7, §8 |
| 5. Dashboard, ISO/IEC 25010, DOST-FNRI | **Partially met.** Dashboard built and tested; ISO/IEC 25010 not collected (0/50); FNRI direction agrees (descriptive). | §11–§13 |

## 15. Remaining limitations and exactly what resolves them

1. **No independent quarter yet.** Score the sealed FIRI v2 forecasts (`FINAL_Thesis_System/out/firi2_sealed_prospective.csv`)
   when SWS posts 2026-Q4 (expected about January 2027) and 2027-Q1. Use the same rule (regional mean ≥ 0.5 vs H > 11.3%).
2. **Regional outcome only.** A provincial or LGU food-insecurity series (for example PSA CBMS 2024 household items, or
   FNRI provincial FIES for all five provinces) would allow provincial validation. It is a data request, out of scope
   under the deadline.
3. **One episode.** FIRI's separation rests on the 2023–24 El Niño and production shock. More regime changes are needed
   to show that it generalises.
4. **ISO/IEC 25010.** Retarget the draft to DA, collect 50 responses, run `score_iso25010.py`.
5. **Lucena poverty value.** Verify the 16.8% figure against the PSA provincial or HUC table.
6. **Quarterly regeneration.** Run the quarterly pipeline after 2027-01-01 with the newly published data to issue the
   2027-Q2 record. Until then the dashboard says that the forecast has not been issued.

## 16. Reproduction

From `backend/`:

```
py -3.13 ../aipheed-backend-aligned/experiments/E97_Validation_Completion/runner/firi_validation.py
py -3.13 ../aipheed-backend-aligned/experiments/E97_Validation_Completion/runner/objective4_t43.py
py -3.13 ../aipheed-backend-aligned/experiments/E97_Validation_Completion/runner/lgu_sensitivity.py
py -3.13 ../aipheed-backend-aligned/experiments/E97_Validation_Completion/runner/fnri_comparison.py
py -3.13 ../aipheed-backend-aligned/experiments/E97_Validation_Completion/iso25010/score_iso25010.py <responses.csv>
<backend venv python> -m pytest tests/integration/test_e97_validation.py
```

- **Environment.**
  - Experiments: Python 3.13, pandas 2.3.2, LightGBM 4.6.0, scikit-learn 1.8.0.
  - Tests: the backend venv (pandas 2.3.3).
- **Seeds.** Bootstrap seed 97; the E96 model seeds are unchanged.
- **Inputs.** All inputs are repository files, listed in §4.
- **Recovered original runner.** `recovered/firi2_evaluate.py` and `recovered/regional.csv`, from commit 151887c.
