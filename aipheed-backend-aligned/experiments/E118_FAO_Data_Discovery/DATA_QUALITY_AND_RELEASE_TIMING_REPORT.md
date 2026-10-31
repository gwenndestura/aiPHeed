# E118 data quality and release timing

## Quality (measured)

| Check | Result |
|---|---|
| Duplicates | none on unit × item × period in any acquired table |
| Negative values | none where impossible |
| Coverage gaps | retail tables list many commodities that are reported only in some months, so whole-table missing shares are 36-90%. The staples (rice, chicken, pork, tilapia, palay farmgate, well-milled rice wholesale) are complete in every published month. Missing values are left missing. |
| Series breaks | PSA retail and wholesale prices have an old series (1990-2021) and a 2018-based series (2018-2026). The overlapping years must be reconciled, not concatenated. CPI 2012=100 for 1994-2018 is annual only, so it cannot fill the monthly 2012=100 vintage. |
| Survey precision | subsistence incidence CVs are 14-88%. Cavite's food-poverty estimates are statistically unreliable (CV 44-88%). |
| Geography traps | "Quezon City" appears in PSA tables and must not be read as Quezon province. Lucena (HUC) is separate in poverty and FIES tables. |
| Point vs area | NASA POWER values are model and satellite estimates at one point per province, not station data and not provincial averages. |

## Release timing (point-in-time use)

| Source | What is known | Status for strict evaluation |
|---|---|---|
| OpenSTAT tables | Each table has one "updated" stamp (for example palay 2026-10-29, prices 2026-10), not a per-period release date. Retrieval timestamps are recorded. | **rule_unverified** until PSA release calendars or dated releases are collected. Rules to test: prices month m at day ~10-15 of m+1; production quarter q about 6-8 weeks after its end. |
| CPI (all income, bottom 30%) | released about the 5th of the following month nationally; provincial dates partly archived (E-series ledger) | as the existing CPI ledger |
| NASA POWER | near real time (about 1-2 months); MERRA-2-based values can be revised | vintage risk. Store the retrieval date; treat values as unverified for strict historical use. |
| Subsistence incidence, FIES | publication dates known (e.g. 2023 published 2024-08-15) | verified, but triennial |
| FNRI, CBMS, OPT Plus | report dates per round | verified per round once obtained |

## Implications

1. **Strict point-in-time training cannot use any new monthly or quarterly series yet.** None has verified per-period release dates. The same applies to the existing CPI and production inputs (E117).
2. **Provisional training can use them** with documented release rules, labelled provisional, plus a +1-period lag sensitivity.
3. **Collecting PSA release calendars would unlock both new and existing features.** PSA publishes an advance release calendar per year; archived copies cover past years.
