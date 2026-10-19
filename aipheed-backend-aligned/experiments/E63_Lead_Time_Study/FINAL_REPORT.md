# E63 final report: lead-time study of the E56/E58 procedure (Objective 2 V)

**Date:** 2026-10-19.
**Protocol:** `PROTOCOL.md`, SHA-256 (LF) `5b3ee7e9cd64d40dcd874c37ef3158bb4d60bba31f9ebcdfc124415e218ba0f2`, frozen 2026-10-19T10:13:15Z.
**Sealed forecasts:** `sealed/predictions.csv`, 155 rows, SHA-256 `7acae3a1c89f72fc17fe740cf345d0c7f612e7b01ecea52730caaac4f17c16d3`, sealed 2026-10-19T10:14:59Z, before any label was read. Both hashes are also recorded outside the repository, in the session notes folder.
**Status:** development evidence. Nothing has been committed, served or switched. E38 remains the production default.

## 1. Answer

**No lead time meets the pre-registered reliability rule.** So the furthest horizon at which reliable forecasting is achievable **cannot be established** with the 2021–2026 data.

| Lead | Verdict |
|---|---|
| **1** (the quarter that begins on the issue date) | Closest to the rule. E56 improves on persistence and climatology in Brier score, with cluster-bootstrap CIs that exclude 0. But it wins only **9 of 12 quarters** against each baseline (sign test p = 0.146; 10 wins are needed). **Suggestive, not established.** |
| **2** (the served E56/E58 horizon) | Improvement over persistence is suggestive. Improvement over climatology is **not supported** (5–5 quarters; CI [−0.192, +0.001]). |
| **3** | E56 is **indistinguishable from climatology**: Brier difference −0.015, CI [−0.114, +0.085]. |
| **4** | **Not computable.** The E56 base-effect projection needs the year-earlier CPI month, which is month 3 of the issue quarter. That month is after the CPI cutoff (month 2 of t), so no forecast can be formed at any origin (PROTOCOL section 1). |

**Skill falls steadily with lead time.** On the same 9 target quarters (2024-Q3..2026-Q3):
- the E56 Brier score is 0.113 at lead 1, 0.178 at lead 2 and 0.251 at lead 3;
- the advantage over climatology is −0.134, −0.079 and −0.015;
- AUC is 0.933, 0.763 and 0.620.

The E58-EW warning form reaches the same verdict at every lead.

## 2. What was run

**Procedure:**
- E56-TUNED was re-run at every eligible origin of leads 1, 2 and 3, with walk-forward expanding-window refitting.
- Selection was the same as E56: 72 configurations, seed 56, inner forward log-loss with the simplicity tie-break, and decision p ≥ 0.5.
- The E56 code chain was imported read-only. Only the six places where it hard-codes "2" were re-implemented with the lead as a parameter (`runner/e63_lib.py`, PROTOCOL section 3, H1–H6).

**Data:**
- Cutoffs are E41/E56's, unchanged (PROTOCOL section 2).
- The data window is 2021-01..2026-10-14. No new data were fetched.

**Integrity checks:**

| Check | Result |
|---|---|
| Lead-2 inputs of `e63_lib` vs the E56 inputs | identical (exact frame equality) |
| Lead-2 forecasts vs sealed E57 | max abs difference **5.0e-13**; same configuration at all 10 origins |
| Write guard (411 files in E56–E62 and `backend/data`) | unchanged before vs after (`out/guard_check.json`) |
| Tests (`tests/test_e63.py`) | 5 passed: fold equality at h = 2, embargo h+1, lead-4 cutoff conflict, training targets ≤ t−1, seals |
| Re-running the score step | byte-identical tables |

**Rows:**

| Lead | Origins | Targets | Rows (quarters) | Configurations selected | Training quarters |
|---|---|---|---|---|---|
| 1 | 2023-Q3..2026-Q2 | 2023-Q4..2026-Q3 | 60 (12) | 8 distinct | 6–17 |
| 2 | 2023-Q4..2026-Q1 | 2024-Q2..2026-Q3 | 50 (10) | 9 distinct | 7–16 |
| 3 | 2023-Q4..2025-Q4 | 2024-Q3..2026-Q3 | 45 (9) | 6 distinct | 6–14 |
| 4 | — | — | 0 | not computable | — |

## 3. Lead × metric table (each lead's full eligible set)

- Decisions use p ≥ 0.5.
- 95% CIs come from a quarter-cluster bootstrap (4000 draws, seed 63).
- E58-EW scores P_price as its probability.
- Calibration columns: CITL = mean(y) − mean(p); slope = logistic calibration slope (1 = ideal; < 1 = over-confident).

| Lead | Arm | n (quarters) | HIGH | Accuracy [95% CI] | Balanced acc. [CI] | HIGH recall [CI] | HIGH precision [CI] | Brier [CI] | Log loss [CI] | AUC | CITL | Slope |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | **E56** | 60 (12) | 21 | **0.850** [0.733, 0.933] | 0.819 [0.675, 0.944] | 0.714 [0.417, 1.000] | 0.833 [0.631, 1.000] | **0.130** [0.078, 0.188] | 0.420 [0.272, 0.583] | 0.901 | −0.005 | 0.968 |
| 1 | E58-EW | 60 (12) | 21 | 0.883 [0.800, 0.950] | 0.877 [0.783, 0.959] | 0.857 [0.667, 1.000] | 0.818 [0.652, 0.943] | 0.118 [0.080, 0.157] | 0.403 [0.278, 0.537] | 0.923 | −0.065 | 1.142 |
| 1 | Persistence | 60 (12) | 21 | 0.683 [0.567, 0.800] | 0.647 [0.512, 0.766] | 0.524 [0.231, 0.789] | 0.550 [0.263, 0.818] | 0.317 [0.200, 0.433] | 2.188 [1.382, 2.994] | 0.647 | 0.017 | — |
| 1 | Climatology | 60 (12) | 21 | 0.650 [0.467, 0.817] | 0.500 | 0.000 | — | 0.284 [0.164, 0.414] | 0.851 [0.524, 1.211] | 0.344 | 0.184 | −0.458 |
| 2 | **E56** | 50 (10) | 18 | **0.720** [0.560, 0.840] | 0.684 [0.542, 0.832] | 0.556 [0.217, 0.895] | 0.625 [0.375, 0.857] | **0.214** [0.146, 0.304] | 0.623 [0.461, 0.840] | 0.649 | −0.029 | 0.550 |
| 2 | E58-EW | 50 (10) | 18 | 0.780 [0.700, 0.860] | 0.780 [0.679, 0.867] | 0.778 [0.500, 1.000] | 0.667 [0.454, 0.840] | 0.182 [0.143, 0.222] | 0.562 [0.460, 0.672] | 0.786 | −0.103 | 0.753 |
| 2 | Persistence | 50 (10) | 18 | 0.560 [0.400, 0.740] | 0.535 [0.341, 0.745] | 0.444 [0.100, 0.857] | 0.400 [0.095, 0.750] | 0.440 [0.260, 0.600] | 3.040 [1.797, 4.145] | 0.535 | −0.040 | — |
| 2 | Climatology | 50 (10) | 18 | 0.640 [0.440, 0.820] | 0.500 | 0.000 | — | 0.304 [0.167, 0.457] | 0.939 [0.543, 1.420] | 0.214 | 0.190 | −1.709 |
| 3 | **E56** | 45 (9) | 14 | **0.622** [0.467, 0.800] | 0.569 [0.462, 0.724] | 0.429 [0.143, 0.800] | 0.400 [0.200, 0.667] | **0.251** [0.154, 0.343] | 0.726 [0.488, 0.958] | 0.620 | −0.053 | 0.249 |
| 3 | E58-EW | 45 (9) | 14 | 0.644 [0.511, 0.800] | 0.624 [0.506, 0.761] | 0.571 [0.308, 0.846] | 0.444 [0.235, 0.700] | 0.244 [0.151, 0.334] | 0.705 [0.476, 0.930] | 0.657 | −0.112 | 0.321 |
| 3 | Persistence | 45 (9) | 14 | 0.511 [0.333, 0.667] | 0.488 [0.274, 0.667] | 0.429 [0.000, 0.786] | 0.300 [0.000, 0.600] | 0.489 [0.333, 0.667] | 3.378 [2.303, 4.606] | 0.488 | −0.133 | — |
| 3 | Climatology | 45 (9) | 14 | 0.689 [0.489, 0.867] | 0.500 | 0.000 | — | 0.266 [0.134, 0.412] | 0.816 [0.468, 1.211] | 0.247 | 0.149 | −1.038 |
| 4 | all arms | 0 | — | not computable (section 1) | | | | | | | | |

**Notes on the table:**
- The lead-2 point estimates equal E57's. The CIs differ slightly, because E63 uses 4000 draws with seed 63 (the E61 rule), while E57 used 2000 draws with seed 57.
- Majority-class and province-climatology results are in `tables/lead_metrics.csv`.
- Reliability bins are in `tables/reliability_bins.csv`.

## 4. Reliability rule (PROTOCOL section 8)

A lead is reliable only if the paired Brier improvement over **both** persistence and climatology has:
- a cluster-bootstrap 95% CI entirely below 0; **and**
- a quarter sign test with p < 0.05 in the model's favour.

| Lead | Model | vs | Mean Brier diff [95% CI] | Quarter W–L | Sign p | Wins needed | Verdict |
|---|---|---|---|---|---|---|---|
| 1 | E56 | Persistence | −0.187 [−0.287, −0.085] | 9–3 | 0.146 | 10 of 12 | suggestive, not established |
| 1 | E56 | Climatology | −0.155 [−0.258, −0.056] | 9–3 | 0.146 | 10 of 12 | suggestive, not established |
| 2 | E56 | Persistence | −0.226 [−0.389, −0.058] | 7–3 | 0.344 | 9 of 10 | suggestive, not established |
| 2 | E56 | Climatology | −0.090 [−0.192, +0.001] | 5–5 | 1.000 | 9 of 10 | not supported |
| 3 | E56 | Persistence | −0.237 [−0.419, −0.067] | 7–2 | 0.180 | 8 of 9 | suggestive, not established |
| 3 | E56 | Climatology | −0.015 [−0.114, +0.085] | 6–3 | 0.508 | 8 of 9 | not supported |
| 4 | — | — | not computable | — | — | — | fails by definition |
| 1 | E58-EW | Persistence / Climatology | −0.198 [−0.313, −0.084] / −0.166 [−0.286, −0.050] | 9–3 / 9–3 | 0.146 / 0.146 | 10 of 12 | suggestive / suggestive |
| 2 | E58-EW | Persistence / Climatology | −0.258 [−0.438, −0.072] / −0.123 [−0.264, −0.002] | 7–3 / 5–5 | 0.344 / 1.000 | 9 of 10 | suggestive / suggestive |
| 3 | E58-EW | Persistence / Climatology | −0.245 [−0.423, −0.072] / −0.022 [−0.134, +0.084] | 6–3 / 5–4 | 0.508 / 1.000 | 8 of 9 | suggestive / not supported |

**Furthest reliable lead:**

| Arm | Set | Result |
|---|---|---|
| E56 (headline) | full | **none** |
| E56 | common | **none** |
| E58-EW | full | **none** |
| E58-EW | common | **none** |

**Why lead 1 falls short.** The three quarters lost to persistence are 2024-Q1, 2026-Q2 and 2026-Q3:
- Persistence was right in all five provinces in 2024-Q1 and 2026-Q3 (Brier 0), and in four of five in 2026-Q2 (Brier 0.20).
- E56 lost by 0.012, 0.051 and 0.002 respectively.

The three quarters lost to climatology are 2024-Q1, 2025-Q4 and 2026-Q2. These are calm quarters (0–1 HIGH province), where climatology's low probability (0.04–0.25) is hard to beat. In 2025-Q4 and 2026-Q2, E56 issued at least one high probability (up to 0.56 and 0.87) for a province that stayed LOW.

So the large average gain at lead 1 comes from the stress quarters, and the near-unanimity the sign test demands is not reached. This is a property of the rule with 9–12 quarters, stated in advance (PROTOCOL section 8). The rule was not changed.

## 5. Common-target sensitivity (2024-Q3..2026-Q3, 45 rows at each lead)

| Lead | E56 accuracy | Balanced acc. | HIGH recall | HIGH precision | Brier | AUC | vs persistence | vs climatology |
|---|---|---|---|---|---|---|---|---|
| 1 | 0.889 [0.800, 0.978] | 0.880 | 0.857 | 0.800 | 0.113 [0.063, 0.162] | 0.933 | −0.221 [−0.341, −0.096], 7–2 (p 0.180) | −0.134 [−0.254, −0.028], 7–2 (p 0.180) |
| 2 | 0.778 [0.689, 0.867] | 0.760 | 0.714 | 0.625 | 0.178 [0.137, 0.225] | 0.763 | −0.222 [−0.412, −0.039], 6–3 (p 0.508) | −0.079 [−0.195, +0.020], 4–5 (p 1.000) |
| 3 | 0.622 [0.467, 0.800] | 0.569 | 0.429 | 0.400 | 0.251 [0.154, 0.343] | 0.620 | −0.237 [−0.419, −0.067], 7–2 (p 0.180) | −0.015 [−0.114, +0.085], 6–3 (p 0.508) |

- Same verdict as the full sets: no lead is reliable.
- On identical targets, the decline from lead 1 to lead 3 is monotone in every metric.
- Climatology's accuracy (0.689) is above E56's at lead 3. Its balanced accuracy is 0.5, because it never predicts HIGH.

## 6. Calibration and discrimination by lead

| Lead | Slope | CITL | What it means |
|---|---|---|---|
| 1 | 0.97 | −0.005 | Well calibrated overall. The bin 0.0–0.2 has 27 rows, mean p 0.09, observed 0.04; the upper bins are small (6–12 rows) and scatter around the diagonal. |
| 2 | 0.55 | — | Over-confident. The 0.0–0.2 bin has mean p 0.13 but observed 0.43, driven by the 2024-Q2 stale-hunger quarter documented in E58/E59. |
| 3 | 0.25 | — | Strongly over-confident. The probabilities carry little ranking information (AUC 0.62). |

**Persistence beyond lead 2.** E56's advantage over persistence stays large at every lead (about −0.19 to −0.24). This is mostly because a 0/1 persistence forecast is heavily penalised when the state changes; it is not because E56 itself stays skilful. Against climatology, which is the harder benchmark here, the gain fades by lead 3.

## 7. Limitations

1. **Development evidence only.** Every target quarter was examined in E43–E62, and the lead-2 result was known before the protocol (disclosed in PROTOCOL section 0). Leads 1 and 3 had not been scored for this model. Independent evidence can only come from forecasts frozen before their outcomes are published.
2. **Few quarters.** The study has 9–12 target quarters per lead. The CIs are wide, and the sign test needs 9 of 10, 10 of 12 or 8 of 9 quarter wins.
3. **One regional hunger series.** The hunger part of T43 is a single regional SWS series, so the five provinces in a quarter are not independent. Clustering by quarter handles this. It is also why the effective sample is the quarter count, not the row count.
4. **No multiplicity correction across leads.** A correction would only make the rule stricter, so it cannot change the "none" verdict.
5. **Lead 4 is a cutoff limit, not a model failure.** The E56 offset needs a year-earlier CPI base month that is not yet published at the issue date. A lead-4 forecast would need a different procedure. None was introduced, and none should be added without a new protocol.
6. **Lead 1's operational window is short.** Lead 1 forecasts the quarter that has just begun. Its outcome is published only after that quarter ends: CPI about one month later, SWS rounds later still. This still gives warning time before the official figures, but less than lead 2 gives.

## 8. Chapter IV-ready answer to SOP Q2 / Objective 2 V

To address Objective 2 V, the forecasting procedure of the system was re-run at lead times of one, two, three, and four quarters. This is the E56-TUNED LightGBM model, P(HIGH) = P(hunger) × P(price pressure), together with its E58 early-warning form. The re-run used walk-forward expanding-window cross-validation, in which the model was retrained at every origin using only information published before the issue date, in accordance with the study's data-availability rules. Since Chapter I does not define reliability, a working definition was fixed before any result was read. A lead time was considered reliable when the paired Brier-score improvement over both persistence and climatology was supported by a quarter-cluster bootstrap confidence interval that excluded zero and by a quarter-level sign test at p < 0.05. Forecast skill declined steadily as the lead time lengthened. On the same nine target quarters (2024-Q3 to 2026-Q3), the Brier score rose from 0.113 at one quarter to 0.178 at two quarters and 0.251 at three quarters, while the advantage over climatology narrowed from 0.134 to 0.079 and 0.015. At one quarter ahead, the model improved on persistence and climatology with confidence intervals that excluded zero (Brier score 0.130 against 0.317 and 0.284; accuracy 0.85 and balanced accuracy 0.82 on 60 province-quarters). However, it was better in only 9 of 12 quarters, short of the 10 required by the sign test, so this improvement is suggestive and not established. At two quarters, the improvement over climatology was not supported. At three quarters, the model was indistinguishable from climatology. At four quarters, a forecast could not be produced, because the year-earlier consumer price month required by the base-effect projection is not yet published on the issue date. Correspondingly, none of the four lead times met the reliability criterion, and the furthest horizon at which reliable forecasting is achievable could not be empirically established within the 2021–2026 study window. These results are indicative and not definitive determinations. They rest on 9 to 12 target quarters that were already examined during development, and the strongest evidence of short-horizon skill lies at one quarter ahead, arising from the quarters of rising food stress rather than the calm quarters.

## 9. Files

| File | Content |
|---|---|
| `PROTOCOL.md`, `runner/PROTOCOL_SHA256.txt`, `runner/PROTOCOL_FROZEN_AT.txt` | pre-registration and freeze |
| `runner/e63_lib.py` | lead-h generalisation (H1–H6), baselines, score-free label existence |
| `runner/e63_eligibility.py` → `tables/eligibility.csv`, `out/eligibility.json` | score-free eligibility and the lead-2 input identity check |
| `runner/e63_predict.py` → `sealed/predictions.csv` (+ `.sha256`), `out/predict_meta.json`, `out/predict_console.txt` | sealed forecasts and the E57 reproduction |
| `runner/e63_score.py` → `tables/lead_metrics.csv`, `tables/paired_tests.csv`, `tables/per_quarter.csv`, `tables/reliability_bins.csv`, `out/scores.json`, `out/score_console.txt` | scores and rule verdicts |
| `runner/e63_guard.py` → `out/guard_before.json`, `out/guard_after.json`, `out/guard_check.json` | write guard for E56–E62 and `backend/data` |
| `tests/test_e63.py` | 5 checks |
| `DEVIATIONS.md` | deviations from the brief and the protocol |

**Reproduce** (from this folder):

```
C:/Users/admin/aipheed/backend/venv/Scripts/python.exe -B runner/e63_score.py
```

The predict step refuses to run again, because the seal is write-once.
