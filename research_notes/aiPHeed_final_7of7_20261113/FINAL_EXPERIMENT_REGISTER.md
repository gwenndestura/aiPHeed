# FINAL lineage: experiment register

**What "reused rows" means.** "Rows" means the 72 forward province-rounds (ENNS 2018, 2019, 2021) unless stated. Every row-level result after FINAL's first forward scoring (2026-11-12) is **retrospective on reused rows**. "Development" means training rows or the held-out FNRI 2015 round.

**What stays untouched.** All experiments preserve FINAL, H_cw, E196 and the seals.

| # | Date | Question / hypothesis | Data | Configuration (exact) | Key result | Decision |
|---|---|---|---|---|---|---|
| E1 | 11-12 | Does learning change per quarter (RATE) plus missing indicators (MIND) beat H_cw on a held-out round? | Development: FNRI 2015 held out | `engine_final` rate='lin', miss='mind'; PROTOCOL_FINAL sha `263a9dd7` | Held-out Brier −0.042 vs H_cw; forward L1 86.1 % | FINAL defined |
| E2 | 11-12 | Synthetic rows fix Rules 3–4? | Rows | PROTOCOL_SYN `2aa9cff0` | Worse | Rejected; synthetic data now prohibited |
| E3 | 11-12 | Anchor averaging ("FINAL-MIX", anchors) | Rows | PROTOCOL_MIX `3b6a86c2` | Fails 6 of 7 original rules | Rejected |
| E4 | 11-12 | Class weights chosen on training (FINAL-CW) | Rows | PROTOCOL_CW `69688113` | 4 of 7 | Rejected |
| E5 | 11-13 | Standalone rules: does FINAL meet them on its own? | Rows | PROTOCOL_SA `15202d27` | 6 of 7 (fails 7c) | Baseline status |
| E6 | 11-13 | Cap the RATE multiplier at the training gap + training threshold (FINAL-SA) | Rows | Part B `112ca651` | 6 of 7 (fails Rule 6) | Rejected |
| E7 | 11-13 | Elapsed time = time since the latest released round (FINAL-ET) | Rows | `c5e76bd5` | 6 of 7 (fails Rule 6) | Rejected |
| E8 | 11-13 | Walk-forward leads 1–8 for FINAL and FINAL-ET | Rows, Leads 1–8 (110 fits) | `c5e76bd5` section 3 | No reliable lead | Reported |
| E9 | 11-13 | **Equal mixture of g and s (FINAL-ETMIX; named "FINAL-MIX" in its locked protocol)** | Rows (inadmissible); sealed ENNS 2022 | `a365da1f`; no fit (combination of E7 fits). Seal sha `71ebe142` | Retrospective L1: balanced accuracy 0.856, recall 0.84, precision 0.78, mean p − rate +0.074, Cox p 0.10, 2021 recall 2/4: **7/7 retrospective, inadmissible** (predicted in the protocol before computing). Retrospective maximum lead 1 (Lead 2 fails 7c) | **Sealed. The gate is UNVERIFIED** |
| E10 | 11-13 | Which input groups drive FINAL? | Rows; withholding 576 forecasts (outcome-free) + retraining at Lead 1 (21 fits) | `scripts/ablation.py`, seed 168 | Regional accounts > market > poverty > agriculture/fish; climate, employment and news have no forecast effect | Dashboard recommendation |

**Reproducibility, all verified.**
- FINAL: 45/45 and 110/110 fits re-run identically (difference 0.0).
- FINAL-ET fitted models are identical to FINAL (750 rows, 0.0).
- The 2022 seal's FINAL rows equal the existing seal `4ad9267f` to within 5e-7 (six-decimal storage).
- Pipeline as-of, leakage and reproduction tests: 26/26.

**Not run, on purpose:**
- learned elapsed-time weights or damping (not identifiable from training);
- any threshold, class-weight or calibration tuning on the rows;
- province-specific features;
- displacement data (not compiled; identified from a test province);
- alternative algorithms (no evidence that the algorithm is the binding constraint: the in-round oracle of 11-12 matched H_cw).
