# E134 event analysis: the 2024 surge and the 2025–26 moves

**Sources.**
- `out/ev_driver_timeline.csv`: every P-DASH issue from 2023-07-01. For each driver it gives the latest quarter available at the issue (publication rules applied) and its in-fold z.
- `out/e134_predictions.csv`, and E133 `out/d3_sharp_increase_events.csv`.
- National = mean of the 4 SWS areas.

## Timeline at each issue (Lead-2 target = issue quarter + 1)

| Issue | Latest SWS | Lead-2 target | Realized change | Rice q/q z | ONI z | Unemp. change z | Area rain deficit z | Area palay drop z | Shortage news z |
|---|---|---|---|---|---|---|---|---|---|
| 2023-07-01 | 2023-Q1 | 2023-Q4 | +1.9 | −0.31 | +0.98 | +1.41 | −0.47 | −0.62 | +0.62 |
| 2023-10-01 | 2023-Q2 | 2024-Q1 | +3.9 | **+1.93** | **+2.42** | +1.06 | +0.55 | −0.49 | −0.31 |
| 2024-01-01 | 2023-Q3 | 2024-Q2 | +7.0 | **+2.76** | **+2.53** | +1.67 | +0.49 | +0.14 | +0.80 |
| 2024-04-01 | 2023-Q4 | 2024-Q3 | **+12.1** | +1.65 | +2.39 | +1.18 | **+1.04** | −0.12 | +0.26 |
| 2024-07-01 | 2024-Q1 | 2024-Q4 | **+11.1** | +1.53 | +1.94 | +0.98 | **+1.72** | +0.56 | −0.20 |
| 2025-01-01 | 2024-Q3 | 2025-Q2 | −5.2 | −0.89 | +0.13 | +1.13 | −0.68 | +1.05 | −1.07 |
| 2025-04-01 | 2024-Q4 | 2025-Q3 | −3.8 | −1.25 | −0.15 | +1.29 | −0.63 | +0.01 | −0.88 |
| 2025-07-01 | 2025-Q2 | 2025-Q4 | +0.2 | −1.69 | −0.32 | +1.31 | −0.56 | −0.22 | −0.62 |
| 2025-10-01 | 2025-Q2 | 2026-Q1 | **+4.6** | **−2.20** | +0.06 | +1.30 | −0.50 | −1.22 | −0.59 |
| 2026-01-01 | 2025-Q3 | 2026-Q2 | −0.6 | −1.43 | −0.06 | +1.25 | −1.09 | −1.03 | −0.46 |
| 2026-04-01 | 2025-Q4 | 2026-Q3 | +1.6 | −0.15 | −0.52 | +1.85 | −0.99 | +0.48 | −0.96 |
| 2026-07-01 | 2026-Q1 | 2026-Q4 | (sealed) | **+2.24** | −0.35 | +1.76 | +0.18 | +0.28 | −0.75 |
| 2026-10-01 | 2026-Q2 | 2027-Q1 | (sealed) | **+1.85** | +0.75 | +1.29 | +1.48 | −0.13 | −0.19 |

**Typhoons (PAR)** change little and are often stale under the E119 period rule (2023-Q4 is still the latest value on 2024-07-01).

## Findings by question

1. **When conditions began changing.**
   - Rice prices accelerated in 2023-Q2/Q3; El Niño conditions are visible in ONI from 2023-Q2.
   - Both were **published before** the 2023-10-01 and 2024-01-01 issues, three quarters ahead of the 2024-Q1 and Q2 targets.
2. **What moved before hunger.**
   - Rice price change, ONI and unemployment change.
   - The area rainfall deficit followed later: positive from 2023-Q4 onward, as El Niño's dry season arrived.
3. **What moved with or after hunger.**
   - The rainfall deficit was largest at the 2024-07-01 issue (+1.72), when hunger was already peaking.
   - Palay drops are mixed, and they are small at the onset.
4. **Local or national.**
   - The surge was national: every area rose.
   - The 2024-Q3/Q4 escalation was concentrated in Visayas (+16.7) and Mindanao (+18.7 to +21.6).
5. **Was the information available at the issue?** Yes for every driver above (publication rules in the leakage audit).
6. **Anticipable at Lead 2?**
   - **The onset was, in direction:** HFM-X caught 5/5 onset rows (E133).
   - **The escalation magnitude (+11 to +12 nationally, +16 to +22 in Visayas/Mindanao) was not.** No driver at the 2024-04 or 2024-07 issues was more extreme than at the onset. A linear model therefore forecast +0.5 to +7.
   - Area rainfall deficit was available in time, but adding it (E134-AREA-T) did not improve Lead 2 (MAE 5.39 against 4.87).

**Why the model forecast a decline for 2026-Q1.**
- At 2025-10-01 the rice-price driver was −2.20 (rice prices fell through 2025), so HFM-X's price channel predicted lower hunger.
- Hunger rose +4.6 instead.
- **Post-break design structure:** SEAS-LLM's quarter-of-year effect caught 2026-Q1, which points to part of the rise being the 2025+ survey design (Q1/Q3 rounds with larger samples read higher).
- **No ratchet:** treating price falls as zero (E133 PH1) made the overall results worse (0.35), so a simple ratchet is not supported.

## Root causes of the missed escalation (evidence-ranked)

1. **Missing household-level stress dynamics** (income loss, savings depletion, debt). FIES 2023 shows the poorest decile in Quezon already dissaving (−2.9 thousand pesos a year), but there is **no quarterly or area-level series** of household savings or income in 2021+.
2. **A single episode.** With 2021+ data, the models learn the size of the response to a price and ENSO shock from **one** event, and before 2024 they had seen none. They therefore under-scale the first large response. Pre-2021 SWS history (2008 rice crisis, 2020 pandemic) contains more such episodes (pre-2021 feasibility).
3. **Survey structure after 2025.** It mixes design effects with true change.
4. **Not the cause:**
   - publication delay: all drivers were available;
   - local climate measurement: the area rainfall deficit was tested;
   - survey noise: it accounts for only 12 % of the MSE.
