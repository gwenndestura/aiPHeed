# E122 corrections report

## V1: provincial CPI year-on-year for 2021 used a 2020 comparison base (corrected)

### Records

- **Count.** 40 province-quarter rows, of which:
  - `cpi_food_yoy_pct`: 20 (5 provinces × 2021-Q1..Q4);
  - `cpi_headline_yoy_pct`: 20.
- **Source.** `experiments/E40_SWS_CPI_Tiers/data_acquired/psa_cpi_yoy_headline_food_2021_2026.csv`, reference months 2021-01..2021-12.
- **Why they violate the cutoff.** These are PSA-published year-on-year changes. Every 2021 month is compared with the same month of 2020.

### Where they came from

| Stage | What happened |
|---|---|
| E119 `runner/preprocess.py` `build_series()` | Kept as "PSA-published 2021 YoY", a declared exception in the E119 protocol §2 and E120 methodology |
| E120 `load()` | Passed through |
| `firi3.validate_inputs` (v1) | Rejected only periods before 2021-Q1, so the rows were admitted |

### What they affected

- **FMA_food_cpi and FMA_headline_cpi**, in two ways:
  - as current values for the 2021 quarters;
  - as percentile reference values for every later quarter, through the expanding window.
- **Provincial FMA, and therefore the provincial FIRI3.**
- **Regional FIRI3: unaffected.** It uses the Region IV-A index, recomputed from 2021+ values.

### Correction (Amendment 1, `E122_FIRI3_PROTOCOL_AMENDMENT_1.md`, SHA-256 4fd05309…)

**What changed.** `firi3.validate_inputs` now admits a change-type series only from 2022-Q1. Change-type series are the year-on-year changes, drops, pp changes, declines and anomalies, which need a base inside the window.

**Where the rejection happens.** Earlier rows are rejected **before** scoring and normalization, so they cannot enter as current values or as reference values.

**Unchanged:** definitions, directions, normalization, aggregation, completeness rules, bands and weights.

### Effect (`out/e121_vs_amended.csv`)

| | Before (E121) | After (Amendment 1) |
|---|---|---|
| Computable provincial scores | 75 | 75 |
| Computable regional scores | 10 | 10 |
| Provincial scores changed | — | 73 of 75 |
| Mean \|change\| | — | 0.0032 |
| Max \|change\| | — | 0.0125 |
| Band changes | — | 0 |
| FMA_food_cpi / FMA_headline_cpi first observation used | 2021-Q1 | **2022-Q1** |
| … first scored origin | 2021-Q4 | **2022-Q4** |

The effect on the scores is small because the 2021 values were mostly early percentile references. The rule is fixed regardless of the size of the effect.

### Regression tests

`backend/tests/unit/test_e122_cutoff.py`:
- `test_2021_yoy_rejected_before_normalization`: extreme 2021 values cannot become references;
- `test_2021_change_rows_rejected`: every change-type series, parametrized over all 21;
- `test_level_series_keep_2021`.

### Records kept

- **E121 outputs and snapshots** are unchanged: they are the pre-amendment record.
- **Amended results** are in `out/firi3_amended_*.csv` and `snapshots/` (23 retrospective, write-once).

## C2: geography check order in `firi3.validate_inputs` (corrected)

**Problem.** The E122 tests found that an observation with an unknown provincial unit could be silently dropped by the date rules *before* the geography check ran, instead of stopping the run.

**Fix.** The geography check now runs first, on all rows. This is a code-order fix only; results are unchanged. All 23 snapshots verified unchanged after the fix.

## Not corrected (no cutoff violation; disclosed)

| Id | Item | Why no correction |
|---|---|---|
| W1 | FSSI intensities come from a general pretrained multilingual NLI model (zero-shot) | Model weights, not food-insecurity observations; no pre-2021 observation enters |
| W2 | News relevance rules were written on a development half of 2021–26 articles | Design-time wording; values still use only articles published before each issue |
| W3 | PSA SAE 2021 poverty is a model estimate using 2020-census auxiliary data | A published 2021 estimate, not a comparison computed by FIRI3 |
| W4 | All historical scores are retrospective reconstructions from inputs ingested in 2026-10; 30 of 34 features rest on release rules | No future observation enters; availability is provisional, not verified |

**DI-3 is not changed.** The annual EHS latest-year rule stays as frozen: a latest year without all five provinces is unavailable, with no fallback. It is not a cutoff issue, and changing it needs approval.
