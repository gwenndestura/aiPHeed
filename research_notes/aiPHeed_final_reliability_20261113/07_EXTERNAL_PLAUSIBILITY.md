# 07 — External plausibility checks (context only; none is provincial HFIAS ground truth)

Script: `scripts/ext_checks.py`. Evidence:
- `evidence/EXT_summary.json`
- `EXT_A_region_fies2023_vs_final2022.csv`
- `EXT_A_calabarzon_provinces.csv`
- `EXT_B_province_final2022_vs_poverty.csv`
- `EXT_C_sws_balance_luzon_context.csv`

Forecasts used:
- FINAL rows of the sealed ENNS 2022 forecast (`71ebe142`, equal to `4ad9267f` within 5e-7);
- the live experimental 2027-Q1/Q2 FINAL probabilities (`aipheed_hcw/backend/data/etmix/out/rows.csv`, column `p_own_survey_gap`);
- the retrospective test rows.

## A. PSA/FNRI FIES 2023 vs FINAL
FIES uses a 12-month recall and is a different instrument at a different geographic level.

**CALABARZON:**
- FIES 2023 moderate-or-severe: **19.1 % (95 % CI 17.0–21.1)**, the lowest of the 15 regions compared.
- FINAL's sealed 2022 regional mean probability of HIGH: **0.019**, the 3rd lowest.
- Every CALABARZON province is LOW in every FINAL forecast.

| Province | Retrospective (observed HFIAS; FINAL p) | Sealed 2022 L1 p | Live 2027-Q1 p | Live 2027-Q2 p |
|---|---|---|---|---|
| Batangas | 2021: 39.9 %; p 0.009 | 0.007 | 0.001 | 0.001 |
| Cavite | 2021: 35.5 %; p 0.012 | 0.001 | 0.003 | 0.003 |
| Laguna | 2018: 26.2 %; p 0.024 | 0.008 | 0.001 | 0.001 |
| Quezon | 2019: 44.0 %; p 0.114 | 0.043 | 0.006 | 0.005 |
| Rizal | 2019: 39.1 %; p 0.035 | 0.035 | 0.003 | 0.003 |

**All regions:** across 15 matched regions, Spearman ρ between FIES 2023 and FINAL's 2022 regional mean p = **0.835** (p = 0.0001). NCR and BARMM were not matched, because FINAL has no NCR provinces and the seal uses ARMM.

**What this does not show:**
- No CALABARZON province has been HIGH since 2015, so the region tests only that FINAL avoids false alarms there.
- Part of the regional agreement is built into the model: FINAL's strongest input is regional GRDP per capita.

## B. PSA provincial poverty incidence vs FINAL
- Poverty in 2023 was published after the 2022 seal's origin and is not an input at that origin.
- Spearman ρ between FINAL's sealed 2022 L1 p and poverty incidence: **0.60** for 2023 and 0.60 for 2021 (77 provinces).
- **Reference (2021 round, 25 provinces):**
  - the *observed* HFIAS tracks poverty 2021 at ρ = 0.55;
  - FINAL's 2021 forecasts track it at ρ = 0.87.

**Reading:** FINAL's ranking is plausible, since poorer provinces get higher risk. But FINAL follows structural poverty more closely than food insecurity itself does. Agreement with poverty is therefore evidence of plausibility, **not of predictive skill**.

## C. SWS hunger, Balance Luzon (household heads, 3-month recall, area level; context only)

| Year | SWS BL hunger (mean of rounds) | Luzon test provinces | Observed HFIAS mod+sev mean | FINAL mean P(HIGH) |
|---|---|---|---|---|
| 2018 | 10.2 % | 11 | 36.6 % | 0.366 |
| 2019 | 8.5 % | 10 | 37.2 % | 0.316 |
| 2021 | 12.6 % | 14 | 38.4 % | 0.064 |
| 2022 | 11.1 % | 37 (sealed) | not available | 0.064 |
| 2026 | **21.1 %** | 5 (CALABARZON live) | not available | 0.003 |

**Reading:**
- Between 2018 and 2021, the observed Luzon HFIAS means were roughly flat while SWS hunger moved a few points. The two measures did not move together, which confirms they cannot stand in for each other.
- **Tension to flag:** SWS Balance Luzon hunger has roughly doubled since 2022 (about 11 % to about 21 %), while FINAL's live CALABARZON forecasts are near zero.
  - This does not show FINAL is wrong: HIGH needs ≥ 50 % HFIAS, and CALABARZON's 2023 FIES is the lowest in the country.
  - In the live fits, every CALABARZON forecast is set mainly by the survey anchor (29.6–32.8 %) and the elapsed-time trend term (−0.35 to −0.45 logit).
  - News contributions are at most ±0.08 logit and climate +0.05 to +0.07. Nothing in the model moves with the 2024–2026 rise in self-rated hunger.
  - Only the next FNRI provincial round can settle this.
