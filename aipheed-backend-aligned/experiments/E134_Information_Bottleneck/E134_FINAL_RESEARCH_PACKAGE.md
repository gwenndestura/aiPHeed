# AIPHEED E134 · Resolving the predictive information bottleneck: final research package

**Evidence status.**
- Protocol `139ca7f` was frozen before any E134 candidate was computed (sha256 in `runner/PROTOCOL_SHA256.txt`).
- Every SWS value from 2021-Q2 to 2026-Q3 had already been seen, so **all results here are development evidence**.
- Confirmation is only prospective (`E134_PROSPECTIVE_VALIDATION_PROTOCOL.md`).
- Production, the dashboard, FIRI v2/FIRI3 and the E131–E133 seals are unchanged.

## Decision: **B. A viable path is not yet demonstrated.**

**What E134 did:**
- **Acquired new 2021+ data:**
  - NASA POWER daily climate at 18 regional centres covering all four SWS areas and at the five provinces;
  - PSA quarterly palay production by region;
  - FIES 2023 provincial expenditure, income and savings by decile.
- **Built drivers at the target's own geography** and tested them under the frozen rules.
- **Audited** the target, the geography and the 2024 surge.

**What it found:**
- **No new information closes the gap.**
  - The area climate and agriculture drivers worsen Lead-2 MAE: 4.87 → 5.39 when added to HFM-X.
  - The rainfall deficit helps only at Lead 4.
- **The best Lead-2 agreement stays at 0.50** (20 of 40 rows); 75 % needs 30 of 40.
- **No lead is reliable.**

**What is still missing:**
1. Household-level stress dynamics (income, savings, debt) at quarterly frequency and SWS-area or provincial geography.
2. Enough episodes of large true change to learn their size.
3. Unseen quarters.

What would supply each is in §5.

---

## 1. E133 baseline (verified)

`out/e134_baseline_record.json`: E133 reproduced exactly (524 rows, maximum forecast difference 0.0, metric difference 0.0).

| Claim | Verified value |
|---|---|
| HFM-X Lead-2 within, S-U (40 rows, 10 quarters) | 0.50 |
| HFM-X MAE / RMSE | 4.87 / 6.42 |
| Sharp increases caught | 8 of 16 |
| 75 % at any lead, any model | No |
| Any lead passing N1–N7 | No |
| High-tercile bias | −7.14 |
| Trigger groups at Lead 2 | None demonstrated |
| PH2 (ONI) | Lead-2 MAE 4.27, within 0.50, post-hoc |
| Provincial | Model-based only |

**Seals (hashes unchanged):**
- E131 `92b5535f`;
- E132 `cea5a2ec` / `a1f80d57`;
- E133 `efba3235` / `76c2388a`.

**Production:**
- served map: the P0H4 ch1 engine (`backend/data/ch1_engine/rows.csv`; `AIPHEED_CH1_ENGINE` unset);
- thesis governing config: MODEL-B2, not served (`backend/config/governing_model.json`).

## 2. Data investigation (Phase 1)

- **Full inventory:** `E134_DATA_SOURCE_INVENTORY.csv` (29 sources: dataset, organization, geography, period, frequency, release lag, access, alignability, construct).
- **Acquisitions:** `E134_DATA_ACQUISITION_LOG.md`.

**Household stress (1.2).**
- **Available:** FIES 2023, which gives provincial food-expenditure shares and savings by decile. Acquired.
- **Not available:**
  - quarterly or area-level income, savings, debt, meal-skipping or borrowing series;
  - the LFS at regional or quarterly level (it is in releases only, not on OpenSTAT);
  - remittances at household or regional level;
  - social-assistance coverage at quarterly level (the DSWD registry is not public).

**Local climate and disasters (1.3).**
- **Acquired:** NASA POWER daily precipitation and temperature, 2021-01-01 … 2026-09-30.
- **Not acquired:**
  - PAGASA station data (formal request);
  - NDRRMC and DA damage reports (event PDFs, not a dated panel).

**Agriculture (1.4).** Palay production by quarter and region acquired, 2021-Q1 … 2026-Q3.

**Pre-2021 feasibility (1.1; analysis only, nothing loaded).**

| Item | Finding |
|---|---|
| Data already held | Branch `aiPHeed/e114-genuine-forecast` (`de05c5d`) holds SWS 4-area rounds 1998–2026 (`sws_rounds_1998_2026.csv`, with release-date evidence) and covariates: CPI, LFS, ONI, palay, IBTrACS (`cov_*.csv`) |
| What it would add | Many more large moves to learn from: the 2008 rice-price crisis, 2011–12 swings and the 2020 pandemic peak. In 2021+ the models learn shock size from one episode (E134 event analysis). |
| Prior evidence | E114 on untouched 2013–2020 found LightGBM beat persistence on level, damped mean reversion beat it, and the triggers added nothing (`e114_genuine_forecast`). So more history is **not guaranteed** to close the gap. |
| Provisions that would need amendment | (a) the owner's rule "study window 2021+; never use pre-2021 data" (E25/E39/E110); (b) E131–E134 protocol scope lines "study window 2021+"; (c) training windows in `e133_run`/`e134_run` (`T0 = 2021-Q2`; loaders assert ≥ 2021); (d) new design-break handling for pre-2021 SWS methodology changes, including 2020 pandemic-era fieldwork |
| What would stay unchanged | Target, tolerance, 75 %, leads, N1–N7, and the 2021+ evaluation sets S-U/S-E132 (for comparability) |
| Status | **Needs explicit owner approval.** Not done. |

## 3. Measurement, geography and events

- **Target audit** (`E134_TARGET_MEASUREMENT_AUDIT.md`).
  - SWS remains the primary target. PFDR, FNRI and FIES are separate reference tracks; they are not averaged.
  - Sampling variance is only **8–15 %** of Lead-2 MSE (HFM-X 12 %). The error is true change, not noise.
- **Geography** (`E134_GEOGRAPHIC_ALIGNMENT_AUDIT.md`).
  - Drivers are aggregated from regions to SWS areas; the target is modelled at its own geography.
  - The provincial stage is separate and labelled.
  - FSSI (5 IV-A provinces) cannot represent Balance Luzon. Its correlation with the residual: ρ = 0.19, p = 0.67.
- **Events** (`E134_EVENT_ANALYSIS.md`).
  - **Onset:** rice price and ONI signals of the 2024 surge were published three quarters ahead, and HFM-X caught the onset.
  - **Escalation:** no driver was more extreme during the 2024-Q3/Q4 escalation, so its size (+11 to +12 nationally; +16 to +22 in Visayas and Mindanao) was not anticipable with held data.
  - **2026-Q1:** falling rice prices pointed down, but hunger rose +4.6. Post-break design structure explains part of this, and SEAS-LLM caught it.

## 4. Models and results (Phases 5–8)

**Lead 2, P-DASH** (`E134_MODEL_COMPARISON.csv`, `E134_WALK_FORWARD_RESULTS.csv`):

| Model | S-U within | S-U MAE | S-E132 within | S-E132 MAE | Surge 2024 within | Post-break within |
|---|---|---|---|---|---|---|
| PERSIST | 0.40 | 5.98 | 0.46 | 5.28 | 0.25 | 0.50 |
| SEAS-LLM | 0.45 | 5.72 | **0.61** | 4.78 | 0.06 | **0.71** |
| **HFM-X (selected)** | **0.50** | 4.87 | 0.43 | 4.96 | **0.56** | 0.46 |
| E134-AREA-T (+ area rain, palay) | 0.50 | 5.39 | 0.43 | 5.67 | 0.56 | 0.46 |
| E134-AREA-O (+ ONI) | 0.48 | 4.85 | 0.39 | 5.24 | 0.56 | 0.42 |
| E134-ONI (PH2) | 0.50 | **4.27** | 0.43 | 4.47 | 0.56 | 0.46 |
| E134-ENS (HFM-X + SEAS-LLM) | 0.48 | 4.81 | 0.50 | 4.42 | 0.31 | 0.58 |

**Selection** (frozen rule): HFM-X (tied 0.50 with E134-AREA-T; lower MAE).

**Trigger groups and new drivers** (`E134_FEATURE_CONTRIBUTION_REPORT.csv`; criterion: removal worsens MAE and within, with p < 0.10):

| Driver / group | Demonstrated at |
|---|---|
| Employment (E) | Lead 3 |
| News (N) | Lead 4 (tiny) |
| Area rainfall deficit (aR) | Lead 4 (Δ MAE +0.46, Δ within −0.06, p < 0.001) |
| Palay drop (aP) | None; it hurts at every lead (removing it improves MAE by 0.17–0.65) |
| Market, climate (typhoons/ONI), poverty | None |

**Nothing is demonstrated at Lead 2.**

**Reliability** (`E134_LEAD_RELIABILITY_REPORT.md`):
- HFM-X fails N2 and N5 at Lead 2.
- No model passes N1–N7 at any lead.
- **Maximum reliable lead: none.**

**Generalization, bias and overfitting** (`E134_GENERALIZATION_BIAS_OVERFITTING_REPORT.md`):
- **No model generalizes across regimes.** Driver models work in the surge; level and design models work after the break.
- Mindanao and Visayas are weakest.
- The high-tercile bias stays at about −7, of which about 2 points is irreducible.
- Adding inputs overfits.

**Leakage and calibration** (`E134_LEAKAGE_AND_CALIBRATION_AUDIT.md`):
- No material leakage. The only residual risk is the data vintage.
- HFM-X 80 % coverage is 0.70–0.75, but only 0.46 during surges and 0.61 in Visayas and Mindanao.

**Provincial** (`E134_PROVINCIAL_ESTIMATION_REPORT.md`):
- The estimates are model-based and not validated.
- **New:** FIES 2023 household-stress indicators rank provinces almost unrelated to PFDR (Spearman 0.0 / −0.1). Quezon ranks most stressed on household stress but 4th on PFDR. **The provincial ordering is measure-dependent.**

## 5. Remaining gap and what would supply the missing information

**Gap (frozen criteria, Lead 2, S-U):**
- **Agreement:** 0.50 against 0.75, i.e. 20 against 30 of 40 rows. The excess error beyond sampling must fall from RMSE 6.0 to about 2.35.
- **Required explained change:** about **74 %** of the true-change variance three quarters ahead must be predicted (E133 D1).
- **Rules:** N2 and N5 fail.
- **Sample:** N1 needs ≥ 10 unseen quarters.

| Missing information | Institution / dataset | Acquisition step | Expected role |
|---|---|---|---|
| Quarterly household income, employment hours and informality at regional level | PSA LFS regional quarterly tables (in releases) | Manual extraction with release dates (no request) | E group at area level |
| Household savings, debt, coping (meal skipping, borrowing for food) | SWS / FNRI / BSP Consumer Expectations Survey (household finance outlook, quarterly, national; not checked in E134) | Data request or table extraction | Escalation-size signal |
| Local disaster impact (affected families, crop damage) | NDRRMC, DA | Manual coding of situation reports, dated by publication | Area C at event level |
| Station climate | PAGASA | Formal request | Validation of NASA POWER |
| Provincial food-insecurity measurement | PSA/LGU CBMS 2024 FIES; FIES 2021 PUF; future FNRI rounds | Data request (owner decision) | Provincial validation |
| More episodes of large change | SWS 1998–2020 (already held on the E114 branch) | **Owner approval of a protocol amendment** | Learning shock size |
| Unseen quarters | SWS 2026-Q4 onward | Score the seals quarterly | N1 and confirmation; ≥ 10 Lead-2 quarters gives the earliest decision in 2029-Q3 |

## 6. Final scorecard

| Research objective | Required | Status | Evidence |
|---|---|---|---|
| Numerical agreement | ≥ 75 % within frozen tolerance | **NOT ACHIEVED** | Best 0.50 (S-U) / 0.61 (S-E132) |
| Lead 2 | Pass N1–N7 | **NOT ACHIEVED** | HFM-X fails N2, N5 |
| Maximum reliable lead | Established by N1–N7 | **ACHIEVED (none)** | No lead passes, on 2021+ evidence |
| Actual food insecurity | Target remains hunger | **ACHIEVED** | SWS measured hunger; CPI, poverty and FIRI never targets |
| Five trigger groups | Contributions demonstrated | **PARTIALLY ACHIEVED** | E (Lead 3), N (Lead 4), area rain (Lead 4); none at Lead 2 |
| Overfitting | Controlled and documented | **ACHIEVED** | Tight priors; added inputs shown to overfit and rejected |
| Generalization | Unseen periods and areas | **NOT ACHIEVED** | Fails across regimes and areas in development data; unseen-period test only prospective |
| Bias | Assessed, addressed where possible | **PARTIALLY ACHIEVED** | Assessed; high-hunger bias not reduced |
| Leakage | None material | **ACHIEVED** | Audit and tests |
| Calibration | Frozen N7 | **PARTIALLY ACHIEVED** | N7 met at Leads 1, 2 and 4; poor in surges and in Visayas/Mindanao |
| Provincial estimates | Defensible, labelled | **PARTIALLY ACHIEVED** | Labelled model-based; ordering measure-dependent |
| Prospective validation | Independent, reproducible | **NOT YET TESTABLE** | Protocol and seal frozen; first scoring around January 2027 |

## 7. Comparison with E133

| Aspect | E133 | E134 |
|---|---|---|
| Best Lead-2 within (S-U) | 0.50 (HFM-X) | 0.50 (HFM-X, unchanged) |
| New data | Bottom-30 % CPI | Area climate (18 regional points), regional palay, FIES 2023 provincial stress |
| New-data effect at Lead 2 | B30: worse (0.425) | Area drivers: worse MAE (5.39) |
| Geography | National drivers | Drivers at SWS-area geography |
| Target uncertainty | τ² ≈ 0 | Sampling = 8–15 % of MSE (quantified) |
| ONI | Post-hoc PH2 | Registered for prospective test (E134-ONI) |
| Provincial | Model-based | Model-based + measure-dependence shown |
| Decision | Not met | **B: viable path not yet demonstrated** |

## 8. Production

- **Nothing changes.**
- HFM-X and the registered hypotheses are prospective candidates only.
- Adoption follows the prospective protocol.
