# Why aiPHeed has no maximum reliable lead time

2026-11-06.
- **Sources:** `data/e156/out/max_lead_all.json`, `data/e166/out/lead_horizon.json`, `data/e166/out/c1_c4_diagnosis.json`, `docs/e166/C1_C4_ANALYSIS.md`.
- **Rule:** fixed in E156 before any of these results.

## 1. The rule
A forecast lead (quarters ahead) is **reliable** only if that lead **and every shorter lead** pass all six criteria:

| | Criterion | What it guards against |
|---|---|---|
| C1 | Accuracy above the always-LOW rule, with the lower end of its 95 % interval above that rule at the effective sample size | A result that could be luck |
| C2 | Brier score better than persistence (the latest survey), with the interval below 0 | A model no better than "nothing changes" |
| C3 | HIGH recall ≥ 0.5 and LOW recall ≥ 0.5 | A model that only predicts one class |
| C4 | Calibration slope 95 % interval includes 1 | Forecast levels systematically too spread or too flat |
| C5 | At least as good as persistence in 2 of 3 survey rounds | A result carried by one round |
| C6 | At least 40 evaluated rows | Too few cases |

**Maximum reliable lead = the number of consecutive passing leads, starting from Lead 1.** If Lead 1 fails, the answer is 0, whatever happens at longer leads.

## 2. The result
| Lead | E158 accuracy | E166 accuracy | C1 | C2 | C3 | **C4** | C5 | C6 |
|---|---|---|---|---|---|---|---|---|
| 1 | 73.6 % | 76.4 % | ❌ | ✅ | ✅ | **❌** | ✅ | ✅ |
| 2 | 73.6 % | 79.2 % | ✅ (E166) | ✅ | ✅ | **❌** | ✅ | ✅ |
| 3–4 | 75.0 % | 76.4 % | ❌ | ✅ | ✅ | **❌** | ✅ | ✅ |
| 5–6 | 72.2 / 68.1 % | 73.6 / 72.2 % | ❌ | ✅ | ✅ | **❌** | ✅ | ✅ |
| 7–8 | 48–56 % | 68.0 % | ❌ | ❌ | | ❌ | ❌ | ✅ |

**Every model (E158, E164, E165, E166, E167) has a maximum reliable lead of 0.** Two criteria are responsible: **C4 fails at every lead for every model**, and **C1 fails at Lead 1.**

## 3. Reason 1: calibration (C4) fails because the national level shifted between survey rounds
| Round forecast | Training survey rounds available | National HFIAS (moderate + severe) | E166 mean forecast | Observed mean | Error |
|---|---|---|---|---|---|
| 2018 | 2013, 2015 (57.6, 56.2) | 46.5 | 54.2 | 47.4 | **+6.8** |
| 2019 | 2013, 2015 | 48.4 | 54.6 | 49.2 | **+5.4** |
| 2021 | 2013, 2015, 2018, 2019 | 43.0 | 39.6 | 41.6 | **−2.0** |

- **National food insecurity fell about 9 points between 2015 and 2018.** The 2018 and 2019 forecasts could only learn from 2013 and 2015, when the level was flat. So they forecast too high, especially for provinces that turned out LOW (+9 to +11 points).
- **By 2021 the model had learned the lower level, and the error reversed** (−2.0). In 2021 the provinces were also forecast **too far apart** (slope 0.62).
- **Calibration by round:**

| Round | Calibration slope |
|---|---|
| 2018 | 1.15 |
| 2019 | 0.91 |
| 2021 | 0.62 |

  Pooled over the three rounds, the slope is 0.74 [0.51, 0.87], which excludes 1. **The error changes direction from round to round.**
- **Training-only calibration was tested and failed:**
  - linear recalibration and Platt scaling inside the training data (E165, E167);
  - a correction learned from the 2018–2019 forecasts and applied to 2021, which made 2021 worse (bias −2.0 → −7.9 points, Brier 0.098 → 0.106, slope unchanged).

  **The shift could not be learned from the earlier rounds.**
- **Fitting the calibration on the test rounds themselves would make C4 pass, but it would be circular and is not done.**

## 4. Reason 2: accuracy (C1) is not yet statistically clear at Lead 1
- Errors are shared within a region and survey round (73 % of error variance), so **72 forecasts are worth about 46 independent ones.**
- Always predicting LOW would score **65.3 %**.
- At 46 effective rows, the lower bound must exceed 65.3 %, which needs **56 of 72 correct:**

| Lead | E166 correct | Needed | Result |
|---|---|---|---|
| 1 | 55 | 56 | **One forecast short** |
| 2 | 57 | 56 | Passes |

- **C1 is a sample-size limit, not a model defect.**

## 5. Why Lead 2 does not count even though it passes C1
- **Lead 2 still fails C4.**
- And under the rule, **a longer lead cannot be reliable when a shorter lead is not.** An operational forecast must be trustworthy one quarter ahead before it can be trusted two quarters ahead.

## 6. Why accuracy stays flat across leads, and what that means
- **E166 beats persistence significantly up to 6 quarters ahead.** That is its skill horizon (C2); E158's is 5.
- **Accuracy barely changes from Lead 1 to Lead 4** because the forecast relies mostly on each province's latest FNRI survey. FNRI releases surveys about 6 quarters after fieldwork, so the 1-, 2-, 3- and 4-quarter-ahead forecasts usually start from **the same survey.**
- **High accuracy at long leads therefore reflects stable survey information, not foresight**, and it is not evidence of a reliable horizon.

## 7. The underlying limit: too few survey rounds
| Constraint | Effect |
|---|---|
| Only 3 testable rounds (2018, 2019, 2021) | Calibration across rounds cannot be learned and tested |
| 2018 and 2019 forecasts had a single earlier round (2015) to learn from | The 2015→2018 fall was invisible |
| About 46 effective rows | C1 needs 77–78 % accuracy |
| No CALABARZON province ever observed HIGH | High-risk detection inside the region is untested |
| No public provincial HFIAS after 2021 | No new round to validate on |

## 8. A definitional note on C4 (does not change the answer)
- **The implemented and pre-registered C4** is the slope of observed on predicted **prevalence levels** (logit scale). It fails.
- **Some reports also quoted a "probability slope"** (logistic regression of HIGH on the forecast probability). E166 passes that one (1.53 [0.93, 3.40]).
- **The official definition is kept,** because switching after seeing the results would be post hoc.
- **Even under the alternative,** Lead 1 still fails C1, so **the maximum reliable lead remains 0.** The adviser should confirm the intended definition for future rounds.

## 9. What would establish a reliable lead
1. **ENNS 2022 provincial HFIAS results.** Frozen forecasts for every province are already sealed (49e514d2), so they can be scored on a round no model has seen. That adds about 20 rows for C1 and a fourth round for C4.
2. **Any later FNRI provincial HFIAS round.** The 2023 NNS used FIES and cannot be used.
3. **A timely national indicator of the HFIAS level** between rounds. None exists in the project: SWS hunger moved the opposite way in 2020–2021.

## 10. Statement for the thesis
> "No forecast lead met all six predefined reliability criteria, so a maximum reliable forecast horizon could not be established (0 quarters). The models outperformed persistence up to five to six quarters ahead and reached 73.6–79.2 % accuracy at Leads 1–2, but probability calibration failed at every lead because forecast errors shifted direction between the three available survey rounds (over-prediction in 2018–2019 after an unseen national decline, under-prediction in 2021), and Lead 1 accuracy was one correct forecast short of statistical significance at the effective sample size. Additional provincial HFIAS rounds are required to establish a reliable horizon."
