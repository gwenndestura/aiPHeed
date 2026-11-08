# E137 SARF: results and gate decision (2026-11-03)

**Protocol.** E137-P1 (`PROTOCOL.md`), locked 2026-11-03 14:20 UTC before any fit on real outcomes
(`backend/data/e137/out/PROTOCOL_LOCK.json`). It was run once; the lock was verified at the start of the run.

**Results files.**
* `backend/data/e137/out/results.json`
* `oof_predictions.csv`
* `external_s11.json`

**Registry.** `e137-sarf-1.0` is **REJECTED**. Production stays `null`. The dashboard is unchanged.

All figures below are **development evidence**. ENNS rows were examined in hfias-1.0 (owner decision D-3), so no
result here is a confirmatory test.

## 1. Headline

| Question | Answer from the locked run |
|---|---|
| Can indicators estimate food-insecurity **risk** where surveys are missing? | **Yes, at the structural (between-province) level.** Out-of-region AUC for measured elevated vs lower relative HFIAS is 0.78–0.84 (LightGBM) and 0.85 (poverty-only logistic). Regional agreement with PSA FIES 2023: Spearman 0.79 (LightGBM), 0.82 (poverty-only), 0.86 (latest HFIAS position). |
| Does LightGBM add value over simpler approaches? | **No.** Its expected Brier score (0.205–0.231) never beats the 3-variable poverty logistic (0.212) with confidence. It does not beat persistence of the previous survey on ENNS rows (0.206–0.238 vs 0.195). It overfits: training 0.14 vs cross-validation 0.21–0.23. |
| Maximum reliable lead | **None.** No lead passes S1, S5, S6 or S7. |
| Contributor dominance | **None.** Mean group share: poverty 0.42–0.49, climate 0.31–0.43, market 0.15–0.21. The median largest share is 0.52–0.55, below the 0.80 limit. |
| Employment and news groups | Not learnable nationally: there is no provincial labour series before 2021, and the news archive is CALABARZON-only. Layer T (regional timing) gave LightGBM no passing lead in FI6, so neither group enters the risk score. |

## 2. Formulation choice (frozen rule)

At Lead 0, V1 expected Brier was 0.2256 for REL and 0.2357 for SOFT. SOFT was not lower by more than 0.005, so
**REL** (continuous relative-risk regression) was chosen. SOFT is reported as the "other formulation": it is worse
at every lead (0.220–0.236).

## 3. V1: leave-one-region-out, primary outcome (moderate-or-severe, pooled reference)

Expected Brier score (lower is better). AUC, BA, recall and precision are on decisive rows (40 ELEVATED, 22 LOWER).

| Lead | LGBM EB | AUC [95 % CI] | BA | Recall | Precision | ECE | Train EB | B0 EB | B2 PSA-only EB / AUC | B3 logistic EB / AUC |
|---|---|---|---|---|---|---|---|---|---|---|
| 0 | 0.226 | 0.776 [0.57, 0.93] | 0.708 | 0.825 | 0.786 | 0.111 | 0.146 | 0.258 | 0.212 / 0.851 | 0.228 / 0.843 |
| 1 | 0.231 | 0.768 [0.57, 0.91] | 0.720 | 0.850 | 0.791 | 0.105 | 0.150 | 0.258 | 0.212 / 0.851 | 0.235 / 0.834 |
| 2 | 0.216 | 0.807 [0.66, 0.95] | 0.728 | 0.775 | 0.816 | 0.067 | 0.145 | 0.258 | 0.212 / 0.851 | 0.226 / 0.832 |
| 3 | 0.205 | 0.842 [0.72, 0.96] | 0.753 | 0.825 | 0.825 | 0.078 | 0.141 | 0.258 | 0.212 / 0.851 | 0.210 / 0.860 |
| 4 | 0.206 | 0.825 [0.67, 0.98] | 0.776 | 0.825 | 0.846 | 0.060 | 0.141 | 0.258 | 0.212 / 0.851 | 0.213 / 0.843 |

**Confusion matrix (TP / FP / TN / FN):**
* Lead 0: 33 / 9 / 13 / 7.
* Lead 4: 33 / 6 / 16 / 7.

**95 % cluster-bootstrap CI of EB(LGBM) − EB(baseline):**

| Lead | vs B0 base rate | vs B2 PSA-only | vs B1 persistence |
|---|---|---|---|
| 0 | [−0.082, +0.015] | [−0.019, +0.052] | [−0.051, +0.123] |
| 3 | [−0.101, −0.010] | [−0.034, +0.016] | [−0.072, +0.099] |

**ENNS rows: previous-survey persistence (B1) vs LightGBM.**

| Model | EB | AUC |
|---|---|---|
| B1 persistence | 0.195 | 0.766 |
| LightGBM (with anchor) | 0.206–0.238 | 0.64–0.75 |

**Why AUC rises with lead.** The poverty and structural features are the same at every lead. Only the quarterly
inputs differ: CPI, production, rainfall and cyclones. A higher AUC at longer leads is therefore not forecasting
skill. It shows that the recent quarterly inputs add noise rather than signal for a between-province risk target.

## 4. V2: train on 2015, predict ENNS 2018/2019 (out-of-round transfer)

| Lead | LGBM EB / AUC / BA | B1 persistence EB / AUC | B2 PSA-only EB / AUC |
|---|---|---|---|
| 0 | 0.238 / 0.686 / 0.685 | 0.194 / 0.769 | 0.188 / 0.846 |
| 2 | 0.191 / 0.809 / 0.745 | 0.194 / 0.769 | 0.188 / 0.846 |
| 4 | 0.212 / 0.766 / 0.683 | 0.194 / 0.769 | 0.188 / 0.846 |

## 5. Sensitivity (S9) and external agreement (S11)

* **Any-level outcome:** V1 AUC 0.83–0.85.
* **Round-printed reference:** V1 AUC 0.82–0.89.

  In both cases the conclusion is unchanged.
* **S11, FIES 2023 (16 regions; features as of 2023-07-01, Lead 0, population-weighted):**

  | Score | Spearman | p |
  |---|---|---|
  | LightGBM | 0.786 | 0.0003 |
  | PSA-only | 0.823 | < 0.001 |
  | Latest HFIAS position | 0.855 | < 0.001 |

  S11 passes. FIES is a different instrument, so this is agreement, not accuracy.

## 6. Gate result (Lead 0, the shortest horizon)

| Check | Result |
|---|---|
| S1 beats baselines with confidence | **fail** (every lead) |
| S2 AUC ≥ 0.70, lower bound ≥ 0.60 | **fail** at Leads 0–1 (lower bound 0.57); pass at Leads 2–4 |
| S3 class performance | pass (every lead) |
| S4 ECE ≤ 0.10 | **fail** at Leads 0–1 (0.111, 0.105); pass at Leads 2–4 |
| S5 island stability | **fail**. Only Luzon has ≥ 3 decisive rows of each class (AUC 0.62–0.70). Visayas and Mindanao are not evaluable, so this is partly a data-volume limitation. |
| S6 overfitting gap ≤ 0.05 | **fail** (0.065–0.081) |
| S7 beats persistence on ENNS rows | **fail** (every lead) |
| S8 out-of-round AUC ≥ 0.65 | pass |
| S9 sensitivity | pass |
| S10 no dominance | pass |
| S11 external agreement | pass |
| S12 confirmatory | not evaluable (no unseen round) |

Even if S5 were set aside as a data-volume artefact, S1, S6 and S7 fail at every lead. **Decision: REJECTED; no
reliable lead; nothing is promoted or shown on the dashboard.**

## 7. Interpretation for the research question

1. **The data-scarcity problem is partly solvable.** Public PSA indicators, mostly poverty, subsistence and poverty
   gap, identify which provinces have measured household food insecurity above the national level, in regions the
   model never saw (AUC ≈ 0.85). They also agree with FIES 2023 regional rankings. This is genuine,
   non-circular evidence: the label is measured HFIAS and the predictors are separate statistics.
2. **The signal is structural.**
   * The previous survey position alone is as informative as any model (persistence B1).
   * Quarterly market and climate inputs do not improve between-province risk.
   * No measured outcome exists to test within-province quarterly change, so a quarterly "rise in risk" cannot be
     validated.
3. **LightGBM is not justified at this sample size** (125 rows, 62 decisive). The inner search chose stumps most
   often, and the model still overfits. A 3-variable logistic regression does as well or better.
4. **CALABARZON.** All five provinces are below or not distinguishable from the national level in every measured
   round.
   * Illustrative 2023-Q3 scores (S11 run, not served): LightGBM gives Quezon 0.68, Cavite 0.58, Rizal 0.25,
     Laguna 0.20, Batangas 0.06. The poverty-only model gives Quezon 0.42 and the others 0.16–0.22.
   * Cavite's 0.58 contradicts its measured history (LOWER in 2015). It is an example of the LightGBM instability
     that the gate caught.

## 8. Files added or changed

* **New code:** `backend/app/e137/` (`__init__`, `acquire`, `outcomes`, `features`, `model`, `evaluate`, `external`,
  `gate`).
* **New tests:** `backend/tests/unit/test_e137.py` (10 tests).
* **New data:** `backend/data/e137/`.
  * `raw/`: PSA, NASA POWER and IBTrACS files, plus MANIFEST.csv with sha256.
  * The IBTrACS CSV (115 MB) is gitignored; re-download it with `acquire ibtracs`.
  * `out/`: the lock and results.
* **New docs:** `docs/e137/PROTOCOL.md`, `OUTCOME_AUDIT.md`, this file.
* **Changed:** `backend/app/registry/catalog.py` (adds the `e137-sarf-1.0` entry) and
  `backend/data/registry/registry.json` (registered, then rejected).
* **Unchanged:** production model, public routes, frontend.
