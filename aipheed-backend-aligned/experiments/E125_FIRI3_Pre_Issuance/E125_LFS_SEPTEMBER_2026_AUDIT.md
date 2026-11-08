# E125 LFS September 2026 audit (EHS national unemployment change)

| Item | Finding |
|---|---|
| Source | PSA OpenSTAT table `1B/LFS/0021B3FKEI2.px`, "Unemployment Rate", Philippines (the same table and selection as E114), re-queried **2026-10-31** (`data/raw/psa_lfs_0021B3FKEI2_unemployment.csv`; hash in `data/refresh_log.json`) |
| 2026-Q3 months in the table | **July 6.005, August 5.269; September "." (not published)** |
| Changes vs the E114 retrieval (2026-10-25) | None (0 rows differ) |
| Definition | Unemployment rate (%), unemployed ÷ labour force, both sexes, national. The feature is the change in the quarterly mean vs the same quarter one year earlier, in percentage points (2021+ base). |
| Release rule | First day of m+3, so September is due by **2026-12-01** (rule; not an archived date). No search for a release was made. |
| Treatment | A 2-month mean is **not** treated as the complete 2026-Q3 quarter. The feature is **BLOCKED** for the 2026-Q4 issue until September is published and retrieved. |
| Effect if still missing at the issue | The regional EHS indicator would rest on the remittance decline only (one of two components, ⌈2/2⌉ = 1 needed, so still computable) |

**Disclosure.** E119's rule takes the mean of the survey months held. Historical E1 values were therefore computed from whatever months existed at retrieval. All historical quarters from 2021 to 2026-Q2 have all three months in the table, so the issue concerns 2026-Q3 only.

**Action.** On or after 2026-12-01, re-query the table. Confirm all three months, then recompute E1 for 2026-Q3 with the unchanged E119 rule.
