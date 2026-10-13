# Decision Note for the Adviser: How a Quarter's SWS Label Is Composed (2026-10-09)

**Purpose:** set out the consequences of the current label definition and the options available.

**What this note does not do:** it does not choose a definition, change any label, or compute any replacement value. The evidence is in `evidence/2026-10-09_readiness/sws_rounds_reconciliation.csv`.

## The current definition (as implemented)

- **Equation 3:** stress = SWS Balance-Luzon hunger + 2 × (provincial food CPI YoY − regional mean); HIGH if stress > the global median.
- **Round assignment:** each SWS round is assigned to the calendar quarter in which it was **fielded** (not SWS's own "First/Second Quarter" naming). The rule is recorded in the header of `app/ml/corpus/sws_hunger_fetcher.py`.
- **Two rounds in one quarter:** where two rounds fall in one quarter, the label uses their **average** (as stated in the fetcher header; the stored labels for 2021-Q2 and 2022-Q2 are averages).

## Facts that bear on the decision

| Quarter | SWS rounds fielded in the quarter | Rounds the stored label uses | Respondent population (per SWS releases) |
|---|---|---|---|
| 2021-Q2 | May 2021 ("First Quarter 2021"); June 2021 ("Second Quarter 2021") | Both, averaged | Household heads |
| 2022-Q2 | April 2022 ("First Quarter 2022"); June 2022 ("Second Quarter 2022") | Both, averaged | Household heads |
| 2025-Q1 | January, February and March 2025 (Stratbase-SWS) | **March only** | **Registered voters** (Stratbase-SWS series, January to April 2025) |
| 2025-Q2 | April 23–28, 2025; June 2025 | **None; no label stored** | April: adults (the April release notes the change from household heads); June: [U] |
| 2025-Q3 | September 24–30, 2025 | **None; no label stored** | [U] |
| 2025-Q4 | November 24–30, 2025 | November | [U] |
| 2021-Q1, 2022-Q1 | None fielded in these quarters, as far as found; SWS's "First Quarter" surveys of 2021/2022 were fielded in April–May | None | n/a |

Respondent bases come from the SWS April 2025 release (search-index excerpt): household heads through December 2024, registered voters January–April 2025, and adult respondents for the April 23–28, 2025 survey. The populations for June, September and November 2025 have not been confirmed [U].

**What the facts mean for the label:**

1. **The number of rounds behind a label is inconsistent.**
   - Two quarters average two rounds.
   - One quarter uses one of three available rounds.
   - Two quarters with rounds available have no label at all.

   Averaging two rounds also gives a quarter's label a different noise level from a single-round quarter.
2. **The respondent population changes within the 2025 labels.** SWS itself flags the change, so 2025 values may not be directly comparable with 2021–2024 values. 2025 includes some of the highest stress readings, and the global-median threshold (14.345) depends on them.
3. **Missing rounds affect inputs and labels differently:**
   - 2025-Q2 and 2025-Q3 have no label, so they cannot be training rows or targets.
   - Their rounds are also absent as **inputs**, so forecasts made after their publication used a stale SWS value (the 2025-Q4 test fold, and the 2026 origins).
4. **Timing (Rule L) depends on the composition.** An averaged label is published only when its **last** round is. Under "March only", 2025-Q1's label is complete on 2025-04-04 (CPI) or about mid-April (provincial CPI). Including January and February would not change that date, but their own release dates are [U].

## Options (no recommendation made)

| Option | Definition | Effect on 2021–2025 labels | Main consideration |
|---|---|---|---|
| A. Keep current | Fieldwork quarter; average the rounds when there are two; 2025-Q1 = March only; 2025-Q2/Q3 unlabelled | None | Inconsistent round count. The respondent change is undisclosed in the label itself. |
| B. Average all rounds fielded in the quarter | Fieldwork quarter; mean of every round | 2025-Q1 would include January and February (registered voters). 2025-Q2 would average April and June, once collected. 2025-Q3 would gain a label once collected. | Consistent rule, but mixes respondent populations and needs the missing values |
| C. Latest round in the quarter only | Fieldwork quarter; the last-fielded round | 2021-Q2 and 2022-Q2 would use June only. 2025-Q1 is unchanged. 2025-Q2 = June; 2025-Q3 = September (after collection). | One round per label; earliest possible publication; discards the earlier rounds |
| D. Comparable population only | As A or C, but flag or exclude rounds outside the household-head design | 2025 labels flagged or excluded unless comparability is established | Most comparable series; fewer labels (2025 weakened) |
| E. SWS's own quarter naming | Use SWS's "First/Second Quarter" labels | Shifts 2021 and 2022 rounds back a quarter | Conflicts with Rule 3 (a label would be set by data collected after the quarter); not recommended by the existing fetcher note |

**Decision requested:**

1. Which option governs (A–E, or a variant).
2. How the respondent-population change in 2025 is treated.
3. Whether to authorize collecting the missing April, June and September 2025 rounds (dates already established) so the chosen definition can be applied consistently.

Changing the definition changes labels and the threshold, so it is a methodology change.
