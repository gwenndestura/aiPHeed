# Adviser Decision Brief: Primary Output for aiPHeed (one page)

**Decision needed.** Should the thesis and the dashboard present the **two-layer output** as the primary result, keeping the S1 HIGH/LOW label only as a secondary legacy indicator?

## Why the question arises (E12–E13 evidence)

- **S1 = H + 2D** labels 33 of 35 province-quarters in the evaluation period HIGH, and every province HIGH from 2024-Q2.
  - Its HIGH/LOW equals the regional-hunger-only call in **94%** of those rows.
  - The threshold was set in a low-hunger period (2021–2023), and regional hunger then rose.
- **The SWS weight cannot change provincial rankings.** The ranking always equals D's ranking.
- **There is no provincial food-insecurity outcome,** so no weight, threshold or model can be validated for provincial food insecurity.

## The options

| | **A. Two-layer primary (recommended)** | B. S1 HIGH/LOW primary (current) |
|---|---|---|
| Regional | SWS Balance-Luzon hunger: level, trend, publication date. Shown **once**. | Hidden inside each province's score |
| Provincial | Food inflation F, D, and the relative-pressure rank | HIGH/LOW per province (all HIGH since 2024-Q2) |
| S1 | Secondary, labelled "legacy composite, not validated as food insecurity" | Primary |
| Needs an unvalidated weight or threshold? | No | Yes (2 and τ0) |
| Repeats one regional value as five provincial ones? | No | Yes |

**Prototype:** `TWO_LAYER_MOCK_REPORT.md`. Development only, not connected to the dashboard.

## Claims

| Allowed | Prohibited |
|---|---|
| "Regional hunger in Balance Luzon was X% in quarter T, up or down Y points from the previous measured quarter." | "Province X is food insecure" or "high-risk" |
| "Province X's food prices rose faster than the five-province average (D = +d points; rank r of 5)." | "Province X has more food insecurity than province Y" |
| "S1 is the thesis's documented composite. It is not validated as food insecurity." | "The model predicts food insecurity with N% accuracy" |
| "For relative price pressure, a shrinkage forecast was more accurate than carry-forward on 2023–2025 quarters that had already been examined (exploratory). It is pre-registered for prospective testing." | "A validated forecasting model", or any 75% claim |
| "Provincial food-insecurity accuracy cannot be established with the available data." | Presenting the 2021–2025 walk-forward results as an independent test |

## What follows from each choice

- **A:** Chapter 4 reports the two layers, with S1 as a documented secondary result. A frontend change would be a separate, approved task; **nothing is changed now.**
- **B:** The thesis must state the limits of S1 (the all-HIGH pattern, regional dominance, no validation).
- **Either way:** prospective testing follows `PROSPECTIVE_VALIDATION_PROTOCOL.md` (frozen, hash `1069bcb3…`).
  - **H1** (shrinkage of D) needs **at least 12 new quarters**, from 2026-Q3. Fewer quarters give exploratory results only.
  - **H2** (shrinkage for S1) cannot reach adequate power in any foreseeable period.

## Also needed from you

1. **Approval of a protected-data procedure** before any quarter after 2025-Q4 is scored.
2. **A view on pursuing an independent provincial outcome:** FNRI provincial microdata, CBMS, or a DA- or LGU-run FIES module.
