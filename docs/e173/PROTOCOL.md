# E173 protocol: E168 plus official regional unemployment

Locked 2026-11-07, before any E173 result exists. Run once. The result is reported whatever it is.

## Why

**Diagnosis** (`docs/final/FINAL_REPORT_E168_v2.md` §3; input audit of the 732 training rows at the 2026-Q4 issue):
- The employment group cannot carry province-specific information. Its three filled inputs (`unemp_rate`, `unemp_yoy`, `unemp_chg_since`) are national, so 0 % of their variance is between provinces.
- The input designed for regional unemployment (`unemp_region`) is **empty in every training and validation row**. Its source table (PSA SDG 8.5.2) starts in 2021, after every validation origin.

**Fix with official data.** PSA Philippine Statistical Yearbook Table 11.1 gives the unemployment rate by region, 2014–2023, for all 17 regions:
- OpenSTAT `DB/3S/C11/0011B2BPYO0.px`
- Saved as `backend/data/e173/raw/psa_yearbook_t11_1_unemployment_region.csv` (sha256 `d31f323a…`)

Nothing is imputed, allocated to provinces or invented. Each province takes **its region's** published rate.

## Change (the only one)

1. `unemp_region` is filled for every training and test row with the region's annual unemployment rate for year y.
2. **Publication rule (unchanged from `app/e148/panel.py`):** year y's rate is usable from the second quarter of year y + 1. A quarter before that uses year y − 1; earlier than 2014 means missing.
3. Region names map one-to-one to the Yearbook rows: ARMM → BARMM, Bicol → Bicol Region, Davao → Davao Region, Ilocos → Ilocos Region, and the other 12 by their own names.
4. **Everything else is E168 unchanged:** the procedure (`app.e168.lgbm_only.run_proc`), the 384-configuration search, training-only selection, monotone sign of `unemp_region` (+1), calibration, the 0.5 cutoff, and the validation rows.

## Runs

E173 at Leads 1, 2 and 3, for ENNS 2018, 2019 and 2021. Nine nested runs, each once.

## Decision rule (fixed now)

E173 replaces E168 only if **all** of these hold:
1. **Better than E168 at Lead 1.** The Lead-1 Brier difference E173 − E168 has a 95 % bootstrap CI (4,000 resamples, seed 173) entirely below 0.
2. **Still meets the project rule at Leads 1–3:** accuracy ≥ 75 %, and significantly better than the latest survey.
3. **Leakage check passes.** No `unemp_region` value used at an origin comes from a year that was not yet published.

**Otherwise E168 stays.** The report then states either:
- regional unemployment carries **no measurable** province-level information, if the CI includes 0; or
- it **worsens** the forecast, if the CI is above 0.

**What this answers.** E168 is E173 with `unemp_region` empty, so the E173 − E168 difference is exactly the contribution of official regional employment information.

## Not changed and why

| Item | Why it stays as it is |
|---|---|
| OFW remittances | No official regional or provincial remittance series exists. PSA's Overseas Filipinos survey publishes only regional OFW shares, and only in PDFs. A structural share is not a remittance flow, and allocating national pesos by it would invent data. Stays national; documented. |
| Climate, fish kill | Already provincial and well covered (57–99 % of variance between provinces). There is no data defect to fix. |
| Market prices | No change. |
