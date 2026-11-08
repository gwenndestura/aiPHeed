# E149: HIGH at 50 %. Results

**Date:** 2026-11-04. **Branch:** `pfi/e149-high-50`, local only. **Protocol:** `docs/e149/PROTOCOL.md`, locked in commit `660dbe82` before any metric. **E148:** unchanged. **Production and dashboard:** unchanged.

## Verdict

**E149 does not pass its validation gates, so it is not eligible for deployment.** At 50 %, Lead 1 accuracy is 0.80, which is exactly what always saying HIGH scores.

**Evidence status.** The 2021 labels were opened by E148, so this is **not an untouched test**. Models train only on earlier releases, and nothing was tuned on 2021.

## 1. What 50 % does to the data

Any-level food-insecure households, the same measure as E148.

| Round | Share HIGH at 50 % | Rows |
|---|---|---|
| 2013 | 0.99 | 78 |
| 2015 | 0.96 | 78 |
| 2018 | 0.68 | 22 |
| 2019 | 0.92 | 25 |
| 2021 | 0.80 | 25 |

In CALABARZON, 14 of 15 HFIAS rows through 2021 are HIGH; only Laguna 2018 (39.3 %) is LOW. So there is very little LOW evidence to learn from: 1 row in 2013, 3 in 2015, 7 in 2018, 2 in 2019.

## 2. Lead 1 on 2021 (25 provinces: 20 HIGH, 5 LOW)

| Model | Accuracy | Precision | HIGH recall | LOW recall | F1 | AUC | Brier |
|---|---|---|---|---|---|---|---|
| **Q-G, LightGBM (selected)** | **0.80** | 0.857 | 0.90 | **0.40** | 0.878 | 0.770 | **0.107** |
| Always HIGH | 0.80 | 0.800 | 1.00 | 0.00 | 0.889 | n/a | n/a |
| **B1 Naive persistence** | **0.88** | 0.870 | 1.00 | 0.40 | 0.930 | 0.740 | 0.120 |
| Drift | 0.80 | 0.857 | 0.90 | 0.40 | 0.878 | 0.740 | 0.132 |
| Q-frozen | 0.80 | 0.857 | 0.90 | 0.40 | 0.878 | 0.750 | 0.118 |
| Q-noSWS | 0.80 | 0.857 | 0.90 | 0.40 | 0.878 | 0.740 | 0.110 |
| Q-GNB (corrected news) | 0.84 | 0.944 | 0.85 | 0.80 | 0.895 | 0.770 | 0.109 |
| Q-GN (raw news) | 0.84 | 0.944 | 0.85 | 0.80 | 0.895 | 0.750 | 0.110 |
| News-only LightGBM | 0.80 | 0.800 | 1.00 | 0.00 | 0.889 | 0.680 | 0.167 |
| B2 PSA-only logistic | 0.72 | 0.783 | 0.90 | 0.00 | 0.837 | 0.700 | 0.147 |
| B3 NLP-only logistic | 0.80 | 0.826 | 0.95 | 0.20 | 0.884 | 0.720 | 0.165 |
| B4 Logistic, all inputs | 0.84 | 0.944 | 0.85 | 0.80 | 0.895 | 0.740 | 0.158 |

**Confusion, Q-G:** TP 18, FP 3, TN 2, FN 2.

**How to read this:**
* LightGBM has the **best Brier**, but not significantly better than persistence: −0.014 [−0.053, +0.025].
* **Persistence beats it on accuracy,** 0.88 against 0.80.
* **The news arms' 0.84 and LOW recall 0.80 are not a news result.** Their Brier is slightly worse (+0.002 [−0.013, +0.017]) and three provinces changed side. These arms were not selected under the locked rule, and no claim follows.
* **Both of LightGBM's misses are in CALABARZON.** Batangas (56.9 %) and Cavite (50.2 %) were HIGH and predicted LOW (P 0.375, 0.382).

## 3. Gates at every lead

| Lead | Accuracy | LOW recall | AUC | Brier | Failed gates |
|---|---|---|---|---|---|
| 1 | 0.80 | 0.40 | 0.77 | 0.107 | R4, R7, R8 |
| 2 | 0.80 | 0.40 | 0.77 | 0.107 | R4, R7, R8 |
| 3 | 0.80 | 0.40 | 0.78 | 0.120 | R4, R6, R7, R8 |
| 4 | 0.80 | 0.40 | 0.77 | 0.121 | R4, R7, R8 |
| 5 | 0.80 | 0.40 | 0.77 | 0.121 | R4, R6, R7, R8 |
| 6 | 0.80 | 0.40 | 0.76 | 0.122 | R4, R6, R7, R8 |
| 7 | 0.88 | 0.40 | 0.78 | 0.121 | R4, R6, R8 |
| 8 | 0.88 | 0.40 | 0.78 | 0.121 | R4, R6, R8 |

R4 = beats persistence with confidence. R6 = predicts change. R7 = beats always-HIGH. R8 = LOW recall ≥ 0.50.

**Maximum reliable lead: 0 quarters.**

**R1 (accuracy ≥ 75 %) passes at every lead, but it means little here,** because always-HIGH passes it too. Leads 7 and 8 reach 0.88 because that model nearly always says HIGH, matching persistence.

**Development rows (2018, 2019, n = 47, 38 HIGH), Lead 1:** accuracy 0.809, equal to always-HIGH, with LOW recall 0.

## 4. News and quarterly information

* **News:** Q-GNB − Q-G +0.0024 [−0.013, +0.017]. Holm fails at leads 1 to 4; placebo share 1.00. **No news claim.**
* **Quarterly updating:** Q-G − Q-frozen −0.012 [−0.038, +0.004]. Not significant, and the +0.009 on development rows points the other way.
* **Independent SWS check:** inherited from E148 and failed (ρ −0.004), because the continuous forecast is identical.

**Threshold does not affect the forecast percentages.** LightGBM learns the continuous value, and the 200 forecast rows match E148 to 1e-16. Only P(HIGH), the classes and the logistic baselines change. Trigger-group contributions are therefore unchanged too, with employment still at 0 %.

## 5. Five provincial forecasts, Q1 2027

| Province | Last survey | Measured | Forecast | 90 % interval | P(HIGH ≥ 50) | Class | Separable from 50 %? |
|---|---|---|---|---|---|---|---|
| Quezon | 2019 | 61.9 | 51.8 | 33.7 to 69.4 | 0.56 | HIGH | No |
| Rizal | 2019 | 56.6 | 50.2 | 32.3 to 68.1 | 0.51 | HIGH | No |
| Batangas | 2021 | 56.9 | 48.3 | 30.7 to 66.4 | 0.44 | LOW | No |
| Cavite | 2021 | 50.2 | 43.6 | 26.8 to 62.1 | 0.29 | LOW | No |
| Laguna | 2018 | 39.3 | 32.6 | 18.6 to 50.5 | 0.06 | LOW | No, narrowly |

**No province is separable from 50 %.** Batangas and Cavite are called LOW even though their latest measurements are above 50 %, and that same downward pull is what misclassified them on 2021. Leads 2 to 4 are in `issue/five_province_forecasts.csv` and move by under 0.2 point.

## 6. 142 LGU rankings

`data/e149/out/issue/lgu_priority_2027-Q1.csv`: priority = P(HIGH ≥ 50) × vulnerability (0.6 poverty percentile, 0.4 density percentile). Top: Plaridel, Pagbilao, Candelaria (Quezon). Median rank by province: Quezon 22, Rizal 57, Batangas 74.5, Cavite 82, Laguna 126.5.

It is a vulnerability-based prioritisation, not a municipal measurement, and it inherits the provincial uncertainty above.

## 7. 60 % against 50 %

| Lead 1, 2021 | E148, 60 % | E149, 50 % |
|---|---|---|
| Share HIGH | 0.40 | 0.80 |
| LightGBM accuracy | 0.76 | 0.80 |
| No-information accuracy | 0.60 | 0.80 |
| Persistence accuracy | 0.56 | **0.88** |
| LOW recall (LightGBM) | 0.60 | 0.40 |
| Balanced accuracy | 0.80 | 0.65 |
| Brier vs persistence | −0.050 [−0.116, +0.005] | −0.014 [−0.053, +0.025] |
| Beats a no-information rule | Yes | **No** |
| Evidence | Untouched | Re-scored, not untouched |

## 8. For the panel

1. **At 50 %, a rule with no model reaches the 75 % target.** The thesis should present accuracy beside always-HIGH and persistence, or examiners may raise it.
2. **Which measure does the panel's 50 % apply to?** This experiment uses any-level food insecurity. On moderate-or-severe, 50 % gives 0 of 13 CALABARZON HFIAS rows HIGH, which would remove all HIGH cases there.
3. **Naming.** FNRI labels 40 to 59.9 % "Medium". A province that is HIGH here may be Medium on FNRI's scale, so the thesis must say this is the panel's threshold.
4. **More models won't fix this.** The limits are the 5 LOW rows in 2021 and the lack of unseen rounds.

## Files

`backend/app/e149/evaluate.py`; `backend/data/e149/out/results.json`, `oof_2021.csv`, `oof_dev.csv`; `issue/five_province_forecasts.csv`; `issue/lgu_priority_2027-Q1.csv`.
