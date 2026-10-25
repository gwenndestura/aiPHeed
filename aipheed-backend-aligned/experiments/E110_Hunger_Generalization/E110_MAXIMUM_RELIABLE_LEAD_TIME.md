# E110 Maximum reliable lead time

**Target.** SWS Total Hunger (%), Balance Luzon primary, 4-area panel for generalization. Issue date = day 1 of the quarter after the origin.

**Criteria** (frozen before scoring; `PROTOCOL.md` §3):

| | Criterion |
|---|---|
| P1 | ≥ 8 quarters, skill vs RW with Diebold–Mariano p < 0.10 |
| P2 | Balance Luzon MAE ≤ RW and ≤ 4.0 points |
| P3 | better in every third, in rising and falling quarters, and after the 2025 change |
| P4 | survives removing any single quarter |
| P5 | not worse on the last four quarters |
| P6 | confirmed on unseen outcomes |

**The 75% accuracy requirement** applies only to the research-defined binary readings (§4 of the comparison report). There, accuracy never measures skill: B4's 75% equals the share of quarters with no rise.

| Lead | Method | Quarters (rows) | MAE (RW) | Paired p | P1 | P2 | P3 | P4 | P5 | P6 | **Status** |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | LLR (primary) | 10 (40) | 5.46 (5.26) | 0.64 | ✘ | ✘ BL 4.66 | ✘ | ✘ | ✔ | ✘ | **not reliable** |
| 1 | COMB | 10 (40) | 5.25 (5.26) | 0.48 | ✘ | ✘ BL 4.09 | ✘ | ✘ | ✔ | ✘ | not reliable |
| 1 | NAT-R | 10 (40) | 7.45 | 0.97 | ✘ | ✘ | ✘ | ✘ | ✘ | ✘ | not reliable |
| 1 | LGBM-R / RIDGE-R | 5 BL | 2.46 / 3.74 (2.11) | — | ✘ | ✘ | ✘ | ✘ | ✘ | ✘ | insufficient evidence |
| 2 | LLR | 8 (32) | 5.39 (6.12) | 0.13 | ✘ | ✘ BL 4.65 | ✘ | ✔ | ✔ | ✘ | **not reliable** |
| 2 | COMB | 8 (32) | 5.69 (6.12) | **0.098** | ✔ | ✘ BL 4.62 | ✘ | ✔ | ✔ | ✘ | not reliable |
| 2 | LGBM-R / RIDGE-R | 2 BL | — | — | | | | | | | insufficient evidence |
| 3 | all | 6 (24) | LLR 3.52, MA2 3.34 (4.04) | ≥ 0.18 | ✘ (< 8 q) | | | | | | insufficient evidence |
| 4 | all | 5 (20) | MA2 3.32 (3.77) | ≥ 0.40 | ✘ | | | | | | insufficient evidence |
| 5 | all | 3 (12) | — | — | ✘ | | | | | | insufficient evidence |
| 6 | all | 1 (4) | — | — | ✘ | | | | | | insufficient evidence |

**Results.**
- **Maximum lead tested:** 6 quarters (panel).
- **Maximum provisional lead:** none.
- **Maximum reliable lead:** **none established.**
- **Confirmed on unseen outcomes:** no.
  - The first scorable quarter is 2026-Q4, expected around January 2027.
  - Seal: `out/sealed_prospective.csv`, sha `81f0b237…`.

**Why no lead passes.**
- **Lead 1:** nothing beats the latest reading.
- **Lead 2:** smoothing beats it on average, but not during the rising 2024 period or in Balance Luzon.
- **Leads 3–6:** the 2021+ window leaves fewer than 8 evaluable quarters.

Neither the end of the data nor the latest displayed target quarter is evidence of reliability.

**What the evidence does support (not a reliability claim).**
- The latest published Balance Luzon reading forecasts the next quarter with an average error of about 3.7–3.9 points, close to the survey's own ±4-point margin.
- Over 2–3 quarters, averaging recent readings (MA2/LLR) has tended to reduce errors in calm periods, but not during surges.
