# E197: E196 with an F1-maximising HIGH cut-off chosen on training rows only. Fixed before results. Local only.

Written 2026-11-11 at the owner's request ("fix the F1"). E196's F1 is 0.772 / 0.759 / 0.746 at Leads 1–3; Chapter IV's
target is ≥ 0.75. **Chapter IV chooses its decision threshold from tuning (training-side) predictions only**, so this
follows the paper's own method.

## Method
- **Training-side probabilities.**
  - For each distinct outer training set (ENNS2018; ENNS2019; ENNS2021 Leads 1–2; ENNS2021 Leads 3–6), re-fit E196's
    E194 component unchanged: top-5 Stage-A configurations × 20 draws.
  - Average the **real training rows' inner out-of-fold forecasts** (mu) over the 100 fits.
  - Convert them to P(HIGH) = Φ(mu / sd), with sd from `A4.scale` on the OOF errors (E187's raw-layer convention).
- **Cut-off rule.**
  - Choose t ∈ {0.30, 0.35, …, 0.70} that **maximises F1 (HIGH = y ≥ 0) on all real training rows**.
  - Ties go to the cut-off closest to 0.50.
- **E197.**
  - E196's probabilities, unchanged.
  - HIGH if p ≥ t, using the t of the job's training set.
  - Brier and AUC are therefore identical to E196's. Only the classifications change.

## Decision (fixed now)
- **E197 replaces E196's 0.50 cut-off only if all three hold:**
  - F1 ≥ 0.75 at all of Leads 1–3;
  - F1 ≥ E196's F1 at every lead 1–3;
  - accuracy ≥ E196's at every lead 1–3.
- **Otherwise** E196 keeps 0.50 and its F1 is reported as 0.772 / 0.759 / 0.746.
- **Disclosure.** This is the 21st comparison on the same 72 rows. If adopted, it is reported as post-hoc and subject to
  the sealed 2022 confirmation.
- **Scope.** Nothing is staged, committed or pushed by this experiment.
