# Final target and evaluation protocol (Chapter I province-quarter risk)

**Branch:** `aiPHeed/final-thesis-objectives`, from `74af1a4` (final-system-completion).

**Freezing:** this file's SHA-256 goes in `runner/PROTOCOL_SHA256.txt` before any model below is scored. Changes go in numbered addenda only.

## 0. Requirement basis (exact wording)

Thesis source: `THESIS 2 (11).pdf`, 13 Oct 2026; extract in `sources/chapter1_THESIS2_11_extract.txt`.

| Section | Exact text |
|---|---|
| §1.4 | "The dependent variable is the binary food insecurity risk classification, either high or low, of a CALABARZON province in a given quarter." |
| §1.7 | "SWS quarterly hunger data and PSA food price data will be used to determine food insecurity risk … City and municipal estimates will be derived from province-level forecasts using PSA Small Area Estimates and population data; therefore, these estimates will not represent official food insecurity classifications." |
| §1.5.2 Obj. 2 | Accuracy, precision/recall, F1 and AUC of "high- and low-risk province-level classifications"; "the furthest horizon at which reliable forecasting is achievable". |

## 1. Disclosure: what was known before freezing

- **T43.** The label below was defined and frozen in E40/E43 (2026-10-15).
  - Its thresholds were chosen by the researcher from a P60–P85 grid, using label-prevalence gates only.
  - E43–E108 scored it on 2021–2026. E108's factored LightGBM reached 0.892 at Lead 1 on 65 rows; Leads 2–4 were below climatology.
  - These results were seen before this protocol was written.
- **Why T43 now.** The choice follows Chapter I's wording above, not those scores:
  - the dependent variable is a province-quarter high/low class;
  - it is determined from SWS hunger *and* PSA food prices.
- **FINAL / FINAL_OBJECTIVE_ACHIEVEMENT's ELEVATED label does not meet this definition.** It is regional, uses SWS only, and is a researcher-defined "above past-year average". It is therefore not the thesis target.
- **Evidence status.** All 2021–2026 quarters are development evidence, except the rows created by the outcome correction in §2. The 2025-Q2 and 2025-Q3 province-quarters were never scored as T43 labels before.

## 2. Target (frozen): T43c, the Chapter I risk class on the corrected SWS series

**Definition.** HIGH(p, q) = **[H_BL(q) > 11.3]** AND **[F_p(q) > P60food_p OR F_p(q) − HL_p(q) > P60gap_p]**

**Hunger term H_BL(q)**
- The mean Balance Luzon involuntary hunger of quarter q's **non-commissioned** SWS rounds.
- Source: `../FINAL_FOOD_INSECURITY_LIGHTGBM/data/sws_area_rounds_2021.csv` (verified against SWS).

**Price terms F_p(q) and HL_p(q)**
- The quarter means of the three PSA-published monthly food and all-items YoY rates of province p.

**Thresholds** (from `../E40_SWS_CPI_Tiers/label_spec.json`, frozen 2026-10-15, 2021–22 window, never recomputed)
- Hunger: 11.3.
- Province food and gap P60 values.

**Correction** (the only change from T43)
- The E40–E108 series (`backend/data/inputs/sws_rounds.csv`, `definition_A`) included the commissioned Stratbase voter round (2025-Q1, 24.0) and dropped the regular 2025-Q2 and 2025-Q3 rounds.
- T43c uses the verified non-commissioned series. 2025-Q1 therefore has no label, and 2025-Q2 and 2025-Q3 get labels.

**No label** when the quarter has no non-commissioned round or its CPI quarter is incomplete.

**Not an official classification.** A HIGH label means "regional hunger above 11.3% and unusual food-price pressure in the province". It is not a measured provincial prevalence (§1.7).

## 3. Time convention (one rule for the thesis)

**Issue date:** O(t) = 00:00 on the first day of quarter t+1.

**What is used at O(t)**
- SWS rounds published before O(t).
- CPI months up to month 2 of quarter t (PSA releases month m about day 5 of month m+1).
- News published before O(t).
- The E107 family cut-offs.

**Leads**

| Lead | Target | Meaning |
|---|---|---|
| 0 | Quarter t | A nowcast of the quarter that has just ended, whose SWS and complete CPI are not yet published. Reported, but not a forecast horizon. |
| 1 | t+1 | The quarter that starts on the issue date (ends 3 months later) |
| 2 | t+2 | Ends 6 months after issue |
| 3 | t+3 | Ends 9 months after issue |
| 4 | t+4 | Ends 12 months after issue |

**Recorded per row:** the issue date; the newest SWS quarter known, with its publication date; the newest CPI month; the newest news date; the target quarter; days from issue to the target-quarter end; the true SWS horizon.

## 4. The primary model: CH1-LGBM

**Formula:** P(HIGH) = π_H × π_P. The class is HIGH when P ≥ 0.5.

This mirrors §1.7: risk requires both the hunger condition and the price condition.

**π_H (hunger condition)** = Φ((h_last − 11.3)/σ_h)
- h_last: the newest Balance Luzon reading published before O(t).
- σ_h: the RMSE of earlier latest-reading errors at the same true horizon, from pairs whose target was published before O(t). At least 4 pairs are needed; otherwise 4.0.
- π_H is the corrected H1 family column.

**π_P (price condition)** is one LightGBM classifier trained on the province price condition of quarters complete before O(t).
- It uses E108's `Price` model with spec F1: min_child_samples 15, depth {1,2} × trees {50,150} × class_weight {None, balanced}, chosen by inner chronological log-loss on the last 4 training quarters, seed 108.
- Training starts once there are at least 6 labelled quarters with at least 5 HIGH and 5 LOW price labels.

**Columns: all 12 families**
- E107's 13 columns, with H1 replaced by the corrected π_H.
- Plus `A_mom` (family A1): the province food CPI 3-month log change in the newest three published months, × 100.
- Plus `G_pri_yoy` (family N1): GDELT GKG price-news share YoY of quarter t, from E113 `news_composites_G.csv`, used only if its last document is before O(t).
- Plus `NG_gap_price` (family N1): the FINAL gap-aligned GDELT price-news indicator.

**Why these three additions** (each pre-specified, none tuned)
- `A_mom` adds price momentum to the base-effect projection.
- The two news columns test E113's validated finding that price news leads food-inflation change by about two quarters.

## 5. Comparators (same rows, same information)

### 5.1 No-skill references

| ID | Definition |
|---|---|
| PERSIST-SI | **Same-information persistence.** π_H(h_last > 11.3) AND the price condition evaluated on the newest three published CPI months; a 0/1 call. E108's persistence used the last *complete* label, which is older than the information at O(t). |
| CLIM | Training base rate of T43c |
| ALWAYS-LOW | The majority class |

### 5.2 Chapter I baselines (Objective 4 / RQ3)

Each is trained on the price condition and multiplied by π_H, so all comparators share the definition.

| # | Baseline |
|---|---|
| 1 | Naive persistence (PERSIST-SI) |
| 2 | Logistic regression on all columns (LR-COMB) |
| 3 | Logistic regression on government indicators only (LR-GOV) |
| 4 | Logistic regression on news only (LR-NLP: N1, G_pri_yoy, NG_gap_price) |
| 5 | LightGBM on government indicators only (LGBM-GOV = CH1-LGBM without news) |
| 6 | LightGBM on news only (LGBM-NLP) |

### 5.3 Reference rule

**STRUCT:** E108's no-learning CPI base-effect projection × π_H.

### 5.4 Diagnostic ablation

**CH1-DIRECT:** one LightGBM trained directly on T43c with the same columns. It shows why the factored structure is used.

## 6. Metrics

**Per lead**
- accuracy, with a 90% cluster-bootstrap CI over target quarters (2,000 draws, seed 2026);
- balanced accuracy, precision, recall, F1;
- AUC, Brier;
- confusion matrix;
- HIGH share and majority-class accuracy.

**Leave-one-quarter-out:** minimum and maximum accuracy.

**Accuracy by third of the target quarters.**

**Onset recall:** province-quarters that are HIGH after a LOW quarter.

## 7. Reliability rule (frozen; the same at every lead from 1 to 4)

Objective 2 V asks when forecasting is *reliable*, so the rule tests forecast quality against no-skill references. Superiority over the Chapter I baselines is Objective 4 / H3 and is tested separately (§8).

| # | Criterion |
|---|---|
| R1 | At least 10 target quarters and at least 40 rows |
| R2 | **Accuracy ≥ 0.75** |
| R3 | Balanced accuracy ≥ 0.70 |
| R4 | Accuracy > ALWAYS-LOW accuracy and > PERSIST-SI accuracy |
| R5 | Brier(CH1) < Brier(PERSIST-SI) and < Brier(CLIM), each with a one-sided paired cluster-bootstrap p < 0.10 |
| R6 | Precision ≥ 0.60 and recall ≥ 0.60 for HIGH |
| R7 | Accuracy ≥ 0.60 in each third of the target quarters, and leave-one-quarter-out minimum accuracy ≥ 0.70 |

**Maximum reliable lead:** the largest K such that Leads 1 … K all pass. If Lead 1 fails, none.

**Lead 0** is reported with the same rule, but it is a nowcast and does not count as a forecast horizon.

**Also reported:** the verdict under a stricter variant that adds "balanced accuracy above every Chapter I baseline and STRUCT", so readers can see both.

## 8. Objective 4 / H3: does CH1-LGBM outperform the six comparators?

For each comparator:
- paired cluster-bootstrap Brier difference (one-sided p);
- McNemar on correct and incorrect calls.

**Holm correction** across the six comparators at each lead.

**H3 rejected** at a lead only if CH1-LGBM is significantly better (Holm p < 0.05) than **all six**.

## 9. News (Objective 1 predictive value)

| Comparison | Test |
|---|---|
| CH1-LGBM vs LGBM-GOV (no news), same rows | Brier difference (two-sided cluster bootstrap) and McNemar at Leads 0–4, with Holm across leads |
| Pre-specified direction | News improves Leads 2–3 (E113) |
| Placebo | 100 refits with the news columns permuted across quarters, at Leads 1 and 2 |

## 10. Regional hunger outcome (direct hunger evidence, unchanged)

The FIL-OA regional SWS hunger forecasts and their evaluation (FINAL_OBJECTIVE_ACHIEVEMENT, protocol `d94f0c2c`) are reported alongside, not re-run. They answer whether *hunger itself* can be forecast; this protocol answers the Chapter I *risk classification*.

## 11. Leakage audit and seal

**Leakage audit (must pass before scoring).** At 10 origins, CH1-LGBM forecasts must be identical after each perturbation:
- future SWS rounds randomised;
- future CPI months randomised;
- future GDELT documents' flags shuffled.

A negative control (perturbing past SWS rounds) must change them.

**Seal.** CH1-LGBM, STRUCT and PERSIST-SI forecasts at O(2026-Q3) = 2026-10-01 for Leads 1–4 (targets 2026-Q4 … 2027-Q3). Output: `out/sealed_prospective.csv` + SHA-256.
