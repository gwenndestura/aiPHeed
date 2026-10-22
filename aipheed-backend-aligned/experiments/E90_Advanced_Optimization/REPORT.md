# E90 — advanced forecasting optimization and generalization (report)

**Branch.** `e90-advanced-optimization` (from e89-model-optimization at b9222ac). Nothing pushed; production branch
`final-system-v2` unchanged.

**Evidence.**
- Diagnostic: `runner/diagnose_onsets.py` → `onset_diagnostic.csv`, `onset_diagnostic.json`.
- Protocol: `PROTOCOL.md` + `PROTOCOL.sha256`, frozen and committed at fdf645c before scoring.
- Run: `runs/20261022T040445Z/` (`metrics.json`, `predictions_k1.csv`, `predictions_k2.csv`).
- Rows: the same 65 walk-forward forecasts per lead as E84/E89 (13 target quarters 2023-Q1..2026-Q3 × 5 provinces,
  16 HIGH, target T43). Data 2021-Q1 onward only.
- Rules: the E83 PASS rule and the pre-set quarter-level generalization criteria, unchanged.

## 1. E89 baseline (re-verified)

| Lead | Model | Accuracy | Balanced | HIGH caught | Brier | PASS |
|---|---|---|---|---|---|---|
| 1 | S-SIM (pre-registered) | 0.846 (55/65) | 0.751 | 9/16 | 0.118 | No |
| 1 | HYB-GBA-SIM (post-hoc) | 0.877 (57/65) | 0.834 | 12/16 | 0.101 | Yes (post-hoc only) |
| 2 | S-COV | 0.800 (52/65) | 0.636 | 5/16 | 0.177 | No |

All reproduced exactly from the E89 run files.

## 2. Why the 2023–24 hunger surges were missed

**Where the errors are.** At both leads the misses concentrate in two quarters: 2023-Q4 (3 HIGH) and 2024-Q2
(4 HIGH). Both are regional hunger *onsets*: SWS hunger crossed the 11.3% line from below. Every model forecasts
hunger as a random walk from the last posted reading, so it cannot forecast a crossing that the last reading does not
already show.

**Was there a signal before the target quarter?** Hunger change was compared with every driver's origin-time value
(`onset_diagnostic.json`):

| Driver feature at the origin | Lead 1 | Lead 2 |
|---|---|---|
| Rice CPI YoY | ρ = +0.79, p < 0.001 | ρ = +0.71, p = 0.003 |
| Rice 3-month momentum | — | ρ = +0.69, p = 0.003 |
| Employment, remittances, typhoons, fisheries, palay, ENSO | no significant correlation | no significant correlation |

**Onset by onset:**

| Target | Lead 2 origin | Last hunger | Rice YoY | Visible? |
|---|---|---|---|---|
| 2023-Q4 | 2023-07-01 | 8.7% | +3.8% | No. The rice spike began after this origin. |
| 2024-Q2 | 2024-01-01 | 10.3% | +10.5% (world rice +29% in 6 months) | Yes, in the inputs |

**Delayed effect, asymmetric.** Rice inflation leads hunger by about one to two quarters. The relationship holds for
rises only: in 2025–26 rice prices *fell* (−13.7% YoY) while hunger stayed at 20–24%. A linear driver model (E87
HUN-MKT) therefore failed, because the deflation years cancel the onset years.

**Modeling problem or data problem?**

| Cause | Kind | Evidence |
|---|---|---|
| 2023-Q4 onset | Data | No input showed it at the Lead-2 origin. Unforeseeable with the available sources. |
| 2024-Q2 onset | Learning delay | The signal was in the inputs, but a walk-forward model has no earlier surge to learn from. The fitted rice coefficient stays at 0 until 2024-Q3 at Lead 2 (`beta_by_origin`). A surge must happen once before the model can respond to the next one. Pre-2021 surges are outside the study window. |
| Aggregation | Data | The hunger reading is Balance Luzon, one number for all five provinces. Every province gets the same hunger forecast, so a provincial onset can't be separated from a regional one. |
| Proxy target | Target | Since 2023-Q4 hunger stayed above the line in 10/10 quarters, so T43 has been decided by the price condition alone. That condition moves *against* hunger (r = −0.61). |
| Label reproduction | Not a cause | T43 labels reproduce exactly from E40 thresholds. |

## 3. What was tried (pre-registered, `PROTOCOL.md`)

| Arm | Idea |
|---|---|
| **HUN-RICE** | Hunger forecast = last reading + a + β × origin rice YoY. a and β are fitted walk-forward, with β ≥ 0 and shrinkage. The hunger probability then multiplies the unchanged S-COV price probability. |
| **WARN** | Three-level warning (HIGH / WATCH / LOW) on the HUN-RICE probability. The WATCH threshold is chosen at each origin on earlier, already-published labels only (recall-weighted F2). |

**Disclosure.** Rice CPI was chosen *after* seeing the full-period correlation. Coefficients are fitted walk-forward,
but the choice of predictor is selection-informed. These results are development evidence, not validation.

## 4. Results

### Lead 1 (65 rows)

| Model | Accuracy | Balanced | TP / FP / FN | Brier | Quarters vs persistence (W/L/T) | Holm p vs persistence / climatology | PASS |
|---|---|---|---|---|---|---|---|
| HYB-GBA-SIM (post-hoc) | 0.877 | 0.834 | 12 / 4 / 4 | 0.101 | 4 / 1 / 8 | 0.098 / 0.098 | Yes (post-hoc) |
| **S-SIM (current)** | **0.846** | 0.751 | 9 / 3 / 7 | **0.118** | 4 / 3 / 6 | 0.105 / 0.105 | No |
| S-HUN-RICE | 0.831 | 0.740 | 9 / 4 / 7 | 0.138 | 4 / 3 / 6 | 0.160 / 0.160 | No |
| S-COV | 0.815 | 0.709 | 8 / 4 / 8 | 0.141 | 4 / 3 / 6 | 0.171 / 0.171 | No |
| Always-LOW | 0.754 | 0.500 | 0 / 0 / 16 | 0.246 | — | — | — |
| Persistence | 0.723 | 0.627 | 7 / 9 / 9 | 0.277 | — | — | — |

Against S-SIM, HUN-RICE wins one quarter (2024-Q4) and loses one (2024-Q2), has a worse Brier, and catches the same
9 HIGH rows. **It fails the promotion rule. Lead 1 keeps S-SIM.**

### Lead 2 (65 rows)

| Model | Accuracy | Balanced | TP / FP / FN | Brier | Quarters vs persistence (W/L/T) | Holm p vs persistence / climatology | PASS |
|---|---|---|---|---|---|---|---|
| **S-HUN-RICE** | 0.800 | **0.657** | **6** / 3 / 10 | **0.168** | 5 / 1 / 7 | **0.053** / 0.188 | No |
| S-COV (current) | 0.800 | 0.636 | 5 / 2 / 11 | 0.177 | 5 / 1 / 7 | 0.066 / 0.232 | No |
| S-SIM | 0.692 | 0.522 | 3 / 7 / 13 | 0.276 | 5 / 3 / 5 | 0.091 / 0.355 | No |
| HYB-GBA-SIM | 0.554 | 0.494 | 6 / 19 / 10 | 0.347 | 3 / 5 / 5 | 0.212 / 0.766 | No |
| Always-LOW | 0.754 | 0.500 | 0 / 0 / 16 | 0.246 | — | — | — |
| Persistence | 0.646 | 0.555 | 6 / 13 / 10 | 0.354 | — | — | — |

Against S-COV, HUN-RICE ties every quarter, improves Brier (0.177 → 0.168) and catches one more HIGH row (6 vs 5).
**It formally meets the pre-registered promotion rule**, but the gain is one row. It comes from 2024-Q3 onward, after
the first surge had been learned; it does not help either onset. It still fails PASS: recall is 0.38 (< 0.5) and the
Brier gain over climatology is not significant (Holm p = 0.19).

### Ordinary versus worsening quarters

"Worsening" = SWS hunger rose by 3 points or more from the last posted reading.

| Lead | Model | Worsening: correct / HIGH caught | Ordinary: correct / false HIGH |
|---|---|---|---|
| 1 | S-SIM | 19/25, 8 of 14 | 36/40, 3 |
| 1 | S-HUN-RICE | 18/25, 8 of 14 | 36/40, 3 |
| 2 | S-COV | 24/35, 5 of 15 | 28/30, 1 |
| 2 | S-HUN-RICE | 24/35, 6 of 15 | 28/30, 1 |

The models are reliable in ordinary quarters and weak exactly when warning matters: in worsening quarters they catch
about half the HIGH rows at Lead 1 and about a third at Lead 2.

### By province (S-HUN-RICE)

| Province | Lead 1 correct | Lead 1 HIGH caught | Lead 2 correct | Lead 2 HIGH caught |
|---|---|---|---|---|
| Batangas | 10/13 | 1/3 | 10/13 | 1/3 |
| Cavite | 11/13 | 2/4 | 11/13 | 2/4 |
| Laguna | 11/13 | 2/4 | 9/13 | 1/4 |
| Quezon | 9/13 | 4/5 | 9/13 | 2/5 |
| Rizal | 13/13 | — (no HIGH) | 13/13 | — (no HIGH) |

Rizal's perfect score is all LOW rows. Quezon has the most HIGH rows and the most errors.

### Coverage

All four arms issue all 65 rows at both leads (the E89 coverage fix is kept).

### Warning tier (WARN)

| Lead | HIGH or WATCH issued | HIGH caught | HIGH missed | False alarms | Precision |
|---|---|---|---|---|---|
| 1 | 31 | 13/16 | 3 | 18 | 0.42 |
| 2 | 42 | 8/16 | 8 | 34 | 0.19 |

At Lead 1 a WATCH level raises the catch from 9 to 13 of 16 HIGH rows, at the cost of 18 false alarms (10 of them in
2023, before any surge had been learned). At Lead 2 it doubles the catch but issues WATCH for 42 of 65 rows, which is too
many to act on. **WARN is a usable Lead-1 complement and not useful at Lead 2.**

### Generalization verdicts

| Lead | Model | Verdict |
|---|---|---|
| 1 | S-SIM, S-HUN-RICE, S-COV | Partially generalized |
| 1 | HYB-GBA-SIM | Partially generalized |
| 2 | S-HUN-RICE, S-COV, S-SIM | Partially generalized |
| 2 | HYB-GBA-SIM | Not demonstrated to generalize |

Which criteria fail (a–e from GENERALIZATION_CRITERIA.md):
- **Lead 1 (all arms):** only (c) fails. None wins significantly over persistence quarter by quarter (sign test
  p = 0.50; hybrid 0.19). Recall is 0.56 for S-SIM and HUN-RICE, 0.75 for the hybrid.
- **Lead 2 (HUN-RICE, S-COV):** (c) and (d) fail. Quarter wins 5–1 over persistence (p = 0.11), and recall is 0.38 and
  0.31. Correct majority in 85% of quarters; early 0.75, late 0.88.

## 5. Decisions

1. **Lead 1: keep S-SIM** (0.846, Brier 0.118). HUN-RICE does not improve it. HYB-GBA-SIM (0.877) stays the best
   exploratory candidate, awaiting unseen quarters.
2. **Lead 2: HUN-RICE becomes the development candidate.** It meets the promotion rule against S-COV, but the gain is
   one row and its predictor was selection-informed. **S-COV stays the reference model** until HUN-RICE is confirmed on
   unseen quarters.
3. **WARN: report as an optional Lead-1 WATCH level** (13/16 caught). Not adopted at Lead 2.
4. **No production change.** `final-system-v2` is untouched.

## 6. Sealed forecasts: when each can be evaluated

The sealed forecasts (E83 1331d498, E84 ad402660) are untouched. Each needs the target quarter's SWS hunger survey and
the quarter's PSA provincial CPI. Dates below are expected from the usual release lags and are not guaranteed.

| Target quarter | Needs | Expected evaluable |
|---|---|---|
| 2026-Q4 | SWS Q4 2026 survey; PSA CPI through December 2026 | about February 2027 |
| 2027-Q1 | SWS Q1 2027 survey; PSA CPI through March 2027 | about May 2027 |
| 2027-Q2 | SWS Q2 2027 survey; PSA CPI through June 2027 | about August 2027 |

**HUN-RICE is not covered by those seals.** It needs its own seal at the 2026-Q3 origin to be validated prospectively.

## 7. Target and data strategy

- **The binding limit is the outcome data, not the model.** Five model families (structural, component, LightGBM,
  hybrid, rice-led drift) agree on the ordinary quarters and fail on the same onset rows.
- **T43 has become a price indicator.** Since 2023-Q4 the hunger condition is always met, so T43 measures food
  inflation, which has moved against hunger. A target that tracks hunger directly (the E76 SWS hunger target) is the
  honest alternative. It was tested separately in E76/E87: persistence is unbeaten there at Leads 1–2.
- **Most valuable next source: SWS CALABARZON-level hunger** (microdata or regional tabulation; E87 request C). It
  would replace the Balance Luzon aggregate with a reading for the study region and give more onset examples to learn
  from. Next: a provincial outcome (CBMS 2024 or FNRI provincial FIES; E87 requests A–B) for province-level validation.

## 8. Are the objectives met?

| Question | Answer |
|---|---|
| Lead 1 above 75% accuracy? | Yes: 0.846 (S-SIM), partially generalized. Not significantly better than persistence quarter by quarter. |
| Lead 2 above 75% accuracy? | Yes nominally: 0.800 (S-COV and HUN-RICE). But always-LOW scores 0.754, and recall is 0.31–0.38. |
| PASS rule met with a pre-registered model? | **No**, at either lead. |
| Reliable HIGH-risk early warning at Lead 2? | **No.** Onsets are missed; the 2023-Q4 onset was not in any available input. |
| Longest reliable horizon | Lead 1, with the generalization caveats above. |

**Bottom line.** E90 explains the missed surges (one unforeseeable from the data, one learnable only after a first
surge) and adds a small, selection-informed Lead-2 improvement. It does not turn Lead 2 into a validated early warning.
That needs a regional hunger signal and unseen quarters.
