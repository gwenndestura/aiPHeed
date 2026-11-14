# E189 report: audit of E184 and the last untested improvement (model family)

Local only. Nothing in this report has been committed or pushed. Protocol: `docs/e189/PROTOCOL.md`, whose SHA-256 was
logged before the run. Outputs are in `backend/data/e189/audit/` and `backend/data/e189/out/`.

## 1. Executive summary
- **E184 holds up.** It reproduces exactly, shows no leakage, and its synthetic-data gain over E168 is real in direction.
- **Nothing reached 80 % at all three leads.** That includes the inner-selected model family (E189), ridge, random
  forest, and every variant from E179–E188.
- **Ridge came closest.** It reached 79.2 / 80.6 / 79.2 %, but its probabilities got worse at Lead 1 (Brier +0.012),
  and none of its differences from E184 is statistically supported (Holm-adjusted McNemar p = 1.0).
- **Where the ceiling comes from.** 10–14 of E184's 15–17 errors per lead are made by every model variant tried. They
  are real, large province changes that no input signalled, not label noise.
- **On this data, 80 % at all three leads is at or beyond what the evidence can support.** Lead 3 would need
  essentially every fixable row fixed.
- **Recommendation: keep E184.**

## 2. E184 baseline reproduction
- **Reproduction.** E184 was re-run inside E188 (Leads 1–6) and inside E189 (Leads 1–3). Both re-runs match the stored
  probabilities exactly (maximum |Δp| = 0).
- **Recomputed accuracy.** From scratch: 55, 57 and 56 correct out of 72 = 76.4 / 79.2 / 77.8 %, as reported.
  - False alarms: 13 / 11 / 12.
  - Missed HIGH: 4 / 4 / 4.
  - E168's false alarms were 15 / 13 / 14, so the reported decrease is correct.

## 3. Root causes of the remaining errors (`data/e189/audit/audit.json`)
| | Lead 1 | Lead 2 | Lead 3 |
|---|---|---|---|
| E184 errors | 17 | 15 | 16 |
| … wrong in every variant tried (E168, E180, E182, E184–E186, E188a/b) | 10 | 12 | 14 |
| … on labels the survey itself leaves uncertain (q between 0.2 and 0.8) | 3 | 3 | 2 |
| … with p within 0.1 of the 0.5 cut | 11 | 8 | 9 |
| Accuracy if every non-shared error were fixed | 86.1 % | 83.3 % | 80.6 % |
| Accuracy of a perfect forecaster, given survey sampling error | 95.1 % | 95.1 % | 95.1 % |

- **Large real changes no input predicts.** Twelve province-rounds are wrong at all three leads, and most have certain
  labels (q ≈ 0 or 1). Examples: Mountain Province, Sorsogon and Oriental Mindoro in 2018; Pangasinan, Quirino and
  Southern Leyte in 2019; Masbate, North Cotabato and Occidental Mindoro in 2021.
  - In each case the province moved far from its last survey. The national or regional inputs (unemployment,
    remittances, prices) do not differ by province, so they could not signal the move.
- **HIGH is over-called.**
  - E184 has 11–13 false alarms against 4 missed HIGH provinces.
  - On the outer rows, calibration intercept ≈ −0.87 and slope ≈ 1.7–1.8: at p = 0.5 the observed HIGH rate is about
    30 %.
  - Training folds do not show this. E187's training-only cut-off came out between 0.40 and 0.55 and did not help.
  - So it is a shift between periods (food insecurity fell in the 2018–2021 rounds), not something the training data
    can reveal.
- **Weakest window: ENNS 2018 (68–73 %).** Its training data is a single earlier round (FNRI 2015, 78 provinces × 2
  rows).
- **Class balance.** 25 HIGH out of 72 (35 %). By round, 8 / 22 in 2018, 13 / 25 in 2019 and 4 / 25 in 2021.
- **CALABARZON.** It contributes 5 of the 72 rows per lead, so province-level conclusions for CALABARZON are not
  possible.
- **Power.** One province = 1.39 points. An exact McNemar p < 0.05 needs at least 6 net fixes with zero new errors
  (about +8.3 points). A move from 76 % to 80 % is +3 provinces and cannot be shown to be real on 72 rows.

## 4. Data quality and leakage audit
- **Origins.** Each outer job trains only on outcomes released by its issue quarter (`M.released`). These are three
  chronological origins: ENNS 2018, 2019 and 2021.
- **Corruption control.** Corrupting the unreleased rounds changes E184's forecasts by 0.0.
- **Synthetic rows.** They are generated inside each inner fold and the final fit from that job's training rows only.
  Code asserts check that the outer rows contain no synthetic rows. OOF scoring and calibration use real rows only.
- **Shuffled-trigger control.** E184 − shuffled Brier = +0.0013 [−0.012, +0.018]. The triggers' own contribution is not
  distinguishable from chance, so most of the skill comes from the survey anchor and the change model's structure.
- **Not an untouched holdout.** The 72 rows have been used for model comparison since E151, so they are not an
  untouched holdout. This favours whatever wins on them, and it means E184 itself is somewhat optimistically measured.

## 5. Synthetic-data quality (E178 fidelity checks, jitter generator)
- All outer training sets pass:
  - median KS ≈ 0.09 (≤ 0.15);
  - maximum standardized Wasserstein ≈ 0.28 (≤ 0.5);
  - correlation drift ≈ 0.06 (≤ 0.10);
  - TSTR/TRTR ≈ 1.02 (≤ 1.25);
  - 0 exact copies;
  - 91 % sign agreement.
- **Ratio, generator and settings.** 129 settings (E179), the best-of-variants search (E181), copula (E185),
  20 draws and survey-noise only (E188) were all within ±1–3 provinces of E184.
- **Conclusion.** The synthetic rows are realistic and help modestly. They cannot supply the province-specific signal
  that is missing.

## 6. Feature engineering findings
- **Already in the features:**
  - historical food-insecurity anchors (three kinds);
  - lags (Leads 1–8 snapshots are already in training);
  - rolling "since last survey" statistics;
  - trends;
  - poverty;
  - climate, agriculture, prices and news.
- **Provincial local data (E186: farmgate, rice, rainfall)** was never selected in inner CV.
- **What is genuinely national.** Unemployment and remittances have one value per quarter nationwide. Provincial LFS
  exists only for CALABARZON 2021–2025.
- **Provincial FIES income (2018 / 2021 / 2023).** It would leak for the 2018 and 2019 origins, so it was not used.

## 7–8. Candidate experiment E189 (model family) and Lead 1–3 comparison
In inner CV, random forest won for the ENNS2021 jobs and LightGBM won for the ENNS2018/2019 jobs. Ridge never won.

| Model | L1 | L2 | L3 | Balanced accuracy (L1/L2/L3) | Brier (L1/L2/L3) | False alarms | Missed |
|---|---|---|---|---|---|---|---|
| Persistence | 62.5 | 62.5 | 62.5 | .703/.703/.703 | .213/.213/.213 | 26/26/26 | 1/1/1 |
| E168 | 75.0 | 77.8 | 75.0 | .780/.802/.771 | .1230/.1221/.1352 | 15/13/14 | 3/3/4 |
| **E184** | **76.4** | **79.2** | **77.8** | .782/.803/.792 | .1211/.1185/.1258 | 13/11/12 | 4/4/4 |
| E189 (inner-selected family) | 76.4 | 77.8 | 77.8 | .782/.792/.792 | .1244/.1223/.1238 | 13/12/12 | 4/4/4 |
| E189_ridge | 79.2 | 80.6 | 79.2 | .794/.814/.803 | .1335/.1203/.1277 | 10/10/11 | 5/4/4 |
| E189_rf | 79.2 | 76.4 | 76.4 | .803/.782/.782 | .1186/.1146/.1209 | 11/13/13 | 4/4/4 |

- **Exploratory, after seeing the results, not eligible.** An equal-weight average of E184, ridge and RF gives
  83.3 / 76.4 / 76.4 %. The same rows swing by ±3–5 provinces with small changes in method. That is exactly why no
  80 % result on these rows can be trusted.

## 9. Statistical significance (paired, against E184)
| Arm | McNemar p (L1/L2/L3), Holm-adjusted | Brier − E184 [95 % CI], L1 / L2 / L3 | Supported? |
|---|---|---|---|
| E189 | 1.0 / 1.0 / 1.0 | +.0033 [−.0002, +.0083] / +.0037 [−.0008, +.0093] / −.0020 [−.0085, +.0046] | no |
| E189_ridge | 1.0 / 1.0 / 1.0 (8 vs 6, 5 vs 4, 5 vs 4 discordant) | +.0124 [−.011, +.033] / +.0018 [−.016, +.019] / +.0019 [−.026, +.024] | no |
| E189_rf | 1.0 / 1.0 / 1.0 | −.0025 [−.011, +.005] / −.0040 [−.013, +.005] / −.0049 [−.013, +.004] | no |

- **Classification.** Every difference is observed but not statistically supported.
- **E184 against E168.** Observed gains at all leads. Brier is supported at Leads 3–6 only, for example Lead 3:
  −0.0094 [−0.0165, −0.0029].

## 10. Reliability and calibration
- **E184.** AUC 0.89 at every lead, PR-AUC 0.83–0.85, recall 0.84, specificity 0.72–0.77.
- **Calibration on the outer rows** shows the over-calling of HIGH described in section 3.
- **E189_rf** has the best Brier at every lead, but the gain is not significant and its accuracy is lower at Leads 2–3.

## 11. Province-level performance
- **Too few rows per province.** Each province appears once per lead, so per-province accuracy cannot be estimated.
  The 12 province-rounds wrong at every lead are listed in `audit.json`.
- **By island:** see `audit.json`.
- **By round:** 2018 is the weakest; 2021 is the strongest (80–88 %).

## 12. Overfitting and generalization
- **Narrow spread.** Across about 40 experiments on the same 72 rows, the best single-lead results range from 79 % to
  83 %, and no method wins at all leads. That pattern is what selection noise produces.
- **The only untouched test** is the sealed ENNS 2022 forecasts (E180, E182, E184–E186), which need labels.

## 13. Final recommendation
**Keep E184.**

| Question | Answer |
|---|---|
| 80 % at all three leads? | No (best candidate: ridge 79.2 / 80.6 / 79.2) |
| Improved over E184? | Observed at some leads; not consistently |
| Reliability requirements? | E189 fails criterion 1; ridge fails criteria 1 and 4; RF fails criteria 1 and 2 |
| Statistically supported? | No |
| Suitable to replace E184 in aiPHeed? | No |

## 14. Remaining limitations
- 72 outer rows per lead, reused across many experiments.
- Period shift (falling food insecurity) that the training data cannot reveal.
- Several inputs are national, not provincial.
- CALABARZON has only 5 rows per lead.

## 15. Additional real data needed
1. **ENNS 2022 and NNS 2023 province estimates** (moderate+severe % and SE) from DOST-FNRI. This would add a new round
   for training and an untouched test, and would allow the 2022 seals to be checked.
2. **Province-level labour and remittance series** (PSA LFS provincial tables, BSP regional remittances) going back to
   2015.
3. **Province-level price series before 2018** (PSA retail and farmgate), to strengthen the 2018 origin.
