# IMPROVE_V2 results (EXPLORATORY)

**Plan:** `PLAN.md`, sha `2973784a…46ad`, commit `973a6ac`. The runner checked the hash before every stage. Run and seal:
commit `89d109e`. Local commits only; nothing was pushed.

**Evidence status.** Every quarter scored here was already examined in HISTORY_RETRAIN (and 2021–2026 in many earlier
experiments). The three improvements were proposed knowing how the reference behaved there. **Any gain here would be
weak evidence; the only clean test is the sealed 2027+ forecast.**

**Target:** SWS Balance Luzon involuntary hunger > 11.3% (food insecurity). Food prices are inputs only. One row per
quarter; verdict window targets 2010-Q1..2026-Q3, **62 quarters at each lead**, HIGH in 43 (0.694).

Full tables (every rule value, every window): `out/summary.md`; numbers: `out/results.json`; every forecast:
`out/forecasts.csv`; scored rows: `out/rows_lead1.csv`, `out/rows_lead2.csv`.

## 1. Checks (PLAN §9), all passed before scoring

| Check | Result |
|---|---|
| Plan hash; HISTORY_RETRAIN data hashes | equal to the recorded values (`out/checks.json`) |
| 9.1 REF fidelity | REF, LOGIT, PERSIST and CLIM equal HISTORY_RETRAIN's stored forecasts at all 136 (origin, lead) pairs; largest difference 1.1e-16 |
| 9.2 I1 labels | BL rows equal HISTORY_RETRAIN's T2 table; BL labels equal `t2_labels`; every area's label is its own SWS mean; `pi_area(BL)` = `pi_h4l` |
| 9.3 Leakage | at 2005-Q2, 2015-Q3, 2020-Q2, 2021-Q3, 2023-Q4 and 2026-Q2, randomizing everything published on or after the issue date (SWS of all four areas, CPI, production, typhoons, ONI, Pink Sheet, LFS, GDELT, FSSI items, E112 shares) left every row and training label unchanged |
| 9.4 Training rows | t′ < t, q′ ≤ t−1 and label published before O(t), at six origins; Platt pairs and σ errors only from earlier origins with known targets (by construction in code) |
| 9.5 Counts | 62 verdict quarters per lead (≥ 40) |

News columns first exist at: category shares 2021-Q1, N1R 2021-Q3, G_pri_yoy 2022-Q1. They are blank (NaN) before.

## 2. Objective 2 I–IV: every arm and baseline (verdict window, 62 quarters)

HIGH when P ≥ 0.50. "vs REF" and "vs PERSIST" are Brier differences with the one-sided cluster-bootstrap p (seed 2036,
5000 draws) that the model is not lower. NLP-only is scored on the news era only (20 quarters at Lead 1, 19 at Lead 2).

### Lead 1

| Model | Acc | Bal | Prec | Rec | F1 | AUC | Brier | TP/FP/FN/TN | Fails | vs REF | vs PERSIST |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **REF** | **0.790** | 0.717 | 0.812 | 0.907 | 0.857 | 0.702 | **0.188** | 39/9/4/10 | **R7** | — | −0.151 (0.000) |
| I1 pooled areas | 0.758 | 0.679 | 0.792 | 0.884 | 0.835 | 0.712 | 0.185 | 38/10/5/9 | R3, R7 | −0.002 (0.425) | −0.153 (0.000) |
| I2 rate regression | 0.710 | 0.541 | 0.712 | 0.977 | 0.824 | 0.678 | 0.197 | 42/17/1/2 | R2, R3, R7 | +0.010 (0.725) | −0.142 (0.003) |
| I3 Platt | 0.694 | 0.500 | 0.694 | 1.000 | 0.819 | 0.581 | 0.209 | 43/19/0/0 | R2, R3, R7 | +0.021 (0.850) | −0.130 (0.006) |
| ALL | 0.694 | 0.500 | 0.694 | 1.000 | 0.819 | 0.533 | 0.213 | 43/19/0/0 | R2, R3, R5, R7 | +0.026 (0.860) | −0.126 (0.008) |
| REF+news | 0.758 | 0.693 | 0.804 | 0.860 | 0.831 | 0.688 | 0.195 | 37/9/6/10 | R3, R5, R7 | +0.008 (0.820) | −0.143 (0.000) |
| I1+news | 0.742 | 0.667 | 0.787 | 0.860 | 0.822 | 0.706 | 0.187 | 37/10/6/9 | R2, R3, R7 | −0.001 (0.474) | −0.152 (0.000) |
| I2+news | 0.726 | 0.567 | 0.724 | 0.977 | 0.832 | 0.687 | 0.195 | 42/16/1/3 | R2, R3, R7 | +0.007 (0.674) | −0.144 (0.002) |
| I3+news | 0.694 | 0.500 | 0.694 | 1.000 | 0.819 | 0.573 | 0.209 | 43/19/0/0 | R2, R3, R7 | +0.022 (0.854) | −0.130 (0.006) |
| ALL+news | 0.694 | 0.500 | 0.694 | 1.000 | 0.819 | 0.534 | 0.213 | 43/19/0/0 | R2, R3, R5, R7 | +0.025 (0.860) | −0.126 (0.008) |
| PERSIST (latest reading) | 0.661 | 0.594 | 0.750 | 0.767 | 0.759 | 0.594 | 0.339 | 33/11/10/8 | R2–R5, R7 | +0.151 | — |
| LOGIT | 0.710 | 0.629 | 0.766 | 0.837 | 0.800 | 0.759 | 0.193 | 36/11/7/8 | R2, R3, R5, R7 | +0.005 (0.560) | −0.146 (0.001) |
| PSA-only | 0.726 | 0.582 | 0.732 | 0.953 | 0.828 | 0.633 | 0.208 | 41/15/2/4 | R2, R3, R5, R7 | +0.021 (0.744) | −0.130 (0.011) |
| NLP-only (20 q) | 0.450 | 0.478 | 0.625 | 0.385 | 0.476 | 0.390 | 0.353 | 5/3/8/4 | R1–R7 | — | — |
| ALWAYS-HIGH | 0.694 | 0.500 | 0.694 | 1.000 | 0.819 | – | 0.306 | 43/19/0/0 | R2, R3, R5, R7 | +0.119 | −0.032 (0.365) |

### Lead 2

| Model | Acc | Bal | Prec | Rec | F1 | AUC | Brier | TP/FP/FN/TN | Fails | vs REF | vs PERSIST |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **REF** | **0.790** | 0.717 | 0.812 | 0.907 | 0.857 | 0.704 | **0.184** | 39/9/4/10 | **R7** | — | −0.155 (0.000) |
| I1 pooled areas | 0.742 | 0.667 | 0.787 | 0.860 | 0.822 | 0.666 | 0.198 | 37/10/6/9 | R2, R3, R5, R7 | +0.014 (0.838) | −0.140 (0.001) |
| I2 rate regression | 0.742 | 0.579 | 0.729 | 1.000 | 0.843 | 0.710 | 0.188 | 43/16/0/3 | R2, R3, R7 | +0.004 (0.611) | −0.151 (0.001) |
| I3 Platt | 0.677 | 0.488 | 0.689 | 0.977 | 0.808 | 0.682 | 0.197 | 42/19/1/0 | R2, R3, R7 | +0.013 (0.843) | −0.142 (0.001) |
| ALL | 0.694 | 0.500 | 0.694 | 1.000 | 0.819 | 0.606 | 0.215 | 43/19/0/0 | R2, R3, R5, R7 | +0.032 (0.912) | −0.123 (0.011) |
| REF+news | 0.758 | 0.693 | 0.804 | 0.860 | 0.831 | 0.674 | 0.199 | 37/9/6/10 | R3, R5, R7 | +0.015 (0.964) | −0.140 (0.000) |
| I1+news | 0.726 | 0.655 | 0.783 | 0.837 | 0.809 | 0.654 | 0.206 | 36/10/7/9 | R2, R3, R5, R7 | +0.022 (0.937) | −0.133 (0.001) |
| I2+news | 0.726 | 0.567 | 0.724 | 0.977 | 0.832 | 0.712 | 0.188 | 42/16/1/3 | R2, R3, R7 | +0.004 (0.616) | −0.151 (0.001) |
| I3+news | 0.661 | 0.491 | 0.690 | 0.930 | 0.792 | 0.656 | 0.203 | 40/18/3/1 | R2–R5, R7 | +0.019 (0.929) | −0.135 (0.001) |
| ALL+news | 0.694 | 0.500 | 0.694 | 1.000 | 0.819 | 0.599 | 0.218 | 43/19/0/0 | R2, R3, R5, R7 | +0.035 (0.930) | −0.120 (0.012) |
| PERSIST (latest reading) | 0.661 | 0.594 | 0.750 | 0.767 | 0.759 | 0.594 | 0.339 | 33/11/10/8 | R2–R5, R7 | +0.155 | — |
| LOGIT | 0.661 | 0.624 | 0.775 | 0.721 | 0.747 | 0.670 | 0.234 | 31/9/12/10 | R2–R5, R7 | +0.050 (0.921) | −0.105 (0.034) |
| PSA-only | 0.677 | 0.576 | 0.735 | 0.837 | 0.783 | 0.579 | 0.239 | 36/13/7/6 | R2, R3, R5, R7 | +0.055 (0.960) | −0.100 (0.036) |
| NLP-only (19 q) | 0.421 | 0.482 | 0.600 | 0.250 | 0.353 | 0.488 | 0.434 | 3/2/9/5 | R1–R7 | — | — |
| ALWAYS-HIGH | 0.694 | 0.500 | 0.694 | 1.000 | 0.819 | – | 0.306 | 43/19/0/0 | R2, R3, R5, R7 | +0.123 | −0.032 (0.366) |

**Flags.** No LightGBM arm fell back to the training share at any verdict origin. Platt was fitted at every verdict
origin (no skips); I2's σ came from its own past errors at every verdict origin (no σ fallback). NLP-only fell back to
the training HIGH share at 13 of its 20 (Lead 1) and 13 of 19 (Lead 2) quarters, because the news-era training rows
had fewer than 5 LOW quarters; most of its forecasts are therefore a constant, not a news model.

## 3. Objective 2 V: reliability (unchanged R1–R7) and the maximum reliable lead

**No arm passes R1–R7 at either lead. Maximum reliable lead: none (0).**

The closest is still REF, which passes R1–R6 at both leads and fails only **R7** (stability):

| | Lead 1 | Lead 2 |
|---|---|---|
| R1 quarters | 62 ✔ | 62 ✔ |
| R2 accuracy ≥ 0.75 | 0.790 ✔ | 0.790 ✔ |
| R3 balanced ≥ 0.70 | 0.717 ✔ | 0.717 ✔ |
| R4 > always-LOW 0.306 and > persistence 0.661 | ✔ | ✔ |
| R5 Brier < persistence and < CLIM (p < 0.10) | −0.151 (p 0.000); −0.033 (p 0.096) ✔ | −0.155 (0.000); −0.039 (0.070) ✔ |
| R6 precision, recall ≥ 0.60 | 0.812, 0.907 ✔ | 0.812, 0.907 ✔ |
| **R7 each third ≥ 0.60, LOQO ≥ 0.70** | thirds 0.952 / **0.571** / 0.850 ✘ | thirds 0.952 / **0.571** / 0.850 ✘ |

Every improvement made the middle third (about 2015–2020) worse, not better: I1 0.476 (Lead 1) and 0.429 (Lead 2);
I2 0.524; I3 and ALL 0.476 or 0.429. I3 and ALL fail R2 and R3 because Platt pulled the probabilities above 0.5 in
(nearly) every quarter: they say HIGH in all 62 quarters, except I3 at Lead 2 (61 of 62).

## 4. Selection (PLAN §4)

| Lead | Arms passing R1–R7 | Carried forward |
|---|---|---|
| 1 | none | **REF** (HISTORY_RETRAIN LightGBM (b)) |
| 2 | none | **REF** |

## 5. Did any improvement beat the reference? (Brier, verdict window)

| Arm | Lead 1 vs REF | Lead 2 vs REF |
|---|---|---|
| I1 pooled areas | −0.002 (p 0.43): not significant | +0.014: worse |
| I2 rate regression | +0.010: worse | +0.004: worse |
| I3 Platt | +0.021: worse | +0.013: worse |
| ALL | +0.026: worse | +0.032: worse |

Only I1 at Lead 1 had a lower Brier point estimate, by 0.002 (p 0.43), and its accuracy fell from 0.790 to 0.758.
**No improvement beat the reference.** Every arm, with or without news, beat persistence on Brier (p ≤ 0.012).

## 6. Objective 4: the proposed model (REF) against the Chapter I baselines

Brier difference (REF minus comparator), one-sided cluster-bootstrap p, **Holm across the five comparisons at each
lead**. NLP-only on the news-era quarters, the others on all 62.

| Comparator | Lead 1 diff | p | Holm p | Lead 2 diff | p | Holm p |
|---|---|---|---|---|---|---|
| Naive persistence | −0.151 | 0.000 | **0.001** | −0.155 | 0.000 | **0.001** |
| PSA-only | −0.021 | 0.256 | 0.511 | −0.055 | 0.040 | 0.080 |
| NLP-only (20 / 19 q) | −0.153 | 0.002 | **0.008** | −0.227 | 0.003 | **0.014** |
| Logistic regression | −0.005 | 0.440 | 0.511 | −0.050 | 0.079 | 0.080 |
| ALWAYS-HIGH | −0.119 | 0.009 | **0.028** | −0.123 | 0.008 | **0.023** |

REF is significantly better than persistence, NLP-only and ALWAYS-HIGH at both leads after Holm. It is **not**
significantly better than PSA-only or logistic regression at either lead (Holm p 0.08–0.51), although its point
estimate is lower in all four.

## 7. Objective 1: news ablation (with news minus without; positive = news made the forecast worse)

| Arm | Lead 1 full (62 q) | Lead 1 news era (20 q) | Lead 2 full | Lead 2 news era (19 q) |
|---|---|---|---|---|
| REF | +0.008 (p 0.82) | +0.024 | +0.015 (p 0.96) | +0.049 |
| I1 | +0.002 | +0.006 | +0.008 | +0.026 |
| I2 | −0.002 (p 0.11) | −0.007 (p 0.12) | +0.000 | +0.001 |
| I3 | +0.000 | +0.001 | +0.006 | +0.021 |
| ALL | −0.000 | −0.001 | +0.003 | +0.010 |

**News did not improve the forecast.** No arm gained significantly from news (the smallest p is 0.11, I2 at Lead 1,
a 0.002 gain). At Lead 2 news made REF, I1 and I3 worse in the news era. In SHAP the news group is 0.8–4.1% of the
influence. NLP-only alone was the worst model. BERTopic topics were not used as inputs (PLAN §5).

## 8. SHAP group shares (verdict window, % of absolute contributions; `lead` excluded)

| Arm (SHAP of) | Hunger (SWS) | Food and headline prices | Rice | Climate (ONI) | Typhoons | Crops | Fisheries | World prices | News | Area |
|---|---|---|---|---|---|---|---|---|---|---|
| REF, I3 (REF) — Lead 1 | 64.7 | 6.3 | 2.8 | 2.0 | 0.1 | 0.9 | 1.0 | 22.4 | | |
| REF, I3 (REF) — Lead 2 | 64.7 | 6.3 | 2.7 | 2.1 | 0.1 | 0.9 | 0.9 | 22.4 | | |
| I1 — Lead 1 | 52.1 | 5.6 | 1.5 | 4.3 | 0.0 | 0.6 | 1.9 | 32.4 | | 1.7 |
| I2 — Lead 1 (rate points) | 68.6 | 8.5 | 0.9 | 7.4 | 0.0 | 0.5 | 0.3 | 13.7 | | |
| ALL (I1+I2) — Lead 1 | 53.2 | 9.9 | 3.0 | 4.0 | 0.0 | 0.2 | 1.9 | 24.9 | | 3.0 |
| REF+news — Lead 1 | 64.3 | 6.1 | 2.5 | 1.9 | 0.1 | 0.8 | 0.5 | 21.2 | 2.8 | |
| I2+news — Lead 1 | 65.8 | 8.2 | 0.7 | 7.3 | 0.0 | 0.7 | 0.1 | 13.0 | 4.1 | |

All 20 arm × lead rows are in `out/summary.md`. The past SWS readings carry about two thirds of the influence; world
prices about a fifth; CALABARZON food prices 5–10%; typhoons, crops and fisheries almost none. These are relative model
influence, not causes. Not in the inputs: V1 poverty (static, provincial), E1, provincial rice wholesale and E2
remittances (not acquired).

## 9. Secondary windows and known-break sensitivities (no verdict; they never change the selection)

Accuracy (✔ = would pass all of R1–R7 on that window):

| Window | REF L1 | REF L2 | best other arm L1 | best other arm L2 | PERSIST L1 / L2 |
|---|---|---|---|---|---|
| 2010–2022 (48 q) | 0.729 | 0.750 | I1, I2 0.688 | I2 0.729 | 0.604 / 0.646 |
| 2023–2026 (14 q; R1 cannot pass) | 1.000 | 0.929 | I1 1.000 (Brier 0.111) | I1 0.929 (Brier 0.121) | 0.857 / 0.714 |
| News era (20 / 19 q; R1 cannot pass) | 0.850 | 0.842 | I1 0.850 | I1 0.842 | 0.650 / 0.579 |
| **S1** without 2020 phone rounds (60 q) | **0.800 ✔** | **0.817 ✔** | I1 0.767 | REF+news 0.783 ✔ | 0.683 / 0.683 |
| **S2** without 2025-Q2+ adult respondents (56 q) | 0.768 | **0.768 ✔** | I1 0.732 | I1, I2 0.714 | 0.625 / 0.625 |
| **S3** without both (54 q) | 0.778 (fails R7) | **0.796 ✔** | I1 0.741 | I1 0.741 | 0.648 / 0.648 |

Without the 2020 phone-survey quarters, REF would pass every rule at both leads, as HISTORY_RETRAIN also found. This is
a sensitivity only: under the fixed rules the verdict stays "not reliable". None of the improvement arms (I1, I2, I3,
ALL, with or without news) passes in any sensitivity window; REF+news passes only at Lead 2 under S1.

## 10. Objective 3: municipal and city rankings (`out/lgu_rankings.csv`)

For the sealed quarter (2027-Q1, Lead 2, P(HIGH) = 0.860), all 142 LGUs were ranked with the backend's approved method
(`forecaster_v2.lgu_table` → `lgu_poverty.rank_lgus`, read-only, exact ranks): province probability × (0.6 poverty_norm
+ 0.4 density_norm) within each province. Every row is labelled **"priority ranking, not a measured food-insecurity
rate"**.

**The forecast is regional, so all five provinces get the same probability (0.860).** The order inside each province is
therefore set by poverty and density alone; the forecast only scales the score. First in each province: Taytay (Rizal),
Lipa (Batangas), Lucena (Quezon; province-mean poverty substitute), Gen. Mariano Alvarez (Cavite), Siniloan (Laguna).
The backend's known limitation applies: many LGUs carry a province-mean poverty substitute rather than a municipal
estimate.

## 11. Objective 5: what the dashboard would need to show this forecast (no change made)

1. **Target wording:** "Probability that SWS Balance Luzon hunger exceeds 11.3% in quarter q", not a provincial or
   price-based risk.
2. **Regional scope:** one value for the whole region; the province map would show the same colour everywhere, so a
   regional gauge fits better than a choropleth.
3. **Horizon status:** "Not reliable at Lead 1 or Lead 2 (fails the stability rule R7)", with the issue date and the
   newest SWS round used.
4. **Driver bars:** SHAP group shares (§8), labelled "relative model influence, not causes", with the excluded families
   listed.
5. **News status:** news is shown as context only; it did not improve the forecast.
6. **LGU table:** the §10 ranking with its label and the poverty-substitute flag.
7. **Seal status:** the sealed 2027-Q1 forecast, its SHA-256, and its score once SWS publishes 2027-Q1.

## 12. Seal (PLAN §10)

| Item | Value |
|---|---|
| File | `sealed_prospective_IMPROVE_V2.csv`, SHA-256 `94c6259670d0605b1c944deaf75a4671d3063f853445badbb46567f5db0c2477` (`SEAL_LEDGER.md`) |
| Forecast | Issue date 2026-10-01 (origin 2026-Q3), **Lead 2, target 2027-Q1**, arm **REF**, **P(HIGH) = 0.860 → HIGH** |
| Inputs | Newest SWS reading 17.3% (published 2026-08-24) |
| Persistence on the same date | HIGH (P = 1) |
| Not yet issuable | Lead 1 for 2027-Q1: issue date 2027-01-01. `runner/seal_next.py 2027-01-01` writes it to a new file and appends it to the ledger. It refuses before that date, refuses an issue date already sealed, and never overwrites a file. |
| Scoring | `runner/score_seal.py` checks every ledger hash, then scores targets whose SWS rounds are published. Today it reports the hash OK and 2027-Q1 pending. |

## 13. Departures from the plan

1. **Seal before RESULTS.md text.** PLAN §10 says the seal comes after RESULTS.md. The seal was written after scoring
   (`results.json`, which fixes the selection) but before this prose. The sealed forecast depends only on the selection,
   so its content is the same either way.
2. **A guard added to `seal_next.py`.** While testing its refusal paths, `seal_next.py 2026-10-01` was started. That
   date was already sealed under the main file name, so the script did not refuse. It was stopped before writing
   anything: no file was created, the ledger was unchanged and the sealed file's hash still matched. A refusal for
   issue dates already in the ledger was then added. No forecast changed.
3. **Ranking call.** The plan names `rank_lgus`; it was called through the backend's own wrapper
   `forecaster_v2.lgu_table` (which builds its inputs from `lgu_vulnerability.csv` and calls `rank_lgus`), with
   `exact_ranks=True` so that 4-decimal display rounding does not create artificial ties.

Nothing else departed from the plan. The served model, `backend/`, the dashboard, the frontend, PREREG_LEAD2, its
addenda, HISTORY_RETRAIN and every existing seal are unchanged.

## 14. Verdict in plain words, objective by objective

| Objective | Status | Evidence |
|---|---|---|
| **1 NLP** | **Partially achieved** | The news indicators (regional FSSI-v3, GDELT, six news categories) were built, cut at the issue date and put into every arm. **They did not improve the forecast**: no significant gain in any arm, worse at Lead 2, and the news-only model was the worst. BERTopic topics were not used. |
| **2 I–IV** | **Achieved (reported)** | Accuracy, precision, recall, F1, AUC and Brier for every arm at both leads (§2). The proposed model (REF): accuracy 0.790, precision 0.812, recall 0.907, F1 0.857, AUC 0.70, Brier 0.188 / 0.184. The 75% accuracy target is reached on the 62-quarter window. |
| **2 V** | **Method achieved; result: no reliable lead** | Walk-forward with an expanding window, unchanged R1–R7, counted in quarters. Nothing passes at Lead 1 or Lead 2. REF fails only R7: it was right 95% of the time in 2010–2015 but only 57% in about 2015–2020. |
| **3** | **Partially achieved** | 142 LGUs ranked by the approved method and labelled as rankings. But the forecast is not validated (no lead passes), and because it is regional the order comes from poverty and density only. |
| **4** | **Achieved (comparison done); superiority only partly** | All five comparisons on the same quarters with Holm (§6). Better than persistence, NLP-only and always-HIGH; not significantly better than PSA-only or logistic regression. |
| **5** | **Not done here, by design** | No dashboard change; §11 lists what would be needed. ISO 25010 and FNRI validation remain outside this experiment. |

**Did any improvement beat the reference and persistence?** Every improvement beat persistence, but **none beat the
reference**. Pooling the four SWS areas tied with it at Lead 1 and was worse at Lead 2. The rate regression and Platt
calibration were worse at both leads. News did not help.

**Is any lead reliable for food-insecurity forecasting?** **No.** The best model is right about 79% of the time over
2010–2026 at both leads and clearly beats copying the latest survey. But it fails the stability rule: in about
2015–2020 it was right only 57% of the time. Without the 2020 phone-survey quarters it would pass, but that is a
sensitivity, not the rule.

**Which model was sealed, and what must happen in 2027 for it to count?** The reference model (HISTORY_RETRAIN
LightGBM (b)), because no arm passed. Its Lead-2 forecast for 2027-Q1 is **HIGH, P = 0.86** (hash `94c62596…`).
- In 2027, SWS must publish its 2027-Q1 Balance Luzon readings.
- `score_seal.py` then confirms the hash and scores the forecast.
- Lead-1 forecasts must be issued on each quarter's issue date (`seal_next.py 2027-01-01`, then 2027-04-01, and so on).

One quarter proves nothing: in 2027-Q1 the latest-reading rule also says HIGH. The forecast counts as evidence only
after **at least 10 sealed quarters** are scored (R1) and it beats persistence on them. Even then it supports a
reliable forecast only if it also passes R2–R7 on those sealed quarters.
