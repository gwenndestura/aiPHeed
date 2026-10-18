# E58: detecting rising food stress (one improvement cycle)

**Date:** 2026-10-18. **Branch:** `e46-lead2-policy`, not pushed.

**Procedure**
- The protocol (`PROTOCOL.md`) was frozen at cbcf4af, after the diagnosis and before any candidate was scored.
- Forecasts were sealed at 6299924 and scored at 05d16ad; the repeat run is identical.
- Evaluation rows: the 50 E57 rolling-origin rows, two quarters ahead, using as-of data.
- **Evidence status:** these 10 quarters were examined before. The diagnosis used their outcomes, and the improvement was designed from it. **This is development evidence, not independent validation.**

## 1. Answer

**Yes, but on narrow evidence.**

| Rule | Onset recall | HIGH recall | Accuracy | Balanced |
|---|---|---|---|---|
| **E58 two-signal early warning (EW)** | **7 of 10 (0.70)** | 0.778 | 0.78 | 0.78 |
| E56 | 3 of 10 (0.30) | 0.556 | 0.72 | 0.684 |

- EW passes all six pre-registered acceptance criteria. It is adopted for **experimental** use: `AIPHEED_LEAD2_MODEL=e58`. Production stays E38.

**The improvement rests on a single episode:**
- EW and E56 make **identical decisions in 9 of the 10 quarters**.
- All the gain comes from **2024-Q2**: one regional hunger jump, 4 onsets.
- The onset-recall interval is **0.2–1.0**.
- A rule built only on the CPI projection, with no LightGBM, does almost as well (onset recall 0.70, accuracy 0.74).

**What the gain shows:**
- The improvement is a **decision-rule correction for stale hunger data**, not better learning.
- The price-driven misses are unchanged.
- The rising-food-price recall barely moves (0.33 → 0.39).

**What the available data cannot establish:**
- that aiPHeed detects rising food stress reliably;
- how often EMERGING warnings would be false alarms in a period when hunger is low.

## 2. Why E56 missed rising food stress (`tables/diagnosis_rows.csv`, `diagnosis_summary.json`)

E56 missed 8 of 18 HIGH rows and 7 of 10 onsets. The misses split into two causes.

| Cause | Misses | Evidence |
|---|---|---|
| **Stale hunger reading** | 4: Cavite, Laguna, Quezon, Batangas in 2024-Q2, all onsets | The price part was right (P_price 0.81–0.96). The hunger part said 0.21: at the issue date (2024-01-01) the latest SWS round posted was 2023-Q3 (10.3%). The 2023-Q4 round (14.3%) was posted 2024-01-22, and hunger reached 19.6% in 2024-Q2. Hunger data are **3–4 quarters older than the target**. |
| **Price part missed** | 4: Cavite and Laguna in 2024-Q4 (P_price 0.11–0.13), Batangas 2025-Q1 (0.45), Cavite 2026-Q2 | For the 2024-Q4 cases, food inflation and the food-minus-headline gap rose above threshold after momentum had been negative (mom3 −1.5). The projection under-shot by 2.3 points on average in missed rows, against 1.7 in hits. Cavite 2026-Q2 was a knife-edge case: 4.73 against a 4.71 threshold. **CPI information is 7 months older than the end of the target quarter.** |

**Factors that did not explain the misses:**

| Factor | Finding |
|---|---|
| Thresholds / class imbalance | Only 1 of 8 misses had P(HIGH) in 0.33–0.5. 6 had P < 0.2. Lowering the threshold (C1) or class-weighting (C3) does not help (section 4). |
| Rice prices | Wholesale rice YoY was high in misses (mean 15%) **and** in hits (13%). It does not separate them. |
| Climate | Typhoon counts at issue were similar (0.9 vs 1.3). The 2024-Q4 typhoons occurred **after** the issue date (2024-07-01). |
| Fisheries | Fish production was weaker before misses (−20% vs −5% YoY), but on 8 rows this cannot be distinguished from chance. |
| Employment, remittances | Similar values in misses and hits. Remittances were complete at all evaluated origins. |
| News coverage | Article counts were similar (29 vs 26). No group was "insufficient data" in a missed row. |
| Poverty | Not selected at the missed origins. It is static, so it cannot signal a change. |

**Conclusion from the diagnosis:**
- Half the misses are a **data-timing** problem (hunger), which a decision rule can partly address.
- The other half are **unforecastable price surges** given 7-month-old CPI. No model change on this data can be shown to fix them.

## 3. Events (fixed before scoring; `PROTOCOL.md` section 2)

| Event | Meaning | Count (50 rows) |
|---|---|---|
| HIGH | future high risk (T43 HIGH at the target) | 18 |
| **ONSET** | emerging high risk: HIGH at the target, while the latest known label at issue was LOW | 10 (2024-Q2: 4, 2024-Q4: 3, 2025-Q2: 2, 2026-Q2: 1) |
| RISEP | rising food-price stress: food or gap YoY ≥ 1.0 point above the latest known CPI quarter (BSP band half-width). A **price proxy, not confirmed hunger.** | 18 |

**Two further distinctions:**
- **High level:** the latest known label (persistence).
- **Emerging warning:** the system's output.

**Dependence:** the 10 onsets fall in 4 quarters; one regional hunger change produced four of them.

## 4. Results (identical 50 rows; `tables/rules_comparison.csv`)

| Rule | Acc | Bal | HIGH rec | HIGH prec | FN | FP | FP rate | Brier | Onset recall | New-warning precision | RISEP rec |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **EW (E58)** | **0.78** | **0.78** | **0.778** | 0.667 | **4** | 7 | 0.22 | **0.182** | **0.70** | 0.58 | 0.39 |
| E56 | 0.72 | 0.684 | 0.556 | 0.625 | 8 | 6 | 0.19 | 0.214 | 0.30 | 0.43 | 0.33 |
| C1 cost threshold (P(HIGH) ≥ 1/3) | 0.64 | 0.634 | 0.611 | 0.50 | 7 | 11 | 0.34 | 0.214 | 0.30 | 0.33 | 0.39 |
| C2 training-selected threshold | 0.62 | 0.667 | 0.833 | 0.484 | 3 | 16 | 0.50 | 0.182 | 0.70 | 0.44 | 0.61 |
| C3 class-weighted LightGBM | 0.72 | 0.660 | 0.444 | 0.667 | 10 | 4 | 0.13 | 0.209 | 0.30 | 0.50 | 0.28 |
| C4 two-stage (rising-price LightGBM) | 0.64 | 0.622 | 0.556 | 0.50 | 8 | 10 | 0.31 | 0.214 | 0.30 | 0.27 | 0.50 |
| Projection only (no LightGBM) | 0.74 | 0.748 | 0.778 | 0.609 | 4 | 9 | 0.28 | 0.188 | 0.70 | 0.64 | 0.39 |
| Recent-rise momentum rule | 0.64 | 0.585 | 0.389 | 0.50 | 11 | 7 | 0.22 | – | 0.30 | 0.50 | 0.28 |
| Persistence | 0.56 | 0.535 | 0.444 | 0.40 | 10 | 12 | 0.38 | 0.440 | **0.00** | – | 0.28 |
| Training majority / climatology | 0.64 | 0.500 | 0 | – | 18 | 0 | 0 | 0.304 | 0.00 | – | 0 |
| Always warn | 0.36 | 0.500 | 1.0 | 0.36 | 0 | 32 | 1.0 | 0.640 | 1.00 | 0.33 | 1.0 |

**Acceptance for EW** (all six pass):

| Criterion | Result |
|---|---|
| W1 onset recall ≥ 0.60 and ≥ E56 + 0.20 | 0.70 vs 0.30 |
| W2 HIGH recall ≥ 0.70 | 0.778 |
| W3 balanced accuracy ≥ E56 | 0.78 vs 0.684 |
| W4 accuracy ≥ 0.75 | 0.78 |
| W5 FP rate ≤ 0.30 | 0.22 |
| W6 ≥ every simple baseline | holds; ties the projection rule on onset recall |

**Uncertainty** (quarter-cluster bootstrap):

| Measure | 95% interval |
|---|---|
| EW onset recall | 0.20–1.00 |
| EW HIGH recall | 0.54–1.00 |
| EW accuracy | 0.70–0.86 |
| E56 onset recall | 0.00–0.82 |

**Missed onsets under EW:** Cavite 2024-Q4, Laguna 2024-Q4, Cavite 2026-Q2. All three are price-part misses.

**The other candidates do not help:**
- C2 raises recall only by flagging half of all LOW rows.
- C3 lowers recall.
- C4: the rising-price classifier adds false alarms, not onsets.

## 5. Quarter by quarter (`tables/quarter_by_quarter.csv`)

EW and E56 differ **only** in 2024-Q2.

| Target (issued) | HIGH | Onsets | EW warnings | EW TP/FP/FN | EW acc | E56 acc | Onsets warned: EW / E56 |
|---|---|---|---|---|---|---|---|
| 2024-Q2 (2023-Q4) | 4 | 4 | 5 (all EMERGING) | 4/1/0 | **0.8** | 0.2 | **4 / 0** |
| 2024-Q3 | 1 | 0 | 3 | 1/2/0 | 0.6 | 0.6 | – |
| 2024-Q4 | 3 | 3 | 1 | 1/0/2 | 0.6 | 0.6 | 1 / 1 |
| 2025-Q1 | 4 | 0 | 3 | 3/0/1 | 0.8 | 0.8 | – |
| 2025-Q2 | 3 | 2 | 4 | 3/1/0 | 0.8 | 0.8 | 2 / 2 |
| 2025-Q3 | 2 | 0 | 4 | 2/2/0 | 0.6 | 0.6 | – |
| 2025-Q4 | 0 | 0 | 0 | 0/0/0 | 1.0 | 1.0 | – |
| 2026-Q1 | 0 | 0 | 0 | 0/0/0 | 1.0 | 1.0 | – |
| 2026-Q2 | 1 | 1 | 0 | 0/0/1 | 0.8 | 0.8 | 0 / 0 |
| 2026-Q3 | 0 | 0 | 1 | 0/1/0 | 0.8 | 0.8 | – |

## 6. Province early-warning table (`tables/province_early_warning.csv`)

| Province | HIGH | Onsets | EW warnings | EW recall / precision | Onsets warned: EW / E56 | EW acc | E56 acc |
|---|---|---|---|---|---|---|---|
| Quezon | 6 | 2 | 7 | 1.00 / 0.86 | 2 / 1 | 0.9 | 0.8 |
| Laguna | 5 | 3 | 5 | 0.80 / 0.80 | 2 / 1 | 0.8 | 0.7 |
| Batangas | 3 | 2 | 3 | 0.67 / 0.67 | 2 / 1 | 0.8 | 0.7 |
| Cavite | 4 | 3 | 5 | 0.50 / 0.40 | **1 / 0** | **0.5** | 0.4 |
| Rizal | 0 | 0 | 1 | – / 0.00 | – | 0.9 | 1.0 |

**Sample sizes:** each province has 10 rows and 0–3 onsets. Province figures are descriptive only.

**Cavite** remains the weakest case: two of its three onsets were price surges the model did not see.

## 7. Cost in a low-hunger period (cannot be measured on the test rows)

- In every test quarter hunger was above 11.3%, so price-pressure warnings rarely conflicted with the hunger condition.
- **In 2021–2023, 24 of the 29 province-quarters with food-price pressure were not T43 HIGH**, because hunger was at or below 11.3%.
- In such a period EMERGING warnings would mostly not become HIGH food-insecurity risk.
- For this reason the level is labelled **EMERGING (price pressure; hunger not confirmed)**, distinct from **ALERT**.

## 8. Implementation

**Rule:** EW uses E56's own LightGBM price-pressure probability. No model is retrained.

| Level | Condition |
|---|---|
| ALERT | P(HIGH) ≥ 0.5 |
| EMERGING | P_price ≥ 0.5 and P(HIGH) < 0.5 |
| NONE | otherwise |

**Direction:** rising, steady or easing, relative to the latest label known at issue.

**Serving** (`AIPHEED_LEAD2_MODEL=e58`):
- `scripts/build_record_e58.py` → `data/e58/e58_record.json`. It is the E56 record (probabilities, TreeSHAP, freshness, artifacts unchanged) plus an `earlyWarning` block per province and quarter.
- `e41_lead2.early_warning()`;
- `dashboard.plain_summary` appends the warning text, and the API returns an `earlyWarning` list (`EarlyWarning` schema);
- E58 explanation note.
- No frontend design change. E38 stays the production default; E56 stays available.

**Tests:**

| Suite | Result |
|---|---|
| E58 experiment (`tests/test_e58.py`) | 6 passed: protocol and seal hashes; event alignment (target = t+2, onset definition); latest known label posted before the issue date; RISEP/recent-rise inputs use only published CPI; sealed E56 values equal E57's; warning flags reproducible |
| Serving (`backend/tests/integration/test_e58_early_warning.py`) | 4 passed: probabilities unchanged, levels follow the rule, as-of direction, the 2024-Q2 EMERGING case, 2027-Q1 no warning, default E38 |
| Backend full | **402 passed, 18 skipped** |
| Frontend | tsc clean, 45 vitest |

## 9. Dashboard review (`tables/dashboard_review.json`; live API on port 8003 with `e58`, approved frontend on 8083)

The warning appears in the existing plain-summary line under the factor bars (`RightAnalyticsPanel`, `data-testid="plain-summary"`).

**Q1 2027 (current target), as rendered:** "…in CALABARZON for 2027-Q1 is forecast LOW (8% probability), mainly because Market / Prices lowered it and Employment lowered it. No province has an early warning for this quarter. Data: limited (…OFW Remittance.)"

**2024-Q2, Quezon (backtest; the approved timeline shows only Q1 2026–Q1 2027, so this is the API text the same panel renders):** "…was LOW (20% probability; observed HIGH)… Early warning EMERGING: food-price pressure is likely (96%) although the forecast of HIGH food-insecurity risk is 20%; the latest regional hunger reading (10.3% in 2023-Q3) is at or below 11.3%, so the hunger condition is not yet confirmed. Risk is rising from the latest observed LOW (2023-Q3). Model warning for DA review and planning; not an official classification."

**2024-Q2, region:** "Early warnings: Cavite EMERGING (rising); Laguna EMERGING (rising); Quezon EMERGING (rising); Rizal EMERGING (rising); Batangas EMERGING (rising)." Rizal's warning was a false alarm.

**What DA sees:**
- the warning level and direction;
- both probabilities;
- the target quarter;
- the latest hunger reading with its quarter (data freshness);
- the top factor groups;
- the data status.

**Map colours** still follow P(HIGH) (approved design). An EMERGING warning therefore shows on a LOW-coloured province **only in text**. Making warnings visible on the map would be a design change for your approval.

## 10. Recommendation

| Use | Recommendation |
|---|---|
| Experimental use and historical early-warning demonstration | **Suitable.** EW keeps E56's forecast, adds an explicit EMERGING level that would have warned of the 2024 hunger surge, and states its uncertainty and data age. |
| Production deployment | **Not yet.** |

**Why not production:**
- The gain rests on one episode.
- The price-driven misses remain.
- False-alarm behaviour in a low-hunger period is untested on outcomes.
- The adviser has not approved T43 or the EMERGING level.

**What would establish it:**
1. Score the frozen 2027 forecasts and their EW levels quarter by quarter.
2. **Issue the forecast after each quarter's SWS release** (an issue-time decision), so the hunger data are one quarter fresher.
3. **Obtain a provincial food-insecurity outcome** (CBMS or provincial FIES), so that rising stress can be measured directly, not through a regional hunger series plus prices.

## 11. Files

**Experiment** (`E58_Rising_Stress_Early_Warning/`):
- `PROTOCOL.md`, this report, `CHAPTER_IV_EARLY_WARNING.md`;
- `runner/`: diagnose, event_counts, predict, score, preview launcher;
- `sealed/`, `runs/` (run and repeat), `tables/`, `data/events.csv`, `tests/`.

**Backend:**
- `scripts/build_record_e58.py`, `data/e58/e58_record.json`;
- `app/ml/inference/e41_lead2.py`, `app/services/dashboard.py`, `app/api/v1/insights.py`, `app/schemas/public.py`;
- `tests/integration/test_e58_early_warning.py`.

**Commits:** cbcf4af, 6299924, 05d16ad, and the report commit. Not pushed.

**Left uncommitted on purpose:** another session's E46 D-1 edits.
