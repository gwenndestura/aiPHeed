# E134 · Resolving the predictive information bottleneck

**Decision: B, a viable path is not yet demonstrated.**
- **New data** (2021+ only): area-level climate from NASA POWER at 18 regional centres, regional quarterly palay production, and FIES 2023 provincial household stress.
- **Effect:** adding the area drivers to HFM-X worsens Lead-2 MAE (4.87 → 5.39).
- **Candidate:** HFM-X, unchanged, at Lead-2 0.50 within tolerance (20 of 40 rows; 75 % needs 30).
- **Reliability:** no lead is reliable.
- **Provincial:** the ordering is measure-dependent (FIES household stress against PFDR: Spearman ≈ 0).
- Main document: `E134_FINAL_RESEARCH_PACKAGE.md`. The other 14 deliverables are in this folder.

**Context.**
- Protocol `139ca7f` (sha256 in `runner/PROTOCOL_SHA256.txt`).
- Branch `aiPHeed/corrected-data-pipeline`; offline only. Nothing pushed, and production and the E131–E133 seals are unchanged.

## Reproduce

See `E134_REPRODUCIBILITY_MANIFEST.md`:
- `e134_baseline.py`
- `e134_acquire.py`
- `e134_run.py`
- `e134_diagnostics.py`
- `e134_summary.py`
- `e134_seal.py`

**Scoring and re-issue:**
- `runner/score_e134.py` (primary only);
- `runner/e134_reissue.py <YYYY-MM-01>` (write-once).

Tests: `backend/tests/unit/test_e134_information.py`.
