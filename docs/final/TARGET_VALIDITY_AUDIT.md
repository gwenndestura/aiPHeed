# Target validity audit

**Target:** HFIAS moderate + severe household food insecurity (%) by province. **HIGH = ≥ 50 %.** It is a direct survey measurement, never rescaled. The target is built in `backend/app/e151/prov.py` (`target_rows`).

| Round | Source | Design | Provinces | Reference (project convention) | Standard error |
|---|---|---|---|---|---|
| NNS 2013 | DOST-FNRI National Nutrition Survey | National, all provinces | 78 | 2013-Q3 | Published sampling SE |
| FNRI 2015 | DOST-FNRI updating survey | National, all provinces | 78 | 2015-Q3 | Published SE |
| ENNS 2018 | DOST-FNRI Expanded NNS, **rolling** | Province subset | 22 | 2018-Q3 | Published SE |
| ENNS 2019 | ENNS, rolling | Province subset | 25 | 2019-Q3 | Published SE |
| ENNS 2021 | ENNS, rolling (pandemic year) | Province subset | 25 | 2021-Q3 | **Assumed 3.0 points:** the Heat Map gives no SE (disclosed limitation) |

- **Instrument:** the HFIAS categories are the same in every round. The 2021 value is moderate + severe from the FNRI Heat Map categories.
- **Not pooled:** FIES (PSA SDG 2.1.2, 2023 NNS), SWS involuntary hunger, poverty, subsistence incidence and food prices are not targets.
  - **FIES** is regional context only.
  - **SWS** is an area-level input.
  - **Poverty** is an input.

## Is the post-2015 decline real?
- **National level (two-way fixed effects):** 57.6 (2013) → 56.2 (2015) → 46.5 (2018) → 48.4 (2019) → 43.0 (2021).
- **Consistent with:** falling poverty (PSA 2015 → 2018 → 2021/2023) and PSA FIES 2023 (31.4 % nationally).
- **Cannot be fully separated from design change:** 2013 and 2015 were national surveys; 2018–2021 are rolling subsets with different provinces each year. The fixed-effects national level adjusts for province mix, but not for any difference in fieldwork or mode. **2021 was fielded during COVID-19.**
- **Cannot be confirmed for CALABARZON specifically:** CALABARZON contributes one row per province in 2018–2021.

## Validity verdict
| Question | Answer |
|---|---|
| Genuinely provincial? | Yes. Provincial estimates from FNRI |
| Comparable across rounds? | Same instrument and categories; design changed from national to rolling. **Comparability is plausible but not proven** |
| Enough HIGH cases? | 25 of 72 nationally; **0 in CALABARZON** |
| Newer rounds? | ENNS 2022 (20 provinces, PSA-cleared) exists, but **no public provincial percentages were found** (the owner's search file of 2026-11-06 confirms). The 2023 NNS used **FIES**, so it is not usable. Frozen forecasts for 2022 are sealed (49e514d2) |

**Distinctions kept:**
- **Observed:** FNRI HFIAS %.
- **Derived label:** HIGH/LOW at 50.
- **Proxies:** poverty, CPI, climate, SWS, news.
- **Model estimates:** score and P(HIGH).

**Owner file `CALABARZON_latest_provincial_food_security_2021_2025.csv` (2026-11-06):**
- It has no provincial food-insecurity values for 2022–2025.
- Its "subsistence incidence" values (17–53 %) are **inconsistent with PSA subsistence incidence** (about 0.4–1.5 % for these provinces in 2023) and are probably coefficients of variation. **Not used.**
