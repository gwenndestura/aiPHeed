# Addendum to PROTOCOL_LEAD2_ROOT_CAUSE: re-scoring CR-ANC under verified CPI release dates (pre-registered 2026-10-29)

**Written before any provincial release date is known.** As of today, 0 of the 18 refreshed months have a verified date (`data/psa_cpi_release_evidence.csv`). The SHA-256 goes in `runner/ROOT_CAUSE_ADDENDUM_SHA256.txt`.

1. **Trigger.** A release date counts as verified only when an official dated PSA source gives the original release date of the provincial CPI table for that reference month: the Advance Release Calendar, an RSSO IV-A release log, or a dated press release. Re-posting dates do not count. A verified date is entered as `VERIFIED` with its URL in the evidence file.
2. **Rule.** Once every one of the 18 months is verified, the refreshed CPI cut-off of each Lead-2+ row becomes the newest month whose verified release date is **strictly before** the row's re-issue date. Months released on or after the issue date are not used.
3. **Re-score.** CR-ANC is re-scored **once** under that cut-off, with the frozen columns, grid, seed, target, rows, R1-R7 and `final.adoption_rule` vs P0H4-U. The day-10 results are kept for comparison. No other variant or release rule is scored.
4. **Decision.** CR-ANC becomes eligible for an adoption *proposal* only if the re-score passes R1-R7 at Leads 1 and 2 and the adoption rule. Serving it still needs the researchers' explicit approval.
5. **Prospective.** `sealed/cranc_prospective.csv` (07c99e56…) is scored as its outcomes are published, whatever the re-score shows. It is never refitted or re-sealed.
