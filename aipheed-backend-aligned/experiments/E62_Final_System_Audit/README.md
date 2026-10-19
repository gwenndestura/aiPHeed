# E62: final system audit (2026-10-19)

**Read first:**
1. `FINAL_AUDIT_REPORT.md`: answers to the ten questions; backend stage audit; chronology; continuity; joint probability and target; drift, rice and features; news; tests; limitations; recommendation; how to reproduce.
2. `OBJECTIVE_COMPLIANCE_MATRIX.md`: Chapter I objectives, scope items and hypotheses, each with its evidence and status.
3. `DEFECTS_AND_CHANGES.md`: three defects fixed (D-E62-1..3), ten weaknesses confirmed but not fixed (W1–W10), and every changed file.

**Tables:**
- `r3_chronology_compact.md` (readable) and `r3_chronology_by_province.csv` (full): forecasts against observations.
- `r2_*`: independent re-scoring.
- `r1_labels_independent.csv`: labels recomputed from the raw files.
- `r4_rice_vs_food_by_quarter.csv`.

**State:**
- Branch `e62-final-audit`, local. Committed locally at the user's request (2026-10-19) as separate E59, E60, E61 and E62 commits. **Not pushed, deployed or switched.** The E46 D-1 hunks of another session stay uncommitted.
- E38 is still the production default.
- E56–E61 frozen files are verified unchanged.
