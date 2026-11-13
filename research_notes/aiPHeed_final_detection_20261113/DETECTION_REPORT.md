# Detecting the four ENNS 2021 HIGH provinces: investigation, new method, decision (2026-11-13)

**Summary**
- **New signal.** Given a province's starting level, its *structural poverty and income* predict where its food insecurity moves relative to the national value. This was confirmed on survey transitions with no 2021 involvement.
- **New model.** A Bayesian structural-attractor model (ATTR) built on that signal is the first model in this project to meet **all 8 targets in every ENNS round**. That is on the national-relative label (is the province above or below the national value?).
  - Pooled: Brier 0.159, ROC-AUC 0.845, accuracy 0.81.
  - Stable when any training transition is removed.
  - Significantly better than relative persistence.
- **The four 2021 HIGH provinces on the absolute ≥ 50 % label: still not detectable without excessive false alarms.**
  - The structural method lifts Masbate from rank 10 to 5 and gives the best 2021 ROC-AUC of any model (0.905).
  - It also lifts Sarangani and North Cotabato. Those are the poorest of the high-starting provinces, yet they improved the most.
  - Among the 8 provinces that started 2015 at 64 % or more, every model separates the 4 HIGH from the 4 LOW at close to chance (AUC 0.47–0.63).
- **What would be needed.** The distinguishing 2021 pattern (recent typhoons in Masbate and Occidental Mindoro) runs *opposite* to every earlier transition. No method trained on the historical record can learn it. Testing it requires data not yet compiled: post-disaster assistance (DSWD DROMIC) and 2020 Social Amelioration Program (SAP) coverage by province.
- FINAL and FINAL-LG are unchanged. Nothing is in the dashboard. Nothing is committed.

Folder: `research_notes/aiPHeed_final_detection_20261113/`.

| Item | File |
|---|---|
| Protocol | `PROTOCOL_ATTR.md`, sha256 `79ebae22…`. Locked after the transition analysis, before any 2021 province profile was examined and before any ATTR fit |
| Scripts | `scripts/transitions.py`, `attr_run.py`, `attr_rel_sens.py` |
| Evidence | `evidence/TRANS_partial_correlations.csv`, `TRANS_T1_only_selection.csv`, `TRANS_rows.csv`, `ATTR_per_round_L1.csv`, `ATTR_verdict.json`, `ATTR_2021_rows.csv`, `ATTR_relative_sensitivity.json`, `PROFILE_2021_highstart.csv` |

---

## 1. The detection problem, measured

| | FINAL | FINAL-LG | Persistence | HYB (new) | Oracle diagnostic (exact 2021 national value) |
|---|---|---|---|---|---|
| 2021 TP/FP/FN/TN | 1/0/3/21 | 1/1/3/20 | 4/12/0/9 | 1/2/3/19 | 3/4/1/17 |
| 2021 ROC-AUC | 0.857 | 0.869 | 0.899 | **0.905** | 0.905 |
| AUC within the 8 high-start provinces | 0.56 | 0.63 | 0.47 | 0.63 | — |

**Reading the table**
- The problem is **ranking among high-start provinces**, not the threshold or the probability scale.
- Even with the exact 2021 national level, the best ranking gives 3/4 with 4 false alarms (precision 0.43).
- Full detection would need the four HIGH provinces ranked above Sarangani, North Cotabato and Leyte. No model trained on the earlier rounds does that.

## 2. Why the model cannot distinguish them (province-level evidence, `PROFILE_2021_highstart.csv`)

Values are as published at the 2021 forecast date. Poverty, subsistence and GRDP are relative to the same-quarter mean.

| Province | 2015 → 2021 % | Relative change | Poverty | Subsistence | Regional GRDP | Strong typhoons (12 months) | Typhoon count (12 months) | Food CPI, 3 months |
|---|---|---|---|---|---|---|---|---|
| Tawi-Tawi ★ | 72.8 → 62.2 | +0.03 | 0.20 | −0.40 | −0.92 | 0 | 0 | 7.3 |
| Masbate ★ | 68.3 → 59.4 | +0.13 | 0.75 | 0.61 | −0.37 | **3** | **8** | 3.9 |
| Agusan del Sur ★ | 64.7 → 57.9 | +0.23 | 0.96 | 1.25 | −0.18 | 0 | 1 | 5.6 |
| Occidental Mindoro ★ | 66.7 → 56.3 | +0.07 | 0.17 | 0.59 | −0.09 | **2** | **6** | 8.7 |
| Negros Occidental | 66.7 → 48.6 | −0.23 | 0.03 | 0.32 | −0.15 | 0 | 0 | 2.8 |
| Negros Oriental | 67.9 → 47.9 | −0.32 | 0.39 | 0.94 | 0.17 | 0 | 1 | 5.3 |
| Sarangani | 69.1 → 43.7 | −0.54 | **1.13** | **1.93** | −0.22 | 0 | 0 | 6.3 |
| North Cotabato | 67.8 → 34.1 | **−0.89** | **1.11** | **1.96** | −0.22 | 0 | 0 | 2.7 |

★ = HIGH in 2021.

**Is each pattern generalizable?** Each was checked on the three transitions that do not involve 2021 (`TRANS_partial_correlations.csv`). The table shows partial Spearman ρ with the change in relative position, controlling for the starting level.

| Candidate explanation | 2013→2015 (n 78) | 2015→2018 (22) | 2015→2019 (25) | 2015→2021 | Verdict |
|---|---|---|---|---|---|
| Structural poverty / income keeps provinces high: `income_rel` | −0.30 | −0.47 | −0.53 | −0.36 | **Confirmed** (meta-analysis p 2e-5; Holm 0.001) |
| `hh_grdp_rel` | −0.35 | −0.41 | −0.21 | −0.35 | **Confirmed** (Holm 0.018) |
| `p_poverty` | +0.30 | +0.66 | +0.19 | +0.08 | Confirmed in T1–T3 (Holm 0.007); weak in 2021 |
| `p_subsistence` | +0.27 | +0.66 | +0.07 | −0.03 | Confirmed in T1–T3 (Holm 0.043); absent in 2021 |
| Recent strong typhoons keep provinces high (`vu_tc_strong`) | −0.21 | n/a | −0.61 | **+0.49** | **Reversed.** Not learnable from history |
| Typhoon count since the last survey (`tc_rate_since`) | +0.06 | −0.61 | −0.26 | 0.00 | Not supported |
| Local food inflation (`cpi_food_3m`) | +0.16 | +0.35 | +0.05 | +0.30 | Same sign everywhere, not significant (meta p 0.07) |
| Rice output growth (`ag_palay_yoy`) | −0.24 | −0.27 | +0.13 | +0.30 | Inconsistent |
| Agriculture since the last survey (`agri_since`) | −0.09 | +0.05 | −0.35 | −0.54 | Inconsistent |

**What explains the failure**
- **The rule the model should learn mostly holds in 2021.** High-start provinces revert toward a structural level set by poverty and income.
- **Two of the four HIGH provinces follow it:**
  - Agusan del Sur (subsistence +1.25) stays high, as the rule predicts.
  - Tawi-Tawi has the lowest regional GRDP (−0.92) and stays high, as predicted.
- **The other two do not:**
  - Masbate and Occidental Mindoro stay high with only moderate structural poverty. Their distinguishing feature is recent typhoon exposure, whose historical association is the *opposite* sign.
  - Sarangani and North Cotabato have the strongest structural poverty in the group, yet improved most. They are the largest exceptions to the confirmed rule.
- **Hypothesis consistent with the evidence** (not tested; data not compiled): typhoons followed by large-scale assistance (Yolanda, 2013–15) were followed by relative improvement. The 2019–2020 typhoons fell during COVID restrictions, with assistance competing with the pandemic response.

## 3. Information that was overlooked or is missing

| Indicator | Source / resolution | Coverage | Available at the 2021 forecast date? | Status |
|---|---|---|---|---|
| Structural income and poverty level (`income_rel`, `hh_grdp_rel`, poverty, subsistence) | PSA SAE (provincial), regional accounts | 2009– | Yes | **Already in FINAL but under-used.** FINAL shrinks toward the regional/national mean; ATTR uses it as the reversion target |
| Post-disaster assistance and displacement (families assisted, assistance cost) | DSWD DROMIC per-event PDFs, province/municipality | 2014– (2013 missing) | Yes | **Missing; highest priority.** Needed to test whether assistance changes the typhoon effect. Substantial PDF compilation |
| 2020 SAP / emergency subsidy beneficiaries | DSWD reports, region or province | 2020–21 | Yes | Missing. Has no historical counterpart, so it would need an a-priori sign and prospective validation |
| COVID-period livelihood data | PSA provincial LFS | 2022– | No | Prospective only |
| 2021 provincial poverty | PSA FIES 2021 (released August 2022) | 2021 | No (after the forecast date) | Prospective only (for rounds after 2023) |
| Provincial GDP | PSA PPA | 2018– (first release December 2021 / December 2022) | No | Prospective only |
| Night lights | EOG VNL v2 | 2012– | Yes | Requires creating an account; owner approval |

## 4. Methods considered

| Method | Theoretical fit to this problem | Decision |
|---|---|---|
| Change / error-correction model with a structural attractor (Bayesian linear) | Few independent transitions (78 + 22 + 25), a near-linear confirmed signal, survey-error weights | **Implemented (ATTR)** |
| Hybrid: FINAL-LG national level + ATTR within-round ranking (HYB) | The absolute label is national level plus relative position; FINAL-LG is the best level forecaster | **Implemented** |
| LightGBM on relative change (REL-LGBM) | Already tested; ranking AUC 0.74, worse than the two-parameter model | Not repeated |
| Interaction / multi-stressor trees | The only 2021-distinguishing stressor (typhoons) reverses sign across transitions, so interactions would be fitted to 2021 | Rejected a priori |
| Three-state worsening / stable / improving classifier | Only 47 non-2021 transitions with known direction, and the decisive 2021 pattern is absent from them | Rejected a priori |
| Province random-effect (multilevel) model | Each province appears in at most 2 transitions, so province effects are not identifiable beyond the anchor | Rejected a priori |
| Lower the threshold / predict more HIGH | Forbidden, and shown not to help: persistence finds 4/4 with 12 false alarms | Rejected |

## 5. Experiments (hypothesis → change → result)

| # | Hypothesis | Change | Data | Result |
|---|---|---|---|---|
| X1 | Some origin-available input predicts relative change consistently across transitions | Partial-correlation screen across transitions, Holm-corrected; no model fitted | All 4 transitions; 2021 only displayed | Structural poverty and income confirmed; typhoon exposure reversed; prices weak |
| X2 | A model that reverts to the structural level classifies relative risk reliably | ATTR (BayesianRidge on starting level + 5 structural inputs; weighted by survey error; trained only on released transitions) | Fold tables, Lead 1 | **All 8 targets in 2018, 2019, 2021 and pooled** (relative label) |
| X3 | Combining FINAL-LG's level with ATTR's ranking detects the 2021 HIGH provinces | HYB | Same | 2021 AUC 0.905 but 1/2/3/19. Pooled Brier 0.152, worse than FINAL-LG's 0.123 (Δ +0.029 [0.007, 0.049]). **Fails** |
| X4 | X3 does not depend on which level model is used | HYB-F (FINAL level) | Same | 2021 1/0/3/21; same conclusion |
| X5 | With the right national level, the ranking would suffice | Oracle level (diagnostic, uses the 2021 national value) | Same | 3/4/1/17. **The ranking is insufficient even with a perfect level** |

## 6. Results

**Absolute label (HIGH ≥ 50 %; owner's targets)**

| Model | 2018 TP/FP/FN/TN | 2019 | 2021 | Pooled Brier · AUC · Acc · F1 | All 8 targets: 18 / 19 / 21 / pooled |
|---|---|---|---|---|---|
| FINAL | 8/3/0/11 | 11/2/2/10 | 1/0/3/21 | 0.123 · 0.898 · 0.861 · 0.80 | ✓ ✓ ✗ ✓ |
| FINAL-LG | 8/3/0/11 | 11/2/2/10 | 1/1/3/20 | 0.123 · 0.907 · 0.847 · 0.78 | ✓ ✓ ✗ ✓ |
| HYB | 8/5/0/9 | 8/2/5/10 | 1/2/3/19 | 0.152 · 0.862 · 0.764 · 0.67 | ✗ ✗ ✗ ✗ |
| HYB-F | 8/5/0/9 | 8/2/5/10 | 1/0/3/21 | 0.152 · 0.855 · 0.792 · 0.69 | ✗ ✗ ✗ ✗ |
| ATTR scored on the absolute label (using the latest released national value) | 8/12/0/2 | 12/8/1/4 | 4/8/0/13 | 0.236 · 0.868 · 0.597 · 0.62 | ✗ ✗ ✗ ✗ |
| Persistence | 8/9/0/5 | 12/5/1/7 | 4/12/0/9 | 0.253 · 0.827 · 0.625 · 0.64 | ✗ ✓ ✗ ✗ |

**Verdict under PROTOCOL_ATTR:** HYB is NOT RECOMMENDED. It fails checks 1, 2, 3, 4 and 6.
- Check 6 fails because the multivariable fit flips the signs of `income_rel` and `p_subsistence`; the five poverty/income measures are strongly collinear.
- Seeds: every FINAL-LG seed gives 2021 1/2/3/19.
- Training-transition drops: 1/2, 1/0 and 2/2 (TP/FP), so not stable.

**National-relative label (HIGH = above the same round's national value): ATTR**

| Round | TP/FP/FN/TN | Recall | Precision | F1 | BA | Brier | Acc | ROC-AUC | PR-AUC (prevalence) | All 8 |
|---|---|---|---|---|---|---|---|---|---|---|
| ENNS 2018 | 12/3/1/6 | 0.92 | 0.80 | 0.86 | 0.79 | 0.145 | 0.82 | 0.889 | 0.910 (0.59) | ✓ |
| ENNS 2019 | 11/2/3/9 | 0.79 | 0.85 | 0.81 | 0.80 | 0.179 | 0.80 | 0.805 | 0.838 (0.56) | ✓ |
| ENNS 2021 | 11/3/2/9 | 0.85 | 0.79 | 0.81 | 0.80 | 0.150 | 0.80 | 0.853 | 0.820 (0.52) | ✓ |
| Pooled | 34/8/6/24 | 0.85 | 0.81 | 0.83 | 0.80 | 0.159 | 0.81 | 0.845 | 0.843 (0.56) | ✓ |

**Sensitivity**
- Dropping any one training transition in the 2021 fold leaves 2021 at 11/3/2/9 (Brier 0.148–0.161).
- ATTR is deterministic, so seeds don't apply.

**Paired bootstrap, pooled Brier (relative label)**
- ATTR − relative persistence: −0.035 [−0.066, −0.002]
- ATTR − REL-HB: −0.026 [−0.055, 0.004]
- ATTR − REL-LGBM: −0.033 [−0.069, 0.006]
- ATTR − FINAL scored on the relative label: −0.054 [−0.116, 0.008]

**Caveat on the strength of this evidence**
- The structural inputs were chosen with Holm across three transitions. Two of them, 2015→2018 and 2015→2019, are the 2018 and 2019 outcomes.
- On 2013→2015 alone (before every test round), the same five inputs rank at the top with nominal p < 0.05, but none survives Holm (`TRANS_T1_only_selection.csv`).
- So ATTR's 2018/2019 results are not fully out-of-sample with respect to input selection. 2021 is the only round whose outcomes played no part in the choice.

**Leakage checks**
- Structural inputs are as-of values at the forecast date.
- Training uses only transitions released by the forecast date: T1 for the 2018 and 2019 folds; T1–T3 for 2021.
- Test outcomes never enter a fit.
- The 2013 national value is an estimate (used in training anchors only).
- No synthetic data; no threshold chosen from outcomes.

## 7. Comparison and selection

| Candidate | Problem it addresses | Evidence | Weaknesses | Can be evaluated without leakage? | vs FINAL / FINAL-LG |
|---|---|---|---|---|---|
| FINAL-LG | Long-gap level extrapolation | Best absolute Brier; prevalence error −0.38 pp [−0.71, −0.01] | 2021 HIGH 1/4 | Yes | Ties FINAL on Brier; better level |
| HYB | Ranking within a round | Best 2021 AUC (0.905) | Worse in 2018/2019 and pooled; 2021 still 1/4 | Yes | **Worse** |
| **ATTR (relative risk)** | Which provinces sit above the national value; reversion to a structural level | All 8 targets in every round; stable to transition drops; beats persistence | Input selection partly used 2018/2019 outcomes; not LightGBM; answers "above national", not "≥ 50 %" | Yes (2021 clean) | Different target; on the relative label it beats FINAL scored there (ΔBrier −0.054) |
| Data-driven 4/4 detection | Masbate / Occidental Mindoro typhoon persistence | 2021 only, reversed historically | Would be fitted to 2021 | No | — |

**Selection**

| Use | Selected | Status |
|---|---|---|
| Absolute risk (≥ 50 %) | **FINAL** (official) with **FINAL-LG** as challenger | No method beats them, and the four 2021 provinces cannot be reliably separated with public data available at the 2021 forecast date |
| National-relative risk | **ATTR**, as the strongest new method and a candidate for prospective validation | It is the only formulation-plus-model in this project that is reliable in every round. It is a Bayesian statistical model, not LightGBM: LightGBM on the same task was worse (AUC 0.74 vs 0.85). Using it alongside FINAL needs owner and adviser approval, because Objective 2 and the owner rule name LightGBM |

## 8. Answers to the nine questions

| # | Question | Answer |
|---|---|---|
| 1 | New signal or method discovered? | **Yes.** Structural income and poverty predict reversion of relative food insecurity (confirmed on transitions not involving 2021). ATTR turns this into the first model reliable in every round, on the relative label |
| 2 | What explains missing the four? | Two HIGH provinces (Masbate, Occidental Mindoro) stayed high for a reason tied to recent typhoons whose historical association is reversed. The two poorest high-start provinces (Sarangani, North Cotabato) improved against the structural rule. Ranking, not the threshold, fails, even with the exact national level |
| 3 | All four without excessive false alarms? | **No.** Best ranking: 3/4 with 4 false alarms under an oracle level; 1/4 with an honest level. Persistence finds 4/4 with 12 false alarms |
| 4 | 2018 and 2019 preserved? | HYB: no (worse). ATTR on the relative label: yes, all 8 targets |
| 5 | Stable across seeds and transition drops? | ATTR: yes (11/3/2/9 in every drop). HYB: seeds yes, drops no |
| 6 | Outperforms FINAL and FINAL-LG? | On the absolute label: **no.** On the relative label: yes (point estimate; CI includes 0 against FINAL scored there) |
| 7 | Supported by genuine evidence? | Real survey transitions only. The input choice partly used 2018/2019 outcomes, and 2021 has been viewed many times, so it is **not independent validation** |
| 8 | Suitable for prospective validation? | ATTR (relative) and FINAL-LG (absolute): yes, by sealing forecasts now. HYB: no |
| 9 | What must be validated before production? | A sealed-forecast test on the next FNRI provincial round. Adviser approval for any relative-risk output and for a non-LightGBM component. For the four-province problem: compile DROMIC assistance and displacement plus 2020 SAP coverage by province under a locked protocol; test "typhoon × assistance" on the 2013→2015 transition (Yolanda) before 2021 |

## 9. Relevance to DA Region IV-A

- **Limited direct evidence.** Of the evaluation rows, only Laguna (2018, 26.2 %, LOW) is a CALABARZON province. Generalisation to the five provinces is assumed from national transitions, not demonstrated.
- **Expected classifications.** All five IV-A provinces are well below 50 % in their latest surveys. Their national-relative status depends on the structural indicators (IV-A has a high regional GRDP), so ATTR would mostly classify them below national. A sealed prospective forecast for IV-A would test this.
