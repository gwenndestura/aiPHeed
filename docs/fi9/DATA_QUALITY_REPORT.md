# Data quality report (FI9)

Details per series: the `Predictor_series`, `Discrepancies_flags` and `Missing_data` sheets of
DATA_SOURCE_AND_VALIDATION_LOG.xlsx. Missingness: MISSING_DATA_REPORT.md.

## Outcome (SWS Balance Luzon hunger)

* **Traceable.** Every quarter has its release date and published margin of error (`raw/sws`, FI5 manifest sha256).
* **Regional, not CALABARZON.** CALABARZON is ~34 % of the Balance Luzon population.
* **Noisy at quarterly frequency.** Sampling error explains about 56 % of the variance of quarter-to-quarter changes
  (FI8).
* **Sawtooth.** There is an alternating pattern between rounds beyond what sampling error explains. This is the
  main reason the Lead-1 status is provisional.
* **Few HIGH quarters.** 11 in the evaluation period, concentrated in 2021–2026.

## Predictors by domain

| Domain | Series | Level | Issue |
|---|---|---|---|
| Market | PSA food and rice CPI, palay; world rice and urea | Region IV-A; world | Current vintage; food-only CPI used (no splicing with all-items) |
| Climate | NASA POWER rainfall and temperature; IBTrACS storms; ONI | CALABARZON centroid mean; 200 km of any province centroid; global | Regional exposure, not province-specific |
| Employment | PSA LFS unemployment and underemployment | **national** | Regional quarterly LFS with release dates not assembled; flagged as a national proxy |
| Remittances | BSP cash remittances via World Bank WDI | **national, annual** | Not distributed to provinces; flagged |
| Poverty | PSA poverty incidence; subsistence incidence; density | Region IV-A; provinces and LGUs for the priority layer | Methodology break 2015 → 2018; annual/triennial |
| News (inside domains) | FI6-N archive, GDELT, FSSI | CALABARZON / Philippine news | Coverage changes over time (coverage-normalised) |

## Labels considered and rejected as training targets

See LABEL_COMPARABILITY_REPORT.md: 40 of the 50 workbook records were verified exactly against primary sources;
10 ENNS records could not be verified. None of them is a quarterly or comparable provincial series.

## Data acquisition status (no data requested)

The FNRI public-use files (ENNS 2018–2021, NNS 2015/2023) are blocked by the FNRI firewall for this network. FAO
FIES microdata require a request. Neither was requested, as the directive requires. `backend/data/fi_labels/raw/MANIFEST.csv`
lists everything acquired and not acquired, with URLs and reasons.
