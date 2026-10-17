# E49: fair E38 vs E46 comparison and production recommendation

**Branch:** `e46-lead2-policy`, from 26ca3e0.
- **Protocol** (frozen before scoring): `PROTOCOL.md`, commit 005378b.
- **Run:** `runs/20261017T124452Z`, with a byte-identical repeat `runs/20261017T124652Z` (results differ only in the timestamp).

## Direct answers

| Question | Answer |
|---|---|
| Which model performs better under identical conditions? | **E46**, on the target where discrimination can be measured (T43), and E38 is no better than naive baselines on its own target. On the identical 35 rows (7 quarters), E46 has the best Brier of every arm and E38's procedure collapses on T43. On the thesis Equation 3 label, neither model beats always-HIGH: the label is HIGH in 33/35 rows. |
| Does either meet 75% Lead-2 with meaningful HIGH/LOW discrimination? | **No.** E46: 0.800 accuracy, but HIGH recall 0.44 and balanced 0.684. E38: 0.709 on its own label, LOW recall 2/6, balanced 0.544, below always-HIGH (0.891). |
| Are the results on genuinely unseen quarters? | **No.** Every 2022–2026 quarter was examined in E36–E48. The only unseen test is the frozen 2027-Q1..Q4 forecasts. |
| What causes the remaining weakness? | **The target and the data, not serving.** The thesis label (S1 > median) is saturated in 2024–2026 because SWS hunger rose to 14–25%: 33/35 HIGH with E38's as-of median, and 32/35 with the paper's global median, which is 14% HIGH before 2024. So it cannot show discrimination. T43 has 9 HIGH rows in 7 quarters; the gap-driven HIGHs and the 2024-Q2 hunger jump are not forecastable from as-of inputs; and the non-market triggers are national or sparse (E47). |
| Which model should be the production default? | **Neither meets the pre-registered promotion rule**, so the recommendation is **keep E38 as the default temporarily, with its limitations disclosed.** This is not a finding that E38 is better: it is not, and it is worse than always-HIGH on its own label. Promoting E46 for exploratory decision support is defensible with safeguards (section 7), but that is your decision. |
| What remains before the thesis objectives can be claimed? | (1) An outcome label that varies in the study window and is approved: the Eq. 3 label is saturated, and T43 needs adviser approval. (2) Prospective scoring of the frozen 2027-Q1..Q4 forecasts. (3) The objective 5 evaluations: the ISO/IEC 25010 survey and the FNRI NNS face-validity check. (4) Provincial outcome data (CBMS/FIES) for a non-proxy target. |

## 1. Model and target audit

| | E38 (production default) | E46 I7 (`AIPHEED_LEAD2_MODEL=e46`) |
|---|---|---|
| **Target** | Thesis Eq. 3: S1 = SWS hunger + 2 × (province food YoY − five-province mean). HIGH if S1 > τ, where τ = median S1 of labelled quarters posted before the origin (as of the origin). The thesis text uses a global median. | T43: SWS hunger > 11.3 AND (province food YoY > its 2021–2022 P60 OR food − headline > its P60) |
| **HIGH means** | provincial stress above its recent median (relative) | concurrent elevated hunger and provincial price stress (fixed thresholds) |
| **Horizon / issue** | Lead 2; origin 00:00 day 1 of t+1; target t+2 | same (cutoff audited in E47) |
| **Inputs** | COMPACT: H_margin, H_trend, D_last, Dnow, news_reg, fssi_v2. Trees split only on D_last, Dnow and H_margin (E48). | base-effect food and gap projections + ridge residuals on the five groups + news + policy; hunger ridge |
| **Trigger groups in the model** | Market (price deviation) only | all five groups (E47 audit) |
| **Missing data** | rows with missing COMB inputs dropped | median imputation + missing flags (training only) |
| **Probability / threshold** | LightGBM + prior shift; threshold 0.5 from the inner rule | p = P(hunger) × P(price signal); HIGH if p ≥ 0.5 |
| **Artifact** | `backend/data/e36/model/E38-LGBM-NQ_O2026-10-01_lead2.txt` (LF sha `ce6f7973…`) | `backend/data/e46/e46_record.json` (sha `8b4bc582…`), frozen `E46_I7_PROSPECTIVE_2027Q1.json` `5592d53e…` |
| **Original result** | 39/55 = 0.709 | 28/35 = 0.800 |

## 2. Reproductions

Both are recomputed from committed predictions and **reproduce exactly**:

| Model | Result | Other metrics |
|---|---|---|
| E38 | 39/55 = 0.709 | balanced 0.544, LOW recall 2/6 |
| E46 I7 | 0.800 | |

## 3. Identical evaluation rows

**Rows:** targets 2024-Q3, 2024-Q4, 2025-Q1, 2025-Q4, 2026-Q1, 2026-Q2, 2026-Q3. That is **7 independent quarters, 35 province rows**, the same rows for both targets. 2024-Q2 dropped out because one adapted arm had no forecast there.

**Cutoffs:**
- E38's own posting rule for its labels and τ.
- E46's audited day-1 issue rule.
- The T43 labels are used in E38→T43 only after their SWS rounds were posted.

**Adaptations, labelled as adaptations:**
- **E46→EQ3:** I7's as-of food forecasts and hunger forecast are converted into Ŝ1 and compared with E38's τ. The error scale comes from earlier origins.
- **E38→T43:** E38's code unchanged, with T43 labels.

## 4. Side-by-side results

**Target A: thesis Eq. 3 with E38's as-of τ** (33 HIGH / 35)

| Arm | Accuracy (CI) | Balanced | Rec H | Rec L | Prec | Brier | AUC | TP/TN/FP/FN | HIGH calls |
|---|---|---|---|---|---|---|---|---|---|
| E38 (original) | 0.714 (0.51–0.89) | 0.379 | 0.76 | 0.00 | 0.93 | 0.188 | 0.48 | 25/0/2/8 | 77% |
| E46→EQ3 (adapted) | 0.943 | 0.500 | 1.00 | 0.00 | 0.94 | 0.079 | 0.53 | 33/0/2/0 | 100% |
| Persistence | 0.857 | 0.455 | 0.91 | 0.00 | | 0.143 | | 30/0/2/3 | 91% |
| always-HIGH | 0.943 | 0.500 | | | | 0.057 | | 33/0/2/0 | 100% |
| always-LOW | 0.057 | 0.500 | | | | 0.943 | | | 0% |

With only 2 LOW rows, **no model can show discrimination**, and every arm is at or below always-HIGH.

**Target B: T43** (9 HIGH / 35)

| Arm | Accuracy (CI) | Balanced | Rec H | Rec L | Prec | F1 | Brier | AUC | TP/TN/FP/FN | HIGH calls |
|---|---|---|---|---|---|---|---|---|---|---|
| **E46 (original)** | **0.800** (0.66–0.94) | 0.684 | 0.44 | 0.92 | 0.67 | 0.53 | **0.174** | 0.735 | 4/24/2/5 | 17% |
| E38→T43 (adapted) | 0.371 | 0.286 | 0.11 | 0.46 | 0.07 | | 0.421 | 0.31 | 1/12/14/8 | 43% |
| Persistence | 0.543 | 0.583 | 0.67 | 0.50 | 0.32 | | 0.457 | 0.58 | 6/13/13/3 | 54% |
| always-LOW | 0.743 | 0.500 | | | | | 0.257 | | 0/26/0/9 | 0% |
| always-HIGH | 0.257 | 0.500 | | | | | 0.743 | | | 100% |

**Accuracy by quarter:**

| Target and arm | 2024-Q3 | 2024-Q4 | 2025-Q1 | 2025-Q4 | 2026-Q1 | 2026-Q2 | 2026-Q3 |
|---|---|---|---|---|---|---|---|
| T43, E46 | 1.0 | 0.6 | 0.6 | 1.0 | 1.0 | 0.6 | 0.8 |
| T43, E38→T43 | 0.8 | 0.4 | 0.2 | 0.0 | 0.0 | 0.2 | 1.0 |
| Eq. 3, E38 | 0.6 | 0.6 | 0.2 | 0.8 | 1.0 | 0.8 | 1.0 |

**Probability variation across quarters** (standard deviation of each province's probabilities, Cavite / Laguna / Quezon / Rizal / Batangas):

| Arm | Cavite | Laguna | Quezon | Rizal | Batangas |
|---|---|---|---|---|---|
| E38 (Eq. 3) | 0.37 | 0.20 | 0.35 | 0.19 | 0.18 |
| E46 (T43) | 0.17 | 0.17 | 0.26 | 0.16 | 0.15 |

E38's variation comes almost entirely from 2024; since 2025-Q4 its scores are ≥ 0.95 (E48).

## 5. Why scores differ across quarters (source to screen)

- **E38:** API = record = booster, verified in E48. Its near-constancy since 2025-Q4 is the saturated label. There is no join, cache, imputation or ordering defect.
- **E46:**
  - each past quarter is its own as-of refit, reproduced to 1e-9;
  - contributions sum to the model correction within 1.8e-15;
  - evidence respects each issue date (E47 tests).

## 6. Corrections in E49

**None needed;** no new code defect was found. Earlier defects were already fixed in E46/E47:
- the gap bias;
- the threshold refit;
- the residual intercepts;
- the observed-vs-forecast score mix.

Neither model meets the objective. The principal causes (target saturation, few HIGH quarters, national-only triggers) cannot be fixed by code: they need an approved, varying outcome and more quarters.

## 7. Recommendation

**Pre-registered rule result:** no model beats all baselines on Brier with balanced accuracy ≥ 0.70 and both recalls ≥ 0.60 → **"Neither."**

**What follows:**
- Keep the current default (E38) temporarily.
- The dashboard should keep disclosing that its score is a relative, saturated v1-label probability, not validated.

**If you choose to promote E46 for exploratory decision support,** use these safeguards:
- the "experimental, acceptance not met" label (already in the record and API);
- HIGH recall 0.44 stated: it misses more than half of past HIGH quarters;
- T43 described as an exploratory proxy pending adviser approval;
- prospective scoring each quarter, with automatic demotion if 2027 accuracy or balanced accuracy falls below E38's or the baselines';
- E38 kept behind a flag.

## 8. Tests and live system

| Suite | Result |
|---|---|
| E49 tests (`tests/test_e49.py`: protocol, T43 export, as-of persistence, adaptation changes only labels, metric arithmetic) | **4 passed** |
| Backend (`backend/venv/Scripts/python.exe -m pytest -q`, from `backend/`) | **367 passed, 18 skipped, 0 failed** |
| Frontend (`npx vitest run`) | **45 passed** |

Existing tests cover API = selected model (E46/E48), historical explanations (E47) and dynamic targeting.

**Live:** the `e46` API on 8001 and the tutorial frontend on 8082 serve the scores in section 4. The production default is unchanged.

## 9. Files and hashes

**New** (E49 folder only):
- `PROTOCOL.md`, `runner/PROTOCOL_SHA256.txt`
- `runner/e49_export_t43.py`, `runner/e49_compare.py`
- `data/t43_labels.csv`, `data/t43_persistence.csv`
- `tests/test_e49.py`
- `runs/` (2 runs), this report

**Input hashes:**
- E38 predictions `8fdfd027…`
- I7 predictions `0486e3ed…`
- E36 record `07162391…`

**Commits:** 005378b (protocol freeze) plus the report commit. Nothing is pushed.
