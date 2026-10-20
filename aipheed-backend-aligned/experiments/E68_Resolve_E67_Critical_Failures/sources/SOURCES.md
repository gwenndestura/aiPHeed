# E68 sources (fetched 2026-10-20; PAGASA domain only; no PSA/BSP/SWS queries)

| URL | Finding |
|---|---|
| https://www.pagasa.dost.gov.ph/climate/el-nino-la-nina/monitoring | "updated: 07 October 2026"; links only to Monitoring, Advisories and Climate Advisories. No dry spell/drought assessment documents and no archive of earlier years. No CALABARZON province is named under dry spell or drought on the page. |
| https://www.pagasa.dost.gov.ph/climate/climate-prediction/drought-assessment | HTTP 404 (no such page) |
| https://www.pagasa.dost.gov.ph/climate/el-nino-la-nina/advisories | (E67, 2026-10-20) El Niño Advisories Nos. 1–5, 2026-06-09..2026-10-07; nothing later |
| E65 `sources/` | Advisory PDFs with text: No. 5 (2026-10-07) says "dry conditions likely in Quezon by end-October"; ENSO press-release timeline 2021–2026 |

**Consequence.** No dated, archived 2021–2026 series of PAGASA dry-spell or drought assessments with issue dates is available from these pages, so a drought or dry-spell feature cannot be back-tested without using information published after past issue dates. The only dated forward climate items are the ENSO advisories, already coded in `enso_context.PAGASA_ENSO` and used by `climate_watch` and the K1 arm. Provincial rainfall in the repository holds pre-2021 rows and is excluded by the study-window rule.
