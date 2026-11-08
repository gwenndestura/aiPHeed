# FINAL_ARCHITECTURE protocol (frozen before any new feature or candidate is scored)

**Date:** 2026-10-27.

**Branch:** `aiPHeed/final-architecture` (local only), from `aiPHeed/bias-audit` `309d610`.

**Baselines recorded:**

| Branch | Commit |
|---|---|
| main | `0239273` |
| aiPHeed/lead2-optimization (served P0H4 export) | `a1ce8ce` |
| aiPHeed/lead2-one-model (S3) | `40ea4d9` |
| aiPHeed/bias-audit | `309d610` |

**P0H4 stays served.** Nothing is pushed, merged or deployed without your approval.

**Evidence status.** Every 2021–2026-Q3 quarter has influenced earlier designs. All results are development evidence. Untouched outcomes start with SWS 2026-Q4.

## 1. Fixed elements

| Element | Value |
|---|---|
| Target | T43c (Chapter I), unchanged |
| Rows | The UNI-FINAL evaluation rows (leads 1–15; Lead 1: 70 rows, 14 quarters; Lead 2: 65 rows, 13 quarters) |
| Issue-date rules | Unchanged |
| Reliability | R1–R7 + the later-block check (LEAD2_OPTIMIZATION Addendum 2). Maximum reliable lead = consecutive passes from Lead 1. |
| Decision rule | HIGH at 0.50 |

**Architecture of every candidate.** ONE LightGBM trained on T43c across all leads: the S3 design of LEAD2_ONE_MODEL, with the structural price offset and balanced class weights. No second model, no multiplication.

## 2. Experiment matrix (each change tested on its own against C)

| Id | Change | Question |
|---|---|---|
| A | P0H4 (served hybrid), existing predictions | baseline |
| B / **C** | S3 = all 12 families + lead + world prices + hunger inputs and dynamics + structural offset + balanced weights (existing predictions, reproduced) | single-model baseline |
| **D** | C + **climate representation**: ONI at m0 (NOAA CPC, season ending ≤ m0); max ONI and number of months with ONI ≥ 0.5 over the 12 months to m0 (severity, accumulated exposure); PAGASA El Niño level at O(t) (0 none or Final Advisory, 1 Watch, 2 Alert, 3 Advisory or Climate Advisory; items dated before O(t)); quarters in a row with an El Niño Alert or Advisory in force; typhoons in t−1 and over t and t−1 (C2 lag and accumulation); production drop at t−1 (C3 lag, from the previous origin's row) | Was climate under-represented? |
| **E** | C + **lags and changes**: A2, A3 and E1 change since the previous origin; C4 and E2 at the previous origin | Do changes or lags add information? |
| **F** | C + **interactions**: max(ONI, 0) × A3; max(ONI, 0) × C3; typhoons over t and t−1 × C3 | Does climate act through rice or production? |
| **G** | C + D + E + F | Combined |

**Placebos (for any of D/F that is selected or that improves on C):**
- climate columns shuffled across issue dates within province (20 shuffles);
- climate columns time-displaced: values from 4 quarters earlier.

**Ablations on the selected candidate (refit at every origin):**
- groups: Market; Climate (all climate columns incl. D's); Employment + remittances; News; Poverty; Hunger inputs (H1 + SWS dynamics);
- each of the 12 families on its own.

**Leakage.** 6-origin future-perturbation audit (SWS, CPI, regional CPI, Pink Sheet, news, ONI) for C–G before scoring. Historical replay of the selected candidate.

## 3. Selection (decided now)

**Eligible.** A single-model candidate (C–G) is eligible if both hold:
- Lead 1 passes R1–R7 and the later-block check;
- its Lead-1 Brier is not worse than P0H4 at one-sided p < .10 (cluster bootstrap by quarter).

**Selected.** The eligible candidate with the **lowest mean development Brier over Leads 1–3** (targets ≤ 2024-Q4; longer leads included because S3 degraded at Lead 3). Ties within 0.002 go to fewer columns: C, then D/E/F, then G.

**When a feature block counts as useful.** D, E or F "adds predictive value" only if it lowers the development Brier (mean over Leads 1–3) compared with C **and** its full-period Brier difference vs C excludes 0 (90% CI) at Lead 1 or Lead 2. Otherwise it is reported as no demonstrated gain, and kept only if selected by the rule above.

**Recommendation rule (single model vs hybrid).** The selected single model is recommended as the thesis architecture if:
- it is eligible;
- it is not worse than P0H4 at Lead 1 or Lead 2 at two-sided p < .10.

Any significant longer-lead loss is disclosed. Otherwise P0H4 (a declared hybrid) is recommended.

**Serving.** Nothing replaces P0H4 without your approval. An approved model gets a new seal before its first unseen outcome.

## 4. Explanations (separate commit; no model change)

| Change | Detail |
|---|---|
| "Fish Kill" label | renamed to "Fisheries production" (C4 is a production drop) |
| Families shown | the served explanation adds the omitted families as their own rows (Poverty and vulnerability, News, Regional hunger indicator) from the same SHAP measure |
| Hunger multiplier (P0H4) | stays in the note, because it is not a SHAP quantity |
| `lead` | disclosed as excluded |

**For a single-model candidate,** SHAP explains the full risk probability. The hunger inputs then appear as their own group.
