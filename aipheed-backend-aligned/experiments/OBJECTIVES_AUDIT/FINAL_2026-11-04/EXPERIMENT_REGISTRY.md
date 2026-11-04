# Experiment registry (OBJECTIVES_AUDIT attempts)

**The append-only machine registry is `NEW_MODEL/ALLBASE/REGISTRY.csv`.**
- 17 earlier rows are unchanged (checked against `backup/REGISTRY_before_2026-11-04.csv`).
- 14 rows were appended on 2026-11-04 (C-E, C-E2, C-E3, C-E4, C-E5R, C-E5C, C-E2-NONEWS; one row per lead).
- Earlier families (E-series, K1–K3, S1–S3) are recorded in their own folders and listed here for completeness.

| # | Attempt | Hypothesis | L1 / L2 accuracy | L1 / L2 Brier | Failed rules | MRLT | Sig. of 14 | Outcome |
|---|---|---|---|---|---|---|---|---|
| — | **C-b** (sealed 67baec66) | Main model | 0.790 / 0.790 | 0.187 / 0.184 | R7 | 2 | — | **Main model** |
| 14 | S1 | Kalman latent hunger state | 0.806 / 0.806 | 0.187 / 0.181 | none | 2 | 4 | Not adopted: one changed call; vs C-b p 0.46 / 0.22 |
| 15 | S2 | Threshold analysis | descriptive | — | — | — | — | Descriptive |
| 16 | S3 | 0.5 S1 + 0.5 LOGIT | see `out/s3_results.json` | — | — | — | — | Not adopted |
| 17 | C-E | C-b + E1 (unemployment) + E2 (remittances) | 0.774 / 0.774 | 0.194 / 0.187 | R5 (L1), R7 | 2 | 6 | Not adopted |
| 18 | **C-E2** | C-E with the 8 grid settings averaged | 0.774 / 0.758 | 0.188 / 0.188 | R3, R7 | **3** | 4 | Not adopted; **local demo** |
| 19 | C-E3 | One model per lead | 0.726 / 0.645 | 0.198 / 0.209 | R2, R3, R7 (+R4, R5 L2) | 0 | 3 | Failed |
| 20 | C-E4 | C-E2 + target-quarter season | 0.758 / 0.758 | 0.192 / 0.191 | R3, R7 | 2 | 3 | Failed |
| 21a | C-E5R | Recency weighting, half-life 16 q | 0.661 / 0.645 | 0.212 / 0.215 | R2–R5, R7 | 0 | 3 | Failed |
| 21b | C-E5C | Past-only Platt recalibration (last 24) | 0.613 / 0.597 | 0.222 / 0.238 | R2–R5, R7 | 0 | 0 | Failed |
| 21c | C-E2-NONEWS | Ablation: C-E2 without news | 0.774 / 0.758 | 0.189 / 0.189 | R3, R7 | 3 | 4 | Descriptive (never adoptable) |

## Experiments considered on 2026-11-04 and NOT run (no new information)

| Proposed direction (prompt Part 7B) | Why not run |
|---|---|
| Latent-state / survey-error-aware model | Already tested as S1 (Kalman), whose R1–R7 pass rests on one forecast crossing 0.50, and as C-w (commit 3e15c3e: SWS measurement-error weights; no call changed, Brier −0.007/−0.005 n.s.) |
| Regime-aware forecasting | Tested as C-E5R; it failed. A regime detector would be selected on the same 21 middle-third quarters |
| Past-only calibration | Tested as C-E5C; it failed |
| Reversal-sensitive features | Tested as K3 (Phase C); it failed R5/R7 |
| Multisource interactions | Already allowed by depth-2 trees in the C-E2 grid; no new data |
| Alternative model families | Logistic regression is a baseline. Further families would be fitted to the same 62 labels |
| Pre-2010 evaluation window | Not a model change. The baselines LOGIT, PSA-only and LGBM-GOV start 2009-Q4, and the evaluation period may not be changed (Part 9C). See `POWER_AND_SAMPLE_SIZE_ANALYSIS.md` |

**Rule applied (Part 5):** a new fit must contain genuinely new information. Every remaining direction would re-use the
same 62 examined quarters.
