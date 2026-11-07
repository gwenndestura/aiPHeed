# E172 result (exploratory, 2026-11-07)

Valid run: E168 reproduced inside the same jobs (max difference 0.0); leakage control changed no output (0.0). One locked run.

## Decision (protocol section 4): **not a candidate for adoption**
The pre-declared E172 (best of 32 LightGBM variants by the training-only score) chose `GR0P | GOV_S` (E168 settings + SWS trend) for
ENNS 2018/2019 and `GR3P | GOV_S` (min child 30, L2 20) for ENNS 2021. It **fails C1 at Lead 1 (55/72) and Lead 2 (53/72)**, Lead-2
Brier +0.0077 [-0.0004, 0.0181] vs E168. Its training score beat E168's configuration at every issue: training-only selection on one
survey transition (ENNS 2018/2019) does not predict test performance.

| Lead 2 | Correct | Acc | C1 | C2 | C3 | C4 | C5 | C6 | Brier |
|---|---|---|---|---|---|---|---|---|---|
| E168 (LightGBM) | 55/72 | 0.764 | x | ok | ok | ok | ok | ok | 0.137 |
| E171 (pre-declared) | 53/72 | 0.736 | x | ok | ok | ok | ok | ok | 0.140 |
| **E172 (pre-declared, LightGBM)** | **53/72** | 0.736 | x | ok | ok | ok | ok | ok | 0.145 |
| E172 diagnostic SIMPLE (LightGBM R1-R4 only) | 59/72 | 0.819 | ok | ok | ok | ok | ok | ok | 0.144 |
| E172 diagnostic BAG (5 seeds, correctly applied) | 54/72 | 0.750 | x | ok | ok | ok | ok | ok | 0.136 |
| E166 (reference, not LightGBM) | 57/72 | 0.792 | ok | ok | ok | ok | ok | ok | 0.139 |

## The SIMPLE diagnostic: not a claim
SIMPLE (training-selected within the low-complexity variants) passes C1-C6 at Leads 1-3 (56, 59, 57 / 72). It is one of five
diagnostic subsets examined after the fact, so picking it is selection on the 72 rows. Its Lead-2 gain is six ENNS 2018 rows whose
P(HIGH) moved from 0.505-0.523 to 0.487-0.499 (five became correct, Aklan became wrong): margins of 0.001-0.013 around the line.
Brier, AUC (0.874 vs 0.887) and PR-AUC are not better than E168. A testable hypothesis for new data, not evidence.

## Seed bagging (E169 corrected)
Applied correctly here (5 fits per model): Lead 2 54/72, Brier -0.0014 [-0.0035, 0.0006] vs E168. No class improvement.

## What is needed
New survey rows (2023 NNS provincial estimates) or the 2027 outcomes, on which a pre-specified simple LightGBM (the SIMPLE rule) and
E168 can both be scored once.
