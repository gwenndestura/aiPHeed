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
