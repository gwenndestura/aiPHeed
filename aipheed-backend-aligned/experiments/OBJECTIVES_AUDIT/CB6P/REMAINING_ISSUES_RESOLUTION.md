# Remaining issues: resolution record (2026-11-04)

**Scope:** C-B6D-E and the five objectives.

- **Development evidence only.**
- **Nothing is served, deployed, pushed or committed.**
- **`frontend/` is untouched.**
- **Preserved:** the git stash, the uncommitted C-B7 files, every earlier pre-registration and every earlier result.

## 1. Fixed or resolved with evidence

| # | Issue | What was done | Result |
|---|---|---|---|
| 1 | "Food insecurity or food prices?" | Pre-registered Part A (`PREREGISTRATION_FI.md`): regional no-price (NP), price-only (PO) and hunger-only (HO) refits, scored on **measured** SWS hunger | Price-only fails (accuracy 0.66 / 0.60, AUC about 0.5). The full model is significantly better (p 0.024 / 0.001). Hunger history carries 58% of SHAP. **The regional forecast is food-insecurity driven** |
| 2 | Separate the hunger and price components | Component report for the provincial model | Hunger part 0.74 correct vs measured hunger. Price part sign accuracy 0.70 / 0.61. Price terms 51% / 43% of the provincial index (by construction of Eq. 3) |
| 3 | Too little provincial history (the main cause of the R4/R5/R7 failures) | Found and downloaded PSA OpenSTAT provincial food CPI on the 2012 base (2012–2021) and the 2018 base (2019–2025). Spliced; overlaps checked (2018 base = E40 exactly; 2012 vs 2018 base D correlation 0.93) | Eq. 3 labels go from 20 to **50 quarters** (100 → 250 rows) |
| 4 | C-B6D-E fails R4, R5, R7 | **Diagnosed:** 2021–26 is a persistent high-hunger regime (persistence 0.83). R4 needs accuracy > persistence; the R5 Brier test vs persistence has only 20 clusters (p 0.27); the R7 first third (2021–22) is 0.51 at Lead 2. **Extended sample:** C-B6D-E-X | **C-B6D-E-X passes all R1–R7 at Lead 1** (250 rows, 50 quarters). Lead 2 still fails R2/R3 (accuracy 0.736) |
| 5 | Verify the metrics, statistics and Algorithm 3 | Independent recomputation with sklearn; quarter-cluster bootstrap AUC CIs; Holm recomputed; Algorithm 3 recomputed | All match (max difference 1.1e-16). The AUC CIs are wide (C-B6D-E Lead 1 0.57–1.00; C-B6D-E-X 0.62–0.86) |
| 6 | Leakage | D1 / D̂ use CPI months ≤ issue month − 2; the slope uses past pairs only; labels are known by the BL and CPI release rules; static 2023 poverty is excluded from forecasting (published later) | No defect found. Checks are in the scripts (`leakage()` in `cb6p_model.py`, `S_last` check in `cb6p2_model.py`) |
| 7 | Employment and OFW value | Tested as real inputs (C-B6D-E vs C-B6D; contribution shares) | Small, positive, **not significant:** −0.004 Brier, p 0.16 / 0.13; 1–2% of the provincial index. Not forced |
| 8 | Baseline comparisons on identical rows | Persistence, CLIM, PSA-only, NLP-only, LOGIT, C-B6-R, C-B6P2, all paired on identical rows | Done (B-old and B-ext). See the improvement report |
| 9 | Objective 1 annotation readiness | Verified the files; ran the annotation selftest | Selftest passes; scoring correctly refuses: **0 / 300 labelled by A and by B** |
| 10 | Objective 3 calculations | Rechecked the inputs (142 LGUs, none missing; 25 with poverty CV > 20%); the earlier independent recomputation is exact (`OBJ3_SPATIAL_VALIDATION.md`) | Calculations verified. **Rankings are vulnerability indices, not outcomes.** Province poverty rank vs Eq. 3 HIGH frequency: ρ −0.30 (n = 5, p 0.62) |
| 11 | Objective 5 backend | `pytest` on the food-insecurity mode, the auto-update and its API | 34 / 34 passed |

## 2. Not fixable with the available evidence

| Issue | Why | What resolves it |
|---|---|---|
| AUC ≥ 0.80 | Best 0.74–0.78. The CIs include 0.80 for C-B6D-E Lead 1 but only 17% bootstrap mass for C-B6D-E-X | More provincial quarters (prospective 2027+), or a provincial food-insecurity measurement as the target |
| A significant gain over C-B6P2 / C-B6D-E | Differences of 0.003–0.007 Brier on 20 quarters | Prospective seal from 2027-01-01 (4 quarters × 5 provinces per year) |
| Lead 2 reliability | Accuracy 0.736 on B-ext (fails R2, R3) | Same as above |
| Non-price drivers beyond hunger | NP vs HO not significant; employment and OFW are national series | **Regional or provincial** labour (PSA LFS regional; PDF only) and remittance (PSA Survey on Overseas Filipinos, yearly regional) data |
| Measured provincial food insecurity | SWS is regional; Eq. 3 is a modelled proxy | FNRI ENNS provincial FIES (2021: Batangas 29.7%, Cavite 31.7% exist for 2 provinces only); PSA FIES provincial estimates if published |
| Objective 1 validation | No human labels | Two annotators label the 300 headlines (`annotation/ANNOTATION_GUIDE.md`), then `obj1_annotation_v2.py disagreements` and `score` |
| Objective 5 ISO/IEC 25010 | No responses | 50 DA Region IV-A evaluators (`OBJ5_ISO25010_INSTRUMENT.md`, `OBJ5_ANALYSIS_PLAN.md`) |
| FNRI face validity | No 2019 CALABARZON regional figure exists (`OBJ5_FNRI_FACE_VALIDITY.md`) | Adviser approval of the corrected wording (2021 provincial + 2023 regional) |
| Adoption of a provincial model | Development evidence only | Team and adviser decision |

## 3. Data found (with availability)

| Data | Source | Coverage | Available at origin | Used |
|---|---|---|---|---|
| Provincial food and all-items CPI YoY | PSA OpenSTAT `2M/PI/CPI/2012/0012M4ACPI2`, `2018/0012M4ACP10`, E40 file | 2012-01..2026-09, the 5 provinces | Month m usable at issue when m ≤ issue month − 2 | Yes (Part B) |
| SWS BL hunger | existing | 1998..2026-Q2 | When published (release dates in the table) | Yes |
| Unemployment | PSA OpenSTAT LFS | **National** quarterly only | Yes | E1 (national) |
| OFW remittances | BSP | **National** quarterly | Yes | E2 (national) |
| Provincial food-insecurity prevalence | DOST-FNRI ENNS/NNS | 2021 Batangas and Cavite; 2023 regional | Yearly, lagged | Face validity only |
| LGU outcome data | none found | — | — | **None exists**; LGU rankings cannot be outcome-validated |

## 4. Files added in this run (uncommitted)

**Pre-registrations:**
- `PREREGISTRATION_D.md`
- `PREREGISTRATION_FI.md`

**Scripts:**
- `runner/cb6d_model.py`
- `runner/fi_regional.py`
- `runner/fi_provincial.py`

**Raw data:**
- `data/raw/` (2 CSV files + `FETCH_LOG.json`)

**Outputs:**
- `out/cb6d_*`
- `out/fi_*`

**Reports:**
- `PROVINCIAL_CB6_IMPROVEMENT_REPORT.md` (updated)
- `REMAINING_ISSUES_RESOLUTION.md`
- `OBJECTIVE_COMPLETION_MATRIX.md`

## Update (2026-11-04): Lead 2

| Issue | Done | Result |
|---|---|---|
| Why Lead 2 fails R2/R3 | Error decomposition (oracle) | The hunger part causes 67% of the errors; with the true hunger, accuracy would be 0.888. The price part is weaker too (corr 0.36) |
| Improve Lead 2 | Pre-registered X2 (`PREREGISTRATION_X2.md`): forecast combination, province mean reversion, walk-forward calibration, with ablations | **Not achieved.** X2 is worse (L2 acc 0.664; L1 0.712). ENS −0.003 Brier (n.s.); FE ±0; CAL +0.024–0.038 (worse: regime shift 2013–20 → 2021–26). C-B6D-E-X stays the best |
| Untouched test data | Prospective seal of the 2026-Q4 / 2027-Q1 provincial forecasts (C-B6D-E-X, X2) | SHA-256 2c1ff50a…; score when SWS and PSA publish |

**Remaining blocker for Lead 2:** two-quarter-ahead regional hunger skill (about 0.72–0.79 for every available model).
It needs earlier or more frequent hunger or food-insecurity data, not model changes.


## Update (2026-11-04): paper-aligned Lead 2 attempt (XH)

| Issue | Done | Result |
|---|---|---|
| Use only the paper's variables | Read Ch. I (1.2, 1.3, 1.4, 1.5.2) and the Ch. III families (H1, N1, E1, E2); built H1/N1 momentum, threshold run, other SWS areas, FSSI momentum (`PREREGISTRATION_XH.md`) | Leakage check passed; C-B6E and C-B6D-E-X reproduced exactly |
| Paper baselines (RQ3) | Added the provincial logistic regressions: combined, government-only, NLP-only | XH beats them significantly at Lead 2 (combined, government-only) and NLP-only at Lead 1; not CLIM or PSA-only after Holm |
| Lead 2 | C-B6D-E-XH | **Not fixed:** accuracy 0.708, balanced 0.666 (R2, R3 fail). Momentum helps Lead 1 hunger (p 0.031), not Lead 2 |
| Lead 1 | C-B6D-E-XH | R1–R7 pass; best AUC (0.767) and Brier (0.173); not adopted (the rule required the Lead 2 fix) |
| Untouched data | Sealed the XH forecasts for 2026-Q4 / 2027-Q1 | `out/seal_prospective_XH.sha256` 1709044f… |
| Eq. 3 cut-off | Checked against the paper | The paper says "median of all province-quarters". 11.0 (2021–22 median) is the leak-free version and **needs adviser approval** (unchanged) |

**Final Lead 2 status:** not reliable with the paper's variables on 2013–2026. Algorithm 3 = 1 quarter for the provincial
forecast. Resolution needs data (earlier or more frequent hunger and food-insecurity readings; 2027+ prospective
quarters), not further modelling.

## Update (2026-11-05): province-specific non-price evidence

| Issue | Done | Result |
|---|---|---|
| Why provinces differ only through prices | Traced to Eq. 3: H is regional, D is the only province term | Structural; needs an adviser decision to change |
| Province non-price data | Verified PSA provincial crops (1987+), fisheries (1993+), subsistence and poverty incidence (2018/2021/2023); employment and OFW national only | `data/raw_prov/` with SHA-256 |
| Candidate | C-B6D-E-XA (crop and fisheries shocks), pre-registered | No gain; not adopted; C-B6D-E-X unchanged |
| Independent provincial validation | Part V vs PSA subsistence and poverty incidence | Consistency not shown (p 0.25–0.80); low power (n = 5/year, CV up to 59%) |
