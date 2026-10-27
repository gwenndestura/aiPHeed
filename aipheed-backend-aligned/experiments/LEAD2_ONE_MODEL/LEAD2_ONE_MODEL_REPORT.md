# Lead-2 improvement with one unified LightGBM: report

**Branch:** `aiPHeed/lead2-one-model`, from `a1ce8ce`.

**Protocol:** `PROTOCOL_ONE_MODEL.md`, sha `4a98e2bd…`, frozen and committed (`5dc63e8`) before any candidate was scored.

**Nothing merged, deployed or served:** the dashboard still serves P0H4.

**Evidence status.** All 2021–2026-Q3 quarters were examined in earlier experiments, so every result is **development evidence**. Hyperparameters are chosen inside each origin's training window: never on the quarter being forecast. But the *design* of these candidates was informed by the earlier audits of the same quarters. **No untouched quarter exists** until SWS publishes 2026-Q4 (about January 2027).

## 1. Baseline reproduction (`runner/reproduce.py`, `out/p0h4_reproduction.json`)

**P0H4** (served; commit `a1ce8ce`) was recomputed from code: the hunger term at every origin and lead (max difference 5e-7), and the metrics with sklearn. It matches `backend/data/ch1_engine/evaluation.json` exactly.

| Lead | Rows (quarters, HIGH) | Accuracy | Balanced | Precision / recall | False-alarm rate | ROC-AUC / PR-AUC | Brier | TP / FP / FN / TN |
|---|---|---|---|---|---|---|---|---|
| 1 | 70 (14, 17) | 0.843 | 0.776 | 0.69 / 0.65 | 0.094 | 0.87 / 0.65 | 0.132 | 11 / 5 / 6 / 48 |
| **2** | **65 (13, 17)** | **0.769** | **0.635** | **0.60 / 0.353** | 0.083 | 0.63 / 0.42 | **0.194** | **6 / 4 / 11 / 44** |

**Lead 2 in time.**
- Issued on the first day of quarter t+1, for quarter t+2. The target quarter starts 181–184 days after issue.
- Information cut-off: SWS rounds published before the issue date (newest reading = quarter t−1, true horizon 3 quarters); CPI months ≤ month 2 of quarter t.
- Verified at all 13 issue dates: every target's SWS rounds and CPI months fall after the cut-off (`out/timing_audit.txt`, `out/lead2_timing.csv`).

## 2. Root cause of the Lead-2 misses (`out/audit.txt`, `out/p0h4_lead2_cases.csv`, `../BIAS_AUDIT/out/onsets.txt`)

**The 11 missed HIGH rows (10 are new onsets; 0 of 10 onsets are caught):**

| Group | Rows | What switched on | Component that missed | Cause | Fixable with issue-time data? |
|---|---|---|---|---|---|
| 2023-Q4 Batangas, Laguna, Quezon | 3 | hunger (8.7 → 14.3) | both | No early-warning information: newest SWS 8.7, price projection −5 to −8. The rice surge began after the issue date (2023-07-01). | No |
| 2024-Q2 Batangas, Cavite, Laguna, Quezon | 4 | price (hunger already HIGH in 2024-Q1) | **hunger** (π_H 0.40); the price part was right (0.68–0.80) | **Delayed publication:** the surge reading (2023-Q4, 14.3) came out 2024-01-22, 21 days after the 2024-01-01 issue | Not without information the model did not have |
| 2024-Q4 Cavite, Laguna; 2026-Q2 Cavite | 3 | price | price | No issue-time price warning (A1 −2.9 to −6.1) | No |
| 2024-Q3 Quezon (sustained HIGH) | 1 | – | price | **Model weakness:** the structural projection pointed HIGH (gap +0.58) and the fitted model overrode it | **Yes** (single-model candidates with the structural offset catch it) |

**Further evidence:**
- **The product rule caused no miss.** Of 23 rows with both components ≥ 0.5, the product fell below 0.5 in 13, and **none of those 13 was HIGH**.
- **Target definition:** **8 of the 17 HIGH rows had their price condition decided within 0.5 points of a threshold, and 6 of the 11 misses are among them.** Examples: Cavite 2026-Q2 +0.02, Batangas 2024-Q2 +0.07, Batangas 2023-Q4 +0.11, against CPI published to 0.1 point. Most HIGH rows are decided by the *food-minus-headline gap* leg, whose P60 thresholds are small (−0.56 to +0.92 points).
- **News:** available at issue for only 1 of the 11 missed rows (17% coverage of Lead-2 rows).

**Hunger component (13 independent quarter outcomes at Lead 2).**

| Rule | Quarters correct | Brier | Onset 2023-Q4 | Onset 2024-Q2 |
|---|---|---|---|---|
| π_H4 (served) | 10 | 0.137 | 0.22 | 0.40 |
| π_H0 (previous) | 10 | 0.135 | – | – |
| Latest > 11.3 | 10 | 0.231 | – | – |
| Latest + last change | 7 | – | – | – |
| Either of last two | 9 | – | – | – |

None anticipates either onset.

**Four-area σ.**
- Errors of the four SWS areas correlate at 0.51 across areas, so the 56 pooled errors are worth about **22 independent errors** (design effect 2.5).
- The pooled σ (6.8 points) is wider than Balance Luzon's own (5.0), mainly because Mindanao and Visayas are more volatile.
- So H4 is better described as "BL reading with a borrowed, wider uncertainty". Its gain is in probability calibration (Brier), not in more HIGH calls.

**SWS design change (household heads → adults, 2025-Q2).**
- Quarter-to-quarter |change| in BL hunger: 6.4 points after vs 3.5 before (rounds alternate n = 600 and n = 300).
- Lead-2 P0H4 recall: 1/11 before 2025-Q2 vs 5/6 after. The later period is easier because hunger stayed above 11.3 in every quarter and there were no hunger onsets, not because the model improved.

## 3. Experiments (single LightGBM; frozen protocol)

**Common design.** Every candidate is **one LightGBM** trained directly on the combined target T43c on the stacked rows of all leads 1–15:
- all 12 FIRI v2 families, `lead`, world prices, hunger inputs;
- no separate hunger model, no multiplication.

| Id | Change | Mechanism addressed |
|---|---|---|
| S0 | Base (12 families + lead + world prices + latest SWS reading, true horizon, regional rice and food CPI) | reference |
| S1 | + issue-time hunger dynamics (change, 4-quarter mean and max, margin to 11.3, run length; NCR, Visayas and Mindanao latest readings and changes) | price-before-hunger (4 rows) |
| S2 | S1 + structural price offset (init_score = logit of the A1 structural price probability) | the override (1 row); M5 |
| S3 | S2 with balanced class weights | recall under 26% HIGH |

**Leakage.** A 6-origin future-perturbation audit of all four passed: 900 values identical per origin (`out/leakage_audit.json`).

## 4. Matched evaluation (identical 70 Lead-1 and 65 Lead-2 rows)

| Model | Lead 1 accuracy (bal; P/R; Brier) | Lead 2 accuracy | Bal | P / R | FAR | AUC / PR-AUC | Brier | TP / FP / FN | Max reliable lead |
|---|---|---|---|---|---|---|---|---|---|
| **P0H4 (served hybrid)** | 0.843 (0.776; 0.69/0.65; 0.132) | **0.769** | 0.635 | 0.60 / 0.35 | 0.083 | 0.63 / 0.42 | **0.194** | 6 / 4 / 11 | 1 |
| UNI-FINAL (previous) | 0.829 (0.767; 0.65/0.65; 0.131) | 0.769 | 0.635 | 0.60 / 0.35 | 0.083 | 0.59 / 0.41 | 0.206 | 6 / 4 / 11 | 1 |
| S0 single LightGBM | 0.814 (fails R5, R6) | 0.677 | 0.591 | 0.39 / 0.41 | 0.229 | 0.52 / 0.42 | 0.243 | 7 / 11 / 10 | none |
| S1 + hunger dynamics | 0.771 | 0.662 | 0.562 | 0.35 / 0.35 | 0.229 | 0.51 / 0.40 | 0.241 | 6 / 11 / 11 | none |
| S2 + structural offset | 0.871 (fails R6: recall 0.59) | 0.754 | 0.643 | 0.54 / 0.41 | 0.125 | 0.52 / 0.48 | 0.218 | 7 / 6 / 10 | none |
| **S3 + balanced weights** | **0.857** (0.786; 0.73/0.65; **0.112**); **passes R1–R7** | 0.738 | 0.633 | 0.50 / 0.41 | 0.146 | 0.51 / 0.46 | 0.232 | 7 / 7 / 10 | **1** |
| PERSIST-SI | 0.743 | 0.677 | 0.591 | 0.39 / 0.41 | – | – | 0.323 | – | – |
| Price-only diagnostic (π_P alone) | 0.700 | 0.615 | 0.607 | 0.36 / 0.59 | – | 0.73 / 0.59 | 0.214 | 10 / 18 / 7 | – |
| Hunger-only (latest > 11.3) | 0.514 | 0.431 | 0.482 | 0.25 / 0.59 | – | – | 0.569 | – | – |
| Always-LOW | 0.757 | 0.738 | 0.500 | – / 0 | 0 | – | 0.262 | 0 / 0 / 17 | – |

**Selection (frozen guards).** No candidate was admissible: every development Lead-2 Brier (0.272–0.279) is above the 0.2546 guard. **No winner is declared.**

**Success criteria I1–I6 vs P0H4.**
- Every candidate fails I1 (recall ≥ 8/17: each finds 7), I3 (balanced accuracy ≥ 0.685), I4 (Brier ≤ 0.204) and I5 (new detections in ≥ 2 quarters: each adds one, in 2024-Q3).
- S2 and S3 pass I2 (precision/false alarms) and I6 (Lead 1 not worse).

**S3 vs P0H4** (Brier, cluster bootstrap by quarter; S3 − P0H4):

| Lead | Difference (90% CI) | p |
|---|---|---|
| 1 | −0.020 (−0.060, +0.025) | .43 |
| 2 | +0.037 (−0.012, +0.095) | .25 |
| 3 | **+0.073 (+0.022, +0.131)** | **.003** |

## 5. Quarter by quarter, Lead 2 (5 province rows each; TP/FP)

| Target | BL hunger | HIGH | P0H4 | S2 | S3 | Mean p (P0H4 / S2) |
|---|---|---|---|---|---|---|
| 2023-Q2 | 11.3 (not > 11.3) | 0 | 0/0 | 0/0 | 0/0 | 0.08 / 0.02 |
| 2023-Q3 | 10.3 | 0 | 0/0 | 0/0 | 0/0 | 0.29 / 0.02 |
| **2023-Q4** | 14.3 | **3** | 0/0 | 0/0 | 0/0 | 0.09 / 0.01 |
| 2024-Q1 | 15.3 | 0 | 0/0 | 0/0 | 0/0 | 0.29 / 0.01 |
| **2024-Q2** | 19.6 | **4** | 0/0 | 0/0 | 0/0 | 0.31 / 0.01 |
| 2024-Q3 | 18.1 | 1 | 0/1 | **1**/2 | **1**/2 | 0.35 / 0.50 |
| 2024-Q4 | 25.3 | 3 | 1/0 | 1/0 | 1/0 | 0.28 / 0.22 |
| 2025-Q2 | 16.15 | 3 | 3/1 | 3/1 | 3/1 | 0.53 / 0.66 |
| 2025-Q3 | 23.8 | 2 | 2/1 | 2/1 | 2/2 | 0.58 / 0.62 |
| 2025-Q4 | 16.7 | 0 | 0/0 | 0/0 | 0/0 | 0.32 / 0.22 |
| 2026-Q1 | 22.4 | 0 | 0/0 | 0/0 | 0/0 | 0.29 / 0.24 |
| 2026-Q2 | 17.3 | 1 | 0/1 | 0/1 | 0/1 | 0.30 / 0.34 |
| 2026-Q3 | 23.6 | 0 | 0/0 | 0/1 | 0/1 | 0.12 / 0.18 |

**Reading.** 2023-Q4 and 2024-Q2 (7 HIGH rows) are missed by every model. The single models are *more confident* that those quarters are LOW (p ≈ 0.01), because at those issue dates no T43c HIGH outcome with a low latest SWS reading existed in their training rows.

## 6. Leakage and timing

| Check | Result |
|---|---|
| Future-perturbation audit, 6 origins, S0–S3 | identical (900 values each) |
| Lead-2 timing at all 13 issue dates | verified (§1) |
| Hyperparameters | chosen per origin on that origin's earlier training rows only |
| Thresholds and calibration | in-window only; not applied, as no candidate was selected |
| Historical replay of S3 (diagnostic) | `out/historical_replay_S3.json` |
| P0H4 replay | from LEAD2_OPTIMIZATION (3 origins, ≤ 5e-7) |

## 7. News

**Served P0 (LEAD2_OPTIMIZATION).**

| Lead | No-news ablation (Brier change) | Holm p | Shuffled-news permutation p (20 shuffles) |
|---|---|---|---|
| 1 | −0.012 | .86 | .05 |
| 2 | – | 1.0 | .95 |

News coverage is 17% of Lead-2 rows.

**Single model S3 (diagnostic: S3 was not selected).** `out/news_S3.json`. The Brier change from adding news is *worse* with news:

| Lead | Change (with − without news) | p | Holm p |
|---|---|---|---|
| 1 | +0.0009 | .20 | .60 |
| 2 | +0.0008 | – | 1.0 |
| 3 | +0.0006 | – | 1.0 |

The shuffled-news permutation p is .65 (Lead 1), 1.0 (Lead 2) and .30 (Lead 3). Historical replay of S3 is identical (≤ 5e-7).

**Conclusion.** News does not improve Lead-2 recall, discrimination or calibration. A Lead-1 gain is suggestive at most.

## 8. Selected candidate

**No candidate meets the frozen selection guards or the I1–I6 improvement criteria. P0H4 stays served.**

**Architecture decision for you.**

| | P0H4 | S3 |
|---|---|---|
| Design | **Hybrid**: one LightGBM for the price condition × a closed-form hunger probability. Not an end-to-end single model. | The only **genuinely single** LightGBM (hunger inside the model) that is **reliable at Lead 1** |
| Lead 1 | 0.843 | 0.857 (Brier 0.112 vs 0.132; difference not significant) |
| Lead 2 | Brier 0.194 | Brier 0.232 (difference not significant) |
| Lead 3 | – | significantly worse |
| Maximum reliable lead | 1 | 1 |

If the thesis requires the single-model architecture, S3 satisfies it at no significant cost where the system is reliable (Lead 1), and with lower Lead-2/Lead-3 probability quality.

S3 was not selected by this protocol (it prioritised Lead 2). Adopting it would be your architecture decision, stated as such, with a new seal before its first unseen outcome.

## 9. Objective assessment

| Question | Answer |
|---|---|
| Is Lead 2 reliable? | **No.** All candidates fail R3/R5/R6. 0 of 10 onsets caught by any model. |
| Did Lead 1 regress? | No (S3 0.857, S2 0.871, P0H4 0.843; differences not significant) |
| Maximum supported lead | **1 quarter** (development evidence; unverified until SWS 2026-Q4) |

## 10. Limitations

**Data.**
- 13 independent hunger outcomes at Lead 2, 2 hunger onsets (2023-Q4, 2024-Q2) and 10 province-level onsets that share those quarters.
- No pre-2021 primary training evidence, by your decision.

**What limits Lead 2.**
- **Information limits:** 6 misses had no issue-time warning; 4 depend on an SWS reading published after the issue date.
- **Target fragility:** 6 of 11 misses are within 0.5 points of a price threshold.
- **Proxy target:** regional SWS hunger and provincial prices; it is not observed provincial food insecurity.
- **Design shift:** 2025-Q2 changes comparability; the later period has no onsets.

**What would change this.** Untouched outcomes (seals `a498b5ef` and `fcc4130d`), a provincial hunger outcome, or an earlier hunger signal published before the issue date.

## 11. Approval status

**Nothing merged, deployed or served.** P0H4 and all frozen artefacts are unchanged.
