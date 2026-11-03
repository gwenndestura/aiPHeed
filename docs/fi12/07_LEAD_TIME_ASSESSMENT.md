# Deliverable 7. Lead-time assessment

**FI12** · protocol `2949208888f5` locked 2026-11-03T02:31:10+00:00 · Evidence tags: [V] verified against a primary source in this repository; [S] secondary source, not verified; [R] computed by FI12 under the locked protocol; [F] read from an earlier study's result file.

| Outcome | Maximum reliable lead | Basis |
|---|---|---|
| **A. Direct provincial food insecurity** | **Not verifiable** | One verified wave (2015) in which provinces are not distinguishable; ENNS one year per province, secondary, no SEs. No model has rank skill at any lead (Deliverable 4). Validation needs at least two comparable waves with forecasts issued before them |
| **B. Provincial food poverty** | **None** | Three waves; no model or baseline ranks provinces consistently; FI10 Leads 1–4 pooled ρ ≤ 0.25, never significant; P0H4 2023 only |
| **C. Regional SWS hunger** | **Lead 1, persistence only** (FI7 rules); none under the FI9-Z HIGH-recall ≥ 0.60 requirement | FI7/FI9/FI9-Z/FI11 [F]: naive persistence accuracy 0.871, balanced accuracy 0.743; nothing learned beats it |
| **D. Food-price pressure** | **None adopted; Lead 2 provisional** | FI10 [F]: no lead passed every locked requirement (Lead 1 failed: high_precision_ok, low_recall_ok, low_precision_ok, macro_f1_ok, accuracy_ok, skill_vs_naive, every_province_ba_ge_065); tuned LightGBM beats both persistence rules on Lead-2 Brier in the forensic audit recomputation, but was not the locked selection |

A future map quarter is not evidence of a forecast lead. The dashboard can draw any quarter; a lead is reliable only
where forecasts issued that far ahead have been scored against observations.
