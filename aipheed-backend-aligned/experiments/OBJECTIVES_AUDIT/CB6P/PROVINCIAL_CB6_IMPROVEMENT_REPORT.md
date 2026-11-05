# Provincial C-B6 improvement report (2026-11-04)

**Branch:** `aiPHeed/cb6-final` (local). **Status:** development evidence. Nothing is served, deployed, pushed or committed
by this run. The original C-B6 and every earlier result are unchanged.

**Bottom line.**
- **The new decomposed model, C-B6D-E, is the most genuinely provincial candidate:**
  - its calls differ across provinces in 10 of 20 quarters, the same as the labels;
  - it has the best Lead 1 Brier of every model (0.154).
- **It does not significantly beat C-B6P2 or persistence.**
- **It fails R4 and R5 at both leads, and also R7 at Lead 2.** It meets the paper's accuracy and F1 targets, but not AUC
  ≥ 0.80.
- **Employment and OFW remittances are real inputs, but their predictive value is not significant.**
- **The available provincial data (20 quarters) cannot yet support a reliable province-quarter forecast.**

## 1. Equation 3 target: verified

Checked on `out/cb6p_labels.csv`:

| Check | Result |
|---|---|
| D sums to 0 across the five provinces each quarter | max 1.6e-15 |
| S = H + 2D | max error 3.6e-15 |
| THR = median of S over the 30 province-quarters of 2021–22 (leak-free) | 11.0, recomputed |
| Labelled province-quarters | 100 (20 quarters × 5) |
| Share HIGH | 0.75 |
| Quarters in which the provinces' labels differ | **10 of 20** |

- **H is measured:** SWS Balance Luzon regional hunger. No provincial hunger measurement exists, and none is fabricated.
- **The provincial part is modelled:** 2D, from PSA provincial food CPI.
- **The label is therefore a modelled provincial food-insecurity proxy (Eq. 3), not measured provincial hunger.**

## 2. Why the earlier provincial models failed

| Model | Problem |
|---|---|
| E99 (Ch. III as written) | All-period median (leaks the future); 19 quarters; regime switch; accuracy 0.30 |
| C-B6P / C-B6P2 | Trees learn mostly from the 1998–2020 regional rows, where D is missing. The calls differ across provinces in only 3–4 quarters, though the labels differ in 10. Persistence (0.83 / 0.78) is not beaten |
| C-B6P3 / C-B6P4 | Forcing every driver into every forecast adds noise: accuracy 0.69 / 0.62 and 0.72 / 0.65 |

**Common cause:** 20 provincial quarters, with labels that persist (a label changes in 14.7% of quarter-to-quarter
steps), so persistence is a hard baseline.

## 3. New candidate: C-B6D, the decomposed Eq. 3 model

**Pre-registration:** `PREREGISTRATION_D.md` (PLAN-SHA256 c67db29d…), fixed before any fit. **Script:**
`runner/cb6d_model.py`.

- **Regional part:** the probability that BL hunger > 11.3%, from the validated walk-forward regional model.
  - **C-B6D-E** uses C-B6E, which includes **employment E1 and OFW remittances E2**, news (FSSI anomaly), prices,
    climate, production and rice stocks.
  - This is converted to a hunger distribution using the past forecast-error SD.
- **Province part:** the forecast deviation D̂ = b·D1, the province's latest known food-price deviation. The slope is
  fitted on past pairs only, all provinces pooled.
- **Combination as Eq. 3:** P(HIGH) = Φ((μ_H + 2D̂ − 11.0) / √(σ_H² + 4σ_D²)).
- **Leakage:**
  - every input and every slope uses only data published before the issue date;
  - provinces are pooled only on past pairs (no same-quarter cross-province leakage);
  - static poverty (published 2024) is excluded from the forecast for this reason.

## 4. Results (100 province-quarters per lead; identical rows per comparison)

### Lead 1

| Model | Acc | Bal | Prec | Rec | F1 | AUC | Brier | Acc in mixed quarters | Quarters with differing calls | R1–R7 failed |
|---|---|---|---|---|---|---|---|---|---|---|
| **C-B6D-E** | 0.800 | 0.747 | 0.877 | 0.853 | 0.865 | 0.777 | **0.154** | 0.68 | **10** | R4, R5 |
| C-B6D (no E1/E2) | 0.790 | 0.740 | 0.875 | 0.840 | 0.857 | 0.754 | 0.158 | 0.66 | 10 | R4, R5 |
| C-B6D-EX (+ headline) | 0.820 | 0.773 | 0.890 | 0.867 | 0.878 | 0.773 | 0.154 | 0.70 | 10 | R4, R5 |
| C-B6P2 | 0.810 | 0.780 | 0.900 | 0.840 | 0.869 | 0.787 | 0.158 | 0.64 | 4 | R4, R5, R7 |
| C-B6-R (regional C-B6) | 0.770 | 0.727 | 0.871 | 0.813 | 0.841 | 0.691 | 0.187 | 0.54 | 0 | R4, R5, R7 |
| PSA-only-P | 0.780 | 0.733 | 0.873 | 0.827 | 0.849 | 0.803 | 0.166 | 0.78 | 9 | R4, R5 |
| NLP-only-P | 0.470 | 0.527 | 0.775 | 0.413 | 0.539 | 0.427 | 0.329 | 0.44 | 0 | R2–R7 |
| PERSIST | 0.830 | 0.780 | 0.892 | 0.880 | 0.886 | 0.780 | 0.170 | 0.70 | 10 | R4, R5 (vs itself) |
| LOGIT | 0.730 | 0.687 | 0.853 | 0.773 | 0.811 | 0.767 | 0.164 | 0.70 | 6 | R2–R5 |

### Lead 2

| Model | Acc | Bal | F1 | AUC | Brier | Acc in mixed quarters | Quarters with differing calls | R1–R7 failed |
|---|---|---|---|---|---|---|---|---|
| **C-B6D-E** | 0.770 | 0.700 | 0.846 | 0.667 | 0.191 | 0.58 | 7 | R4, R5, R7 |
| C-B6D | 0.740 | 0.680 | 0.822 | 0.652 | 0.195 | 0.54 | 8 | R2–R5, R7 |
| C-B6D-EX | 0.730 | 0.647 | 0.819 | 0.649 | 0.196 | 0.52 | 7 | R2–R5, R7 |
| C-B6P2 | 0.750 | 0.700 | 0.828 | 0.676 | 0.187 | 0.54 | 4 | R4, R5, R7 |
| C-B6-R | 0.730 | 0.673 | 0.814 | 0.601 | 0.211 | 0.46 | 0 | R2–R5, R7 |
| PSA-only-P | 0.530 | 0.540 | 0.624 | 0.536 | 0.296 | 0.52 | 7 | R2–R7 |
| NLP-only-P (n = 95) | 0.379 | 0.489 | 0.379 | 0.520 | 0.446 | 0.42 | 0 | R2–R7 |
| PERSIST | 0.780 | 0.733 | 0.849 | 0.733 | 0.220 | 0.64 | 11 | R4, R5 |
| LOGIT | 0.690 | 0.607 | 0.789 | 0.636 | 0.197 | 0.62 | 7 | R2–R5, R7 |

**Algorithm 3 (maximum reliable lead):** C-B6D-E 2, C-B6P2 2, PERSIST 2, C-B6D 1, C-B6D-EX 1, C-B6-R 1, LOGIT 0.

### Paired Brier, C-B6D-E minus the comparator (Holm over 12; cluster bootstrap by quarter)

| Comparator | Lead 1 diff (p, Holm) | Lead 2 diff (p, Holm) |
|---|---|---|
| PERSIST | −0.016 (0.27, 1.00) | −0.029 (0.17, 1.00) |
| LOGIT | −0.010 (0.38, 1.00) | −0.006 (0.44, 1.00) |
| PSA-only-P | −0.012 (0.37, 1.00) | **−0.105 (0.001, 0.010)** |
| NLP-only-P | **−0.176 (<0.001, 0.002)** | **−0.252 (<0.001, <0.001)** |
| C-B6P2 | −0.004 (0.38, 1.00) | +0.004 (0.66, 1.00) |
| C-B6-R (regional) | −0.034 (0.006, 0.052) | −0.020 (0.025, 0.20) |

### Pre-registered decisions

| Rule | Result |
|---|---|
| Improves on C-B6P2 (Brier p < 0.10 at both leads, accuracy ≥ C-B6P2) | **No** |
| Meets the paper targets (acc and F1 ≥ 0.75 at both leads, AUC ≥ 0.80 at Lead 1) | **No**: accuracy and F1 yes; AUC 0.777 |
| Reliable under R1–R7 | **No** at either lead |
| Employment/OFW have predictive value (C-B6D-E vs C-B6D, p < 0.10 at both leads) | **No**: −0.0044 (p 0.16), −0.0042 (p 0.13) |
| Province headline deviation adds value (EX vs E) | **No** |

## 5. Feature contributions (C-B6D-E; share of each forecast's probit index, mean)

| Driver | Lead 1 | Lead 2 | Forecasts where it contributes |
|---|---|---|---|
| Past SWS hunger | 36.7% | 42.6% | 100% |
| Province food-price deviation | 33.1% | 23.8% | 79% / 72% |
| Market and prices | 21.3% | 24.4% | 100% |
| Rice stocks | 3.1% | 3.3% | 62% |
| News (FSSI) | 3.1% | 3.1% | 17% |
| Climate | 1.1% | 1.2% | 62% |
| Fish kill | 0.8% | 0.8% | 42% |
| **Employment** | 0.3% | 0.3% | 54% |
| **OFW remittances** | 0.3% | 0.3% | 42% |

- **Employment and OFW are genuine inputs.** They contribute in about half the forecasts, with small weight, and they
  improve Brier slightly (by 0.004) but not significantly.
- **No SHAP value is forced.**

## 6. Objective completion status

| Objective | Status | Evidence / blocker |
|---|---|---|
| 1 NLP | **Not completed: blocked** | `annotation/labels_annotator_A.csv` and `_B.csv` contain **0 of 300** labels. Agreement (kappa), XLM-R validation and FSSI validation need the two annotators' labels. The BERTopic temporal evaluation exists (`FINAL_2026-11-04/BERTOPIC_TEMPORAL_VALIDATION.md`) |
| 2 Provincial LightGBM / lead time | **Evaluated; reliability not achieved** | Best accuracy 0.80–0.82 at Lead 1 and 0.75–0.77 at Lead 2. AUC < 0.80. R4/R5 fail (persistence). Algorithm 3: 2 quarters (C-B6D-E, C-B6P2) |
| 3 Province / 142 LGUs | **Implemented; not validated** | Poverty-weight rank vs Eq. 3 HIGH frequency over 5 provinces: Spearman ρ −0.30 (p 0.62). Quezon has the highest weight but the fewest HIGH quarters (0.55); Rizal the most (0.95). No LGU-level outcome data exists to validate the 142 rankings |
| 4 Baselines | **Comparison complete on identical rows** | Significantly better than NLP-only (both leads) and PSA-only (Lead 2). Not better than persistence or logistic regression |
| 5 Dashboard / alerts / ISO 25010 | **Backend verified; evaluation not done** | 34/34 backend tests pass (`test_foodinsecurity_mode`, `test_cb6_auto`, `test_cb6_auto_api`). No DA personnel ISO/IEC 25010 responses exist yet |

## 7. Limitations

- **Hunger is regional:** H is Balance Luzon, not CALABARZON or a province.
- **Short history:** only 20 provincial quarters (PSA provincial CPI yearly changes from 2021). Every result is
  development evidence on quarters that were already examined.
- **Persistence is strong:** provincial labels change in only 14.7% of steps.
- **The regional-to-hunger conversion assumes a normal error,** with the pooled past SD.
- **Static socioeconomic indicators are excluded from forecasting:** they were published after most origins (leakage).

## 8. Exact data needed for a reliable provincial forecast

1. **A provincial food-insecurity measurement** at least yearly, ideally quarterly, to replace the Eq. 3 proxy:
   - PSA FIES provincial food-insecurity estimates (FIES/SDG 2.1.2), or
   - DOST-FNRI ENNS provincial food-insecurity prevalence, or
   - an SWS provincial oversample for CALABARZON.
2. **A longer provincial CPI history:** PSA provincial CPI on earlier bases (2012 = 100, then 2018 = 100), linked to the
   current series. This would extend D, and the Eq. 3 labels, back by about 8 years (about 30 more quarters × 5
   provinces).
3. **Provincial labour data:** PSA LFS provincial or regional unemployment, which OpenSTAT does not publish as a quarterly
   table (PDF releases only). This would make E1 provincial instead of national.
4. **Provincial or regional OFW remittances:** BSP publishes national figures only. The PSA Survey on Overseas Filipinos
   gives regional figures yearly.
5. **Prospective quarters:** sealing C-B6D-E and C-B6P2 from 2027-01-01 gives untouched test data, 4 quarters × 5
   provinces per year.

## Files

| File | Contents |
|---|---|
| `PREREGISTRATION_D.md` | C-B6D pre-registration |
| `runner/cb6d_model.py` | C-B6D script |
| `out/cb6d_fits.csv` | forecasts of every arm |
| `out/cb6d_contrib.csv` | C-B6D-E contributions |
| `out/cb6d_results.json` | metrics, R1–R7, Holm, decisions |
| Earlier files | `PREREGISTRATION.md`, `_P2`, `_P3`, `_P4`, `RESULTS.md`, `runner/cb6p*_model.py` (unchanged) |

---

# Update (2026-11-04): FI-FOCUS. Food-insecurity focus and extended provincial history

**Pre-registration:** `PREREGISTRATION_FI.md` (PLAN-SHA256 2109fecd…), fixed before any fit.
**Scripts:** `runner/fi_regional.py`, `runner/fi_provincial.py`.
**Outputs:** `out/fi_regional_*`, `out/fi_provincial_*`, `out/fi_labels_ext.csv`.
**New data:** `data/raw/` (PSA OpenSTAT provincial CPI, `FETCH_LOG.json` with SHA-256).

## A. Is the forecast driven by food insecurity or by price? (regional; outcome = measured SWS hunger > 11.3%; 62 quarters)

| Lead 1 / Lead 2 | FULL (C-B6E) | NP: no price inputs | PO: prices only | HO: hunger only |
|---|---|---|---|---|
| Accuracy | **0.790 / 0.790** | 0.726 / 0.758 | 0.661 / 0.597 | 0.726 / 0.774 |
| AUC-ROC | 0.698 / 0.720 | 0.717 / 0.737 | 0.530 / 0.490 | 0.686 / 0.703 |
| Brier | 0.192 / 0.184 | 0.198 / 0.187 | 0.229 / 0.244 | 0.199 / 0.188 |
| Algorithm 3 | **2** | 0 | 0 | 0 |

**Paired Brier comparisons:**
- **FULL vs price-only: −0.037 (p 0.024) / −0.059 (p 0.001). A1 holds:** non-price inputs significantly improve the
  forecast of measured food insecurity.
- **FULL vs no-price:** −0.006 (p 0.35) / −0.003 (p 0.46). A2 fails: prices add no significant value beyond the
  non-price inputs.
- **NP vs hunger-only:** −0.001 (p 0.42 / 0.43). A3 fails: climate, crops, fisheries, rice stocks, employment, OFW and news
  add no significant value beyond hunger history.

**SHAP share in FULL:**
- hunger history 58%;
- prices 31%;
- other non-price inputs 11%.

**Conclusion:**
- The regional forecast **is a food-insecurity forecast**: hunger history drives it, and a price-only model fails
  (accuracy 0.60–0.66, AUC about 0.5).
- It does not over-rely on price.
- The other drivers do not yet add significant skill beyond hunger history.

## B. Extended provincial history (Eq. 3 labels 2013–2026)

**Labels:**
- 250 province-quarters (50 quarters, 2013-Q1..2026-Q3); HIGH share 0.70.
- THR 11.0 unchanged.
- The 100 earlier labels are reproduced exactly (D max difference 7.8e-16).

### B-ext results (250 rows per lead)

| Lead 1 | Acc | Bal | Prec | Rec | F1 | AUC | Brier | R1–R7 |
|---|---|---|---|---|---|---|---|---|
| **C-B6D-E-X** | **0.772** | 0.711 | 0.821 | 0.863 | 0.841 | 0.739 | **0.181** | **all pass** |
| NP-P-X (no price) | 0.720 | 0.678 | 0.811 | 0.783 | 0.797 | 0.758 | 0.183 | fails R2, R3, R7 |
| PO-P-X (price only) | 0.740 | 0.658 | 0.786 | 0.863 | 0.823 | 0.679 | 0.196 | fails R2, R3, R5 |
| C-B6-R (regional) | 0.752 | 0.705 | 0.823 | 0.823 | 0.823 | 0.709 | 0.194 | fails R5 |
| PERSIST-X | 0.708 | 0.666 | 0.804 | 0.771 | 0.787 | 0.666 | 0.292 | fails R2–R5, R7 |
| CLIM-X | 0.700 | 0.500 | 0.700 | 1.000 | 0.824 | 0.523 | 0.221 | fails R2–R5, R7 |

| Lead 2 | Acc | Bal | F1 | AUC | Brier | R1–R7 |
|---|---|---|---|---|---|---|
| **C-B6D-E-X** | 0.736 | 0.674 | 0.815 | 0.711 | **0.193** | fails R2, R3 |
| NP-P-X | 0.688 | 0.659 | 0.766 | 0.713 | 0.197 | fails R2–R5, R7 |
| PO-P-X | 0.640 | 0.526 | 0.759 | 0.553 | 0.228 | fails R2–R5, R7 |
| C-B6-R | 0.736 | 0.686 | 0.811 | 0.691 | 0.198 | fails R2, R3, R5 |
| PERSIST-X | 0.692 | 0.650 | 0.774 | 0.650 | 0.308 | fails R2–R5, R7 |

**Algorithm 3 (B-ext):** C-B6D-E-X reaches **1 quarter** (accuracy by lead: 0.772, 0.736, 0.682, …); every other arm
reaches 0.

### Holm family (10 tests, C-B6D-E-X minus the comparator)

- **Significant:** vs PERSIST-X at both leads (−0.111 and −0.115, Holm p < 0.001).
- **Not significant after Holm:**
  - vs CLIM-X: −0.040 / −0.031;
  - vs C-B6-R: −0.014 / −0.005;
  - vs PO-P-X: −0.016 / −0.035 (raw p 0.020 at Lead 2);
  - vs NP-P-X: −0.002 / −0.003.

### B-old: the same 100 rows as before (2021+)

| Lead 1 / Lead 2 | C-B6D-E-X | C-B6D-E | C-B6P2 |
|---|---|---|---|
| Accuracy | **0.840** / 0.760 | 0.800 / 0.770 | 0.810 / 0.750 |
| Brier | **0.151** / 0.187 | 0.154 / 0.191 | 0.158 / 0.187 |

- **X vs C-B6D-E:** −0.003 (p 0.15) / −0.004 (p 0.18). **B1 fails** (not significant).

### Hunger part vs price part (C-B6D-E-X, B-ext)

| | Lead 1 | Lead 2 |
|---|---|---|
| **Hunger part:** correct quarterly calls vs measured BL hunger > 11.0 (50 quarters) | 0.74 | 0.74 |
| **Price part:** sign accuracy of D̂ vs the realised D | 0.70 | 0.61 |
| Price part: correlation of D̂ with D | 0.60 | 0.36 |
| Contribution: hunger history | 39.6% | 45.9% |
| Contribution: regional prices | 22.8% | 26.5% |
| Contribution: province price | 28.1% | 16.9% |
| Contribution: employment | 1.9% | 2.2% |
| Contribution: OFW | 1.0% | 1.2% |
| Contribution: other non-price | 6.5% | 7.3% |
| **Price total** | **50.9%** | **43.5%** |

**Interpretation:**
- At the provincial level, about half of each forecast comes from price terms. This is by construction: Eq. 3's
  provincial part is a price deviation.
- The provincial model's skill is **not** price skill alone: the price-only arm is worse (Lead 2 accuracy 0.640 vs
  0.736). But B3 (non-price significantly better) is not proven after Holm.
- **The claim that is supported:** C-B6D-E-X forecasts the Eq. 3 provincial food-insecurity **risk** proxy. Its hunger
  component is measured regional hunger, and its provincial differences come from food prices.

## Caveats

- **The 2013–2020 extension is not untouched data:** the regional fits for those quarters were examined during regional
  development. The provincial labels before 2021 are new.
- **The CPI is spliced** across a base change (2012 = 100 to 2019-01, then 2018 = 100). Current vintage.
- **Wide AUC 95% CIs:** C-B6D-E-X 0.616–0.861 at Lead 1 and 0.584–0.815 at Lead 2. AUC ≥ 0.80 is not reached.

---

# Update (2026-11-04): Lead 2 improvement attempt, C-B6D-E-X2

**Pre-registration:** `PREREGISTRATION_X2.md` (PLAN-SHA256 f4bf89d0…). **Script:** `runner/x2_model.py`.
**Outputs:** `out/x2_fits.csv`, `out/x2_contrib.csv`, `out/x2_results.json`. C-B6D-E-X is reproduced exactly (0.0).

## Why Lead 2 fails R2/R3 (diagnosis before the plan)

- **The hunger part is the bottleneck.**
  - In 67% of C-B6D-E-X's Lead 2 errors, the regional hunger call is wrong.
  - With the true regional hunger in its place (diagnostic oracle), Lead 2 accuracy would be **0.888**, not 0.736.
  - The two-quarter-ahead regional hunger forecast calls measured BL hunger > 11.0 correctly in 0.74 of the 50 quarters.
- **The price part weakens at Lead 2:** D̂–D correlation 0.36, against 0.60 at Lead 1.

## Arms tested (B-ext, 250 province-quarters, 2013–2026)

| Lead 1 | Acc | Bal | F1 | AUC [95% CI] | Brier | R1–R7 failed |
|---|---|---|---|---|---|---|
| C-B6D-E-X (reference) | **0.772** | 0.711 | 0.841 | 0.739 [0.62, 0.86] | 0.181 | none |
| X-ENS (4-model hunger combination) | 0.752 | 0.697 | 0.825 | 0.756 [0.64, 0.87] | **0.177** | R3 |
| X-FE (province mean reversion of D) | 0.764 | 0.706 | 0.835 | 0.737 [0.61, 0.86] | 0.181 | none |
| X-CAL (walk-forward Platt) | 0.708 | 0.616 | 0.802 | 0.677 [0.56, 0.79] | 0.219 | R2–R5, R7 |
| **X2 (ENS + FE + CAL, primary)** | 0.712 | 0.638 | 0.800 | 0.688 [0.58, 0.79] | 0.212 | R2, R3, R5, R7 |
| PSA-only-P-X | 0.716 | 0.580 | 0.819 | 0.664 [0.56, 0.77] | 0.203 | R2, R3, R5, R7 |

| Lead 2 | Acc | Bal | F1 | AUC [95% CI] | Brier | R1–R7 failed |
|---|---|---|---|---|---|---|
| C-B6D-E-X | **0.736** | 0.674 | 0.815 | 0.711 [0.58, 0.82] | 0.193 | R2, R3 |
| X-ENS | 0.700 | 0.656 | 0.781 | 0.716 [0.58, 0.83] | **0.191** | R2, R3, R7 |
| X-FE | 0.740 | 0.677 | 0.818 | 0.705 [0.58, 0.81] | 0.194 | R2, R3 |
| X-CAL | 0.680 | 0.570 | 0.787 | 0.620 [0.50, 0.74] | 0.217 | R2–R5, R7 |
| **X2** | 0.664 | 0.566 | 0.772 | 0.618 [0.49, 0.74] | 0.218 | R2–R5, R7 |
| PSA-only-P-X | 0.624 | 0.522 | 0.743 | 0.584 [0.47, 0.70] | 0.247 | R2–R5, R7 |
| C-B6-R | 0.736 | 0.686 | 0.811 | 0.691 [0.56, 0.80] | 0.198 | R2, R3, R5 |
| PERSIST-X | 0.692 | 0.650 | 0.774 | 0.650 [0.57, 0.73] | 0.308 | R2–R5, R7 |

**Ablations vs C-B6D-E-X (Brier):**

| Arm | Lead 1 | Lead 2 |
|---|---|---|
| ENS | −0.003 (p 0.32) | −0.003 (p 0.30) |
| FE | +0.000 | +0.000 |
| CAL | **+0.038 (p 0.99)** | **+0.024 (p 0.995)** |

**Why calibration hurt:**
- The Platt map is fitted on past forecasts, mostly from 2013–2020, when hunger was lower (66.7% HIGH, against 75% in
  2021–26).
- It therefore shrinks probabilities in the later high-hunger regime and adds false negatives.
- This is non-stationarity, not a code defect.

**Holm family (12):**
- **Significant:** X2 is better than PERSIST-X only (both leads).
- **Not significant:** vs C-B6D-E-X, CLIM-X, C-B6-R, PSA-only-P-X and X-ENS.

**B-old (2021+, 100 rows): X2 is worse than C-B6D-E-X** at both leads (Lead 1 acc 0.800 vs 0.840; Lead 2 0.680 vs
0.760).

## Pre-registered decisions

| Decision | Result |
|---|---|
| Lead 2 fixed (R1–R7) | **No** |
| Lead 1 preserved | **No** (X2 Lead 1 acc 0.712) |
| Improvement over C-B6D-E-X at Lead 2 | **No** |
| Hunger share ≥ 30% | Yes (X2: 50% / 57%) |

**C-B6D-E-X remains the best provincial model.** Per the plan, no further variant is fitted on these data.

## Why Lead 2 cannot currently be fixed

- **Lead 2 is bounded by the two-quarter-ahead regional hunger forecast.**
- Every regional model available is about 0.72–0.79 accurate on measured hunger at Lead 2: C-B6E, C-B6, no-price,
  hunger-only, and their combination.
- No legitimate change to the price part or the calibration lifts that ceiling.
- **Lifting it needs earlier or more frequent hunger information:**
  - SWS rounds published sooner, or monthly;
  - a provincial or regional food-insecurity survey (FIES);
  - leading indicators with demonstrated two-quarter skill, which none of the tested employment, OFW, climate,
    production or news inputs showed.

## Untouched test data: prospective seal

- **Sealed:** `out/seal_prospective_X2.csv`, SHA-256 `2c1ff50aee70b3f7e759d17f120cd7f83efcd9d6c327529149079a84e7647b8f`.
- **What it holds:** C-B6D-E-X and X2, issued 2026-10-01, for 2026-Q4 (Lead 1) and 2027-Q1 (Lead 2), 5 provinces each,
  written before either outcome exists.
- **This is the only genuinely untouched test data.** All 2013–2026 results above were examined during development.


---

# Update (2026-11-04): paper-aligned Lead 2 attempt, C-B6D-E-XH

**Pre-registration:** `PREREGISTRATION_XH.md` (PLAN-SHA256 2b32270c…).
**Script:** `runner/xh_model.py`.
**Outputs:**
- `out/xh_features.csv`, `out/xh_checks.json`;
- `out/xh_regional_fits.csv`, `out/xh_provincial_fits.csv`;
- `out/xh_logit_baselines.csv`, `out/xh_results.json`;
- `out/seal_prospective_XH.csv` (SHA-256 1709044f…).

## Paper alignment

- **Only variables the thesis names:** H1 momentum (two-reading change, acceleration), "run above or below 11.3", "other
  SWS areas", and N1 FSSI momentum (Ch. I "temporal momentum features"; Ch. III H1/N1 families).
- **Unchanged:** Eq. 3, the 11.0 cut-off and the objectives.
- **Baselines now match Ch. I RQ3:**
  - persistence;
  - logistic regression × 3 (combined, government-only, NLP-only), new provincial versions;
  - the LightGBM government-only ablation (PSA-only-P-X).
- **Disclosed:** the paper's Eq. 3 cut-off is the all-period median. 11.0 is its leak-free 2021–22 version and still
  needs adviser approval.
- **Leakage check passed:** the features are unchanged when every SWS round published on or after O(t) is removed.
- **Reproduction:** C-B6E and C-B6D-E-X are reproduced exactly.

## Regional hunger component (measured BL hunger > 11.3%, 62 quarters)

| | Lead 1 C-B6E | Lead 1 **C-B6E-H** | Lead 2 C-B6E | Lead 2 **C-B6E-H** |
|---|---|---|---|---|
| Accuracy | 0.790 | 0.790 | 0.790 | 0.774 |
| Balanced accuracy | 0.717 | 0.731 | 0.717 | 0.720 |
| AUC | 0.698 | **0.735** | 0.720 | 0.712 |
| Brier | 0.192 | **0.179** | 0.184 | 0.184 |
| R1–R7 failed | R5, R7 | R7 | R7 | R7 |

- **Momentum improves the one-quarter hunger forecast:** Brier −0.013, p 0.031.
- **It does not improve the two-quarter forecast:** −0.0004, p 0.46.
- **The new features carry about 25% of SHAP.**

## Provincial Eq. 3 forecast (B-ext, 250 province-quarters, 2013–2026)

| Lead 1 | Acc | Bal | F1 | AUC [95% CI] | Brier | R1–R7 failed |
|---|---|---|---|---|---|---|
| **C-B6D-E-XH** | 0.764 | **0.721** | 0.831 | **0.767** [0.66, 0.87] | **0.173** | **none** |
| C-B6D-E-X | **0.772** | 0.711 | 0.841 | 0.739 [0.62, 0.86] | 0.181 | none |
| LOGIT-GOV-P | 0.732 | 0.660 | 0.814 | 0.727 | 0.200 | R2, R3, R5, R7 |
| LOGIT-COMB-P | 0.700 | 0.633 | 0.789 | 0.683 | 0.231 | R2–R5, R7 |
| PSA-only-P-X | 0.716 | 0.580 | 0.819 | 0.664 | 0.203 | R2, R3, R5, R7 |
| C-B6-R | 0.752 | 0.705 | 0.823 | 0.709 | 0.194 | R5 |
| PERSIST-X | 0.708 | 0.666 | 0.787 | 0.666 | 0.292 | R2–R5, R7 |

| Lead 2 | Acc | Bal | F1 | AUC [95% CI] | Brier | R1–R7 failed |
|---|---|---|---|---|---|---|
| **C-B6D-E-XH** | 0.708 | 0.666 | 0.787 | 0.714 [0.59, 0.81] | **0.192** | R2, R3 |
| C-B6D-E-X | **0.736** | **0.674** | 0.815 | 0.711 [0.58, 0.82] | 0.193 | R2, R3 |
| LOGIT-GOV-P | 0.656 | 0.583 | 0.757 | 0.606 | 0.260 | R2–R5, R7 |
| LOGIT-COMB-P | 0.640 | 0.571 | 0.743 | 0.629 | 0.268 | R2–R5, R7 |
| PSA-only-P-X | 0.624 | 0.522 | 0.743 | 0.584 | 0.247 | R2–R5, R7 |
| C-B6-R | 0.736 | 0.686 | 0.811 | 0.691 | 0.198 | R2, R3, R5 |
| PERSIST-X | 0.692 | 0.650 | 0.774 | 0.650 | 0.308 | R2–R5, R7 |

**LOGIT-NLP-P (news era only, 100 rows):** Lead 1 accuracy 0.570, Lead 2 0.700; AUC 0.45 / 0.58.

**B-old (2021+, 100 rows):**

| | XH | C-B6D-E-X | C-B6D-E | C-B6P2 | PERSIST |
|---|---|---|---|---|---|
| Lead 1 accuracy | **0.860** | 0.840 | 0.800 | 0.810 | 0.830 |
| Lead 1 AUC | **0.835** | 0.778 | 0.777 | 0.787 | 0.793 |
| Lead 1 Brier | **0.140** | 0.151 | 0.154 | 0.158 | 0.170 |
| Lead 2 accuracy | 0.740 | 0.760 | 0.770 | 0.750 | 0.800 |

**Holm family (14):**

| XH vs | Lead 1 | Lead 2 |
|---|---|---|
| PERSIST-X | **significant** (Holm < 0.001) | **significant** (Holm < 0.001) |
| LOGIT-NLP-P | **significant** (Holm 0.004) | n.s. |
| LOGIT-COMB-P | n.s. (Holm 0.18) | **significant** (Holm 0.014) |
| LOGIT-GOV-P | n.s. | **significant** (Holm < 0.001) |
| C-B6D-E-X | n.s. (−0.008, Holm 0.56) | n.s. (−0.001) |
| CLIM-X | n.s. | n.s. |
| PSA-only-P-X | n.s. | n.s. |

**Algorithm 3:** 1 quarter (both models).

## Pre-registered decisions

| Decision | Result |
|---|---|
| Lead 2 R1–R7 | **No** (accuracy 0.708, balanced 0.666) |
| Lead 1 preserved | Yes (R1–R7 pass, accuracy 0.764) |
| Improvement over C-B6D-E-X at Lead 2 | **No** |
| Adopt | **No** |

**C-B6D-E-X stays the provincial candidate.**
- XH is a better Lead 1 probability model (AUC 0.767 vs 0.739; Brier 0.173 vs 0.181; regional hunger Brier p 0.031), but
  the pre-registered rule required a Lead 2 fix.
- **Both are sealed for the prospective test.**

## Conclusion on Lead 2 (all attempts: X2 and XH)

- **Every paper-supported construction fails to lift the two-quarter-ahead hunger component:** forecast combination,
  hunger momentum, the threshold run, other SWS areas and FSSI momentum.
- Lead 2 hunger skill stays at about 0.72–0.79 on measured hunger. The provincial Lead 2 forecast therefore stays below
  R2 (0.75) and R3 (0.70).
- **With the paper's variables and the available data, a reliable two-quarter-ahead provincial forecast is not
  supported.** The paper's Algorithm 3 result is 1 quarter.
- **What could change it is data, not modelling:**
  - more frequent or earlier hunger readings (FIES / SWS);
  - prospective quarters from 2027.

---

# Update (2026-11-05): province-specific non-price evidence

**Full write-up:** `PROVINCIAL_NONPRICE_EVIDENCE.md`. **Pre-registration:** `PREREGISTRATION_PV.md` (632f495d…).

- **C-B6D-E-XA** (C-B6D-E-X + province crop and fisheries shocks):
  - Lead 1 accuracy 0.772, AUC 0.736, Brier 0.181, R1–R7 pass;
  - Lead 2 accuracy 0.728, fails R2/R3;
  - no significant gain over C-B6D-E-X (coefficients about 0.01);
  - **not adopted**.
- **Independent check against PSA provincial subsistence and poverty incidence (2018, 2021, 2023):**
  - Eq. 3's provincial term: mean ρ +0.09 (p 0.39) and −0.25 (p 0.80);
  - C-B6D-E-X: +0.20 (p 0.25) and −0.08 (p 0.61);
  - **consistency is not shown.**
- **Conclusion:** the provincial differentiation is food-price pressure by construction of Eq. 3. Changing that needs an
  adviser decision on Eq. 3 and provincial food-insecurity data.
