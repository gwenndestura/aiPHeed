# Remaining data gaps (not fixable with existing data)

| Gap | Indicators | Current status in the pipeline | What would close it |
|---|---|---|---|
| CPI release dates for most province-months | A1, A2 | 80 of 115 profile rows `rule_unverified` (no archived release before the issue) | dated PSA provincial CPI release pages, or the PSA advance release calendar |
| As-released (unrevised) CPI index values | A1, A2 | final vintage used; 3 known revisions | archived OpenSTAT snapshots or the PDF attachments of the releases |
| 2012=100 CPI for issues before the rebase | A1, A2 | 25 rows flagged | 2012=100 provincial tables (PSA) for 2021-early 2022 |
| Publication dates of rice prices, palay/corn, fisheries | A3, C3, C4 | all `rule_unverified` | PSA release calendars or dated release pages |
| Quarterly provincial or regional employment | E1 | national monthly (`rule_unverified`); provincial annual only | PSA quarterly LFS for Region IV-A / provinces, with release dates |
| Publication dates of annual provincial employment | E1 | `rule_unverified` | the PSA source URL and date for each value in the owner file |
| OFW remittances: long series and original-release dates | E2 | 2 of 18 quarters verified; national only; no pre-2021 data | BSP OFW cash remittance series (1989+) and its release calendar, downloaded manually (BSP blocks automated access) |
| Remittance source conflict | E2 | E107 panel differs from the release ledger by up to 0.79 bn per quarter | confirm against BSP's own table |
| Rainfall | C2 / climate | not available (column empty) | PAGASA station rainfall or CHIRPS, with dates |
| Poverty before 2024 | V1 | SAE 2021 public only from 2024-25 | SAE 2018 / 2015 provincial poverty for earlier origins |
| News coverage | N1 | 20 of 115 rows observed | denser provincial news collection; the history cannot be backfilled |
| Pre-2021 SWS release dates | regional target | rule (month end + 60 days), 704 regional rows | SWS release archive |
| Provincial food-insecurity outcome over time | provincial forecasting | none | repeated CBMS FIES or FNRI provincial rounds (send the E87 requests) |

**Domain status after the fixes:**
- **Market and food prices:** corrected thresholds and flags. Timing mostly `rule_unverified`.
- **Fish production:** provincial 2021+ (profile) and area-level 1993+ (regional panel). Kept separate. Timing `rule_unverified`.
- **Climate:** El Niño verified, typhoons verified, local exposure added, palay `rule_unverified`. No rainfall.
- **Employment:** national quarterly plus provincial annual, at their real resolutions. Still no quarterly provincial series.
- **OFW remittances:** national only, 2021+, 2 verified quarters.
