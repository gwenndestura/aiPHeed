# Does T43 measure food insecurity? (E83 audit)

The numbers come from `runner/analyze.py` (`RESULTS.json → t43_audit`) and the hunger check in REPORT §5. All data
fall in 2021-01 .. 2026-10-14.

## 1. What T43 is

- **Rule.** HIGH = Balance Luzon SWS involuntary hunger > 11.3% **and** (province food CPI YoY > its P60, **or** food
  minus headline YoY > its P60). Otherwise LOW.
- **Thresholds.** Frozen on 2021–22.
- **Classification of the parts:**

  | Part | What it is |
  |---|---|
  | SWS involuntary hunger (Balance Luzon) | a **direct observation** of household hunger, one regional value per quarter (about ±4–5 points of sampling error) |
  | Province food CPI conditions | **predictive indicators** of economic access (prices), not observations of food insecurity |
  | T43 | a **constructed proxy** combining the two |

## 2. What the data show

| Check | Result |
|---|---|
| Evaluated target quarters (2023-Q1 .. 2026-Q3) | 13 quarters, 65 province rows, 16 HIGH (24.6%) |
| Quarters since 2023-Q4 with hunger above 11.3% | **10 of 10** |
| Agreement of T43 with the price condition alone since 2023-Q4 | **100%** |
| Correlation of regional hunger with the five-province mean food inflation (2023–26) | **−0.61** |
| HIGH by province (evaluated rows) | Cavite 4, Laguna 4, Quezon 5, Rizal 0, Batangas 3 |
| HIGH by year | 2023: 3; 2024: 8; 2025: 4; 2026: 1 |

## 3. Interpretation

1. **Since 2023-Q4 the hunger condition has been switched on in every quarter.**
   - T43 has therefore been identical to the provincial food-price condition.
   - In its current regime it measures **food-price pressure**, not food insecurity.
2. **The two parts moved in opposite directions in this window.**
   - Hunger rose to 22–25% in 2024-Q4 .. 2026-Q1.
   - Food inflation fell after the July 2024 rice-tariff cut (EO 62) and the 2025 rice measures.
   - So T43 turned LOW in 2025–26 while measured hunger was at its highest.
   - **This is a construct-validity failure**, not a modelling failure.
3. **Rizal is never HIGH.** Its food P60 threshold (7.1%) was set during the 2021–22 window, and the province never
   exceeded it again. Provincial differences in T43 come only from provincial price thresholds.
4. **There is no provincial outcome to validate against.**
   - SWS publishes no provincial hunger figure.
   - FNRI FIES (NNS 2025) is available only for the region: CALABARZON 22.6% moderate or severe, from secondary
     reporting.
   - CBMS 2024 municipal data are not in the project.

## 4. Alternatives compared (not substituted; the approved T43 is kept)

**(a) Direct regional hunger** (SWS > 11.3%, 13 regional quarters):

| Lead | Persistence accuracy | Always-HIGH accuracy |
|---|---|---|
| 1 | 0.85 | — |
| 2 | 0.69 | 0.77 |
| 3 | 0.54 | — |

- Persistence MAE at Lead 2 is 5.0 points.
- Nothing has beaten the latest reading at Lead 2 (E69, E76, E80).
- This is the more valid food-insecurity target, but it has one value per quarter for the whole region, so it cannot
  rank provinces.

**(b) FIRI v2** (the served index): an evidence-weighted composite of six domains. It is multidimensional by
construction and is validated only against regional SWS hunger (E71–E73), so it is development evidence.

## 5. Recommendation for the thesis

- **Keep T43 as the approved evaluation target**, and state plainly that:
  - since 2023-Q4 it equals provincial food-price pressure;
  - in 2025–26 it moved against measured hunger.
- **Report the direct-hunger results next to it.**
- **Make provincial validity a defence point.** It needs an outcome measured by province, such as CBMS 2024 FIES-type
  modules or provincial FIES from FNRI. Changing the target is the adviser's decision. E83 does not make it.
