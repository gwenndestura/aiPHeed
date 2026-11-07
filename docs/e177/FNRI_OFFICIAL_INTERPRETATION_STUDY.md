# E177: should aiPHeed interpret its forecasts on FNRI's official scale? (investigation, 2026-11-07)

**Code:** `backend/app/e177/fnri_bands.py`.
**Outputs:** `backend/data/e177/out/{results.json, rows.csv, live_2027.csv}`.
**Production:** no change.

## 1. Evidence: FNRI's official interpretation

Checked directly on DOST-FNRI's **Hunger and Malnutrition Heat Map** (heatmap.fnri.dost.gov.ph, v1.0.0, 2025) on 2026-11-07.

**What FNRI publishes.** "Cut-off values for public health significance (Food Insecure Households)":

| Band | Very Low | Low | Medium | High | Very High |
|---|---|---|---|---|---|
| Share of households | < 20 % | 20–39.9 % | 40–59.9 % | 60–79.9 % | ≥ 80 % |

**What they apply to:**
- **Measure:** the share of households with **any** food insecurity (HFIAS mild + moderate + severe; "Food Insecure Households").
- **Instrument:** HFIAS for 2013, 2015, 2018, 2019 and 2021, per the methodology tab.
- **National level** (2018, 2019 & 2021): 56.3 %, shown as **Medium**.

**FNRI's own values for CALABARZON** (heat-map data):
- **Quezon:** 71.4 % (2013, **High**), 59.7 % (2015, Medium), 61.9 % (2019, **High**).
- **Batangas, Cavite and Rizal:** 50–58 % (Medium).
- **Laguna:** 39.3–55.9 % (Low to Medium).

The convention is the same as WHO's prevalence thresholds for public health significance of child malnutrition (de Onis et al. 2019, *Public Health Nutrition* 22(1):175–179): survey prevalence is read against fixed severity bands to judge how serious a problem is.

## 2. Is the idea justified?

**Yes, in substance.**
- FNRI officially interprets these percentages as **public-health significance**. In FNRI's own terms, CALABARZON is mostly **Medium** and Quezon has been **High**.
- Showing only "LOW" (below the 50 % moderate + severe line) understates what the official source says.

**But not by relabelling or rescaling E168's numbers:**
- FNRI's bands apply to **any** food insecurity. E168 forecasts **moderate + severe**.
- Putting FNRI's band labels on the moderate + severe number would mix two measures. For example, Quezon 2019 at 44 % moderate + severe would wrongly read "Medium" instead of FNRI's "High".

**The credible route is to put the forecast on FNRI's measure first, then apply FNRI's bands.** E168's model, target and 50 % rule are unchanged.

## 3. Method

FNRI publishes both measures for every province and round, so they can be linked directly:

> logit(any food insecurity) = a + b · logit(moderate + severe)

- Fitted **only on rounds published before each forecast's origin** (2013 and 2015 for the 2018 and 2019 forecasts; 2013–2019 for 2021).
- For the live 2027 forecasts, fitted on all five rounds: a = 0.635, b = 0.926, residual SD 0.19 logit.

## 4. Validation

**Data:** 71 past forecasts with FNRI any-level values.

**Comparison:** E168's forecast converted to FNRI's scale, against persistence (the province's latest published FNRI band).

| Lead | Exact FNRI band: E168 | Persistence | Within one band | Mean error (pts): E168 | Persistence | "High or above" alert: accuracy | F1 | recall | Persistence: accuracy / F1 |
|---|---|---|---|---|---|---|---|---|---|
| 1 | **67.6 %** | 57.7 % | 100 % | **6.5** | 10.0 | **74.6 %** | **0.80** | 0.88 | 64.8 % / 0.75 |
| 2 | **67.6 %** | 57.7 % | 100 % | **6.8** | 10.0 | **76.1 %** | **0.81** | 0.88 | 64.8 % / 0.75 |
| 3 | 62.0 % | 57.7 % | 100 % | 7.2 | 10.0 | 70.4 % | 0.76 | 0.83 | 64.8 % / 0.75 |

**Bands in these rows:** High 35, Medium 29, Very High 6, Low 1.

**Reading:**
- On FNRI's own scale, the converted forecast beats reusing the last FNRI measurement at every lead: about 10 points better on the band, 3.5 points less error, better alerts.
- It is never more than one band off.

## 5. What FNRI's scale says for 2027-Q1 (E168 forecasts, converted)

| Province | Moderate + severe (E168) | E168 class (50 % rule) | Any food insecurity (estimated) | 90 % range | **FNRI band** |
|---|---|---|---|---|---|
| Batangas | 25.3 % | LOW | 40.9 % | 33.6–48.7 | **Medium** |
| Cavite | 28.5 % | LOW | 44.6 % | 37.0–52.4 | **Medium** |
| Laguna | 30.2 % | LOW | 46.5 % | 38.8–54.3 | **Medium** |
| Quezon | 36.3 % | LOW | 52.9 % | 45.0–60.6 | **Medium** (upper range reaches High) |
| Rizal | 35.7 % | LOW | 52.3 % | 44.4–60.0 | **Medium** (upper range reaches High) |

So on FNRI's official scale, all five provinces are forecast at **Medium public-health significance**: neither low nor (yet) high. Quezon and Rizal are close enough to High that their 90 % ranges reach it.

## 6. Recommendation

Add FNRI's official interpretation **beside** E168's validated HIGH/LOW. The model, target and the panel's 50 % rule stay as they are.

1. **Every province card and summary shows both:**
   - E168's class;
   - "FNRI public-health significance: Medium (estimated 53 % of households food insecure at any level, 90 % range 45–61 %)".
2. **A separate alert tier, "FNRI High public-health significance",** staged for DA review when the estimated any-level share is ≥ 60 %:
   - It is validated above: 75 % accuracy, F1 0.80 at Lead 1.
   - It is kept distinct from the model's HIGH alert.
   - None would trigger for 2027-Q1. Quezon and Rizal are flagged as approaching it, because their 90 % range reaches 60 %.
3. **Source and limits, stated:**
   - The bands are FNRI's.
   - The any-level value is estimated from E168's forecast through a fitted link to FNRI's own paired data; the 90 % range reflects that.
   - This is an interpretation, not a separately validated model.

**Backend only**, through the existing text fields and alert staging; no design change.

## 7. Owner decision (2026-11-07)

**Not added to the dashboard.** The owner declined the FNRI interpretation layer and the "FNRI High" alert tier. This study stays as research evidence only; the system shows E168's validated HIGH/LOW (50 % rule) unchanged.
