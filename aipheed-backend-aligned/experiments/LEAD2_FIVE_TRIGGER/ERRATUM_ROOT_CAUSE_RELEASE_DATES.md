# Erratum to PROTOCOL_LEAD2_ROOT_CAUSE and ADDENDUM_ROOT_CAUSE_RELEASE_DATES (2026-10-29)

**Neither frozen file is edited.** Their SHA-256 values stay as committed:
- `runner/ROOT_CAUSE_SHA256.txt` (5850dee2…);
- `runner/ROOT_CAUSE_ADDENDUM_SHA256.txt`.

This erratum corrects two counts and states how the release-date evidence is graded. It changes no rule, criterion, candidate, target or threshold.

## E1. Price-reversal count (PROTOCOL §1)

- **What the protocol says:** "6 of CR's 7 false alarms are price reversals".
- **What the data shows** (`out/rootcause_errors.csv`): **5 of 7**. The other two are the model-behaviour cases of 2024-Q3 (Laguna, Batangas).
- **Effect:** none on any candidate. CR-ANC was motivated by the reversal pattern, which holds either way.

## E2. Months needed by the addendum's re-score (ADDENDUM §1-2)

- **What the addendum says:** "18 refreshed months".
- **What its rule requires:** rule 2 applies to every Lead-2+ stack row, training rows included. That needs **36 reference months (180 province-months)** (`data/psa_cpi_release_months_needed.csv`):
  - 34 months counted by the day-10 rule;
  - 2 it excluded that might have been released before the re-issue date: July 2023 for 2023-08-03, and October 2025 for 2025-11-06.
- **Effect:** the re-score runs only when all 180 province-months are confirmed.

## E3. Grading of release-date evidence (applies the addendum's rule 1)

1. The date that counts is the release's own date, never a web page's posting, capture or indexing date.
   - The Internet Archive copies of the Region IV-A release pages carry the release record's **Release-Date** field (older pages: "Release Date:"). That field is used.
   - Capture timestamps are not used.
   - The release PDFs were not archived, so no date in this evidence is read from the PDF itself. The evidence level records this.
2. **Province-specific release first.** A regional CALABARZON release may stand for a province only when its text states that province's figures. The owner must still confirm that its tables carry the province's food and all-items CPI of the all-income-households series.
   - Another province's release is never evidence for a province.
   - Bottom-30% and Lucena City releases are different series and are never used.
3. When several qualifying releases exist for a province-month, the province's own release is used.
4. **A row is `confirmed` only** when the owner marks `confirmed_by_owner = yes` and `is_release_date_printed_on_document = yes` with a saved copy. Document evidence alone makes it `awaiting_owner_review`. A missing date stays blank and `unresolved`.
5. Releases for reference months from 2026-10 onward are neither collected nor kept (blind boundary).

## E4. Corrections after the owner's web-research ledger (2026-10-29)

1. **A page's subject decides whose release it is, not its title.**
   - Many Region IV-A pages have generic titles. The pages titled "Summary Inflation Report Consumer Price Index (2018=100) <month> 2025" (January-July 2025, plus April 2024) open with "The Batangas Province headline ... inflation", so they are **Batangas releases**. They mention other provinces only as rankings.
   - Pages titled "Special Release on Summary Inflation Report: <month> 2024" are Laguna's.
   - The matching now uses each page's subject (`release_pages_fetch.subject`). It no longer uses those Batangas pages for Cavite, Laguna, Quezon or Rizal, which the first pass (f0786a0) did for 9 rows: Cavite and Rizal 2025-03; Rizal 2025-04; Cavite, Laguna and Rizal 2025-06; Cavite, Laguna and Rizal 2025-07.
   - The owner's priority file used the Batangas July 2025 release (2025-08-07) for the other four provinces too. Those 4 rows are kept, with the flag `owner_date_from_batangas_release`.
2. **The ledger is recorded as owner research, not as confirmation.**
   - `data/psa_cpi_release_date_web_research_ledger_20261029.csv` is kept verbatim.
   - Its dates fill the `ledger_*` columns. Regional ledger entries carry `regional_coverage_unverified`.
   - Most of its URLs have no archived copy, so they await the owner's check.
   - Its claim that the Cavite December 2024 archive date came from a Batangas page is not borne out: the saved page is titled "Cavite Summary Inflation: December 2024".
3. **2021 sources are the 2012=100 series.**
   - The model uses the 2018=100 series (OpenSTAT 0012M4ACP22). PSA published 2018-based provincial CPIs only after the rebasing, so for issue dates in 2021 the 2018-based values used by training rows did not yet exist; only the 2012-based figures did.
   - This affects training rows only, not any evaluation forecast: evaluation origins start in 2022-Q4.
   - It is a vintage choice for the owner: either the 2012-based release dates stand for when the information was public, or 2021 rows are treated as not real-time. Flagged as `ledger_source_2012_base`. No result is changed by this note.
4. **September 2026 decides whether the sealed forecasts used only published data.**
   - The sealed CR and CR-ANC Lead 2-4 forecasts were re-issued on 2026-10-15 with CPI through 2026-09.
   - The regional September 2025 release came out on 2025-10-15.
   - If the September 2026 provincial CPI was released on or after 2026-10-15, both sealed files used data not yet public at their stated issue date. The owner must establish this date.
   - The September 2026 releases are allowed under the blind rule (reference month 2026-09).

## E5. The Rizal 2027-Q1 companion record is not the counted forecast (2026-10-29)

- The companion manifest (`sealed/rizal_2027q1_companion.sha256`) contains a `scoring_rule` saying the companion counts unless the issue-day timing is resolved. **That rule is withdrawn.**
- No frozen document authorizes it. Addendum rule 5 scores the sealed originals as published.
- The manifest and the companion CSV (b1edb799…) are left exactly as sealed, as a labelled diagnostic record.
- Its construction pairs September food CPI with August all-items CPI in one gap feature. That violates rule 1 of `ASOF_RULE_SEPT2026.md`.

## E6. The September 2026 timing impact (LEAD2_SEPT2026_VINTAGE_AND_CAUSES_REPORT section 1)

- **What section 1 says:** "28 of 30 rows valid; only Rizal Lead 2 depends on the timing". That came from the split construction of E5.
- **What the consistent cut-off shows:** one cut-off month per province-month (addendum rule 2), applied to all provinces and Leads 2-4. September 2026 is not verified for any province.
  - 9 of the 30 sealed Lead 2-4 rows change class with the cut-off. If the owner-reported provincial dates are verified, 3 still depend on it.
  - Rizal 2027-Q1 Lead 2 is LOW under every consistent cut-off.
- Details are in section 4 of that report and in `out/sept2026_asof_variants.csv`.
- No rule, criterion, seal or score is changed.
