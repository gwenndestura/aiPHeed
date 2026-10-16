# E46 protocol: rice-policy price regimes and fragile-feature correction (frozen before any E46 score)

**Written:** 2026-10-17 on branch `e46-lead2-policy`, from `dc5c0f6`.
**Reproduction:** E44 I2 reproduces from code at three origins, with max |Δp| ≤ 1e-16 (`runner/e46_repro.py`).
**Freeze:** the SHA-256 of this file is in `runner/PROTOCOL_SHA256.txt`, committed before any E46 fit.
**Run rule:** run once, then a byte-identical repeat.

## 0. Evidence status: stated before any result

E46's design comes from the E45 error analysis of the **same** quarters it can be scored on:
- all 9 of I2's false positives fall in rice-policy price-shock periods;
- 4 of the false negatives come from the 2024-Q2 hunger surge.

So **any historical score of E46 on 2022–2026 is hindsight-informed development evidence. It cannot satisfy the 75% acceptance requirement**, however high it is.

The only valid acceptance evidence is **prospective**: quarters whose outcomes do not exist at the freeze (§5).

## 1. Rice-policy data (official, dated)

The events are in `data/rice_policy_events.csv`. Each row has its instrument, announcement date, effective period, a primary source (LawPhil or DA) and a secondary source.

| Event | What it did | Dates |
|---|---|---|
| EO 39 s.2023 | Rice price ceiling | 2023-09-05 to 2023-10-04 |
| EO 62 s.2024 | Rice tariff cut 35% → 15% | announced 2024-06-20; effective about 2024-07-06 |
| DA Department Circular 3 s.2025 | Food-security emergency; NFA stock release | 2025-02-03 to about 2025-07-31 |
| EO 93 s.2025 | Rice import suspension | 2025-09-01 to 2025-10-30 |
| EO 102 s.2025 | Extension of the suspension | announced 2025-10-30; to 2025-12-31 |

**Excluded, with the reason recorded:**
- **2025 MSRP steps for imported rice:** the start is known, but no verified end date.
- **EO 105's variable tariff from 2026:** no certified adjustment is known.

## 2. Policy features (as of O(t); national, so the same value for every province)

An event counts only if its **announcement date is before O(t)**. The target months are the three months of t+2.

| Feature | Definition |
|---|---|
| `tariff_yoy_regime` | Share of target months whose YoY compares a post-cut month with a pre-cut base (12 months after the EO 62 effective month) |
| `import_suspension_share` | Share of target months inside an announced suspension period |
| `price_ceiling_share` | Share of target months inside an announced ceiling period |
| `food_emergency_share` | Share of target months inside an announced emergency window |

**Rationale:** rice is the largest single item in the food CPI. Officially announced policy changes shift domestic rice prices on known dates, and that is information available at issuance.

## 3. Candidates (fixed now)

**I6 (primary):** E44 I2 plus the policy block in the food-price residual model. Everything else is identical:
- all five triggers in both components;
- the same grids, inner validation, threshold and Platt rules.

**I6b (fragility correction):** I6, except the hunger component drops the national employment and OFW features.
- E44 showed that masking employment moves p by about +0.2, and the series is province-invariant, i.e. a time-trend-like dependence.
- The price component keeps all five triggers, so the model as a whole still uses all five.

**I6-MKT:** market plus the policy block in the price component, with a random-walk hunger component. It measures how much the other triggers add.

**Comparators:** taken from E44 run 1 on the identical S44 rows (2024-Q3..2026-Q3, 7 quarters, 35 rows):
- I2 (current five-trigger candidate);
- B-maj, B-persist, B-clim, SIM-0, SIM-5T;
- E41-M1;
- E38-served.

## 4. Historical evaluation (hindsight-informed; reported, never used for acceptance)

- **Gates:** E44 A0–A4 on S44, plus the two windows (2024-Q2..2025-Q1 and 2025-Q4..2026-Q3).
- **Date-cluster bootstrap CIs.**
- **Quarter-level reporting:** results are also reported per quarter; there are 7 independent quarters, not 35 independent rows.

## 5. Prospective acceptance rule (the only route to "75% met")

- **Freeze now:** I6's and I6b's 2027-Q1 forecasts, from O = 2026-10-01, with configuration, threshold and features, in `frozen/E46_PROSPECTIVE_2027Q1.json` with a sha256.
- **At each later origin:** the same frozen procedure, unchanged, issues the next quarter's forecast.

**Acceptance is declared only when all of the following hold:**
- the first **4 prospective target quarters** (2027-Q1..2027-Q4; 20 province-quarters) have released outcomes;
- the primary (I6) has accuracy ≥ 0.75, balanced accuracy ≥ 0.70, HIGH recall ≥ 0.60 and LOW recall ≥ 0.60 (when both classes occur);
- its Brier score is better than always-LOW and persistence.

The threshold, calibration and features are those frozen at each origin. Nothing is selected on the outcomes.
