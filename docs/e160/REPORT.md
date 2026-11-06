# E160 report: Quezon ranking and LGU priority correction

- **Criteria:** `CRITERIA.md`, committed in 185cf425 before any arm result.
- **Code:** `backend/app/e160/` (`trace.py`, `arms.py`).
- **Outputs:** `backend/data/e160/out/`.
- The owner's prompt names this "E159". That number holds the earlier ranking test.

## 1. Calculation trace, 2027-Q1, Lead 1 (E158)
All values are on the logit scale unless marked %. Score = 100/(1+e^−final).

| | Batangas | Cavite | Laguna | Quezon | Rizal |
|---|---|---|---|---|---|
| Latest survey (round) | 39.9 % (2021) | 35.5 % (2021) | 26.2 % (2018) | **44.0 % (2019)** | 39.1 % (2019) |
| Quarters since that survey | 22 | 22 | 34 | 30 | 30 |
| Shared level (national 2021 = 43.0 %) | −0.283 | −0.283 | −0.283 | −0.283 | −0.283 |
| Structural level (poverty, density, food threshold; cross-fitted by region) | −0.409 | −0.441 | −0.360 | −0.260 | −0.350 |
| Own deviation × weight 0.75 | −0.084 | +0.157 | −0.034 | −0.079 | +0.158 |
| **Anchor** | 31.5 % | 36.2 % | 33.7 % | 34.9 % | 38.3 % |
| Residual: common intercept | −0.276 | −0.276 | −0.276 | −0.276 | −0.276 |
| Residual: province-specific (sum of the groups) | +0.039 | +0.092 | +0.099 | +0.128 | +0.155 |
| **Final score** | 26.6 | 32.1 | 29.8 | 31.6 | 35.5 |
| P(HIGH) | 0.014 | 0.051 | 0.031 | 0.047 | 0.097 |
| Class | LOW | LOW | LOW | LOW | LOW |

The province-specific residual by group, in logit units:
- Quezon: climate +0.051, news +0.041, poverty +0.013, employment +0.012.
- Rizal: climate +0.081, news +0.040, market +0.026.
- The full split is in `trace.json`.

## 2. Why Quezon's 44.0 becomes 31.6
| Step | Points (approx.) | Cause |
|---|---|---|
| 44.0 → 38.7 | −5.3 | **National change.** Quezon's 44.0 is a 2019 reading, when the national level was 48.4 %. By 2021 it was 43.0 %. Carrying Quezon's 2019 position relative to the nation forward gives 38.7. This step is legitimate. |
| 38.7 → 34.9 | −3.8 | **Structural level + shrunk deviation.** The model replaces Quezon's observed relative position (−0.18 in 2019, −0.28 averaged over rounds) with −0.34. Most of this comes from PSA 2023 poverty: Quezon fell from 1.86 to 2.18 below the logit mean (to 10.2 %), and its subsistence incidence fell to about 0.5 %, below Rizal's 1.5 %. **These are genuine PSA figures, not an artifact.** But E159 showed that this structural mapping does not order provinces within a region well. |
| 34.9 → 31.6 | −3.3 | **Residual.** A common −0.276 intercept (the anchor runs high) moves every province by the same amount, partly offset by Quezon's +0.128. |

- **Batangas falls to last** because its structural level (−0.409) and its 2013/2015 deviations (−0.38, −0.21) pull it below its 2021 reading. Its 2021 deviation of +0.25 is averaged with older rounds of equal weight, so the age of a survey is ignored.
- **Rizal and Cavite overtake Quezon** because their own deviations are positive (+0.21 each): they had higher food insecurity than their low poverty predicts. In 2026 the PSA 2023 inputs also move Rizal's structural level up by about +0.23 relative to its past rounds, and Quezon's down by about −0.1.

## 3. Shrinkage diagnosis
Three components compress the differences between provinces:
1. **One flat national level for everyone.** This doesn't by itself change the order.
2. **The structural level from poverty and density.** It is cross-fitted on other regions and replaces each province's observed position with a nationally learned mapping.
3. **Own deviations averaged over all rounds with equal age weight,** then shrunk by 0.75.

Measured spread (median sd of predicted / sd of observed, within region-round):
- E158 keeps the spread: 1.23 at Lead 1.
- The problem is the **order, not the amount of spread:** within-region concordance is 0.60.

## 4. Alternatives, same chronological protocol (Lead 1, 72 rows)
| Arm | Accuracy | Brier | AUC | HIGH recall | LOW recall | Within-region concordance [95 %] | Gap ≥ 5 | Spearman 2018/19/21 | Top-province hit | Brier − E158 [95 %] |
|---|---|---|---|---|---|---|---|---|---|---|
| E158 | 73.6 % | 0.134 | 0.860 | 0.84 | 0.68 | 0.600 [0.436, 0.732] | 0.60 | 0.72 / 0.54 / 0.65 | 3/6 | n/a |
| PERS | 62.5 % | 0.213 | 0.827 | 0.96 | 0.45 | 0.700 [0.545, 0.837] | 0.80 | 0.59 / 0.62 / 0.67 | 3/6 | n/a |
| RP | 69.4 % | 0.171 | 0.855 | 0.96 | 0.55 | 0.700 [0.545, 0.837] | 0.80 | 0.59 / 0.62 / 0.67 | 3/6 | +0.036 [−0.006, +0.087] |
| OH | 62.5 % | 0.167 | 0.928 | 1.00 | 0.43 | 0.675 [0.515, 0.813] | 0.80 | 0.78 / 0.72 / 0.62 | 3/6 | +0.032 [−0.007, +0.072] |
| **RP+R** | 72.2 % | 0.148 | 0.839 | 0.92 | 0.62 | **0.700 [0.564, 0.822]** | 0.73 | 0.52 / 0.47 / 0.69 | 2/6 | +0.013 [−0.023, +0.054] |
| OH+R | 77.8 % | 0.121 | 0.910 | 0.96 | 0.68 | 0.675 [0.524, 0.812] | 0.73 | 0.79 / 0.71 / 0.67 | 3/6 | −0.013 [−0.034, +0.010] |

Leads 2 to 4 are in `results.json` and give the same pattern.

**Gates:** RP+R and OH+R both pass G1 to G4. The fixed tie-break (higher concordance) **adopts RP+R.** Its margin over OH+R is 0.025, which is **one pair out of 40.**

**OH+R is better on class:** 77.8 %, Brier 0.121, and it passes C1 at Lead 1. It was not adopted. Choosing it now, after seeing these numbers, would be selecting on results, which the criteria forbid. It is recorded as the strongest unadopted arm.

None of the arms passes C4 (calibration slope) at Lead 1, so **the maximum reliable lead stays 0 for every arm.**

## 5. Historical province ranking
- **Most vulnerable province:** in the 6 region-rounds with 3 or more provinces, every arm picks the observed top province 2 to 3 times out of 6. **No arm identifies it reliably.** n = 6, so this cannot be validated.
- **Within-region concordance:** RP+R reaches 0.70, lower bound 0.56. That passes G1, but:
  - **it is retrospective and has a hindsight advantage,** because the RP family was designed after E159 showed that the latest survey ranks better;
  - only 40 pairs and 15 large-gap pairs exist;
  - it is no better than the plain latest survey (0.70).

## 6. Revised LGU prioritisation (LGU-v2)
The old rule was province P(HIGH) × vulnerability. The new rule:
1. Tier by province class (HIGH first).
2. Within a tier, sort by vulnerability = 0.6 × poverty percentile + 0.4 × density percentile. These are the owner's weights, unchanged.
3. Province score and P(HIGH) are shown as context, not multiplied in.

This creates no municipal label.

## 7. Old vs new top 20
| Province | Old top 20 | New top 20 | First rank, old → new |
|---|---|---|---|
| Cavite | 9 | 11 | 9 → 1 |
| Quezon | **0** | **6** | 24 → 10 |
| Rizal | 11 | 1 | 1 → 9 |
| Laguna | 0 | 1 | 71 → 6 |
| Batangas | 0 | 1 | 101 → 16 |

**Entered**, all because the multiplier is gone:
- Siniloan (Laguna, poverty 24.4 %)
- Plaridel, Pagbilao, Candelaria, Agdangan, Lucena, Tiaong (Quezon)
- Lipa (Batangas)
- Gen. Mariano Alvarez and Silang (Cavite)

**Left:** Rizal towns with 3.6–9.8 % poverty (San Mateo, Pililla, Angono, Baras, Teresa, Cainta and others). They ranked high only because Rizal's P(HIGH) of 0.097 was the largest.

**Remaining issue, owner decision:** density carries 40 % of the weight, so dense urban LGUs with moderate poverty still outrank sparse, very poor ones.
- The **poorest LGU in the region, San Francisco, Quezon (30.2 %), ranks 28th.**
- Cavite City (12.7 %) ranks 1st.
- This follows from the recorded 0.6/0.4 weights, not from the forecast. It was not changed.

## 8. Leakage and chronological validity
- **Every round used** at issue `i` satisfies RQ + 6 ≤ `i`. This is asserted in code.
- **Corruption test, Lead 1, all 3 surveys:** the `y` of every unreleased round, including the target round, was replaced with random values. **The maximum change in any new arm's forecast was 0.0.**
- **Quarterly inputs** are E158's, which already passed the E156 test for corrupting data after the issue quarter.

## 9. Decision on displaying the provincial order
- **By the fixed rule:** RP+R is adopted, so the provincial order **may be shown, labelled "retrospective validation", with P(highest)**.
- **2027-Q1 under RP+R:**

| Province | Score | 90 % range | P(HIGH) | P(highest) |
|---|---|---|---|---|
| Quezon | 34.8 | 20.1–53.2 | 0.105 | **0.36** |
| Batangas | 34.3 | 19.7–52.6 | 0.097 | 0.32 |
| Rizal | 31.7 | 17.9–49.7 | 0.063 | 0.17 |
| Cavite | 31.2 | 17.5–49.1 | 0.057 | 0.15 |
| Laguna | 21.0 | 11.1–36.2 | 0.004 | 0.00 |

- All are LOW.
- **Quezon is the most likely highest, but this is not established.** Quezon and Batangas are 0.5 points apart, with P(highest) of 0.36 and 0.32. The display should show P(highest), not rank numbers 1 to 5.
- **Not changed:** production, the dashboard, the API, the threshold and the E158 seal f69e7a02. RP+R is not sealed. A prospective seal is needed before it can be claimed beyond retrospective validation.
