# FINAL — public-data reliability and credibility study (2026-11-13)

**Model:** FINAL (RATE + MIND) LightGBM. Not retrained, re-tuned or re-thresholded. No synthetic data.
**Gates:** `PROTOCOL_REL.md`, sha256 `1efdf5a4…`, written before the new computations.

| # | Deliverable | File |
|---|---|---|
| 1 | Complete data audit | `01_DATA_AUDIT.md` |
| 2 | Historical validation by survey round | `02_VALIDATION_BY_SURVEY_ROUND.md` |
| 3 | Metric comparison against all baselines | `03_METRICS_VS_BASELINES.md` |
| 4 | HIGH-risk detection report | `04_HIGH_RISK_DETECTION.md` |
| 5 | Stability and maximum-lead report | `05_STABILITY_AND_MAX_LEAD.md` |
| 6 | Five-group contributor validation | `06_CONTRIBUTOR_GROUP_VALIDATION.md` |
| 7 | External plausibility report | `07_EXTERNAL_PLAUSIBILITY.md` |
| 8 | Reproducibility report | `08_REPRODUCIBILITY.md` |
| 9 | Sealed forecast artifacts and scoring procedure | `09_SEALED_FORECASTS_AND_SCORING_PROCEDURE.md` |
| 10 | PASS/FAIL for every criterion | `10_PASS_FAIL_ASSESSMENT.md` |

`scripts/` holds every script used, `evidence/` every output, and `parts/` the 40 new stability refits. `HASHES.sha256` covers all of them.

**Verdict:** FINAL fails the gates at Lead 1, because 2021 HIGH recall is 1/4. The maximum reliable lead is therefore 0. Nothing was frozen and no new seal was made. The ENNS 2022 seals `4ad9267f` / `71ebe142` remain the prospective test.

Nothing is committed or deployed. E196 remains production.
