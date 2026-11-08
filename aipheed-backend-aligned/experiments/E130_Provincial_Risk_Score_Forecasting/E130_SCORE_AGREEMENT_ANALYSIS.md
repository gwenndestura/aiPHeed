# E130 score-agreement analysis

## 1. The tolerance (fixed before any evaluation, protocol §4)

**Definition.** A prediction agrees with the reference when

|prediction − reference| ≤ 1.645 × SE_reference

That is the reference's own two-sided 90 % sampling interval.

**Why this width:**
- **Measurement.** A prediction inside it cannot be told apart from the reference using the reference's own precision. Anything tighter would ask the model to beat PSA's survey precision.
- **Practical meaning.** On 2023 PFDR values the tolerance is 0.59–1.05 pp. That is less than one percentage point of the population for most provinces, and DA staff would read it as "about the same level".
- **Not generous.** An oracle that knows the true value is inside it only 90 % of the time, and a forecast as precise as the measurement itself (error SD = SE) only 75.5 %. The 75 % bar is therefore demanding, not easy.

Sensitivity at 0.5× and 2× the tolerance is reported for information only. **Pass/fail uses 1×.**

## 2. What 75 % within tolerance requires (analytic)

Let s_f be the forecast error SD against the true value and s_e the reference SE, with independent normal errors. Then

share within = 2Φ(1.645 / √(1 + (s_f/s_e)²)) − 1

**Share within ≥ 0.75 holds if and only if s_f ≤ 1.022 × s_e** (`e130_lib.required_forecast_sd_over_se`). In words, the forecast must be as precise as the survey that measures the outcome.

**On PFDR 2023 precision**, the required error SDs are:

| Province | Required SD (pp) |
|---|---|
| Batangas | 0.48 |
| Cavite | 0.51 |
| Laguna | 0.46 |
| Quezon | 0.36 |
| Rizal | 0.65 |

**What persistence did last time (exploratory).** These values were already seen in E129, so this is not evidence. Over 2021→2023 persistence had:
- MAE 2.10 pp and RMSE 2.80 pp;
- **1 of 5** predictions (Batangas) inside the 2023 tolerance.

## 3. Planning simulation: when can a model pass N2 and N4?

**Synthetic data only. This is not model performance.** Settings: `out/planning_simulation.csv`; protocol §11; 300 simulations per cell.

**Model of the world.**
- True provincial risk is AR(1) with persistence ρ and 74 % of its variance common to all five provinces (the CPI value).
- The reference observes it with noise ratio r = SE / SD(true).
- The *informed* model knows ρ and the noise level, shrinks the last observation, and predicts a share R² of the true change over the information horizon h. It is an upper bound for any model learned from few quarters.
- Pass means: ≥ 75 % within tolerance (N2), **and** MAE and RMSE below persistence, **and** a squared-error advantage over both persistence and climatology at p < 0.10 (N4).

**P(pass N2 and N4), h = 2 (release-anchored Lead 2), ρ = 0.6**

| r \ R² | quarters | 0.00 | 0.25 | 0.50 | 0.75 |
|---|---|---|---|---|---|
| 0.5 | 10 / 20 / 40 | 0 / 0 / 0 | .02 / 0 / 0 | .11 / .06 / .02 | .51 / .58 / .65 |
| 1.0 | 10 / 20 / 40 | .09 / .19 / .29 | .35 / .52 / .76 | .52 / .79 / .96 | .78 / .93 / 1.00 |
| 2.0 | 10 / 20 / 40 | .21 / .23 / .21 | .33 / .42 / .58 | .43 / .58 / .77 | .55 / .67 / .88 |

**P(pass N2 and N4), h = 2, ρ = 0.9**

| r \ R² | quarters | 0.00 | 0.25 | 0.50 | 0.75 |
|---|---|---|---|---|---|
| 0.5 | 10 / 20 / 40 | .06 / .06 / .01 | .12 / .15 / .10 | .28 / .36 / .34 | .51 / .75 / .75 |
| 1.0 | 10 / 20 / 40 | .19 / .38 / .61 | .32 / .49 / .76 | .47 / .64 / .83 | .52 / .76 / .93 |
| 2.0 | 10 / 20 / 40 | .24 / .29 / .42 | .27 / .36 / .49 | .34 / .43 / .58 | .36 / .50 / .67 |

**Findings.** Passing with probability ≥ 0.8 needs all three of the following:
- **at least 20 quarters** (100 province rows), not the N1 minimum of 10. With highly persistent risk (ρ = 0.9) it takes 40 quarters, and the best result at 10 quarters is 0.78;
- a reference whose **sampling SE is about the size of the true variation** (r ≈ 1). If it is much more precise, the tolerance becomes too tight; if much noisier, climatology is hard to beat.
- predictors that explain **at least half of the true two-quarter change** (R² ≥ 0.5).

At h = 3 (the quarter-start issue) the picture is the same; see the CSV.

**Persistence alone** reaches 75 % within tolerance only when noise swamps the signal: with probability 0.22–0.25 at r = 1 and 0.45–0.51 at r = 2.

**Implementation correction (DEVIATIONS V1).** The first simulation run omitted the climatology part of N4. That version let a model with no information pass on noisy references just by smoothing. The reported numbers include climatology, as the frozen N4 requires.

## 4. The sealed survey-year forecasts

| Item | Status |
|---|---|
| Seal file | `sealed/E130_SURVEY_YEAR_SEAL.csv`, sha256 `94a08cd1…` |
| Frozen | Before any search (commit `b58c48e`) |
| Target | The next PSA provincial subsistence round after 2023 (2025 was expected at the freeze; none is published as of 2026-10-31) |

| Province | S1 persistence | S2 two-round mean | S3 EB-shrunk | 90 % PI (S1) |
|---|---|---|---|---|
| Batangas | 1.40 | 1.20 | 1.40 | 0.0–5.87 |
| Cavite | 0.80 | 1.60 | 1.09 | 0.0–5.27 |
| Laguna | 1.30 | 1.85 | 1.34 | 0.0–5.76 |
| Quezon | 0.90 | 3.75 | 1.06 | 0.0–5.34 |
| Rizal | 2.60 | 1.75 | 1.88 | 0.0–7.12 |

**Scoring status.**
- **No provincial subsistence round after 2023 is published.** The owner verified this on 2026-10-31: the latest official provincial subsistence data are 2023. PSA's 2025 full-year release (August 2026) has poverty tables only, and OpenSTAT stops at 2023.
- On 2026-10-31 the owner supplied PSA's `2025 Full Year Official Poverty Statistics_24Aug2026_0.xlsx` (sha256 `ea80fe8d…`). It contains only:
  - Tables 1 and 2: poverty incidence among families and among the population;
  - Tables 5 and 6: magnitudes;
  - Table 15: province groupings.

  It has **no subsistence-incidence table** (`out/owner_workbook_check.json`).
- **The seal therefore stays unscored.** Scoring it against poverty incidence would swap in a different measure after the fact.

**To score it:**
1. When PSA publishes provincial subsistence for a survey year after 2023, supply its "Annual Per Capita Food Threshold and Subsistence Incidence Among Population … by Region and Province" table (Table 4 in PSA's numbering).
2. Run `runner/extract_psa_2025.py <workbook>`, which writes `data/owner_supplied/psa_subsistence_population_2025.csv`.
3. Run `runner/score_e130.py`.

Five provinces in one fold are descriptive only. The intervals are wide (up to 7 pp) because the 2021→2023 change variance is dominated by Quezon's 5.7 pp fall.
