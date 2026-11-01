# AIPHEED final research package (E132, final master directive)

**Status of the evidence.**
- Development evidence comes from walk-forward runs over SWS 2021-Q2 … 2026-Q3. Every value had been seen in earlier work, so these are not confirmatory.
- The confirmatory evidence will be the sealed prospective forecasts (§15), scored on the frozen primary criterion only (E131 Addendum 1).

**Protocols and commits:**
- E130 `b58c48e`;
- E131 `88b270c`, plus Addendum 1 `c32e5bc`;
- E132 `4b880f0` (results committed after it).

**Reproduce:** see `README.md`.

## 1. Root-cause investigation

| # | Cause | Evidence (sample, period, output) | Objectives affected | Resolution |
|---|---|---|---|---|
| 1 | No quarterly provincial food-insecurity measurement | Gate G1–G8 (E130 `out/gate*.json`). PFDR has 2 provincial rounds (2021, 2023); no 2025 provincial table (owner-verified). | 1, 5 | **Partly resolved:** a two-layer design (§4) |
| 2 | **True hunger change over the forecast horizon dominates the error** | ORACLE-NOW (perfect knowledge of today's true level, no foresight of change) is within tolerance only 35–55 % at Lead 2: 40 rows, 2024-Q1 … 2026-Q3 (`out/e132_univariate_and_oracle.csv`) | 2, 3 | **Not resolvable** with available predictors: closing it needs foresight of change |
| 3 | **Instrument (non-sampling) disagreement in the target** | SWS against OCTA, Balance Luzon, 7 matched quarters (2023–2026): MAE 5.18; only 29 % of OCTA readings inside the SWS primary tolerance; correlation 0.77 (`out/d2_sws_vs_octa.*`) | 1, 2 | Documented. The frozen tolerance counts sampling error only and is **not changed**. |
| 4 | Information horizon at the served issue time | Lead 2 lies 3 quarters past the newest SWS reading in 19 of 21 issues (E130 mapping) | 2, 3 | Release-anchored re-issue (P-REL) evaluated. It helps persistence only (0.536). Serving it would be a design option needing approval. |
| 5 | Design and regime change in SWS from 2025 (adult respondents; alternating rounds) | SEAS-LLM learns a shrunk quarter-of-year effect from past data only. Lead-2 within tolerance rises 0.50 → **0.61** (28 rows). | 2 | **Partly resolved** (development). The hypothesis was prompted by visible data, so confirmation must be prospective (§15). |
| 6 | Trigger groups carry no forecastable signal for measured hunger | Ablations in E131 and E132. HYB-RIDGE gets *worse* with its price features (−3.18 MAE when removed) and income features (−1.20). E114 untouched 2013–2020: no trigger skill. | 4 | Not resolvable with current data |
| 7 | Income side measured only annually, regionally, and stale | New series: SDG daily basic pay 2021–2025 (2025 preliminary); regional unemployment 2021–2023 only (`data/raw/`) | 4, 5 | Acquired and tested. No gain. |
| 8 | Learned models overfit on ~40–100 rows | Training against out-of-sample MAE: LGBM-ALL 2.12 vs 6.30; HYB-LGBM 2.07 vs 6.12; HYB-RIDGE 3.23 vs 8.94 | 6 | **Resolved:** parsimonious state-space models selected |
| 9 | Provincial food deprivation is income-driven, and income is unmeasured between FIES rounds | E131 X3a: income effects −6.0 (Quezon), −2.4 (Laguna), −1.7 (Cavite); price effects +0.1 to +1.7 | 5 | Not resolvable quarterly. Explained at survey years. |
| 10 | Evaluation power | Lead-2 shared rows cover 7 quarters (N1 needs 10) | 3 | Prospective accumulation (the seals) |
| 11 | Implementation defects | E131 pipeline re-verified (filter, as-of rules, tolerance arithmetic, training-row timing). E132 reproduces E131's LLM and PERSIST exactly. | — | None that change results |

## 2. Dataset inventory and provenance

- **Full inventory:** E130 `E130_DATA_INVENTORY.csv` (30 datasets) and E131 `E131_DATA_SOURCE_INVESTIGATION.md`.
- **New in E132:**
  - PSA SDG 8.5.1.p1 average daily basic pay by region, 2021–2026 columns (2025 preliminary; 2026 blank);
  - PSA SDG 8.5.2 unemployment by region, 2021–2025 columns (values 2021–2023);
  - both in `data/raw/`, hashed in `data/acquisition_log.json`.
- **Checked and found unusable as a target:**
  - OpenSTAT "Food Security Indicators" (3L): availability and access indicators only (CPI 1994–2018, farmers' share, cropping intensity, cereal stocks to 2020, food per capita, import dependency, food-expenditure ratio). No food-insecurity prevalence.
  - LFS OpenSTAT tables: national only.

## 3. Target-measurement validation

| Level | Target | Status |
|---|---|---|
| Quarterly | SWS involuntary hunger, 4 areas, 80 area-quarters | Measured, independent of the predictors, sampling SE from published margins (median 1.95 points) |
| Provincial | PFDR (PSA subsistence) | Measured at survey years; reproduced from FIES 2023 microdata within 0.25 points |

**Latent-variable combination with OCTA: rejected.** The instruments disagree by 5.2 points on average, so they do not measure an interchangeable quantity (§1 #3).

**Composites of CPI, poverty or FIRI: rejected** as targets (circular, or not food insecurity; E131 `E131_PROVINCIAL_CPI_QUESTIONS.md`).

## 4. Final methodology and justification

**Layer 1 (quarterly, measured).**
- **SEAS-LLM:** a measurement-aware local-level state-space model. Its observation noise is fixed to each round's published sampling error.
- It allows extra level variance at the documented 2025 respondent-base break, estimated by maximum likelihood on past data.
- It adds a pooled quarter-of-year effect estimated from post-break innovations only and shrunk by n / (n + 2).
- **Why:** it is the best model under the frozen selection rule (§5); it has 2–3 parameters; its intervals are calibrated (N7 passes at Lead 2); and it is the only design that captures known measurement structure without fitting noise.

**Layer 2 (provincial).**
- Measured PFDR (2021, 2023) with CIs, and the price-versus-income decomposition.
- Quarterly provincial values are labelled **model-based** estimates: Balance Luzon SEAS-LLM × relative food deprivation.

**Rejected:** LightGBM and ridge, raw or hybrid. They overfit and lose to the state-space models.

## 5. Model comparison and selection

**Shared rows, P-DASH:** Lead 1: 36 rows / 9 quarters; Lead 2: 28 / 7 (2024-Q4 … 2026-Q3); Lead 3: 24 / 6; Lead 4: 20 / 5.

| Model | Within tolerance, L1 / L2 / L3 / L4 | MAE, L1 / L2 / L3 / L4 |
|---|---|---|
| PERSIST (baseline) | 0.44 / 0.46 / 0.54 / 0.50 | 5.38 / 5.28 / 4.04 / 3.77 |
| LLM | 0.42 / 0.50 / 0.50 / 0.55 | 5.44 / 4.70 / 3.72 / 3.52 |
| **SEAS-LLM (selected)** | 0.36 / **0.61** / 0.50 / **0.65** | 5.97 / 4.78 / 3.53 / 3.16 |
| ENS | 0.42 / 0.46 / 0.54 / 0.60 | 5.49 / 4.81 / 3.73 / 3.39 |
| HYB-LGBM | 0.31 / 0.39 / 0.38 / 0.20 | 6.25 / 6.12 / 4.71 / 5.76 |
| HYB-RIDGE | 0.39 / 0.25 / 0.08 / 0.45 | 6.24 / 8.94 / 10.24 / 12.08 |
| LGBM-ALL | 0.33 / 0.36 / 0.42 / 0.15 | 6.19 / 6.30 / 5.12 / 6.49 |
| PSA-ONLY (baseline) | 0.36 / 0.29 / 0.33 / 0.50 | 6.59 / 8.13 / 5.46 / 5.65 |
| NLP-ONLY (baseline) | 0.33 / 0.39 / 0.67 / 0.30 | 5.51 / 5.46 / 3.24 / 17.19 |
| RIDGE-ALL (linear baseline) | 0.39 / 0.39 / 0.33 / 0.15 | 6.79 / 7.36 / 6.23 / 8.41 |

**Selection:** the frozen rule picks the highest Lead-2 share within tolerance, which is SEAS-LLM.

## 6. Feature engineering and five-trigger contribution

| Group | Representation tested | Contribution (out of sample, controlled ablation) |
|---|---|---|
| A Market | Area food and rice YoY, food ÷ all-items level and change, rice affordability (rice ÷ all-items, 4-quarter change) | None stable. Hurts the hybrid ridge (−3.18 MAE when removed); +0.23 in HYB-LGBM at Lead 2. |
| C Climate | ONI, El Niño flag, PAR typhoons | Small help in trees at Lead 2 (+0.61 MAE when removed); not significant |
| E Employment and OFW | National unemployment and remittances; **new** regional real-pay growth and unemployment | None. Income features hurt the hybrid ridge (−1.20). Data are annual and stale. |
| N News | GDELT shares | None (−0.20 to +0.08) |
| V Poverty | Area poverty (PSA rounds) | None (−0.02) |
| H History (H1) | Measured level, its denoised state and its post-break seasonality | **The only consistent signal** |

**FIRI v2 families:** A1–A3 → A; C1, C2 → C (C3, C4 are provincial only); E1, E2 → E; N1 → N; V1 → V; H1 → H.

**Not demonstrated:** a genuine contribution from the five groups. It is not forced.

## 7. Numerical forecasting evaluation

**Frozen primary tolerance:** 1.645 × SE (median ±3.2 points).

**SEAS-LLM at Lead 2** (28 rows):

| Measure | Value |
|---|---|
| MAE | 4.78 |
| RMSE | 6.53 |
| Bias | −1.16 |
| Direction accuracy | 0.67 |
| 80 % coverage | 0.71 |
| **Share within tolerance** | **0.61** |

**By area:** Metro Manila 0.86, Balance Luzon 0.71, Mindanao 0.43, Visayas 0.43.

**By level:** low tercile bias +4.15; middle −1.54; high **−6.68** (under-predicts high hunger).

**Sharp increases:** 3 of 7 within tolerance; LLM caught 0 of 7.

**Univariate set** (Lead 2: 40 rows, 2024-Q1 … 2026-Q3, including the 2024 surge):

| Model | Within, P-DASH | Within, P-REL |
|---|---|---|
| SEAS-LLM | 0.45 | 0.40 |
| PERSIST | 0.40 | 0.50 |

**At 75 %: not achieved, by any model, at any lead, under either issue rule.**

## 8. Lead 1–4 reliability evaluation

**SEAS-LLM failures by lead** (N1–N7, P-DASH, shared rows; `out/e132_rules.json`):

| Lead | Fails |
|---|---|
| 1 | All seven |
| 2 | N1, N2, N4 (p vs persistence 0.17), N5, N6. Passes **N3** and **N7**. |
| 3 | N1, N2, N3, N5, N6, N7 |
| 4 | N1, N2, N4, N5, N6 |

ENS at Lead 2 passes N3, N4 (p = 0.046), N6 and N7, and fails N1, N2 and N5.

**No model passes N1–N7 at any lead.**

## 9. Maximum reliable lead

**None, for every model.** The first unreliable lead is Lead 1. **Lead 2: failed.** It cannot be validated on 7 shared quarters, and agreement is 0.61, not 0.75.

## 10. Overfitting

| Model | Training MAE | Out-of-sample MAE |
|---|---|---|
| LGBM-ALL | 2.12 | 6.30 |
| HYB-LGBM | 2.07 | 6.12 |
| HYB-RIDGE | 3.23 | 8.94 |

The state-space models have 2–3 parameters, and their Lead-2 out-of-sample MAE (4.7–4.8) is the lowest.

## 11. Generalization

| Check | Result |
|---|---|
| Walk-forward by issue date | Both policies |
| Across areas | Uneven: Metro Manila and Balance Luzon good; Visayas and Mindanao weak |
| Across regimes | Fails on the 2024 surge (univariate set 0.45) |
| Province-held-out | Not applicable: no quarterly provincial target |
| Unseen periods | Only through the seals |

## 12. Geographic and risk-level bias

- Under-prediction in every area (bias −1.0 to −1.4).
- High-hunger quarters are under-predicted by 6.7 points; low ones over-predicted by 4.2.
- News coverage favours Cavite (E130).
- Model-based provincial estimates depend on the deprivation measure (E131 X3c).

## 13. Leakage audit

- Point-in-time features: SWS rounds published before the issue date; CPI from day 10 after the month; annual pay and unemployment from 30 June of the next year.
- Training targets were published before the issue date; interval calibration used only targets published before the issue date.
- The seasonal effect is learned from innovations available at the issue date.
- The 2025 break date comes from SWS documentation, not from outcomes.
- No pre-2021 rows.
- Hyperparameters fixed in advance.
- Seals are write-once.
- **Caveat:** hypothesis H1 was prompted by patterns already seen in 2025–26, so its development gain is not confirmatory.

## 14. Calibration and uncertainty

80 % coverage at Lead 2:

| Model | Coverage |
|---|---|
| SEAS-LLM | 0.71 (within N7's 0.70–0.90) |
| ENS | 0.82 |
| LLM | 0.86 |
| PERSIST | 0.82 |
| LGBM-ALL | 0.64 |
| HYB-LGBM | 0.61 |

Provincial model-based intervals propagate both the forecast and the relative-deprivation uncertainty.

## 15. Final provincial forecasting outputs (sealed, labelled model-based)

**File:** `sealed/E132_PROVINCIAL_MODEL_BASED_SEAL.csv` (sha256 `a1f80d57…`). Each value is the Balance Luzon SEAS-LLM forecast × EB-shrunk relative food deprivation (PFDR 2023).

| Province | 2026-Q4 (Lead 1) | 2027-Q1 (Lead 2) |
|---|---|---|
| Batangas | 20.5 [13.0–32.0] | 22.2 [13.6–35.5] |
| Cavite | 15.6 [9.2–26.4] | 16.9 [9.7–28.8] |
| Laguna | 19.6 [12.4–30.6] | 21.3 [13.0–33.7] |
| Quezon | 15.5 [9.6–24.9] | 16.7 [10.0–27.0] |
| Rizal | 27.9 [18.1–42.1] | 30.2 [18.8–46.6] |

**These are not measurements and not validated forecasts.**

**Area seal:** `sealed/E132_PROSPECTIVE_SEAL.csv` (sha256 `cea5a2ec…`). Balance Luzon SEAS-LLM: 2026-Q4 21.8 [16.6–27.0]; 2027-Q1 23.6 [17.0–30.3].

## 16. Reproducible code and configurations

- **Runners:**
  - `runner/e132_acquire.py`;
  - `runner/e132_run.py` (about 2 minutes);
  - `runner/e132_seal.py` (write-once).
- **Built on** E131 `runner/e131_x1.py` and E131/E130 libraries.
- **Fixed settings:** seeds and grids.
- **Inputs:** hashed in `data/acquisition_log.json` and E131 `data/acquisition_log.json`.
- **Tests:** `backend/tests/unit/test_e132_final.py`.

## 17. Final thesis-objective assessment

| Objective | Status | Key evidence |
|---|---|---|
| 1 Measure and forecast food insecurity | **Measurement achieved; forecasting partly achieved** | Measured targets (SWS; PFDR); forecasts exist and are sealed, but not validated |
| 2 ≥ 75 % numerical agreement | **Not achieved** | Best 0.61 (SEAS-LLM, Lead 2, 28 rows). Perfect denoising alone gives 0.35–0.55. Two hunger surveys agree only 29 % of the time within the same tolerance. |
| 3 Reliable Lead 2; maximum lead | **Not achieved. Maximum reliable lead: none (established empirically).** | No model passes N1–N7; 7 shared quarters at Lead 2 |
| 4 Five trigger groups | **Investigated; contribution not demonstrated** | Controlled ablations, hybrids, new income data |
| 5 Provincial and geospatial | **Partly achieved** | Measured survey-year PFDR plus decomposition; labelled model-based quarterly estimates |
| 6 Best model | **Achieved as a comparison** | SEAS-LLM selected by a frozen rule; LightGBM inferior and overfits |

**What would make Objectives 2 and 3 achievable:**
1. **Forecastable information about true hunger change.** Nothing in the five groups provides it today. Changes over 2–3 quarters are the binding constraint.
2. **At least 10 scored quarters** for N1, which can only come from the prospective seals (2026-Q4 onward).
3. **A provincial repeated food-insecurity measurement** for Objective 5 (CBMS rounds; provincial FIES).

None of these can be produced from the data that exist today without breaking the integrity rules.

## 18. Production readiness

**No E132 component is validated, so nothing replaces the served system.**
- Production, the dashboard, FIRI v2 and FIRI3 are unchanged.
- SEAS-LLM is a **prospective candidate**. Adoption requires ≥ 75 % within tolerance and N1–N7 passing on ≥ 10 unseen quarters, plus owner approval and a separate integration branch.
