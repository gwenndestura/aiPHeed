# E123 Batangas employment and underemployment verification (DI-6)

**Sources:**
- `out/batangas_chain.csv`;
- `out/batangas_owner_rows.csv`;
- `out/summary.json` → `batangas`.

**No value was adjusted.**

## 1. Source chain

**From the owner file to FIRI3:**
1. `E116_FIRI_Domains/data/owner/calabarzon_provincial_employment_food_insecurity_relevant_2021_2026.csv` (owner-compiled);
2. E119 `E119_PROVINCIAL_ANNUAL_INDICATORS.csv`;
3. the FIRI3 feature `raw_value`.

| Feature | Year | Owner file | E119 | FIRI3 raw | Match |
|---|---|---|---|---|---|
| Unemployment | 2021 | 10.8 | 10.8 | 10.8 | yes |
| Underemployment | 2021 | 12.2 | 12.2 | 12.2 | yes |
| Unemployment | 2022 | 6.7 | 6.7 | 6.7 | yes |
| Underemployment | 2022 | 23.0 | 23.0 | 23.0 | yes |
| Unemployment | 2023 | 5.5 | 5.5 | 5.5 | yes |
| Underemployment | 2023 | 31.0 | 31.0 | 31.0 | yes |
| Unemployment | 2024 | (blank) | 6.0 | 6.0 | **derived** = 100 − employment rate 94.0 (exact by definition; flagged in E119) |
| Underemployment | 2024 | 39.5 | 39.5 | 39.5 | yes |
| Underemployment | 2025 | 21.1 | 21.1 | (not used: 2025 incomplete, skipped under Amendment 2) | — |

**No transformation or aggregation error was found.** Values enter as percentages, on the same scale as the other provinces.

## 2. Definitions and internal consistency

**Definitions.**
- **Underemployment rate:** underemployed persons as a percentage of **employed** persons (PSA LFS definition).
- **Unemployment rate:** unemployed persons as a percentage of the labour force.

**Consistency check.** The underemployed count divided by the employed count reproduces the reported rate:

| Year | Underemployed / employed (thousands) | Implied rate | Reported rate |
|---|---|---|---|
| 2021 | 150 / 1,234 | 12.2 | 12.2 |
| 2022 | 306 / 1,332 | 23.0 | 23.0 |
| 2023 | 420 / 1,352 | 31.1 | 31.0 |
| 2024 | 538 / — | — | 39.5 (employed count not in the file) |

## 3. Against PSA

| Year | Status | Evidence |
|---|---|---|
| 2023 | **Corroborated** | A web search found the PSA Region IV-A special release "2023 CALABARZON Labor Market Statistics" (rsso04a.psa.gov.ph, SR09). Its indexed text reports that underemployment *"decreased in all provinces except in Batangas with rate of 31.0 percent"*, with 2023 marked preliminary and 2021–2022 final. The document itself returned **HTTP 403**, and no Internet Archive copy could be reached, so the table, its date and its exact wording could not be read. |
| 2024 (39.5%) | **Not verified** | Owner note: "PSA 2023-2024 provincial LFS infographic; preliminary 2024". No PSA document retrieved. |
| 2025 (21.1%) | **Not verified** | Owner note: "PSA 2025 annual provincial results". Not used: the year is incomplete. |
| Publication dates | **Unknown** | The 30 June Y+1 rule is an assumption |

## 4. Influence

**Batangas in the rankings.** Batangas ranks first on the SVS in all 5 computable origins and first on FIRI3 in 9 of 15. Its underemployment rank is the highest of the five in 2022–2024.

**Sensitivity (not an adjustment).** Removing only Batangas underemployment from EHS:
- mean FIRI3 change 0.005, max 0.063;
- band changes 4%;
- province-rank ρ 0.98.

Batangas's EHS rank is driven by both its unemployment and its underemployment.

## 5. Status

- **Values:** traced and internally consistent; 2023 corroborated; 2024 and 2025 unverified.
- **Publication dates:** unverified. EHS is classified **unverified** in `E123_PUBLICATION_DATE_AUDIT.csv`.
- **To close the item:** obtain the PSA provincial LFS tables, or the RSSO IV-A releases with their dates, through the owner. Batangas 2024 at 39.5% (vs 7.8–13.8% elsewhere) should be confirmed before any adoption.
