# E161 result: overfitting and bias audit (Lead 1, 72 rows)

The criteria are in `CRITERIA.md` (bd332c4c), committed before results. The code is `backend/app/e161/audit.py` and the output is `backend/data/e161/out/results.json`.

**One clarification made while coding, before the run:** the shuffled-input test permutes every E158 input except `gap_q` and `lead`. Those two are timing columns used by the interval model, not trigger or news inputs. Permuting them would test the interval, not the triggers.

## A. Overfitting
| Check | E158 | RP+R | OH+R | Flag |
|---|---|---|---|---|
| Accuracy | 73.6 % | 72.2 % | 77.8 % | |
| Nested selection: pick an arm on 2 rounds, score on the 3rd | | | | **72.2 %**, against 77.8 % for the best arm afterwards. **OVERFIT-SELECTION** |
| Real − shuffled Brier [95 %] | −0.037 [−0.090, +0.014] | **+0.011 [+0.001, +0.024]** | −0.003 [−0.018, +0.012] | **NO-SIGNAL for all three** |
| Accuracy by round, 2018 / 2019 / 2021 | 63.6 / 68.0 / 88.0 | 59.1 / 72.0 / 84.0 | 63.6 / 84.0 / 84.0 | **UNSTABLE for all three** (range > 20 points) |

- **77.8 % is selection optimism.** When the choice of arm is made without seeing the scored round, accuracy is 72.2 %. The held-out rounds picked OH+R, E158 and OH+R.
- **No arm's trigger and news inputs beat shuffled inputs with confidence.**
  - E158 comes closest: −0.037, with an interval just reaching 0.
  - For RP+R, **real inputs are significantly worse than shuffled ones.** Its residual adds noise to a good anchor.
- **Accuracy rises from about 60 % in 2018 to about 85 % in 2021.** That swing is larger than any difference between arms.

## B. Bias (predicted % − observed %)
| Group | n | E158 | RP+R | OH+R |
|---|---|---|---|---|
| Overall | 72 | +2.9 [0.6, 5.1] | **+4.5 [1.9, 7.2] BIAS** | **+3.2 [1.1, 5.4] BIAS** |
| Luzon | 35 | **+5.5 [3.0, 7.7] BIAS** | **+7.5 [3.5, 12.2] BIAS** | **+4.6 [1.1, 8.2] BIAS** |
| Visayas | 15 | −0.6 | **+3.3 [0.6, 5.1] BIAS** | +1.4 |
| Mindanao | 22 | +1.1 | +0.3 | +2.3 |
| Observed HIGH | 25 | −1.6 | 0.0 | −0.2 |
| Observed LOW | 47 | **+5.3 [2.8, 7.7] BIAS** | **+6.8 [3.4, 10.4] BIAS** | **+5.0 [2.2, 7.9] BIAS** |
| CALABARZON | 5 | −0.6 | +0.3 | −3.5 |

- **The CALABARZON row cannot be tested.** It is one region, so its bootstrap interval collapses to a point. The OH+R flag for it is mechanical and not evidence.
- **Every arm over-predicts provinces that turned out LOW, by 5 to 7 points, mostly in Luzon.** This bias points towards false alarms, not misses. No arm is biased on HIGH provinces.
- **E158 is the least biased:** overall +2.9, below the 3-point flag.

Unequal errors by island (n is small, 7 to 14 per cell):
- E158: Visayas misses 38 %; Mindanao false alarms 38 %.
- RP+R: **Visayas false alarms 71 %.**
- OH+R: Mindanao false alarms 63 %; Luzon misses 1 of 3.

## What this means
1. **Accuracy:** about 72–74 % is the honest Lead 1 figure: E158's 73.6 % as a single, pre-chosen model, or the 72.2 % nested estimate. The 77.8 % is not.
2. **Overfitting:** the anchors (survey history) carry the forecast. The quarterly triggers and news have no signal proven against chance at the province level. The trigger groups meet the objective's design, but **their measured contribution is not distinguishable from noise.**
3. **Bias:** a consistent upward bias on LOW provinces, mainly Luzon. It is smallest in E158.
4. **E160 adoption:** RP+R was adopted for province order by a fixed rule. E161 shows that its ordering benefit comes from the anchor (RP alone also scores 0.70), while its residual hurts and it is the most biased arm. **Per the E161 criteria, nothing is changed automatically. Revisiting the E160 adoption is an owner decision.**
