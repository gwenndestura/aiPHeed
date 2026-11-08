# E134 provincial estimation report (Cavite, Laguna, Batangas, Rizal, Quezon)

**Status.**
- No quarterly provincial food-insecurity measurement exists (E130 gate; E131–E134).
- Provincial values are therefore **model-based estimates, not measurements and not validated forecasts**.
- The E134 selected candidate is HFM-X, the same as E133. The provincial seal therefore remains E133's `E133_PROVINCIAL_MODEL_BASED_SEAL.csv` (sha256 `76c2388a…`), unchanged:
  - Balance Luzon HFM-X forecast × EB-shrunk relative food deprivation (PFDR 2023), with Monte Carlo 80 % intervals.

## Estimates for 2027-Q1 (Lead 2) and their support

| Province | Estimate [80 % interval] | Supporting data | Geographic assumption | Validation evidence | Independently validated? |
|---|---|---|---|---|---|
| Batangas | 21.6 [13.5–34.0] | PFDR 2021 1.0 / 2023 1.4; FNRI FIES 2021 29.7; FIES 2023 bottom-decile food share 47.3 %, savings rate 15 % | Inherits Balance Luzon dynamics | Survey years only | **No** |
| Cavite | 16.5 [9.6–27.7] | PFDR 2.4 / 0.8; FNRI FIES 2021 31.7; food share 50.3 %, savings rate 18 % | Same | Survey years only | **No** |
| Laguna | 20.6 [12.9–32.3] | PFDR 2.4 / 1.3; food share 52.3 %, savings rate 8 % | Same | Survey years only | **No** |
| Quezon (excl. Lucena in FIES tables) | 16.3 [9.9–25.9] | PFDR 6.6 / 0.9; food share **65.4 %**, savings rate **−2 %** (bottom decile dissaving) | Same | Survey years only | **No** |
| Rizal | 29.3 [18.7–44.7] | PFDR 0.9 / 2.6; food share 53.4 %, savings rate 10 % | Same | Survey years only | **No** |

## New E134 evidence: the provincial ordering depends on the measure

FIES 2023 Tables 7–8 (acquired in E134; `out/pv_provincial_household_stress.csv`) give two household-stress indicators for the poorest decile: food-expenditure share and savings rate.

| Rank (1 = most stressed) | PFDR 2023 | Bottom-decile food share | Bottom-decile savings rate |
|---|---|---|---|
| 1 | Rizal | **Quezon** | **Quezon** |
| 2 | Batangas | Rizal | Laguna |
| 3 | Laguna | Laguna | Rizal |
| 4 | Quezon | Cavite | Batangas |
| 5 | Cavite | Batangas | Cavite |

**Rank agreement with PFDR (Spearman, n = 5):** food share 0.00; savings rate −0.10.

**Sensitivity.** Scaling the same Balance Luzon forecast (22.9) by relative bottom-decile food share instead of relative PFDR would give:

| Province | Food-share scaling | PFDR scaling |
|---|---|---|
| Batangas | 20.2 | 21.6 |
| Cavite | 21.4 | 16.5 |
| Laguna | 22.3 | 20.6 |
| Quezon | **27.9** | 16.3 |
| Rizal | 22.7 | 29.3 |

**Quezon moves from lowest to highest.** The provincial *ordering* is therefore **not robust** to the choice of deprivation measure, which confirms E131 X3c (poverty against subsistence). The intervals above do **not** include this measure uncertainty, which is larger than the sampling uncertainty.

## Methods evaluated

| Method | Data required | Available? | Verdict |
|---|---|---|---|
| Independent provincial quarterly measurement | Quarterly provincial survey | No | Not possible |
| Small-area estimation (Fay–Herriot) | Direct provincial estimates at repeated times + covariates | Only 2021 and 2023 PFDR; FNRI for 2 provinces | Survey-year SAE possible; quarterly SAE not possible |
| FIES microdata | FIES 2023 PUF (held), 2021 (archive) | 2023 only | Used for decomposition (E131) and stress (E134) |
| CBMS LGU FIES | CBMS 2024 | Not held (request) | Best cross-sectional validation if obtained |
| Multilevel pooling across provinces | Repeated provincial outcomes | Two time points | Not identifiable for dynamics |
| Province-specific economic conditions (provincial CPI, palay, NASA POWER) | Held | Yes | They can describe provincial pressure, but with no provincial outcome their link to provincial hunger cannot be estimated or validated |

## Conclusion

- **Provincial estimates are defensible only as labelled, uncertainty-aware, model-based estimates.**
- Their ordering depends on the deprivation measure; this must be shown to users.
- Independent validation needs CBMS 2024 FIES or repeated provincial FIES/FNRI rounds.
