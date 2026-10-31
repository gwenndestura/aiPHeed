# E130 reference risk-score methodology: PFDR v1

## 1. Definition

**PFDR v1 (Provincial Food-Deprivation Reference, version 1).** PSA subsistence incidence among the population of province *p* in FIES survey year *y*: the percentage of people whose per-capita income is below the provincial food threshold. The food threshold is the cost of a basket of food that meets minimum nutritional needs, priced in that province.

| Property | Value |
|---|---|
| Owner role | Provincial food-deprivation reference (owner, 2026-10-31) |
| Scale | % of population, 0–100. No rescaling: a 0–1 score would need anchors (minimum and maximum) that the data do not supply. |
| Direction | Higher means more food deprivation |
| Geography | Province, as published by PSA; Quezon excludes Lucena City |
| Observation period | Calendar year *y* (FIES income reference period) |
| Frequency | Every two years: 2021, 2023, 2025 |
| Publication | 2021 and 2023: vintage of 2024-08-15 (held). 2025: first released 2026-08-21 (not held). |
| Uncertainty | Published CV; SE = value × CV / 100; 90 % interval = value ± 1.645 SE |
| Code | `runner/e130_lib.py: load_reference()`. It asserts no pre-2021 rows, no duplicated province-year and all five provinces. |
| Data | `E130_REFERENCE_SCORE_DATA.csv` |

## 2. Why a single official measure rather than a composite

The brief allows a composite if it can be justified. E130 does not build one, for four reasons:

1. **The candidate components measure different things.**
   - Subsistence incidence: income below a food threshold, % of population.
   - FNRI FIES: experienced food insecurity, % of households.
   - FIES food share: % of spending.
   - Averaging them, even after standardization, would produce a number with no defined meaning.
2. **The frequencies and coverage differ.** FNRI FIES exists for 2 provinces in 1 round. A composite would be undefined for 3 provinces and every other year.
3. **A normalization needs an anchor.** Min–max or z-scaling over 10 values makes each value depend on the others, so a province's "risk" would change when another province's estimate is revised.
4. **The owner assigned the roles.** Subsistence is the provincial food-deprivation reference and FNRI FIES the household food-insecurity reference. Keeping them separate preserves both.

## 3. Relation to quarterly forecasts

**None.** A survey-year value is not a quarterly observation. E130 does not interpolate, disaggregate (Chow-Lin, Denton) or repeat it across quarters:
- disaggregation would use the predictors to build the label (circular);
- repetition would count one observation four times.

The dashboard's quarterly targets have **no provincial reference** (`target_quarter_has_provincial_reference = False` in every row of `E130_ISSUE_DATE_AND_OPERATIONAL_LEAD_MAPPING.csv`).

## 4. Overlap with the predictors (circularity check)

**The food threshold is priced at provincial food prices.** Between rounds, a province whose food prices rose faster sees its threshold rise faster. With income growth equal across provinces, its subsistence incidence would then rise relative to others. So provincial food CPI enters PFDR partly by construction.

**What the data show (descriptive; N = 5; values already seen in E129).** Across provinces, the food-price rise from 2021 to 2023 ranks the PFDR change almost exactly:

| Province | Food prices, 2021→2023 | PFDR change |
|---|---|---|
| Rizal | +16.3 % | +1.7 pp |
| Batangas | +15.3 % | +0.4 pp |
| Cavite | +13.1 % | −1.6 pp |
| Laguna | +9.8 % | −1.1 pp |
| Quezon | +7.0 % | −5.7 pp |

- Spearman 0.90; exact one-sided p = 5/120 = 0.042.
- The change in provincial unemployment ranks it not at all (Spearman 0.00).

**How the overlap is controlled:**
- CPI is never the target.
- A model must beat the PSA-only arm, which contains CPI, before it can claim to learn more than price indexation.
- Income-side information (employment, remittances) is reported separately.

**For a PFDR target, food prices are part of the construct (affordability), not a confound.** But a model that uses only prices cannot see the income side of deprivation.

## 5. Independent cross-checks

| Check | Result |
|---|---|
| FNRI FIES 2021 (household experienced food insecurity) | Batangas 29.7 % [27.3–32.2]; Cavite 31.7 % [27.0–36.4]. The intervals overlap, so FIES cannot order these two provinces. PFDR 2021 orders them Cavite 2.4 > Batangas 1.0, consistent in direction only. |
| PSA FIES 2023 food share of spending | Spearman with PFDR 2023 = −0.20: the two PSA measures order the provinces differently in 2023 |
| SWS Balance Luzon hunger (regional, never copied) | Annual means: 11.6 (2021), 10.9 (2022), 11.2 (2023), 19.6 (2024), 18.9 (2025). Flat from 2021 to 2023 while PFDR fell in 3 of 5 provinces, then a sharp regional rise in 2024 that no provincial round yet covers. |

## 6. Categories

**No officially approved PFDR category thresholds exist**, so HIGH/MEDIUM/LOW classification is **not valid** in E130.

**Proposal for the owner (not applied):** three bands relative to the regional value of the same round, each defined at the 90 % level using both SEs:
- significantly below;
- not significantly different;
- significantly above.

## 7. Reference versions

| Version | Status |
|---|---|
| PFDR v1 | 2021 and 2023 held |
| v1 + 2025 | Adds the 2025 round, unchanged in definition, once the owner supplies the PSA table |

Any change to the definition requires a new version and a new protocol.
