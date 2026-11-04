# Power and sample-size analysis (`runner/obj4_power.py` → `out/obj4_power.json`)

## Assumptions (stated, not tested)

- The observed mean per-quarter Brier gain μ and its SD σ are the true values for future quarters.
- Serial dependence is AR(1) with the observed lag-1 autocorrelation ρ (floored at 0). The inflation factor is
  (1 + ρ)/(1 − ρ).
- One-sided z test at 80% power, reported at the strictest Holm step (α/14 = 0.0036) and the loosest (0.05). A single
  comparison's real level lies between them.
- Required n = ((z₁₋α + z₀.₈) σ/μ)² × (1 + ρ)/(1 − ρ).
- **These are planning estimates, not guarantees.** They supersede the rough figures in the 2026-11-04 improvement
  report (about 6,500 and about 89 quarters), which used neither the power term nor autocorrelation.

| Lead | Baseline | n now | Gain μ | d | ρ | Significant now | Quarters needed (α 0.05 … α/14) | Extra years at 4 q/year |
|---|---|---|---|---|---|---|---|---|
| 1 | Persistence | 62 | 0.151 | 0.38 | 0.16 | ✅ | 60 … 121 | 0 … 14.7 |
| 1 | LGBM-GOV | 62 | 0.045 | 0.44 | 0.13 | ✅ | 41 … 82 | 0 … 4.8 |
| 1 | NLP-only logistic | 20 | 0.144 | 0.54 | 0.00 | ❌ | 22 … 44 | **0.4 … 5.9** |
| 1 | LGBM-NLP | 20 | 0.097 | 0.43 | 0.12 | ❌ | 43 … 86 | 5.6 … 16.5 |
| 1 | Always-HIGH | 62 | 0.119 | 0.33 | 0.48 | ❌ | 162 … 326 | 25 … 66 |
| 1 | PSA-only | 62 | 0.021 | 0.10 | 0.26 | ❌ | 1,005 … 2,026 | 235 … 491 |
| 1 | **LOGIT** | 62 | 0.005 | 0.02 | 0.12 | ❌ | **18,951 … 38,233** | thousands |
| 2 | Persistence | 62 | 0.151 | 0.38 | 0.03 | ✅ | 47 … 93 | 0 … 7.7 |
| 2 | LGBM-GOV | 62 | 0.052 | 0.43 | 0.35 | ✅ | 70 … 140 | 1.8 … 19.4 |
| 2 | NLP-only logistic | 19 | 0.215 | 0.51 | 0.09 | ❌ | 29 … 58 | **2.3 … 9.5** |
| 2 | LGBM-NLP | 19 | 0.090 | 0.36 | 0.34 | ❌ | 98 … 197 | 19.6 … 44.3 |
| 2 | Always-HIGH | 62 | 0.119 | 0.33 | 0.55 | ❌ | 196 … 396 | 34 … 83 |
| 2 | PSA-only | 62 | 0.051 | 0.23 | 0.31 | ❌ | 215 … 433 | 38 … 93 |
| 2 | LOGIT | 62 | 0.046 | 0.17 | 0.17 | ❌ | 292 … 588 | 57 … 132 |

**Check:** the four comparisons already significant need about 41–140 quarters by this approximation. That is
consistent with the bootstrap finding significance at 62 (the normal approximation is conservative here).

## Reading

- **Reachable with prospective quarters:** NLP-only logistic (Lead 1: 2–24 more news-era quarters).
- **Not reachable in any thesis timeframe:** LOGIT (Lead 1 especially), PSA-only, always-HIGH, LGBM-NLP at Lead 2.
  **"Beats all seven" cannot be established with SWS Balance Luzon quarterly data alone, at the current effect sizes.**
- **Legitimate ways to more evidence** (Part 11): see `FINAL_EXECUTION_SUMMARY.md` §Data acquisition. None duplicates
  labels across provinces.
