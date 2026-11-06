# DRAFT data request to DOST-FNRI (for the owner to review and send; not sent)

**To:** DOST-FNRI, Nutritional Assessment and Monitoring Division / data request desk (eNutrition portal or FOI e-FOI request)

**Subject:** Request for provincial HFIAS estimates, 2022 Follow-up Survey of the 2019 ENNS, for thesis research

Dear Sir/Madam,

I am a graduate researcher developing aiPHeed, a provincial food-insecurity early-warning study for the Department of Agriculture Region IV-A (CALABARZON). I am writing to request summary estimates from the **2022 Epidemiologic Follow-up Survey of the 2019 ENNS**, for use in validating forecasts that were fixed and time-stamped before the results were obtained.

**Data requested** (summary tables only; no microdata or personal information):

For each of the 20 survey areas:
- Lanao del Norte, Lanao del Sur, South Cotabato, Kalinga, Davao del Norte, Quirino, Zamboanga Sibugay, Zamboanga del Sur, Marinduque, Rizal, Pampanga, Pangasinan, Benguet, Ilocos Norte, Southern Leyte, Cebu;
- Marikina City, Parañaque City, Malabon City, Puerto Princesa City.

1. Household food-security status based on **HFIAS**, 2022: % food secure, mildly, moderately and severely food insecure.
2. The standard error or 95 % confidence interval for each percentage, and the number of households.
3. If available, the same figures for **2019** for the matched panel households.

**Purpose:** academic thesis research (out-of-sample validation of a forecasting model). Results will be cited to DOST-FNRI and will not be redistributed beyond the thesis.

Thank you very much.

[Name], [Program, University], [contact]

---
**Before sending:**
- This goes beyond the project's public-data-only rule, so sending it is the owner's decision.
- When the data arrive, run:
  `python -m app.e171.score_enns2022 <file.csv>`
  The CSV needs the columns `province,moderate_pct,severe_pct,se_pct,source`, with **every** province included.
