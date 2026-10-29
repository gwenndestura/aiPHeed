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
