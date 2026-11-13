# FINAL (RATE + MIND): official model selection, thesis-aligned validation (2026-11-13)

**Basis:** the owner's brief "Official model selection, thesis-aligned validation, scientific justification and final implementation". It supersedes the same-day "targeted reliability recovery" brief; ENNS 2022 is excluded.

**Builds on:** `../aiPHeed_final_reliability_20261113/` (reliability study, G1–G9 diagnostics) and the 11-12/11-13 FINAL studies. Nothing there was overwritten.

| # | Brief deliverable | Where |
|---|---|---|
| 1 | Final model selection and justification | `01_MODEL_SELECTION_AND_RECOMMENDATION.md` §1–3 |
| 2 | Research objective compliance matrix | `02_OBJECTIVE_COMPLIANCE_MATRIX.md` |
| 3 | Methodological decision and reference matrix | `03_METHODOLOGY_REFERENCE_MATRIX.md` |
| 4 | Public dataset and ground-truth audit | `04_DATA_GROUND_TRUTH_AND_HARMONIZATION.md` |
| 5 | FNRI harmonisation and uncertainty | `04_…` §1–3 |
| 6 | Chronological validation by round | `05_VALIDATION_BASELINES_STABILITY_EXTERNAL.md` §1 |
| 7 | HIGH-risk detection and false negatives | `06_HIGH_RISK_FALSE_NEGATIVES.md` |
| 8 | Baseline comparison | `05_…` §2 |
| 9 | Algorithm 3 MRLT, Leads 1–8 | `07_ALGORITHM3_MRLT_AND_ACCEPTANCE.md` §2 |
| 10 | Fold accuracies and mean accuracy | `07_…` §2; `evidence/A3_folds.csv` |
| 11 | F1 and AUC acceptance | `07_…` §3 |
| 12 | Stability and sensitivity | `05_…` §3 |
| 13 | Group and indicator contributions | `09_CONTRIBUTORS_AND_DASHBOARD.md` §1–4 |
| 14 | Final dashboard contributor structure | `09_…` §5 |
| 15 | External plausibility | `05_…` §4 |
| 16 | Configuration and reproducibility | `11_CONFIG_REPRODUCIBILITY_AND_SEAL.md` §1, §4 |
| 17 | Sealed forecast artifacts | `evidence/SEALED_FINAL_2027Q1_2028Q1.json` (+ `.sha256`); `11_…` §2–3 |
| 18 | Updated PASS/FAIL | `12_PASS_FAIL_ASSESSMENT.md` |
| 19 | Production-readiness recommendation | `01_…` §4 |

**Headline:**
- Thesis Algorithm 3 gives **MRLT = 5 quarters** (Lead 6 first fails at 74.7 %).
- Lead 1 meets every thesis target: accuracy 86.1 %, F1 0.80, AUC 0.898.
- The F1 target fails at Leads 3 and 5, so Leads 1–2 are recommended for publication.
- 2021 HIGH detection is 1/4, caused by long-gap extrapolation.
- Only regional economy and harvests have out-of-sample value.
- Forecasts sealed: `80b20aed…`, all LOW.
- Nothing is committed or deployed. Production is still E196.
