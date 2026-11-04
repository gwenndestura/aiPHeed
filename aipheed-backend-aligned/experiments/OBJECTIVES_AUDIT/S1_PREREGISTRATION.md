# S1 pre-registration: C-b + a measurement-error (Kalman) estimate of true hunger

**Fixed before any S1 fit:** written and hashed on 2026-11-03. Development evidence only (62 previously examined
quarters). This is the 14th historical attempt; Phase A–C, NOISE_W and earlier attempts are recorded in
`NEW_MODEL/ALLBASE/PHASE_A_AUDIT.md` §4.

## 1. Hypothesis

C-b errs mainly by following one noisy SWS reading through reversals (10 of 13 Lead-1 errors are persistence's call).
A local-level state-space model that knows SWS's sampling variance per quarter estimates **true** hunger better than
the raw last reading. Giving that estimate to C-b improves Brier at Leads 1 and 2.

## 2. Features (per origin t, from BL readings published before O(t) only)

- **Model:**
  - x_q = x_{q−1} + w_q, with w ~ N(0, σ_w²);
  - y_q = x_q + e_q, with e ~ N(0, 2.908² / rounds_q).
  - Quarters without a reading are prediction steps only.
  - Initial state: the first reading, with variance 100.
- **σ_w²:** estimated at each origin by maximum likelihood (prediction-error decomposition) over a fixed grid of 40
  log-spaced values from 0.1 to 50, using only the readings known at O(t).
- **`kf_level`:** the filtered mean at the last known quarter.
- **`kf_pi`** (per lead k): Φ((m − 11.3) / √(P + h·σ_w²)), with h = (t + k) − q_last.
- **Inputs:** S1 = C-b's 21 inputs + `kf_level` + `kf_pi` (23), fitted exactly as C-b (same grid, inner selection,
  seed, walk-forward from 1998-Q3).

**Pre-checks (S1 is not scored if one fails):**
- C-b refit reproduces stored C-b (≤ 1e-12);
- the features are unchanged when every SWS round published on or after O(t) is randomized (5 reps);
- a second implementation of the filter agrees (≤ 1e-9).

## 3. Evaluation and gates (unchanged from `ALLBASE/PHASE_B_PREREGISTRATION.md`)

**Window:** the 62 quarters, Leads 1 and 2.

**Reported:** all metrics, R1–R7, Algorithm 3, the reversal analysis, folds S/E, and a **14-test Holm family** (S1 ×
7 baselines × 2 leads, paired Brier, cluster bootstrap seed 2036, B 5000). The family is separate from the Phase C
42-test family and is reported beside it.

**Gates:**

| Gate | Condition |
|---|---|
| G1 | All 14 comparisons significant (Holm) |
| G2 | Brier < C-b at both leads, one-sided p < 0.10, and accuracy not lower |
| G3 | R1–R7 pass at both leads |
| G4 | MRLT ≥ 2 |
| G5 | R7 fixed without displacement |

**Adoption:** G2 and G4, plus team and adviser approval. Otherwise **C-b stays**.

## 4. Dropped before running: S2 (K1 with a walk-forward threshold)

A threshold changes classes, not probabilities, so S2's Brier equals K1's (+0.001 vs C-b at Lead 2). **S2 cannot
pass G2 by construction**, so it is not run.
PLAN-SHA256: 6a59cccb0f3423efe02d81455fd57d1098ac1fc1c097d1d3843f1257f7f94f24
