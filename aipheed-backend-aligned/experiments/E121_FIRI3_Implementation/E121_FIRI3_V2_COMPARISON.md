# E121 FIRI3 vs FIRI v2

**Basis.** FIRI v2 values come from the served history `backend/data/thesis/firi2_history.csv`, read only. They are matched to FIRI3 on origin quarter and province: **75 province-quarters, 15 origins**. 20 v2 rows have no FIRI3 because fewer than 4 indicators were available. FIRI v2 has no regional index.

## 1. Side by side

| | FIRI v2 | FIRI3 |
|---|---|---|
| Inputs | 12 indicators, 6 code domains (A V C E N H), including H1 regional hunger and A1 (a LightGBM output) | 34 features → 6 indicators; no SWS, no model output |
| Weights | Walk-forward evidence weights from SWS (mean over matched rows: C 0.40, H 0.20, A 0.13, E 0.13, V 0.12, N 0.02) | Equal |
| National values in provincial scores | C1, C2, E1, E2, H1 | None |
| Completeness rule | ≥ 4 of 6 domains | ≥ 4 of 6 indicators (provincial), ≥ 4 of 5 (regional) |
| Verification share | Not reported | Reported: provincial mean 8.6%, regional 16.9% |
| Score distribution (matched) | 81.3% HIGH (≥ 0.5) | 44.0% ≥ 0.5; bands: 42 usual or below, 30 above usual, 2 elevated, 1 high |
| Mean quarterly change | 0.072 | 0.063 |
| Regional score | none | 10 quarters (2024-Q2+) |
| Sensitivity to a missing domain/indicator | Not reported | Reported per score (leave-one-out range, mean 0.13) |

## 2. Agreement

| Measure | Value |
|---|---|
| Spearman, all matched rows | **−0.298** |
| Same side of 0.5 | **38.7%** |
| Mean Spearman of the province ranking per quarter | −0.067 |

## 3. Why they disagree: decomposition of FIRI v2

| FIRI3 correlated with … | Spearman |
|---|---|
| v2 A domain (affordability) | **+0.391** |
| v2 N domain (news) | +0.329 |
| v2 V domain (vulnerability) | −0.055 |
| v2 C domain (climate and production) | −0.099 |
| v2 E domain (national economy) | −0.179 |
| v2 H domain (regional hunger) | **−0.347** |
| v2 recomputed without H | −0.125 |
| v2 recomputed without H and E | +0.105 |
| v2 recomputed from its A and V domains only | **+0.287** |

**v2 vs its own H domain:** Spearman +0.448.

**Explanation.**
1. **The negative correlation comes from v2's regional-hunger domain (H) and its national domains.**
   - H is v2's regional-hunger outlook and drives v2 (ρ +0.45). In the matched quarters it moved against FIRI3's provincial evidence (ρ −0.35). The data cannot say whether that reflects a real link between hunger and prices or coincidence over 15 quarters.
   - With H and E removed, v2 and FIRI3 correlate slightly positively.
   - On the shared concepts they agree in direction: price affordability +0.39; v2's provincial A and V domains +0.29.
2. **v2's 81% HIGH share** is driven by H and by the SWS-derived weights on C and H. Neither is in FIRI3.
3. **The province rankings are unrelated** (−0.07).
   - v2 orders provinces through V1 (poverty with 40% density) and provincial A/C.
   - FIRI3 orders them mainly through annual employment ranks and poverty (DI-1).

## 4. What this does and does not show

**It shows that the two indices measure different things.**
- **v2:** partly the regional hunger outcome, weighted toward it.
- **FIRI3:** the non-outcome risk evidence.

**It does not show that FIRI3 is better.** No provincial outcome exists to judge either.

**FIRI3 was not tuned toward v2, and SWS was not used to adjust it.** The SWS figures in the final recommendation are descriptive only.
