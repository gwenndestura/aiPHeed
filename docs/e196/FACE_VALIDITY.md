# E196 face-validity check against DOST-FNRI CALABARZON figures (Objective 5) — local only

**Sources.** Script: `backend/app/e196/face_validity.py`. Output: `backend/data/e196/out/face_validity.json`. E196 is not
changed. All forecasts use only information available at their issue date.

## Part A — DOST-FNRI CALABARZON province results, same instrument (HFIAS moderate + severe)

Forecast = E196 back-test forecast of the share of food-insecure households; 90 % = its forecast range.

| Province | Survey | Last survey | **Actual** | E196 L1 (90 % range) | L2 | L3 | Error L1–L3 (pts) | Class |
|---|---|---|---|---|---|---|---|---|
| Quezon | **ENNS/NNS 2019** | 48.8 % | **44.0 %** | 44.3 % (26.9–63.3) | 44.7 % | 45.0 % | 0.3 / 0.7 / 1.0 | LOW = LOW ✓ |
| Rizal | **ENNS/NNS 2019** | 41.3 % | **39.1 %** | 35.6 % (20.3–54.5) | 35.4 % | 35.2 % | 3.5 / 3.7 / 3.9 | LOW = LOW ✓ |
| Laguna | ENNS 2018 | 41.4 % | **26.2 %** | 32.2 % (19.5–48.3) | 32.5 % | 31.8 % | 6.0 / 6.3 / 5.6 | LOW = LOW ✓ |
| Cavite | ENNS 2021 | 41.8 % | **35.5 %** | 28.8 % (18.4–42.0) | 28.0 % | 27.9 % | 6.7 / 7.5 / 7.6 | LOW = LOW ✓ |
| Batangas | ENNS 2021 | 43.5 % | **39.9 %** | 28.6 % (18.3–41.8) | 28.0 % | 27.3 % | 11.3 / 11.9 / 12.6 | LOW = LOW ✓ |

**Summary (15 forecasts):**
- **The 90 % range always contained the published figure:** 15 of 15.
- **HIGH/LOW class correct:** 15 of 15.
- **Mean absolute error:** 5.9 points.
- **NNS 2019 figures:**
  - Quezon was forecast within 1 point.
  - Rizal was forecast within 4 points.
- **Largest error:** Batangas 2021, about 12 points too low. E196 expected a larger decline than happened, but the class
  is still correct (LOW).

## Part B — NNS 2023 (published on the FIES scale)

- **What was run.** E196 as of 2023-Q2 (Lead 1, averaged with the Lead-2 forecast issued at 2023-Q1, target 2023-Q3),
  using only data available then.

| Province | E196 forecast | 90 % range | P(HIGH) | Class |
|---|---|---|---|---|
| Batangas | 28.2 % | 17.7–41.7 | 0.011 | LOW |
| Cavite | 28.0 % | 17.6–41.5 | 0.011 | LOW |
| Laguna | 28.8 % | 18.2–42.5 | 0.014 | LOW |
| Quezon | 32.5 % | 20.9–46.7 | 0.040 | LOW |
| Rizal | 32.2 % | 20.7–46.4 | 0.036 | LOW |
| **CALABARZON (weighted by PSA 2020 population)** | **29.6 %** | | | all LOW |

- **Published NNS 2023 results.**
  - National moderate + severe food insecurity: **31.4 %**.
  - **CALABARZON was the lowest of the 17 regions.** Mindanao Times, citing DOST-FNRI.
  - A regional value of about **19.1 %** (95 % CI 17.0–21.1) appears in DOST-FNRI's regional map. That value could not
    be verified here: the FNRI site blocks automated download.
- **Comparison.** Directionally consistent: E196 places every CALABARZON province well below the HIGH line, with the
  lowest risk class.
- **Instrument caveat.** NNS 2023 uses **FIES**, while E196 forecasts **HFIAS**. HFIAS usually reads higher; for
  example, Quezon in 2019 was 44.0 % on HFIAS against 32.2 % on FIES. So E196's 29.6 % on HFIAS is not contradicted by a
  lower FIES figure, but the two levels cannot be compared directly.

## Conclusion

E196 passes the face-validity check.
- **Against the published DOST-FNRI CALABARZON figures,** including the NNS 2019 values for Quezon and Rizal: every
  forecast range contained the actual value, and every risk class was correct.
- **For 2023:** it correctly places CALABARZON at low risk, matching the NNS 2023 finding that CALABARZON was the
  least food-insecure region.

**Limits.**
- 5 province results (15 forecasts, which are not independent across leads).
- The 2023 comparison is directional because of the FIES/HFIAS difference.
- The exact 2023 regional value should be confirmed from the FNRI publication.
