# E196 results: training-selected lagged averaging of E194 (local only, not committed)

**Sources.**
- Protocol: `docs/e196/PROTOCOL.md`, whose SHA-256 was logged before the run.
- Outputs: `backend/data/e196/out/`.

**Checks.**
- The E194 re-run reproduces stored E194 (maximum |Δp| = 6e-16).
- One crash, an index bug when no averaging option exists, was fixed by defaulting to S1. The rule did not change.

## Rules chosen on training rows only
- **Lead 1: S2** (average with the Lead-2 forecast) for all three origins. Training weighted SSE improved:
  - ENNS2018: 121.8 → 117.5;
  - ENNS2019: 118.2 → 114.5;
  - ENNS2021: 76.3 → 75.9.
- **Leads 2–3: S1** (E194 unchanged).
  - ENNS2021: averaging was worse on its training rows (L2: 75.7 against 77.8 / 78.7).
  - ENNS2018/2019: no training forecasts exist at those leads.
- **Lead 4:** S3 for ENNS2021, S1 for the others.

## Results (72 real rows per lead)
| Lead | E184 | E194 | **E196** | E196 against E194: fixed / broken (p) | Brier difference against E194 [95 % CI] |
|---|---|---|---|---|---|
| 1 | 76.4 % (FA 13) | 77.8 % (FA 12) | **81.9 %** (FA 10, miss 3, B .1187) | 3 / 0 (0.25) | −0.0004 [−0.0034, +0.0021] |
| 2 | 79.2 % (FA 11) | 80.6 % (FA 11) | **80.6 %** (FA 11, miss 3, B .1188) | 0 / 0 (1.0) | 0 |
| 3 | 77.8 % (FA 12) | 79.2 % (FA 12) | **79.2 %** (FA 12, miss 3, B .1255) | 0 / 0 (1.0) | 0 |
| 4 | 77.8 % (FA 12) | 76.4 % (FA 12) | 76.4 % (FA 12, B .1228) | 0 / 0 | −0.0024 [−0.0092, +0.0028] |

- **Against E184:**
  - Lead 1: 4 fixed, 0 broken (p = 0.125); Brier −0.0024 [−0.0077, +0.0026].
  - Lead 2: 2 / 1.
  - Lead 3: 1 / 0.
- **Owner rule:** passed at Leads 1–4.

## Decision (as fixed): **E196 is preferred to E194** (candidate only; not staged)
- Accuracy is ≥ E194's at Leads 1–3, Brier is ≤ E194's at Leads 1–3, and Lead 1 is higher.

## Caveats a panel will ask about
1. **Not statistically significant.** Against E194, p = 0.25 at Lead 1; against E184, p = 0.125. The gain is 3–4
   provinces at Lead 1.
2. **Forking paths.** The selection mechanism uses training rows only. But the idea of choosing averaging per lead came
   after seeing E195's per-lead test results. E196 is therefore less independent than an experiment designed blind,
   and its 81.9 % should be confirmed on the sealed 2022 labels.
3. **The 72 rows have been reused** across E151–E196.
4. **80 % target.** Leads 1 and 2 reach it (81.9 %, 80.6 %). Lead 3 is 79.2 %, one province short (57 of the 58
   needed).
5. **Operational requirement.** Lead 1 needs the previous quarter's Lead-2 forecast for the same target. The live
   system already stores each issue (`data/e184/issues/`), so this is available.
