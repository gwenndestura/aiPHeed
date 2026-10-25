# E111 Audit of E110 metrics and implementation

**Sources:**
- `out/audit_e110.json` (`runner/audit_e110.py`);
- `out/audit_dm_kernel.json` (`runner/dm_kernel_audit.py`).

Recomputed from E110's saved predictions (`E110_Hunger_Generalization/out/panel_lead*.csv`) and its code. **E109 and E110 files were not modified**; every correction lives in E111.

| Check | Finding | Verdict |
|---|---|---|
| MAE recomputed from saved predictions | Matches the reported values to ≤ 1.04e-9 at Leads 1–4 | **Correct** |
| Same origins and targets for every method | All methods are present on every row (`all_methods_on_same_rows = true`) | **Correct** |
| Same information cutoff for baseline and candidates | 116 rows checked: the latest reading comes from rounds published before the issue date, and the LLR forecasts reproduce. 0 violations. | **Correct** |
| Significance test accounts for temporal dependence | **Defect.** The helper inherited from E109 and E110 summed autocovariances with uniform (truncated) weights, not Newey–West. That variance can be negative, which turned into p = 0 at Leads 4–6 in E111's first scoring. Corrected with Bartlett weights (E111 Addendum 1). | **Defect, corrected in E111.** E110 Lead-2 COMB p 0.098 → **0.120**: its only "P1 pass" disappears. E110 Lead-2 LLR p 0.127 → 0.144. E109 Lead 1 is unchanged (lag 0). |
| Bootstrap CIs | Quarter-level block bootstrap, which is appropriate. The 90% interval of the E110 Lead-2 mean differential includes 0 for LLR (−1.61, +0.17) and COMB (−0.90, +0.06). | **Consistent with no significant gain** |
| Area panel: genuine observations | 23 rounds × 4 areas from SWS releases (2023–26 read directly) or news reports of them (2021–22) | **Genuine.** 2021–22 values are secondary-sourced. |
| The inferred 2021 cells | June 2021 Metro Manila, Visayas and Mindanao were inferred from "fell … from" or "stayed at" wording. They are **never evaluation outcomes** (the first evaluated target is 2024-Q1 in E110, 2023-Q2 in E111); they enter only as training history. E111 sensitivity S-NOINF removes them: ASYM Lead-1 MAE 4.51 (vs 4.44), LLR Lead-2 4.85 (vs 4.83). | **Handled correctly; conclusions unchanged** |
| Do the extra areas add independent information? | Quarter-to-quarter changes correlate weakly across areas (−0.11 to +0.41). Lead-1 errors of the latest reading correlate on average 0.30, which is worth about **2.1 independent areas per quarter**. | **Partly independent.** E110 correctly clustered inference by quarter. |
| "40–90% of change variance is survey noise" | The share is the assumed sampling variance ÷ the observed change variance (17 changes; 95% CI of the variance 11.5–48.2): **17–72%** at the ±4% margin and **39–>100%** at ±6%. The supporting lag-1 autocorrelation (−0.45) has a 90% bootstrap interval of −0.84 to +0.06, which includes zero. SWS margins assume simple random sampling, and design effects are not published. | **Overstated in E110.** Correct statement: "plausibly a substantial share, between about one-fifth and all of the variance; not precisely estimable from 17 changes." |
| "±6-point (80%) band" | Empirical coverage of the latest-reading 80% interval: **65% (panel), 50% (Balance Luzon, 5 of 10)** at Lead 1; 72% / 75% at Lead 2. Mean half-width 7.1 (panel), 5.2 (BL). | **Not supported.** The band under-covers; it is not an 80% interval. |
| Regime change | BL mean 10.9% (2021-Q2..2023-Q3) vs 20.0% (2025-Q2..2026-Q3), Welch p = 0.0008 | **Measured finding** |
| Survey-design effect (1,500 vs 1,200 rounds, 2025–26) | BL +5.3 points (p = 0.04, 4 vs 3 rounds); Metro Manila +2.8 (p = 0.18); Visayas −1.1 (p = 0.72); Mindanao +2.7 (p = 0.66). Design and season are confounded (March/September vs June/November). | **Hypothesis, not established** |
| Horizon description | E110 said "Lead 1 is effectively two quarters ahead". Confirmed by the issue-date table: 19 of 21 issue dates. | **Correct**, now documented per issue date |

## Corrections made in E111

1. Diebold–Mariano variance → Bartlett-weighted Newey–West (Addendum 1).
2. Noise-share wording → a range with its uncertainty.
3. The "±6-point 80% band" claim → withdrawn. The coverage evidence is reported.
4. Lead semantics → "lead" and "true horizon" (target minus newest observed quarter) are now reported separately.
5. E110's panel eligibility required the national-indicator model to be fittable, which cut the panel from 13 to 10 quarters at Lead 1. E111 uses the method-independent eligibility (every area has ≥ 6 known quarters), so all methods are compared on the larger common set.
