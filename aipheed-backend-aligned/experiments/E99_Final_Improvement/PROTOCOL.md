# E99 (final improvement): outcome reliability, simple baselines, robustness, provincial data, labels and evaluation packages (pre-registered)

**Branch.** `e99-final-improvement`, from `e98-acceptance-gate` (a42de8c). Frozen before any scoring.

**Relation to the other E99.** `e99-chapter3-evaluation` (6da1054, pushed, untouched) ran the Chapter III pipeline as
written: Eq. 3 label, Algorithms 3–4, six comparators. It failed its own criteria (k* = 0). This experiment does not
repeat that search. Its findings are cited as prior evidence.

**Production lock.** `final-system-v2` stays at 053a95d (origin). There is no merge, no deployment and no change to a
production artifact. The sealed forecasts (`FINAL_Thesis_System/out/firi2_sealed_prospective.csv`) are read only.

**Evidence status.** Every SWS quarter to 2026-Q3 has been examined. All historical results are **development
evidence**.

## Questions

**Q1. How reliable is the regional "measured outcome" itself?** The OCTA Tugon ng Masa Balance Luzon hunger series
(8 quarters; `inputs/octa_validation_E73.json`, recovered from commit 0029bca, E73) is a second, independent hunger
survey.
- Agreement between SWS (> 11.3%, Chapter I) and OCTA (> 11.0%, the E73 rule from its first 4 rounds; sensitivity
  > 11.3%) on the common quarters with a `definition_A` SWS round.
- Report: class agreement, Cohen's κ, and the Spearman correlation of levels.
- On the same quarters: served FIRI v2 (Lead 2, regional mean ≥ 0.5) and H1 against each survey.
- Claim rule: if the two surveys disagree on the class in ≥ 1/3 of the common quarters, accuracy against either survey
  is described as **survey-specific**.

**Q2. Do simpler forecasts do as well?** Smoothed persistence of the posted SWS rounds, on the E98 Question D quarters
(same targets, issue dates and outcome):
- MA2 / MA4: mean of the last 2 / 4 posted quarterly readings before the issue date.
- Class: HIGH if the mean is > 11.3.
- Probability: Φ((MA − 11.3) / σ), where σ is the RMSE of the rule's own past Lead-L errors known at the issue date
  (≥ 4 pairs, else 4.0), as for H1.
- Compared at Lead 1 and Lead 2 with H1, FIRI v2 and always-HIGH: accuracy, balanced accuracy, AUC, Brier.
- Paired differences vs FIRI and vs H1: quarter bootstrap (5,000 draws, seed 99), sign test.

**Q3. Robustness of FIRI v2's Lead-2 accuracy** (report only; the threshold stays 0.5).
- Distance of each quarter's regional FIRI from 0.5, and the number of quarters within ±0.05.
- Accuracy at thresholds 0.45, 0.475, 0.525 and 0.55.
- Accuracy split into **regime quarters** (outcome class equal to the class of the latest posted reading at the issue
  date) and **transition quarters** (different), for FIRI, H1, MA2 and MA4.

**Q4. Can existing local data give a provincial measured outcome?** The sources are already on disk: PSA FIES 2021/2023
public-use files (`Downloads/`) and PSA subsistence incidence (`data/inputs/psa_subsistence_population_2021_2023.csv`).
- Check whether the PUF holds a food-insecurity-experience module.
- Otherwise compute the RFACT-weighted household food expenditure share per province, 2021 and 2023.
- Descriptive Spearman (n = 5) between the 2023 provincial mean FIRI (2023 targets) and each 2023 indicator.
- Circularity is disclosed: V1 uses PSA SAE poverty, which is modelled from FIES.

**Q5. Lucena substitute.**
- Verify the served 16.8% against `Downloads/2018 - 2021 SAE_with PSGC_noHUC.xlsx`.
- Sensitivity, report only: replace it with Lucena's own latest municipal estimate (2018 SAE) and report the change in
  Lucena's and Quezon's within-province ranks, and in Quezon's V1.
- The served input is not changed: it also feeds FIRI's V1, which is sealed and evaluated.

**Q6. Display labels (G6).**
- Smallest change on this branch: the LightGBM output is printed as a 0–1 "food-price-pressure score (not a calibrated
  probability)" instead of a percentage or a "% chance".
- Then an automated audit of every thesis-mode API payload (config, provinces, municipalities, ranking for the target
  and two backtest quarters) for "% chance", "probability of", "chance of", or a percentage attached to the price score,
  FIRI or an LGU index. Target: 0 hits.

**Q7. Evaluation packages.**
- ISO/IEC 25010 scorer v2 with eligibility rules: agency = DA Region IV-A, consent recorded, unique respondent id,
  items 1–15 in 1..5. Exclusions are reported, never imputed.
- H4 instrument and scorer:
  - Each evaluator ranks, for the province they know best, 6 LGUs chosen by a fixed rule: the served
    within-province vulnerability ranks at quantiles 0, 0.2, 0.4, 0.6, 0.8 and 1. They are listed alphabetically and
    blind to aiPHeed's order.
  - Agreement = Spearman ρ between the evaluator's rank and aiPHeed's.
  - **H4 null rejected** if the median ρ across eligible evaluators is ≥ 0.40 **and** a one-sided Wilcoxon
    signed-rank test of ρ > 0 gives p < 0.05, with at least 10 evaluators.
- Both scorers return NO_RESPONSES on empty input.

**Q8. Sealed forecasts.** A scorer that verifies the seal's SHA-256 (LF- or CRLF-normalised content) and refuses to
score a target whose SWS round is not in `sws_rounds.csv`.
- Rule: regional mean FIRI ≥ 0.5 vs `definition_A` mean H > 11.3%.
- Status on 2026-10-22: expected PENDING.

**Q9. Reproduction and version.**
- Re-run the E98 Question D script; its metrics must be identical to the committed run.
- Record the SHA-256 of the served artifacts and serving code, and list every file changed against a42de8c.

## Decision rules

1. No model is promoted unless it beats FIRI v2 at Lead 2 in accuracy **and** beats H1 in Brier with the
   quarter-bootstrap CI entirely below 0 (the E98 rule D, unchanged).
2. Q3–Q5 are report-only.
3. The Q6 wording change is the only serving change. It stays on this branch.

## Release gate (unchanged from E98 §6)

G1–G12 all must pass. A criterion that cannot be verified counts as failed. A passing build or test suite is not
evidence of forecasting validity.
