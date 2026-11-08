# Prospective adoption criteria for REL-only (frozen 2026-10-23, before any of the scored quarters exist)

**Candidate:** FIRI v2 with the price domain = pct(REL) only, C3 walk-forward weights (E103 arm `REL-only`).
**Comparator:** the served FIRI v2. **Also tracked:** FB2, S-noA (no price domain), H1 alone (persistence), always-elevated.

## Sealing (every quarter, before the outcome exists)

On each issue date (day 1 of a quarter), before SWS posts any round of the target quarters, write the Lead-1 and Lead-2 regional and provincial values of the candidate and every tracked arm to a new sealed file with a SHA-256, using only data available on that date. Already sealed: `E102/out/sealed_prospective.csv`, `E103/out/sealed_addendum.csv` (2026-Q4 at Leads 1 and 2; 2027-Q1 at Lead 2). A sealed value is never recomputed.

## Scoring

Outcome: SWS Balance Luzon involuntary hunger, mean of all rounds of the target quarter, HIGH if > 11.3%. A quarter is scored only after all its rounds are posted.

## Adoption requires all of the following, at Lead 2, over at least **6 unseen target quarters**

1. **Probability quality:** mean Brier of the candidate lower than Served's, exact sign-flip permutation p < 0.10 (with 6 quarters the smallest attainable two-sided p is 0.031).
2. **Classification:** accuracy (HIGH at 0.5) ≥ Served's.
3. **HIGH recall** ≥ Served's.
4. **LOW quarters:** if at least one unseen LOW quarter occurs, LOW recall ≥ 0.5; if none occurs, adoption is deferred until one does, because discrimination cannot otherwise be shown.
5. **Baselines:** mean Brier lower than both H1 alone and always-elevated.
6. **Lead 1:** over the same issue dates, the candidate's mean Brier is not higher than Served's by more than 0.01.
7. **Approval:** the adviser reviews the scored file before any change to production.

## What does not count

Retrospective quarters (seen before 2026-10-23), interim looks after fewer than 6 quarters (descriptive only), any arm modified after sealing, and any quarter whose value was recomputed after its outcome was posted.
