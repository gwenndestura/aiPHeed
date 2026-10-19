# E65 protocol: the 2026-Q4 / 2027-Q1 risk drop under the 2026–27 El Niño

Frozen 2026-10-19, before any E65 arm is scored. SHA-256 (LF line endings) in `runner/PROTOCOL_SHA256.txt`.

## 1. Question and status of the evidence

- **Question:** E56/E58, the two-quarter-ahead experimental model, gives LOW for 2026-Q4 and 2027-Q1. PAGASA reports a strong to very strong El Niño. Is the low forecast supported, and does the model take account of the approaching climate threat?
- **Evidence status:** every outcome in the 50 evaluation rows (targets 2024-Q2..2026-Q3) was seen by E56–E62. The climate variants below are also designed with knowledge that El Niño occurred in 2023–24 and is occurring in 2026. **All E65 comparisons are development evidence only.** No arm is served, sealed, or presented as validated.
- **Protected artifacts:** E38 and E56–E62 artifacts, sealed files and records are only read. The sealed E57/E58 files are hash-verified before use. Historical outcomes are recomputed, never edited.

## 2. Trace (descriptive, no model choice)

For each province, three forecasts are traced from raw inputs to the dashboard:
- target 2026-Q3 (origin t = 2026-Q1, issued 2026-04-01; a back-test);
- target 2026-Q4 (t = 2026-Q2, issued 2026-07-01);
- target 2027-Q1 (t = 2026-Q3, issued 2026-10-01).

The trace covers:
- raw CPI and SWS inputs;
- features;
- the hunger part: ridge per-feature terms, H_hat, P_hunger;
- the price part: structural CPI offset, per-feature TreeSHAP, P_price;
- P;
- the dashboard values.

Changes between consecutive forecasts are decomposed two ways:
1. **Across origins** (each origin's own model): Δlog P = Δlog P_hunger + Δlog P_price. Δlogit P_price is split into the offset, the tree constant, and per-feature tree terms.
2. **Fixed model** (the later origin's fitted model): the later and earlier input rows are compared by exact Shapley values over input blocks (CPI/market, climate, fish, employment, OFW/FX, news, policy, hunger base). This gives the input effect with the model held fixed. The remainder of the total change is the model/configuration effect.

## 3. Climate audit (descriptive)

For each climate input, at each of the three origins, the audit reports:
- value and source;
- observation period and publication timing;
- availability at the issue date;
- observed versus forecast;
- missing handling;
- whether the input reaches the model (tree splits, ridge coefficient);
- its contribution;
- its spatial level.

The PAGASA ENSO status at each issue date comes from `sources/SOURCES.md`. Only items issued before the issue date count as available; later items are labelled context.

## 4. Controlled rolling-origin comparison

**Common rules for all arms:**
- Same 10 E57 origins (t = 2023-Q4..2026-Q1).
- Same 50 rows and labels (E58 `events.csv`, T43).
- Same issue-date rule: E56 `tuned_forecast`, the 72-configuration search and nested selection, unchanged.
- No other change and no re-tuning.

**Arms:**

| Arm | Definition |
|---|---|
| A | Frozen E56: the sealed E57 `E56_p`. Re-running arm A through the E65 harness must reproduce it to ≤ 1e-6, or E65 stops. |
| B1 | Climate *corrected*. The binary ENSO phase codes `enso`, `enso_l2` (and `enso_x_mom`) are replaced by the **signed CPC intensity class** of the same quarters: t−1 and t−2, La Niña −1..−4, El Niño +1..+4, from the same `pagasa_climate.parquet`. Same timing, so nothing becomes available earlier than in A. Used in both the price and hunger parts. |
| B3 | Climate *added*. A plus `pagasa_enso`: the PAGASA ENSO Alert and Warning System status in force on the issue date O(t), coded El Niño Advisory +2, Alert +1, Watch +0.5, none 0, La Niña Watch −0.5, Alert −1, Advisory −2. Used in both parts. This is official forward-looking information dated before O(t). |
| B2 | B1 and B3 together. |
| C | Ablation. All climate inputs are removed from both parts: `tc_count`, `tc_count_l1`, `enso`, `enso_l2`, `palay_yoy`, `corn_yoy`, `enso_x_mom`, `tcl1_x_palay` and `news_climate`. |
| D1 | Transparent climate rule: HIGH iff a PAGASA El Niño Alert or Advisory is in force on the issue date (status ≥ +1). P = 1 or 0. |
| D2 | Transparent food-price baseline: the sealed structural CPI projection-only probability `BPROJ_p` (E58 sealed). |
| Baselines | Persistence (`PERSIST_p`) and as-of majority (`MAJORITY_p`) from the sealed E57 file. |

**Metrics:**
- n rows and quarters;
- accuracy;
- balanced accuracy;
- HIGH recall;
- false alarms (FP) and missed HIGH (FN);
- Brier (hard 0/1 for D1 and the baselines);
- onset recall (E58 `ONSET` rows) and rising-risk recall (`RISEP` rows).
- Decision threshold: 0.5.

**Decision rule** (the same as E63). An arm *improves on A* only if both hold:
- the paired Brier difference (arm − A) has a quarter-cluster bootstrap 95% CI entirely below 0 (2,000 draws, seed 65);
- the quarter-level sign test of Brier wins over A has p < 0.05.

Otherwise the result is reported as **no supported difference**. Accuracy gains without this are reported only as descriptive. No arm is adopted or served by E65 in any case.

**Forward forecasts.** Arms A, B1, B2, B3 and C are also run at t = 2026-Q2 and 2026-Q3 (targets 2026-Q4 and 2027-Q1). They are reported as exploratory what-if values. They are not sealed, not served, and do not replace the frozen forecasts.

**Information-cutoff limits disclosed in advance:**
- ONI values are from the 2026-09-09 vintage for all quarters; past vintages are not reproducible.
- The PAGASA status for 2022-04-01..2023-01-01 is inferred continuity.
- No PAGASA rainfall or drought outlook series exists in the pipeline for 2021–2026. Provincial rainfall (`province_rainfall.parquet`) holds pre-2021 rows and is not loaded.

## 5. Target check (descriptive)

On all labelled province-quarters 2021-Q1..2026-Q3, from the E62 independent label table, the check reports how often T43 is LOW while each of the following holds:
- regional hunger is above 11.3%;
- the ENSO phase is El Niño (same or previous quarter);
- the PAGASA status is El Niño Alert or Advisory;
- provincial palay or corn production fell year on year.

It also reports how often the T43 label equals the price-pressure condition alone.

Labels and thresholds are not changed. An exploratory climate-related indicator may be proposed under a separate name. It is not used as a target here.

## 6. Dashboard

Only backend text fields that the approved components already render are changed (`summary.sentence`, trigger `evidenceNote` / `statusNote`). No UI element, colour or legend changes. The horizon stays at two quarters. The production default (E38) is not switched.
