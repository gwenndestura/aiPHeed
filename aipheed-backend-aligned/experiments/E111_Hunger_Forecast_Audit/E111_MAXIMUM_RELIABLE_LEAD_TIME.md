# E111 Maximum reliable lead time

**Rule** (`PROTOCOL.md` §4, frozen; DM test as corrected in Addendum 1):

| | Requirement |
|---|---|
| P1 | ≥ 8 quarters and skill vs RW, p < 0.10 |
| P2 | Balance Luzon MAE ≤ RW and ≤ 4.0 points |
| P3 | better in every third, in rising **and** falling rows, and after 2025-Q2 |
| P4 | survives leave-one-quarter-out |
| P5 | last 4 quarters not worse |
| P7 | surge underprediction ≤ RW |
| P8 | 80% interval coverage ≥ 0.70 |
| P6 | unseen confirmation |

**Status labels:** provisional = all except P6.

| Lead (true horizon) | Quarters / area-rows | Best method | Panel MAE (RW) | BL MAE (RW) | p vs RW | Rising / falling | Last 4 | Failed criteria | **Status** |
|---|---|---|---|---|---|---|---|---|---|
| 1 (2) | 13 / 52 | ASYM | 4.44 (4.84) | 3.19 (3.32) | 0.002 | −0.78 / **+0.27** | −0.16 | **P3**, P6 | not reliable (exploratory near miss) |
| 2 (3) | 12 / 48 | LLR | 4.83 (5.53) | **4.50** (4.76) | 0.058 | −0.23 / −1.57 | −0.97 | **P2** (BL > 4.0), P6 | not reliable (near miss) |
| 2 (3) | 12 / 48 | BRK | 4.90 | 4.46 | 0.073 | — | — | **P2**, P6 | not reliable |
| 3 (4) | 11 / 44 | LLR | 5.41 (5.98) | 5.14 (5.56) | 0.12 | — | — | P1, P2, P8, P6 | not reliable |
| 4 (5) | 10 / 40 | ASYM | 5.62 (6.37) | 5.03 (5.38) | 0.096 | — | — | P2, P3, P6 | not reliable |
| 5 (6) | 9 / 36 | ASYM | 6.72 (7.41) | — | 0.19 | — | — | P1, P2, P3, P8, P6 | not reliable |
| 6 (7) | 8 / 32 | ASYM | 7.59 (8.38) | — | 0.27 | — | — | P1, P2, P3, P8, P6 | not reliable |
| 1–4 | 9 / 7 / 6 / 5 (BL only) | LGBM12 | 4.04 / 5.62 / 4.49 / 4.04 | RW 3.72 / 4.77 / 4.08 / 3.25 | 0.72 at Lead 1 | — | — | many | not reliable (Lead 1); insufficient evidence (Leads 2–4) |

**Results.**
- **Maximum lead tested:** 6 quarters, i.e. true horizon 7.
- **Maximum provisional lead:** none.
- **Maximum reliable lead:** **none established.**
- **Confirmed on unseen outcomes:** no.

**The 75% accuracy requirement.** It does not apply to the continuous outcome. No research-defined binary reading was evaluated as a reliability claim in E111; see E109/E110, where every one failed or had insufficient evidence.

**What the evidence shows short of reliability:**
1. **One quarter ahead** (true horizon 2), surge-protected smoothing (ASYM) beats the latest reading consistently across 4 areas and 13 quarters. It reduces surge underprediction, but it is by design worse when hunger falls. It is an **exploratory candidate** for prospective confirmation.
2. **Two quarters ahead** (true horizon 3), noise-aware smoothing (LLR) beats the latest reading in every period and direction. Its Balance Luzon error (4.5 points) still exceeds the ±4-point survey margin used as the accuracy bound.
3. **Beyond two quarters,** errors grow to 5.5–8 points and no method is reliably better.

**Pending future SWS observations.** The sealed forecasts (`out/sealed_prospective.csv`, sha `adf27ba9…`; E107–E110 seals preserved) can be scored from SWS 2026-Q4 (published around January 2027). About 8 new quarters (two years) would be needed for a confirmatory test at Lead 1.
