# E171 result (exploratory, 2026-11-07)

Valid run: E168 reproduced exactly inside the same jobs (max difference 0.0); leakage control changed no output (0.0).

## Decision (protocol section 5)
**Lead 2 did not genuinely improve.** The pre-declared E171 (best of 32 configurations by the time-aware training score) passes C1-C6 at
Lead 1 (57/72) but **fails C1 at Lead 2 (53/72, worse than E168's 55/72)**; Lead-2 Brier +0.0022 [-0.005, 0.011] vs E168.
E168 remains the thesis model. Nothing is served from E171.

| Lead | E168 | E171 | A (LightGBM + SWS trend) | B (lead-band) | C (ElasticNet + SWS) | D (hybrid trend) |
|---|---|---|---|---|---|---|
| 1 | 56/72, C1-C6 pass | 57/72, pass | 53/72, C1 | 53/72, C1 | 57/72, pass | 47/72, C1 C3 C5 |
| 2 | 55/72, C1 | 53/72, C1 | 50/72, C1 | 50/72, C1 | 57/72, pass | 48/72, C1 |
| 3 | 54/72, C1 | 52/72, C1 | 52/72, C1 | 55/72, C1 C4 | 55/72, C1 | 50/72, C1 |

Family C passing at Lead 2 is a diagnostic chosen after seeing results (protocol: not a claim). It is not LightGBM, and it matches
E166 (also not LightGBM), which passed C1-C6 at Leads 1-2 before.

## Root cause
1. ENNS 2018 and 2019 forecasts have one training transition (NNS 2013 -> FNRI 2015): a national-trend effect cannot be learned from a
   single national change. The SWS trend inputs did not change ENNS 2018 (14, 13, 12 correct at Leads 1-3, as E168) and made LightGBM
   worse elsewhere (A: Lead-2 Brier +0.0069 [0.0001, 0.0166]).
2. 72 rows (45.5 effective): C1 needs 56/72; differences of 1-3 rows are within noise (no Brier difference is significant except A, D worse).
3. Learner: linear residual models (ElasticNet, E166) reach 57/72 at Lead 2; LightGBM residual models reach 50-55/72 here.

## Correction
E169's seed bagging was never applied in its worker processes (they used Res2); E169 did not test seed bagging.
