# FINAL model optimization across ENNS 2018 / 2019 / 2021 (2026-11-13)

**Bottom line**
- No candidate meets all 8 targets in ENNS 2021, so FINAL stays the model.
- Thirty arms were scored per round. Twenty-nine were non-synthetic (FINAL plus 28 alternatives); persistence was the baseline. Synthetic-data arms are excluded because the owner prohibits them.
- The two new structural redesigns run in this study were change-since-survey inputs and genuine long-gap training pairs. Both leave 2018 and 2019 intact. Neither changes the 2021 ranking.
- The statistical limit, shown with evidence:
  - With only 4 HIGH provinces in 2021, a model as good as FINAL's true pooled skill passes the 2021 count targets only 27 % of the time, and all three rounds only 14 %.
  - Passing 2021 needs 3 of its 4 HIGH provinces ranked in the top 4–5 of 25.
  - No public input available before the 2021 forecast date produces that ranking. Persistence comes closest (AUC 0.899) and still fails.
- Nothing was put into the dashboard. Nothing was committed.

Folder: `research_notes/aiPHeed_final_model_optimization_20261113/`.

| Item | File |
|---|---|
| Protocol 1 | `PROTOCOL_OPT.md`, sha256 `bb05c253…`. Written before the DELTA, TRAJ and DELTA_TRAJ arms were fitted |
| Protocol 2 | `PROTOCOL_OPT2.md`, sha256 `f3a6fdf7…`. Written before the long-gap arm was built |
| Erratum | `ERRATUM_PROTOCOL_OPT2.md` |
| Scripts | `scripts/run_opt.py`, `opt_eval.py`, `build_lg.py`, `r1_after_load.py`, `opt2_eval.py`, `opt_limits.py` |
| Evidence | `evidence/OPT_per_round_L1.csv`, `OPT_verdict.json`, `OPT_province_rows_L1.csv`, `OPT2_LG_per_round_L1.csv`, `OPT2_verdict.json`, `OPT2_LG_2021_rows.csv`, `LG_build_log.json`, `LG_R1_after_load.json`, `DELTA_missingness.json`, `OPT_statistical_limit.json` |
| Predictions | `parts/` (DELTA, TRAJ, DELTA_TRAJ, LG, NOPAIR; 61 fits) |

## 1. Existing model weaknesses (FINAL, Lead 1)

| Round | HIGH / LOW | TP/FP/FN/TN | Recall | Precision | F1 | BA | Brier | Acc | ROC-AUC | PR-AUC (prevalence) | All 8 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| ENNS 2018 | 8 / 14 | 8/3/0/11 | 1.00 | 0.73 | 0.84 | 0.89 | 0.130 | 0.86 | 0.964 | 0.950 (0.36) | ✓ |
| ENNS 2019 | 13 / 12 | 11/2/2/10 | 0.85 | 0.85 | 0.85 | 0.84 | 0.151 | 0.84 | 0.853 | 0.841 (0.52) | ✓ |
| ENNS 2021 | 4 / 21 | 1/0/3/21 | **0.25** | 1.00 | **0.40** | **0.63** | 0.090 | 0.88 | 0.857 | 0.610 (0.16) | ✗ |
| Pooled | 25 / 47 | 20/5/5/42 | 0.80 | 0.80 | 0.80 | 0.85 | 0.123 | 0.86 | 0.898 | 0.846 (0.35) | ✓ |

- **2021 failure:** FINAL misses 3 of the 4 HIGH provinces in 2021 (Masbate, Occidental Mindoro, Agusan del Sur). This fails three targets: recall, F1 and BA.
- **Rounds rarely re-measured:** every 2021 province was last measured in 2015, 24 quarters earlier.
- **Earlier 2019 issue:** misses tied to regional GRDP and Marawi displacement. That was found in an earlier study; 2019 still passes.

## 2. Root causes of the inconsistency

1. **Gap extrapolation (design).**
   - 2021-fold training covers gaps of 8, 14 and 16 quarters; the 2021 test gap is 24.
   - FINAL's elapsed-time (RATE) term is −0.48 logit in 2021, against −0.19 and −0.25 in 2018 and 2019. It predicted a decline of about 19 points; the actual decline was about 13.
   - **Confirmed and fixed here (LG, §4).** Adding genuine gap-20–24 training rows raises 2021 probabilities by about 0.07 and improves 2021 Brier and AUC.
2. **Ranking among high-start provinces (information).**
   - Seven provinces started at 2015 levels of 64.7–69.1 %.
   - Three of them stayed HIGH: Masbate (68.3), Occidental Mindoro (66.7), Agusan del Sur (64.7).
   - Four fell to LOW: Sarangani (69.1), Negros Oriental (67.9), North Cotabato (67.8), Negros Occidental (66.7).
   - Nothing available at the 2021 origin orders them correctly: not the 48 FINAL inputs, not their changes since 2015 (DELTA), not their own earlier trajectory (TRAJ), not long-gap training (LG).
   - **This cause is not fixable with current data.**
3. **Too few 2021 positives (statistics).**
   - With 4 HIGH provinces, one province moves recall by 0.25.
   - The 95 % interval for an observed 1/4 is 0.006–0.81, so it is consistent with a true recall of 0.80 (§12 and `OPT_statistical_limit.json`).
4. **Ruled out by earlier studies:**
   - class imbalance (2021 training was 52 % HIGH, with balanced weights);
   - the 0.50 threshold: even a threshold tuned on the 2021 answers fails for every model (`../aiPHeed_final_round_recovery_20261113/evidence/RR_oracle_threshold_2021.csv`);
   - label noise (assumed survey SE changes outcomes by only 1.3–4.5 pp);
   - missing data in the decisive inputs.

## 3. Architectures and strategies investigated

| Family | Arms (all chronological, Lead 1, 5 seeds unless noted) | Source |
|---|---|---|
| Time representation / survey-gap awareness | BASE (gap as a plain input), RATE, RATE_SQRT, FINAL-ET (time since latest release), FINAL-SA (time capped at training support), FINAL-ETMIX, **LG (genuine long-gap pairs, new)** | 11-12 / 11-13 studies; LG here |
| Missing-data handling | IMPUTE, MIND, RIMP, DROPGAP | 11-12 |
| Survey composition | COMP (HFIAS mild/severe shape of the anchor survey) | 11-12 |
| Province trajectories / hierarchical | **TRAJ (new):** own change, regional and national change, deviation from the region, volatility between released rounds | PROTOCOL_OPT |
| Change-explaining inputs | **DELTA (new):** change since the anchor survey in poverty, subsistence, poverty gap and regional GRDP; **DELTA_TRAJ (new)** | PROTOCOL_OPT |
| Seasonal data gaps | FINAL-CF (one-quarter carry-forward) | 11-13 |
| Regularisation / variance | CAP, CAPVAR, VAR, CONV | 11-12 (supplementary, stored) |
| Anchor shrinkage | A025/A050/A075/A100 × IMP/MIND | 11-12 (supplementary, stored) |
| Ensemble / hybrid | STACK and STACK-ET (FINAL + persistence; weight learned on earlier rounds only, came out at 1.0) | 11-13 |
| Rolling-origin model selection | **SELECT (new):** picks the arm for 2021 by log loss on the 2018 + 2019 out-of-sample forecasts | PROTOCOL_OPT |
| Class weighting / synthetic balance | 46 arms in the 11-12 studies; synthetic arms are excluded (owner prohibition) | 11-12 |
| New external data | PSA provincial GDP, provincial LFS, 4Ps, VIIRS night lights, DROMIC, COVID (§3a) | this report |

### 3a. Candidate new indicators (genuine availability at the 2021 Lead-1 origin)

| Indicator | Source / resolution | History | Available before the 2021 origin? | Verdict |
|---|---|---|---|---|
| Provincial GDP (PPA) | PSA, provincial, annual | 2018– | **No.** Pilot regions (MIMAROPA, Central Visayas) were first released in December 2021 and the full 2018–2021 series in December 2022 | Inadmissible for 2021; prospective use only |
| Provincial labour force | PSA LFS provincial | 2022– | No | Prospective only |
| Change in provincial poverty since the anchor survey | PSA SAE 2015/2018, provincial | 2009– | Yes (2018 estimates published before 2021) | **Tested (DELTA):** ≥95 % present, no 2021 gain |
| Change in regional GRDP since the anchor survey | PSA RAA, regional | yearly | Yes | **Tested (DELTA):** no 2021 gain |
| 4Ps households | DSWD quarterly-report PDF appendices, province/municipality | appendices seen for 2019–2020; earlier years unverified | Partly | Not tested: needs PDF extraction, and coverage for the training origins (2013–2019) is unverified |
| VIIRS night lights | EOG / Payne Institute annual VNL v2, 500 m | 2012– | Yes | Not tested: download requires creating an EOG account and multi-GB rasters, which needs owner approval |
| DROMIC displacement | DSWD per-event PDFs | 2014– | Yes | Not tested: needs a large compilation, and 2013 is missing |
| COVID-19 cases and quarantine level | DOH DataDrop / IATF | 2020– | Yes | **Inadmissible as a learned input:** zero in every training round, so a tree cannot learn its effect |
| Typhoon exposure since the anchor survey | already in the inputs (`vu_tc_*`, `tc_rate_since`) | — | Yes | Already tested; did not separate the provinces |

Sources: [PSA PPA release announcement](https://psa.gov.ph/system/files/PR-Announcement-of-PPA-Releases.pdf), [PSA PPA Western Visayas](https://psa.gov.ph/system/files/sead/Press-Release_PPA_R6.pdf), [PIA: Central Visayas first PPA (Dec 2021)](https://mirror.pia.gov.ph/news/2021/12/10/psa-7-launches-provl-product-account-in-cv), [DSWD Pantawid 2nd Quarterly Report 2020](https://pantawid.dswd.gov.ph/wp-content/uploads/2020/09/2nd-Quarterly-Report-2020.pdf), [EOG VNL](https://eogdata.mines.edu/products/vnl/), [Payne Institute: EOG registration](https://payneinstitute.mines.edu/?p=3162).

## 4. Experiments in this study and their evidence

**PROTOCOL_OPT (DELTA, TRAJ, DELTA_TRAJ; 45 fits; `OPT_per_round_L1.csv`).**
- Engine, grid, seeds and folds are FINAL's; only the candidate inputs differ.
- 2018 and 2019 are unchanged (DELTA improves Brier slightly: pooled 0.1223 vs 0.1233).
- In 2021, every one of the three arms gives 1/0/3/21. TRAJ and DELTA_TRAJ lower 2021 ROC-AUC (0.786 vs 0.857).
- The engine selected the trajectory inputs in the 2021 fold, but they reordered the wrong provinces.
- **SELECT:** chose FINAL-CF for 2021 (the lowest 2018 + 2019 log loss, 0.4291). Result: 2021 1/0/3/21.

**PROTOCOL_OPT2: LG, survey-gap-aware training with genuine long-gap pairs (16 fits; `OPT2_*`).**
- **The rows:** 376 extra training rows. These are the ENNS 2018/2019 outcomes, anchored on each province's NNS 2013 round (gap 20–24 quarters), with genuine inputs at each row's issue quarter.
- **Release check:** all rounds were released before the 2021 origin (`LG_build_log.json`). The 2018 and 2019 folds have no such pairs before their origins, so LG equals FINAL there (max |Δp| = 0.0).
- **Check R1:** rebuilding the 2021 table without pairs reproduces FINAL's table exactly (max diff 0.0) and its seed-168 probabilities (max diff 0.0). LG therefore differs from FINAL only by the pair rows.
- **Check R2:** every pair anchor is NNS 2013.
- **Result in 2021:**
  - mean p rises by about 0.07;
  - Brier 0.0887 (FINAL 0.0898), ROC-AUC 0.869 (0.857), PR-AUC 0.624 (0.610);
  - but Sarangani (LOW, p 0.517) crosses 0.50 before Agusan del Sur (HIGH, 0.481), giving **1/1/3/20**. This is identical for every seed.
- **Decision:** under the locked rule, LG fails, and FINAL is kept.

**What the failures revealed, and how each one set up the next test:**
- **DELTA and TRAJ:** the 2021 misses are not explained by how measured conditions changed, or by the province's own earlier trajectory.
- **Next test, LG:** asked whether the cause was the time extrapolation rather than the inputs.
- **What LG showed:** fixing the level with genuine long-gap data does not change the order.
- **What is left:** the binding limit is the ranking of 7 provinces with nearly equal anchors.
- **The only remaining lever:** new provincial-change information (§3a). Each candidate is either inadmissible at the 2021 origin or needs owner-approved data acquisition.

## 5. Best-performing candidate and justification

- **FINAL stays.**
- Several arms tie or beat it on pooled Brier: A100_IMP 0.119, A075_IMP 0.120, A050_IMP 0.122, DELTA 0.122, LG 0.123 and FINAL-CF 0.123, against FINAL's 0.123. All of them give 2021 1/4.
- FINAL-ETMIX is the only arm with 2021 2/4 that keeps 2018 and 2019 intact. It is still short of recall (0.50) and F1 (0.57), and it was designed knowing its components.
- No arm is better than FINAL on all of these together: per-round targets, 2018/2019 preservation, pooled metrics and seeds.
- The blind choice for 2021 (SELECT, made without any 2021 outcome) also gives FINAL's 2021 result.

## 6. Before and after, per round (Lead 1, 5-seed mean, cut-off 0.50)

| Model | 2018 TP/FP/FN/TN · F1 · BA | 2019 · F1 · BA | 2021 · Recall · F1 · BA · Brier · AUC | All 8 in 2018 / 2019 / 2021 |
|---|---|---|---|---|
| FINAL (before) | 8/3/0/11 · 0.84 · 0.89 | 11/2/2/10 · 0.85 · 0.84 | 1/0/3/21 · 0.25 · 0.40 · 0.63 · 0.090 · 0.857 | ✓ / ✓ / ✗ |
| DELTA | same | same | 1/0/3/21 · 0.25 · 0.40 · 0.63 · 0.090 · 0.857 | ✓ / ✓ / ✗ |
| TRAJ | same | same | 1/0/3/21 · 0.25 · 0.40 · 0.63 · 0.101 · 0.786 | ✓ / ✓ / ✗ |
| DELTA_TRAJ | same | same | 1/0/3/21 · 0.25 · 0.40 · 0.63 · 0.101 · 0.786 | ✓ / ✓ / ✗ |
| LG (after) | same (identical) | same (identical) | 1/1/3/20 · 0.25 · 0.33 · 0.60 · 0.089 · 0.869 | ✓ / ✓ / ✗ |
| SELECT | same | same | 1/0/3/21 · 0.25 · 0.40 · 0.63 · 0.091 · 0.869 | ✓ / ✓ / ✗ |
| FINAL-ETMIX | same | same | 2/1/2/20 · 0.50 · 0.57 · 0.73 · 0.100 · 0.869 | ✓ / ✓ / ✗ |
| BASE (= H_cw) | 8/4/0/10 · 0.80 · 0.86 | 13/5/0/7 · 0.84 · 0.79 | 1/1/3/20 · 0.25 · 0.33 · 0.60 · 0.101 · 0.869 | ✗ / ✓ / ✗ |
| Persistence | 8/9/0/5 · 0.64 · 0.68 | 12/5/1/7 · 0.80 · 0.75 | 4/12/0/9 · 1.00 · 0.40 · 0.71 · 0.313 · 0.899 | ✗ / ✓ / ✗ |

All 30 scored arms are in `OPT_per_round_L1.csv`. None meets all 8 targets in 2021.

## 7. Pooled performance (72 province-rounds)

| Model | Acc | Recall | Precision | F1 | BA | Brier | ROC-AUC | PR-AUC |
|---|---|---|---|---|---|---|---|---|
| FINAL | 0.861 | 0.80 | 0.80 | 0.80 | 0.847 | 0.123 | 0.898 | 0.846 |
| LG | 0.847 | 0.80 | 0.77 | 0.78 | 0.836 | 0.123 | 0.907 | 0.853 |
| DELTA | 0.861 | 0.80 | 0.80 | 0.80 | 0.847 | 0.122 | 0.896 | 0.842 |
| FINAL-ETMIX | 0.861 | 0.84 | 0.78 | 0.81 | 0.856 | 0.127 | 0.903 | 0.849 |
| Persistence | 0.625 | 0.96 | 0.48 | 0.64 | 0.703 | 0.253 | 0.827 | 0.705 |

FINAL, LG, DELTA and ETMIX all pass every pooled target.

## 8. Confusion matrices (HIGH = positive)

**FINAL** (rows: actual HIGH / actual LOW; columns: predicted HIGH / predicted LOW)
- 2018: [8, 0 / 3, 11]. HIGH caught 8/8; LOW correct 11/14.
- 2019: [11, 2 / 2, 10]. HIGH 11/13; LOW 10/12.
- 2021: [1, 3 / 0, 21]. HIGH 1/4 (Tawi-Tawi only); LOW 21/21.
- Pooled: [20, 5 / 5, 42].

**LG**
- 2018 and 2019: identical to FINAL.
- 2021: [1, 3 / 1, 20]. The false alarm is Sarangani.
- Pooled: [20, 5 / 6, 41].

**2021 probability order under LG** (top 10; ★ = HIGH):
Tawi-Tawi★ 0.93, Sarangani 0.52, Agusan del Sur★ 0.48, Surigao del Norte 0.36, Leyte 0.36, Negros Occidental 0.29, Occidental Mindoro★ 0.28, North Cotabato 0.27, Romblon 0.24, Masbate★ 0.23.

## 9. Seed stability and sensitivity

| Model | Seeds | Pooled accuracy range | 2021 result across seeds |
|---|---|---|---|
| FINAL | 168/1/2/3/4 | 0.847–0.861 | every seed passes the pooled targets |
| DELTA | same | 0.847–0.861 | 2021 unchanged |
| TRAJ | same | 0.833–0.861 | 2021 unchanged |
| LG | same | 0.833–0.847 | **1/1/3/20 in every seed**; 2018 identical; 2019 10–11 TP |

- **Training-round removal (2021 fold, earlier study):** recall moves between 1/4 and 3/4. 2021 HIGH detection is not stable to which rounds are in training.
- **Input ablation (`../aiPHeed_final_reliability_20261113/evidence/CONTRIB_group_retrain_L1.csv`):**
  - Only regional economy (ΔBrier +0.029 [0.003, 0.054]) and agriculture/fish (+0.011 [0.001, 0.020]) improve out-of-sample performance significantly.
  - Market and poverty: confidence intervals include 0.
  - Climate and employment: about 0 effect.
- **Change-input sensitivity (this study):** DELTA −0.001 Brier; TRAJ +0.004 Brier and −0.07 2021 AUC.

## 10. Baseline comparisons (Lead 1, pooled)

| Baseline | Brier | Acc | F1 | FINAL ΔBrier [95 % CI] |
|---|---|---|---|---|
| Always-LOW | 0.347 | 0.653 | 0.00 | −0.224 [−0.338, −0.112] |
| Climatology | 0.292 | 0.347 | 0.52 | −0.169 [−0.220, −0.119] |
| Persistence | 0.253 | 0.625 | 0.64 | −0.130 [−0.197, −0.069] |
| PSA-indicator logistic | 0.274 | 0.556 | 0.60 | −0.150 [−0.211, −0.088] |
| Logistic regression, all inputs | 0.320 | 0.611 | 0.60 | −0.197 [−0.288, −0.116] |
| NLP-only logistic | 0.244 | 0.639 | 0.59 | −0.121 [−0.183, −0.063] |

Source: `../aiPHeed_final_reliability_20261113/evidence/REL_vs_baselines.csv`. LG and DELTA beat persistence by the same margin.

## 11. Leakage and chronological-validation checks

| Check | Result |
|---|---|
| Release lag | Every training round satisfies reference quarter + 6 ≤ forecast origin. The test round is never in training. 110 FINAL fits, 0 violations (`LEAK_origin_check.json`) |
| LG pair rows | Targets released before the 2021 origin (`pair_target_release_ok: true`); anchor NNS 2013 for every row (R2) |
| LG table reproduction (R1) | Rebuilt without pairs, the table equals FINAL's exactly, and probabilities match to 0.0 (`LG_R1_after_load.json`) |
| DELTA values | Both the origin-quarter value and the anchor-quarter value come from as-of panels: published by the origin, no outcome used |
| Engineered inputs | Unchanged when all future panel values and unreleased outcomes are replaced with noise (`aiPHeed_complete_validation/tests/opt_cache.py leakcheck`) |
| Model selection | SELECT used only 2018 + 2019 out-of-sample forecasts. STACK weights were learned on earlier rounds only. No threshold or weight was chosen from 2021 |
| Synthetic labels | None |
| Evaluation reuse | The 72 province-rounds have now been viewed in about 33 arm evaluations. No result here counts as independent validation |

## 12. Final acceptance status (FINAL, which remains the model)

| Metric (target) | 2018 | 2019 | 2021 | Pooled |
|---|---|---|---|---|
| HIGH recall (≥ 0.70) | ✓ 1.00 | ✓ 0.85 | ✗ 0.25 | ✓ 0.80 |
| F1 HIGH (≥ 0.70) | ✓ 0.84 | ✓ 0.85 | ✗ 0.40 | ✓ 0.80 |
| Precision HIGH (≥ 0.70) | ✓ 0.73 | ✓ 0.85 | ✓ 1.00 | ✓ 0.80 |
| Balanced accuracy (≥ 0.70) | ✓ 0.89 | ✓ 0.84 | ✗ 0.63 | ✓ 0.85 |
| Brier (≤ 0.20) | ✓ 0.130 | ✓ 0.151 | ✓ 0.090 | ✓ 0.123 |
| Accuracy (≥ 0.75) | ✓ 0.86 | ✓ 0.84 | ✓ 0.88 | ✓ 0.86 |
| ROC-AUC (≥ 0.70) | ✓ 0.964 | ✓ 0.853 | ✓ 0.857 | ✓ 0.898 |
| PR-AUC (> prevalence) | ✓ 0.950 > 0.36 | ✓ 0.841 > 0.52 | ✓ 0.610 > 0.16 | ✓ 0.846 > 0.35 |

**Gate:** NOT MET. 2021 fails recall, F1 and BA, and no candidate fixes it.

**Statistical-limit evidence (`OPT_statistical_limit.json`, 200,000 simulations at the real round sizes):**
- These are the chances of passing the count-based targets (recall, precision, F1, BA, accuracy).

| True model skill | 2018 | 2019 | 2021 | All three rounds |
|---|---|---|---|---|
| FINAL's pooled skill (recall 0.80, false-alarm rate 0.106) | 72 % | 74 % | **27 %** | **14 %** |
| Same, with posterior uncertainty | 61 % | 64 % | 24 % | 12 % |
| Recall 0.90, false-alarm rate 0.05 (far better than any arm) | 95 % | 97 % | 68 % | 63 % |

- **Why 2021 is so hard:** passing it requires at least 3 TP of 4 *and* at most 1 false alarm among 21 LOW provinces.
- **Recall intervals:** 2021 recall of 1/4 has a 95 % interval of [0.006, 0.81]; pooled recall of 20/25 has [0.59, 0.93].
- **Conclusion:** the per-round targets in 2021 cannot statistically separate a good model from a bad one.

**Other gate items**

| Item | Status |
|---|---|
| HIGH detection meaningful | Yes, pooled and in 2018/2019. **No in 2021** |
| LOW detection reliable | Yes (2021 LOW correct 21/21) |
| Stable across seeds | Yes |
| Stable across training rounds | **No** |
| Chronological validation and no leakage | Yes |
| No synthetic labels | Yes |
| Baselines | Completed; FINAL beats all six on pooled Brier |
| One-quarter-ahead forecasting | Demonstrated retrospectively with genuine out-of-sample Lead-1 forecasts (72 rows, chronological). Not independently validated |

## 13. Remaining limitations and independent validation requirements

1. **No unseen provincial HFIAS round exists** for independent confirmation. ENNS 2022 is excluded by owner rule.
   - FINAL's sealed forecasts (`80b20aed…`) are the confirmation path: score them against the next eligible FNRI provincial round.
2. **LG is the most defensible design change.** It removes the extrapolation with genuine data, improves 2021 Brier and AUC, and leaves 2018/2019 identical. But it did not pass the locked rule.
   - If the owner wants it pursued, lock and seal LG forecasts alongside FINAL's now, and score both on the next round. Do not re-tune either on the 72 rows.
3. **New provincial-change data needs owner approval** to acquire (VIIRS account, 4Ps PDF extraction, DROMIC compilation). Each source needs its own locked protocol and must be judged prospectively. The 2021 round has already been viewed too often to count as a test.
4. **ENNS 2021 has only 4 HIGH provinces,** so per-round recall targets there are dominated by chance (§12). A per-round acceptance rule for future rounds should require a minimum number of HIGH provinces or use interval-based criteria. That is an owner/adviser decision.
5. **Nothing here is committed or deployed.** The production dashboard is unchanged.
