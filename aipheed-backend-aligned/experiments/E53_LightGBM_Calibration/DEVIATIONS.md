# E53 deviations and clarifications (after the protocol freeze, before any E53 score)

## D-1: explanation mapping of the news and rice-policy inputs (explanation only; no probability or score changes)

**Found:** while preparing the explanation audit (protocol section 5), before any E53 arm was scored.

**The defect:**
- E52's record attributes only the inputs listed in the five `PRICE_GROUPS` (market, climate, fish_kill, employment, ofw_remittance) plus the base projection.
- The residual model also uses the rice-policy block (`tariff_yoy_regime`, `import_suspension_share`, `price_ceiling_share`, `food_emergency_share`) and the news block (`news_market`, `news_climate`, `news_fish_kill`, `news_employment`, `news_ofw_remittance`, `news_n`).
- Their contributions were attributed to no group, while the record states `other_pct = 0`.
- **Size:** across the 2023-Q4..2026-Q3 origins, the unattributed part of the food residual is a median of 0.10 and at most 1.01 food-inflation points (gap: at most 0.06 points). The largest values are in the 2026-Q2/Q3 origins.
- The probabilities are correct. The explanation was incomplete, so it was not fully faithful.

**The correction**, used by every E53 explanation and by the E53 rebuild of the E52-arm record:

| Input | Group | Reason |
|---|---|---|
| Rice-policy block | Market / Prices | tariff, import suspension, price ceiling and food emergency are market and price interventions |
| `news_<group>` | its own trigger group | e.g. `news_climate` → Climate Stress; the article share tagged to that trigger |
| `news_n` (total article volume) | "other" | belongs to no single trigger; reported as `other_pct`, not hidden |

**Additivity:** the ridge contributions of all inputs + the base-projection deviation reconcile with F̂ and Ĝ, as in E52 (check < 1e-8). The five groups + other now cover every input.

**Scope:** E52's committed record is kept unchanged as the E52 artifact. E53 documents the defect and serves the corrected attribution. Whether E46's record has the same gap is checked and reported in the E53 report.

## D-2: float tolerance in the E52 reproduction check (no effect on any score)

- **What happened:** the first run (`runs/20261017T135737Z`, kept with `ABORTED.txt`) stopped at the check that recomputes E52's metrics from E52's `rows.csv`.
- **Cause:** E52 computed B6_LR_COMB's Brier from in-memory probabilities, while E53 reads them back from the CSV. The two values differ by 5.6e-17, which is float round-off.
- **No E53 metric was seen:** the run stopped before any E53 metric was computed or printed. Only the per-origin probabilities had been printed.
- **Fix:** the check compares floats with an absolute tolerance of 1e-12 (accuracy CIs still exactly). The run is then repeated from scratch, with no other change.

## D-3: what is served behind `e53` when no arm is adopted (serving only; no score changes)

- **Situation:** protocol section 6 serves "an arm adopted under section 4". After run 1 and addendum I2, no calibrated arm (C1–C4) and no LightGBM arm (LGB-R, LGB-RL, LGB-C, LGB-R2, LGB-C2) passed its rule, so R0 (the E52 model) remains the development candidate.
- **What `e53` serves:** R0's probabilities, identical to E52's and to E52's frozen 2027-Q1 file, with:
  - the D-1 corrected attribution: every input is attributed, rice policy goes to Market, each news share to its own trigger, and total news volume to "other";
  - a per-trigger data-coverage field (`inputsPresent`), so a group with some inputs missing at the issue date (OFW: BSP remittances end at 2025-Q4 in the dataset) shows a "limited" data status instead of a silent "no effect".
- **No new frozen forecast:** none is written, because the R0 probabilities are E52's and are already frozen. E52 remains in the record and serving unchanged.
