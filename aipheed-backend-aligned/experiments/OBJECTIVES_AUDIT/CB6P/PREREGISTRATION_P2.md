# C-B6P2 pre-registration: C-B6P + the province's last known Eq. 3 score (fixed 2026-11-04, before any fit)

**Development evidence; one variant only.** Same 100 province-quarters as C-B6P (`PREREGISTRATION.md`, e6405536…),
which were already examined.

## Why

- PERSIST (the province's last known label) beats C-B6P on accuracy: 0.830 vs 0.780 at Lead 1, 0.780 vs 0.720 at
  Lead 2.
- C-B6P sees regional hunger (`h_last`) and the current price deviation (D1), but not the province's own last stress
  level.

## Definition

- **Exactly C-B6P** (label, THR 11.0, rows, procedure, grid, seed, origins, leads), keeping E1 and E2, plus two inputs
  (28 in all):
  - **S_last:** the last Eq. 3 score of that province known at the row's own origin O(t'), under C-B6P's availability
    rule (BL label known and the three CPI months <= m_avail). If none is known, the last known BL hunger (S = H
    when D = 0). BL history rows use the last known BL hunger.
  - **y_last:** S_last > THR.

## Acceptance (all required)

1. Brier < C-B6P at Leads 1 and 2, one-sided cluster-bootstrap p < 0.10 (B 5000, seed 2036).
2. Accuracy >= C-B6P at Leads 1 and 2.
3. Leakage: S_last at origin t uses only labels known at O(t) (checked by recomputation with later labels removed).

Also reported: all metrics, Algorithm 3, and the Brier comparison vs PERSIST, LOGIT and C-B6-R (Holm over 6).
If accepted, C-B6P2 replaces C-B6P as the province-quarter candidate; C-B6 remains the served main model.
**Reported whatever the result; no further variant.**
PLAN-SHA256: 93ec374b9b5a38e17bea016eb8a3a20e9dcc3a900e342dfc2d610fcd65f35959
