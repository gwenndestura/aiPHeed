# aiPHeed provincial food-insecurity forecasting — consolidated report v3 (E143)

**Date:** 2026-11-04 (Asia/Manila)
**Baseline:** `PROVINCIAL_FORECASTING_FINAL_REPORT_v2.md` (E142)
**Code:** `backend/app/e143/` (audit, model, evaluate, posthoc, issue, serve, gate)
**Protocol:** `docs/e143/PROTOCOL.md`, locked in `data/e143/out/PROTOCOL_LOCK.json` before any candidate was scored
**Unchanged:** E137–E142 code, results and seals.

**Production decision:** CANDIDATE IMPLEMENTED — VALIDATION PENDING. The production pointer stays `null`.

**Concepts kept separate in every output** (`forecast_next_quarter.json → concepts`):

| Concept | What it is here |
|---|---|
| Directly measured provincial HFIAS | FNRI rounds 2013, 2015, 2018/2019 |
| Estimated current relative risk | relative logit vs national |
| Latent risk state | structural level + survey anchor |
| Next-quarter forecast | P for 2027-Q1; candidate, quarterly change assumed |
| Independently validated future prediction | none yet |
| LGU priority | vulnerability-weighted ranking, not a municipal measurement |

---

## 1. E142 audit: reproduced findings

The audit (`python -m app.e143.audit` → `data/e143/out/audit.json`) reads E142's locked out-of-fold files and does not rerun E142.

| Origin | n | Noise floor | E142 EB | PERS | REGPREV | E142 − PERS [95 % CI] | E142 − REGPREV [95 % CI] | Share of pooled diff vs PERS |
|---|---|---|---|---|---|---|---|---|
| O1 2013→2015 | 78 | 0.094 | 0.221 | 0.214 | 0.212 | +0.008 [−0.017, +0.030] | +0.009 [−0.013, +0.038] | +0.005 |
| O2 →2018 | 22 | 0.030 | 0.151 | 0.207 | 0.140 | −0.056 [−0.124, +0.008] | +0.010 [−0.074, +0.091] | −0.010 |
| O3 →2019 | 25 | 0.038 | 0.141 | 0.187 | 0.164 | −0.046 [−0.115, +0.022] | −0.023 [−0.090, +0.052] | −0.009 |
| Pooled | 125 | 0.072 | 0.193 | 0.207 | 0.190 | −0.014 [−0.039, +0.009] | +0.003 [−0.031, +0.038] | |

## 2. Exact causes of the failed E142 gate

Each confirmed cause is quantified. The rejected ones are stated as rejected.

1. **O1 has no identifiable transition. Confirmed, and the largest cause.**
   * O1 is 62 % of the rows. A model trained on 2013 alone cannot estimate persistence, so E142 is structural-only there.
   * At O1, E142 is worse than both persistence and the region's previous level. This adds **+0.005** to the pooled difference vs persistence. Without O1, the pooled difference would be −0.045.
   * Diagnostic (labelled leaky): giving the O1 model the persistence estimated from later rounds does not help (O1 EB 0.2227 vs 0.2215).
2. **The survey anchor was built from in-sample residuals. Confirmed defect.**
   * φ and τ² came from out-of-fold deviations, but the forecast's last-survey deviation used the full-training level. That level had already been fitted on the province's own earlier row.
   * Training-only check: in-sample deviation variance is 0.15–0.17, against 0.24–0.31 out of fold. The level absorbs about 40 % of each province's deviation.
   * Consequence: at O2 and O3, φ = 0 scores better than E142's fitted φ (O2 0.144 vs 0.151; O3 0.138 vs 0.141). **E142's anchor added nothing.** Its advantage over persistence came from the structural level.
3. **The transition form is wrong. Confirmed (section 3).**
4. **Limited independent evaluation clusters. Confirmed.**
   * There are 16 regions. The bootstrap SE of the pooled difference is 0.012, so the minimum detectable difference (80 % power) is **0.034**.
   * The observed −0.014 would need about **5.8 times** the current evidence.
   * Against REGPREV the point estimate is positive, so more data would not rescue E142 there.
5. **Uncertain survey observations. Confirmed, but not the deciding factor.**
   * The noise floor is 0.072 of the pooled 0.193 EB.
   * 40 % of the variance of measured between-round change is survey error. Level reliability is 0.85.
   * Scaling the survey SE by 0.5–1.5 moves the O2/O3 EB by at most 0.004.
6. **Weak quarterly features. Confirmed (section 6).**
7. **Overdependence on structural poverty and geography. Partly confirmed.**
   * The structural level carries the skill, and the history term in E142 contributed nothing (cause 2).
   * Model instability: the region-bootstrap SD of the level is 0.18, against a deviation SD of 0.46 (about 15 % of the deviation variance).
8. **Target or forecast misalignment. Rejected.**
   * Leads 0, 1 and 3 give EB 0.193, 0.193 and 0.205.
   * Shifting the ENNS reference quarter by ±2 quarters changes φ by ≤ 0.005 and the O3 EB by ≤ 0.001.

## 3. Transition-model identification and sensitivity

**Deviation correlations for every measured pair of rounds** (`audit.json → C`). Level = LightGBM, out of fold, measurement-error corrected, region-bootstrap 95 % CI:

| Pair | Gap (quarters) | n | Correlation [95 % CI] |
|---|---|---|---|
| 2013→2015 | 8 | 78 | 0.61 [0.28, 0.78] |
| 2015→2018 | 12 | 22 | 0.61 [0.09, 0.95] |
| 2015→2019 | 16 | 25 | 0.35 [−0.10, 0.66] |
| 2013→2018 | 20 | 22 | 0.67 [0.07, 1.05] |
| 2013→2019 | 24 | 25 | 0.53 [−0.21, 0.84] |

**Markov test.**
* An AR(1) (Markov) transition implies corr(2013, 2018) = corr(2013, 2015) × corr(2015, 2018) = 0.37. The measured value is **0.67**.
* For 2013→2019 the AR(1) prediction is 0.21, against a measured **0.53**.
* Both excesses (+0.30, +0.31) point the same way, and so does the ridge level (+0.32, +0.20).
* The deviations behave like a **permanent province component plus independent round shocks**, not an exponential decay.

**Fitted forms** (weighted SSE over the five pairs):

| Form | Parameters | SSE |
|---|---|---|
| AR(1) | φ 0.959 | 3.43 |
| Constant | c 0.57 | 1.62 |
| Permanent + AR | ρ 0.52, φ 0.80 | 1.38 |

**Live implication.**
* The 2027-Q1 targets are 30–46 quarters after the last survey. The largest observed gap is 24.
* E142 extrapolated φ = 0.935 to 46 quarters, which put a weight of 0.045–0.13 on the last survey.
* Every form the data support puts about **0.52–0.57** there.
* E142's quarterly transition claim is therefore **not supported** beyond the observed gaps. **No time decay of the province component is identified.**

**Sensitivity of the E142 fits (O2/O3):**
* EB rises monotonically from φ = 0 to φ = 1 (O2 0.144→0.213; O3 0.138→0.199). This follows from cause 2.
* Removing horizon growth worsens O2/O3 by 0.005.
* Reference-quarter shifts and survey-error scaling are negligible (section 2).

## 4. Calibration results

**The untouched 2013 ECE of E142 (0.106)** (`posthoc.json → calibration_2013`):

* **Small sample:**
  * If E142 were perfectly calibrated, its 2013 ECE would have a median of 0.072 and a 95th percentile of 0.123 (2000 simulations).
  * 13 % of perfectly calibrated runs exceed 0.106.
  * The "failure" cannot be told apart from sampling noise at n = 78.
* **Direction:**
  * The calibration slope is 1.47 and the intercept +0.31. The model is **under-confident and too low** (mean P 0.60 vs mean q 0.68), not over-confident.
  * The 2013 round has more provinces above national than the 2015–2019 training rounds: a level shift between rounds.
* **SE approximation:** E141 approximates the 2013 SE with design effect 3.17. With deff 2.0, 3.17 and 4.5, the ECE is 0.112, 0.106 and 0.099. The approximation alone moves E142 across the 0.10 threshold.
* **Training-only remedy (pre-registered):**
  * The cross-fitted level with out-of-fold τ² reaches a 2013 ECE of **0.091**, within 0.087–0.094 across deff values.
  * Its pooled rolling ECE is 0.089 (C2) and 0.098 (C4). Both pass S3.
  * No 2013 label was used for calibration.
* **E142's Platt calibrator (LGBM-PLATT) was worse:** 0.118.

## 5. Additional independent outcome data

Searched this round:

| Source | Instrument | Level | Result |
|---|---|---|---|
| FNRI 2021 ENNS | **HFIAS** (eNutrition public-use-file description lists HFIAS for 2018, 2019, 2021) | provincial replicate (81 provinces planned) | National 33.4 % moderate+severe (Philippine Development Plan ch. 3). **No provincial table found.** eNutrition is unreachable from this network and from the fetch service. The FOI portal returns 403. |
| FNRI 2023 NNS (fieldwork 2023–2024, 36,703 households, 117 areas) | **FIES**, not HFIAS (FNRI summit slides; Mindanao Times) | 81 provinces + 33 HUCs sampled; regional estimates published | National 31.4 %; CALABARZON lowest region (no figure printed). **Not an HFIAS round; it may be used for agreement only, never as confirmation.** |
| Semeniano et al., *Phil. J. Dev.* 49(2b), 2025, doi:10.62986/pjd2025.49.2b | HFIAS, ENNS 2018–2019 + 2021 pooled | regional determinants | Pooled 43.19 % moderate+severe. The PDF is behind a captcha, which was not bypassed. No provincial table is visible. |
| Cavite COVID-19 food-insecurity studies (*Phil. J. Sci.* 2025; ResearchGate) | FIES (abstract) | Cavite households | HTTP 403. Not HFIAS, not province-representative per the snippets. Not used. |

* **No new HFIAS provincial round could be acquired.**
* The exact request remains `docs/system/DATA_REQUEST_FNRI_PROVINCIAL_HFIAS.md` (updated with these findings, **not sent**; owner rule).
* The 2021 ENNS provincial replicate is the decisive missing evidence.
  * It would be an **untouched** round 2–8 years after the last measured ones.
  * It is exactly the transition length that is currently unidentified.

**Alternative validation strategies:**

| Strategy | Assessment |
|---|---|
| More annual provincial HFIAS rounds | The only route to validation; listed above |
| Independent food-access outcomes measured between rounds | None exists provincially: PSA FIES/APIS are regional; SWS is regional (not used) |
| Repeated province-specific household surveys | None found |
| Survey-anchored estimation with validated indicators | Implemented as E143; validated survey-to-survey only |
| Nationwide training with CALABARZON evaluation | Already the design. CALABARZON has 13 measured province-rounds |

## 6. Provincial time-varying features

Feature audit (`audit.json → G`), 120–125 measured transitions:

| Feature | Varies within province (share of variance) | Province-specific within region | Δfeature vs Δmeasured (rank ρ [95 % CI]) |
|---|---|---|---|
| food CPI YoY | 0.72 | 0.41 | −0.13 [−0.37, +0.10] |
| rice CPI YoY | 0.84 | 0.27 | −0.29 [−0.53, −0.01] (wrong sign) |
| food threshold relative | 0.25 | 0.61 | +0.02 |
| rain anomaly 6 m | 0.64 | 0.13 (mostly regional) | +0.15 [−0.05, +0.40] |
| cyclones 4 q | 0.61 | 0.27 | +0.01 |
| cyclone climatology | 0.00 (static) | 0.07 | n/a |
| agriculture per capita | 0.004 (static) | 0.39 | −0.18 |
| agriculture YoY | 0.52 | 0.51 | −0.11 [−0.22, −0.01] |
| fisheries YoY | 0.59 | 0.55 | −0.04 |
| poverty / subsistence / gap | 0.09 / 0.26 / 0.18 | 0.35–0.43 | −0.11 / −0.05 / −0.02 |
| density | 0.001 | 0.36 | +0.34 [+0.07, +0.56] (census updates only) |

**Diagnosis.**
* Three of 12 tests are nominally non-zero; about 0.6 is expected by chance.
* Two of the three have the wrong sign, and the third reflects census density updates.
* The market features use the **latest annual** provincial CPI, which lags 6–18 months at the issue date.
* The climate features are largely regional.
* Poverty changes only when PSA releases a new round, so it is constant between most survey pairs.

**Better sources investigated (not acquired this round; no new data was in scope):**

| Group | Source | Status |
|---|---|---|
| Market | PSA monthly provincial CPI and retail prices | Available publicly; would remove the annual lag |
| Climate and agriculture | PSA quarterly palay/corn production | Already held |
| Employment | PSA LFS provincial (annual) | Starts 2021, after every measured round |
| OFW remittances | BSP | National/regional only |
| Income | PSA FIES | Triennial, regional/provincial |
| Nutrition and health | FNRI | Same rounds as the target |

**None of these can be tested against the current folds.**
* Provincial labour and remittance series do not cover 2013–2019.
* A monthly CPI feature would change only the market group, which shows no change signal at any lag in the annual series.

## 7. New experiment: protocol and results

* **Protocol:** `docs/e143/PROTOCOL.md` (hypothesis, target, features and cutoff, origins, baselines, metrics, uncertainty, adoption).
* **Locked before scoring.** The lock covers the protocol, model.py, evaluate.py and the thresholds.
* **Gate thresholds are identical to E142.** S8 (interval coverage) and Holm multiplicity were added; nothing was relaxed.

**Candidates.** All use a **cross-fitted** structural level: a province's level never sees its own region. All anchors use out-of-fold deviations.

| ID | Anchor | Level |
|---|---|---|
| C1 STATE-LGBM-X | E142 AR(1) | LightGBM |
| C2 RE-LGBM-X | permanent province component from **all** earlier rounds (BLUP) | LightGBM |
| C3 RE-RIDGE-X | C2 | ridge (LightGBM's contribution) |
| C4 HRE-LGBM-X | hierarchical region + province components | LightGBM |

**Directive candidates not run separately:**
* **Within-province-change model:** not built. No feature change carries signal (section 6), so it reduces to the anchor.
* **"Only temporally valid features":** reduces to the level without quarterly features. E141's ablation (dropping the quarterly group: −0.004) already covers it.

## 8. Fair comparison (identical 125 rows, 16 region clusters, 2000 bootstraps)

| Model | EB | AUC [95 % CI] | Accuracy | HIGH recall | Precision | F1 | ECE | 90 % coverage | Change ρ [95 % CI] |
|---|---|---|---|---|---|---|---|---|---|
| **C4 HRE-LGBM-X** | **0.190** | **0.984 [0.95, 1.00]** | **0.903** | 0.90 | **0.95** | **0.92** | 0.098 | 0.94 | **0.48 [0.31, 0.64]** |
| C2 RE-LGBM-X | 0.202 | 0.949 [0.88, 1.00] | 0.855 | 0.88 | 0.90 | 0.89 | 0.089 | 0.90 | 0.44 [0.26, 0.62] |
| C1 STATE-LGBM-X | 0.206 | 0.925 | 0.887 | 0.90 | 0.92 | 0.91 | 0.101 | 0.94 | 0.39 [0.24, 0.55] |
| C3 RE-RIDGE-X | 0.232 | 0.899 | 0.823 | 0.78 | 0.94 | 0.85 | 0.130 | 0.83 | 0.32 [0.10, 0.54] |
| E142 STATE-LGBM | 0.193 | 0.956 [0.91, 1.00] | 0.887 | 0.95 | 0.88 | 0.92 | 0.053 | n/a | 0.44 [0.32, 0.59] |
| E141 LGBM | 0.194 | 0.964 | 0.903 | 0.88 | 0.97 | 0.92 | 0.040 | n/a | 0.39 |
| Ridge (RR-F) | 0.203 | 0.930 | 0.806 | 0.75 | 0.94 | 0.83 | 0.072 | n/a | 0.33 |
| PSA-only | 0.206 | 0.908 | 0.790 | 0.80 | 0.86 | 0.83 | 0.066 | n/a | 0.42 |
| Persistence | 0.207 | 0.856 | 0.806 | 0.85 | 0.85 | 0.85 | 0.131 | n/a | — |
| Region's previous | 0.190 | 0.926 | 0.806 | 0.82 | 0.87 | 0.85 | 0.063 | n/a | 0.25 |
| National | 0.250 | 0.451 | 0.645 | 1.00 | 0.65 | 0.78 | 0.069 | n/a | — |

**Confusion matrices** (62 decisive rows; TP/FP/TN/FN):

| Model | TP | FP | TN | FN |
|---|---|---|---|---|
| C4 | 36 | 2 | 20 | 4 |
| C2 | 35 | 4 | 18 | 5 |
| E142 | 38 | 5 | 17 | 2 |
| Persistence | 34 | 6 | 16 | 6 |
| Region's previous | 33 | 5 | 17 | 7 |

**By origin (EB):**

| Origin | C4 | C2 | E142 | PERS | REGPREV |
|---|---|---|---|---|---|
| O1 | 0.237 | 0.237 | 0.221 | 0.214 | 0.212 |
| O2 | **0.098** | 0.131 | 0.151 | 0.207 | 0.140 |
| O3 | **0.124** | 0.157 | 0.141 | 0.187 | 0.164 |

**Gate (Holm-adjusted):**

| Candidate | ΔEB vs PERS [95 %] | Holm upper | ΔEB vs REGPREV [95 %] | Holm upper | Failed checks |
|---|---|---|---|---|---|
| C4 | −0.017 [−0.044, +0.012] | +0.018 (98.75 %) | +0.000 [−0.032, +0.030] | +0.038 | S1, S2 |
| C2 | −0.005 [−0.034, +0.026] | +0.032 | +0.012 | +0.059 | S1, S2 |
| C1 | −0.001 | +0.031 | +0.016 | +0.061 | S1, S2, S3 |
| C3 | +0.025 | +0.060 | +0.042 | +0.077 | S1, S2, S3, S6 |

**Adoption: none.**
* **LightGBM's contribution:** the LightGBM level beats the ridge level in every pairing (C2 − C3 = −0.029, SE 0.011; C4 − C3 = −0.042).
* **Is the improvement repeatable?** It repeats wherever an anchor is identified:
  * C4 beats persistence and REGPREV at both O2 and O3.
  * Descriptive only, not the gate: over O2 + O3 (n = 47), C4 − PERS = −0.084 [−0.149, −0.013]; C4 − REGPREV = −0.041 [−0.096, +0.017].
* **Why it still fails:** at O1, where no anchor can be identified, the cross-fitted level is weaker than E142's (0.237 vs 0.221). It cannot use the province's own region.

**CALABARZON rows in the folds** (P(elevated); measured status):

| Row | C2 | C4 | E142 | PERS | REGPREV |
|---|---|---|---|---|---|
| O1 Batangas 2015 (LOWER) | 0.42 | 0.42 | 0.43 | 0.24 | 0.27 |
| O1 Cavite 2015 (LOWER) | 0.19 | 0.19 | 0.19 | 0.19 | 0.27 |
| O1 Laguna 2015 (LOWER) | 0.14 | 0.14 | 0.27 | 0.22 | 0.27 |
| O1 Quezon 2015 (n.d.) | 0.36 | 0.36 | 0.52 | 0.45 | 0.27 |
| O1 Rizal 2015 (LOWER) | 0.24 | 0.24 | 0.26 | 0.31 | 0.27 |
| O2 Laguna 2018 (LOWER) | 0.10 | 0.08 | 0.17 | 0.07 | 0.16 |
| O3 Quezon 2019 (n.d., q 0.66) | 0.47 | 0.56 | 0.42 | 0.29 | 0.15 |
| O3 Rizal 2019 (n.d., q 0.13) | 0.10 | 0.02 | 0.12 | 0.07 | 0.15 |

## 9. Separate outputs for the five provinces

* **Issue:** 2026-Q4 (issued 2026-10-01). **Target quarter:** 2027-Q1.
* **Model:** e143-re-lgbm-1.0 (C2). The protocol issues C2 when no candidate is adopted.
* **Status:** CANDIDATE, gate S1/S2 failed. **Not a validated forecast.**
* **Class rule:**
  * **HIGH:** P ≥ 0.80, the whole refit range ≥ 0.5, **and every candidate model ≥ 0.5**.
  * **LOW:** symmetric, below 0.20 and 0.5.
  * **UNCERTAIN:** otherwise.

| Province | P(elevated) | Refit range 90 % | Relative logit [90 % PI] | Class | Last direct survey | Quarters since | Structural level | Survey anchor | Weight on own surveys | C1 / C3 / C4 / E142 |
|---|---|---|---|---|---|---|---|---|---|---|
| Batangas | 0.064 | 0.015–0.371 | −0.54 [−1.12, 0.04] | **LOW** | FNRI 2015 | 46 | −0.260 | −0.278 | 0.63 | 0.26 / 0.26 / 0.07 / 0.07 |
| Cavite | 0.124 | 0.041–0.529 | −0.41 [−0.99, 0.17] | **UNCERTAIN** | FNRI 2015 | 46 | −0.260 | −0.147 | 0.64 | 0.26 / 0.36 / 0.07 / 0.07 |
| Laguna | 0.075 | 0.026–0.224 | −0.49 [−1.05, 0.07] | **LOW** | ENNS 2018 | 34 | −0.260 | −0.231 | 0.73 | 0.23 / 0.18 / 0.07 / 0.07 |
| Quezon | 0.165 | 0.082–0.579 | −0.33 [−0.90, 0.23] | **UNCERTAIN** | ENNS 2019 | 30 | −0.255 | −0.078 | 0.72 | 0.28 / 0.54 / 0.07 / 0.26 |
| Rizal | 0.191 | 0.087–0.427 | −0.30 [−0.86, 0.26] | **LOW** | ENNS 2019 | 30 | −0.260 | −0.040 | 0.72 | 0.28 / 0.45 / 0.07 / 0.23 |

**Exact explanation** (logit): base 0.312 + poverty −0.335 + geography −0.18 + market −0.006 + climate −0.05 + history (the anchor column). The sum check is enforced in code.

**Two findings the outputs make visible:**
1. **The cross-fitted LightGBM level does not distinguish the five provinces.** It is identical, −0.26, because it falls in the same shallow-tree leaves. **All provincial differences come from each province's own HFIAS rounds.**
   * Batangas 2013/2015: −0.41/−0.41.
   * Laguna 2013/2015/2018: −0.44/−0.50/−0.75.
   * Cavite 2013/2015: −0.49/−0.48.
   * Quezon 2013/2015/2019: −0.08/−0.20/+0.05.
   * Rizal 2013/2015/2019: −0.28/−0.50/−0.15.
2. **In the final fit, the region's permanent variance equals the whole permanent variance** (σ_G² = σ_A² = 0.092). A province-specific permanent difference within CALABARZON is not detectable beyond survey noise. C4 therefore gives all five about 0.07.
   * The provincial separation in C2 is measured, but its persistence is not separately established.

**Correction to the v2 message.**
* The v2 summary sent to the owner showed "—" as the last survey round for Cavite and Rizal. That was a transcription error in the message.
* The E142 artifact correctly anchored Cavite on FNRI 2015 and Rizal on ENNS 2019.

**Withdrawn seals.**
* The first E143 issue run built the refit range by resampling CALABARZON itself out of some refits. That dropped the provinces' own surveys and widened the ranges.
* It was corrected to resample only the other regions. CALABARZON's measurements are the anchoring data, not a sampling unit.
* The two seals written by that run were withdrawn, together with their two register lines, before any commit. They were re-issued with identical point predictions.

## 10. Uncertainty decomposition (relative-logit variance, C2)

| Province | Total V | Transitory round shock | Permanent-component uncertainty | of which survey error of anchoring rounds | of which finite rounds |
|---|---|---|---|---|---|
| Batangas | 0.125 | 0.091 | 0.034 | 0.003 | 0.031 |
| Cavite | 0.125 | 0.091 | 0.033 | 0.003 | 0.031 |
| Laguna | 0.116 | 0.091 | 0.025 | 0.002 | 0.023 |
| Quezon | 0.117 | 0.091 | 0.026 | 0.003 | 0.023 |
| Rizal | 0.117 | 0.091 | 0.026 | 0.003 | 0.023 |

**Other uncertainty sources:**
* **Structural-level error:** inside τ², which is estimated out of fold. Its region-bootstrap SD is about 0.18.
* **Parameter uncertainty:** the refit range, from 30 refits that resample the other regions.
* **Model selection:**
  * The C1–C4/E142 spread is 0.07–0.54 for Quezon and 0.07–0.45 for Rizal.
  * The largest single source is the level: cross-fitted LightGBM vs ridge.
* **Transition form:** AR(1) puts 0.04–0.12 on the surveys, the permanent component 0.63–0.73. This is the main reason the C1 values are higher.
* **Horizon:** no decay is identified, so C2 is not horizon-dependent. Under AR(1), the horizon would dominate.

**Can better evidence reduce the uncertainty?** Yes, but only through new measurements.
* **The transitory shock (0.091) is irreducible** for any forecast made before the next survey, because no quarterly provincial measure exists.
* **The permanent-component uncertainty falls with each additional round.** For example, a 2021 round would cut it for Batangas and Cavite from 0.034 to about 0.023.

**Interval calibration on the folds.** The 90 % PI coverage of the measured relative logit is:

| Candidate | Coverage | O3 coverage |
|---|---|---|
| C2 | 0.90 | 0.80 |
| C4 | 0.94 | 0.88 |
| C1 | 0.94 | |
| C3 | 0.83 | 0.68 |

## 11. Five contributor groups

| Group | Provincial features | Coverage | Structural risk | Within-province change | Next-round incremental value | Can a better source fix it? |
|---|---|---|---|---|---|---|
| Market & food prices | food/rice CPI YoY, food threshold | 96–99 % | ablation −0.001 (no gain); live TreeSHAP −0.006 | no robust signal (rice CPI wrong sign) | none | Monthly provincial CPI would remove the annual lag; it cannot be tested on the current folds beyond the annual signal, which is absent |
| Climate & agriculture | rain anomaly, cyclones, agri/fish YoY | 97–100 % | ablation −0.003 (no gain); TreeSHAP −0.05 | rain +0.15 [−0.05, +0.40]; others ≈ 0 | none | Already province-level NASA/IBTrACS/PSA; no better source identified |
| Employment & OFW remittances | **none** | 0 % | not testable | not testable | not testable | Provincial LFS begins 2021, after all measured rounds; remittances only regional |
| News & NLP (FSSI v2) | CALABARZON only | 5 provinces, 2008–2026 | not testable | not testable | not testable | Requires national geocoded news (section 12) |
| Poverty & vulnerability | poverty, subsistence, gap, density | 97–99 % | **largest**: ablation +0.020 (dropping hurts); TreeSHAP −0.335 | none (only changes at PSA releases) | carries the level | 2018/2021/2023 provincial poverty releases are held; their timing relative to the rounds leaves no testable change |

* Geography (island) adds +0.013 in the ablation and −0.18 in TreeSHAP.
* **Measured HFIAS history** is the main time-varying provincial information. It is not one of the five groups and is shown separately as "history".
* No equal weighting is imposed.

## 12. FSSI coverage and validation

(`posthoc.json → fssi`; the E142 FSSI v2 evidence is preserved unchanged.)

**Outlets.**
* **Rappler 59,497 (94.9 %)**, VERA Files 1,843, NewsBytes 1,010, PCIJ 348.
* Only **3** events are reported by more than one source, so source bias cannot be reweighted.
* No other publisher archive covering CALABARZON 2008–2026 at province level is held.
* GDELT files that appear untracked in this checkout belong to another session's E114 work. They are national, so they were not used.

**Geographic resolution.**
* Of 62,698 articles: 283 at province level, 1,875 LGU, 250 region, 12,841 national, and 47,449 body mentions only.

**Overlap.**
* FSSI v2 vs cyclones and volume: R² = 0.034, so 97 % of its variance is unique.
* That information is **unvalidated**: there is no quarterly provincial outcome to test it against.

**Agreement with the measured rounds.**
* Across 13 CALABARZON province-rounds, the mean FSSI v2 over the 4 quarters before issue has rank ρ = −0.08 with the measured relative logit. That is no agreement, and n is far too small for inference.

**Conclusions.**
* **Sentiment accuracy:** unverified. No independent human-labelled sample may be used (owner rule).
* **Forecasting contribution:** not demonstrated. **The volume-bias improvement is not a forecasting improvement.**
* XLM-RoBERTa and BERTopic are preserved. There was no technical reason to change them.

## 13. 142 LGU priorities

* **File:** `data/e143/out/issue/lgus_next_quarter.csv` (142 rows, each labelled).
* **Formula:** province P (C2) × vulnerability (½ SAE 2021 poverty percentile + ½ POPCEN 2024 density percentile, region-wide). The refit range is carried through as priority low/high.
* Top 2: **Taytay (Rizal) 0.144 [0.065, 0.322]** and **Antipolo (Rizal) 0.122**.
* It is a **vulnerability-weighted priority ranking**, not a municipal food-insecurity measurement. The status is "candidate ranking pending provincial forecast validation".

## 14. API and dashboard status

* **Public outlook** (`/api/v1/final/food-insecurity/outlook`) returns `validation_pending` with `forecast: null`. The production pointer is null.
* **CH1 explanations** (`/api/v1/explainability`): every note says it describes the **CH1 price-pressure risk index**, not provincial food insecurity. Test `test_ch1_explanation_is_labelled_as_price_pressure` passes.
* **E143 candidates:**
  * They are served only at `/api/v1/admin/candidates/e143-re-lgbm-1.0/*` and `/api/v1/admin/candidates/e143-hre-lgbm-1.0/*` (outlook, evaluation, model card, LGUs).
  * Without admin they return 401/403. Their outputs carry `CANDIDATE_NOT_APPROVED`.
* **Registry:** e143-re-lgbm-1.0 and e143-hre-lgbm-1.0 are `rejected` (S1, S2), and so are E140–E142.
* **Prospective register:** both E143 seals are registered (hash chain verified; 7 seals E138–E143).

| Model id | Seal sha256 |
|---|---|
| e143-re-lgbm-1.0 | `4c61cc0e…3648` |
| e143-hre-lgbm-1.0 | `58a9daa7…bd1` |

* **No frontend change was made** (approved design rule).

## 15. Tests

| Suite | Result |
|---|---|
| Full backend `tests/unit` | **879 passed**, 0 failed (296 s) |
| Frontend `tsc --noEmit` | clean |
| Frontend `vitest` | **88 passed** (18 files) |
| New `tests/unit/test_e143.py` | **7 passed** |
| Protocol locks E137–E143 | verify |

**test_e143.py covers:**
* lock;
* the anchor is not identified without a different-round pair;
* BLUP uses earlier rounds only and shrinks with survey error;
* the cross-fitted level predicts each region from a model without it;
* the issue decomposes exactly, follows the class rule, and has 142 LGUs;
* the gate is recorded and nothing is promoted;
* the admin-only route.


## 16. Thesis objective acceptance matrix

| Objective | Status | Evidence |
|---|---|---|
| 1 NLP (XLM-R + BERTopic, bias-corrected FSSI) | **PARTIALLY ACHIEVED** | Pipeline and FSSI v2 (volume ρ 0.05). One outlet (95 %); sentiment accuracy unverified; provincial forecasting value not demonstrated |
| 2 LightGBM forecasting, walk-forward, furthest reliable horizon | Evaluation **ACHIEVED**; **no horizon validated** | E143 LightGBM level beats ridge; C4 best AUC/EB/change ρ; Holm-adjusted gate failed (S1, S2) |
| 3 LGU rankings from province forecasts | **PARTIALLY ACHIEVED** | 142 LGUs complete; province forecast unvalidated |
| 4 Baselines (persistence, PSA-only, NLP-only, logistic) | **PARTIALLY ACHIEVED** | All on identical folds except NLP-only (not constructible provincially) |

## 17. Final production decision

**CANDIDATE IMPLEMENTED — VALIDATION PENDING. No promotion.**
* No E143 candidate passed its pre-registered gate.
* A pass would itself have been development evidence on re-used folds.

**What E143 changed:**
* It removed a real defect in E142 (in-sample anchor).
* It replaced an unsupported transition (AR(1) to 46 quarters) with the form the measured rounds support.
* It fixed the 2013 calibration with a training-only method.
* It produced the best measured round-to-round skill so far (C4, O2/O3).

**What has not been established:**
* That any model beats persistence and the region's previous level across all origins with confidence.
* That provincial risk changes from quarter to quarter in a way any indicator can predict.

## 18. External evidence still required

1. **FNRI 2021 ENNS provincial HFIAS** (the third replicate), with SEs, sample sizes and fieldwork dates by province.
   * It is the only route to an untouched test of the 2–8-year transitions that decide E143.
   * Scoring: `python -m app.registry.prospective_provincial score <file>`.
   * The confirmation rule is pre-stated: n ≥ 20; EB below persistence and below the region's previous level with CI < 0; AUC ≥ 0.75.
2. **FNRI 2013 NNS design-based SEs.** They decide whether the 2013 calibration result moves across the threshold (section 4).
3. **ENNS 2018/2019/2021 fieldwork months by province** (currently Q3 is assumed; sensitivity is small).
4. **Any HFIAS provincial round after 2021.** The 2023 NNS uses FIES, so HFIAS continuity after 2021 must be confirmed with FNRI. **If HFIAS was discontinued, the thesis target ends with the 2021 round,** and later validation must be framed as FIES agreement.
5. **A quarterly or annual provincial food-insecurity measure** (PSA/FNRI). None exists. It is required for any validated quarter-to-quarter claim.
6. **Provincial labour/remittance series and multi-outlet geocoded news covering 2013–2021,** before employment and news can be tested.
