# aiPHeed final model report (E165)

- **Protocol and gates:** `docs/e165/PROTOCOL.md` (30f4b25c), fixed before results and evaluated once.
- **Code:** `backend/app/e165/final.py`.
- **Outputs:** `backend/data/e165/out/` (`all_rows.csv`: 24 runs × 72 rows; `results.json`).
- **Registry:** `docs/EXPERIMENT_REGISTRY.md`.

## 1. Executive summary
- **AUTO-FINAL is not accepted.** It passes F1, F3, F4 and F5, and fails F2/F8 (feature contribution), F6 (probability calibration), F7 (generalisation in 2021) and F10 (reliable Lead 1).
- **E158 remains the production thesis model. Nothing is deployed, frozen or sealed in E165.**
- **E164 AUTO's 79.2 % does not survive the audit.**
  - It used two consumption inputs that were selected in E157 by ranking sources on the same 72 test rows.
  - With them removed, the identical procedure scores **73.6 %, the same as E158.**
  - Its significant "trigger groups beat shuffled inputs" result also disappears (−0.006 [−0.020, +0.008]).
  - **E164 is therefore withdrawn as release candidate.** Its seal cbfb61dc stays in the register as a recorded forecast only.
- **The honest final figures for the thesis:**
  - Lead 1 classification accuracy is about 73.6 % (E158; AUTO-FINAL equal).
  - The best probability score is Brier 0.121 (AUTO-FINAL), not significantly better than E158's 0.134.
  - **No forecast lead passes the reliability criteria**, so the maximum reliable lead is 0.

## 2. E158 vs E164 AUTO vs AUTO-FINAL (Lead 1, 72 rows, about 46 effective)
| | Persistence | **E158** | E164 AUTO (uses test-selected features) | **AUTO-FINAL** |
|---|---|---|---|---|
| Accuracy | 62.5 % | **73.6 %** | 79.2 % | **73.6 %** |
| Balanced accuracy | 0.703 | 0.760 | 0.812 | 0.770 |
| HIGH precision / recall | 0.48 / 0.96 | 0.58 / 0.84 | 0.65 / 0.88 | 0.58 / 0.88 |
| LOW precision / recall | 0.96 / 0.45 | 0.89 / 0.68 | 0.92 / 0.75 | 0.91 / 0.66 |
| Macro F1 | 0.624 | 0.730 | 0.785 | 0.732 |
| ROC-AUC / PR-AUC | 0.83 / 0.71 | 0.86 / 0.81 | 0.90 / 0.86 | 0.89 / 0.85 |
| Brier | 0.213 | 0.1344 | 0.1223 | **0.1213** |
| Confusion (TP / FP / FN / TN) | 24 / 26 / 1 / 21 | 21 / 15 / 4 / 32 | 22 / 12 / 3 / 35 | 22 / 16 / 3 / 31 |
| False alarms / missed HIGH | 0.55 / 0.04 | 0.32 / 0.16 | 0.26 / 0.12 | 0.34 / 0.12 |
| Within-region concordance | 0.70 | 0.60 | 0.725 | 0.70 [0.56, 0.84] |

**Paired comparison, AUTO-FINAL vs E158:**
- Brier −0.013 [−0.036, +0.008], not significant.
- Exact McNemar: 5 rows right only for AUTO-FINAL, 5 right only for E158, p = 1.00.
- **No classification difference.**

**AUTO-FINAL's selections** (training rows only):

| Rounds | Selection |
|---|---|
| 2018, 2019 | OH anchor + LightGBM + all inputs, identity calibration |
| 2021 | OH + RandomForest + all inputs, identity calibration |

Platt and linear calibration were offered and lost inside the inner validation.

## 3. Root causes of the remaining failures
1. **Upward bias on provinces that are truly LOW, mainly in Luzon.** LOW-province error is +4.7 [2.0, 7.3]; Luzon +4.4 [1.1, 8.0]. Those rows sit near the 50 line, so the **0.4–0.6 probability band holds 22 rows, of which only 23 % were HIGH.** This is the false-alarm zone. Its source is the drift of the national level between survey rounds, which no training-only calibration can see: at the 2018 and 2019 issues, training holds a single round (2015).
2. **Probability calibration is now under-confident:**
   - logistic slope 1.73 [1.14, 2.94], where 1 is ideal;
   - prevalence-level slope 0.74 (C4 fails).

   Both point to the same thing: the error model's sd is inflated by between-round drift, so probabilities are pulled toward 0.5. Fixing this needs more training rounds, not a different calibrator.
3. **There is too little provincial signal in the inputs.**
   - The employment and remittance official inputs are national-only.
   - News shows no out-of-sample value.
   - With the test-selected consumption inputs removed, **no group passes its shuffled control** (§7).
4. **Batangas 2021 (−11.9) and Laguna 2018 (+6.8)** are real changes between rounds that no input recorded in advance.
5. **The sample is small:** 72 rows, about 46 effective, 3 test rounds, 25 ranking clusters. A 5-point accuracy difference is 3–4 rows.

## 4. Final model and justification
**E158 is retained**:
- it was chosen before E159;
- AUTO-FINAL is not better on classification (McNemar p = 1.0);
- AUTO-FINAL fails four gates.

AUTO-FINAL's probabilities are slightly better (Brier −0.013, not significant). This is documented but not adopted.

## 5. Calibration and classification (Lead 1)
Reliability of AUTO-FINAL:

| Probability band | Rows | Mean predicted | Observed HIGH rate |
|---|---|---|---|
| 0–0.2 | 18 | 0.06 | 0.00 |
| 0.2–0.4 | 8 | 0.29 | 0.25 |
| **0.4–0.6** | **22** | **0.51** | **0.23** |
| 0.6–0.8 | 15 | 0.71 | 0.60 |
| 0.8–1.0 | 9 | 0.92 | 1.00 |

- **Logistic calibration slope:**

| Model | Slope [95 % CI] |
|---|---|
| E158 | 1.53 [0.95, 2.78] |
| E164 AUTO | 1.43 [0.87, 2.98] |
| AUTO-FINAL | 1.73 [1.14, 2.94], **F6 fails** |

- **Training-only threshold sensitivity (not adopted):** a Youden threshold chosen on inner out-of-fold probabilities (0.65, 0.65, 0.31) would give 83.3 % accuracy. It was declared in advance as a sensitivity only. Adopting it now would be choosing after seeing the result. **It may be pre-registered for the next prospective round.**
- **HIGH/LOW bias:**
  - No model leans toward missed HIGH cases: HIGH recall is 0.84–0.88 and the HIGH-province error is −1.2 to −1.6.
  - All lean toward false alarms on true LOW provinces.

## 6. Bias and overfitting audit
| Check | Result |
|---|---|
| Leakage (unreleased-round corruption) | **0.0 change, pass** |
| Test-influenced features | **Found and removed:** `income_growth`, `income_rel` (E157 ranking on test rows) |
| Menu optimism | **Large.** With only E158's anchor (S-H), Brier is 0.163, accuracy 63.9 %. The OH and RSS anchors, designed after seeing E159–E163, carry the whole gain over E158 (−0.042 [−0.060, −0.024]). That gain is real out of sample, but it was found by looking at these rows |
| Shuffled provinces (all groups) | −0.006 [−0.020, +0.008]: **no demonstrated advantage over shuffled inputs** |
| Per round, accuracy and Brier | 2018: 63.6 % / 0.147 (E158 63.6 % / 0.150). 2019: 76.0 % / 0.138 (68.0 % / 0.172). 2021: **80.0 %** / 0.082 (**88.0 %** / 0.083). **F7 fails: 2021 is 8 points below** |

Signed error in points (95 % CI):

| Group | E158 | AUTO-FINAL |
|---|---|---|
| Overall | +2.9 [0.6, 5.1] | +2.6 [0.5, 4.9] |
| Luzon | +5.5 | +4.4 |
| Visayas | −0.6 | +0.5 |
| Mindanao | +1.1 | +1.3 |
| Observed HIGH | −1.6 | −1.2 |
| Observed LOW | +5.3 | +4.7 |

**Fairness is not established** for any single province (n = 1 per round), or by data completeness (every row has 2 earlier rounds).

## 7. Five-group contribution (AUTO-FINAL, Lead 1)
AUTO-FINAL − shuffled-variant Brier; a negative value means the real inputs help:

| Group | Real − shuffled Brier [95 %] | Accuracy with the group shuffled | Granularity of official inputs |
|---|---|---|---|
| Market | −0.005 [−0.011, +0.001] | 73.6 % | Mostly provincial CPI |
| Climate | −0.005 [−0.019, +0.006] | 77.8 % | Provincial and regional |
| Employment | −0.001 [−0.003, +0.000] | 72.2 % | **National only** |
| Remittances | +0.000 [−0.000, +0.001] | 73.6 % | **National only** |
| Poverty & social vulnerability | −0.003 [−0.022, +0.014] | 75.0 % | Provincial and regional |
| **All groups** | −0.006 [−0.020, +0.008] | 77.8 % | |
| No news | −0.007 [−0.017, +0.001] | 72.2 % | |
| No national-only columns | −0.002 [−0.005, +0.000] | 73.6 % | |

- **No group, and not the five together, shows a demonstrated incremental contribution.**
- **Why news had 49 % importance with no value:** tree models split on the 36 high-variance news columns because they vary by province and quarter. Those splits do not generalise, so the importance reflects fitting, not information.
- **All five groups remain on the dashboard as required monitoring indicators, labelled "monitoring; predictive contribution not demonstrated".**

## 8. Provincial validation
- **Classification:** all five CALABARZON test rows were LOW, and every model got them right. **CALABARZON has never been observed HIGH, so detection there is untested.**

| Back-test row | E158 | AUTO-FINAL |
|---|---|---|
| Laguna 2018 | +9.3 | +6.8 |
| Quezon 2019 | +4.0 | **+1.4** |
| Rizal 2019 | +3.6 | −2.9 |
| Batangas 2021 | −13.7 | −11.9 |
| Cavite 2021 | −6.2 | −8.5 |

- **Ordering:** AUTO-FINAL's within-region concordance is 0.70 [0.56, 0.84] (E158 0.60). The F9 interval part passes, but no 2027-Q1 forecast was made with AUTO-FINAL. Under E158 the order is not validated. **Provinces are shown unranked.**
- **Batangas:** the residual gap is the real 2015→2021 rise in its position relative to the national level. No input could foresee it.
- **Laguna 2018:** the reverse, a real fall from 41 % to 26 %.

## 9. Lead 1 and Lead 2
| | Lead 1 | Lead 2 |
|---|---|---|
| AUTO-FINAL accuracy / balanced | 73.6 % / 0.770 | 76.4 % / 0.791 |
| Brier (E158) | 0.121 (0.134) | 0.127 (0.137) |
| Brier − E158 [95 %] | −0.013 [−0.036, +0.008] | −0.010 [−0.035, +0.013] |
| McNemar (only AUTO-FINAL right / only E158 right) | 5 / 5, p = 1.00 | 5 / 3, p = 0.73 |
| vs persistence (accuracy) | +11.1 points | +13.9 points |
| E156 C1–C6 | **C1, C4 fail** | **C1, C4 fail** |
| Reliable | **No** | **No** |

**Neither lead is reliable**:
- the accuracy margin over the majority rule is not established at about 46 effective rows;
- the calibration slope excludes 1.

**The thesis's one-quarter-ahead requirement is implemented and evaluated but not validated as reliable.**

## 10. Confidence intervals and statistical comparisons
All intervals are region-cluster bootstraps (2,000 draws). Region clusters contain every round of their provinces, which accounts for repeated provinces over time.

| Comparison | Point estimate | 95 % CI | Significant? |
|---|---|---|---|
| AUTO-FINAL − E158 Brier, Lead 1 | −0.013 | [−0.036, +0.008] | No |
| AUTO-FINAL − E158 Brier, Lead 2 | −0.010 | [−0.035, +0.013] | No |
| E158 − persistence Brier | −0.078 | below 0 (E158 report) | **Yes** |
| AUTO-FINAL − H-anchor-only Brier | −0.042 | [−0.060, −0.024] | **Yes**, but menu-optimistic |
| McNemar, Lead 1 | 5 vs 5 | p = 1.00 | No |

**Practical significance:** a Brier gain of 0.013 is about 10 % of E158's score. It is noticeable but unproven.

**Development vs prospective:** every number here is historical development evidence on rounds read repeatedly. **The only independent tests are the sealed 2027 forecasts** (f69e7a02 for E158; 343d1f06; cbfb61dc). They are scorable only if FNRI publishes provincial HFIAS for 2027.

## 11. Acceptance gates (fixed in advance)
| Gate | Requirement | Result |
|---|---|---|
| F1 | No leakage | ✅ 0.0 |
| F2 | No advantage from shuffled provinces | ❌ −0.006 [−0.020, +0.008] |
| F3 | Non-inferior to E158 | ✅ 0.1213 ≤ 0.1344; upper bound +0.008 < +0.02 |
| F4 | HIGH and LOW performance | ✅ 0.88 / 0.66, balanced 0.770 |
| F5 | No material bias | ✅ overall +2.6, islands within ±5 |
| F6 | Probability calibration | ❌ slope 1.73 [1.14, 2.94] |
| F7 | Generalises across periods | ❌ 2021: 80.0 % vs 88.0 % |
| F8 | Features contribute | ❌ same as F2 |
| F9 | Ordering, if displayed | Interval passes; **not displayed** |
| F10 | Reliable Lead 1 | ❌ C1 and C4 fail |

**Status: NOT ACCEPTED.**

## 12. Production recommendation
| Item | Decision |
|---|---|
| Classification model | **E158** (unchanged; seal f69e7a02) |
| Lead claims | "One-quarter-ahead forecast produced and evaluated: 73.6 % retrospective, better than persistence and all four baselines; **not validated as reliable**." Maximum reliable lead 0; **do not hardcode a lead on the dashboard** |
| Provincial display | All LOW, with 90 % ranges. **No ranks.** Quezon evidence note (E162) |
| Five groups | Displayed as monitoring indicators, with predictive contribution "not demonstrated" |
| LGU list | LGU-v2, owner weights 0.6/0.4 |
| E164 AUTO | **Withdrawn as release candidate** (test-selected features) |
| AUTO-FINAL | Not accepted; not frozen or sealed |
| Production API and dashboard | **Unchanged.** Wiring E158 into the API needs the owner's go-ahead |

## 13. Remaining limitations and data requirements
1. **New provincial HFIAS rounds** (FNRI). This is the binding constraint for training rounds, calibration across rounds, and any untouched test.
2. **Provincial employment** (PSA LFS provincial estimates) and **remittances** (BSP regional, PSA SOF). These need a manual download, because PSA and BSP block scripts.
3. **The subsistence-incidence definition break** (families → population, 2018+ methodology), to be harmonised at source.
4. **Province-level news with event dates and geographic confidence.** The current news features show no out-of-sample value.
5. **A pre-registered training-only threshold rule** (Youden) for the next prospective round.

## Configuration, code, tests, commit
| Item | Value |
|---|---|
| Final procedure tested | AUTO-FINAL: anchors {H, RP, OH, RSS} × learners {NONE, RIDGE, ENET, RF, LGBM} × {GOV, FULL = `Pv.GNT_COLS`} × calibration {id, lin, platt}; inner region GroupKFold(5); inner Brier; P(HIGH) ≥ 0.5 |
| Code | `backend/app/e165/final.py` |
| Runs | 24 modes × 3 rounds at Lead 1, plus Lead 2: 1,728 forecast rows, analysed once. A crash in the summary step (duplicate `cfg` column) was fixed and only the analysis was rerun from the saved rows |
| Commit | in git log after this report |
| Deployment | **None** |
