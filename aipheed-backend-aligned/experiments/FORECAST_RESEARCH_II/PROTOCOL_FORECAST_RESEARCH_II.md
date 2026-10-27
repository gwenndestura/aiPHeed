# FORECAST_RESEARCH_II protocol (frozen before scoring)

**Branch:** `aiPHeed/forecast-research`, continuing from 32b368a (FORECAST_RESEARCH, protocol `1974fae6`).
**Written:** 2026-10-27. The SHA-256 of this file goes in `runner/PROTOCOL_SHA256.txt` and is committed before any arm in §5 is scored or any test in §3, §7 or §9 is run.
**Unchanged:** the served model (P0H4, seal a498b5ef), the P0H4-U export (`backend/data/ch1_engine_fr`, seal bd6572e1) and every frozen artifact.

## 0. Honesty note

- Every 2021-2026 quarter has been inspected by more than 100 earlier experiments, including FORECAST_RESEARCH. No 2021-2026 figure in this study is a clean test.
- This protocol limits further selection bias in three ways:
  1. One pre-registered selection rule on the DEV block (§6.3).
  2. An **online-selection** forecaster (§6.4). It picks the arm at each origin from outcomes known before that origin, so its score estimates what the selection procedure itself achieves.
  3. A prospective seal (§10), the only clean test.
- No result already known from earlier work is re-run unless a step here needs it as a reference.

## 1. Questions and hypotheses

| ID | Hypothesis (stated before testing) | Test | Supported if |
|---|---|---|---|
| **T1** | T43c can be rebuilt exactly from the raw PSA YoY file and the SWS rounds, and since 2023-Q4 it is decided by the price condition | §3.1 | 100/100 labels reproduce |
| **T2** | The hunger term is often within SWS sampling error of 11.3, which caps the accuracy any forecaster can reach | §3.2 | ≥ 1 evaluation quarter with P(true side ≠ observed side) ≥ 0.20 |
| **T3** | If T43c measures food-insecurity *risk*, provincial price pressure goes with higher (or rising) regional hunger | §3.3 | Spearman ρ > 0 with permutation p < 0.10 at lag 0 or lag 1 |
| **H1** | Explicitly modelling food-price trend and reversal (drift, target anchoring, partial reversion) beats the flat projection at Leads ≥ 2 | §5 J1-J3 vs Z0/J0 | Lower DEV price Brier at Leads 2-3, and not significantly worse at Lead 1 |
| **H2** | Modelling the food and gap conditions jointly (instead of the independence formula) improves price-term calibration | J0 vs Z0 | Lower price log loss at ≥ 2 of Leads 1-3 |
| **H3** | Bootstrapped (fat-tailed) innovations improve log loss for rare HIGH outcomes | JB3 vs J3 | Lower T43c log loss at ≥ 2 of Leads 1-3 |
| **H4** | The ten non-base families fail for identifiable reasons (coverage, timing, redundancy, missing cross-sectional variation, target mismatch, power, architecture), not because they were never tested fairly | §7 decision table | A reason is assigned to every family |
| **H5** | The schedule-B Lead-1 loss is concentrated in quarters whose newest reading is within 1 SE of 11.3 (noise), not systematic | §8 | ≥ 70% of the B-minus-A Lead-1 Brier loss comes from such quarters |
| **H6** | The price-pressure component alone is reliable to a longer lead than T43c | §6.5 | Component max reliable lead > T43c max reliable lead |
| **H7** | Online selection performs as well as DEV selection | §6.4 | Not significantly worse (two-sided p ≥ 0.10) at Leads 1-3 |

## 2. Data (all already in the repository; nothing new is collected)

| Data | File | SHA-256 (first 8) |
|---|---|---|
| Feature stack, labels, SWS rounds (with margins of error), realised YoY, known labels | `FORECAST_RESEARCH/data/{stack, labels_t43c, sws_rounds_primary, ps_full, known_by_origin}.csv` | ad88256a, b11008ec, 11220452, 6d7ec187, cd583905 |
| FR predictions (π_H under A and B, Z0-Z3, P0, persistence, climatology) | `FORECAST_RESEARCH/out/predictions.csv` | recorded at run time |
| Evaluation rows | `FINAL_ARCHITECTURE/out/predictions.csv` | 3810639a |
| PSA monthly CPI index, food and all items, five provinces, 2021-01..2026-09 | `E41_Lead2_Audit/data_acquired/cpi_index_ACP22.csv` | 69004dd7 |
| PSA published YoY (label source) | `E40_SWS_CPI_Tiers/data_acquired/psa_cpi_yoy_headline_food_2021_2026.csv` | 3b382d27 |
| Thresholds | `E40_SWS_CPI_Tiers/label_spec.json` | a0d8054a |
| FNRI FIES observations | `E87_Outcome_Gap/data_acquired/fnri_fies_observations.csv` | recorded at run time |
| OCTA Balance Luzon hunger rounds | `git show final-aipheed-thesis-e72:…/E73_Objective_Remediation/inputs/provenance.csv`, copied to `data/octa_bl.csv` | recorded at run time |
| PSA FIES 2023 PUF (Family Income and Expenditure Survey; **not** a food-insecurity survey) | `C:\Users\admin\Downloads\PHL-PSA-FIES-2023-V1-PUF\` (read only; outputs are aggregates) | recorded at run time |

**Window.** Every value used is dated 2021-01 or later and published before 2026-10-15. Monthly log increments start at 2021-02, so that no 2020 index enters an increment. YoY rates of in-window months come from PSA's own published series (the label's own definition).

## 3. Target investigation (no model is fitted)

### 3.1 Rebuild and anatomy (T1)

- **Rebuild.** For each province p and quarter q:
  - H_q = the mean of the quarter's non-commissioned Balance Luzon rounds (`sws_rounds_primary`);
  - F, HL = the quarter means of the published monthly food and all-items YoY;
  - y = [H_q > 11.3] AND [F − θ_f(p) > 0 OR F − HL − θ_g(p) > 0].
  - Compare with `labels_t43c.csv`.
- **Anatomy.** Counts of HIGH rows by reason (food only, gap only, both), of rows blocked by hunger, and of rows blocked by price, by year.
- **Thresholds.** θ = province P60 of 2021-Q1..2022-Q4 and H = P60 of BL over the same window. They are relative ("above this province's own 2021-22 normal"), not an absolute food-insecurity standard. This is reported as a fact of the definition.

### 3.2 Measurement reliability of the hunger term (T2)

- For round r, SE_r = (moe_r / 1.96) × √(p_r(1 − p_r)) / 0.5, with p_r = H_r / 100. The margin of error in `sws_rounds_primary` is the published one for a 50% proportion at the area level.
- For a quarter with R rounds: SE_q = √(Σ SE_r²) / R.
- With a flat prior, the true value ~ N(H_q, SE_q²). Then:
  - P(true > 11.3) = Φ((H_q − 11.3) / SE_q);
  - **label reliability** ρ_q = max(P, 1 − P).
- **Accuracy ceiling.** Consider a forecaster who knows every province's true price condition and the true hunger level, and is scored against the observed label. Its expected accuracy is E[agreement]:
  - 1 for rows whose price condition is not met;
  - E_true[max(Φ(z), 1 − Φ(z))] for rows whose price condition is met, with z = (true − 11.3) / SE_q, by Monte Carlo (20,000 draws, seed 2031).
  - It is reported per lead on the evaluation rows. It is an upper bound that comes from sampling noise alone.
- **Price borderline share.** The share of rows whose deciding price margin lies within 0.5 points of its threshold.

### 3.3 Construct validity (T3, descriptive plus one pre-set test)

1. **Price → hunger link (test).** Let X_q = the five-province mean of max(F − θ_f, F − HL − θ_g), the regional price-pressure excess. Compute Spearman ρ(X_q, H_{q+L}) for L = 0, 1, 2 over all quarters with both, and ρ(X_q, H_{q+L} − H_{q−1}).
   - p-values come from circular-shift permutation: every cyclic shift of H against X except the identity.
   - T3 is supported if ρ > 0 with p < 0.10 at L = 0 or L = 1.
2. **FNRI FIES (descriptive).** Compare annual means for 2021, 2023 and 2025 with the FNRI moderate-or-severe prevalence: BL SWS, T43c HIGH share and the price-condition share. The basis (households vs population) and the geography (province vs region) are reported, not equated.
3. **OCTA (descriptive).** For quarters with both surveys: agreement of OCTA vs SWS on the "above 11.3" side, and the gap between OCTA's publication date and SWS's (is OCTA an earlier signal?).
4. **PSA FIES 2023 (descriptive, n = 5).** Province food share of spending and share of people in the national bottom 30%, against each province's T43c HIGH share and mean price excess 2021-26. Spearman ρ only. Because the price thresholds are province-relative, a null result is expected by construction, and it is reported as such.

## 4. Issue schedules and hunger term (unchanged from FORECAST_RESEARCH)

- **A:** day 1 of quarter t+1.
- **B:** the day after the last BL round of quarter t is published, capped at day 1 of month 3 of quarter t+1. Only π_H changes; every other input keeps the A cut-off.
- **π_H:** the served H4 rule (FR §4), read from `FORECAST_RESEARCH/out/predictions.csv` (`pi_H_A`, `pi_H_B`).
- **Product schedule S-AB** (the P0H4-U schedule):
  - Lead 1 uses A;
  - Leads ≥ 2 use B.
  - S-AB is the primary product. A-only is reported too.
- **No new hunger arm.** E109-E113 and LEAD2_OPTIMIZATION found nothing that beats the newest reading.

## 5. Price-part arms (π_P = P(food condition OR gap condition) for the target quarter)

**Reference arms**
- **Z0:** the flat projection with the independence formula (FR).
- **P0:** the served LightGBM price part.
- **P4:** the LightGBM boosted from Z0 (Addendum 1). Reference only.

**New arms: a structural random walk with drift for the monthly log food and all-items indices, simulated jointly**

At origin t, m0 = month 2 of quarter t (the A cut-off). Increments d_m = ln I_m − ln I_{m−1}, months 2021-02..m0.

- **Innovation covariance Σ.** A 2×2 matrix (food, all items), pooled over the five provinces after removing each province's mean. It uses the trailing 36 months (fewer if not available; minimum 12 per province), with dof = N − 5.
- **Drift g (per series):**

| Arm | Drift |
|---|---|
| **J0** | 0 (the flat projection, but with structural σ and joint conditions) |
| **J1** | The province's mean increment over the trailing 12 months (inflation persists) |
| **J2** | ln(1.03)/12 for both series (anchored at the 3% midpoint of the BSP 2-4% target) |
| **J3** | 0.5·J1 + 0.5·J2 (partial reversion towards the anchor; a fixed glide-path weight, not fitted) |

- **Drift-estimation uncertainty.** J1 adds ĝ ~ N(g, Σ/12) per draw. J3 adds N(g, 0.25·Σ/12). J0 and J2 add none.
- **Simulation.**
  - 4,000 joint draws per (origin, province), seed 2031 + 10·(t − 8000) + province index. The same draws serve every lead.
  - Each draw builds the log paths m0+1..m0+13, computes each target month's YoY exactly (100·(exp(L_m − L_{m−12}) − 1), using simulated base months where m−12 > m0), and takes the quarter means F̃ and H̃L.
  - π_P = share of draws with F̃ − θ_f > 0 OR F̃ − H̃L − θ_g > 0.
- **J3T (σ check against the track record).**
  - For lead k: s_k = max(1, RMSE_k / SD_k).
  - RMSE_k = the RMSE of J3's mean F̃ against the realised F on training rows of lead k (target ≤ t−1).
  - SD_k = the median simulated SD of F̃ on the same rows.
  - It needs ≥ 4 target quarters; otherwise s_k = 1.
  - Draw deviations of F̃ and H̃L from their means are multiplied by s_k.
- **JB3 (fat tails).** J3 drift, with innovations resampled iid by month from the pooled demeaned (food, all-items) increment pairs of the trailing 36 months (all provinces).
- **CMB (forecast combination).** The equal-weight mean of the Z0 and J3T probabilities. The weights are fixed, not fitted.
- **LJ (LightGBM correction).**
  - A LightGBM binary classifier on the price label, with init_score = logit(clip(J3T π_P, 0.005, 0.995)). Each training row's J3T value comes from that row's own origin.
  - Features: FR's F12 (all 12 families plus lead).
  - Grid: LEAD2 `reg_grid` (depth 1, 2 leaves, learning rate 0.05, trees ∈ {10, 25, 50, 100}, min_child 25, L1 1, L2 10, colsample 0.7), seed 2031.
  - Selected by log loss over the inner folds (the last 4 training origins).
  - Training rows: t' < t, target ≤ t−1, realised CPI quarter known. With fewer than 30 rows or one class, LJ = J3T.

**Audit before scoring.**
- For the known months, YoY computed from the index vs the published YoY: max |Δ| is reported.
- J0's mean F̃ at Lead 1 vs Z0's A1_food + θ_f: reported. The differences are index rounding and the m0 alignment.

## 6. Evaluation

### 6.1 Rows and metrics
- The FR evaluation rows: origins 2022-Q4..2026-Q3, Leads 1-4, 70/65/60/55 rows.
- **T43c forecast:** p = π_H(S-AB) × π_P.
- **Metrics:**
  - accuracy at 0.50, with a 90% quarter-block CI;
  - balanced accuracy, precision, recall, TP/FP/FN/TN;
  - Brier score, log loss, AUC;
  - calibration (bins, calibration-in-the-large, slope, ECE; diagnostic only);
  - n_eff;
  - price-term Brier, log loss and AUC;
  - continuous RMSE of F̂.

### 6.2 Reliability
- R1-R7 exactly as in FR §6, with same-information persistence under S-AB and climatology.
- Maximum reliable lead = the largest k such that Leads 1..k all pass.

### 6.3 Selection (one rule, DEV only)
- Candidates: Z0, P0, J0, J1, J2, J3, J3T, JB3, CMB, LJ, each × π_H(S-AB).
- **Choose the lowest DEV (targets ≤ 2024-Q4) T43c Brier averaged over Leads 1-3.**
- **LightGBM preference:** if the best LightGBM arm (P0 or LJ) is within 0.002 of the best, choose it. Otherwise choose the best and state that LightGBM adds no development value.
- **"FINAL"** = the chosen arm. It is compared with:
  - P0H4 (A schedule, the served model);
  - P0H4-U (S-AB);
  - persistence, climatology and always-LOW.
- Comparisons use a one-sided quarter-block bootstrap on Brier, with Holm correction across the five comparisons of a lead.
- **FINAL replaces P0H4-U as the research candidate only if** its DEV Brier (L1-3) is lower **and** it is not significantly worse than P0H4-U at any of Leads 1-4 (diff > 0 with two-sided p < 0.10). Otherwise P0H4-U stays the candidate, and FINAL is reported as a benchmark.

### 6.4 Online selection (H7)
- **ONL:** at each origin t, use the arm among the 10 with the lowest mean price-term Brier over all-lead rows of earlier origins whose target ≤ t−1.
- It needs ≥ 4 such target quarters; otherwise P0. Ties go to the earlier arm in the §6.3 list.
- ONL × π_H(S-AB) is scored on all rows and compared with FINAL.

### 6.5 Component reliability (H6)
- **Price component.**
  - Label: the price condition.
  - Rows: every evaluation-origin row with a realised CPI quarter, including quarters without SWS.
  - Persistence: the condition on the latest three CPI months (F_ex > 0 or G_ex > 0).
  - Climatology: the price-label share among training rows of that lead.
  - Criteria: R1-R7.
- **Hunger component.**
  - Label: BL > 11.3, one row per target quarter.
  - π_H under A and S-AB.
  - Persistence: the newest reading > 11.3. Climatology: the FR hunger climatology.
  - Criteria: R1-R7. R1 cannot pass with one regional series, and that structural limit is reported.

## 7. Why the ten families do not help (H4)

**Main column per family:** A2→A2, A3→A3, V1→V1, C1→C1, C2→C2, C3→C3, C4→C4, E1→E1, E2→E2, N1→N1 (FSSI), with GDELT `G_pri_yoy` reported separately, and H1→h_last.

| Test | Definition |
|---|---|
| D1 coverage | Missing share in the evaluation rows (Leads 1-3) |
| D2 cross-section | Between-province share of the column's variance within origins (origin-level table) |
| D3 time confound / redundancy | \|Spearman(column, t)\|; R² of a linear regression of the column on (A1_food, t) |
| D4 predictive association | Spearman(column at origin t, e_f(t,k)) for k = 1, 2, 3, where e_f = realised food excess − the flat projection (Z0 error). 90% quarter-block CI. |
| D5 explanatory association | Spearman(column value describing the target quarter, e_f), taken from origin t* = target_q + 1 (published by the end of the following quarter); same CI. Also both associations with the BL hunger change (target reading − newest reading at issue), regional means. |
| D6 out-of-sample, 1 parameter | Rolling origin: e_f = lead mean + β·z(column) (ridge α = 10 on the standardised column; intercept by lead) vs lead mean only. ΔRMSE by lead with a 90% CI. Compared with Addendum 2's LightGBM add-one ΔRMSE (architecture test). |
| D7 power | MDE = 2.49 × the bootstrap SD of the T43c Brier difference (add-one LJ-f vs J3T) at Leads 1-3, plus the best-case bound of its 90% CI |

**Reason assignment (every reason that applies is listed):**

| Reason | Rule |
|---|---|
| Coverage | D1 > 30% |
| No cross-sectional information | D2 < 5% (a national series: only quarter-level variation, n ≈ 20) |
| Time-confounded / redundant | D3 \|ρ_t\| > 0.8 or R² > 0.8 |
| Coincident, not leading | D5 CI excludes 0 at some lead while D4's CI includes 0 at the same lead |
| No association with the target | D4 and D5 CIs include 0 at every lead |
| Architecture | D6 significantly better than the LightGBM add-one (CI of the difference excludes 0) |
| Underpowered | the D7 best-case improvement ≥ 0.01 while the CI includes 0 |

## 8. Schedule investigation (H5)

- **Decomposition.** Decompose the Lead-1 T43c Brier difference (B − A, P0 price part) by target quarter.
- **Noise test.** For each quarter, record the B reading, its SE (§3.2) and whether |reading − 11.3| < SE. H5 = the share of the positive (B worse) Brier sum that comes from those quarters.
- **Warning time.** Report the warning time in days of each product (L1-A, L2-B, L2-A, L3-B, L3-A, L4-B, L4-A), and the T43c accuracy and Brier of each. Warnings are then ordered by days rather than by the nominal lead.
- **The defensible calendar.** A quarter-start issue for Leads 1-4, plus an SWS-update re-issue for Leads 2-4. A B-schedule Lead-1 forecast is a nowcast, issued after its quarter starts, and is never shown as a warning.

## 9. Contributions for FINAL (§6.3) and limits

**Contributions**
1. **Structural components.**
   - Remove the price projection (π_P → the price climatology by lead).
   - Remove π_H (→ the hunger climatology).
   - Drift ablation: FINAL's drift vs J0.
   - Report ΔBrier by lead with a CI.
2. **Ten families through LJ.**
   - Add-one: LJ with family f's columns plus lead only.
   - Leave-one-out: LJ without f.
   - Permutation: LJ fixed; f's columns are swapped with the same province and lead's values from a random other evaluation origin, 20 draws.
   - Report ΔBrier T43c by Lead 1-3, with a 90% CI, one-sided p and Holm across the ten families.
   - **Predictive** = add-one CI excludes 0 (helps), no lead significantly worse, and permutation Δ > 0.
3. **SHAP for LJ,** by chronological third (Spearman between thirds). Reported as model influence only. No percentages are normalised across families.
4. **If FINAL is not LJ,** the families' contribution *to FINAL* is zero by construction. The LJ results then show what they would add to it.

**Limits**
- **L1.** The label-noise ceiling (§3.2) per lead.
- **L2.** The oracle ceilings (FR1, cited).
- **L3.** MDE for FINAL vs P0H4-U at Leads 1-3, and the number of further quarters needed to detect ΔBrier = 0.01 and 0.02 (SD ∝ 1/√quarters).
- **L4.** Predictable share of the price error: 1 − (J0 theoretical variance of F̃ / Z0 realised MSE) by lead. A value near 0 means the error is the variance of future innovations.

## 10. Prospective seal

- FINAL and ONL (if different) at origin 2026-Q3 for target quarters 2026-Q4..2027-Q3:
  - Lead 1 issued 2026-10-01;
  - Leads 2-4 issued under B (2026-10-15).
- Written to `out/sealed_prospective.csv`; the SHA-256 goes in `out/PROSPECTIVE_SEAL.json`.
- Scored only after SWS publishes the target quarters.

## 11. Integration

- FINAL is exported to `backend/data/ch1_engine_fr2/` and served only with `AIPHEED_CH1_ENGINE=fr2`.
- If FINAL = P0 (i.e. P0H4-U), no new export is made.
- The default stays P0H4. Tests cover: default unchanged, the flag, seal, verdict, and API = rows.

## 12. Readiness rules (fixed now)

| Use | Requires |
|---|---|
| Demonstration | Lead 1 reliable on development evidence; served text matches the model |
| Pilot (lead k) | Demonstration, plus ≥ 1 sealed quarter scored at lead k with accuracy ≥ 0.75 and recall ≥ 0.60, and lead k reliable on development evidence |
| Operational | ≥ 4 consecutive sealed quarters passing R2 and R6 at the lead, plus validation against an independent provincial food-insecurity outcome (CBMS or FNRI provincial FIES) |

## 13. Not allowed

- Changing the target, thresholds, rows or rules after seeing results.
- Fitting any calibrator on evaluation outcomes.
- Pre-2021 data.
- Web queries for current PSA, BSP or SWS values; sws.org.ph.
- Changing the served artifacts or seals.
- Frontend design changes.
- Pushing or deploying without the user's approval.
