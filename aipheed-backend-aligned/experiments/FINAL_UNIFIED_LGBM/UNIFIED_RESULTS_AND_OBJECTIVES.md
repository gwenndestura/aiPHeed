# Final unified LightGBM: methodology, results, objectives and acceptance

**Branch:** `aiPHeed/unified-lgbm-objectives`, from `aiPHeed/firi-data-audit` `f8efaf9`. Not merged; not deployed.

**Pre-registration.**
- Protocol `PROTOCOL_UNIFIED_LGBM.md`: sha `889e55e8…`, frozen 2026-10-26 before any unified model was scored.
- Leakage audit passed at 6 origins.
- Post-hoc arms: `ADDENDUM_1_IMPROVEMENT_ARMS.md`, sha `f07360e4…`, written after the frozen run and before the arms were scored.

**Evidence status.** Every quarter 2023–2026 was already examined by earlier experiments. All results are development evidence. The frozen run separates model *selection* (targets ≤ 2024-Q4) from *evaluation*, but no unseen outcome exists before SWS 2026-Q4.

## 1. What the system forecasts (target)

| Item | Definition | Status |
|---|---|---|
| **Forecast class (T43c)** | A province is HIGH in quarter q when SWS Balance Luzon hunger(q) > 11.3% **and** the province's food inflation, or food minus headline inflation, is above its 2021–22 60th percentile. This is the risk definition of Chapter I §1.4/§1.7 (SWS hunger + PSA food prices). | **A combined proxy.** The hunger condition is a direct food-insecurity measurement, but it is regional (Balance Luzon), not provincial. The price condition is a proxy. Provinces differ only through food prices. |
| Direct food-insecurity component | The hunger condition, one observation per quarter, reported separately | Lead 1: 12 of 14 quarters correct, the same as the latest-reading persistence |
| What is **not** forecast | Provincial or municipal food-insecurity *rates* | No provincial or LGU outcome exists 2021–2026; none was manufactured |

## 2. Methodology (final, as served)

**UNI-FINAL:**

P(HIGH) = π_H × π_P

| Term | Definition |
|---|---|
| **π_H** | P(BL hunger(target) > 11.3) from the latest published SWS reading and its past forecast error (no learning; the frozen CH1 term) |
| **π_P** | **One LightGBM**, refitted at each issue date on the stacked rows of **every lead** (1–15) |

**Features of π_P:**
- all **12 FIRI v2 families** (16 columns);
- the **lead**;
- 5 **World Bank Pink Sheet** world-price columns: Thai rice YoY and 3-month change (A3), cereal YoY (A1), crude oil YoY (A2), urea YoY (C3);
- **monotone constraints:** higher projected food inflation can only raise π_P.

**Training of π_P:**
- inner chronological validation over the last 4 training origins (depth 1–2, 50/150 trees, class weight none/balanced, min child 15);
- only data published before the issue date.

**Decision rule:** HIGH at 0.50.

**Development selection (frozen).**
- **Price variant:** U2 (world prices + monotone) had the lowest development Brier: 0.2289, vs 0.2313 for U0 and 0.2329 for U1.
- **Hunger term:** the four-area hunger LightGBM (HG) was **rejected**. Its development Brier was 0.413, vs 0.259 for π_H.

**What changed from the previous served model (CH1-LGBM).**
- Four separate per-lead models were replaced by one model across all leads, as your directive requires.
- World prices were added.
- Monotone price terms were added.

## 3. Verified metrics by horizon (frozen UNI-FINAL; R1–R7 rule of FINAL_THESIS_OBJECTIVES §7)

**R1–R7 in brief:**

| Rule | Requirement |
|---|---|
| R1 | ≥ 10 quarters and ≥ 40 rows |
| R2 | Accuracy ≥ 0.75 |
| R3 | Balanced accuracy ≥ 0.70 |
| R4 | Beats always-LOW and persistence |
| R5 | Brier below persistence and climatology (one-sided p < .10) |
| R6 | Precision and recall ≥ 0.60 |
| R7 | Stable across thirds and leave-one-quarter-out |

| Lead | Rows (quarters) | Accuracy | Balanced | Precision / Recall | Brier | AUC | Always-LOW | Persistence | Failed | Reliable |
|---|---|---|---|---|---|---|---|---|---|---|
| **1** | 70 (14) | **0.829** | 0.767 | 0.65 / 0.65 | 0.131 | 0.88 | 0.757 | 0.743 | – | **yes** |
| 2 | 65 (13) | 0.769 | 0.635 | 0.60 / 0.35 | 0.206 | 0.59 | 0.738 | 0.677 | R3 R5 R6 | no |
| 3 | 60 (12) | 0.750 | 0.648 | 0.58 / 0.41 | 0.183 | 0.72 | 0.717 | 0.567 | R3 R6 | no |
| 4 | 55 (11) | 0.655 | – | – | – | – | 0.691 | 0.545 | R2–R7 | no |
| 5 | 50 (10) | 0.700 | – | – | – | – | 0.720 | 0.500 | R2–R7 | no |
| 6–10 | 45 → 30 (9 → 6) | 0.63–0.73 | – | – | – | – | 0.69–0.80 | – | all incl. R1 | no |
| 11–15 | 25 → 5 (5 → 1) | 0.88–1.00 (= always-LOW) | – | – | – | – | 0.88–1.00 | – | R1 and others | no |

**Horizons:**

| Horizon | Value | Why |
|---|---|---|
| Generated | **15 quarters** | Longest lead with any labelled target |
| Testable | **5 quarters** | Longest lead meeting R1. Pooling made Leads 4–5 testable; per lead, only Lead 3 was. |
| **Maximum reliable lead** | **1 quarter** | The quarter starting on the issue date, 1–2 quarters after the newest published SWS survey |

**The 75% target:** **met at Lead 1** (0.829, 90% CI 0.74–0.91) under every frozen criterion. Leads 2 and 3 also reach 0.769 and 0.750 accuracy, but fail balanced accuracy and HIGH recall, so 75% accuracy alone is not a reliable result there.

**Comparison with the per-lead CH1-LGBM** (same rows):

| Lead | UNI-FINAL | CH1-LGBM | Brier test |
|---|---|---|---|
| 1 | 0.829 | 0.914 | CH1 significantly better, p = .022 |
| 2 | **0.750** | 0.583 | UNI significantly better, p = .021 |
| 3 | **0.760** | 0.520 | UNI significantly better, p < .001 |

The unified model trades some Lead-1 sharpness for much better longer-lead behaviour. Neither is reliable beyond Lead 1.

## 4. Generalization (Lead 1 unless stated)

| Check | Result |
|---|---|
| Thirds of the test period | 0.88 / 0.76 / 0.85 |
| Leave-one-quarter-out | min 0.815, max 0.862 |
| Confirmation block 2025-Q2..2026-Q3 (after the respondent-base change) | 0.833 (always-LOW 0.80, persistence 0.73) |
| Rising-hunger quarters | 0.78 (always-LOW 0.72) |
| Falling-hunger quarters | 0.95 (always-LOW 0.85) |
| Rising-hunger quarters at Leads 2 and 3 | 0.725 and 0.73: no better than always-LOW at Lead 2 |
| HIGH onsets (LOW → HIGH) | 4 of 10 caught at Lead 1; 0 of 10 at Lead 2 |
| Hunger condition alone | 12/14 quarters, the same as latest-reading persistence |

## 5. Improvement attempts (post-hoc, Addendum 1)

| Arm | Change | Development result | Outcome |
|---|---|---|---|
| U4 | More capacity for lead interactions (depth 2–3) | Brier 0.235 vs 0.229 | **Rejected** |
| U3 | In-fold decision cutoff τ (chosen at 0.20–0.50 per origin) | Balanced accuracy 0.575 vs 0.563; accuracy 0.682 vs 0.676 | **Selected** |

**U3 on all quarters (post-hoc):**

| Lead | Accuracy | Balanced | Recall | Reliable |
|---|---|---|---|---|
| 1 | 0.843 | 0.796 | 0.71 | yes |
| 2 | 0.754 | — | — | no |
| 3 | 0.683 | — | — | no |

The maximum reliable lead is unchanged at 1.

**Why U3 is not served.** Its cutoff varies by issue date, while the approved dashboard calls HIGH at 0.50 (colours, legend, glossary, the "0.50 or more" text). Re-scaling the probabilities to fake a 0.50 cutoff would misstate them. This departs from the addendum's serve line and is disclosed.

**Why no further arms were tried.** At Lead 2 the model's AUC is 0.59. No cutoff can then reach balanced accuracy 0.70; discrimination itself is the limit. Earlier experiments E41–E113 also tried CPI, rice, climate, employment, news and lags against the same problem.

## 5b. Attempt to make Lead 2 reliable (Addendum 2, post-hoc; sha `7716c9fb…`)

**Diagnosis before the attempt.** Two causes block Lead 2:

1. **The hunger term.** In 2023-Q4 and 2024-Q2 the price model flagged pressure (mean π_P 0.77 for 2024-Q2). But π_H was 0.26–0.29, because the newest SWS reading at issue was 10.3% and the 2024 surge had not started. This loses 7 of 17 HIGH rows. It is not forecastable from 2021+ hunger history.
2. **The price term.** Even with the hunger condition known exactly (a diagnostic oracle), Lead 2 would reach only accuracy 0.677, balanced accuracy 0.648 and precision 0.42.

**The arm (U6).** The food-price projection follows each province's past calendar-month pattern instead of holding the latest CPI flat.

| | U6 | UNI-FINAL |
|---|---|---|
| Development Brier | 0.236 | 0.229 |
| Price AUC, Leads 1 / 2 / 3 | 0.59 / 0.61 / 0.48 | 0.67 / 0.67 / 0.62 |
| Lead 1 | 0.757, fails | 0.829 |
| Lead 2 | 0.692, fails | 0.769 |

**Result.** The arm was **not adopted** by the pre-set rule.

**Conclusion.** Lead 2 cannot be made reliable honestly with 2021–2026 data. It needs both:
- a forecast of the hunger-surge onset, which earlier data did not contain;
- sharper two-quarter provincial price forecasts.

No further arms were run; more tries on the same quarters would only fish for a chance pass. Lead 2 stays **experimental** on the dashboard. Its sealed forecasts will be scored as SWS publishes 2027-Q1.

## 6. News contribution

| Test | Result |
|---|---|
| UNI-FINAL vs the same model without news, Lead 1 | Brier −0.012 (raw two-sided p = .026; **Holm p = .36**). Accuracy 0.829 with news vs 0.786 without. |
| Leads 2–3 | No gain (Holm p = 1) |
| Shuffled-news placebo (post-hoc, 20 refits, Lead 1; `out/news_placebo.json`) | Real-news Brier 0.131 vs placebo mean 0.139. One of 20 shuffles was at least as good: permutation p = .095. |
| Conclusion | **Suggestive at Lead 1, not demonstrated.** The ablation (raw p = .026) and the placebo (p = .095) point the same way, but the gain does not survive Holm correction across leads, the placebo is post-hoc with only 20 refits, and there is no gain at Leads 2–3. The NLP pipeline runs and supplies dated features; its predictive value remains unproven. |

## 7. Indicator families (SHAP share of π_P at Lead 1)

All 12 FIRI v2 families are in the model:

| Family | Share |
|---|---|
| A1 food-price projection | 0.48 |
| V1 vulnerability | 0.13 |
| A3 rice | 0.13 |
| E1 unemployment | 0.09 |
| lead | 0.06 |
| N1 news | 0.05 |
| C4 fisheries | 0.04 |
| C3 production | 0.03 |
| H1 hunger outlook | 0.03 |
| A2 headline inflation | 0.01 |
| C2 typhoons | ≈ 0 |
| C1 El Niño | 0 |
| E2 remittances | 0 |

Families with no measured effect are reported as such, not forced to matter.

## 8. LGU prioritisation

**The 142 city and municipal values are a priority ranking:** the province's risk probability re-weighted by PSA poverty (60%) and population density (40%), as Objective 3 specifies.

**They are not validated forecasts.**
- No municipal food-insecurity outcome exists 2021–2026 (CBMS 2024 LGU results are not public).
- Regional and provincial results do not validate individual municipalities.

The dashboard says so in its About dialog and on every LGU value.

## 9. Objective-by-objective status

| Objective (Chapter I) | Status | Evidence |
|---|---|---|
| 1. NLP pipeline (XLM-R + BERTopic → FSSI, latent patterns) | **Partial** | Runs and feeds dated news features. Lead-1 gain is suggestive (ablation raw p = .026, Holm p = .36; shuffled-news placebo p = .095), not demonstrated. No gain at Leads 2–3. |
| 2 I–IV. LightGBM accuracy, precision/recall, F1, AUC | **Achieved for the forecast class** | Lead 1: accuracy 0.829, balanced 0.767, P/R 0.65/0.65, AUC 0.88. Reported for every lead. |
| 2 V. Furthest reliable horizon by walk-forward | **Achieved (answered)** | Generated 15, testable 5, **reliable 1 quarter**, from one unified LightGBM |
| 3. LGU rankings from validated province forecasts | **Partial** | Rankings produced from the reliable Lead-1 province forecast. The ranking itself has no municipal outcome to validate against. |
| 4. Comparison with baselines | **Achieved** | Lead 1 beats always-LOW (0.757) and persistence (0.743), and its Brier beats persistence and climatology. The per-lead CH1 comparison is reported. |
| 5. Dashboard, ISO 25010, DA evaluation | **Partial** | Dashboard serves the unified model and shows generated / testable / reliable horizons separately. The DA user evaluation is still to be run; the E114 evaluation package is ready. |

## 10. Acceptance checklist

| Item | Evidence |
|---|---|
| Target measures future food insecurity, or the unsupported claim is named | §1: a combined proxy. The hunger part is direct but regional. Provincial and LGU rates are not forecast. |
| Required LightGBM includes all 12 families | §2, §7 |
| Training data corrected, aligned, leakage-free | Audited inputs (FIRI_V2_DATA_AUDIT). Leakage audit passed (`out/leakage_audit.json`). Issue-date cuts for SWS, CPI, news and Pink Sheet. |
| Substantive improvement attempts | Unified pooling + world prices + monotone terms (frozen); capacity and cutoff arms (Addendum 1); HG hunger model (rejected) |
| 75% evaluated honestly | Met at Lead 1 only. Not claimed at Leads 2–3 despite accuracy ≥ 0.75 there. |
| Maximum reliable lead from the longest testable horizons | Leads 1–15 scored; R1 reachable to 5; reliable 1 |
| Generalization across quarters and difficult periods | §4 |
| News tested honestly | §6 |
| LGU level of validation stated | §8 |
| Dashboard, methodology and results agree | `backend/data/ch1_engine/` exported by `runner/export_uni.py` (stops if any served Lead-1 probability differs from the evaluated one). About dialog checked in the running app. |
| Tests pass; reproducible; branch pushed | Backend 834 passed / 18 skipped; frontend 75 passed; build OK. Seal `fcc4130d` (issue 2026-10-01, Leads 1–15). |
| Nothing merged or deployed | Yes |

## 11. Remaining gaps

1. **No unseen confirmation.** Score the seal from SWS 2026-Q4, published about January 2027.
2. **Lead 2+ is limited by discrimination of future provincial food inflation** (AUC 0.59–0.72), not by the threshold or model capacity.
3. **No provincial or municipal food-insecurity outcome.** CBMS 2024 LGU tables and FNRI provincial FIES are needed to validate Objective 3.
4. **The DA IV-A user evaluation (Objective 5)** remains to be conducted.

## Reproduction

Run from `aipheed-backend-aligned/experiments/FINAL_UNIFIED_LGBM/runner`, with `/c/Users/admin/aipheed/backend/venv/Scripts/python.exe`:

```bash
python run_uni.py audit
```

```bash
python run_uni.py score
```

```bash
python improve.py score
```

```bash
python improve.py placebo
```

```bash
python export_uni.py
```
