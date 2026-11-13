# aiPHeed FINAL — deep problem reassessment and selected solution (2026-11-13)

**Decision**
- Do not change the target.
- The national-relative target I expected to fix the problem was tested under a locked protocol, and it is worse:
  - every model reaches only about 0.19 Brier on it, against 0.123 for FINAL on the current target;
  - 31 % of its labels are within survey error of the cut-off.
- The selected solution has three parts. All of them use genuine data only.
  1. **FINAL-LG model:** FINAL's LightGBM, also trained on genuine long-gap survey pairs. It is the best level forecaster: pooled prevalence error 0.38 pp lower than FINAL's, 95 % CI [−0.71, −0.01]; 2021 bias halved from −6.0 to −3.2 pp; 2018 and 2019 identical.
  2. **Measurement-aware, three-tier reporting:** HIGH / BORDERLINE / LOW, using each survey's own standard error.
  3. **Power-aware acceptance rule:** count-based targets (recall, precision, F1, BA, accuracy) are binding only in rounds with at least 8 HIGH and at least 8 LOW provinces, and pooled. This rule must be fixed now, before the next round.
- FINAL stays the official model until FINAL and FINAL-LG are compared on sealed forecasts for an unseen round.
- Nothing was put into the dashboard. Nothing was committed.

Folder: `research_notes/aiPHeed_final_reformulation_20261113/`.

| Item | File |
|---|---|
| Protocol | `PROTOCOL_REL.md`, sha256 `4b740e48…`. Written before any relative-target model was fitted |
| Scripts | `scripts/rel_run.py`, `rel_eval.py`, `supp_eval.py`, `lg_vs_final_boot.py` |
| Evidence | `evidence/REL_per_round_L1.csv`, `REL_verdict.json`, `REL_province_rows_L1.csv`, `REL_national_reference.json`, `SUPP_absolute_continuous_soft.csv`, `SUPP_borderline_2021.json`, `LG_vs_FINAL_bootstrap.json` |
| Predictions | `parts/` (21 LightGBM fits, plus the statistical models) |
| Earlier study used here | LG (long-gap) evidence is in `../aiPHeed_final_model_optimization_20261113/` |

---

## 1. Problem reassessment

| Question | Finding (evidence) |
|---|---|
| Exact label | HIGH = province HFIAS moderate+severe ≥ 50 % (`GT_rounds.csv`; manuscript: "at least 50 percent of households… moderate or severe food insecurity") |
| Is this "relative to the national level"? | **No.** It is an absolute cut. Chapter I, as restated in the manuscript, defines no target. I found no "relative to the national level" wording in the thesis files. A relative target would be a reformulation, not a correction |
| Is 50 % an official cut-off? | **No.** It is a project choice. FNRI's published scale applies to *any-level* insecurity (High = 60–79.9 %). FNRI's factsheets compare each province with the national value (`*_sig_vs_ph`) |
| Are the rounds comparable? | **Partly.** Same HFIAS instrument (9 items, 30-day recall) in all rounds. But 2018, 2019 and 2021 each cover a *different* set of provinces. 2021 was fielded during COVID, and its provincial SEs are unpublished (assumed 3.0 pp) |
| What drives the label? | National mod+sev moves: 53.8 (2015) → 41.6 (2018) → 46.9 (2019) → 41.0 (2021). The absolute label is the national level plus the province's relative position, so the HIGH share swings 36 % / 52 % / 16 % |
| Is binary classification appropriate? | Only with an uncertainty band. 17 of 72 absolute labels and 22 of 72 relative labels are within 1.96 survey SE of their cut-off, so they cannot be called HIGH or LOW with confidence |
| Are per-round targets appropriate? | **Not with 4 HIGH provinces.** A model with FINAL's true pooled skill passes the 2021 count targets only 27 % of the time, and all three rounds only 14 %. The 95 % interval for an observed 1/4 recall is [0.006, 0.81] (`../aiPHeed_final_model_optimization_20261113/evidence/OPT_statistical_limit.json`) |

## 2. Root cause: supported by evidence vs. still hypothesis

**Supported by evidence**
1. **Over-extrapolated time trend (design).**
   - FINAL's 2021 levels are 6.0 pp too low on average (`SUPP_absolute_continuous_soft.csv`).
   - The national value it starts from (2019, 46.9 %) is 0.24 logit too high. So its elapsed-time decline overshoots by about 0.5 logit.
   - In reality, the 2021 provinces fell about as much as the nation did (about 13 points each).
   - Genuine long-gap training (LG) halves this bias. Persistence, which has no trend at all, is 12.9 pp too high, so the trend itself is real and needed.
2. **Within-round ranking adds nothing over persistence in 2021.**
   - Spearman rank correlation with the outcome, FINAL vs persistence: 2018 0.85 vs 0.59; 2019 0.62 vs 0.62; 2021 0.67 vs 0.67.
   - The three missed HIGH provinces are confident labels: Masbate, Occidental Mindoro and Agusan del Sur are clearly above 50 %.
   - The borderline rows are LOW provinces just under 50: Leyte 49.8, Negros Occidental 48.6, Negros Oriental 47.9. So the misses are real, not label noise.
   - Nothing available before the forecast date re-ranks these provinces: not the 48 inputs, not their changes since the last survey (DELTA), not their trajectories (TRAJ).
3. **Too few positives to judge the round.** 2021 has 4 HIGH provinces (§1).
4. **The relative target does not help.** Tested here (§4): moving the cut-off to the national value puts it in the dense middle of the province distribution.

**Hypotheses not testable now**
- Unobserved provincial shocks (COVID-period livelihood losses; typhoon recovery in Masbate and Occidental Mindoro).
- Differences in ENNS rolling-sample composition behind the national swings.
- Missing provincial-change data: 4Ps coverage, night lights, displacement.

**Ruled out by earlier studies:** class imbalance, the 0.50 threshold (even oracle thresholds fail), label noise for the misses, missing data in the decisive inputs.

## 3. Alternatives investigated (beyond LightGBM tweaks)

| Approach | Implemented? | Result |
|---|---|---|
| National-relative target (province > national, same round) | Yes (PROTOCOL_REL) | Balanced rounds (13/9, 14/11, 13/12), but 31 % of labels are borderline. Every model scores ≈ 0.19 Brier |
| Measurement-error-aware empirical-Bayes hierarchical model (REL-HB, non-ML, region-shrunk relative anchor) | Yes | Brier 0.185 and AUC 0.79 on the relative target, the best of the relative models. Stable when a training round is dropped. Has no inputs, so it cannot explain triggers |
| Relative persistence (REL-P) | Yes | Brier 0.193. On confidently labelled rows it meets all 8 targets in every round, which locates the difficulty in label noise |
| Hybrid: statistical relative anchor + LightGBM residual (REL-LGBM) | Yes (FINAL engine, 5 seeds) | 2021 13/3/0/9 (all 8 targets) for every seed, but fails 2018 (BA 0.70, accuracy 0.73) and 2019 (F1 0.59). Pooled Brier 0.192, AUC 0.74. Dropping 2018 from training turns 2021 into 9/5/4/7 |
| FINAL scored against the relative label | Yes | Best relative ranking (AUC 0.84), but recall 0.50, because the latest released national value is too high |
| Survey-gap-aware training with genuine long-gap pairs (LG) | Yes (previous study) | Best level forecaster (§5) |
| Change-since-survey inputs and province trajectories (DELTA, TRAJ) | Yes (previous study) | No 2021 gain |
| Continuous and ordinal evaluation (prevalence error, rank correlation, soft-label Brier, three tiers) | Yes (evaluation only) | Informative even with 4 HIGH provinces; separates level error from ranking error |
| New provincial-change data | Assessed | Inadmissible at the 2021 forecast date (provincial GDP, provincial LFS, COVID), or needs owner-approved acquisition (night lights, 4Ps, displacement) |

## 4. Comparison under both targets (Lead 1, 5-seed mean, cut-off 0.50)

**Relative target** (HIGH = above national; counts HIGH/LOW: 2018 13/9, 2019 14/11, 2021 13/12)

| Model | 2018 TP/FP/FN/TN · F1 · BA | 2019 · F1 · BA | 2021 · F1 · BA | Pooled Brier · AUC · Acc | All 8: 18/19/21/pooled |
|---|---|---|---|---|---|
| REL-LGBM | 11/4/2/5 · 0.79 · 0.70 | 8/5/6/6 · 0.59 · 0.56 | 13/3/0/9 · 0.90 · 0.88 | 0.192 · 0.74 · 0.72 | ✗ ✗ ✓ ✗ |
| REL-HB | 12/5/1/4 · 0.80 · 0.68 | 12/5/2/6 · 0.77 · 0.70 | 8/4/5/8 · 0.64 · 0.64 | 0.185 · 0.79 · 0.69 | ✗ ✗ ✗ ✗ |
| REL-P | 10/5/3/4 · 0.71 · 0.61 | 11/2/3/9 · 0.81 · 0.80 | 8/3/5/9 · 0.67 · 0.68 | 0.193 · 0.76 · 0.71 | ✗ ✓ ✗ ✗ |
| FINAL scored as relative | 8/1/5/8 · 0.73 · 0.75 | 9/2/5/9 · 0.72 · 0.73 | 3/0/10/12 · 0.38 · 0.62 | 0.212 · 0.84 · 0.68 | ✗ ✗ ✗ ✗ |
| Always-LOW | — | — | — | 0.556 · 0.50 · 0.44 | ✗ |

**Paired bootstrap of pooled Brier:**
- REL-LGBM − FINAL-as-relative: −0.021 [−0.086, 0.044]
- REL-LGBM − REL-P: −0.002 [−0.039, 0.034]
- REL-LGBM − REL-HB: +0.007 [−0.020, 0.034]

**Verdict under PROTOCOL_REL:** NOT RECOMMENDED. REL-LGBM fails the pooled targets (a), fails the targets in 2018 and 2019 (b), and falls more than 0.05 below FINAL's F1/BA in 2018/2019 (d). LightGBM adds no measurable value over the two-parameter statistical model on this target.

**Absolute target (current; counts 2018 8/14, 2019 13/12, 2021 4/21)**

| Model | 2018 | 2019 | 2021 | Pooled Brier · AUC · Acc · F1 | Prevalence error (pp) / 2021 bias (pp) |
|---|---|---|---|---|---|
| FINAL | 8/3/0/11 ✓ | 11/2/2/10 ✓ | 1/0/3/21 ✗ (count targets not evaluable: 4 HIGH) | 0.123 · 0.898 · 0.861 · 0.80 | 7.73 / −6.0 |
| FINAL-LG | identical ✓ | identical ✓ | 1/1/3/20 ✗ (not evaluable) | 0.123 · 0.907 · 0.847 · 0.78 | **7.36 / −3.2** |
| Persistence | 8/9/0/5 ✗ | 12/5/1/7 ✓ | 4/12/0/9 ✗ | 0.253 · 0.827 · 0.625 · 0.64 | 11.16 / +12.9 |
| REL-LGBM converted to absolute | 7/10/1/4 ✗ | 9/5/4/7 ✗ | 4/10/0/11 ✗ | 0.252 · 0.691 · 0.583 · 0.57 | — |

**Soft-label Brier** (scored against the probability that the true value is ≥ 50 %, given the survey SE): FINAL 0.106, LG 0.104, persistence 0.213.

## 5. Decision matrix

| Candidate solution | Why it may solve the problem | Evidence supporting it | Main weaknesses | Validation required | Overall suitability |
|---|---|---|---|---|---|
| A. FINAL as is (absolute target, LightGBM RATE+MIND) | Strongest probabilistic forecaster | Brier 0.123, AUC 0.90, beats all six baselines; passes 2018, 2019 and pooled | 2021 level bias −6 pp from the over-extrapolated time trend; 2021 recall 1/4 | Prospective round (sealed `80b20aed`) | High (current official) |
| **B. FINAL-LG (A + genuine long-gap training pairs)** | Removes the extrapolation using real long-gap outcomes instead of extrapolating | Pooled prevalence error −0.38 pp [−0.71, −0.01]; 2021 bias −6.0 → −3.2 pp; 2021 Brier and AUC better; 2018/19 identical; all seeds identical in 2021 | One more 2021 false alarm (Sarangani); Brier tied; failed the locked count-target rule; only one long-gap round exists | Seal now beside FINAL; score both on the next FNRI round | **Highest: selected** |
| C. Relative target + REL-LGBM | Cancels national shifts; balanced rounds | 2021 passes | Fails 2018/19; label noise 31 %; LightGBM ≤ statistical model; unstable to round drops | — | Low |
| D. Relative target + REL-HB (non-ML) | Parsimonious; uncertainty-aware | Best relative Brier (0.185) | No inputs, so no trigger explanation (the dashboard needs it); relative labels noisy; conflicts with Objective 2 ("evaluate the LightGBM model") | — | Medium as a baseline only |
| E. Three-tier output with survey-SE band; soft-label scoring | Treats survey uncertainty honestly; avoids false certainty near 50 % | 17/72 labels borderline; soft Brier 0.106 | Does not change the 2021 misses (they are confident) | Adviser approval | High (complement) |
| F. Power-aware acceptance rule (count targets binding only with ≥ 8 HIGH and ≥ 8 LOW; pooled; CIs) | Per-round targets with 4 HIGH are decided by chance | Monte Carlo 27 % / 14 %; recall CI [0.006, 0.81] | Could look like weakening, so it must be fixed before the next round and applied to every model | Adviser approval | Required |
| G. New provincial-change data (4Ps, night lights, displacement) | Could re-rank provinces with equal anchors | None testable without acquisition | Approval and acquisition needed; must be judged prospectively | Its own protocol | Future |

## 6. Selected solution and why

1. **What is wrong with the current approach**
   - **Level:** its elapsed-time term extrapolates a decline beyond the gaps it was trained on. 2021 was the only round outside that range, and its levels came out 6 pp too low.
   - **Evaluation:** it judges a 4-positive round with count targets.
   - **Not wrong:** the absolute target itself. The relative alternative is worse (§4).
2. **What the solution changes**
   - **(B) Training data:** add genuine 2013-anchored 2018/2019 outcomes, so the model sees 20–24-quarter gaps. No other change.
   - **(E) Reporting:** add a HIGH / BORDERLINE / LOW band from the survey SE.
   - **(F) Acceptance:** fix the power-aware rule now.
3. **Why this addresses the actual failure, not just a metric**
   - B removes the documented mechanism (extrapolation) with real outcomes, not synthetic rows or tuning.
   - E and F stop judging the model on outcomes the survey cannot resolve.
4. **Why it fits provincial food-insecurity forecasting**
   - It keeps prevalence (absolute need), the 50 % threshold and the HFIAS outcome the manuscript defines.
   - It keeps LightGBM's inputs, so the trigger explanations remain.
   - It reports uncertainty where a survey cannot separate a province from the threshold.
5. **What it keeps from FINAL**
   - The engine, inputs, grid, seeds and folds are unchanged.
   - 2018 and 2019 forecasts are bit-identical (max |Δp| = 0.0).
6. **What would prove it better**
   - Sealed FINAL and FINAL-LG forecasts scored on an unseen FNRI provincial round.
   - Primary criterion: paired prevalence error and Brier, with CIs.
   - Count targets are binding only if that round has at least 8 HIGH and at least 8 LOW provinces.
7. **What could still make it fail**
   - Only one long-gap round exists, so the long-gap relationship may not generalise.
   - It still ranks provinces with equal anchors no better than persistence.
   - National shifts between rounds remain unforecastable.

## 7. Implementation and evaluation summary

**Implemented**
- PROTOCOL_REL arms (21 LightGBM fits, plus the statistical models).
- Evaluation of both targets, the soft-label and continuous scores, and the LG-vs-FINAL bootstrap.
- FINAL-LG itself was built and checked earlier (R1 reproduction exact, R2 anchors correct; `../aiPHeed_final_model_optimization_20261113/`).

**Seeds**
- REL-LGBM: 2021 is 13/3/0/9 for every seed; pooled Brier 0.190–0.194.
- LG: 2021 is 1/1/3/20 for every seed.

**Training-round sensitivity (2021 fold)**
- REL-LGBM: 13/3/0/9 → 9/5/4/7 without 2018, 12/3/1/9 without 2019. Unstable.
- REL-HB: 8/4/5/8 → 11/4/2/8 without 2019.
- 2013-national sensitivity (setting it to 53.8 %) changes REL-HB pooled Brier by 0.0006.

**Baselines (absolute target):** FINAL beats persistence, climatology, always-LOW, PSA-indicator, logistic regression and NLP-only on pooled Brier. All six CIs exclude 0 (`../aiPHeed_final_reliability_20261113/evidence/REL_vs_baselines.csv`). LG's pooled Brier is within 0.0004 of FINAL's; LG was not separately bootstrapped against these baselines.

**Leakage checks**
- Relative anchors use only rounds released by the origin (2013, 2015) and their national values.
- The target-round national value enters only the label.
- Test tables carry no outcomes.
- No synthetic data; no threshold or weight chosen from evaluation outcomes.

**Evaluation reuse:** the province values had been inspected many times; only the relative labels are new. None of this is independent validation.

## 8. Objective alignment and final recommendation

**Objective alignment**
- **Objective 2** (evaluate LightGBM by accuracy, precision, recall, F1, AUC and lead time, with chronological walk-forward validation): met retrospectively by FINAL and FINAL-LG at Lead 1, pooled and in every round where the count targets can be evaluated. 2021 (4 HIGH) cannot support a count-based verdict.
- **Objective 4** (four baselines): met.

**Recommendation**

| Question | Answer |
|---|---|
| Is FINAL-LG better than FINAL? | Better as a level forecaster (significant on prevalence error). Not shown better on Brier or classification |
| Is it ready? | Ready for prospective validation only, not for production |
| What to do next, with owner approval | Seal FINAL-LG forecasts beside FINAL's `80b20aed` |
| What the adviser must approve | The three-tier band and the power-aware rule, fixed before the next round |
| What stays as is | FINAL remains official; the dashboard is unchanged; the national-relative target is not adopted |

**Sources:** [PSA PPA release announcement](https://psa.gov.ph/system/files/PR-Announcement-of-PPA-Releases.pdf), [EOG VNL](https://eogdata.mines.edu/products/vnl/), [DSWD Pantawid Q2 2020](https://pantawid.dswd.gov.ph/wp-content/uploads/2020/09/2nd-Quarterly-Report-2020.pdf), [FNRI 8th NNS](https://fnri.dost.gov.ph/index.php/19-nutrition-statistic/118-8th-national-nutrition-survey). National HFIAS values come from local FNRI sources: 2015 report Appendices 1–4, ENNS 2018/2019 factsheets, ENNS 2021 Table F.2.
