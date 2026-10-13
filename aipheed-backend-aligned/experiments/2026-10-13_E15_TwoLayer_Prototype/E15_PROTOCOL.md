# E15 Protocol: Two-Layer Prototype and Prospective Validation Protocol

**Written:** 2026-10-13, before any E15 code, output or calculation.

**Folder name.** No E14 folder exists. The brief names this experiment E15, and the name is unused, so it is kept.

## 1. Scope

| In scope | Out of scope |
|---|---|
| A **development-only** two-layer output: a regional hunger layer, a provincial relative food-price-pressure layer, and a secondary legacy S1 layer, built from eligible 2021–2025 data | A new model search, new formulas, weights or thresholds |
| A JSON Schema, a CSV layout and a static mock report | Wiring to the production API, the dashboard or the frontend |
| Synthetic tests | Running any test on 2026 data |
| A **prospective validation protocol**, frozen and hashed now, to be evaluated later under a separately approved procedure | Running that evaluation |
| A data-gap inventory from project records and code | Fetching data or opening protected files |

## 2. Safety rules

- **Writes:** only inside `experiments/2026-10-13_E15_TwoLayer_Prototype/`.
- **Read-only:** E9–E13 and everything else. No commit, push, deploy, Git-history rewrite or scheduled-task change.
- **Inputs:** an explicit, hash-pinned allowlist enforced by `runner/guard.py` (the E13 guard pattern).
  - **The data files:**
    - E12 `realized_components_2021_2025.csv`
    - E12 `details.json`
    - E13 `metrics.json` and `scored_rows.csv`, read only to size the prospective protocol
  - **All four contain only 2021–2025 quarters.**
  - **Runtime assertion:** every quarter label in every loaded row or record is ≤ 2025-Q4, or the run stops.
- **No protected 2026 file, cache, log or derived value is opened.** The data-gap inventory uses only code docstrings and project documents.

## 3. Prototype rules (taken from the brief; nothing added)

### Regional layer

One record per quarter:

- **Fields:** the SWS Balance-Luzon hunger level, scope `"Balance Luzon"`, the rounds with their publication dates and source flags, and the change against the prior quarter that has a value. When that quarter is not the calendar-previous one, the gap is recorded.
- **The level** is the mean of all eligible rounds in the quarter. This matches the regional series used in E12 and E13.
- **Never repeated per province.**

### Provincial layer

For each quarter:

- **F[p,t]** for each province.
- **D[p,t] = F[p,t] − the unweighted mean of the five F**, only when all five F exist. Otherwise D and the rank are `null`, with the reason given. No value is imputed and none is set to 0.

**Rank:** 1 is the highest D, and the label is "relative food-price pressure".

**Tie rule:** D values that are equal after rounding to 9 decimals share the lowest rank of the tied group (competition ranking: 1, 2, 2, 4). Tied provinces are listed alphabetically.

### Legacy layer

- **S1 = H_A + 2D**, where H_A is the mean of the production-series (`definition_A`) rounds. That is how S1 was defined in E9–E13.
- **HIGH if S1 > τ0 (strictly), else LOW.**
- **τ0 = 10.84335**, the recorded and served value, displayed as 10.843. A runtime check confirms that the thresholds 10.843, 10.8433333 and 10.84335 give identical labels on all 80 eligible rows. If they did not, the run would stop and report it.
- **Label:** "legacy composite, not validated as food insecurity". It is placed after the two primary layers.
- **When there is no production round in the quarter** (2025-Q2, 2025-Q3), S1 is `null`, with the reason given.

### Caveats

The output always carries the five required caveats.

### Wording rule

- **Banned:** no field name or string value may contain "food insecure" (as an adjective) or "risk".
- **Allowed:** the mandated legacy caveat may say "not validated as food insecurity".

## 4. Tests (synthetic fixtures only)

1. D sums to 0 for complete data.
2. A missing F gives no D and no rank for that quarter, and nothing is filled with 0.
3. The regional value appears once per quarter.
4. Ties follow the documented rule.
5. The legacy S1 equals H_A + 2D within 1e-9, and the label uses a strict ">".
6. The wording rule holds for every key and string in the output.
7. The output validates against `TWO_LAYER_SCHEMA.json`.
8. The guard denies protected, mixed and 2026 paths and writes outside E15.

**Runtime checks on the eligible data:**

- the legacy S1 reproduces E12's S1 within 1e-9;
- the threshold-equivalence check;
- the quarter ≤ 2025-Q4 assertion;
- schema validation of the real output.

## 5. Prospective validation protocol

`PROSPECTIVE_VALIDATION_PROTOCOL.md` is written after this file and **hashed before E15 produces any prototype output**.

- **Hypotheses:** H1 and H2 only, as given in the brief.
- **The shrinkage forecasts:** E13's already-defined arms `B2_ridge_D` (primary) and `B2_ridge_DP` (secondary). No new formula.
- **The minimum number of new quarters** is computed from E13's per-quarter results (2023-Q2..2025-Q4) and frozen.
- **No evaluation is run.**

## 6. Deliverables

1. `E15_PROTOCOL.md`
2. `TWO_LAYER_SCHEMA.md` and `TWO_LAYER_SCHEMA.json`
3. `TWO_LAYER_MOCK_REPORT.md`
4. `SYNTHETIC_TESTS.md` and the test code
5. `PROSPECTIVE_VALIDATION_PROTOCOL.md` and its hash
6. `DATA_GAP_INVENTORY.md`
7. `ADVISER_DECISION_BRIEF.md`
8. `INTEGRITY_REPORT.md`

Plus code, run outputs and `E15_FILES_SHA256.txt`.
