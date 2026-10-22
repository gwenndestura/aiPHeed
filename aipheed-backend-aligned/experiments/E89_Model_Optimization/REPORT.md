# E89 — targeted model optimization for Lead 1 and Lead 2 (report)

**Branch.** `e89-model-optimization`.

**Evidence.**
- Protocol: `PROTOCOL.md`, frozen at 2947311 before scoring.
- Run: `runs/20261022T033435Z/` (`metrics.json`, `predictions_k1.csv`, `predictions_k2.csv`).
- Rows: the same 65 walk-forward forecasts per lead (13 target quarters 2023-Q1..2026-Q3, 16 HIGH, target T43).
- Rules: the E83 PASS rule and the pre-set quarter-level generalization criteria.

## 1. What was diagnosed

E89 started from the error lists of the current best models (`PROTOCOL.md` §1).

**Lead 2 (S-COMP), 18 errors:**

| Errors | Cause |
|---|---|
| 5 | Unissued 2023-Q1 rows. The hunger random walk required 5 posted SWS quarters, and only 4 existed. |
| 7 | The 2023-Q4 and 2024-Q2 hunger onsets |
| 6 | Price-side errors |

**Lead 1 (S-SIM), 10 errors:**

| Errors | Cause |
|---|---|
| 3 | The 2023-Q4 hunger onset |
| 7 | Price-side errors, including three Quezon false HIGHs |

## 2. What was tried (pre-registered)

| Arm | Hypothesis | New information |
|---|---|---|
| COV | Issue every forecast: the hunger random walk needs only 3 posted SWS quarters | none (coverage) |
| PCAL | Remove province bias in the price part. Logistic calibration per origin, trained on the provincial food-price condition, which is labelled every quarter from CPI alone. | about 4× more training labels than T43 |
| PCAL-GB | The same, with constrained LightGBM boosted from the structural price probability | as PCAL |

## 3. Results

**Lead 2** (65 rows; unissued rows count as wrong):

| Model | Correct | Accuracy | Balanced | TP / FP / FN / TN | Recall (HIGH) | Precision | Brier | Quarters vs persistence (W/L/T) | 95% CI (quarter block) |
|---|---|---|---|---|---|---|---|---|---|
| **S-COV (new)** | **52** | **0.800** | 0.636 | 5 / 2 / 11 / 47 | 0.31 | 0.71 | **0.177** | **5 / 1 / 7** | [0.662, 0.923] |
| S-COMP (E84) | 47 | 0.723 | 0.585 | 5 / 7 / 11 / 42 | 0.31 | 0.42 | 0.250 | 5 / 2 / 6 | [0.538, 0.877] |
| S-SIM (E83) | 45 | 0.692 | 0.522 | 3 / 7 / 13 / 42 | 0.19 | 0.30 | 0.276 | 5 / 3 / 5 | [0.508, 0.846] |
| PCAL-GB | 48 | 0.738 | 0.595 | — | 0.31 | 0.45 | 0.198 | 5 / 2 / 6 | — |
| PCAL | 45 | 0.692 | 0.564 | — | 0.31 | 0.36 | 0.212 | 4 / 1 / 8 | — |
| Persistence | 42 | 0.646 | 0.555 | — | 0.38 | 0.32 | 0.354 | — | — |
| Climatology / always-LOW | 49 | 0.754 | 0.500 | 0 / 0 / 16 / 49 | 0.00 | — | 0.219 / 0.246 | — | — |

Note on S-COMP's false HIGHs: under the pre-registered rule, an unissued row is scored as a wrong forecast. Five of
S-COMP's seven false HIGHs are the unissued LOW rows of 2023-Q1, which is why S-COV removes them.

**Lead 1** (65 rows):

| Model | Correct | Accuracy | Balanced | TP / FP / FN / TN | Recall (HIGH) | Brier | Quarters vs persistence (W/L/T) | 95% CI |
|---|---|---|---|---|---|---|---|---|
| HYB-GBA-SIM (E83 post-hoc) | 57 | 0.877 | 0.834 | 12 / 4 / 4 / 45 | 0.75 | 0.101 | 4 / 1 / 8 | [0.769, 0.969] |
| **S-SIM (E83, pre-registered)** | 55 | 0.846 | 0.751 | 9 / 3 / 7 / 46 | 0.56 | 0.118 | 4 / 3 / 6 | [0.738, 0.938] |
| S-COV = S-COMP (no unissued Lead-1 rows) | 53 | 0.815 | 0.709 | 8 / 4 / 8 / 45 | 0.50 | 0.141 | 4 / 3 / 6 | [0.677, 0.938] |
| PCAL | 50 | 0.769 | 0.658 | — | 0.44 | 0.148 | 4 / 4 / 5 | — |
| PCAL-GB | 49 | 0.754 | 0.626 | — | 0.38 | 0.157 | 4 / 4 / 5 | — |
| Persistence | 47 | 0.723 | 0.627 | — | 0.44 | 0.277 | — | — |

**Price-condition scorecard** (the price part alone, 65 rows):

| Lead | S-COMP raw | PCAL | PCAL-GB |
|---|---|---|---|
| 1 | 0.815 | 0.769 | 0.754 |
| 2 | 0.738 | 0.646 | 0.677 |

Calibration made the price part worse at both leads.

## 4. Decisions

1. **COV is adopted as the Lead-2 model.** It meets the promotion rule against S-COMP: no quarter is worse (1 better,
   12 equal) and Brier improves from 0.250 to 0.177. Its forecasts for the sealed quarters are identical to S-COMP's
   (origin 2026-Q3 had full hunger history), so the existing seal ad402660 already covers it.
2. **PCAL and PCAL-GB are rejected.** The Quezon false HIGHs were not a stable province bias that could be learned.
3. **Lead 1 keeps S-SIM** (pre-registered, 0.846). The hybrid (0.877) remains the best exploratory candidate, awaiting
   the sealed 2026-Q4 outcome.

## 5. Honest assessment against the 75% target

**Lead 2.** S-COV reaches **80.0% accuracy (52/65)**, above 75%. But:
- **Most of the gain comes from easy rows.** It is the 5 previously unissued 2023-Q1 rows, which were all LOW.
  Always-LOW scores 75.4% on the same rows.
- **It misses most HIGH risks.** It catches only 5 of 16 HIGH rows (recall 0.31), and 1 of 11 in 2023–24 (the hunger
  onsets).
- **Its edge over climatology isn't established.** The Brier gain is not significant (Holm p = 0.23), so it fails the
  pre-registered PASS rule.
- **Generalization verdict: Partially generalized.**
  - Pass: correct majority in 12 of 13 quarters; early 0.75 and late 0.88.
  - Fail: not significantly better than persistence (5–1, sign test p = 0.11); recall below 0.5.

**Lead 1.** 84.6% (S-SIM), partially generalized as shown in the Lead-1 generalization report. It is not significantly
better than persistence quarter by quarter.

**Conclusion.** The accuracy figures now exceed 75% at both leads, but this is **not a demonstrated 75% food-insecurity
early warning at Lead 2**. The model still misses most deteriorations, because the regional hunger onsets (2023-Q4,
2024-Q2) are not foreseeable from any available input. That is the binding constraint shown in E84 and E87.

**What evidence is still missing:**
1. A hunger or food-insecurity signal that precedes the SWS reading by about a quarter, for example SWS CALABARZON
   microdata or monthly monitoring (E87 request C).
2. Unseen quarters: the sealed 2026-Q4..2027-Q2 forecasts.
3. A provincial outcome (CBMS 2024 or FNRI provincial FIES; E87 requests A–B).
