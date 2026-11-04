# C-B6P results (2026-11-04): province-quarter C-B6 with employment and OFW remittances

**Pre-registration:** `PREREGISTRATION.md` (e6405536…). **Scripts:** `runner/cb6p_model.py fit|score`.
**Outputs:** `out/cb6p_fits.csv`, `out/cb6p_labels.csv`, `out/cb6p_checks.json`, `out/cb6p_results.json`.

**Result: does not pass the pre-registered acceptance. Not served; C-B6 (regional) stays the main model.**

## Label

- Eq. 3 province-quarter labels: 100 (20 quarters x 5 provinces, 2021-Q1..2026-Q3).
- THR = 11.0 (2021-22 median). HIGH share 0.75.
- Leakage check passed.

## Metrics (100 province-quarters per lead)

| Lead 1 / Lead 2 | **C-B6P** | C-B6P-noE | C-B6-R (regional) | PERSIST | LOGIT |
|---|---|---|---|---|---|
| Accuracy | **0.780 / 0.720** | 0.810 / 0.750 | 0.770 / 0.730 | 0.830 / 0.780 | 0.730 / 0.690 |
| F1 | 0.845 / 0.803 | 0.869 / 0.828 | 0.841 / 0.814 | 0.886 / 0.849 | 0.811 / 0.789 |
| AUC-ROC | 0.783 / 0.671 | 0.774 / 0.681 | 0.691 / 0.601 | 0.780 / 0.733 | 0.767 / 0.636 |
| Brier | 0.159 / 0.189 | 0.157 / 0.184 | 0.187 / 0.211 | 0.170 / 0.220 | 0.164 / 0.197 |
| Algorithm 3 (max lead) | 1 | 2 | 1 | 2 | 0 |

## Findings

1. **Acceptance fails:**
   - Lead 2 accuracy is 0.72, below the required 0.75.
   - Lead 1 AUC is 0.78, below 0.80.
   - It is not better than PERSIST or LOGIT.
2. **Employment and OFW remittances do not help.** C-B6P is slightly worse than C-B6P-noE:
   - Brier +0.002 / +0.005;
   - accuracy −0.03 at both leads;
   - 3 calls changed;
   - SHAP share: employment 0.4%, OFW 2.2%.
3. **Brier is better than regional C-B6** at Lead 1 (Holm p 0.035), because the province price deviation adds information
   (SHAP 12.6%).
4. **Provinces almost never differ:** the five provinces get different calls in only 3 of 20 quarters. The Eq. 3 label
   is driven by regional SWS hunger (SHAP 47.5%), so the forecast is still mostly regional.
5. **Short history:** 20 labelled quarters. Persistence is hard to beat.

## C-B6P2 (PREREGISTRATION_P2.md 93ec374b…): + the province's last known Eq. 3 score (S_last, y_last)

**Script:** `runner/cb6p2_model.py`. The C-B6P replication is exact (1.1e-16). Leakage check passed.

| Lead 1 / Lead 2 | **C-B6P2** | C-B6P | PERSIST |
|---|---|---|---|
| Accuracy | **0.810 / 0.750** | 0.780 / 0.720 | 0.830 / 0.780 |
| F1 | 0.869 / 0.828 | 0.845 / 0.803 | 0.886 / 0.849 |
| AUC-ROC | 0.787 / 0.676 | 0.783 / 0.671 | 0.780 / 0.733 |
| Brier | 0.158 / 0.187 | 0.159 / 0.189 | 0.170 / 0.220 |
| Algorithm 3 | **2** | 1 | 2 |

- **Accuracy rises:** +0.03 at both leads. Lead 2 reaches the 75% rule, so the maximum reliable lead is now 2.
- **Brier gain is not significant:** −0.0012 (p 0.24) and −0.0016 (p 0.14).
- **The pre-registered acceptance therefore fails** (Brier p < 0.10 at both leads was required).
- **Against regional C-B6:** better Brier at both leads (Holm p 0.017 and 0.032).
- **Against PERSIST and LOGIT:** not better.
- **Employment and OFW stay in;** SHAP shares are 0.4% and 2.3%.

## C-B6P3 (PREREGISTRATION_P3.md 18e01504…, owner directive): every driver forced into every forecast

**Script:** `runner/cb6p3_model.py`. **Model:** an L2 logistic base on the 15 driver inputs, with C-B6P2's LightGBM
boosting on top.

| Lead 1 / Lead 2 | **C-B6P3** | C-B6P2 |
|---|---|---|
| Accuracy | **0.690 / 0.620** | 0.810 / 0.750 |
| F1 | 0.760 / 0.716 | 0.869 / 0.828 |
| AUC-ROC | 0.730 / 0.531 | 0.787 / 0.676 |
| Brier | 0.212 / 0.264 | 0.158 / 0.187 |
| Algorithm 3 | **0** | 2 |

- **The directive is met:** all five drivers contribute to 100% of forecasts. SHAP shares:
  - market 31%;
  - fish kill 16%;
  - employment 11–14%;
  - climate 5%;
  - OFW 4%.
- **Forecast quality falls sharply:**
  - accuracy −0.12 / −0.13;
  - Brier +0.054 / +0.077 (Lead 2 CI excludes 0).
- **Acceptance therefore fails** (criteria 2 and 3).
- **Interpretation:** forcing employment, fish kill and the others into every forecast adds noise. In C-B6P2 they had
  little or no weight because they do not predict the Eq. 3 label on this data.

## C-B6P4 (PREREGISTRATION_P4.md 96582102…, owner directive): C-B6P3 with the logistic C chosen on inner folds

**Script:** `runner/cb6p4_model.py`. **Chosen C per origin:** 0.001 (15), 0.01 (2), 0.1 (2), 1.0 (8).

| Lead 1 / Lead 2 | **C-B6P4** | C-B6P3 | C-B6P2 |
|---|---|---|---|
| Accuracy | **0.720 / 0.650** | 0.690 / 0.620 | 0.810 / 0.750 |
| F1 | 0.788 / 0.745 | 0.760 / 0.716 | 0.869 / 0.828 |
| AUC-ROC | 0.725 / 0.553 | 0.730 / 0.531 | 0.787 / 0.676 |
| Brier | 0.194 / 0.240 | 0.212 / 0.264 | 0.158 / 0.187 |

- **All five drivers contribute** in 100% of forecasts. SHAP shares: market 29%, fish kill 10%, employment 9–11%,
  climate 4%, OFW 3%.
- **It improves on C-B6P3** (+0.03 accuracy).
- **It is still well below C-B6P2:** Brier +0.036 / +0.053. Acceptance fails.
- **The trailing-8 driver view** (an average over the latest 8 forecasts) was also checked for C-B6P2. It still leaves fish
  kill at 0 in 15 of 85 rows and employment in 5.
- **Conclusion:** on this data, forcing every driver into every forecast costs 0.09–0.12 accuracy whichever way it is
  done.
