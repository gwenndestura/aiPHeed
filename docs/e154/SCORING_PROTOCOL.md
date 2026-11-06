# Scoring the sealed forecasts

Written 2026-11-06, before any target outcome exists. **Nothing here may change after an outcome is seen.** Run `python -m app.e154.score_seals`. The script refuses to score a seal whose file hash has changed.

## Seals

| Seal | File | sha256 starts | Predicts |
|---|---|---|---|
| SWS areas, E151 | `data/e151/out/sealed_sws_2026-Q4.json` | `1a1c34bf` | SWS hunger, 4 areas, 2027-Q1 to Q4 (Leads 1 to 4), arms PERS, AR, GOV, NEWS, GN, GNT |
| Provinces, E151 required | `data/e151/out/issue/sealed_forecast_2027-Q1.json` | `b397c40f` | 5 provinces |
| Provinces, D5 attempt | `data/e151/out/issue/sealed_attempt_2027-Q1.json` | `0f430203` | 5 provinces |
| Provinces, E152 | `data/e152/out/sealed_2027-Q1.json` | `f6c07789` | 5 provinces |
| Provinces, E154 frozen | `data/e154/out/sealed_2027-Q1.json` | `d724c454` | 5 provinces |
| **Provinces, E158 thesis model** | `data/e158/out/sealed_2027-Q1.json` | `f69e7a02` | 5 provinces, Leads 1 to 4 |
| Provinces, E163 candidates C1–C3 + E158 | `data/e163/out/sealed_2027-Q1.json` | `343d1f06` | 5 provinces, Lead 1. Score each arm, and also the **order** of the five against any 2027 HFIAS round |

## SWS areas: scorable as SWS publishes

* **Outcome:** SWS involuntary hunger for each area and quarter, as first published. Revisions are ignored.
* **Per quarter and lead:** squared error of each arm on the logit of hunger; the sign of the change from the last reading; persistence is the comparator.
* **Claim rule:** after 4 or more scored quarters at Lead 1 (16 area rows), report GNT - persistence and GOV - persistence with a block bootstrap by quarter. Before that, report each quarter's result as it comes, **with no claim of skill.**
* SWS is not a provincial measure. A good SWS result does not validate the provinces.

## Provinces: scorable only if a matching survey appears

* **Outcome needed:** a published HFIAS moderate-plus-severe percentage for any of the five provinces, with a reference period in 2027.
* **Matching:** live scores do not change between Leads 1 and 4 at this issue date (section 9 of `docs/e151/FINAL_REPORT.md`), so a 2027 survey is compared with the sealed 2027-Q1 score, **and that approximation is stated.** A survey for a later year is compared only with a new seal made before its release.
* **Scored:** class (HIGH at 50), error in points, and whether the survey falls inside the sealed 90 % range.
* **Not scorable:** a FIES result, an any-level result, or a regional result. These are different instruments or areas and are reported only as context. **FNRI's 2023 survey used FIES, so a usable HFIAS round may never come.** If none does by the time the thesis is final, the province seals are recorded as unscored.
* **With five provinces, one round cannot establish accuracy.** It is reported row by row, with no percentage claim.

## Rules for the analyst

* Do not look for these outcomes before the owner provides or authorises them.
* Do not re-issue, edit or replace a seal. A new seal is a new file with its own date.
* Score every seal, including the ones that are not the frozen model.
