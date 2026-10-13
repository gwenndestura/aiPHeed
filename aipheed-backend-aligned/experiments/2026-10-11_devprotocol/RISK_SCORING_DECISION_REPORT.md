# Risk Scoring Decision Report (before any promotion)

| Item | Value |
|---|---|
| Date | 2026-10-11 |
| Basis | `SCORING_FORMULA_REPORT.md` (E5), `app/ml/features/risk_score_v2.py` (S1, unwired) |
| Not done | No model was trained or run. No production, thesis or scheduled-task change. `risk_score_v2.py` remains unwired. |
| Data limits | Computations used `data/processed/labels.parquet` restricted to **2021-Q1 to 2025-Q4** before any calculation. No 2026 outcome was inspected, printed or used. |
| Status of thresholds | **Neither threshold below is an official DA or government standard.** Both are empirical applications of the thesis's median rule. |

## 1. Threshold logic (verified)

**The S1 rule:** τ_ref is the median Equation 3 stress over all complete labelled quarters (5 provinces each) whose label was **published before the as-of date**. Publication follows Rule L (the later of the last SWS round and the final-month provincial CPI release). Unknown dates are excluded, and at least 8 quarters are required.

| | Retrospective τ0 | Prospective τ_ref |
|---|---|---|
| As-of date | 2023-10-01 (first exploratory evaluation origin) | 2026-07-01 (first protected forecast origin, 2026-Q3) |
| Quarters used | 8: 2021-Q2 to 2023-Q2 (40 rows) | 16: 2021-Q2 to 2025-Q4 (80 rows) |
| Value | **10.843** | **14.345** |
| Purpose | Leakage-free labels for evaluating the reused 2023-Q4 to 2025 quarters | Labels for forecasts issued from 2026-Q3 onward |
| Meaning | Above the typical stress of 2021 to mid-2023, a low-hunger period | Above the typical stress of 2021–2025, which includes the 2024–2025 high-hunger period |

**Why the two differ:**

- They are the same rule applied at different dates.
- 14.345 is higher because the reference now includes 2024–2025, when Balance-Luzon hunger reached 14.3–25.3%.
- **Neither value should replace the other.** τ0 is only for retrospective evaluation; 14.345 is for prospective use.
- 14.345 coincides with the approved "global median". For future forecasts that median becomes leakage-free, because every quarter it uses is published before 2026-07-01.

### Point-in-time verification of 14.345

| Check | Result |
|---|---|
| Latest label used | 2025-Q4. Published 2026-01-20 (CPI proxy: national release + 14 days), more than 5 months before 2026-07-01. |
| Date types of the 16 publication dates | 15 proxy, 1 verified (2024-Q4) |
| Delay every proxy date by 90 days | **Unchanged** (14.345, 16 quarters) |
| As-of 2026-10-01 (2026-Q4 origin) | **Unchanged** (14.345, 16 quarters) |
| Strict protocol (verified dates only) | **Undefined.** Only 1 quarter qualifies (< 8). The prospective value rests on the development-protocol proxy dates; it is robust to their uncertainty, but not formally verified. |

### Frozen afterward

`reference_threshold()` is a pure function: given a later as-of date **and** new labels, it would return a new value.

- At 2026-10-01 it is unchanged **only because no 2026 label exists**.
- Freezing is therefore a **governance step**: the value must be recorded once and passed to `classify()`, not recomputed.

A proposed record is saved as `S1_FROZEN_REFERENCE_PROPOSAL.json` (SHA-256 `dc77104476c28141…`). It holds:

- the value 14.345 and the as-of date;
- the 16 quarters, with their publication dates and date types;
- the SHA-256 of `labels.parquet`;
- the freeze rule: "do not recompute when later labels are published; change only through a documented, dated review".

**It is a proposal. It is not adopted and not wired.**

## 2. The overclassification concern, quantified

**Decomposition (80 rows, 2021–2025).**

- stress = R_t + P_p,t, where R_t = SWS_t (regional) and P_p,t = 2·d_p,t (provincial).
- Because P sums to zero within every quarter, their covariance is exactly 0, so the variance splits cleanly:

| Component | Variance | Share | Mean absolute contribution |
|---|---:|---:|---|
| Regional hunger R | 25.05 | **65.2%** | Mean distance from 14.345: 4.14 points |
| Provincial deviation 2·d | 13.37 | **34.8%** | Mean absolute value: 2.92 points |
| Total | 38.42 | 100% | — |

**How much of the HIGH/LOW label comes from the regional term alone:**

| Threshold | Labels equal to the regional-only call (R > τ) | Before 2023-Q4 | 2023-Q4 to 2025-Q4 |
|---|---:|---:|---:|
| 14.345 | **65/80 (81%)** | 36/45 | 29/35 |
| 10.843 | 61/80 (76%) | 28/45 | **33/35** |

- The provincial term could change at least one label in 13 of 16 quarters (|R − 14.345| < max|P|). In practice it changed **15 of 80** labels at 14.345.
- **In 2023-Q4 to 2025, the classification is almost entirely the regional hunger level.**

**What this means for the overclassification concern:**

- The aligned score is HIGH in 50% of 2021–2025 rows overall. Its 90% HIGH in 2024–2025 follows Balance-Luzon hunger, which was above 14.345 in **every** quarter of 2024–2025 (and in 0 quarters of 2022–2023).
- **This is the hunger data, not a scoring error.**
- The score does over-generalize in one sense: **all five provinces inherit one regional value.** So "most provinces HIGH" means "the region's hunger level was high", not five independent findings.

### Is the factor of 2 defensible?

**There is no methodological basis on record.**

- The thesis gives only "alpha coefficient amplifying the provincial CPI deviation signal" (Equation 3 legend).
- The code comment says the same (`label_generator.py` l.100–101).
- No derivation, citation, calibration or sensitivity analysis exists in the project.

**Its practical effect:**

| Weight | Provincial-term sd relative to regional sd | Provincial share of variance |
|---|---:|---:|
| α = 2 (current) | 0.73 × (3.66 vs 5.00) | 35% |
| α ≈ 2.74 (would equalize the two variances) | 1.00 | 50% |

- α = 2 is therefore neither "equal weight" nor estimated from data.
- **No defensible alternative value was found either.** No outcome measure exists against which α could be estimated; that would need a province-level food-insecurity outcome.
- **Recommendation: keep α = 2 (approved), and document it as an unvalidated design choice.** Do not change it to alter HIGH counts.

## 3. Two separate purposes

| | Regional stress indicator | Provincial food-price pressure indicator |
|---|---|---|
| Question | Is hunger-related stress for the region above a fixed historical reference? | Are a province's food prices rising faster than the region's? |
| Measure | R_t = SWS Balance-Luzon hunger % (the quarter mean of Equation 3 stress) | d_p,t = provincial food CPI YoY − five-province mean, in pp |
| Reference | Frozen point-in-time reference (see note below) | 0 (the regional mean), by construction |
| 2021–2025 behaviour | Above 14.345 in 7 of 16 quarters (2021: 33%; 2022–2023: 0%; 2024–2025: 100%). Above the series median 13.05 in 8 of 16 quarters. | Share of quarters above the mean: Rizal 0.62, Batangas 0.56, Cavite, Laguna and Quezon 0.38 each. The ordering shifted over time (E2/E4). |
| Can it be called food insecurity? | **Regional** hunger, yes, with limits (below) | **No.** It is relative price pressure, not a confirmed food-insecurity outcome. |
| Forecastability (E1–E5) | Persistence and carry-forward already perform well. LightGBM is non-inferior, not better. | No tested predictor beats carry-forward (E2: Spearman ρ 0.20 vs 0.38; E4 D-D: balanced accuracy 0.535). Best shown as observed, lagged data. |

**Note on the regional reference:** the frozen median of row stress (14.345), or the frozen median of the quarterly regional series (13.05). Which reference is used is an adviser decision.

**Limits of the regional indicator:**

1. **SWS "Balance Luzon" is all of Luzon outside Metro Manila,** not CALABARZON alone. The thesis text does not state this.
2. **SWS respondent populations changed in 2025:** household heads, then registered voters, then adults (D3).
3. **It is one value per quarter:** 16 labelled quarters in the approved window.

### Does the data support a province-level food-insecurity classification?

**No.**

- The only province-specific variation in Equation 3 is relative food inflation. No measured food-insecurity or hunger outcome exists for any CALABARZON province, and the regional hunger series is not even CALABARZON-specific.
- A province labelled HIGH by Equation 3 is "in a high-hunger super-region with above- or below-average food-price pressure". **It is not a confirmed province-level food-insecurity finding.**

**Missing outcome data (within 2021–2026; none retrieved):**

| Data | Value to the classification |
|---|---|
| Province-level food-insecurity prevalence (FIES or similar) | Directly measures the target. NNS FIES is published at regional level only. |
| A CALABARZON-specific (Region IV-A) hunger series | SWS regional or provincial tabulations on request |
| NNC/DOH OPT Plus provincial malnutrition prevalence | Annual provincial outcome |
| CBMS provincial or LGU indicators | Provincial welfare indicators |
| DSWD provincial program caseloads | Provincial need |

Any of these would allow (a) validating province-level labels and (b) estimating α instead of assuming it.

## 4. Recommended methodological decision

**Is S1 suitable as the current baseline?** **Yes,** as the baseline computation of the thesis's Equation 3 label, for both retrospective evaluation and prospective use.

**What S1 fixes:**

1. **Leakage:** the threshold uses only labels published before the as-of date. The full-sample median used retrospectively is no longer applied.
2. **Drift:** the threshold is frozen. HIGH no longer changes meaning fold by fold (10.8 → 14.1).
3. **Zero-fill:** a missing CPI value is now "insufficient data", not 0% inflation, and the regional mean requires all five provinces.
4. **Traceability:** the reference value, quarters, publication dates and source hash are recorded (proposal JSON).

**What S1 does not fix:**

1. **It does not solve the excessive HIGH predictions.** It labels 2024–2025 HIGH in 90–100% of rows, because the hunger data are high. **No fix to the score was found that both stays hunger-anchored and reduces this.** Doing so would contradict the data.
2. **Regional dominance:** 81% of labels equal the regional-only call. Provinces mostly move together.
3. **No province-level outcome:** S1 cannot confirm which provinces are more food insecure.
4. **α = 2 is unvalidated.**
5. **The SWS stratum is broader than CALABARZON,** and its respondent populations changed in 2025.
6. **Proxy publication dates:** the prospective threshold is undefined under the strict protocol.
7. **Forecast evidence is still weak:** small, reused test sets; LightGBM non-inferior, not superior.

**Recommendation for the adviser (the next decision):**

1. **Adopt S1 as the baseline label computation,** with the frozen prospective reference 14.345 recorded per the proposal JSON.
2. **Report outputs as two components rather than one "provincial food-insecurity" HIGH/LOW:**
   - **regional stress status** (S1 regional level against the frozen reference; LightGBM forecast compared with carry-forward);
   - **provincial food-price pressure** (observed relative CPI deviation, explicitly not food insecurity).
3. **Do not describe province labels as confirmed food-insecurity risk** until a province-level outcome is available.
4. **Keep α = 2,** documented as an unvalidated design choice.
5. **Decide whether to seek province-level outcome data** (§3).

**Still pending, outside this decision:**

- retiring or replacing the served `backend/` `label_cpi`, a price-index trend artifact (E5);
- handling the 2026 CPI rows already present in production `backend/` data (`RISK_CLASSIFICATION_REPORT.md` §7).

## 5. Safety

| Item | Result |
|---|---|
| `risk_score_v2.py` | Unchanged and unwired. A test confirms it is not imported by services, the API, `main.py`, the label generator or training code. |
| Model experiments | None run |
| Production files, scheduled tasks, thesis | Unchanged |
| 2026 data | None inspected, printed or used |
| New files | `RISK_SCORING_DECISION_REPORT.md` (this file); `S1_FROZEN_REFERENCE_PROPOSAL.json` |

**Stopping for review.**
