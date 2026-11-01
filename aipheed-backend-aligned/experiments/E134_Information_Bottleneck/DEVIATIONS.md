# E134 deviations and implementation notes

**No deviation changes the target, the tolerance, the 75 % requirement, the leads, N1–N7, P-DASH, the evaluation sets or the selection rule.**

## V1 · Settings not stated in the protocol (fixed before the first E134 run)

**Metro Manila palay.** NCR grows no palay, so Metro Manila's palay driver is 0 (neutral).

**Rainfall points:**
- Daily values below 0 (NASA fill) are dropped.
- A quarter counts only with at least 88 daily values.

**Driver minimum.** An area driver needs at least 8 available area-quarters before it becomes active at an issue.

**Ablation.** "AREA-T-delayed" moves every area-driver availability date back by 92 days per quarter of delay.

**E134-ENS:**
- Its development rows use the reproduced E133 HFM-X and E132 SEAS-LLM forecasts.
- In the seal, its interval half-width is z80 × the mean of the two members' SDs (taken from their sealed 80 % intervals).

## V2 · Coding fixes before results were used

- The palay crosswalk raised an error for NCR (no palay). It was fixed before the first complete run.
- Two diagnostics-only fixes:
  - FIES T8 column indices;
  - Quezon's FIES name ("QUEZON (Excluding City of Lucena)").

  Neither affects any candidate.
- The rank direction in the provincial household-stress table was corrected so that rank 1 = most stressed. This is diagnostic only.

## V3 · Data-prompted elements (disclosed in the protocol)

E134-AREA-O and E134-ONI use ONI, which E133's D2 screen found using outcomes. E134-ENS was prompted by E133's set disagreement. None of the three is confirmatory.

## V4 · Idempotent driver patch (found by the unit test after the results)

**Defect.** `e134_run.py` replaces E133's driver function (`e133_models._exog`) with one that also applies the area drivers. Importing the module a second time in the same process wrapped the function again, applying the area effect twice. This affected only multi-import contexts such as the test suite.

**Why no result was affected.** Every runner (run, diagnostics, summary, seal) imports the module once.

**Fix and check.** The patch is now idempotent (`M._exog_e133` holds the original). After the fix the complete walk-forward was re-run: every forecast is identical to before (maximum difference 0.0).
