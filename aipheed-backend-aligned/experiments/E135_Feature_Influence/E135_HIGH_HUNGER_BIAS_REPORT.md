# E135 high-hunger bias report

**Data:** P-DASH, Lead 2, S-U (40 rows, 10 quarters); terciles of observed hunger. Source: `out/e135_metrics.csv`, `out/e135_loo_audit.csv`.

## Bias by tercile

| Model | Overall | Low | Mid | High | Sharp increases within (of 16) |
|---|---|---|---|---|---|
| HFM-X | −2.53 | +1.62 | −2.10 | −7.14 | 8 |
| SEAS-LLM | −3.19 | −0.85 | −1.23 | −7.64 | 3 |
| FULL7 | −3.36 | +1.20 | −2.82 | −8.49 | 6 |
| X-RED (prior 0.5) | −2.97 | +0.22 | −1.85 | −7.38 | 3 |
| X-EXCL (post-hoc, no typhoons) | −2.59 | +1.29 | −2.17 | **−6.91** | 7 |
| X-NSD | −3.59 | −0.54 | −2.38 | −7.94 | 1 |
| X-SEL | −4.77 | −1.09 | −4.32 | −8.94 | 3 |
| X-GREG | −4.59 | −0.77 | −4.14 | −8.89 | 3 |
| X-STACK | −4.32 | −1.23 | −3.47 | −8.32 | 2 |
| X-COMB | −5.58 | −2.38 | −4.57 | −9.89 | 0 |

**About 2 of the −7 points are irreducible.** A forecaster that knew the true target level would still show −2.0 in the high tercile (E133 D4).

## Do misleading features cause the bias?

**Leave-one-out effect on the high-tercile bias** (removing the group from FULL7; positive means less under-prediction):

| Group | Change when removed | Interpretation |
|---|---|---|
| aR rainfall deficit | +0.97 | Pulls high forecasts down, because 2025–26 was wet while hunger stayed high |
| aP palay drop | +0.36 | Misleading; also harmful at Leads 2–3 |
| A rice price | +0.30 | Helps in the surge (removal +0.77 MAE) but pulls forecasts down in 2025–26 as prices fell (removal −0.66 MAE post-break). This is the 2026-Q1 case. |
| C typhoons | +0.22 | Weak or harmful |
| E unemployment change | **−1.12** | **Helps** high-hunger forecasts; removing it worsens the bias |
| N news shortage | −0.08 | Neutral |
| V poverty × market | 0.00 | None |

**Findings.**
- Removing the misleading signals (palay, typhoons) reduces the high bias by only 0.2–0.4 points each.
- The remaining bias is **lag behind true change** (ORACLE-NOW −8.3), not feature distortion.
- **Every in-fold influence procedure makes the bias worse** (−7.9 to −9.9). At the 2024 onset they had learned from calm 2021–23 errors that drivers did not help, so they shrank or dropped the market driver just before the surge.
- **"Prices fell, hunger rose" (2026-Q1):**
  - the price driver is the cause of HFM-X's miss there;
  - fixing it by dropping A post-break would need knowledge of the regime at the issue date, and the nested procedures could not supply that knowledge in time;
  - a shock-only (asymmetric) price response was worse overall (E133 PH1, 0.35).
- **No candidate reduces the high-hunger bias without damaging the other terciles.**
  - X-EXCL (−6.91) is the only small improvement, and it is post-hoc.
  - X-RED moves the low tercile toward zero (+0.22) but leaves the high tercile almost unchanged.
- **Status: not resolved.**
