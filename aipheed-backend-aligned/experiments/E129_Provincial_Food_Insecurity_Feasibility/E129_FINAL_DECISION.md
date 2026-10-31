# E129 final decision

## Classification: **PROVINCIAL TARGET NOT READY**

**No defensible provincial food-insecurity target can be established today.**
- No official source measures food insecurity separately for the five provinces **repeatedly over time**.
- The only provincial food-insecurity measurements are cross-sections:

  | Source | Coverage | Held? |
  |---|---|---|
  | FNRI ENNS 2021 | 2 of 5 provinces | Held |
  | FNRI ENNS 2022 | Coverage unverified | Not held |
  | CBMS 2024 FIES | All LGUs, one window | Not held |

**Missing**
- A repeated provincial food-insecurity series: at least 10 periods per province.
- Or SWS microdata with province codes plus an approved pooling and estimation design.
- Or future CBMS / ENNS rounds.

**Required**
- Owner-signed data requests A–C (drafted in E87).
- Owner decisions on the target names and the amendments.

**Owner addendum (2026-10-31; `E129_ADDENDUM_1_OWNER_VALIDATION_DATA.md`).** The owner assigned these roles:

| Source | Role |
|---|---|
| PSA subsistence incidence | Provincial food-deprivation reference |
| FNRI FIES | Household food-insecurity reference |
| SWS Balance Luzon | Regional hunger reference |
| Provincial food CPI | Predictor |

**Effect of the addendum**
- The food-price-pressure *target* option is **not adopted**.
- The three references define a **provincial validation framework**: 10 subsistence points plus 2 FNRI points, all cross-sectional. They do not provide a quarterly label, so the classification is unchanged.

**No model was trained. Nothing in E128, FIRI3, FIRI v2 or production was changed.**

## Measured vs proxy vs index vs price condition

| Category | Examples | Provincial and repeated? |
|---|---|---|
| Measured food insecurity | CBMS / ENNS FIES, SWS hunger | No (cross-sections; SWS regional) |
| Proxy indicators | Subsistence incidence, FIES food share, OPT Plus | Provincial; triennial or annual |
| Constructed risk index | FIRI3 | Provincial, quarterly; validates only itself |
| Food-price conditions | Provincial food CPI, retail rice | Provincial, monthly. Valid target for price pressure only. |

## Answers

1. **Why did E128 become regional-only?**
   - The only repeated food-insecurity measure in the window is SWS Balance Luzon hunger.
   - The E128 rules forbade copying it to provinces, and T43c's provincial class is that copy multiplied by a price condition.
2. **Why does provincial PSA food CPI matter?**
   - It is the one complete, official, monthly series that genuinely differs by province (0 % of quarters identical; 25 % of variance province-specific in a given quarter).
   - So it is what lets aiPHeed produce province-differentiated outputs. Most other inputs are national or regional.
3. **Which official provincial food-insecurity targets exist?**
   - FNRI ENNS 2021 FIES: Batangas 29.7 %, Cavite 31.7 %, Lucena.
   - ENNS 2022: 20 domains; CALABARZON coverage unverified.
   - CBMS 2024 FIES: all participating LGUs, July 2023 – June 2024.
   - None is repeated within the window.
4. **Can FNRI, PSA, CBMS or DSWD data support provincial labels?**
   - **Cross-sectional validation labels: yes** (CBMS strongest), once obtained.
   - **Quarterly forecasting labels: no.**
   - PSA FIES has no food-insecurity items. DSWD data measure programmes, not need.
5. **Can SWS give a provincial breakdown?** Not in published releases. Microdata (not held) would give about 20–75 respondents per province-round: usable only pooled annually.
6. **Can pre-2021 SWS help?**
   - **For the regional series:** about 90 quarters, if the owner widens the window and dates and the 2020 phone rounds are handled.
   - **For provinces:** no.
7. **Which trigger groups have genuinely provincial data?**

   | Group | Provincial data |
   |---|---|
   | Market and food prices (including production) | Yes: 36 of 38 features |
   | Climate | Partly: local typhoon counts, though identical across provinces in 64–82 % of quarters; NASA centroid rainfall and temperature; ONI and PAR are not |
   | Employment and OFW | Annual provincial unemployment only; remittances national |
   | News and NLP | Provincial article volume and FSSI-v3 (83 % missing); GDELT national |
   | Poverty | Provincial but static or triennial |

8. **Independent provincial target observations**
   - Food insecurity: **2 held** (2021, 2 provinces). At most about 10–12 obtainable, all cross-sectional.
   - Food CPI: 115 province-quarters, effective n about 29.
9. **Can a valid provincial panel be built?**
   - **For food insecurity: no.**
   - **For food-price pressure: yes** (5 × 23 quarters).
10. **Is the fixed 11.3 % SWS threshold suitable for provinces?** **No.**
    - It is a regional, researcher-set P60 of six 2021–22 quarters.
    - It has been saturated since 2023-Q4.
    - It has no provincial meaning.
11. **Can a continuous provincial target replace the binary threshold?**
    - **Yes, for food-price pressure** (food CPI YoY).
    - **No continuous provincial food-insecurity series exists.**
12. **Can a constructed risk index be used, and what would it validate?**
    - Yes, declared as an index. FIRI3 already fills this role.
    - Forecasting it validates **index forecasting only**, partly circular because it is built from the predictors.
    - It can be checked against CBMS / ENNS cross-sections.
13. **Are R1–R7 appropriate for the provincial panel?**
    - **Mostly yes**, read with clustering by quarter.
    - Proposed amendments for owner approval: A-R1p, A-R4p, A-R7p; and A-R2c for a continuous target.
    - None weakens the rule.
14. **Which validation design avoids temporal and geographic leakage?**
    - Expanding-window walk-forward by issue date, with all provinces cut at the same date.
    - Cluster bootstrap by quarter.
    - Per-province reporting and per-province persistence.
    - Province-held-out only as a supplement.
    - No random splits.
15. **Is Lead 2 realistically evaluable?**
    - **For food-price pressure: yes** (13 quarters, 65 rows). Province deviations keep autocorrelation 0.55 at two quarters, so some province signal remains.
    - **For provincial food insecurity: no.**
16. **Recommended next step before model training**
    1. Freeze a provincial **validation** protocol on the owner's references: V-S1, V-S2, V-F1 and V-R (Addendum 1).
    2. Decide the R-amendments.
    3. Send data requests A–C. CBMS 2024 FIES is the only route to an LGU-level food-insecurity check.
    4. Verify the 148 unverified CPI release dates (CPI is a predictor).
    5. **Quarterly provincial model training stays blocked.** No provincial quarterly label exists. Any provincial model output can be checked only against the cross-sectional references.
