# DA Usefulness Assessment (E13)

**The DA question:** can aiPHeed tell DA Region IV-A, ahead of the official figures, where food insecurity will be worse among Cavite, Laguna, Batangas, Rizal and Quezon?

**Short answer.** Not with the evidence available.

- Provincial food insecurity is not measured anywhere in a repeated way, so aiPHeed's provincial food-insecurity accuracy is **unknown**. It is not low and not high.
- What aiPHeed can give DA is a **regional hunger signal** and a **provincial food-price-pressure signal**. Each comes with a measured forecast error.

## 1. What each output can honestly tell DA

| Output | What it means | Forecast skill found (retrospective, reused quarters) | Usefulness for DA |
|---|---|---|---|
| **Regional hunger** (SWS Balance Luzon) | Share of families reporting involuntary hunger, for an area wider than CALABARZON | Best: carry the latest published value forward. MAE 4.8 points. It under-forecast the 2024–2025 rise by about 3 points on average. **No model beat it.** The ridge models were worse (MAE 6.6). | **Context.** It shows when regional hunger is high against recent years. It cannot rank provinces. |
| **Provincial food inflation** (F) | How fast food prices rose in the province, year on year | Best: the province's value two quarters earlier. MAE 2.4 points. "Above 4%" flagged with balanced accuracy 0.70 (14 false alarms and 4 misses in 55). **No model beat it.** | **Price monitoring.** It is useful as an early indication, if read as price pressure only. |
| **Relative provincial price pressure** (D) | Whether a province's food prices rose faster or slower than the five-province average | Carry-forward MAE 1.36. A shrinkage model (`B2_ridge_DP`) reached MAE 1.18 and met the frozen improvement rule (see §2 for the limits). Sign right in about 70% of cases. Ranking agreement τ ≈ 0.45. | **Relative targeting of price monitoring.** It is not a food-insecurity ranking. |
| **S1 HIGH/LOW** (current dashboard label) | Regional hunger level plus 2 × relative price pressure, against a 2021–2023 threshold | HIGH in 33/35 test rows, and every province HIGH from 2024-Q2 | **Low for prioritization.** It restates the regional level (`CURRENT_MODEL_DIAGNOSIS.md`). |

## 2. The one measured improvement, in DA terms

`B2_ridge_DP` forecasts relative price pressure as **(recent deviation) shrunk, minus part of the province's long-run deviation.**

- **Size:** it lowers the average error from 1.36 to 1.18 points (13%).
- **Effect on calls:** it changes 3 of 55 "above or below average" calls (2 better, 1 worse). Two of the three were near zero.
- **Practical impact:** a DA officer reading the dashboard would see almost the same picture as with simple carry-forward. The gain is mostly in the size of the deviation, not the direction.
- **Why it cannot yet be relied on:**
  1. The quarters were examined before (7 of the 11 were E9–E12 test quarters).
  2. The idea of shrinking D came from E12's look at the same period.
  3. On the 7 E9–E12 quarters alone, it does not meet the rule. There, "no difference" (0) is the best baseline, and the interval crosses zero.
  4. Its negative weight on each province's history reflects the 2023–2024 reversals and may not persist.

## 3. Lead time and timeliness

| Output | Forecast issued | Official value available | Lead |
|---|---|---|---|
| Regional hunger for quarter T | Start of T | About 1–15 weeks after the SWS fieldwork (2021–2025 range) | About 1 to 6 months |
| Provincial F and D for quarter T | Start of T | About 3 weeks after T ends (proxy date) | About 3.5 months |

The lead time is real. However, the forecast errors are about the same size as the quarter-to-quarter movements DA would want to act on.

## 4. Risks if the current outputs are used as food-insecurity predictions

1. **False reassurance or false alarm by province.**
   - D is not related to household vulnerability across provinces (ρ = −0.05 and +0.62 against subsistence incidence, n = 5).
   - Quezon, the poorest province, had the **lowest** relative price pressure in 2023.
2. **No differentiation.** An all-HIGH label gives no basis for allocating attention.
3. **Regional values presented as provincial.**
   - Hunger (SWS) and FIES (FNRI) are regional.
   - The project's FIES file repeats one regional value five times.

## 5. What would make aiPHeed useful for DA provincial decisions

| Need | Example source | Status |
|---|---|---|
| A provincial food-insecurity outcome, repeated yearly or more often | FNRI provincial FIES or HFIAS (from microdata with provincial weights); PSA CBMS food-shortage items; a DA- or LGU-run FIES module | **Not available in the project** |
| Real-time vintages and verified release dates for provincial CPI | PSA release calendar and archived releases | Proxy dates only |
| Prospective scoring on new quarters | 2026-H2 onward (protected; sealed Q4 forecast exists from E10) | Pending |
| An adviser decision on presenting two layers (regional hunger + provincial price pressure) instead of one HIGH/LOW label | — | Pending (E12) |
