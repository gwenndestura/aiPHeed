# E163 report: master model correction and validation

- **Criteria:** `CRITERIA.md` (93ff4d98), fixed before results.
- **Code:** `backend/app/e163/model.py` (`eval`, `live`).
- **Outputs:** `backend/data/e163/out/` (`results.json`, `oof.csv`, `group_audit.csv`, `live_2027-Q1.csv`, `sealed_2027-Q1.json`).
- **Seal:** `343d1f06`, registered in `docs/e154/SCORING_PROTOCOL.md`.

## Decision first
**No candidate passed all seven success criteria, so E158 remains the classification model.** Nothing is deployed.

The candidates did fix specific problems:
- **C1 (relative state space)** gives the best calibration and a better provincial order, and cuts the Batangas 2021 miss from −13.7 to −5.0. But it over-predicts LOW provinces by +7.2 points.
- **C2** gives the best Brier at every lead, but it raises false alarms and does not improve ordering.

**In 2027-Q1 every candidate puts Quezon highest. No candidate reaches the 0.80 needed to display it as rank 1.**

## 1. Audit of E158 / E160 / E161 (Phase 1)
| Question | Answer (evidence) |
|---|---|
| Which model classifies? | E158 (E151 + PSA regional consumption) |
| Which model orders provinces? | The same E158 score. No separate priority output existed before E162 |
| Is E158 defensible for ordering? | **No.** Within-region concordance 0.60 [0.44, 0.73]; it is the weakest arm (E159, E162) |
| Was RP+R's gain from its anchor? | **Yes.** RP alone scores 0.70. RP+R's residual was worse than shuffled inputs (E161) |
| Does the regional adjustment suppress differences? | The own-deviation shrinkage is mild (weight 0.75). **The main suppressor is the structural level** (a cross-region poverty/density mapping) overriding each province's observed position (E160 trace) |
| Are scores and P(HIGH) confused? | **Yes, in the old LGU formula** (P(HIGH) × vulnerability). Fixed in LGU-v2. Within the model, P(HIGH) is monotone in the score |
| Does the LGU formula suppress municipalities? | The old multiplier did (Quezon 0 of the top 20). LGU-v2 gives 6 of 20. With the owner's 0.6/0.4 weights, very poor sparse LGUs still rank below dense, moderately poor ones (San Francisco 30.2 % ranks 28th) |

The trace for all five provinces is in `data/e160/out/trace.json` (E160 REPORT §1).

## 2. Official evidence inventory (Phase 2)
The full table, with source, year, level, definition, direct or contributing, and usability, is in E162 REPORT §1.

| Province | HFIAS 2013 | HFIAS 2015 | Latest HFIAS | PSA poverty 2023 | PSA subsistence 2023 | LGUs > 20 % poverty (SAE 2021) |
|---|---|---|---|---|---|---|
| Quezon | **48.9** | **48.8** | 44.0 (2019) | **10.2** | 0.5 | **56 %** |
| Batangas | 40.8 | 43.5 | **39.9 (2021)** | 7.6 | 0.8 | 0 % |
| Rizal | 43.8 | 41.3 | 39.1 (2019) | 8.5 | **1.5** | 0 % |
| Cavite | 38.8 | 41.8 | 35.5 (2021) | **6.7 (lowest)** | 0.4 | 0 % |
| Laguna | 40.0 | 41.4 | 26.2 (2018) | 7.9 | 0.8 | 3 % |

- **Regional FIES 2023:** Region IV-A 19.1 %. This is a different instrument and never pooled with HFIAS.
- **Not available at provincial level in project data:** LFS employment, remittances, and NNC data after 2015.
- **Available at the issue date:** every row except the 2021 HFIAS, which counts as released for the 2027 issue.

## 3. Quezon calculation trace (Phase 3)
**E158:** 44.0 (2019) → 38.7 after the national decline → 34.9 after the structural level and shrunk deviation → **31.6** after a common residual intercept of −0.276.

| Hypothesis | Verdict |
|---|---|
| Shrinkage overpowers Quezon | No (+0.026 logit) |
| Stale anchor | Partly: E158 weights all rounds equally, regardless of age |
| Poverty mis-transformed | No: values match PSA. The cross-region mapping lowers Quezon after its real poverty fall |
| Missing data read as low | No: missing employment and remittance inputs are identical for all five |
| Rewarding complete data | Not testable: every test row has exactly 2 earlier rounds |
| Shared inputs make provinces similar | **Yes:** employment and remittance official inputs are national (§12) |
| P(HIGH) used as a multiplier | Only in the old LGU list (fixed) |

**Under C1, Quezon's relative state is −0.432, the highest of the five,** and Quezon is highest in all three candidates (§15).

## 4. Batangas underprediction (Phase 4)
2021 back-test, Lead 1. Batangas' history at issue: 2013 (40.8) and 2015 (43.5).

| Step | E158 | C1 |
|---|---|---|
| National level carried (2019) | 48.4 | 48.4 |
| Relative position | structural −0.557 + adjustment −0.052 | Kalman on own rel (−0.68, −0.51), region prior |
| Anchor | 33.8 | n/a |
| Residual | **−7.6 points** | none |
| Forecast | **26.2** (error −13.7) | **34.9** (error −5.0) |

- **Cause:** E158's residual removed 7.6 points, and its anchor gave the 2015 reading no more weight than 2013.
- **The remaining gap is a genuine change** that no input could show in advance: Batangas' position relative to the national level rose from −0.51 (2015) to −0.13 (2021).
- **Cavite:** E158 −6.2, C1 **−0.9**.
- **The fix does not hold everywhere:** C1 over-predicts Laguna 2018 by +15.2 points (E158 +9.3), and LOW provinces overall by +9.9.

## 5. Root cause of compression (Phase 5)
- **E158** is not compressed nationally (spread ratio 1.23) but **misorders within regions**.
- **C1 compresses** (spread ratio 0.55). Partial pooling to the region, plus q = 0 chosen in the live fit, averages all rounds.
- **In 2027-Q1, all methods put the five provinces within about 3–9 points**, well inside each other's 90 % ranges. The real differences are smaller than the uncertainty, so this compression is honest, not a defect.

## 6. Revised methodology and rationale
Three pre-specified candidates (CRITERIA §Candidates):
- **C1, RSS:** national level of the last released round + province relative position, estimated by a Kalman local-level filter.
  - Age variance `q` is chosen by predictive likelihood on released rounds.
  - The prior pools to the other provinces in the same region. This separates regional from provincial effects, as the prompt asks.
- **C2:** C1 + the E158 LightGBM residual (five groups and news).
- **C3:** C1 + a regularised ridge residual (alpha chosen by inner region cross-validation).

## 7–8. Candidate comparison and Lead 1 validation against E158 (72 rows, about 46 effective)
| Lead 1 | E158 | C1 | C2 | C3 |
|---|---|---|---|---|
| Accuracy | **73.6 %** | 69.4 % | 70.8 % | 69.4 % |
| Balanced accuracy | **0.760** | 0.757 | 0.749 | 0.729 |
| HIGH precision / recall | 0.583 / 0.84 | 0.533 / **0.96** | 0.550 / 0.88 | 0.538 / 0.84 |
| LOW recall | **0.681** | 0.553 | 0.617 | 0.617 |
| F1 / AUC | **0.689** / 0.860 | 0.686 / **0.930** | 0.677 / 0.903 | 0.656 / 0.862 |
| Brier | 0.1344 | 0.1518 | **0.1265** | 0.1512 |
| Brier − E158 [95 %] | n/a | +0.017 [−0.027, +0.063] | −0.008 [−0.037, +0.024] | +0.017 [−0.014, +0.050] |
| Calibration slope (C4) | 0.72 (fail) | **0.985 (pass)** | 0.80 (fail) | 0.64 (fail) |
| False-alarm rate / missed HIGH | **0.32** / 0.16 | 0.45 / **0.04** | 0.38 / 0.12 | 0.38 / 0.16 |
| MAE points / mean signed | 8.2 / **+2.9** | 8.6 / +7.2 | **7.6** / +3.7 | 9.3 / +5.1 |
| E156 C1–C6 | 011011 | **011111** | 011011 | 011011 |

| Gate | C1 | C2 | C3 |
|---|---|---|---|
| S1 Brier ≤ E158 | ✗ | ✓ | ✗ |
| S2 calibration | ✓ | ✓ | ✗ |
| S3 false alarms / misses | ✗ | ✗ | ✗ |
| S4 ordering | ✓ | ✗ | ✗ |
| S5 bias | ✗ | ✓ | ✗ |
| S6 every round | ✓ | ✓ | ✓ |
| S7 own evidence | ✓ | ✓ | ✓ |
| **Adopted** | no | no | no |

**Leads 2–4:**
- **C2 has a lower Brier than E158 at every lead:** L2 −0.021, L3 −0.014, L4 −0.029 [−0.057, +0.001]. **None is significant.**
- **C2 at Lead 4: 77.8 %** and passes C1. C3 at Lead 2: 79.2 % and passes C1.
- **These are single-lead peaks among 3 candidates × 4 leads, not pre-specified, so they are not claimed.** C4 still fails for both, so **no lead is reliable for any candidate.**

**Nested selection** (lowest Brier, held-out round): picks C2, E158, C2. Nested accuracy **70.8 %**.

**Leakage:** corrupting unreleased rounds changed forecasts by 0.0 for every candidate.

## 9. Provincial ranking validation (Lead 1, 40 pairs, 25 clusters)
| | E158 | C1 | C2 | C3 | C1 without own evidence |
|---|---|---|---|---|---|
| Concordance [95 %] | 0.600 [0.44, 0.73] | **0.675 [0.52, 0.83]** | 0.650 [0.49, …] | 0.650 [0.47, …] | 0.325 [0.19, …] |
| Per round 2018 / 2019 / 2021 | 0.58 / 0.57 / 0.64 | 0.58 / 0.64 / **0.79** | 0.58 / 0.57 / 0.79 | 0.58 / 0.57 / 0.79 | 0.33 / 0.43 / 0.21 |
| Position error | 0.467 | 0.373 | 0.413 | **0.307** | 0.58 |
| Spread ratio | 1.23 | 0.55 | 0.55 | 0.72 | 0.29 |

- **Own-evidence control (S7):** real − held-out concordance is +0.35 [+0.05, +0.62] for C1. **Caution:** removing a province's history is a *weaker* control than E162's swap test, which SS failed. C1's 0.675 is also no better than RP, FH or SS (0.70), which were seen earlier. **Ordering is improved over E158 but not established.**
- **CALABARZON, the two test pairs:**
  - Quezon above Rizal (2019): all arms right.
  - Batangas above Cavite (2021): C1–C3 right, E158 wrong.
  - **Quezon vs Batangas, Cavite or Laguna was never in a test round, so it cannot be validated.**

## 10. Overfitting and shuffled inputs
**C2 or C3 with all trigger inputs shuffled within survey-lead:**
- C2: real − shuffled +0.004 [−0.012, +0.023]. No signal.
- C3: **+0.030 [+0.008, +0.052]. Real inputs do worse than shuffled ones.**

The same pattern holds per group: dropping poverty or news hurts C3, but shuffling them across provinces *helps*. **The usable information is round-level (time), not province-level. The province-specific assignment of trigger values overfits.**

Group controls on C3 (Brier of C3 − Brier of the variant; negative means the group helps):

| Group | Columns | Dropped | Shuffled across provinces |
|---|---|---|---|
| Market | 10 | +0.007 [−0.010, +0.026] | +0.000 [−0.016, +0.019] |
| Climate | 14 | −0.002 [−0.010, +0.007] | +0.004 [−0.002, +0.011] |
| Employment | 9 | +0.006 [−0.003, +0.018] | +0.007 [+0.002, +0.011] |
| Remittances | 7 | +0.026 [−0.005, +0.053] | +0.002 [−0.002, +0.006] |
| Poverty & social vulnerability (incl. general news, SWS h2) | 26 | **−0.061 [−0.103, −0.019]** | +0.015 [+0.005, +0.026] |

## 11. Bias and calibration
Signed error in points (predicted − observed):

| Group | E158 | C1 | C2 | C3 |
|---|---|---|---|---|
| Overall | +2.9 | **+7.2 BIAS** | +3.7 BIAS | +5.1 BIAS |
| Luzon (35) | +5.5 BIAS | +8.5 BIAS | +5.5 BIAS | +7.2 BIAS |
| Visayas (15) | −0.6 | +5.1 BIAS | +1.8 | +1.6 |
| Mindanao (22) | +1.1 | +6.5 BIAS | +2.3 | +4.3 BIAS |
| Observed HIGH (25) | −1.6 | +2.1 | −0.3 | +1.7 |
| Observed LOW (47) | +5.3 BIAS | +9.9 BIAS | +5.9 BIAS | +6.9 BIAS |

CALABARZON rows:

| Row | E158 | C1 | C2 | C3 |
|---|---|---|---|---|
| Laguna 2018 | +9.3 | +15.2 | +10.8 | +12.0 |
| Quezon 2019 | +4.0 | +1.0 | −1.9 | +9.2 |
| Rizal 2019 | +3.6 | +2.8 | +0.3 | +3.6 |
| Batangas 2021 | −13.7 | **−5.0** | −11.6 | −9.2 |
| Cavite 2021 | −6.2 | **−0.9** | −6.7 | −9.0 |

- **C1's upward bias has a known cause:** the national level is carried flat while national HFIAS fell from 57.6 (2013) to 43.0 (2021). E158's residual intercept absorbs that drift.
- **Fairness by data completeness cannot be tested** (every row has 2 rounds). With 5 CALABARZON rows, **province-level fairness cannot be established.**

## 12. Five-group contribution (`group_audit.csv`)
| Group | Columns (news) | Granularity of official inputs | Empty in training |
|---|---|---|---|
| Market | 10 (4) | 6 provincial, 3 regional, 1 national | 0 |
| Climate | 14 (4) | 8 provincial, 4 regional, 2 national | 0 |
| **Employment** | 9 (4) | **All official inputs national**; `unemp_region` empty; `income_growth` regional and empty at the live issue | 1 |
| **Remittances** | 7 (4) | **All official inputs national**; `remit_q_yoy` empty | 1 |
| Poverty & social vulnerability | 26 (20) | 6 provincial, 15 regional, 5 national | 0 |

- **Why employment and remittances contribute nothing:** their official inputs have no provincial variation. They can only shift every province together, and the national level already does that.
- **Legitimate fixes need provincial data the project cannot fetch by script:** PSA provincial LFS estimates, and BSP or PSA regional remittance series. PSA and BSP return 403 or Cloudflare checks. National values were **not** copied into provinces.

## 13. NLP incremental value
- **Removing all news from C3 worsens it:** −0.039 [−0.070, −0.003].
- **Shuffling news across provinces improves it:** +0.026 [+0.013, +0.041].
- **So news carries round-level (timing) information but no demonstrated province-level information,** consistent with E151, E155 and E157. The news collectors are paused, not tuned.

## 14–15. LGU method and old vs new rankings
- **LGU method:** LGU-v2 with the owner's 0.6/0.4 weights. Tier by class, then vulnerability, with a province-blind poverty tie-break and no P(HIGH) multiplier (E162 addendum).
- **Top 20:** the old list had Rizal 11, Cavite 9, Quezon 0. The new list has Cavite 11, Quezon 6, Laguna 1, Rizal 1, Batangas 1. Every change is explained in E160 §7.
- **No LGU-level climate or agricultural exposure data exist in the project, and none was invented.**

**2027-Q1 provinces, sealed 343d1f06:**

| Province | E158 score | C1 score (90 %) | C2 | C3 | P(highest) C1 / C2 / C3 / E158 |
|---|---|---|---|---|---|
| Quezon | 31.6 | **32.8** (18.7–50.9) | **31.2** | **31.9** | **0.41 / 0.50 / 0.65** / 0.19 |
| Batangas | 26.6 | 31.7 | 26.1 | 27.0 | 0.23 / 0.02 / 0.03 / 0.03 |
| Rizal | **35.5** | 31.2 | 30.7 | 30.4 | 0.17 / 0.41 / 0.30 / **0.47** |
| Cavite | 32.1 | 30.9 | 26.4 | 26.0 | 0.14 / 0.02 / 0.01 / 0.20 |
| Laguna | 29.8 | 29.6 | 27.5 | 25.4 | 0.05 / 0.05 / 0.01 / 0.11 |

- **Every candidate ranks Quezon highest.** C1's order is Quezon > Batangas > Rizal > Cavite > Laguna, which matches the order of the official evidence.
- All are LOW.
- **No candidate reaches P(highest) ≥ 0.80, and none was adopted, so rank 1 is not displayed.**

## 16. Release gate
| Component | Decision |
|---|---|
| Classification model | **E158 retained.** No candidate met S1–S7 |
| Provincial order | **Not validated for display.** Show the five provinces unranked, plus the Quezon evidence note (E162 §10) |
| Candidate status | C1 is the most defensible *priority* method on calibration, ordering and the Batangas/Quezon fixes, but it is biased upward in level. C2 is the most accurate on Brier but not significantly better, with more false alarms. **Both are sealed (343d1f06) for prospective scoring. Neither is deployed.** |
| Five groups | Kept, as the objective requires. **Contribution not demonstrated**: employment and remittances lack provincial data |
| LGU list | LGU-v2, final owner weights |
| Production, dashboard, API | **Unchanged** |

## Final acceptance test
| # | Question | Answer |
|---|---|---|
| 1 | Why was Quezon underestimated? | E158's cross-region structural level and its equal weighting of rounds by age. Not shrinkage, not P(HIGH) |
| 2 | Why was Batangas underestimated? | The residual's −7.6 points and the age-blind averaging. The remaining gap is a real 2015→2021 change that no input could foresee |
| 3 | Does the revised method preserve real differences? | C1 preserves **order** better (0.675 vs 0.60) but compresses spread (0.55). Differences in 2027 are within uncertainty |
| 4 | Does Quezon rank highest when the evidence supports it? | **Yes, in every candidate.** But P(highest) is 0.41–0.65, below the 0.80 display rule |
| 5 | Does Batangas get a defensible score? | C1 puts it 2nd (31.7), consistent with its 2021 reading. Its 2021 back-test error fell from −13.7 to −5.0 |
| 6 | Does the ranking generalise? | Partly: ≥ 0.5 in every round, lower bound 0.52. Quezon vs Batangas was never testable |
| 7 | Better without more overfitting or bias? | **No for C1** (+7.2 bias, more false alarms). **Mixed for C2** (better Brier, more false alarms) |
| 8 | Do the five groups add information? | **No, not at province level.** Employment and remittances are national-only. News and poverty carry round-level signal only |
| 9 | Are LGU priorities independent of P(HIGH)? | **Yes** (LGU-v2) |
| 10 | Is the revised model better than E158? | **Not as a whole.** It is better on specific objectives (calibration and order in C1; Brier in C2) but fails the pre-registered combined gate. **E158 stays; C1 and C2 are sealed for prospective testing.** |
