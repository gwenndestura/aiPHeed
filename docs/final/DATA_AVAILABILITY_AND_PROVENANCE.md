# Data availability and provenance

**As-of rule:** every historical forecast uses only values released at its issue quarter. This was verified by the corruption tests (0.0 change) in E156 and E160–E167. Granularity is from `data/e163/out/group_audit.csv`.

| Group | Input (examples) | Source | Level | Frequency | Availability rule in code | Missing in training |
|---|---|---|---|---|---|---|
| Market and prices | `cpi_food_yoy`, `cpi_rice_yoy`, `cpi_since`, wholesale and farmgate rice (E152) | PSA CPI (OpenSTAT); PSA price surveys | **Provincial** (6), regional (3), national (1) | Monthly → quarterly | Value at the issue quarter | about 2 % |
| Climate stress | rain and soil anomalies, typhoon counts, `c_agri_yoy`, `c_fish_yoy`, ONI | NASA POWER; typhoon tracks; PSA agricultural and fisheries production; NOAA ONI | **Provincial** (8), regional (4), national (2) | Monthly / quarterly | Value at the issue quarter | about 1 % |
| Employment | `unemp_rate`, `unemp_yoy`, `unemp_chg_since`, `income_growth` | PSA LFS (**national**); PSA regional HFCE | **National only**; consumption regional | Quarterly; HFCE annual | HFCE: year Y public from Q3 of Y + 1 | `unemp_region` 100 % |
| OFW remittances | `remit_yoy`, `remit_since` | BSP (**national**) | **National only** | Monthly | Value at the issue quarter | `remit_q_yoy` 100 % |
| Poverty and social vulnerability | `p_poverty`, `p_subsistence`, `p_poverty_gap`, `p_density`, `income_rel`, SWS `h2` | PSA official poverty statistics (2015, 2018, 2021, 2023); POPCEN; PSA HFCE; SWS | **Provincial** (6), regional (15), national (5) | Triennial or biennial; quarterly (SWS) | Latest PSA release before the issue | about 7 % |
| News (inside the groups) | `p_e_*` (province), `a_e_*` (SWS area), `n_e_*` (national), SunStar | GDELT and SunStar, LEX lexicon by group | Provincial / area / national | Daily → quarterly | Articles dated before the issue quarter | 0 % |
| Survey anchor | latest HFIAS reading | FNRI | Provincial | Rounds | Round public 6 quarters after reference (`ANCHOR_LAG`) | n/a |

## Known provenance issues
1. **Employment and remittances have no provincial official data.** They are never copied into provinces as if provincial. They are recorded as national.
2. **Definition breaks:**
   - subsistence incidence moves from families (training years) to population (2018+ methodology);
   - the CPI base changes from 2012 to 2018 (E137 notes).

   Both are disclosed, not corrected at source.
3. **Regional household consumption** (PSA OpenSTAT `2B/EA/BR/PHF_OS/0672B5BEPC1.px`):
   - the project file ends in 2023;
   - **PSA published 2024** (PSA regional office release, 2025);
   - **2025 is not verified;**
   - **so at the 2026-Q4 issue it is unavailable** and nothing older is substituted.
4. **PSA and BSP block scripted downloads** (403 / Cloudflare), so updates need a manual download.
5. **Publication dates** for CPI, LFS and BSP follow the release lags coded in the panels (value at the issue quarter). An exact per-release date audit against PSA calendars was not possible for every series. The HFCE and FNRI rules are conservative.
