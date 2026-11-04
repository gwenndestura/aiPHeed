# Pre-registration hashes (all recomputed and verified on 2026-11-04)

**Method:** each plan's last line is the SHA-256 of every byte before that line. It is recorded before the fit and
asserted by the runner's `check()` at fit and score time. S2 names its line `ADDENDUM-SHA256`; all others use
`PLAN-SHA256`.

| Plan (OBJECTIVES_AUDIT/) | SHA-256 | Runner | Recomputed today |
|---|---|---|---|
| OBJ1_PREREGISTRATION.md | c263c36ee7e5a557268831e0605e202b41df93cc964d7eece41bfd2300acd131 | obj1_nlp.py | ✅ match |
| S1_PREREGISTRATION.md | 6a59cccb0f3423efe02d81455fd57d1098ac1fc1c097d1d3843f1257f7f94f24 | s1_kalman.py | ✅ match |
| S2_ADDENDUM.md | b18787f4a031dce3520538f719e5e44855337ef83a6fa8e70bfee3d02388f480 | s2_threshold.py | ✅ match |
| S3_PREREGISTRATION.md | 0358bac23c97ccb49a9b69be2cb8193bcaa395d67c34e242f01e5b9da9c7758d | s3_blend.py | ✅ match |
| CE_PREREGISTRATION.md | bde69c08820ece1d38ab6f6824384dbb20306117be1c733db4b4da99d6a9f10f | ce_model.py | ✅ match |
| CE2_PREREGISTRATION.md | a1b469da7f325c2e7582af57c1a5f4a1b62db308624ae1ce842049e4274bd1aa | ce2_model.py | ✅ match (and refit) |
| CE3_PREREGISTRATION.md | 34b1c1f9445234129a26b856fe7c5bb7bf625d816d7ee29680f044abcf6d0e05 | ce3_model.py | ✅ match (and refit) |
| CE4_PREREGISTRATION.md | 95a9cc6164212da10982f68bb32abd546f903491ac1e325a6c0229c5e338e917 | ce4_model.py | ✅ match (and refit) |
| CE5_PREREGISTRATION.md | 2ab41820f61daf1a2107a3a5d5805e7d6101899cf3fbbd77d6fe4ded8ce809e9 | ce5_model.py | ✅ match |
| OBJ5_ANALYSIS_PLAN.md | 851ea697401a6e6e5c85776f80c9d05d560a859a28681b562c3ed1a5440bd10f | (survey analysis; not run) | ✅ match |

**Analyses without a model fit** (read only; nothing is selected from them, so no plan is needed):
- `obj2_diagnostics.py`, `obj2_label_uncertainty.py`;
- `obj3_exposure.py`;
- `obj4_table.py`, `obj4_power.py`;
- `obj1_annotation_v2.py`, `seal_ce2_dryrun.py`.
