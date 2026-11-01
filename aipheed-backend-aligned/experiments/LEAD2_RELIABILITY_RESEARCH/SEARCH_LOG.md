# Lead-2 search log

This is a chronological record of every approach considered in Phase 2 (2026-10-29): why it was pursued or rejected, and
what was learned. Phase 1 (X1–X4) is in `RESULTS.md`.

**Pre-registration.** Each confirmatory step was frozen before it was run:

| Plan | Covers | SHA-256 | Frozen (UTC) |
|---|---|---|---|
| `EXPERIMENT_PLAN_PHASE2.md` | Y2–Y5 | `af18a7ab…` | 11:52:28 |
| `EXPERIMENT_PLAN_PHASE2_ADDENDUM_A.md` | Y8 | `cdc4c6ed…` | 12:19:56 |
| `EXPERIMENT_PLAN_PHASE2_ADDENDUM_B.md` | Y10 | `315f4342…` | 12:22:22 |
| `EXPERIMENT_PLAN_PHASE2_ADDENDUM_C.md` | Y11 | `5b8f3be3…` | 12:23:24 |

## Already tested before Phase 2 (not repeated)

`LEAD2_OPTIMIZATION/` had tried about 20 configurations, all scored on the 2021–2026 rows:

- **price models:** P0–P8, Platt calibration, distributional regressors, the A1 structural prior;
- **hunger terms:** H1, H2, H3a, H3b, H4;
- **one-model variants:** U-ONE.

Phase 1 had tried RW, mean reversion and food-CPI-augmented mean reversion on 2005–2020. Phase 2 does not repeat threshold or tuning variants of any of these.

## Log

| # | Approach | Why pursued | Data verified | Outcome | Learned |
|---|---|---|---|---|---|
| 1 | **Y0 scoring audit** | A bug in scoring could hide a pass or a fail. | Official rows; stored `evaluation.json` | **No bug.** Two independent implementations agree with the stored criteria. Confusion order, orientation, NaN, ties, alignment, label definition and issue-time inputs are all correct. Two flags were benign: a Brier difference of 5e-8 (CSV rounding), and my own timing check, which compared against a partially observed quarter's later round. | Lead 2 fails R3, R5 and R6 genuinely. Effective n ≈ 33 of 65 rows (design effect 1.97). |
| 2 | Component error breakdown | To find which term to fix. | Official rows | Of 11 false negatives, 7 come from the hunger term and 4 from the price term. | This repeats the earlier report. |
| 3 | **Y7 oracle headroom** | To test whether a perfect hunger forecast would be enough. | Official rows | **No.** Observed hunger × each of the 10 existing price terms fails at least 2 rules (best: P6, fails R5 and R6). Served hunger × observed price fails R6 and R7. | **The price condition is a second binding limit.** The earlier view that only hunger binds is incomplete. |
| 4 | **Y2 latent-state Kalman AR(1)**, with known SWS sampling error | It handles noisy readings and widens predictive uncertainty properly. | Four SWS areas, 1998–2020; MoE per round | **Gate failed.** Lead 2, all areas: Brier 0.165 vs RW 0.151 (p = 0.91). BL balanced accuracy 0.44 vs 0.61. | Mean reversion pulls forecasts toward the area mean. Onsets are sudden jumps of 5–15 points, which the filter treats as noise. |
| 5 | **Y3a H3b on independent years** | It was the only term that nearly passed Lead 2 (R5 only), but it had never been tested outside 2021+. | BL 1998+, Region IV-A CPI 1994+ | **Gate failed badly.** BL Lead 2, 2005–2020: Brier 0.212 vs RW 0.184. Balanced accuracy 0.41 vs 0.61. | **The 2021+ near-pass of P4H3b is not supported by independent evidence.** |
| 6 | **Y3b pooled regularised logistic on crossing**, 8 issue-time indicators: rice and food CPI, ONI, typhoons, palay, unemployment | Earlier-published drivers might anticipate crossings; pooling four areas gives 4× the data. | All covariates with release lags (`DATA_AUDIT.md` Phase 2) | **Gate failed.** Brier 0.192 vs 0.151 (p = 1.0). | The added features add variance and no signal. |
| 7 | **Y3c ridge on the continuous change** in hunger | The continuous target uses level information; crossing is derived from it. | Same | **Gate failed.** Brier 0.188 vs 0.151. | A continuous target does not help either. |
| 8 | **Y3 diagnosis: leading vs concurrent correlation** | To check whether indicators predict the target or only co-move with it in hindsight. | 316 pairs, 79 quarters, 1998–2020 | Rice inflation leads the change at r = −0.09 (CI −0.26 to 0.11). Onsets had rice YoY 0.0% vs 2.3% where no onset followed. Unemployment is concurrent only (r = +0.32 concurrent, −0.08 leading). Palay leads at +0.15, with an implausible sign. | **No issue-time indicator leads hunger onsets.** The 2008 and 2014 rice-shock story does not hold up as a forecast. |
| 9 | **Y6 an earlier hunger signal (desk search)** | X2/X4 showed the newest reading is 3 quarters old at a Lead-2 issue; a fresher survey would shorten that. | Web: OCTA Tugon ng Masa, WFP mVAM, DSWD | **None usable.** OCTA's Q3 2024 round (fieldwork 28 Aug–2 Sep) was published 22 Oct 2024, after the 1 Oct issue. OCTA BL Q4 2023 was 11%, below the line, while SWS was 14.3%, so it would not have caught the onset. WFP mVAM ran 3 rounds (Oct 2022–Mar 2023) and stopped. No monthly DSWD hunger series was found. | The fresher-signal path stays the top data hypothesis, but no current source satisfies it. |
| 10 | **Y5 confirmation** (descriptive, because no candidate passed the gate) | To show what the candidates do on the official rows. | Official 65 / 70 rows | No candidate passes Lead 2. H3B × P4 reproduces the earlier near-pass (0.800 / bal 0.751 / R 0.65, fails R5). | It is a test-period artefact (rows 5 and 13). |
| 11 | **Y4 stacking** of logit π_H and logit π_P, refitted per origin (exploratory, 2021+ only) | The product rule assumes independence and calibration. | Official rows; labels known at issue | **Worse.** All 4 variants fail R2–R7 at Lead 2. Same-lead P0 gives recall 0.00 and Brier 0.231 vs 0.194. | Only 10–40 labelled rows exist before each origin, mostly from the pre-onset regime, so the fit learns to say LOW. A fitted combination needs far more labelled quarters. |
| 12 | **Y8 the price condition on independent years** (Region IV-A CPI 1994+) | Y7 showed price is binding, and earlier price work had never been validated outside 2021+. | Region IV-A food and all-items CPI | **Gate failed.** On 2002–2020, persistence reaches balanced accuracy 0.61–0.66 (AUC 0.68). Ridge (AR) and logistic (LOGX) are worse (Brier +0.06 / +0.07). | The price condition 5–7 months ahead is only weakly predictable. |
| 13 | **Y9 joint analysis on independent years** | To see which half limits the joint target outside the test period. | X2 + Y8 rows, 2005–2020 | In 13-quarter windows, R2, R3 and R6 pass together in **0%** for RW × PERS-PROB, **10%** with perfect hunger, and **90%** with perfect price. | **The price side is the larger lever** when hunger stays HIGH, as in 2005–2020 and 2024–2026. |
| 14 | **Y10 world commodity prices** (World Bank Pink Sheet) as leading price indicators | The Philippines imports rice; fuel and fertiliser costs pass through to food. Not used in any earlier aiPHeed model. | Pink Sheet monthly, vintage 2025-01-03, sha `bd89b83e…`; published about the 2nd–3rd business day of the next month | **Gate failed.** LOGW Brier 0.289 and LOGW2 0.292, vs PERS-PROB 0.235. | Full-period correlations with the coming change in food inflation are sizeable (palm 0.46, wheat 0.42, crude 0.39). The 8–14 feature logistic overfits. |
| 15 | **Y11 parsimonious continuous world-price model** (top 3 chosen in-fold) | It targets the change signal found in #14 with few parameters. | Same | **Gate failed.** WAR Brier 0.275 vs PERS-PROB 0.235. WAR minus its no-world ablation: +0.024 (p = 0.99). | **World prices correlate in hindsight but do not forecast in real time.** The correlations come mainly from the 2007–08 and 2010–11 commodity spikes, which an expanding window cannot learn before they happen. |
| 16 | **Y1 label sensitivity** | The task asked for it, and several outcomes sit at 11.3. | SWS MoE per round | P0H4 L2 R2 passes in only 38% of plausible label draws. H3B × P4's classification passes need the 2023-Q2 label (exactly 11.3) to be LOW; they hold in 41% of draws. FIRI's R7 holds in 44% of draws. | **13 Lead-2 quarters cannot distinguish skill from label noise.** |

## Considered and not pursued

| Approach | Reason |
|---|---|
| Monthly predictors as extra target rows | The outcome is quarterly. Monthly rows would duplicate labels, which the task forbids. Monthly predictors were aggregated to the issue month instead (Y3, Y8, Y10, Y11). |
| Moving the issue date, changing the 0.50 threshold or the test period | Forbidden. They would change the evaluation, not the forecast. |
| Re-tuning P0–P8 or H1–H4 | Already done in `LEAD2_OPTIMIZATION`; it would only be threshold or hyperparameter variation. |
| Provincial pre-2021 CPI | Provincial series start in 2021 in the project data. The regional series was used instead (Y8–Y11). |
| GDELT news as a leading indicator | Starts in 2017, so it cannot be validated on independent years. Earlier P0H4 news ablations found its gain only in-sample (`FINAL_SYSTEM_SELECTION`). |
| A Bayesian hierarchical model across areas | Y2 is its state-space core, with partial pooling of dynamics across four areas. X2 showed the other areas transfer to BL as well as BL's own history does. A fuller hierarchy cannot add information the four series lack. |
| Alternative target: latent (denoised) hunger | Reported only as a diagnostic (X1, Y1). It would change the meaning of T43c, and is labelled as an alternative and not proposed. |

## Phase 3 (Y12, 2026-10-29)

| # | Approach | Why pursued | Data verified | Outcome | Learned |
|---|---|---|---|---|---|
| 17 | **Y12 domestic rice supply** (PSA OpenSTAT: national stocks by sector 1980+, provincial farmgate palay 1990+, provincial CPI 2012=100 1995-2021) | Phase 2 identified it as the strongest remaining hypothesis | See `y12_domestic_rice_supply/DATA_AUDIT.md`. Pre-2021 release dates could not be verified (psa.gov.ph 403), so lag bounds plus a sensitivity run were used. | **No candidate credible.** On 380 provincial rows, 2002-2020: M1 Brier 0.239, M2 0.238, M3 0.225, vs persistence 0.230. Supply vs its ablation: -0.0003 (p 0.43). Step 4 not run. | Farmgate palay moves with retail food inflation (r +0.46 same months, -0.01 leading). Stocks lead only weakly (r -0.19). |

## Phase 4 (2026-10-29)

| # | Approach | Outcome |
|---|---|---|
| 18 | **y13 joint-forecast diagnostics.** Started, then stopped at your direction change. | No outputs. One audit finding: target 2025-Q1 is excluded at every lead because its only SWS round is commissioned (Stratbase); this is a design rule, not a defect. |
| 19 | **Y14 food-insecurity forecast**, target = observed BL hunger > 11.3 at Lead 2: FIRI-analog, drivers-only, logistic, continuous, Kalman reference | **No candidate passed the gate** on independent 2009-2020 years. FIRI-analog Brier 0.244 vs hunger persistence 0.181. No driver leads hunger. The served FIRI v2's 2021+ climate-domain AUC of 0.95 comes from a scoring warm-up (3 of 5 LOW targets had climate = 0.0 because indicators had no history), the 2023-24 El Nino coinciding with the onset, and in-sample weights. The same domain has AUC 0.49 on 1999-2020. A sealed prospective workflow was built. |

## Phase 5 (Y15, 2026-10-29)

| # | Approach | Outcome |
|---|---|---|
| 20 | **A. FIRI climate-domain warm-up audit** (read-only on stored history) | **Confirmed artefact.** At the first three LOW targets, unavailable climate indicators were averaged as 0.000. Without that zero, 2 of 5 LOW quarters become false alarms: acc 0.941 -> 0.824, specificity 1.00 -> 0.60. Under domain abstention, FIRI cannot issue them. |
| 21 | **B. Remittances**: IMF BOP personal transfers, 1999-2026, national, via the public API (BSP Excel not obtainable without circumventing a block) | Validated against BSP (r 0.997). Weak leading signal (r +0.17 [0.03, 0.31]). **No forecast gain** (Brier +0.007 vs H1). |
| 22 | **C. Five predeclared candidates** (FIRIR, SCREEN, KAL, CONT, REMIT) on 2001-2020, 77 quarters | **None passed the gate.** Best: KAL (survey-uncertainty state space), Brier 0.192 vs H1 0.216, Holm p 0.455, better calibration and AUC. Continuous: the climatological mean beats persistence (MAE 4.23 vs 4.87). 17-row seven-rule table: no candidate passes. R1 is structurally unreachable. Next: pre-register KAL vs H1 for prospective seals from 2027-01-01. |

## Phase 6 (Y16, 2026-10-29)

| # | Approach | Outcome |
|---|---|---|
| 23 | **Prospective preregistration: Kalman (challenger) vs hunger persistence (baseline)** for TFI-2 | Plan frozen 2026-10-29T14:17:41Z (sha 208b5754...) before any code was written. Audit: the operational and historical specifications are identical (parity < 1e-4). Isolated issuance, sealing and evaluation code in y16 (Y14 issue_forecast.py untouched); new SWS rounds come in through an append-only overlay (backend/data untouched). 19/19 tests pass. No forecast issued; first valid issue 2027-01-01 targets **2027-Q2** (corrects the Y14 erratum of 2027-Q3). Primary analysis at 20 resolved quarters (about 2032). |
