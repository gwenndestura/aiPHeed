# E109 Lead-time reliability report

**Target.** SWS Balance Luzon Total Hunger (% of families), continuous, regional; issue date = day 1 of the quarter after the origin.
**Rule** (frozen before scoring; `PROTOCOL.md` §7):

| | Criterion |
|---|---|
| C1 | ≥ 8 evaluated quarters |
| C2 | MAE below the best baseline, with Diebold–Mariano p < 0.10 |
| C3 | MAE ≤ 4.0 points (SWS's published Balance Luzon margin) |
| C4 | better than the best baseline in both halves of the period |
| C5 | not worse than the best baseline on the last 4 quarters |
| C6 | confirmed on unseen outcomes |

**Status:** reliable = all six; provisional = C1–C5; not reliable; insufficient evidence = C1 fails.

## Decision table (primary candidate: LightGBM, all 12 families eligible)

| Lead | Target | Quarters (rows) | LGBM MAE (block 95% CI) | Best baseline MAE | LGBM last-4 MAE (best baseline) | C1 | C2 | C3 | C4 | C5 | C6 | **Status** |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | H_{t+1} | 9 (9) | 4.04 (1.99–6.57) | RW 3.72 (1.94–5.65) | 1.38 (RW 0.94) | ✔ | ✘ (p = 0.72) | ✘ (4.04 > 4.0) | ✘ | ✘ | ✘ | **not reliable** |
| 2 | H_{t+2} | 7 (7) | 5.62 (4.08–6.63) | MA2 3.92 | 5.38 (MA2 3.04) | ✘ | ✘ | ✘ | ✘ | ✘ | ✘ | **insufficient evidence** |
| 3 | H_{t+3} | 6 (6) | 4.49 (2.61–7.19) | MA2 3.26 | 4.15 (MA2 3.33) | ✘ | ✘ | ✘ | ✘ | ✘ | ✘ | **insufficient evidence** |
| 4 | H_{t+4} | 5 (5) | 4.04 (3.21–4.04) | MA2 3.19 | 3.84 (MA2 2.39) | ✘ | ✘ | ✘ | ✘ | ✘ | ✘ | **insufficient evidence** |

**Other candidates at Lead 1:** LL (MAE 4.53) and RIDGE (4.49) are also **not reliable**; both fail C2, C3, C4 and C5. At Leads 2–4 every candidate has insufficient evidence.

**Binary readings (secondary).**
- **B1 and B2** are insufficient evidence at every lead: every evaluated quarter is HIGH.
- **B3 (> 20%)** at Lead 1 meets the binary rule for LGBM and RIDGE (accuracy 0.78, balanced 0.78, 9 quarters, 4 HIGH). This is **provisional at best**: one of four sensitivity thresholds, a one-quarter margin over persistence, and no unseen confirmation.
- **B4** is not reliable.

**Baselines' usable accuracy** (C3 only, not a reliability claim): the latest reading (RW) has a Lead-1 MAE of 3.72, inside the ±4-point survey margin; the next reading falls within ±4 of it in 56% of quarters.

## The answer

- **Maximum lead tested:** 4 quarters.
- **Maximum reliable lead time:** **none established.**
- **Maximum provisional lead:** none.
- **Confirmed on unseen outcomes:** no. No hunger quarter after the protocol was frozen has been published. The first scorable target, 2026-Q4, is expected around January 2027.

**Why.**
1. **Lead 1:** the model cannot beat carrying the latest SWS reading forward. Hunger moved in large steps (14 → 25% in 2024, 25 → 16% in 2025) that no 2021–2026 input anticipated. Part of each step is survey noise (±4–6 points).
2. **Leads 2–4:** too few evaluable quarters (5–7). The study window starts in 2021, the first outcome is 2021-Q2, three quarters have no non-commissioned round, and each lead needs 8 training pairs before its first forecast.

**A constant forecast and accuracy.** On B1 (> 11.3%) "always HIGH" scores 100% at every lead, because hunger has stayed above 11.3% since 2023-Q4. This is why accuracy against that threshold says nothing about skill, and why the continuous error is the primary measure.

**Missed rises and false alarms (B4, rise > 4 points, Lead 1).**
- LGBM flagged 0 of the 3 rises (2024-Q2, 2024-Q4, 2025-Q3).
- A missed rise means DA learns of the surge only when SWS publishes, about 1–3 months after the quarter.
- A false alarm would trigger unneeded checks; none occurred because no rise was forecast.

## What would be needed to decide the lead time

1. **More hunger quarters.** The SWS hunger item has been asked since 1998 (more than 100 rounds; S1). The study's 2021+ window leaves 20 quarters. Extending the window, which needs the researcher's authorization under the project's study-window rule, would allow a proper rolling-origin test at Leads 1–4.
2. **Area-level SWS series** for Metro Manila, Visayas and Mindanao, to learn hunger dynamics jointly. These are new data, not yet collected.
3. **A provincial outcome:** PSA CBMS food-shortage items, or FNRI FIES by province.
4. **Prospective quarters:** the sealed file (`out/sealed_prospective.csv`, sha `61bcc353…`) is scored by `runner/score_prospective.py` as SWS publishes each quarter.
