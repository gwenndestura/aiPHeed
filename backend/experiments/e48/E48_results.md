# E48: aligning the model with THESIS_2_14, Chapter 3 (lead 1)

Experiment only; the live system is unchanged.

- **Run:** `runs/20261015T213448Z` (`E48_results.json`, `runner/e48_lib.py`, `runner/e48_run.py`).
- **Procedure:** E36's own walk-forward (`e36_lib.walk_forward`) runs unchanged: 13 test quarters (2023-Q1..2026-Q3, 65 rows), grid G1/G4/G3/G2, seed 36, nested rule, threshold 0.5, baselines. The trigger arm is an extra pool in memory.
- **Trigger proportions:** `e38_lib` shares, i.e. for each province-quarter the share of its attributed news titles that `app/ml/nlp/trigger_classifier.py` tags as market, climate, employment, ofw_remittance or fish_kill (Algorithm 2). They are titles of quarter t, the same window E36's news inputs use.
- **Source:** `THESIS 2 (14).pdf` (Downloads), Chapter 3: pp. 35 and 39–40 (Algorithm 2, trigger proportions), p. 51 (Eq. 3), p. 52 (Table 3.4.2.3, Eq. 5), p. 53 (Table 3.4.2.4), pp. 30, 59 and 65 (model blend, Optuna, release gate).

## Arms

| Arm | Labels | Features |
|---|---|---|
| A0 | current: S1 > **trailing** median of S1 posted before the origin (as served) | E36 (13 inputs) |
| A1 | current | E36 + `trig_market`, `trig_climate`, `trig_employment`, `trig_ofw_remittance`, `trig_fish_kill` |
| B0 | **paper**: S1 > **global median** of S1 over all labelled province-quarters | E36 |
| B1 | paper | E36 + the five trigger proportions |

**About the B arms.** The paper's threshold is a **label-definition choice**: one median over the whole 2021-Q2..2026-Q3 label period (95 province-quarters in the data; τ = **15.47**). It uses outcomes that come after each forecast origin, so the threshold could not have been known at the origin. It is not a model input.

## Labels: current vs paper

| | Current (trailing τ) | Paper (global τ = 15.47) |
|---|---|---|
| HIGH share, all 85 comparable province-quarters | **70.6%** | 52.9% |
| HIGH share, all 95 labelled (paper definition) | – | **49.5%** (the "50/50" holds overall) |
| HIGH on the 65 test rows | 53 (81.5%) | 42 (64.6%) |
| Labels that differ | | **17.6%** (15 of 85) |

| Year | n | Current HIGH | Paper HIGH | Differ |
|---|---|---|---|---|
| 2021 | 5 | 0% | 0% | 0 |
| 2022 | 15 | 47% | 20% | 4 |
| 2023 | 20 | 55% | **10%** | 9 |
| 2024 | 20 | 95% | 85% | 2 |
| 2025 | 10 | 90% | 90% | 0 |
| 2026 | 15 | 93% | 93% | 0 |

The paper's 50/50 balance is balanced only **over the whole period**. Under either definition, 2024–2026 is 85–95% HIGH, because S1 rose above the 2021–2026 median and stayed there.

## Performance (65 test rows; baselines on the same labels)

| Arm / baseline | Labels | Accuracy (95% CI) | Balanced acc. | AUC | Brier |
|---|---|---|---|---|---|
| **A0** E36 | current | 0.815 (0.738–0.892) | 0.822 | 0.850 | 0.154 |
| **A1** E36 + 5 triggers | current | 0.815 (0.708–0.908) | 0.822 | 0.839 | **0.154** |
| always-HIGH | current | 0.815 | 0.500 | 0.500 | 0.185 |
| persistence (B1) | current | 0.877 | 0.860 | 0.860 | 0.123 |
| **B0** E36 | paper | 0.677 (0.492–0.862) | 0.720 | 0.751 | 0.236 |
| **B1** E36 + 5 triggers | paper | 0.677 (0.492–0.862) | 0.720 | 0.738 | 0.243 |
| always-HIGH | paper | 0.646 | 0.500 | 0.500 | 0.354 |
| persistence (B1) | paper | **0.815** | 0.837 | 0.837 | **0.185** |

(The other four baselines are in the JSON.)

| Paired comparison | Brier difference (95% CI) | McNemar p | Quarters better / worse |
|---|---|---|---|
| A1 vs A0 | −0.0003 (−0.018, +0.016) | 1.000 (2 vs 2) | 4 / 4 |
| B1 vs B0 | +0.0070 (−0.0004, +0.021) | 1.000 (0 vs 0) | 2 / 2 |

The Brier difference is the arm minus its baseline, per date (negative favours the arm), with a paired date-cluster bootstrap of 2,000 resamples (seed 20261014).

**Adoption (rule fixed before results).** **A1 acceptable** and **B1 acceptable**: each CI includes 0 and accuracy is unchanged. B1 is non-inferior only to B0; both B arms perform poorly in absolute terms and below persistence.

## Q4 2026 (origin 2026-10-01)

| Arm (chosen setting) | CALABARZON | Cavite | Laguna | Quezon | Rizal | Batangas |
|---|---|---|---|---|---|---|
| A0 (COMB × G2) = served | **0.822** | 0.983 | 0.989 | 0.986 | 0.981 | 0.169 |
| A1 (COMB_T5 × G2) | **0.800** | 0.957 | 0.941 | 0.994 | 0.941 | 0.167 |
| B0 (COMPACT × G4) | **0.811** | 0.857 | 0.857 | 0.857 | 0.857 | 0.624 |
| B1 (COMPACT_T5 × G4) | **0.811** | 0.857 | 0.857 | 0.857 | 0.857 | 0.624 |

**Driver shares, as the paper describes them.** Market = |SHAP| of the price inputs (D_last, Dnow, rice_rel) + trig_market; each other driver = |SHAP| of its trigger proportion; Other = everything else. Shares are summed over the five provinces and add to 100%.

| Arm | Market | Climate | Fish Kill | Employment | OFW | Other |
|---|---|---|---|---|---|---|
| A0 | 38.7% | 0% | 0% | 0% | 0% | 61.3% |
| **A1** | 36.1% | **15.4%** | 0% | 0% | 0% | 48.6% |
| B0 | 20.2% | 0% | 0% | 0% | 0% | 79.8% |
| B1 | 20.2% | 0% | 0% | 0% | 0% | 79.8% |

**Trigger proportions at Q4 2026** (titles of 2026-Q3):
- **Climate:** Cavite 0.16, Laguna 0.23, Quezon 0.03, Rizal 0.25, Batangas 0.03.
- **Fish Kill:** Laguna 0.04, Rizal 0.03.
- **Market:** Batangas 0.01.
- **Employment and OFW:** 0 everywhere.

**Mean |SHAP| per driver over the 65 test rows** (log-odds per row; share of the total in brackets):

| Arm | Market | Climate | Fish Kill | Employment | OFW | Other |
|---|---|---|---|---|---|---|
| A0 | 1.732 (50.1%) | 0 | 0 | 0 | 0 | 1.726 (49.9%) |
| **A1** | 1.782 (45.8%) | **0.238 (6.1%)** | 0 | 0 | 0 | 1.867 (48.0%) |
| B0 | 0.721 (38.1%) | 0 | 0 | 0 | 0 | 1.172 (61.9%) |
| B1 | 0.724 (37.9%) | 0.019 (1.0%) | 0 | 0 | 0 | 1.169 (61.1%) |

**Which triggers get used.** Only **trig_climate** is used by the model. trig_fish_kill, trig_employment and trig_ofw_remittance are never split on: across 2021–2026 the classifier tags 17, 1 and 0 attributed titles in those categories. trig_market is almost always 0, because titles about prices rarely match its patterns.

## Paper alignment (Chapter 3 vs the served system)

| Item | Chapter 3 says | Served system (E36) | Status |
|---|---|---|---|
| Target formula | stress = sws_hunger + 2 × (food_cpi_yoy − regional mean) (Eq. 3) | S1 = H + 2D, D = province food CPI YoY − five-province mean | **MATCHES** |
| Label threshold | median of stress over **all** province-quarter pairs, "guarantees a 50/50 class balance" (Table 3.4.2.3) | **trailing** median of S1 over quarters posted before each origin (no future data); 71% HIGH | **DIFFERS** |
| Label count / period | 120 labelled pairs; 135-row panel, 2020-Q1..2026-Q3 | 95 labelled province-quarters, 2021-Q2..2026-Q3 (no data before 2021) | **DIFFERS** |
| Features | 12 features (Eq. 5): FSSI(t), FSSI(t−1), FSSI(t−2), ΔFSSI, five trigger proportions, CPI_dev, unemployment, rice_change | 13 inputs: H_last, H_gap, H_trend, H_margin, D_last, Dnow, rice_rel, news_n, news_reg, news_direct_share, fssi_v2, fssi_missing, y_last | **DIFFERS** (no trigger proportions, no FSSI lags, no unemployment; adds hunger and last label) |
| Trigger proportions | share of a province-quarter's articles triggering each of five categories, as features (Alg. 2) | not inputs (A1 adds them) | **DIFFERS** (served) / MATCHES (A1) |
| Unemployment | "PSA provincial unemployment rate" | not used; PSA LFS is national only on OpenStat | **DIFFERS** |
| CPI deviation | Eq. 3: from the regional mean; Table 3.4.2.4: "from the rolling provincial mean" (the paper is internally inconsistent) | D = province − five-province mean | **MATCHES Eq. 3** |
| Model | blend: 0.4 Optuna-tuned LightGBM + 0.4 LR (government) + 0.2 LR (triggers); HIGH at blended score ≥ 0.712 | one LightGBM (nested choice over 2 feature sets × 4 settings), threshold 0.5 | **DIFFERS** |
| Tuning | 100-trial Optuna (TPE) on walk-forward F1; blind 4-quarter holdout | nested selection by lowest per-date Brier on earlier dates | **DIFFERS** |
| Validation | walk-forward, expanding window | walk-forward, expanding window, 13 dates | **MATCHES** |
| Lead time | several leads; operational horizon = furthest reliable lead | lead 1 only (AIPHEED_MAX_LEAD = 1) | **DIFFERS** (scope) |
| Explanation | SHAP TreeExplainer on LightGBM | exact TreeSHAP (LightGBM pred_contrib) | **MATCHES** |
| Driver attribution | trigger proportions drive SHAP narratives | Market from price inputs + news inputs split by title topic | **DIFFERS** (approximation) / MATCHES (A1) |
| Release gate | replace the model only if F1 ≥ 0.75 and AUC ≥ 0.80 | not applied; E36 AUC 0.850 | **DIFFERS** |
| Spatial disaggregation | 60% poverty, 40% density, 142 LGUs | same | **MATCHES** |

## Verdict
**A1 (E36 + the paper's five trigger proportions, current labels) best matches the paper and performs acceptably.**
- **Performance:** the same as E36 (accuracy 0.815, Brier 0.154; difference CI −0.018 to +0.016).
- **Paper alignment:** it adds the Eq. 5 trigger features, and its drivers come straight from SHAP of those features, as Algorithm 2 describes.
- **Driver evidence:** only Climate actually carries a share (15% at Q4 2026, 6% over the test rows). Fish Kill, Employment and OFW stay at 0, because their titles barely exist in the corpus.
- **The paper's global-median label (B) is not recommended.** It drops every model to accuracy 0.677, below simple persistence. It doesn't lower the recent index (2024–2026 is still 85–93% HIGH). It also builds future outcomes into the threshold.

**What the manuscript needs.**
1. **Threshold:** describe it as the trailing median of S1 known at each origin (not a global median), and report the realised class balance (71% HIGH, rising to 85–95% after 2024) instead of "guarantees 50/50".
2. **Model and features:** replace Eq. 5, the 12-feature list, the three-model blend, the 0.712 cutoff and the Optuna tuning with what was actually built and evaluated: one LightGBM with E36's inputs (plus the five trigger proportions if A1 is adopted), nested selection, threshold 0.5, lead 1.
3. **Data limits:** say that unemployment is national (no quarterly provincial series), that the data start in 2021-Q2 (95 labelled pairs, not 120), and that Fish Kill, Employment and OFW contribute no explanation because their news titles are almost absent.
4. **CPI deviation:** fix the inconsistency between Eq. 3 and Table 3.4.2.4.
