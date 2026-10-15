# Protected-information exposure log (E26)

| When (UTC) | How | What was seen | Protected? | Consequence |
|---|---|---|---|---|
| 2026-10-14, about 01:15 | A web search for the **location** of the PSA "CPI for the bottom 30% income households" table (source investigation). The search engine's summary quoted the current PSA release page. | **National, NCR and regional** bottom-30% CPI inflation for **August and September 2026** (release dated 2026-10-06), as printed in the search summary | **Yes.** July–December 2026 price information is protected. This is not the provincial food CPI file and not an SWS value. | (1) The E25 seal (`SEAL_E25_20261014T002548Z`, created about 00:25 UTC) predates the exposure and is unaffected; it was re-verified unchanged. (2) **E26 creates no new seal or forecast for 2026-Q3, 2026-Q4 or 2027-Q1**: my judgement about those quarters is no longer blind. (3) No E26 computation uses this information. (4) Mitigation: later searches target methodology and older-year documents only; "latest release" pages of PSA, BSP and SWS are not searched or opened. |

No SWS web page was opened. Every search blocked `sws.org.ph`.
