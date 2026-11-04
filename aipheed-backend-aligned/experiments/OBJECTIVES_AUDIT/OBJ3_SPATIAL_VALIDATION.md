# Objective 3: spatial validation of the province and LGU outputs

**Status:** read only, no model fitted. Script `runner/obj3_spatial.py` → `out/obj3_spatial.json`,
`out/obj3_lgu_rank_intervals.csv`. Issue 2026-10-01, Lead 1 (target 2026-Q4), regional C-b probability 0.8595.

## 1. What each number is

| Output | Meaning | Is it measured? |
|---|---|---|
| SWS Balance Luzon hunger | Survey share of families with involuntary hunger | **Measured** (regional) |
| C-b probability | P(BL hunger > 11.3% next quarter) | Forecast, regional |
| Province score | C-b P × province family poverty incidence 2023 / the highest province's (Quezon 6.9%) | **Vulnerability-weighted index**, not a probability of provincial hunger |
| LGU risk index | Province score × (0.6 poverty_norm + 0.4 density_norm, min-max within province) | **Vulnerability-weighted index**, not a measured municipal rate |

## 2. Correctness (independent recomputation)

| Check | Result |
|---|---|
| Province poverty read from the PSA source table (`psa_poverty.csv`, OpenStat 2023) | Batangas 4.9, Cavite 4.3, Laguna 5.4, Quezon 6.9, Rizal 5.6: equals the served values |
| Province scores recomputed | max \|Δ\| 0.0 |
| 142 LGU indices recomputed (separate numpy implementation) | max \|Δ\| 1e-16 |
| Completeness | 142 LGUs: Quezon 41, Batangas 34, Laguna 30, Cavite 23, Rizal 14; no missing value |
| Poverty sources | 141 from PSA 2021 municipal SAE; **Lucena** from the 2021 official city figure (Table 2a, whole per cent): a different source, disclosed |
| Precision | **25 LGUs have SAE CV > 20%** (PSA's lower-reliability band) |

## 3. Is the weighting justified? (sensitivity; nothing chosen from it)

Poverty and density are **negatively** correlated: Spearman −0.53 over all 142 LGUs (Cavite −0.45, Laguna −0.55,
others near 0). Density with a positive weight therefore pulls dense, lower-poverty towns up.

| Weights (poverty, density) | Kendall τ vs served | Top-10 overlap | Top 5 region-wide | Rank agreement with poverty (ρ) |
|---|---|---|---|---|
| **Served (0.6, 0.4)** | 1.00 | 10 | Taytay, Lipa, San Francisco, Macalelon, San Andres | 0.65 |
| (0.8, 0.2) | 0.82 | 7 | Taytay, San Francisco, Macalelon, San Andres, Infanta | 0.78 |
| Poverty only (1, 0) | 0.71 | 6 | San Francisco, Macalelon, San Andres, Infanta, Panukulan | 0.83 |
| Density as protective (0.6, 1 − density 0.4) | 0.46 | 5 | San Francisco, Macalelon, San Andres, Infanta, Panukulan | 0.81 |
| Density only (0, 1) | 0.18 | 2 | Lucena, Taytay, Biñan, San Pedro, Sto. Tomas | −0.27 |
| Paper Eq. 6 (province score = P, no poverty factor) | 0.79 | 5 | Taytay, Lipa, Bauan, San Pascual, Taal | 0.50 |

**Reading:**
- The ranking is moderately sensitive to the density weight.
- The thesis justifies density as a vulnerability weight, presumably for exposure (more people affected). The data show
  it is not a proxy for poverty.
- **Whether density should raise risk (exposure) or not is a methodological decision for the adviser. It must be
  stated in Chapter III, not chosen from these results.**
- The served formula follows the thesis (0.6/0.4). The province poverty factor is an addition that is not in the
  paper's Eq. 6 and must be either documented or removed (adviser).

## 4. Uncertainty (Monte Carlo over the SAE CVs, 1,000 draws, served weights)

- Median 90% interval of an LGU's regional rank: **51 places** (of 142); maximum 98.
- On average only **5.9 of the served top 10** stay in the top 10 across draws.
- Taytay (89%) and Lipa (87%) are the stablest. San Andres, Infanta, Bauan, Antipolo and Agdangan fall to 23–51%.
- Per-LGU 90% rank intervals: `out/obj3_lgu_rank_intervals.csv`.

**Implication:** the LGU ranks are a **coarse** prioritisation. They should be shown as bands or intervals, not as
precise positions.

## 5. What can and cannot be validated

| Claim | Validation possible? |
|---|---|
| Values computed correctly from the PSA sources | **Yes: done** (§2) |
| LGU ranks reflect relative poverty | Yes: ρ 0.65 with the served weights (§3) |
| LGU ranks reflect measured municipal hunger | **No:** no municipal hunger data exist |
| Ranks agree with DA evaluators (H4) | **Yes, with the survey ranking task** (OBJ5 instrument §H4) |
| Province ordering vs measured food insecurity | Weak: ENNS 2021 has Batangas 29.7% and Cavite 31.7% only. aiPHeed orders Batangas (0.610) above Cavite (0.536), **the opposite** (different year and construct; 2 provinces) |

## 6. Status

**Implemented and verified as computed. Not validated as a food-insecurity ranking.** Validation needs H4 (DA
evaluators) and an adviser decision on the density weight and the province factor.
