# E57: final label/model experiment (lead 1)

## Pre-registration (written 2026-10-17T01:17Z, before any E57 result was computed)

Base: the E56 harness unchanged (E53-A1 inputs, pool COMPACT_T5_C / COMB_T5_C x G1/G4/G3/G2, E36 nested walk-forward,
lead 1, seed 36, threshold 0.5, E49-C2 shrinkage fitted on earlier dates), evaluated on the 65 E53 development rows
(13 quarters x 5 provinces). No tuning.

Variants:
- **V0**: E53-A1 with the L0 label, as a sanity check. It must give accuracy 0.785, balanced accuracy 0.836 and
  AUC 0.880; otherwise the run stops.
- **V1**: L0 label, plus the input y_last (the last L0 label known at the origin: the latest quarter <= F-2 whose SWS
  rounds were all posted before the origin, labelled with tau(t), which itself uses only quarters posted before the
  origin). Note found before running: COMB_T5_C already contains y_last, so V1 adds it to COMPACT_T5_C only
  (pool COMPACT_T5_C + y_last, COMB_T5_C). No other change.
- **V2**: "worsening" label, HIGH if S1(p, q) > S1(p, q-4). The comparison quarter q-4 must be posted before the
  origin; otherwise the label is undefined. Inputs = E53-A1 inputs, with y_last = the V2 label of the latest
  quarter <= F-2 that is posted before the origin and has a defined V2 label. S1 is missing for 2022-Q1, 2025-Q2 and
  2025-Q3, so V2 is undefined for 2023-Q1, 2026-Q2 and 2026-Q3. V2 is therefore scored on the remaining 50 of the
  65 rows, and persistence on the same 50 rows. H_margin keeps the L0 tau (V2 has no H threshold).

Reported per variant: accuracy, balanced accuracy, AUC, Brier, LOW caught, HIGH share 2024-2026, persistence accuracy
and balanced accuracy on the same rows, label flips (rows whose label differs from y_last) and the flips the model
called correctly, and Q4 2026 probabilities (CALABARZON + 5 provinces).

**Adoption rule (pre-registered).** V1 and V2 are each eligible only if all of these hold:
- (a) balanced accuracy >= 0.75 AND strictly greater than persistence balanced accuracy on the same rows;
- (b) AUC >= 0.75;
- (c) H stays in the target (S1 = H + 2D; true for V1 and V2);
- (d) V2 only: HIGH share 2024-2026 between 30% and 70%.

If V1 passes, prefer V1 (same label as the paper). If nothing passes: "Keep L0 / E53-A1; label experiments closed."

Leakage check: for every origin, assert that the y_last quarter and the V2 comparison quarter were fully posted
before the origin.

## Results

Run `20261017T012023Z`. V0 reproduces E53-A1: **True**. Protected md5s identical at start and end: **True**.

| Variant | Rows | Accuracy | Balanced | AUC | Brier | LOW caught | HIGH share 2024–26 | Persistence acc / bal | Flips | Flips caught |
|---|---|---|---|---|---|---|---|---|---|---|
| V0 | 65 | 0.785 | 0.836 | 0.880 | 0.150 | 11/12 | 93% | 0.877 / 0.860 | 8 | 4 |
| V1 | 65 | 0.785 | 0.836 | 0.880 | 0.149 | 11/12 | 93% | 0.877 / 0.860 | 8 | 4 |
| V2 | 40 | 0.650 | 0.406 | 0.240 | 0.240 | 0/8 | 83% | 0.675 / 0.469 | 13 | 3 |

Flips = rows whose label differs from y_last; flips caught = those the model called correctly.

V2 not scored on 2023-Q1, 2023-Q2, 2023-Q3, 2026-Q2, 2026-Q3.

V2 deviation from the pre-registered 50 rows: 2023-Q1, 2026-Q2 and 2026-Q3 have no V2 label (S1 missing for 2022-Q1, 2025-Q2, 2025-Q3), as pre-registered. In addition, 2023-Q2 and 2023-Q3 were skipped by the unchanged E36 walk-forward rule (needs >= 10 training rows; V2 has only 5 there, because the first comparable quarters are 2022-Q2..Q4). So V2 is scored on 40 rows, and persistence on the same 40.

### Q4 2026 probabilities (origin 2026-10-01)

| Variant | CALABARZON | Cavite | Laguna | Batangas | Rizal | Quezon |
|---|---|---|---|---|---|---|
| V0 | 0.789 | 0.916 | 0.912 | 0.284 | 0.917 | 0.917 |
| V1 | 0.789 | 0.916 | 0.912 | 0.284 | 0.917 | 0.917 |
| V2 | 0.719 | 0.719 | 0.719 | 0.719 | 0.719 | 0.719 |

### Adoption

| Variant | (a) bal ≥ 0.75 and > persistence | (b) AUC ≥ 0.75 | (c) keeps H | (d) V2 HIGH share 30–70% | Eligible |
|---|---|---|---|---|---|
| V1 | **no** | yes | yes | n/a | **no** |
| V2 | **no** | **no** | yes | **no** | **no** |

**Verdict: Keep L0 / E53-A1; label experiments closed.**

### Leakage check

- V0: 18 (origin, quarter) checks for y_last and the V2 comparison; 0 used a quarter not fully posted before its origin.
- V1: 18 (origin, quarter) checks for y_last and the V2 comparison; 0 used a quarter not fully posted before its origin.
- V2: 122 (origin, quarter) checks for y_last and the V2 comparison; 0 used a quarter not fully posted before its origin.
