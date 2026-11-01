# AIPHEED E133 · Forecasting breakthrough search: final research package

**Status of the evidence.**
- Every SWS value from 2021-Q2 to 2026-Q3 had been seen in earlier work. All walk-forward results below are therefore **development evidence**. The only confirmatory test is the prospective seal (§12).
- Protocol `9683aad` was frozen (sha256 `249775d0…`) before any E133 candidate was computed. The only earlier computation was the reproduction of E132.
- Two variants, **PH1** and **PH2**, were added after the first run. They are labelled *post-hoc* everywhere and cannot be selected (`DEVIATIONS.md` V3).

**Headline.**
- **What improved.** The frozen rule selects **HFM-X**: a hierarchical factor state-space model with one theory-signed driver per trigger group inside the state equation. At Lead 2 on the 40-row primary set (S-U: 10 quarters, 2024-Q1 … 2026-Q3, including the 2024 surge) it reaches:
  - **0.50 within tolerance**, against 0.45 for SEAS-LLM and 0.40 for persistence;
  - **MAE 4.87**, against 5.72 for SEAS-LLM and 5.98 for persistence;
  - **8 of 16** sharp increases caught (SEAS-LLM 3, persistence 0);
  - **p = 0.089** against persistence on squared error;
  - passes N1, N3, N4, N6 and N7.
- **What did not.** HFM-X fails **N2** (needs 0.75) and **N5** (stability).
  - **No model reaches 75 % at any lead, under either issue policy, on either evaluation set.**
  - **No lead is reliable; the maximum reliable lead is none.**
  - On the later 28-row set (S-E132), SEAS-LLM stays the best at Lead 2 (0.61); HFM-X scores 0.43 there.
- **Why 75 % is out of reach with this data.**
  - With 2021–2026 dynamics, the true change in hunger over the Lead-2 horizon has a standard deviation of about 4.6 points.
  - Reaching 75 % needs a true-level error SD of at most about 2.35 points.
  - So any predictor would have to explain about **74 %** of the true-change variance three quarters ahead (D1).
  - The best signals found explain part of **one** episode (the 2023–24 rice-price and El Niño shock).

**Reproduce:** `README.md`.

**Data window:** 2021+ only.

**Production:** unchanged.

---

## 1. Root-cause report

| # | Suspected cause | E133 test (sample, period) | Finding | Status |
|---|---|---|---|---|
| R1 | **True change dominates** (E132 oracle) | D1: HFM-NS fitted to all 80 area-quarters to 2026-Q3 | Common-level variance q_c = 4.84 per quarter; area deviation q_d = 6.38 with ρ = 0.26. Over the median Lead-2 horizon (h = 3) the SD of true change is **4.62**; the required true-level error SD is **2.35**. Even perfect knowledge of today's true level gives 0.54. A predictor must explain **74 %** (Lead 1: 68 %; Lead 4: 81 %). | **Binding.** This is the root cause. |
| R2 | The process changed regime in 2024 | D1 on data before 2024-01-01 | Before the surge, q_c = 0.58, so true-change SD was 2.7 and only 23 % would have needed explaining. The 2024 surge raised the fitted common variance 8-fold. Pre-surge history could not teach a model how large moves are. | Confirmed; not fixable with 2021+ data |
| R3 | Area noise treated as level change (E132 per-area models) | HFM against LLM, S-U, Lead 2 | Pooling helps a little (MAE 5.65 vs 5.67; within 0.40 vs 0.38) | Minor |
| R4 | Non-sampling measurement noise | HFM-NS, τ² estimated by maximum likelihood | τ² stays at its lower bound (0.01) at every issue. SWS rounds are internally consistent with their published margins. The SWS–OCTA gap (MAE 5.2) is **between** instruments and does not show up as SWS round-to-round noise. | Rejected as a cause of forecast error |
| R5 | 2025 design alternation | HFM-NS-DES | Small gain (MAE 5.65 → 5.51 on S-U; 4.60 → 4.41 on S-E132) | Partly resolved (E132 H1, data-prompted) |
| R6 | **Trigger groups mis-represented** (residual correctors on ~40 rows, E131/E132) | HFM-X: one signed driver per group in the transition, nowcast through the publication gap | Lead-2 MAE 5.51 → **4.87** (p 0.21 for the joint driver effect); sharp increases caught 2 → **8 of 16** | **Partly resolved.** Representation was a real part of E132's failure. |
| R7 | Missing leading information | D2 screen of 54 point-in-time features | Only **ONI** (ENSO) passes Holm at Lead 1 (ρ = 0.78, p_Holm = 0.003, 18 issues). Lead 2: ρ = 0.64, p_Holm = 0.22. Rice price change: ρ = 0.43 at Lead 2 (p 0.10). The ONI signal rests on one El Niño (2023–24). | Signal exists, rests on one episode |
| R8 | Symmetric price response | HFM-X's largest miss: 2026-Q1 (MAE 9.3). Falling 2025 rice prices pushed the forecast down; hunger stayed high. | Post-hoc PH1 (shocks only) is **worse** (Lead-2 within 0.35) | Asymmetry not supported |
| R9 | High-hunger under-prediction is shrinkage | D4: ORACLE-LEVEL (true target level known) | Even it under-predicts the high tercile by **2.0** points (selection on noisy observations). The other ~5 points are lag (ORACLE-NOW −7.5 to −8.3, like persistence). | Lag, not shrinkage (§5) |
| R10 | Information horizon | P-REL against P-DASH | HFM-X-B30 reaches 0.60 at Lead 2 under P-REL, against 0.425 under P-DASH | Issue timing matters; P-REL would need owner approval |
| R11 | Evaluation power | Lead-2 S-U: 10 quarters, 40 rows (N1 met exactly); Leads 3–4 fail N1 | Leads 3–4 cannot be validated with 2021+ data | Prospective only |

## 2. New-data investigation

**Acquired in E133:**
- PSA OpenSTAT **CPI for bottom-30 % income households** (2018 = 100), table `DB/2M/PI/BIH/2018NEW/0022M4ABIR1.px`.
  - All regions and provinces; items all / food / rice.
  - **Year ≥ 2021 in the query**, so no pre-2021 row was downloaded.
  - 2021-01 … 2026-09; sha256 `07c49bce…`; `data/raw/`, `data/acquisition_log.json`.
  - Release: monthly, with the national CPI (early the next month).
  - Limitation: it covers prices only, not income.

**Already held and re-audited for point-in-time use** (E119 `E119_POINT_IN_TIME_VALIDATION.csv`; E131/E132 logs):

| Family | Series | Geography | Frequency | Available at issue |
|---|---|---|---|---|
| A1–A3 market | Area CPI: all, food, rice (E131) | 18 regions → 4 areas | Monthly | Day 10 after the month |
| A1–A3 market | Bottom-30 % CPI (E133) | Regions | Monthly | Same |
| A1–A3 market | Farmgate palay (E119) | IV-A | Quarterly | E119 period rule (one quarter back) |
| C1, C2 climate | ONI, El Niño state, typhoons in PAR, rainfall and temperature anomalies (E119) | National / IV-A | Quarterly | One quarter back |
| C3, C4 production | Palay and corn drop, fisheries drop (E119) | IV-A | Quarterly | One quarter back |
| E1, E2 employment / OFW | Unemployment rate and change (LFS); remittance decline (BSP) | National | Monthly to quarterly | One quarter back |
| E1, E2 employment / OFW | Regional daily pay and unemployment (E132) | Regions | Annual | 30 June of the next year |
| N1 news | GDELT shares: shortage, agri supply, jobs/income, assistance (E119) | National | Quarterly | One quarter back |
| N1 news | FSSI v2 | 5 CALABARZON provinces only | Quarterly | — |
| V1 poverty | PSA poverty 2021/2023/2025 | Regions | Triennial | Release dates (E131) |
| H1 hunger history | SWS 4 areas | 4 areas | Quarterly | Publication date per round |

**Investigated and not obtainable as a usable quarterly series** (provenance only; no values fetched):
- **Provincial income:** LFS provincial estimates are annual and released late. FIES is triennial; the 2023 PUF is held and used in E131. CBMS rounds are irregular and LGU-held.
- **Food consumption:** FNRI ENNS/NNS is held at regional level for 2023 and 2025, and at provincial level only for Batangas and Cavite (2021). It is not quarterly.
- **OCTA hunger:** only 7 Balance Luzon readings exist. At **1 of 21** issues was an OCTA reading newer than SWS (D5), so it cannot serve as an early channel historically.
- **Pre-2021 SWS or CPI history** would allow learning from many episodes, but the study window rule forbids it (owner decision).

**OpenSTAT's LFS tables are national-only.** This is confirmed again; no further income-side series at sub-annual area frequency was found.

## 3. Forecasting methodology

| Model | Why appropriate | E132 weakness addressed | Assumptions | Data | Validation |
|---|---|---|---|---|---|
| **HFM** | SWS areas share a national shock; area departures are partly transient. A common factor plus AR(1) area deviations pools information across areas. | Per-area random walks treat area noise as level change | Linear Gaussian; deviations stationary when ρ < 1 | SWS + published margins | Walk-forward, S-U, S-E132 |
| **HFM-NS** | Adds instrument noise beyond sampling (τ²) | Observation-noise treatment | τ² constant | Same | Same; τ² estimated at 0.01 |
| **HFM-NS-DES** | 2025+ alternating design (E132 rule, pooled) | Design change | Effect stable by quarter of year | Same | Same |
| **HFM-TREND** | Momentum: coping exhaustion makes surges persist | Sharp increases | Damped slope | Same | Same: **worse** (overshoots after peaks) |
| **HFM-X** (candidate) | Drivers move the true level: market (rice CPI change), climate (typhoons), employment (unemployment change), news (shortage share), and vulnerability (poverty × market, by area). Signs come from theory, with prior N(0, 1); the gap between the latest SWS and the target is nowcast with drivers already published. | The five groups were used as residual correctors on deltas and overfit | Linear, sign-constrained, centred drivers | Point-in-time drivers | Walk-forward, ablation, prior sensitivity |
| HFM-X-B30 | Market driver from the bottom-30 % food CPI | Household purchasing power | Same | B30 CPI | Same |
| ENS133 | SEAS-LLM + HFM-NS-DES | Combination | — | — | Same |
| HFM-X-PH1 (post-hoc) | Drivers as shocks only | Asymmetry (R8) | — | — | Not selectable |
| HFM-X-PH2 (post-hoc) | ONI as the climate driver | D2 screen | — | — | Not selectable |

**Considered and not run, with reasons:**
- **Markov regime switching:** one surge in 2021+ cannot identify transition probabilities.
- **Deep or sequence learners and more tree models:** E131/E132 trees overfit (training MAE 2.1 against out-of-sample 6.1–6.3) on 40–100 rows.
- **Bayesian hierarchical models with informative elasticities:** the only structural elasticity available (FIES price effect on subsistence incidence, E131 X3a: +0.1 to +1.7 points) is far smaller than the 2024 SWS surge (+13 points), so it cannot explain the target's changes.

**Fitting rules.** Every model is refitted at every issue on rounds published before it:
- pooled maximum likelihood;
- the documented 2025-Q2 respondent-base break gets extra level variance;
- 2021+ data only.

## 4. Event-level early-warning analysis

**Events:** the 16 Lead-2 sharp increases on S-U (y − y_latest > 2·SE; P-DASH). Seven of them are E132's S-E132 events. Detail: `out/d3_sharp_increase_events.csv`. z values are in-fold standardized drivers at the issue.

| Issue → target | Areas (increase) | Signals at issue | Persistence | SEAS-LLM | **HFM-X** |
|---|---|---|---|---|---|
| 2023-10-01 → 2024-Q1 | BL (+4.0), Visayas (+5.7) | Rice z +1.93 (2023-Q2); unemployment change z +1.06 | miss | miss | **both within** |
| 2024-01-01 → 2024-Q2 | BL (+9.3), Visayas (+7.0), Mindanao (+9.0) | Rice z **+2.76** (2023-Q3); typhoons +0.95; unemployment +1.67; news +0.80 | miss | miss | **all 3 within** |
| 2024-04-01 → 2024-Q3 | MM (+9.0), BL (+3.8), Visayas (+16.7), Mindanao (+18.7) | Rice z +1.65 (2023-Q4) | miss | miss | MM within; 3 missed (forecast +0.5 to +3.3 points against +3.8 to +18.7) |
| 2024-07-01 → 2024-Q4 | BL (+10.0), Visayas (+9.4), Mindanao (+21.6) | Rice z +1.53 | miss | miss | all missed (forecast −1.2 to +6.8 points against +9.4 to +21.6) |
| 2025-10-01 → 2026-Q1 | BL (+6.3), Visayas (+7.3) | Rice z **−2.20** (falling prices) | miss | **both within** (design effect) | missed: forecast *down* |
| 2026-04-01 → 2026-Q3 | MM (+6.7), BL (+6.9) | Neutral | miss | MM within | **both within** |

**Findings.**
1. **The onset of the 2024 surge was foreseeable.**
   - The rice-price driver was 1.9–2.8 SD high three quarters before the 2024-Q1 and Q2 targets, and HFM-X caught 5 of 5 onset rows.
   - D2 shows that ENSO (El Niño, mid-2023 to early 2024) also led the surge.
2. **The magnitude of the 2024-Q3/Q4 peaks was not foreseeable.**
   - Visayas and Mindanao rose by 16–22 points when no driver was more extreme than it had been at the onset.
   - These jumps are larger than anything the in-fold model had seen (pre-surge q_c = 0.6).
3. **Post-2025 increases are design or season, not drivers.** SEAS-LLM's quarter-of-year effect catches 2026-Q1, while HFM-X's price driver points the wrong way.
4. **What was missing.**
   - A driver for the 2024-Q3/Q4 escalation. No held series shows it. The candidates (household savings depletion, food-expenditure share, the July–September 2024 typhoon sequence in Visayas and Mindanao) have no 2021+ area-quarter measurement.
   - An area-level climate driver. The C group is national or IV-A only.

## 5. High-hunger prediction analysis

**Bias by observed-level tercile, Lead 2, P-DASH** (`out/d4_high_hunger_bias.csv`):

| Model | S-U low | S-U mid | S-U high | S-E132 high |
|---|---|---|---|---|
| ORACLE-LEVEL (true target level known) | +1.07 | +0.18 | **−2.01** | −1.94 |
| ORACLE-NOW (true current level known) | −0.59 | −1.47 | −8.29 | −7.48 |
| PERSIST | −0.21 | −1.36 | −7.77 | −6.86 |
| SEAS-LLM | −0.85 | −1.23 | −7.64 | −6.68 |
| **HFM-X** | +1.62 | −2.10 | **−7.14** | −6.77 |
| HFM-TREND | +0.92 | +0.61 | −6.69 | −5.00 |

**Interpretation.**
- About **2 points** of the high-tercile bias are unavoidable for any forecaster of the true level, because observations in the high tercile carry positive sampling error on average.
- The remaining ~5 points come from **lag**: forecasts start from the last true level, and the high tercile is mostly the 2024 surge.
- The loss function and shrinkage are not the cause. ORACLE-NOW, which applies no shrinkage, is as biased as persistence.
- **The momentum model (HFM-TREND)** cuts the high-tercile bias, to −6.7 on S-U and −5.0 on S-E132, but over-predicts elsewhere (Lead-2 MAE 6.97, within 0.33), producing false alarms. **Rejected.**
- **HFM-X** cuts the high bias by 0.6 points and raises the low-tercile bias to +1.6.
- **Not solved.**

## 6. Trigger-group contribution report

**Controlled ablation** on HFM-X, S-U, P-DASH. Criterion fixed in the protocol: removing the group must worsen MAE **and** within, **and** the paired cluster bootstrap must give p < 0.10 (`out/e133_trigger_contribution.csv`).

**Δ MAE when the group is removed** (positive means the group helps):

| Group (FIRI v2 family) | Lead 1 | Lead 2 | Lead 3 | Lead 4 | Demonstrated at |
|---|---|---|---|---|---|
| A market (A1–A3; rice CPI q/q) | −0.24 | **+0.14** (p 0.45) | −0.21 | −0.32 | — |
| C climate (C1, C2; typhoons) | −0.15 | −0.31 | −0.23 | −0.06 | — (hurts) |
| E employment / OFW (E1; unemployment change) | −0.14 | +0.16 (p 0.20) | **+0.93 (p 0.025)** | +1.07 (within unchanged) | **Lead 3** |
| N news (N1; GDELT shortage share) | +0.03 | +0.04 (within unchanged) | +0.04 | **+0.05 (p < 0.001)** | **Lead 4** (tiny) |
| V poverty (V1; × market by area) | −0.01 | −0.01 | +0.01 | −0.03 | — |
| H history (H1) | The state itself | | | | Always the main signal |

**All drivers jointly** (HFM-X against HFM-NS-DES), Lead 2: MAE 5.51 → 4.87, within 0.40 → 0.50, p = 0.21. **Not significant.**

**Status.**
- **Investigated:** all five groups and every FIRI v2 family (A1–A3, C1–C4, E1–E2, N1, V1, H1), in the D2 screen and in HFM-X.
- **Useful information** (diagnostic):
  - market: rice change leads the 2024 onset (§4);
  - climate: ONI, Holm-significant at Lead 1 in D2. The protocol's typhoon representation was the wrong one. Post-hoc PH2 with ONI has the lowest Lead-2 MAE of any model, 4.27 (p = 0.011 against persistence), but its within share is still 0.50;
  - employment: unemployment change.
- **Demonstrated under independent evaluation:**
  - E at Lead 3 and N at Lead 4 only (small effects; development data);
  - **none at Lead 2.**
  - No group has a contribution confirmed on unseen data. That needs the seal.
- **Bottom-30 % CPI as the market driver** (HFM-X-B30): Lead 1 improves (0.59, MAE 4.45, p = 0.003 against persistence); Lead 2 falls to 0.425.

**NLP.**
- The XLM-R / BERTopic / FSSI pipeline (`backend/app/news/`) produces **provincial CALABARZON** indices (FSSI v2, 5 provinces), many quarters marked `NO_USABLE_EVIDENCE`.
- It cannot be aligned with the 4 SWS areas. Only Balance Luzon contains IV-A, and FSSI covers only five of BL's provinces.
- The quarterly national news signal used here is GDELT topic shares. NLP-ONLY (E132) reaches 0.39 at Lead 2.
- The news group is **investigated, weakly useful** (N at Lead 4), and its representation is geographically mismatched with the target.

## 7. Model comparison

**Lead 2, P-DASH.** S-U has 40 rows and 10 quarters; S-E132 has 28 rows and 7 quarters (`out/e133_metrics.csv`).

| Model | S-U within | S-U MAE | S-U RMSE | S-E132 within | S-E132 MAE | Sharp increases caught (S-U, of 16) |
|---|---|---|---|---|---|---|
| PERSIST | 0.40 | 5.98 | 7.71 | 0.46 | 5.28 | 0 |
| LLM (E131) | 0.38 | 5.67 | 7.56 | 0.50 | 4.70 | 0 |
| SEAS-LLM (E132) | 0.45 | 5.72 | 7.58 | **0.61** | 4.78 | 3 |
| HFM | 0.40 | 5.65 | 7.38 | 0.57 | 4.60 | 1 |
| HFM-NS | 0.40 | 5.65 | 7.38 | 0.57 | 4.60 | 1 |
| HFM-NS-DES | 0.40 | 5.51 | 7.31 | 0.57 | 4.41 | 2 |
| HFM-TREND | 0.33 | 6.97 | 8.50 | 0.43 | 6.32 | 3 |
| **HFM-X (selected)** | **0.50** | **4.87** | **6.42** | 0.43 | 4.96 | **8** |
| HFM-X-B30 | 0.43 | 4.90 | 6.39 | 0.50 | 4.83 | 4 |
| ENS133 | 0.40 | 5.38 | 7.33 | 0.54 | **4.29** | 2 |
| HFM-X-PH1 (post-hoc) | 0.35 | 5.53 | 6.69 | 0.50 | 4.79 | 2 |
| HFM-X-PH2 (post-hoc) | 0.50 | 4.27 | 5.70 | 0.43 | 4.47 | 6 |
| PSA-ONLY / NLP-ONLY / RIDGE-ALL (E132) | — | — | — | 0.29 / 0.39 / 0.39 | 8.13 / 5.46 / 7.36 | — |

**Selection** (frozen rule: S-U, P-DASH, Lead-2 within; ties → MAE): **HFM-X**.

**Caution.** The two evaluation sets disagree.
- HFM-X wins on the set containing the 2024 surge.
- SEAS-LLM wins on the post-surge set, which is dominated by the 2025 design alternation.
- No model is best on both.

## 8. Numerical forecasting results (selected model, HFM-X, P-DASH, S-U)

| Lead | Rows / quarters | MAE | RMSE | Bias | Within | 80 % coverage |
|---|---|---|---|---|---|---|
| 1 | 44 / 11 | 4.70 | 6.13 | — | 0.55 | 0.70 |
| 2 | 40 / 10 | 4.87 | 6.42 | −2.53 | **0.50** | 0.75 |
| 3 | 36 / 9 | 5.10 | 6.56 | — | 0.50 | 0.69 |
| 4 | 32 / 8 | 5.51 | 6.80 | — | 0.31 | 0.75 |

**Lead 2 by area:** Metro Manila 0.80, Balance Luzon 0.60, Visayas 0.40, Mindanao 0.20.

**P-REL** (re-issue after each SWS release), Lead 2 on S-U: HFM-X 0.475; HFM-X-B30 **0.60** (the highest under any policy on S-U); persistence 0.50.

**Measurement separation** (directive Part 6):
- **Sampling error:** the target's own SE. A perfect true-level forecaster still scores only 0.90 against the tolerance.
- **Instrument disagreement:** SWS against OCTA, MAE 5.2 (E132 D2). It does not show up inside SWS (τ² ≈ 0).
- **True variation:** q_c and q_d (D1).
- **Forecast error:** the remainder.
- The frozen tolerance counts only the first. It was **not changed**.

**75 %: not achieved.**

## 9. Lead 1–4 reliability report

**HFM-X, S-U, P-DASH** (`out/e133_rules.json`, `out/e133_summary.json`):

| Lead | Fails on S-U | p vs persistence | Fails on S-E132 | Validated |
|---|---|---|---|---|
| 1 | N2, N5, N6 | 0.035 | N1, N2, N5, N6, N7 | No |
| 2 | **N2, N5** (passes N1, N3, N4, N6, N7) | 0.089 | N1, N2, N4, N5, N6 | **No** |
| 3 | N1, N2, N4, N5, N6, N7 | 0.14 | N1, N2, N3, N4, N5, N6 | No |
| 4 | N1, N2, N4, N5, N6 | 0.18 | N1, N2, N3, N4, N5, N6 | No |

**No rule set passes, for any model, lead, set or policy.**
- **Maximum reliable lead: none** (empirically established on 2021+ data).
- **Lead 2: not reliable.**
- Its stability thirds are 0.64 / 0.46 / 0.38: the model does well on the surge onset and worse afterwards.

**Distinctions** (`target.py`):
- Lead k targets quarter D − 1 + k.
- The calendar lead counts from the latest complete quarter.
- The information horizon h counts from the latest SWS quarter: **3 for Lead 2 in most issues**.
- The issue date is the first day of D (P-DASH), or the day after an SWS release (P-REL).

## 10. Generalization and bias report

**Overfitting** (HFM-X):
- 10 parameters for 80 area-quarters.
- In-sample one-step MAE 3.10, against out-of-sample Lead-1 MAE 4.70.
- **Prior sensitivity** (β prior SD) at Lead 2:

  | Prior SD | Within | MAE |
  |---|---|---|
  | 0.5 | 0.475 | 4.79 |
  | 1 (protocol) | 0.50 | 4.87 |
  | 2 | 0.40 | 5.69 |

  A looser prior overfits (`out/e133_prior_sensitivity.csv`).
- **β stability:** the market coefficient rises from 0.41 (issue 2023-Q4) to about 1.0 (2025-Q4), and is 0.58 at the seal. It is learned largely from the one surge.

**Generalization:**
- by area: Mindanao 0.20 against Metro Manila 0.80;
- by regime: thirds 0.64 / 0.46 / 0.38;
- **not demonstrated.**

**Bias:**
- under-prediction overall (−2.5);
- high tercile −7.1, of which about 2 points are irreducible (§5);
- low tercile +1.6.

**Leakage:**
- Drivers are used only once published. CPI is available 10 days after the quarter; E119 drivers on the first issue reporting their period. This is unit-tested.
- Standardization is in-fold.
- Variances and β are refitted at every issue on prior rounds.
- Seasonal effects use post-break innovations available at the issue.
- The break date is documented, not fitted.
- No pre-2021 row is loaded; the B30 query is restricted to Year ≥ 2021 (tested).
- **Caveat:** PH1 and PH2 are post-hoc. ONI was chosen after D2 used outcomes.

**Calibration:** HFM-X 80 % coverage is 0.75 at Lead 2 (N7 passes) and 0.70–0.75 at the other leads. The Kalman filter's log-likelihood equals the exact Gaussian likelihood (unit test, |Δ| < 1e-8).

## 11. Provincial estimation report

**Inventory of provincial measurements** (Cavite, Laguna, Batangas, Rizal, Quezon):

| Measurement | Years | Type | Quarterly? |
|---|---|---|---|
| PFDR (PSA subsistence incidence) | 2021, 2023 | Survey estimate with CI | No |
| FIES 2023 PUF | 2023 | Microdata (held; E131 decomposition) | No |
| FNRI ENNS FIES (moderate + severe) | 2021: Batangas 29.7, Cavite 31.7 only | Survey estimate | No |
| PSA poverty | 2021, 2023, 2025 | Survey estimate | No |
| FSSI v2 news index | 2021–2026 | News-derived, many quarters with no usable evidence | Yes, but not a measurement of hunger |

**Findings.**
- **No independent quarterly provincial food-insecurity measurement exists**, so quarterly provincial forecasts **cannot be validated**.
  - This was checked again in E133; E130 gate G1–G8 found the same.
  - **Small-area estimation** would need a quarterly provincial survey, or survey microdata linked to quarterly covariates. Neither exists (FIES is triennial; SWS publishes no provinces).
  - **Multilevel pooling** across provinces needs a provincial outcome at more than two time points.
- **Income dominates provincial change** (E131 X3a: income effects −6.0 to −0.03 points, against price effects +0.1 to +1.7, 2021→2023). Provincial income is measured only triennially, so quarterly provincial dynamics are not observable.
- **Output.** Provincial values remain **model-based estimates**: Balance Luzon HFM-X forecast × EB-shrunk relative food deprivation (PFDR 2023), with Monte Carlo 80 % intervals that carry the forecast uncertainty and the relative-deprivation CV (0.30–0.37). They are labelled in the seal as *model-based, provincial dynamics inherited from Balance Luzon, validated only at PSA survey rounds*. **They are not measurements and not validated forecasts.**

**Sealed provincial estimates** (`sealed/E133_PROVINCIAL_MODEL_BASED_SEAL.csv`, sha256 `76c2388a…`):

| Province | 2026-Q4 (Lead 1) | 2027-Q1 (Lead 2) |
|---|---|---|
| Batangas | 21.1 [13.5–32.8] | 21.6 [13.5–34.0] |
| Cavite | 16.1 [9.5–27.0] | 16.5 [9.6–27.7] |
| Laguna | 20.2 [12.9–31.3] | 20.6 [12.9–32.3] |
| Quezon | 16.0 [10.0–25.5] | 16.3 [9.9–25.9] |
| Rizal | 28.7 [18.8–43.1] | 29.3 [18.7–44.7] |

## 12. Reproducible code and experiment configurations

**Runners** (backend venv; run from this folder):

| Runner | Purpose |
|---|---|
| `runner/e133_reproduce.py` | E132 reproduction |
| `runner/e133_acquire.py` | B30 CPI |
| `runner/e133_models.py` | Library |
| `runner/e133_run.py` | Walk-forward, metrics, rules, ablation (~70 s) |
| `runner/e133_diagnostics.py` | D1–D5 (~4 min) |
| `runner/e133_sensitivity.py` | Prior sensitivity |
| `runner/e133_summary.py` | Headline numbers |
| `runner/e133_seal.py` | Write-once seal |
| `runner/score_e133.py` | Primary-only scorer |

**Configuration** (fixed in the protocol and `DEVIATIONS.md`):
- grids, bounds, starts and the prior SD are in `e133_models.py`;
- drivers and availability rules are in `e133_run.py`;
- the permutation seed is 133;
- the walk-forward is deterministic.

**Inputs:**
- E110 SWS rounds;
- E131 regional CPI and poverty;
- E119 regional point-in-time dataset;
- E133 B30 CPI (hashed).

**Tests:** `backend/tests/unit/test_e133_breakthrough.py`.

**Area seal:** `sealed/E133_PROSPECTIVE_SEAL.csv` (sha256 `efba3235…`). It covers every E133 model, including PH1 and PH2, for 2026-Q4 … 2027-Q3 (issued 2026-11-01). HFM-X Balance Luzon:
- 2026-Q4: 22.4 [17.4–27.5];
- 2027-Q1: 22.9 [17.0–28.8].

## 13. Thesis-objective assessment

| Objective (directive) | Required | E133 result | Status |
|---|---|---|---|
| Actual food-insecurity target | Independently defensible | SWS measured hunger; τ² ≈ 0 shows rounds are internally consistent | **Achieved** (unchanged) |
| Numerical forecasting | ≥ 75 % within frozen tolerance | Best Lead-2 0.50 (S-U) / 0.61 (S-E132, SEAS-LLM) | **Not achieved** |
| Lead 2 | Passes N1–N7 | HFM-X fails N2, N5 | **Not achieved** |
| Maximum lead | Empirically established | **None** reliable | **Established: none** |
| Forecast food insecurity, not prices | — | Target is measured hunger; drivers move its level | Achieved |
| Five trigger groups | Genuine contribution demonstrated | Investigated all five. Useful information in market, climate (ONI) and employment. Demonstrated E (Lead 3) and N (Lead 4), small, development only; none at Lead 2. | **Partly achieved** |
| FIRI v2 families | All accounted for | A1–A3, C1–C4, E1–E2, N1, V1, H1 (§2, §6) | **Achieved** |
| Model selection | Best appropriate | HFM-X by frozen rule; LightGBM inferior (E131/E132) | **Achieved** as a comparison |
| Overfitting | Acceptable | 10 parameters / 80 observations; tight prior best | Acceptable |
| Generalization | Demonstrated | Uneven by area and regime | **Not demonstrated** |
| Bias | Evaluated and controlled | Evaluated; high-hunger bias not controlled | **Partly** |
| Leakage | None material | Audited and tested | **Achieved** |
| Calibration | Demonstrated | 80 % coverage 0.75 at Lead 2 | **Achieved** at Lead 2 (development) |
| Provincial outputs | Statistically defensible | Model-based, labelled; no quarterly validation possible | **Partly** |
| Reproducibility | Independent | Deterministic runners, hashes, tests | **Achieved** |
| Production | Validated candidate only | None validated | **No change** |

**Genuine improvement relative to E132**, on the set that contains the surge (S-U, Lead 2):

| Measure | E132 SEAS-LLM | E133 HFM-X |
|---|---|---|
| MAE | 5.72 | **4.87** (−15 %) |
| RMSE | 7.58 | **6.42** |
| Within tolerance | 0.45 | **0.50** |
| Sharp increases caught | 3 | **8** |
| Reliability rules passed | 1 | **5** (N1, N3, N4, N6, N7) |

**Not an improvement** on the post-surge S-E132 set: 0.43 against 0.61.

**The original objectives are not weakened.** The gap to 75 % remains large and is quantified (§1 R1).

**What would close it:**
1. **More episodes of true change.** Pre-2021 SWS history, which the owner's rule excludes, or prospective quarters.
2. **Area-level drivers of escalation.** Household savings or expenditure stress, area climate shocks.
3. **A provincial repeated food-insecurity measurement.**

## 14. Production-readiness decision

- **No E133 component is validated, so nothing replaces the served system.**
- Production, the dashboard, FIRI v2, FIRI3 and the E131/E132 seals are **unchanged**.
- **HFM-X** (and HFM-X-PH2 as a post-hoc prospective hypothesis) are **prospective candidates only**.
- **Adoption conditions:**
  - ≥ 75 % within the primary tolerance;
  - N1–N7 passing at Lead 2 on ≥ 10 unseen quarters, scored with `score_e133.py`;
  - owner approval;
  - a separate integration branch.
- The **release-anchored re-issue** (P-REL) is a design option that would need owner approval.
