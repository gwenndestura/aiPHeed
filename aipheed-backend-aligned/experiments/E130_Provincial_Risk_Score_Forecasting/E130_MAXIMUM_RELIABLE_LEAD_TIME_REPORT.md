# E130 maximum reliable lead time

## Result

| Model | Maximum reliable lead | Leads 1–4 |
|---|---|---|
| M1 LightGBM regression (proposed) | **None established** | Not evaluable |
| M2 Persistence | **None established** | Not evaluable |
| M3 PSA-only | **None established** | Not evaluable |
| M4 NLP-only | **None established** | Not evaluable |
| M5 Linear (continuous counterpart of logistic regression) | **None established** | Not evaluable |

- **Does LightGBM exceed every baseline?** Not established.
- **Lead 2 status: failed** (not evaluable). The minimum operational objective is **not** achieved.

The reason is the same for every model and lead. There is **no quarterly provincial food-insecurity reference** to score against, so every lead fails N1 (≥ 10 target quarters and 40 rows), and N2–N7 cannot be computed. This is a data limit at the target, not a modelling result: no model was allowed to train on a target that does not exist (gate, protocol §1).

## What "Lead 2" means on the dashboard

The served clock (`backend/app/quarterly/target.py`) defines it:

| Operational lead | Target quarter | Meaning |
|---|---|---|
| Lead 1 | The dashboard quarter (calendar quarter of the view date) | Under way; its data are incomplete |
| **Lead 2** | The next quarter, which is the dashboard's forecast target | **Minimum operational horizon:** one completed quarter beyond the dashboard quarter |
| Lead 3–4 | Two and three quarters after the dashboard quarter | — |

**The E128/E79 mismatch, resolved.** E128 and the dashboard use the same origin (the quarter-start issue date) and the same lead count, so E128's Lead k is the dashboard's Lead k on all 92 E128 rows. The mismatch was only in the **information horizon**, which is how far the target lies past the newest published reading:

| Issue rule | SWS information horizon at Lead 1 | At Lead 2 |
|---|---|---|
| Quarter start (served; E128) | 2 quarters in 19 of 21 rows | 3 quarters in 19 of 21 rows |
| After the SWS release of the latest complete quarter (E80; median 31.5 days into the quarter; possible in 20 of 23 dashboard quarters) | 1 | 2 |

The provincial reference (PFDR) is older still. At Lead 2 it is 5–13 quarters old (median 9), and it exists at all for only 9 of the 23 dashboard quarters (from August 2024).

## What it would take

From the planning simulation (`E130_SCORE_AGREEMENT_ANALYSIS.md` §3). Establishing Lead 2 with ≥ 80 % probability needs all of:
- a **quarterly** provincial food-insecurity measure;
- **20–40 quarters** of it;
- sampling error about equal to the true variation;
- predictors explaining **≥ 50 %** of the true two-quarter change.

The project has none of these. The nearest data are:
- regional SWS, 20 quarters, where E128 found no model reliable at any lead;
- a biennial provincial subsistence series, 2 rounds held.
