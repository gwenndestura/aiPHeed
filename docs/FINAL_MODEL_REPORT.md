# aiPHeed: final model report

**Provincial food-insecurity risk forecasting for CALABARZON (Batangas, Cavite, Laguna, Quezon, Rizal).** 2026-11-06. Branch `aiPHeed/e158-thesis-model`.

## 1. Decision
| Role | Model | Why |
|---|---|---|
| **Production thesis model** | **E158** | Fixed before all later testing, so it carries the least optimism. It beats persistence and all four baselines significantly. Sealed f69e7a02 |
| **Highest accuracy that is trustworthy** | **E166** | Lead 1 76.4 %, Lead 2 79.2 %. Inputs chosen from training data only; real inputs beat shuffled ones. **Not accepted:** it fails the bias (+3.25), 2021-round and calibration gates by small margins |
| Withdrawn | E164 AUTO (79.2 %) | Its consumption inputs were selected using the test rows |
| Rejected | E165 AUTO-FINAL, E167 | Not better than E158; E167 is worse on bias and accuracy |

**No model has a reliable forecast lead.** The maximum reliable lead is 0 for every model, by the fixed E156 rule (§5).

## 2. Accuracy and high-risk detection (Lead 1 = one quarter ahead, 72 out-of-sample provincial forecasts, about 46 effective)
| | Persistence | **E158** | E164 AUTO (withdrawn) | **E166** | E167 |
|---|---|---|---|---|---|
| Accuracy | 62.5 % | **73.6 %** | 79.2 % | **76.4 %** | 66.7 % |
| Balanced accuracy | 0.703 | 0.760 | 0.812 | **0.800** | 0.726 |
| **HIGH caught / 25** | 24 | 21 | 22 | **23** | 23 |
| **HIGH missed** | 1 | 4 | 3 | **2** | 2 |
| False alarms | 26 | 15 | 12 | 15 | 22 |
| HIGH precision / recall | 0.48 / 0.96 | 0.58 / 0.84 | 0.65 / 0.88 | 0.61 / **0.92** | 0.51 / 0.92 |
| LOW precision / recall | 0.96 / 0.45 | 0.89 / 0.68 | 0.92 / 0.75 | **0.94** / 0.68 | 0.93 / 0.53 |
| Macro F1 | 0.62 | 0.73 | 0.79 | **0.76** | 0.67 |
| ROC-AUC / PR-AUC | 0.83 / 0.71 | 0.86 / 0.81 | 0.90 / 0.86 | **0.90 / 0.86** | 0.89 / 0.85 |
| Brier (lower is better) | 0.213 | 0.134 | 0.122 | **0.125** | 0.156 |
| Overall bias (points) | n/a | **+2.9** | +2.8 | +3.25 | +6.3 |
| Within-region province order | 0.70 | 0.60 | 0.725 | **0.75** | 0.65 |

**Paired comparisons with E158 (region-cluster bootstrap; exact McNemar):**
- **E166:** Brier −0.010 [−0.038, +0.020]. 7 rows right only for E166, 5 only for E158, p = 0.77. **Better, but not statistically significant.**
- **E167:** Brier +0.022 [−0.014, +0.058]. 2 vs 7, p = 0.18. **Worse.**
- **E158 vs persistence:** Brier −0.078, interval below 0. **Significant.**

**High-risk detection:** E166 misses only 2 of 25 HIGH provinces. Errors lean toward false alarms, which suits early warning. Precision is about 0.6.

## 3. Lead 2 (two quarters ahead)
| | E158 | E166 | E167 |
|---|---|---|---|
| Accuracy | 73.6 % | **79.2 %** | 68.1 % |
| Balanced accuracy | 0.760 | **0.822** | 0.746 |
| HIGH caught / missed | 21 / 4 | **23 / 2** | 24 / 1 |
| Brier | 0.137 | **0.125** | 0.153 |
| E156 C1 | fails | **passes** | fails |
| E156 C4 | fails | fails | fails |

## 4. Justifiability checks
| Check | E158 | E166 | E167 |
|---|---|---|---|
| Leakage (unreleased survey rounds randomised) | passes | **0.0 change** | 0.0 change |
| Test-set influence on inputs | none | **none:** source picked from training only (consumption in 2 of 3 rounds) | none |
| Real inputs vs shuffled provinces (Brier) | not tested | **−0.035 [−0.063, −0.009]: real inputs help** | +0.032: real inputs worse |
| Consumption only shuffled | n/a | not tested | +0.021 [+0.003, +0.043]: consumption hurt in E167 |
| Bias by island (Luzon / Visayas / Mindanao) | +5.5 / −0.6 / +1.1 | +4.0 / +1.4 / +3.3 | +7.2 / +4.4 / +6.3 |
| Accuracy by round (2018 / 2019 / 2021) | 63.6 / 68.0 / **88.0 %** | **72.7 / 76.0** / 80.0 % | 50.0 / 64.0 / 84.0 % |
| Probability calibration slope (ideal 1) | 1.53 [0.93, 2.79] | 1.53 [0.89, 3.47] | 1.39 [0.93, 2.52] |

**Consumption's contribution is not robust.** It helped inside E166, where the inputs beat shuffled data. But in E167, the same procedure with a different calibration and fold rule made it worse than shuffled. It is a plausible input, not a proven one.

## 5. Maximum reliable lead, every model (fixed E156 rule: a lead counts only if it and every shorter lead pass C1–C6)
| Model | Leads tested | **Max reliable lead** | Accuracy by lead (criteria failed) |
|---|---|---|---|
| E158 | 1–8 | **0** | L1 73.6 (C1, C4) · L2 73.6 · L3 75.0 · L4 75.0 · L5 72.2 · L6 68.1 · L7 48.0 · L8 56.0 |
| E164 AUTO | 1–4 | **0** | L1 79.2 (C4) · L2 79.2 (C4) · L3 76.4 · L4 76.4 |
| E165 AUTO-FINAL | 1–2 | **0** | L1 73.6 (C1, C4) · L2 76.4 (C1, C4) |
| E166 | 1–2 | **0** | L1 76.4 (C1, C4) · L2 79.2 (C4) |
| E167 | 1–2 | **0** | L1 66.7 (C1, C4, C5) · L2 68.1 |

- Computed by `backend/app/e156/max_lead_all.py` into `data/e156/out/max_lead_all.json`. **The dashboard must read the lead from this file, never from a hardcoded value.**
- **C4 (calibration) fails for every model at every lead.** The cause is the national HFIAS fall from 56.2 % (2015) to 46.5 % (2018). The 2018 and 2019 forecasts had only the 2013 and 2015 rounds to learn from, so they could not see it. This produces **all of the upward bias** (2018 +6.8, 2019 +5.4; 2021 −2.0), and 17 of the 20 rows in the 40–60 % probability band.

## 6. CALABARZON
**Back-test (out of sample; all actual values below 50, so LOW):**

| Province (round) | Actual HFIAS mod + sev | E158 | E166 | Class right? |
|---|---|---|---|---|
| Laguna (2018) | 26.2 | 35.5 | 35.1 | ✅ |
| Quezon (2019) | 44.0 | 48.0 | 45.2 | ✅ |
| Rizal (2019) | 39.1 | 42.7 | 37.5 | ✅ |
| Batangas (2021) | 39.9 | 26.2 | 27.3 | ✅ |
| Cavite (2021) | 35.5 | 29.3 | 27.3 | ✅ |

- All 5 classes are right. **CALABARZON has never been observed HIGH, so HIGH detection inside the region is untested.**
- **Batangas** is under-predicted because its position relative to the national level rose from 2015 to 2021, which no input showed in advance.

**2027-Q1 forecast (E158, sealed f69e7a02; issued 2026-10-01):**

| Province | Score | 90 % range | Class |
|---|---|---|---|
| Batangas | 26.6 | 15.7–41.4 | LOW |
| Cavite | 32.1 | 19.5–47.9 | LOW |
| Laguna | 29.8 | 17.9–45.3 | LOW |
| Quezon | 31.6 | 19.2–47.4 | LOW |
| Rizal | 35.5 | 22.0–51.8 | LOW |

- **Shown unranked.** The order between provinces is not validated (E159, E162).

**Independent evidence for LOW:**
- every FNRI HFIAS reading since 2013 is below 50;
- PSA FIES 2023 puts Region IV-A at 19.1 %, the lowest of 17 regions;
- PSA 2023 poverty is 7.9 %.

**LOW is not "no food insecurity":** 26–44 % of households were moderately or severely food insecure in the latest surveys. **Quezon is closest to the line** (48.9 in 2013, 48.8 in 2015, 44.0 in 2019), with the highest poverty (10.2 %) and the most high-poverty LGUs.

**LGU priority:** LGU-v2: provincial class tier, then 0.6 × poverty + 0.4 × density (owner weights), with no probability multiplier. The top 20 are Cavite 11, Quezon 6, Laguna 1, Rizal 1, Batangas 1.

## 7. Five trigger groups and news
| Group | Provincial official data? | Demonstrated predictive contribution |
|---|---|---|
| Market and prices | Yes (provincial CPI) | Not demonstrated alone |
| Climate stress | Yes / regional | Not demonstrated alone |
| Employment | **National only** | None (cannot separate provinces) |
| OFW remittances | **National only** | None |
| Poverty and social vulnerability | Yes / regional | The strongest group; not demonstrated alone |
| News (inside the groups) | Provincial / regional | **None out of sample**, despite high feature importance |

- **All five groups are kept on the dashboard as monitoring indicators,** labelled "predictive contribution not demonstrated" except where shown.

## 8. What the thesis can claim
> "aiPHeed forecasts food-insecurity risk for the five CALABARZON provinces one quarter ahead. The production model (E158) achieved 73.6 % out-of-sample accuracy, significantly better than persistence and the other baselines. A training-only automated selection with regional household consumption (E166) reached 76.4 % at one quarter and 79.2 % at two quarters, detecting 23 of 25 high-risk cases, but did not meet the pre-specified bias, round-stability and calibration criteria. No forecast lead met all reliability criteria, so a reliable horizon could not be established with the available survey rounds. All five provinces are forecast LOW, consistent with FNRI and PSA evidence."

## 9. What is needed to go further
1. **New FNRI provincial HFIAS rounds** (after 2021). This is the binding limit for calibration, bias and any independent test.
2. **PSA regional household consumption for 2025** (2024 is published; 2025 is not verified). Without it, consumption is unavailable at the 2026-Q4 issue.
3. **Provincial employment** (PSA LFS) and **remittances** (PSA SOF, by region).
4. **Prospective scoring of the sealed forecasts** (f69e7a02, 343d1f06, cbfb61dc) once 2027 data exist.

**Production, the dashboard and the API are unchanged.** Detailed reports are in `docs/e158`–`docs/e167`, and every experiment is listed in `docs/EXPERIMENT_REGISTRY.md`.
