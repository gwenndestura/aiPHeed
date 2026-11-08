# aiPHeed final system: E168 LightGBM (approved 2026-11-07)

## Model
**E168 LightGBM-only** forecasts provincial **HFIAS moderate + severe household food insecurity**. A province is HIGH at 50 % or more. It has three parts:
1. **Survey baseline:** the latest measured provincial HFIAS, carried forward under one of three anchoring rules.
2. **Constrained LightGBM:** predicts the change, using the five trigger groups (market, climate, employment, remittances, poverty) with news inside the groups. It uses 3 leaves, strong regularisation and monotone signs.
3. **Calibration layer:** chosen on training data only.

Every choice is made by nested, region-grouped selection on training rows. Leakage test: 0.0 change.

## Acceptance (owner-defined, 2026-11-07)
A lead is served when the model is:
- **at least 75 % accurate**; and
- **significantly better than reusing the latest survey** (Brier difference 95 % CI below 0).

Both are measured on the 72 chronological, as-of forecasts (ENNS 2018, 2019, 2021).

**Registry gate:** `data/registry/gate_results/e168-lgbm-1.0.json`. All 7 checks pass.

## Accuracy by lead (72 forecasts; 50 at Leads 7–8)
| Quarters ahead | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 |
|---|---|---|---|---|---|---|---|---|
| **E168 accuracy** | **75.0 %** | **77.8 %** | **75.0 %** | 73.6 % | 72.2 % | 69.4 % | 70.0 % | 66.0 % |
| Latest survey alone | 62.5 % | 62.5 % | 62.5 % | 62.5 % | 62.5 % | 62.5 % | 64.0 % | 64.0 % |
| HIGH recall | 0.88 | 0.88 | 0.84 | 0.80 | 0.80 | 0.80 | 0.88 | 0.94 |
| Better than latest survey (95 % CI) | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ |

**Horizons:**
- **Lead time meeting the acceptance (≥ 75 % and better than the latest survey): 3 quarters.**
- **Skill horizon** (better than the latest survey): 6 quarters.

**Leads 1–3 are statistically equal** (McNemar p = 0.63 for Leads 1 vs 2). They use the same latest survey, which is released with a 6-quarter lag. Accuracy falls after Lead 3.

## Forecast served (issued 2026-Q4)
| Province | 2027-Q1 | 90 % range | P(HIGH) | Class |
|---|---|---|---|---|
| Batangas | 25.3 % | 15.8–38.1 | 0.003 | LOW |
| Cavite | 28.5 % | 18.0–41.9 | 0.009 | LOW |
| Laguna | 30.2 % | 19.3–44.0 | 0.016 | LOW |
| Quezon | 36.3 % | 23.9–50.8 | 0.076 | LOW |
| Rizal | 35.7 % | 23.5–50.2 | 0.068 | LOW |

2027-Q2 and 2027-Q3 are within 0.4 points of these values. Quezon and Rizal are the highest-risk provinces.

## Limits (stated in the thesis)
- **Validation size.** The validation uses 72 forecasts from 3 survey rounds.
  - Lead-1 accuracy of 75.0 % has a plausible range of about 65–85 %.
  - Under the stricter E156 test (C1–C6), the maximum reliable lead is 0 quarters. This is disclosed in the gate record.
- **The provincial trigger inputs add no demonstrated province-specific information** beyond timing; real inputs did not beat shuffled ones.
- **Employment and remittance data are national only.**
- **Sealed validation:** forecasts for the 2022 provincial round are sealed (`f8228fae`), so the claim can be checked when FNRI publishes provincial results.

## Where it is served
- `GET /api/v1/final/food-insecurity/outlook` (status `approved`, Leads 1–3).
- The dashboard's approved-model card renders the forecast summary. No UI changes.

**Code:**
- `backend/app/e168/serve.py`
- `backend/app/e168/owner_gate.py`
- `backend/app/e168/longer_leads.py`
