# E113 Final model card: aiPHeed regional hunger outlook

| Field | Value |
|---|---|
| **Name** | aiPHeed regional hunger outlook (E113 adopted forecast) |
| **Adopted model** | **Persistence:** the latest published SWS reading. Selection tier 3 of the pre-registered rule (`PROTOCOL_E113.md` §9). No shrinkage candidate beat it. |
| **Outcome** | SWS Total Hunger (% of families experiencing involuntary hunger in the past 3 months), quarterly |
| **Areas** | Balance Luzon (primary; contains CALABARZON), plus NCR, Visayas and Mindanao as the pooled panel for evaluation and error bands |
| **Inputs** | SWS rounds published before the issue date. News, CPI and the 12 FIRI families are **not** inputs to the adopted forecast; they are context. |
| **Formula** | forecast(area, target quarter) = latest published reading of that area |
| **Error band (80%)** | forecast ± q80, where q80 is the 80th percentile of the model's own earlier out-of-sample absolute errors at the same lead, pooled over the four areas and using only targets published before the issue date. Lead 1 is about ±6.5 points over 2023–2026 and ±7.3 in seal A (pooled); it widens with the lead. |
| **True horizon** | Quarters between the newest published reading and the target. At quarter-start issue dates, Lead 1 = true horizon 2 (SWS publishes after the quarter ends). An outlook re-issued right after a new SWS release has true horizon 1. |
| **Seals** | A: issue 2026-10-01, sha `b53e8793…` (Balance Luzon 17.3%, newest 2026-Q2). B: issue 2026-10-25, sha `a86bcd49…` (Balance Luzon 23.6%, newest 2026-Q3). Both cover Leads 1–6, all models. |

## Measured performance (development; 2023–2026 targets)

| Lead | Quarters | Panel MAE (pts) | Balance Luzon MAE | Panel 80% coverage | BL coverage |
|---|---|---|---|---|---|
| 1 | 14 | 4.72 | 3.14 | **0.75** | 0.93 |
| 2 | 12 | 5.53 | 4.76 | 0.67 | 0.75 |
| 3 | 11 | 5.98 | 5.56 | 0.73 | 0.64 |
| 4 | 9 | 6.57 | 5.53 | 0.69 | 0.67 |
| 5 | 7 | 6.77 | 6.59 | 0.54 | 0.71 |
| 6 | 6 | 6.58 | 3.67 | 0.58 | 0.67 |

- **Bias.** Persistence under-forecast on average (−1.7 points at Lead 1, −4 to −5 at Leads 4–6), because hunger rose over 2023–2026.
- **Band calibration.** The band is calibrated at Lead 1 only. The pooled band is conservative for Balance Luzon, whose errors are smaller than Mindanao's or Visayas'.

## Maximum reliable lead

**None established.** No candidate meets R1–R4 at any lead (all Holm p = 1.0). The *calibrated-persistence horizon* is 1 quarter: the band is honest at Lead 1.

## Known failure regimes

- **Sharp increases.** The 2024-Q3 and Q4 surge produced 8–10-point errors at Lead 1. Persistence cannot anticipate a surge, and no tested signal could either (9 events at Lead 1; no alert claim).
- **The 2025 survey change.** From 2025-Q2 SWS interviews adults rather than household heads. The level shift cannot be separated from real change (no bridging round). Readings across the break are not strictly comparable.
- **Long leads.** Beyond Lead 1 the band under-covers (54–73%), and errors grow to about 6.5–7 points.

## Research models (appendix, not adopted)

| Model | Result |
|---|---|
| Shrinkage to persistence (SH-MR, SH-N, SH-P, SH-MRN, SH-MRP, SH-FULL) | None significantly better than persistence. Long-lead mean reversion is harmful. |
| ETS local level (baseline) | Lowest MASE at Leads 2–3 (raw p = .062, .13). Exploratory candidate for prospective testing (as E111's LLR). |
| 12-family LightGBM (E112) | Worse than persistence at every lead |

## DA IV-A usage guidance

**Usable:**
- The regional hunger outlook for Balance Luzon, stated as: "the latest SWS reading, X%, from quarter Q; for next quarter expect roughly X ± 7 points (80% of past cases)". Always show the source quarter and the true horizon.
- Re-issue the outlook as soon as SWS publishes a new round; this shortens the true horizon by a quarter.
- **News and CPI panels as situational context:**
  - disaster coverage tracks typhoons;
  - rising price coverage has preceded food-inflation upturns by about two quarters.

  They are not hunger predictors.
- The LGU table as a **vulnerability ranking** (poverty and density).

**Not usable:**
- Any provincial, city or municipal food-insecurity forecast.
- Any claim of advance warning of hunger surges.
- Any forecast more than one quarter ahead presented as calibrated.
- CPI or news presented as forecasting hunger.
