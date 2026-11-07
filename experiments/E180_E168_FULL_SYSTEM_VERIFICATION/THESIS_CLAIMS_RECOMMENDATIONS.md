# Thesis claims: correct, qualify, remove

## Correct before submission
1. **F01, CRITICAL:** production must serve E168 (merge into main, change AIPHEED_LEAD2_MODEL on Render; verify the live indicator).
2. **F02:** driver shares = Σ|SHAP| of group / Σ|SHAP| of all features, plus otherPct, summing to 100.
3. **F03 / F04 / F10 / F11:** frontend label, Landing/About text, "Fish Kill" → "Fish production", back-forecasts not shown as "actual".
4. **F05:** add the 300-headline annotations with kappa and classifier metrics, or state the NLP labels are unvalidated.

## Qualify
- "Reliable forecasting": reliable to Lead 3 by Algorithm 3 (>= 75 %); strict C1-C6 at Lead 1; Lead 2 passes 5 of 6 (C1 fails:
  0.6405 vs 0.6528 at n_eff 45.5).
- "Provincial quarterly forecasts": validated at province-survey-round level (2018-2021); quarters between surveys are model output.
- "Employment / OFW remittance drivers": national series shared across provinces.
- Driver attributions: associations in the model, not causes.
- LGU values: vulnerability-weighted rankings of the province forecast (Algorithm 5).
- Evaluation: the 72 rows were reused across experiments; only E168's pre-registered result is held-out evidence.
- F1 0.742 is below the 0.75 target.

## Remove
- Any SWS Balance Luzon / price-pressure description of the target.
- "Fish kill" as a model driver.
- "Validated NLP classifier" (until annotations are added).
- Any claim that SIMPLE (or E172 / E179 candidates) outperforms E168.
- "Live / deployed E168" until F01 is fixed.

## Preserve (verified correct)
E168 code and locked results; HFIAS moderate+severe target; sealed forecast 28f2c918; leakage controls; `app/e156/leads.py`;
Algorithm 5 LGU ranking; map join; thresholds 0.50 / 0.60 / 5 articles; additive SHAP computation in history.
