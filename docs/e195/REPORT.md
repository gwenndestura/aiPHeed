# E195 results: lagged-average forecasting of E194 (local only, not committed)

**Sources.** Protocol: `docs/e195/PROTOCOL.md` (SHA-256 starts `3c83f296a827804c`), written before the combined result
was computed. Results are in `backend/data/e195/out/results.json`. No training: the forecasts are E194's stored
probabilities.

| Lead | E184 | E194 | **E195 (mean of Leads L, L+1, L+2)** | E184 + LAF |
|---|---|---|---|---|
| 1 | 76.4 % (FA 13) | 77.8 % (FA 12) | **81.9 %** (FA 10, miss 3) | 79.2 % (FA 11) |
| 2 | 79.2 % (FA 11) | 80.6 % (FA 11) | 79.2 % (FA 12) | 76.4 % (FA 13) |
| 3 | 77.8 % (FA 12) | 79.2 % (FA 12) | 76.4 % (FA 12, miss 5) | 76.4 % (FA 12) |
| 4 | 77.8 % (FA 12) | 76.4 % (FA 12) | 73.6 % (FA 14) | 76.4 % (FA 12) |

## E195 against E194
| Lead | Provinces fixed / broken | McNemar p | Brier difference [95 % CI] |
|---|---|---|---|
| 1 | 3 / 0 | 0.25 | +0.0013 [−0.004, +0.006] |
| 2 | 0 / 1 | 1.0 | +0.0035 [−0.002, +0.011] |
| 3 | 2 / 4 | 0.69 | −0.0001 [−0.009, +0.007] |

## Decision (as fixed): **E195 is not preferred; E194 stays the best variant**

## What it shows
- **Lead 1 rises, Leads 2–4 fall.** Lead-averaging lifts Lead 1 to 81.9 % (+3 provinces, none broken) because its
  coin-flips are smoothed by the earlier forecasts. Leads 2–4 lose 1–2 provinces, because they are averaged with even
  older, less-informed forecasts.
- **No method has lifted all three leads at once.** Each one moves 1–3 coin-flip provinces from one lead to another.
  This is the expected pattern when the remaining errors are borderline cases and unpredictable large changes, not a
  fixable model weakness.
