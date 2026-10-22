# E95: root-cause investigation and correction (report)

**Branch.** `e95-root-cause-breakthrough`, from `e94-final-unified-lgbm` (bf8a059). Not pushed. Production unchanged.

**Evidence.**
- Protocol: `PROTOCOL.md`, frozen at e78fc14. Deviation D1: a crash fix before any metric. D2: a crash in the final
  console print after `metrics.json` was written; no metric is affected.
- Run: `runs/20261022T062732Z/` (`metrics.json`, `predictions_k{1..4}.csv`).
- Tests: `backend/tests/integration/test_e95_root_cause.py`.

All 2023–2026 quarters are development evidence. This is the twelfth experiment on the same 13 quarters.

## 1. Target audit (from the code)

**Definition.** T43 = (regional SWS Balance Luzon hunger > 11.3%) AND (province food YoY > its 2021–22 P60, OR food
minus headline YoY > its P60).

**On the 65 evaluation rows:**
- the hunger condition holds on 76.9%;
- T43 equals the price condition on 78.5%;
- the hunger part is identical for all provinces;
- the price condition has 5–9 transitions per province; the hunger condition has one regime change.

**Verdict.** T43 is a proxy: provincial food-price pressure under elevated regional hunger. It does **not** measure
household food insecurity. It was **not redefined**.

**The measured outcome.** The only measured food-insecurity outcome observed every quarter is regional SWS involuntary
hunger. It was evaluated as a separate research target (§4).

## 2. Root cause of the K = 1 false alarms, and the correction

**Diagnosis.** At the 2025-Q3 origin, the price component gave 0.68–0.82 for Cavite, Laguna and Batangas, although:
- food YoY was 2–5 points below the threshold;
- the gap was below the threshold;
- rice was deflating 8–15%.

LightGBM contributions trace this to **cumF4**, the 4-quarter cumulative food YoY (+0.56..+0.73). It is a
regime-memory feature that keeps signalling the 2023–24 inflation episode after it ended.

**Corrections tested** (frozen protocol; selection on 2023–24 only):

| K = 1 | Accuracy | Balanced | HIGH caught | Brier | Selection block (2023–24) accuracy | Confirmation block (2025–26) accuracy / Brier |
|---|---|---|---|---|---|---|
| **BASE = E94 model** (reproduced, difference 8e-17) | **0.846** | **0.814** | **12/16** | 0.142 | **0.90** | 0.76 / 0.168 |
| PRUNE: no regime-memory features | 0.723 | 0.606 | 6/16 | 0.146 | 0.68 | **0.80 / 0.113** |
| CORE: parsimonious monotone price model | 0.692 | 0.564 | 5/16 | 0.164 | 0.65 | 0.76 / 0.182 |

**Result.** Removing regime memory **does** remove the 2025 false alarms: confirmation Brier 0.168 → 0.113. But it
also removes most of the 2023–24 HIGH detection (12 → 6 caught).

**The same information drives both.** "Inflation has been high" was the correct signal during the 2023–24 episode and
the wrong one after it. With a single inflation episode in the 2021+ data, no model can learn when such an episode
ends. That is a learnability limit of the data, not a coding defect.

**Decision.** The frozen selection rule (mean Brier, K = 1..3, 2023–24) keeps BASE (0.1562 vs CORE 0.1660, PRUNE
0.1694). E94 remains the model. No correction is adopted.

## 3. Horizon table (selected unified model = E94 M-U94; unchanged)

| K | Accuracy | Balanced | HIGH caught | Brier | Holm p vs persistence / climatology | PASS | Unmet |
|---|---|---|---|---|---|---|---|
| 1 | 0.846 | 0.814 | 12/16 | 0.142 | 0.105 / 0.177 | No | Brier significance only |
| 2 | 0.692 | 0.564 | 5/16 | 0.215 | 0.081 / 0.467 | No | all four |
| 3 | 0.646 | 0.513 | 4/16 | 0.191 | 0.006 / 0.292 | No | all four |
| 4 | 0.585 | 0.493 | 5/16 | 0.255 | 0.051 / 0.669 | No | all four |

**Validated K = 0.** No candidate in E95 passes at any K.

**At K = 2,** PRUNE reaches 0.738 accuracy but catches 1/16. S-COV (0.800, 5/16) remains the most accurate K = 2
model, and it is not ML. No model reaches K = 2 recall ≥ 0.5.

## 4. Research target: measured regional food insecurity (SWS hunger > 11.3%, 13 quarters, 10 HIGH)

Results are for the framework's hunger component; Holm p values are per-quarter sign-flip tests on Brier.

| K | Model accuracy / Brier | Persistence | Climatology | Always-HIGH | Holm p vs persistence / climatology / always-HIGH |
|---|---|---|---|---|---|
| 1 | **0.923 / 0.082** | 0.846 / 0.154 | 0.538 / 0.296 | 0.769 / 0.231 | 0.25 / **0.007** / 0.25 |
| 2 | 0.615 / 0.181 | 0.692 / 0.308 | 0.462 / 0.329 | 0.769 / 0.231 | 0.29 / **0.022** / 0.36 |
| 3 | 0.615 / 0.172 | 0.538 / 0.462 | 0.385 / 0.350 | 0.769 / 0.231 | **0.039** / **0.002** / 0.34 |

**What this shows.**
- **At K = 1, the hunger component is the most accurate predictor of measured regional hunger.** It beats climatology
  significantly, but not persistence or always-HIGH (13 quarters; 10 of them HIGH).
- **This is the framework's closest result to forecasting food insecurity itself,** and it is regional only.

## 5. Model–dashboard alignment (checked)

The production dashboard (`final-system-v2`) serves **FIRI v2 at Lead 2**: an evidence-weighted index, with the
E56-TUNED LightGBM as one affordability input and the SWS outlook = the latest posted round.
- That is **not** the E93–E95 unified model.
- **They are not aligned** in model, horizon (Lead 2 vs the best result at K = 1) or output (index vs T43 probability).
- Aligning them is a production change and needs authorization. Nothing was changed.

## 6. Objectives (Chapter I, §1.5.2) with this implementation

| Objective | Status |
|---|---|
| 1. News pipeline and FSSI | Built and required as model input. Its predictive contribution is not demonstrated (E93–E95 ablations: no gain at K = 1; hurts at K = 2–3). |
| 2. Metrics and the furthest reliable lead | All metrics computed with walk-forward validation. **No lead is reliable under the pre-registered rule (K = 0).** K = 1 misses only significance. |
| 3. Municipal and city rankings | Produced on the dashboard (FIRI v2), not from validated forecasts |
| 4. Comparison with baselines | Beats persistence, always-LOW and the PSA-only and NLP-only baselines on accuracy and balanced accuracy at K = 1. The Brier advantage is not significant. |
| 5. Dashboard and evaluation | Deployed; ISO 25010 results are outside this repository |

## 7. Plan for the observations that would change the result

| Priority | Data | How to obtain | Why it matters | Expected timing |
|---|---|---|---|---|
| 1 | Sealed outcomes 2026-Q4, 2027-Q1, 2027-Q2 | SWS releases; PSA CPI | The first unseen test of the E83/E84/E90/E91 seals | about Feb, May and Aug 2027 |
| 2 | SWS hunger for CALABARZON, 2021–2026 | SWS Survey Data Library request (letter drafted, E87 C), fee-based | A regional outcome instead of Balance Luzon; more onset examples per province | weeks to months |
| 3 | Provincial FIES (FNRI) and CBMS 2024 LGU food-security items | FNRI or eFOI request (E87 B); PSA CBMS request form (E87 A) | Validates the provincial and LGU outputs against measured food insecurity | months |
| 4 | Monthly food-access signal | DSWD or LGU program caseloads, via a DA IV-A data-sharing request | An earlier hunger signal for K = 2 | depends on agencies |
| 5 | More news coverage | Full-text archive with longer history | Tests whether news can lead hunger; currently 49 FSSI-admitted quarters, titles only | — |

None of these were obtained in this study: no new data, by instruction.

## 8. Conclusion

> The root cause of the remaining one-quarter-ahead false alarms was identified. A price feature that remembers past
> inflation kept signalling risk after the 2023–24 inflation episode ended. Removing it eliminated those false alarms
> but also removed most of the correct 2023–24 detections, because the same information drives both, and the
> 2021–2026 data contain only one such episode.
>
> The unified news-informed LightGBM therefore remains the E93/E94 configuration: 84.6% accuracy and 12 of 16 high-risk
> cases detected one quarter ahead. Its probability improvement is not significant, so the validated horizon is
> K = 0 under the unchanged criteria.
>
> Against the measured regional food-insecurity outcome (SWS hunger), its hunger component is the most accurate
> one-quarter-ahead predictor (92.3%), significantly better than climatology but not demonstrably better than
> persistence over 13 quarters.
>
> Further gains require new observations (§7), not further tuning on the same quarters.
