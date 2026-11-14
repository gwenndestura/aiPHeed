# E185: E184 tuned with a Gaussian-copula synthetic generator. Report

## Decision: **the new synthetic generator did not improve E184.** E184 stays the synthetic-data candidate; E168 stays in production. Nothing was staged or deployed.

E185 tried E184's setting against 17 alternatives (12 Gaussian-copula, 4 jitter, none) on inner region folds only,
with a one-standard-error rule against E184's setting, and averaged the choice over seeds 17901–17905
(`docs/e185/PROTOCOL.md`, committed `268b9e9` before any output).

## Results on the 72 real rows per lead

| Lead | E168 | E184 | **E185** | E185 − E184 Brier [95 % CI] | McNemar vs E184 |
|---|---|---|---|---|---|
| 1 | 75.0 % (Brier 0.1230) | 76.4 % (0.1211) | **77.8 %** (0.1214) | +0.0003 [−0.0024, +0.0034] | 1 vs 0, p = 1.0 |
| 2 | 77.8 % (0.1221) | 79.2 % (0.1185) | **77.8 %** (0.1180) | −0.0006 [−0.0033, +0.0019] | 0 vs 1, p = 1.0 |
| 3 | 75.0 % (0.1352) | 77.8 % (0.1258) | **75.0 %** (0.1267) | +0.0009 [−0.0024, +0.0043] | 0 vs 2, p = 0.5 |

**Other measures.**

| Lead | HIGH recall (E184 → E185) |
|---|---|
| 1 | 0.84 → 0.84 |
| 2 | 0.84 → 0.80 |
| 3 | 0.84 → 0.84 |

- Leakage 0.0.
- Shuffled-trigger control: E185 − shuffled +0.0021 [−0.0114, +0.0191], so it does not beat its scrambled-input version
  (as E168, E182 and E184).

## What the tuning chose (main jobs, 45 job × seed choices)
| Choice | Share |
|---|---|
| Kept E184's setting | 40 % |
| A copula setting | 27 % |
| Other jitter settings | 33 % |

The inner-fold gains of these switches did not carry over to the real test rows.

## Rule
| Condition | Result |
|---|---|
| Brier CI vs E184 below 0 at Leads 1, 2 and 3 | ❌ (all CIs include 0) |
| Accuracy ≥ E184 at each lead | ❌ (Lead 1 higher; Leads 2 and 3 lower) |
| Owner rule (≥ 75 % and beats persistence) | ✅ |
| Leakage below 1e-9 | ✅ |

## ENNS 2022 seal
- **File:** `backend/data/e185/out/sealed_enns2022.json`.
- **SHA-256:** `6eac33dfff18c9a5e17b6da38b8ffc105434b81bf3440543630d87dbb6516165`.
- **Contents:** 156 forecasts. The E168 part matches E168's seal.

## Reading
- **What changed.** A genuinely different synthetic generator (a Gaussian copula, which creates new combinations rather
  than near-copies) moved accuracy by one or two provinces per lead, in both directions. The Brier score did not change.
- **Conclusion.** This is consistent with E178–E184: synthetic rows built from the same real rows cannot add the
  information the model lacks.
