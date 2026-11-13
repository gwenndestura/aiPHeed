# PROTOCOL_SA Part B: the pre-registered improvement candidate (locked before any candidate is scored)

Builds on PROTOCOL_SA (sha 15202d27). Written 2026-11-13.

## Basis

The basis is training-only or outcome-free evidence (`evidence/D1_*`, `D2_*`, `D3_*`, `R1_R2_integrity.json`). No outcome of a 2018, 2019 or 2021 test row was read to define it.

1. **Every fold extrapolates the interval length.** Test gaps are 12, 16 and 24 quarters; the longest training gaps are 8, 8 and 20. Live CALABARZON gaps would be 22–34 against 24.
2. **Training rows show change is not proportional to the gap.** Per-quarter logit change was −0.011 (8 quarters), −0.035 (12), −0.016 (16) and −0.019 (20). A 16-quarter transition fell less than a 12-quarter one.
3. **FINAL's own 2021 forecasts (no outcomes) project too large a fall.** For anchors at 60 % or more they project −23.6 points: about −12 from the anchor's built-in shift plus about −12 from RATE × (24 / mean training gap). Training provinces with such anchors fell −9.4 points on average, and 77 % stayed HIGH.
4. **The cut-off of 0.50 is inherited.** The engine already computes a balanced-accuracy threshold on its inner out-of-fold training probabilities, but it is unused.

## Candidate FINAL-SA (the only eligible candidate)

FINAL unchanged (LightGBM; rate = 'lin'; MIND; balanced class weights; same anchors, feature sets, grid, seeds and calibration choice), with two pre-specified changes:

- **(i) No time extrapolation beyond training support.**
  - The RATE multiplier of a test row is min(gap, G_max) / g₀, where G_max is the longest gap among that fit's training rows and g₀ is the mean training gap, as before.
  - The predictive spread keeps the uncapped gap: uncertainty still grows with time, but the mean change is not projected past what training covered.
- **(ii) Decision threshold chosen on training rows only.**
  - Each fit's threshold maximises inner out-of-fold balanced accuracy over 0.30–0.70; ties go to the value nearest 0.50 (`engine_opt._thr`, unchanged).
  - A province is HIGH when the five-seed mean probability is at least the five-seed mean threshold.
  - Probabilities are not altered.

## Scoring

- Scored once on the 72 reused rows with `evaluate.py`, under PROTOCOL_SA unchanged, labelled **retrospective, reused rows**.
- Rule 7a for FINAL-SA: its fits are deterministic given the seed (verified by re-running one fit).

**Diagnostics, ineligible and never selected.** These isolate the effect of each change:
- FINAL with the training threshold only;
- FINAL with the cap only.

**What is not done.**
- No variant is chosen after scoring.
- FINAL-SA is accepted or rejected on its own seven-rule result.
- If it fails, nothing further is tuned on these rows.
- The displacement input is **not** added: it was identified from test provinces, and its history is not compiled. It is reserved for prospective sealing.
