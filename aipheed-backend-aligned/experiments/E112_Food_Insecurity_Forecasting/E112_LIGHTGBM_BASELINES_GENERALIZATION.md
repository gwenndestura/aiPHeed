# E112 The 12-indicator LightGBM: results, baseline comparison and generalization

**Sources:** `out/results.json`, `out/objective4_baselines.json`, `out/bl_lead{1..4}.csv`, `out/panel_lead{1..4}.csv`.

**Basis.**
- Outcome: SWS Total Hunger, Balance Luzon, primary rule, walk-forward.
- Issue dates: 2024-Q1..2026-Q2 at Lead 1.
- Evidence status: development only; every quarter was seen in E109–E111.
- Tests: frozen protocol and Addendum 1.

## 1. The required model

**LGBM12** is E109's LightGBM, reproduced exactly (test `test_lgbm12_reproduces_e109…`):
- the 12 FIRI families as 13 columns, regional means;
- it predicts the change from the latest published reading;
- depth 1, 2 leaves, min_child 3, lr 0.05, L2 5, trees {25, 75} chosen on the last four training targets, seed 109.

**LGBM12N** is the same model with the six news YoY indicators added (19 columns).

## 2. Accuracy against all baselines (MAE in hunger points; lower is better)

| Method | Role (Chapter I Obj. 4) | Lead 1 (9 q) | Lead 2 (7 q) | Lead 3 (6 q) | Lead 4 (5 q) |
|---|---|---|---|---|---|
| **RW** latest reading | naive persistence | **3.72** | 4.77 | 4.08 | **3.25** |
| MA2 mean of last two | simple | 4.46 | **3.92** | **3.26** | 3.18 |
| MEAN | climatology | 6.98 | 7.26 | 6.56 | 7.53 |
| SEAS | same quarter last year | 5.29 | 5.19 | 4.08 | 3.25 |
| LL local level | smoothing | 4.53 | 4.73 | 3.72 | 3.86 |
| PSA-R | **PSA-only** (Addendum 1) | 3.73 | 8.03 | 4.75 | 7.55 |
| RIDGE13 | **linear regression** (Addendum 1) | 4.49 | 7.45 | 3.87 | 8.53 |
| NEWS-C | **NLP-only** (corpus) | 3.52 | 4.86 | 4.55 | 5.69 |
| NEWS-G | NLP-only (GDELT) | 3.94 | 5.75 | 5.05 | 4.12 |
| **LGBM12** | proposed | 4.04 | 5.62 | 4.49 | 4.04 |
| **LGBM12N** | proposed + news | 4.05 | 5.67 | 4.79 | 4.08 |

The ±4-point BL margin is the accuracy bound (P2).

**Comparison tests** (one-sided Newey–West DM, Holm over the 4 leads):

| Comparison | Lead 1 | Lead 2 | Lead 3 | Lead 4 | Holm |
|---|---|---|---|---|---|
| LGBM12 vs RW | worse (+0.32) | worse | worse | worse | n.s. |
| LGBM12 vs PSA-R | worse (+0.31) | better (−2.41, p .21) | better (−0.26) | better (−3.51) | all ≥ .82 |
| LGBM12 vs RIDGE13 | better (−0.45, p .26) | better (−1.83) | worse (+0.62) | better (−4.49) | all ≥ .89 |
| LGBM12 vs NEWS-C | worse | worse | better | better | — |

**Reading.**
- **The proposed LightGBM does not beat persistence at any lead.** At every lead at least one simple baseline (RW or MA2) is better.
- It is more stable than the linear and PSA-only models, which blow up at Leads 2 and 4 (7–8.5 points). None of these differences is significant.

## 3. Reliability status (frozen P1–P8 rule)

| Lead | LGBM12 | LGBM12N | NEWS-C | NEWS-G | Best simple alternative |
|---|---|---|---|---|---|
| 1 | not reliable (fails P1–P5, P8) | not reliable (P1–P5) | not reliable (P1, P3, P4, P5, P8) | not reliable | MA2 / LL not reliable |
| 2–4 | insufficient evidence (< 8 quarters) | insufficient evidence | insufficient evidence | insufficient evidence | insufficient evidence |

**Final method by the frozen rule (PROTOCOL §5): RW, the latest published SWS reading.**

## 4. Generalization (Lead 1, mean per-quarter |error| difference vs RW; negative = better)

| Check | NEWS-C | LGBM12 | LGBM12N |
|---|---|---|---|
| Early third (2024) | −1.26 | −0.70 | −0.53 |
| Middle third (2025) | +0.40 | +1.00 | +1.32 |
| Late third (2026-Q1..Q3) | +0.24 | +0.65 | +0.19 |
| Rising-hunger rows | −0.07 | −0.33 | −0.07 |
| Falling-hunger rows | −0.69 | **+2.58** | **+1.72** |
| After the 2025 survey change | +0.32 | +0.83 | +0.76 |
| Last 4 quarters | +0.31 | +0.45 | +0.52 |
| Worst leave-one-quarter-out mean | +0.24 | +0.50 | +0.63 |
| ALL rule (+ commissioned rounds) | −0.43 | +0.50 | +0.35 |
| HH rule (household heads only, 3 rows) | −1.26 | −0.70 | −0.53 |
| 4-area panel (news ridge NEWS-CP) | +0.01 | — | — |

**Reading.**
- **All three gain only in 2024** (the surge year) **and lose from 2025 on**, after the respondent-base change.
- The LightGBM models are **much worse when hunger falls**: they predicted further rises after the 2024-Q4 peak.

**By true horizon (all leads pooled, MAE):**

| True horizon | Rows (quarters) | RW | LGBM12 | LGBM12N | NEWS-C |
|---|---|---|---|---|---|
| 2 | 9 (8) | 3.00 | 3.85 | 3.64 | 2.82 |
| 3 | 7 (6) | 5.50 | 5.75 | 5.91 | 4.93 |
| 4 | 6 (5) | 3.23 | 3.74 | 4.06 | 4.65 |
| 5 | 4 (4) | 3.99 | 4.76 | 4.84 | 6.14 |

## 5. Which families add value? (N3 removal tests on LGBM12N, Leads 1–2)

**No family and no news category passes** (all Holm p = 1.0).

- **Never used** at Lead 1 (removal changes nothing): V1 (static), C1, C2, E1, E2, N1 (56% missing) and H1. H1 adds nothing because the model already predicts the change from the latest reading.
- **Removals that lower the error**, i.e. the component hurt (not significant):
  - A2 (3.88 vs 4.05), C4 (3.94) and jobs news (3.80) at Lead 1;
  - E1 (5.39 vs 5.67) and C3 (5.45) at Lead 2.
- **Removals that raise the error**, i.e. the component helped (not significant): price news at Lead 1 (4.43, raw p = .19); A3 (5.83) and C1 (5.90) at Lead 2.

E111's single-family screen gave the same answer: Holm p = 1 for all 12.

## 6. Missing data

At the Lead-1 evaluation origins:
- the news indicators, A1–A3, V1, C1–C4, E1 and H1 are complete;
- E2 is missing at 11% (series ends 2025-Q4);
- N1 FSSI-v3 is missing at 56%.

LightGBM handles missing values natively; the ridge models use median fill.
