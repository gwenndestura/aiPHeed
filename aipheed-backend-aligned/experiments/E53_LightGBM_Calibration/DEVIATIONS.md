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
