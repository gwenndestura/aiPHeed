# E58 protocol: early detection of rising food stress (one improvement cycle; frozen before any candidate is scored)

**Written:** 2026-10-18 on branch `e46-lead2-policy` after E57 (8e547fa).
**Freeze:** the SHA-256 (LF) of this file is in `runner/PROTOCOL_SHA256.txt`, committed before the prediction step. Predictions are sealed before scoring (as in E57). One run, then a byte-identical repeat. No further cycle.

## 0. Evidence status (read first)

**The test rows are the 50 E57 rows** (targets 2024-Q2..2026-Q3). They are the only quarters the data support, and they were examined in E43–E57.

**The diagnosis (`tables/diagnosis_rows.csv`) looked at E56's outcomes on these rows**, including the price-part probabilities of the missed rows. The primary candidate below was chosen *because of* that diagnosis, so its result on these rows is partly anticipated.

**E58 is therefore development evidence** that a design change addresses a diagnosed failure. It is not independent validation. The independent test is the frozen 2027 forecasts.

## 1. Diagnosis summary (completed before freezing; `runner/e58_diagnose.py`)

**Misses:** E56 missed 8 of 18 HIGH rows and 7 of 10 onset events.

| Cause | Misses | Detail |
|---|---|---|
| **(a) Stale hunger reading** | 4 (2024-Q2, all onsets) | P_price was 0.81–0.96: the price part was right. The hunger part was 0.21. At 2024-01-01 the only SWS round posted was 2023-Q3 (10.3%); the 2023-Q4 round (14.3%) was posted 2024-01-22, and hunger reached 19.6% in 2024-Q2. Hunger data are 3–4 quarters old relative to the target. **A model change cannot recover hunger information that was not yet published; a decision-rule change can stop a stale reading from suppressing a price warning.** |
| **(b) Price part missed** | 4: 2024-Q4 Cavite and Laguna (P_price 0.11–0.13; food-minus-headline gap rose above threshold after negative momentum), 2025-Q1 Batangas (0.45), 2026-Q2 Cavite (food YoY 4.73 vs threshold 4.71) | The CPI information is 7 months older than the end of the target quarter. |

**Threshold lowering alone recovers almost nothing:** 6 of 8 missed rows had P(HIGH) < 0.2.

**No single trigger group separates misses from hits** (mean feature table in `tables/diagnosis_summary.json`). The rice wholesale YoY was high in both missed and correctly caught rows.

## 2. Events (definitions fixed here; counts are label-only, `tables/event_counts.json`)

Unit: province × target quarter (two quarters after the predictor quarter), on the 50 E57 rows.

| Event | Definition | Count (50 rows) |
|---|---|---|
| **HIGH** (future high risk) | T43 HIGH at the target (E55 PROTOCOL section 2) | 18 |
| **ONSET** (emerging HIGH risk; primary "rising" event) | HIGH at the target **and** the province's latest T43 label known at the issue date was LOW | 10 (2024-Q2: 4, 2024-Q4: 3, 2025-Q2: 2, 2026-Q2: 1) |
| **RISEP** (rising food-price stress; a price proxy, **not** confirmed hunger) | target-quarter food YoY, or food-minus-headline YoY, at least **1.0 point** above the latest complete CPI quarter known at the issue date | 18 |

**Why 1.0 point:** it is the half-width of the BSP inflation target band (3 ± 1%), a documented constant, not chosen from results.

**Further distinctions:**
- **High level:** the latest known label (persistence) is reported as context.
- **Emerging warning:** the system's output (section 3). It is not an outcome.
- **Regional hunger rising** (target H − latest known H) is reported descriptively. With one regional series it is not a provincial event.

**Dependence:** onsets cluster in quarters (one regional hunger jump gave 4 onsets in 2024-Q2). About 4 independent episodes exist, so every onset statistic is reported with this caveat, and quarter-cluster intervals are used.

## 3. Candidates (identical rows, two-quarter horizon, as-of data, sealed before scoring)

All E56 quantities come from the sealed E57 forecasts (`E57/sealed/predictions.csv`), which equal the committed E56 predictions.

| ID | Warning rule | Basis |
|---|---|---|
| **C0 E56** | P(HIGH) ≥ 0.5 | existing model |
| **EW (PRIMARY): E58 two-signal early warning** | **warn when E56's LightGBM price-pressure probability P_price ≥ 0.5**. Whether the latest hunger reading is above the threshold is reported alongside but **does not suppress** the warning. Alert levels: ALERT if P(HIGH) ≥ 0.5; EMERGING if P_price ≥ 0.5 and P(HIGH) < 0.5; NONE otherwise. | diagnosis (a): the hunger reading is 3–4 quarters stale at the target; same E56 model, no refit |
| C1 cost-sensitive threshold | P(HIGH) ≥ 1/3: a miss costs twice a false alarm, which equals the dashboard's existing Watch band | decision theory, fixed constant |
| C2 training-selected threshold | P_price ≥ τ(t). τ(t) ∈ {0.20, 0.25, …, 0.50} maximizes F2 (recall-weighted) of the price part's inner forward-chaining out-of-fold probabilities against the as-of PS training labels, using the configuration E56 selected at that origin. Ties go to the higher τ. | training data only |
| C3 class-weighted LightGBM | E56 nested selection restricted to the configurations with balanced class weights; P(HIGH) ≥ 0.5 | cost-sensitive learning |
| C4 two-stage with a rising-price classifier | Stage 1: a LightGBM classifier of RISEP trained on the as-of RISEP labels of training targets ≤ t−1 (2 leaves, 40 trees, learning rate 0.05, min_child 10, L2 10, seed 58). Features: E56's price inputs plus the projected changes (base_0.0 − F_now, gbase_0.0 − gap_now). Warn when P(HIGH) ≥ 0.5 **or** P_rise ≥ 0.5. | requested two-stage design (an ONSET classifier is infeasible: 0–12 training onsets) |

**Simple baselines:**

| Baseline | Rule |
|---|---|
| B-PERSIST | latest known T43 label (never warns of an onset by construction) |
| B-CLIM | as-of HIGH share ≥ 0.5 (never fires in this window) |
| B-HIGH | always warn |
| B-RECENT-RISE | warn when the latest complete CPI quarter known at issue shows food YoY or gap ≥ 1.0 point above the quarter before it (momentum rule) |
| B-PROJ | warn when the structural base-effect projection probability (m = 1.0, scale from training rows) is ≥ 0.5: projection only, no LightGBM |

## 4. Metrics (per rule; ONSET, RISEP and HIGH)

**Against HIGH:**
- recall, precision, FN and FP counts, FN and FP rates;
- accuracy, balanced accuracy;
- Brier and AUC of the rule's probability (C0, C1, C3: P(HIGH); EW, C2: P_price; C4: max(P(HIGH), P_rise); B-PROJ: the projection probability).

**ONSET:**
- recall (onsets warned);
- missed onsets, listed;
- precision of **new warnings** (warnings where the latest known label was LOW that became HIGH).

**RISEP:** recall and precision of warnings. P_rise is reported for C4.

**Breakdowns:** per target quarter, per province, quarter-cluster bootstrap CIs (2000 draws, seed 58).

**Hunger regime.** In every test quarter the hunger condition was met, so on these rows T43 = PS. The cost of EW in a low-hunger regime cannot be measured on the test rows. It is **estimated from 2021–2023 labels:** the share of province-quarters with PS HIGH but T43 LOW (price warnings that would not have been T43 HIGH).

## 5. Acceptance criteria for EW (all must hold on the 50 rows)

| ID | Criterion |
|---|---|
| W1 | ONSET recall ≥ 0.60 **and** ≥ E56's ONSET recall + 0.20 |
| W2 | HIGH recall ≥ 0.70 |
| W3 | balanced accuracy (vs HIGH) ≥ E56's |
| W4 | accuracy (vs HIGH) ≥ 0.75 (the goal) |
| W5 | false-positive rate ≤ 0.30 |
| W6 | ONSET recall and balanced accuracy ≥ every simple baseline's (B-PERSIST, B-CLIM, B-RECENT-RISE, B-PROJ; B-HIGH is exempt from the onset-recall part) |

**Decision:**
- **EW is adopted for experimental early-warning use only if W1–W6 all hold.** Any failure is reported as such.
- C1–C4 are comparisons. None replaces EW unless it **also** meets W1–W6 **and** EW does not. If several do, the simplest is preferred, in this order: C1, C2, C3, C4.

## 6. Serving (if adopted)

The `e58` record is the E56 record plus, per province and quarter:
- an `earlyWarning` block: level (ALERT / EMERGING / NONE), P_price, P(HIGH), the latest known hunger and its quarter, and the direction relative to the latest known label (rising / steady / easing);
- a plain-language warning sentence in the existing summary.

**Unchanged:**
- no new frontend design; colours and bands stay as approved;
- E38 remains the default; E56 stays available;
- an alert is a model warning for DA review, never an official classification.

## 7. Not allowed

- Changing events, thresholds, rows, candidates or criteria after freezing.
- Additional candidates or cycles.
- Data beyond 2026-10-14; pre-2021 data.
