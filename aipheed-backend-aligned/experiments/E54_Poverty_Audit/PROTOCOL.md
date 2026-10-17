# E54 protocol: does PSA poverty add predictive information to the aiPHeed forecasts? (frozen before any E54 score)

**Written:** 2026-10-17 on branch `e46-lead2-policy` at d215bf8.
**Freeze:** the SHA-256 of this file (LF line endings) is in `runner/PROTOCOL_SHA256.txt` and is committed before the run. The run happens once, then a byte-identical repeat. Any change after freezing is logged in `DEVIATIONS.md`.
**Audit:** `AUDIT.md` (written first) found poverty in no model's feature matrix. This protocol tests whether adding it would help.

## 0. Evidence status

- **What has been seen:** the E46-I7, E52/E53 and E38 scores on their evaluation rows (all 2024–2026 quarters). No model with a poverty input has ever been scored.
- **What E54 results are:** development evidence on quarters already examined. They are not independent validation. Independent evidence can only come from 2027 quarters (section 8).
- **Study window:** 2021-Q1..2026-Q3 outcomes only. No pre-2021 value is read; `backend/data/processed/psa_subsistence.parquet` (it holds 2018 rows) is never opened.

## 1. Poverty variables (provincial; inputs copied to `data/`, hashes in `data/MANIFEST.json`)

| ID | Definition | Source | Level / year |
|---|---|---|---|
| **POV** | Unweighted mean, per province, of the PSA 2021 city/municipal SAE poverty incidence (% of population) over the LGUs with an estimate: Batangas 34, Cavite 23, Laguna 30, Quezon 40, Rizal 14 (141; Lucena has none). Unweighted, so that no second publication date (POPCEN 2024) enters. | `data/sae2021_calabarzon_municipal.csv` | province aggregate of municipal estimates; 2021 |
| **SUB** | PSA provincial subsistence (food-poverty) incidence among population | `data/psa_subsistence_population_2021_2023.csv` | province; 2021, 2023 |

**Encoding (all arms):**
- Each variable is **centred across the five provinces** at each origin (value minus the five-province mean). It is set to **0 when not known** at that origin.
- Centring makes every origin's five values sum to 0. So the unknown-period zeros neither shift the training mean nor create a "data available" regime indicator in the no-intercept ridge.
- The ridge's own missing-value flag is therefore never triggered by poverty.
- **FE** (diagnostic) = five province indicator columns.

**Availability (as-of rule: a value enters the forecast issued at O(t) only if published before O(t)):**
- **POV:** the SAE 2021 municipal release is recorded in the repository only as "2024" (month not verified). Conservative assumption: published by 2024-12-31. POV is therefore known iff O(t) ≥ 2025-01-01.
- **SUB:** `publication_date` 2024-08-15 for both reference years (secondary source). At an origin after that date, the latest reference year (2023) is used; before it, SUB is unknown.

## 2. Arms

Every arm adds its poverty columns to the residual inputs of the reference model. Nothing else changes: label, rows, timing, grid, selection, decision rule, baselines.

| Arm | Poverty input | Timing |
|---|---|---|
| **R** | none (the reference model, reproduced) | — |
| **POV-AS** | POV | **as-of** (primary) |
| **SUB-AS** | SUB | as-of |
| **POV-LA** | POV at every origin | **look-ahead sensitivity**: static attribute assumed known from 2021 |
| **SUB-LA** | SUB of the latest reference year ≤ the calendar year of origin quarter t (2021 for t in 2021–2022, 2023 from 2023), ignoring publication lag | look-ahead sensitivity |
| **FE** | province indicators | diagnostic: is any poverty effect more than province identity? |

**LA arms:**
- They use no outcome information.
- Their only defect is that the forecaster at a past origin could not yet have known the value.
- They answer whether a static poverty attribute carries predictive information at all.
- They can never support a claim about past-quarter performance. A gain from them needs prospective confirmation.

## 3. Three comparisons (one per served model family)

### C1: PS target (E52; E53 kept E52 as R0)

**Model R:** E53 R0 (`e53_lib.price_forecast`, ridge, E46 I7 price component).
- It must reproduce the committed E52 / I7 `I7_p_price` within 1e-9 at every origin; otherwise the run stops.
- Origins 2023-Q4..2026-Q3, issued at O(t) for target t+2, training targets ≤ t−1, vintage `d.cut(t)`.

**Rows:** the 50 E52 rows (`E52/runs/20261017T132935Z/rows.csv`), targets 2024-Q2..2026-Q3.

**Baselines:** E52's B1–B7, climatology, always HIGH and always LOW, taken from that file.

**Decision:** p ≥ 0.5.

### C2: T43 target (E46-I7, the thesis's SWS + PSA food-insecurity definition)

**Probability:** p = `I7_p_hunger` (committed, unchanged) × the arm's price probability from C1.
- The hunger component is regional, so a provincial poverty value would enter it as a constant; it is left unchanged by construction.
- For R, p must reproduce the committed `I7_p` within 1e-9.

**Rows:**
- **S44:** the I7 evaluation rows, 35 rows over 7 quarters, built exactly as in `e46_evaluate_i7.py`. This is the primary T43 set.
- **EXT:** 40 rows over 8 quarters, reported as well.

**Comparators:** the I7 comparators present on those rows (I2, I6, I6b, B-maj, B-persist, SIM-0, SIM-5T, E41-M1, E38-served, BASE-m*).

**Decision:** p ≥ 0.5.

**Metrics:** `e44_evaluate.block`.

### C3: E38 label (production default)

**Model R:** the E38 walk-forward procedure (`e38_lib.walk_forward`), recomputed.
- It must reproduce the committed `E38-LGBM` probabilities and thresholds of `E38/runs/20261015T033922Z/predictions.csv` within 1e-9; otherwise C3 stops.

**Poverty arms:** the poverty columns are appended to every feature set of the E38 pool (COMPACT, COMB, COMB_T5). E38's own per-date configuration choice, prior shift and threshold rule then run unchanged.

**Rows:** E38's 55 rows (11 quarters 2023-Q3..2026-Q3, 49 HIGH / 6 LOW).

**Baselines:** the six E36 baselines, ALWAYS_HIGH and CLIMATOLOGY, from the committed predictions.

**Decision:** each arm's own per-date threshold.

**Metrics:** `e38_evaluate.metrics`.

C1 and C2 run in one process (`runner/e54_evaluate.py`). C3 runs in a separate process (`runner/e54_evaluate_e38.py`), because the E32 data guard that E38 installs blocks the production data tree that C1/C2 read.

## 4. Metrics

**Per arm, per comparison:**
- accuracy (with its quarter-cluster CI);
- balanced accuracy;
- recall HIGH and recall LOW;
- precision;
- Brier;
- AUC;
- calibration-in-the-large;
- confusion matrix.

**Paired Brier difference against R:** mean over rows of (p_arm − y)² − (p_R − y)², with a quarter-cluster bootstrap 95% CI (1000 draws, seed 54, quarters resampled with replacement).

**Diagnostics:**
- **Identity flag:** max |p_arm − p_R| < 1e-12 (poverty never changed a forecast).
- Per origin: training rows in which the poverty input is known (non-zero), the selected residual configuration (C1/C2), and the standardized ridge coefficient on each poverty column when a residual is selected.

## 5. Decision rule (for every arm against R, in each comparison)

**IMPROVES** — all of:
- (a) the paired Brier CI upper bound < 0;
- (b) balanced accuracy ≥ R's;
- (c) recall HIGH ≥ R's − 0.05;
- (d) recall LOW ≥ R's − 0.05.

**WORSENS** — the paired Brier CI lower bound > 0.

**NO DEMONSTRATED DIFFERENCE** — anything else. IDENTICAL is reported when the identity flag holds.

**Primary question:** C1, POV-AS vs R.

**What may be claimed:**
- **"Poverty improves the forecast on the 2024–2026 development quarters"** requires an **AS** arm to IMPROVE.
- **Multiplicity:** there are 4 poverty arms × 3 comparisons. Any IMPROVES outside the primary question is flagged as such.
- **LA arm only:** if only an LA arm improves, the report says "a static poverty attribute shows information under look-ahead; prospective test required". It does not claim an improvement.
- **FE:** if FE does as well as the improving poverty arm (paired Brier CI of POV − FE includes 0), the gain is attributed to province identity, not to poverty specifically.

**E52 acceptance:** C1 also reports E52's A1–A5 for each arm against every baseline. This is for information; nothing is adopted in E54.

## 6. Serving

**Nothing is served or changed:**
- the production default E38;
- the e46/e52/e53 records;
- the frontend;
- the Objective 3 ranking.

## 7. Repeat

Each script is run twice. `predictions.csv` and `rows.csv` must be byte-identical, and `results.json` must be identical apart from `run_utc`.

## 8. Prospective

**Freeze:** for every arm (AS or LA) that IMPROVES in C1 or C2, its 2027-Q1 probabilities from origin 2026-10-01 are written once to `frozen/E54_<comparison>_<arm>_PROSPECTIVE_2027Q1.json` with a sha256.
- At that origin both POV and SUB were published, so the input is legitimately known.
- A frozen file is never edited.

**If no arm improves:** nothing is frozen.

## 9. Not allowed

- Changing labels, thresholds, rows, baselines, grids or selection rules.
- Choosing a poverty variable, encoding or availability date after seeing any E54 score.
- Pre-2021 data.
- Outcomes after 2026-Q3.
- Web searches for PSA/SWS values.
