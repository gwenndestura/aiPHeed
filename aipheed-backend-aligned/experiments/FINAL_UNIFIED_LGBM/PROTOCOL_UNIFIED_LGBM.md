# Protocol: one unified LightGBM across all leads (FINAL_UNIFIED_LGBM)

**Branch:** `aiPHeed/unified-lgbm-objectives`, from `aiPHeed/firi-data-audit`.
**Freezing:** this file's SHA-256 goes in `runner/PROTOCOL_SHA256.txt` before any unified model is scored.
**Authority:** the user's master directive of 2026-10-26 allows substantive changes and requires one unified LightGBM
(not lead-specific final models), all 12 FIRI v2 families, horizons not capped at Lead 4, and an honest 75% test.

## 0. Known before freezing (disclosure)

- CH1-LGBM (one LightGBM per lead) results at Leads 0–8 on audited inputs: Lead 1 0.914, reliable; Leads 2–8 fail.
- Every quarter 2022-Q3 to 2026-Q3 has been scored by CH1. **No unseen outcome exists before 2026-Q4.** The
  development/confirmation split below therefore separates model *selection* from *evaluation*, but the confirmation
  quarters are not new to the researchers. This is stated in every result.
- The World Bank Pink Sheet series were downloaded and parsed; no model has used them.
- Data availability for the unified model (`out/testability_unified.json`, no model scored):
  - pooled training first becomes eligible at origin 2022-Q4;
  - evaluable quarters per lead: 1:14, 2:13, 3:12, 4:11, 5:10, 6:9, 7:8, 8:7, 9:6, 10:6, 11:5, 12:4, 13:3, 14:2, 15:1;
  - so K = 15, and R1 (≥ 10 quarters) is reachable up to Lead 5.

## 1. Target (unchanged)

T43c (FINAL_THESIS_OBJECTIVES protocol §2): HIGH(p, q) = [SWS Balance Luzon hunger(q) > 11.3] AND [province food
YoY or food − headline gap above its frozen 2021–22 P60]. Same labels, thresholds, study window (2021+), issue date
O(t) = first day of quarter t+1, and lead k = target quarter t+k.

**Direct food-insecurity component, reported separately:** the hunger condition H(q) = [BL hunger(q) > 11.3], one
observation per quarter.

## 2. Model: UNI-LGBM

P(HIGH) = π_H × π_P, as in CH1, with one change: **π_P is one LightGBM trained on rows of every lead.**

- **Stacked table:** for k = 1…K, the CH1 feature rows of lead k (16 columns covering all 12 families, computed for
  target t+k at origin t), plus the column `lead` = k. K = the largest lead with at least one evaluable row (origin ≥ 2021-Q1 with eligible pooled training, target labelled ≤ 2026-Q3), computed from data availability before scoring (`out/testability_unified.json`).
- **Training at origin t:** every stacked row with origin t′ < t and target t′+k′ ≤ t−1, labelled with the price
  condition complete before O(t) (`known_ps(t)`). Eligibility: ≥ 6 target quarters, ≥ 5 HIGH, ≥ 5 LOW (frozen minimum).
- **Prediction at origin t:** one model; the rows of origin t for every lead.
- **Settings:** the CH1 grid (depth {1, 2} × trees {50, 150} × class weight {none, balanced}), min child 15,
  learning rate 0.05, L2 5.0. Chosen inside each training window by inner chronological validation: the last 4 origins
  of the training window are each held out in turn, training only on rows whose target is before that origin; lowest
  log-loss wins.
- Refit at every origin (expanding window). This is one model at each issue date, not one model per lead.

## 3. Pre-specified variants (selection on development quarters only)

| Variant | Change |
|---|---|
| **U0** | UNI-LGBM on the 16 CH1 columns + `lead` |
| **U1** | U0 + 5 world-price columns from the World Bank Pink Sheet, months ≤ month 2 of quarter t (published ~3rd business day of the next month): Thai 5% rice YoY (family A3), rice 3-month log change (A3), cereal YoY = mean of rice, wheat and maize YoY (A1), crude oil YoY (A2), urea YoY (C3) |
| **U2** | U1 + monotone constraints (+1) on `A1_food`, `A1_gap` and `A_mom`: higher projected food inflation can only raise P(price pressure) |

**Hunger component variant (pre-specified):**

| Variant | Definition |
|---|---|
| **HG** | π_H replaced by a LightGBM classifier of P(area hunger(t+k) > 11.3) trained on the four SWS areas (NCR, Balance Luzon, Visayas, Mindanao; real measurements of each area, never relabelled as CALABARZON) |

HG features:
- latest reading known at O(t) and its change from the previous known reading;
- the mean of the last 4 known readings;
- true horizon and lead;
- area dummies;
- national food CPI YoY (latest 2 months);
- world rice YoY.

HG uses the same grid and inner validation, depth ≤ 2, min child 15. It is evaluated on Balance Luzon quarters only.

**Selection rule (frozen).** The development set is target quarters ≤ 2024-Q4.
- Among U0, U1, U2 (each with the CH1 π_H), choose the lowest mean Brier on T43c over Leads 1–4 of development rows.
- Then keep HG only if, on development BL quarters, its Brier score for the hunger condition is lower than π_H's,
  averaged over Leads 1–4.
- Ties go to the simpler option (U0 < U1 < U2; π_H < HG).
- The chosen combination is **UNI-FINAL**.

## 4. Evaluation of UNI-FINAL (confirmatory)

- **Rows:** every (origin, lead), Leads 1…K, with eligible pooled training, π_H available, and a labelled target
  ≤ 2026-Q3. Longer leads may now have more evaluable quarters than CH1 had.
- **Baselines on every row:**
  - ALWAYS-LOW;
  - PERSIST-SI (same-information persistence);
  - CLIM (rate of T43c labels known at O(t));
  - CH1-LGBM (per-lead), on the rows it covers;
  - UNI-GOV, which is UNI-FINAL without the news columns (N1, G_pri_yoy, NG_gap_price).
- **Metrics and reliability:** the frozen R1–R7 of FINAL_THESIS_OBJECTIVES §7, per lead.
- **Horizons:**
  - maximum reliable lead: largest K with Leads 1…K all passing;
  - testable horizon: longest lead meeting R1;
  - every individually passing lead, reported as a diagnostic.
- **Also reported:**
  - the confirmation block (targets 2025-Q2 … 2026-Q3) separately;
  - quarter-level sign tests against ALWAYS-LOW and PERSIST-SI;
  - hunger-surge quarters;
  - the hunger condition alone (quarter-level accuracy against the latest-reading persistence).
- **News:** UNI-FINAL vs UNI-GOV, Brier difference by quarter-cluster bootstrap, Holm across leads. News "helps" only
  if significantly lower Brier (Holm p < 0.05).

## 5. What will be served

- **UNI-FINAL replaces CH1-LGBM** on the dashboard only if two conditions hold:
  - its maximum reliable lead is at least CH1's (1);
  - at Lead 1 it is not worse than CH1 by Brier (one-sided p < 0.10 for worse).
- Otherwise CH1 stays served and UNI-FINAL is reported.

Either way the dashboard states the generated, testable and reliable horizons separately.

## 6. Leakage audit before scoring

At 6 origins the UNI-FINAL forecasts must be unchanged when everything published on or after O(t) is randomised:
- SWS rounds;
- CPI months > m0;
- news items;
- Pink Sheet months > m0.
