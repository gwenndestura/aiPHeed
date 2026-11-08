# Maximum reliable lead time, determined from the data (Addendum 3)

## Step 1: which leads can be tested at all (`out/testability.json`, no model scored)

A lead k is evaluable for target quarter q when:
- the origin t = q − k is in the study window (2021-Q1 or later);
- the training set of price labels complete before the issue date meets the frozen minimum (6 quarters, 5 HIGH, 5 LOW);
- q has a T43c label (a regular SWS round, q ≤ 2026-Q3).

| Lead | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9+ |
|---|---|---|---|---|---|---|---|---|---|
| Evaluable quarters (rows) | 14 (70) | 12 (60) | 10 (50) | 8 (40) | 6 (30) | 5 (25) | 3 (15) | 1 (5) | 0 |
| Meets R1 (≥ 10 quarters, ≥ 40 rows) | yes | yes | yes | no | no | no | no | no | – |
| Quarters after the newest published SWS survey | 1–2 | 2–3 | 3–4 | 4–5 | 5–6 | 7 | 8 | 9 | – |
| A1 base months published at the issue date | 3 | 3 | 3 | 2 | 0 | 0 | 0 | 0 | – |

**Why it stops.** The study window starts in 2021 and the last outcome is 2026-Q3. Each extra lead costs one quarter at
the start (the origin must be in 2021+) and one quarter of training labels, so evaluable quarters fall by about two per
lead. From Lead 5 on, the food-price projection has no published base month, so the model's main input is missing.
**Longest lead that can be tested credibly: 3. Longest lead that can be scored at all: 8.**

## Step 2: every evaluable lead scored, same model and rule

| Lead | Rows (quarters) | HIGH share | Accuracy (90% CI) | Balanced | Brier | Always-LOW | Persistence | Failed criteria | Reliable |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 70 (14) | 0.24 | **0.914** (0.84–0.97) | 0.883 | 0.087 | 0.757 | 0.743 | – | **yes** |
| 2 | 60 (12) | 0.28 | 0.583 (0.45–0.72) | 0.496 | 0.271 | 0.717 | 0.650 | R2–R7 | no |
| 3 | 50 (10) | 0.28 | 0.520 (0.36–0.68) | 0.427 | 0.281 | 0.720 | 0.540 | R2–R7 | no |
| 4 | 40 (8) | 0.25 | 0.575 (0.40–0.75) | 0.383 | 0.249 | 0.750 | 0.550 | all | no |
| 5 | 30 (6) | 0.20 | 0.367 (0.13–0.63) | 0.604 | 0.315 | 0.800 | 0.433 | all | no |
| 6 | 25 (5) | 0.12 | 0.360 (0.20–0.56) | 0.492 | 0.291 | 0.880 | 0.360 | all | no |
| 7 | 15 (3) | 0.07 | 0.400 (0.07–0.73) | 0.679 | 0.316 | 0.933 | 0.467 | all | no |
| 8 | 5 (1) | 0.00 | 0.000 | – | 0.507 | 1.000 | 0.400 | all | no |

Performance collapses after Lead 1 and does not recover: from Lead 2 on the model is below always-LOW, and from Lead 5
it calls almost every row HIGH (hunger stays above the line in 2024–2026, and without A1 the price model falls back to
its training base rate).

**Hunger-surge quarters** (BL up ≥ 5 points): Lead 1 20/20; Lead 2 0.60; Lead 3 0.50; Lead 4 0.40.
**Latest four quarters:** Lead 1 0.90 (always-LOW 0.95); Lead 2 0.60; Lead 3 0.45; Lead 4 0.60.

## Step 3: decision

- **Maximum reliable lead (frozen rule, consecutive):** **1**.
- **Leads passing on their own (diagnostic):** only Lead 1, so the consecutive rule changes nothing.
- **Stricter variant** (balanced accuracy above every comparator): none, because LGBM-GOV ties at Lead 1.

## Answer to the acceptance question

The maximum reliable lead is **one quarter after the issue quarter**. A forecast issued on 1 October covers
October–December, so it ends at most 92 days after issue. In SWS terms it is **2 quarters after the newest published
survey** in 13 of 14 test quarters (1 in the other), because SWS publishes each round 1–3 months after fieldwork.

Evidence that it generalises:
- 14 out-of-sample quarters 2023–2026.
- Stable thirds (0.88 / 0.96 / 0.90) and leave-one-quarter-out ≥ 0.908.
- Every hunger-surge quarter correct.
- Rows never scored before the protocol froze: 9/10.
- Exact reproduction, and leakage checks on every row.

Limits:
- 14 quarters only.
- Not significantly better than always-LOW at quarter level (p = 0.11).
- The latest block has one HIGH case.

## Dashboard

The About dialog shows three horizons:
- generated: up to 4 quarters ahead, all beyond Lead 1 labelled experimental;
- testable: 3;
- reliable: 1.

Archived sealed forecasts are labelled "(reliable)" or "(experimental)", and `/api/v1/final/risk/rows` returns
`status` and `horizon`.
