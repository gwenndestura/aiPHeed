# E162 report: Quezon evidence, fair provincial ranking, bias control

- **Criteria:** `CRITERIA.md`, committed in dad19342 before results.
- **Code:** `backend/app/e162/rank.py`.
- **Output:** `backend/data/e162/out/`.
- **Owner decision recorded:** E158 is restored as the province-ordering baseline, and the E160 adoption of RP+R is revoked.

## 1. Evidence inventory, five provinces
| # | Source | Period | Level | Indicator | Direct FI? | Usable in model? | Quezon | Batangas | Cavite | Laguna | Rizal |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | FNRI NNS (Heat Map) | 2013 | Province | HFIAS moderate + severe % | **Direct** | Yes (outcome/anchor) | **48.9** ±3.7 | 40.8 | 38.8 | 40.0 | 43.8 |
| 2 | FNRI survey (Heat Map) | 2015 | Province | HFIAS moderate + severe % | **Direct** | Yes | **48.8** ±3.4 | 43.5 | 41.8 | 41.4 | 41.3 |
| 3 | FNRI ENNS, rolling | 2018 / 2019 / 2021 | Province, **one round each** | HFIAS moderate + severe % | **Direct** | Yes | 44.0 (2019) | 39.9 (2021) | 35.5 (2021) | 26.2 (2018) | 39.1 (2019) |
| 4 | FNRI ENNS 2021, severe only | 2021 | Province | HFIAS severe % | Direct | Yes (part of #3) | n/a | 16.7 | 19.0 | n/a | n/a |
| 5 | PSA official poverty, 2023 | 2023 | Province | Population poverty % | Contributing | Yes, in the model | **10.2** | 7.6 | 6.7 | 7.9 | 8.5 |
| 6 | PSA subsistence incidence, 2023 | 2023 | Province | % below the food threshold | Contributing | Yes, in the model | 0.5 | 0.8 | 0.4 | 0.8 | **1.5** |
| 7 | PSA poverty, latest as of 2021-Q2 | 2018 round | Province | Poverty % | Contributing | Yes, in the model | **13.5** | 11.4 | 5.3 | 3.9 | 4.5 |
| 8 | PSA small-area estimates, 2021 | 2021 | Municipality (142) | LGU poverty %: median; share of LGUs > 20 % | Contributing | Yes, LGU ranking | **20.3; 56 %** | 8.4; 0 % | 11.3; 0 % | 7.1; 3 % | 7.0; 0 % |
| 9 | PSA SDG 2.1.2 (FIES) | 2023 | **Region only** | FIES moderate + severe % | Direct, **different instrument** | Context only, never pooled | Region IV-A 19.1 %, lowest of 17 regions | | | | |
| 10 | NNC Region IV-A profile | ≈2015 (FNRI) | Province | Severe food insecurity | Direct | Context (same data as #2) | Highest in region | | | | |
| 11 | PSA Labor Force Survey | quarterly | **Region only** in project data | Unemployment | Contributing | Region only | n/a | | | | |
| 12 | DA / PSA palay and agricultural production | quarterly | Province / region | Supply | Contributing | In the market group | (E117: only palay helps, at Lead 1) | | | | |

### What the evidence says
- **Quezon's vulnerability is well documented.** It has the highest HFIAS reading in both rounds that measured all five provinces together (2013 and 2015). It has the highest provincial poverty (2023) and by far the poorest municipalities (56 % of its LGUs are above 20 %).
- **That Quezon is the highest now is not established.**
  - The only same-year, same-instrument comparisons are from 2013 and 2015. Quezon's lead was about 5 points each time, about 1.0 to 1.2 standard errors, so each round alone is not significant, but both point the same way.
  - Since 2015 no round has measured the five provinces together.
  - Relative to its round's national level, Batangas in 2021 (−0.13 logit) sits slightly *above* Quezon in 2019 (−0.18).
  - On PSA 2023, Quezon's poverty lead narrowed to 1.7 points over Rizal, and Rizal has the higher subsistence incidence.
- **Not available at provincial level in project data:** NNC indicators after 2015, provincial LFS employment, and provincial FIES.

## 2. E158 vs RP+R vs the revised method (Lead 1, 40 within-region pairs, 25 region-round clusters)
| Arm | Concordance [95 %] | 2018 / 2019 / 2021 | Spearman 2018 / 2019 / 2021 | Kendall 2018 / 2019 / 2021 | Top-1 hit | Position error |
|---|---|---|---|---|---|---|
| E158 | 0.600 [0.436, 0.732] | 0.58 / 0.57 / 0.64 | 0.72 / 0.54 / 0.65 | 0.56 / 0.37 / 0.50 | 3/6 | 0.467 |
| RP (RP+R's anchor) | 0.700 [0.545, 0.837] | 0.58 / 0.64 / 0.86 | 0.59 / 0.62 / 0.67 | 0.44 / 0.47 / 0.50 | 3/6 | 0.333 |
| OH | 0.675 [0.515, 0.813] | 0.67 / 0.57 / 0.79 | 0.78 / 0.72 / 0.62 | 0.63 / 0.54 / 0.49 | 3/6 | 0.373 |
| FH | 0.700 [0.538, 0.842] | 0.58 / 0.64 / 0.86 | 0.75 / 0.74 / 0.65 | 0.58 / 0.54 / 0.51 | 3/6 | 0.307 |
| **SS (revised candidate)** | **0.700 [0.545, 0.837]** | 0.58 / 0.64 / 0.86 | 0.74 / 0.70 / 0.64 | 0.57 / 0.53 / 0.47 | 3/6 | 0.333 |

- **Why RP+R ranks differently from E158:** RP+R's ordering comes entirely from its anchor. RP alone scores the same 0.70. Its LightGBM residual, the trigger and news part, **performed worse than shuffled inputs** in E161, so its added components do not improve ordering.
- **The gap from E158 to the survey-based methods comes from E158's structural level,** a poverty and density mapping learned on other regions, which overrides each province's own survey position.
- **Is E158 more reliable for ordering?** **No.** It is the weakest arm on every ranking measure. But none of the differences is significant (E159: −0.10 [−0.28, +0.07] vs the latest survey), so E158 is not shown to be worse either.

## 3. Quezon calculation trace (E158, 2027-Q1)
From `data/e160/out/trace.json`:

| Step | Logit | % |
|---|---|---|
| Latest survey, 2019 | −0.241 | 44.0 |
| Shared national level (2021) | −0.283 | 43.0 |
| + structural level (poverty, density, food threshold) | −0.260 | |
| + own deviation −0.105 × weight 0.753 | −0.079 | |
| = anchor | −0.623 | 34.9 |
| + residual: common intercept −0.276, Quezon-specific +0.128 | −0.148 | |
| = final | −0.770 | **31.6** |
| P(HIGH) = Φ(−0.770 / 0.459) | | 0.047 |
| Rank among the five (E158) | | 3rd |

## 4. Hypotheses about Quezon's underestimation
| Hypothesis | Finding |
|---|---|
| Regional shrinkage suppresses Quezon | **Minor.** The own-deviation weight is 0.75, so shrinkage moves Quezon by only +0.026 logit. |
| Too much weight on the shared level | **Partly.** All provinces get the 2021 national level (43.0). Moving Quezon's 2019 reading to it costs −5.3 points. That step is legitimate, because the national level fell. |
| Province evidence loses influence with horizon | **Yes, for survey age, not for horizon.** Hier2 carries the level flat, but old and new rounds get equal weight in the deviation. SS adds variance per year (q = 0.05) and keeps more of Quezon's history. |
| Poverty underweighted or mis-transformed | **No transform error.** The PSA 2023 values match the published figures. The structural mapping is learned across regions, and it lowers Quezon after its real poverty fall while raising Rizal (+0.23). It sits **inside** the problem: it is the component that orders worst. |
| Missing employment or remittance data disadvantage Quezon | **No.** `unemp_region` and `remit_q_yoy` are empty in training and dropped. The employment contribution is identical for all five (+0.012). |
| The probability calculation suppresses the score | **No.** The sd is common (0.459), so P(HIGH) has the same order as the score. |
| Classification probability confused with relative priority | **Yes, in the old LGU ranking.** P(HIGH) values near 0 (Rizal 0.097 vs Quezon 0.047) doubled score gaps of a few points. This was fixed in LGU-v2. |

**Exact cause:** E158's structural level replaces each province's observed relative position with a poverty and density prediction learned on other regions. In 2026 that prediction moves Rizal up and Quezon down. Shrinkage and the probability step are not the cause.

## 5. Revised method: tested, **not adopted**
SS (state space, own survey history with age variance and a poverty prior) passes P1, P2 and P3 but **fails P4**:

| Gate | Result |
|---|---|
| P1 concordance lower bound > 0.5 | 0.545, pass |
| P2 Spearman > 0 in every round | pass |
| P3 concordance ≥ 0.5 in every round | 0.58 / 0.64 / 0.86, pass |
| **P4 real − shuffled history, lower bound > 0** | **+0.15 [−0.028, +0.325], FAIL** |

- With histories swapped between provinces of the same region, ordering is still 0.55. The province's own history adds +0.15, but that gain is not distinguishable from chance with 25 clusters.
- **SS level is strongly biased upward** (+10 points overall, +12.7 in Luzon) because it ignores the national decline since 2015. It could never serve as the risk level, only as a priority.
- **Per the rule, the priority method falls back to E158, labelled "order not validated".**

## 6. Historical ranking validation
Lead 1 test rows always have exactly 2 earlier rounds (2013 and 2015), because each province has only one ENNS round. **The data cannot separate provinces by number of survey rounds.**

- **CALABARZON:**
  - Quezon above Rizal in 2019: every arm right.
  - Batangas above Cavite in 2021: every survey-based arm right, E158 wrong.
  - **Quezon was never compared with Batangas, Cavite or Laguna in a test round.**

## 7. Nested selection and shuffled-input results
- **Nested selection for ordering:** RP was picked in each held-out round, giving nested 0.70, equal to the best single arm. **No selection optimism.** The survey-based ordering advantage is stable, though not significant against E158.
- **Shuffled controls:**
  - SS history: above.
  - E161, triggers and news: no arm above chance.

## 8. Bias
| Group | E158 signed error (points) | SS signed error (points) |
|---|---|---|
| Luzon (35) | **+5.5 [3.0, 7.9]** | **+12.7** |
| Visayas (15) | −0.6 | **+7.7** |
| Mindanao (22) | +1.1 | **+7.1** |
| Observed HIGH (25) | −1.6 | +2.9 |
| Observed LOW (47) | **+5.3 [3.0, 7.6]** | **+13.7** |
| Newer survey (47) | **+5.3 [1.2, 9.3]** | +8.3 |
| Older survey (25) | −1.5 | +13.2 |
| Fewer vs more rounds | **Not testable:** every row has 2 | |

- **Ranking by survey age:** among pairs that involve a province with an older survey, E158 gets 0.64 right and SS 0.86. Among the others, E158 gets 0.58 and SS 0.62.
- **CALABARZON alone:** 5 rows, too small to establish fairness. **The absence of a significant result is not proof of fairness.**

## 9. LGU priority
- **LGU-v2 is kept:** tier by class, then 0.6 poverty + 0.4 density, with no multiplier.
  - Top 20: Cavite 11, **Quezon 6**, Laguna 1, Rizal 1, Batangas 1. The old list had Rizal 11, Cavite 9 and **Quezon 0**.
- **Poverty-only sensitivity, not adopted (the weights are the owner's decision):**
  - Top 20: **Quezon 19**, Laguna 1 (Siniloan).
  - Top 10: San Francisco, Macalelon, San Andres, Infanta, Panukulan, Pitogo, Agdangan, Buenavista, Pagbilao, General Luna, all in Quezon with 24.6–30.2 % poverty.
  - File: `lgu_poverty_only_sensitivity.csv`.

## 10. Is Quezon first? **Not supported as a ranking. The vulnerability is supported.**
| Condition | Result |
|---|---|
| (a) The priority method passed P1–P4 | **No.** SS failed P4; E158 failed E159 |
| (b) P(Quezon highest) ≥ 0.80 | **No.** SS 0.36 (Rizal 0.23, Batangas 0.21); E158 0.19 |
| (c) Direct same-instrument comparative evidence consistent | **Partly.** Quezon was highest in 2013 and 2015 (all five measured), but there has been no joint round since 2015 |

**Conclusion:** Quezon's food-insecurity vulnerability is documented directly (FNRI) and indirectly (PSA poverty and LGU poverty). Credible evidence cannot establish that it is higher than every other province **now**.

**Display:**
- the five provinces without rank numbers, all LOW, each with its 90 % range;
- an evidence note: "Quezon recorded the highest HFIAS moderate-or-severe share of the five provinces in 2013 and 2015, the last rounds measuring all five, and has the highest 2023 poverty incidence and the most high-poverty municipalities";
- LGU-v2 for municipalities.

The E158 P(highest) favours Rizal (0.47), but **it is not shown**, because E158's order failed validation.

## 11. Release gate recommendation
| Component | Recommendation |
|---|---|
| HIGH/LOW class (E158) | Keep as the thesis model. Retrospective Lead 1 73.6 %, honest range 72–74 %. Maximum reliable lead 0 (fails C1 and C4). **Not release-ready for production claims.** |
| Provincial ranking | **Not validated. Do not display a ranking or P(highest).** |
| Quezon evidence note | Display, with sources #1, #2, #5 and #8. |
| LGU list | LGU-v2 replaces the multiplier list. Weights await an owner decision. |
| Production, dashboard, API | **Unchanged.** Wiring E158 and LGU-v2 needs the owner's go-ahead. A prospective seal of the five-province order should be added before the next FNRI release. |

## Owner decision, 2026-11-06: LGU weights kept at 0.6 / 0.4
- **Final LGU list:** `backend/data/e162/out/lgu_priority_final_2027-Q1.csv`.
  - Tier by E158 class (all LOW), then vulnerability = 0.6 × poverty percentile + 0.4 × density percentile.
  - The province P(HIGH) is removed from the file, because the provincial order is not validated.
- **Ties:** 15 pairs of LGUs have exactly equal vulnerability. With no validated provincial priority to break them, ties now go to the **higher poverty percentile (LGU-level evidence), then PSGC code.** This is neutral and province-blind.
  - Effect on the top 20: two swaps. Siniloan (24.4 %) moves above Noveleta (12.3 %), and Agdangan (25.5 %) above Candelaria (15.8 %). The set of LGUs is unchanged: Cavite 11, Quezon 6, Laguna 1, Rizal 1, Batangas 1.
- The poverty-only list remains a sensitivity view, not adopted.
