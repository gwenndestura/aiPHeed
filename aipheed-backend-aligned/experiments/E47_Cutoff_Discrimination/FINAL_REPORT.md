# E47: publication-cutoff audit and candidates for HIGH/LOW discrimination

**Branch:** `e46-lead2-policy`, continuing from E46's final commit 74031cf. **Date:** 2026-10-17.
**Protocols (frozen before any score):** `PROTOCOL.md` (commit 2afd9cd) and `ADDENDUM_A1.md` (commit d7ddfc5).

## Decision

| Question | Answer |
|---|---|
| 75% Lead-2 accuracy reached? | **Accuracy yes, requirement no.** The best reproducible candidate, the served E46 **I7**, scores 0.800 on 35 development rows (7 quarters), but it is not accepted. |
| HIGH/LOW discrimination adequate? | **No.** I7's HIGH recall is 0.44 (4 of 9) against the required 0.60; balanced accuracy 0.684 < 0.70. No E47 candidate improves it. |
| Independent evaluation? | **No.** Every 2022–2026 quarter was examined in E41–E46. The only independent test is prospective: 2027-Q1..Q4, frozen. |
| Suitable for production? | **No.** Production stays **E38**. I7 stays the experimental `e46` candidate; nothing new is served. |
| Leakage found? | **No.** Every input at every simulated origin was published before its issue time. The I7 2027-Q1 forecast uses CPI through August 2026, not September. |

## 1. Initial concern, root cause and result

**Concern:** I7 was issued 2026-10-01, and a report suggested September 2026 CPI might be in it.

**Finding:**
- **I7 does not use September CPI.** Its data cut stops at **2026-08** (month 2 of the latest quarter; `runs/cutoff_audit_i7.json`, and `E46/runs/asof_check_i7.json`, which rebuilds the forecast with all later data deleted).
- **September CPI belongs to I8,** whose issue time is 2026-10-15.
- **When September CPI was published:**
  - nationally on **Tuesday 2026-10-06** (GMA News, "nitong Martes"; Trading Economics);
  - the provincial OpenStat table containing it was retrieved 2026-10-15 at 09:54 UTC (17:54 Manila time), which proves availability by that evening only;
  - RSSO IV-A provincial releases typically follow the national release within days (Feb 2024 CPI on 2024-03-07, Mar 2024 on 2024-04-08).
- **So I8's margin is about 2 days** under the conservative 13-day provincial lag. I8 is therefore kept as a reference, not a candidate.
- **No artifact needed rebuilding;** the frozen 2027-Q1 forecasts are unchanged.

## 2. Data and publication-cutoff audit (`runner/e47_cutoff_audit.py`)

At every origin 2021-Q3..2026-Q3, the script took the latest observation each source actually contributes after the as-of cut, added the source's publication lag and compared the result with the issue time.

| Source (geography) | Latest observation used at the 2027-Q1 issue | Publication rule (evidence) | Minimum margin, any origin (I7 / I8) | Available? |
|---|---|---|---|---|
| PSA provincial CPI, food and headline (provincial) | 2026-08 (I7) / 2026-09 (I8) | national release on about the 5th–7th of the next month (Jul 2026 on 08-05, Sep 2026 on 10-06); provincial within days; bound 13 days | 18 d / 2 d | yes / yes (thin) |
| SWS hunger rounds, approved (Balance Luzon, regional) | 2026-Q2, posted 2026-08-24 (I7) / 2026-Q3, posted 2026-10-14 (I8) | exact posting dates in the data | 3 d / 1 d | yes |
| PSA LFS unemployment and underemployment (national) | 2026-06 | about 5–6 weeks; bound 45 days | 46 d / 60 d | yes |
| PSA palay/corn, fisheries/aquaculture production (provincial) | 2026-Q2 | 45–60 days; bound 60 | 31 d / 45 d | yes |
| NOAA ONI / ENSO (national) | 2026-Q2 | early next month; bound 10 | 81 d | yes |
| Typhoons within 300 km (provincial) | 2026-Q3 | real-time advisories, known at period end | 0 d (at midnight) / 14 d | yes; best-track revisions are a vintage risk |
| Province news counts (provincial) | 2026-Q3 | articles counted by publication date | 0 d / 14 d | yes |
| PSA wholesale rice (provincial) | 2026-Q2 | 2–4 weeks; bound 30 | 61 d | yes |
| BSP cash remittances (national) | **2025-Q4** (the series ends there; 2026 is missing and imputed with a missing flag) | about 6–7 weeks; bound 50 | 41 d | yes; coverage gap |
| ECB USD/PHP (national) | 2026-Q2 | daily | 90 d | yes |
| Rice-policy orders (national) | events announced before the issue date | official announcement dates | – | yes |
| Brent crude, new in E47 (global) | 30 days ending 2026-09-21 | EIA weekly, lag of a few days; window ends 10 days before issue | 10 d by construction | yes |
| Training labels (T43) | 2026-Q2 | SWS posted before issue; CPI month 3 of t−1 published before issue | – | yes |

**Remaining vintage caveat:** CPI and production values are the 2026-10-15 vintage. PSA rarely revises CPI, and real-time vintages were not archived.

## 3. Verification of the E46 numbers (`runner/e47_verify_e46.py`, independent sklearn code)

Every figure reproduces exactly. On S44 (35 rows, 7 quarters, 9 HIGH):

| Arm | Accuracy | Balanced | Rec H | Rec L | Prec | F1 | Brier | AUC | TP/TN/FP/FN | Share called LOW |
|---|---|---|---|---|---|---|---|---|---|---|
| I7 | 0.800 | 0.684 | 0.44 | 0.92 | 0.67 | 0.53 | 0.174 | 0.735 | 4/24/2/5 | 0.83 |
| I8 | 0.771 | 0.665 | 0.44 | 0.88 | 0.57 | 0.50 | 0.132 | 0.902 | 4/23/3/5 | 0.80 |
| always-LOW | 0.743 | 0.500 | 0 | 1 | – | – | – | – | 0/26/0/9 | 1.00 |

- **24 of I7's 28 correct rows are LOW calls.**
- **On the 40-row window** (2024-Q2 added): I7 0.725, always-LOW 0.675.
- **I8's AUC 0.902 and Brier 0.132 reproduce** under strict chronological, forward-chaining evaluation (within-quarter AUC 0.889). Its cutoff margin is thin (section 1).
- **The stored T43 labels** equal freshly recomputed ones for all 80 labelled rows.

## 4. Diagnostics (`runner/e47_diagnostics.py`)

**Label support:**
- 18 HIGH in 19 labelled quarters: **12 switched on by the gap rule alone, 5 by both rules, 1 by food alone**.
- By province: Rizal 0, Quezon 6, the others 4 each.
- Hunger was above 11.3 in all 10 quarters since 2023-Q4.
- 47% of label variance lies within quarters (between provinces), all of it from prices.

**Why I7 misses HIGH (9 misses, 2024-Q2..2026-Q3):**

| Misses | Period | Cause |
|---|---|---|
| 4 | 2024-Q2 | hunger: the latest round at the issue date was 10.3% and jumped to 19.6% after it; the price parts were forecast correctly |
| 4 | 2024-Q4 / 2025-Q1 | the gap was forecast below threshold while food stayed 0.3–1.3 points above headline |
| 1 | 2026-Q2 | Cavite food 4.73 against a 4.71 threshold |

**Province variation and the trigger groups:**
- Employment, OFW and FX, ENSO, hunger and policy inputs are **identical for all provinces** (within-quarter variance 0).
- Remittances are missing for 2026.
- The news OFW share is always 0, and the news employment share is non-zero once.
- Provincial variation comes only from CPI, rice prices, production, typhoons and news.
- **Price features dominate** because the other groups have no provincial variation and weak time variation over 19 quarters.

## 5. Protocol and candidates

**Issue convention:** I7's (day 1, audited). **Evaluation:** rolling-origin, expanding window; every model is refitted at each origin using pairs whose outcomes were published before that origin.

| Arm | Weakness it addresses | Result (35 rows) |
|---|---|---|
| **I7-E** | gap misses: headline driven by fuel, none of the groups carried an energy price; adds Brent `brent_yoy`, `brent_mom3` | identical decisions to I7; Brier 0.179 vs 0.174. **No gain.** |
| **SL-P** | the bivariate-normal mapping and fixed cut; sample size | logistic on as-of price and hunger margins: **collapses**, 0.343, AUC 0.12 |
| **SL-5T** | five triggers vs price-only | **collapses**, 0.429, AUC 0.18 |
| **LGBM-C** | the "best corrected LightGBM" comparison | **collapses**, 0.400, AUC 0.30 |
| **PS-P** (A1) | D7, below: the price signal fitted on its own labels × hunger | 0.714, balanced 0.662, HIGH recall 0.56, LOW recall 0.77, AUC 0.748 |
| **PS-5T** (A1) | five triggers in the corrected structure | 0.686, balanced 0.607, AUC 0.607. **Worse than price-only.** |

**D7, why SL-P, SL-5T and LGBM-C collapse:** T43 = hunger AND price.
- In 2022–2023 hunger was ≤ 11.3, so labels were LOW in the quarters of highest food inflation.
- An additive or tree model of T43 therefore learns "high price margin → LOW", the reverse of the target's rule.
- A1 fits the price component on the price-signal outcome itself (about 2× the labelled rows, no hunger confounding). That removes the collapse but does not beat I7.

**Decision thresholds:** chosen on training data only (embargoed forward chaining inside each origin's training pairs). The selected cuts varied by origin: SL-P {0.5, 0.6}, LGBM-C {0.2, 0.4, 0.5}, PS-P {0.45–0.6}. No threshold was chosen on outcomes.

## 6. Comparison, identical rows (targets 2024-Q3..2026-Q3: 7 independent quarters, 35 rows, 9 HIGH)

| Arm | Acc (95% CI) | Bal | Rec H | Rec L | Prec | F1 | Brier | AUC | TP/TN/FP/FN | LOQO min |
|---|---|---|---|---|---|---|---|---|---|---|
| **I7** (served `e46`) | **0.800** (0.66–0.94) | 0.684 | 0.44 | 0.92 | 0.67 | 0.53 | 0.174 | 0.735 | 4/24/2/5 | 0.767 |
| I7-E | 0.800 | 0.684 | 0.44 | 0.92 | 0.67 | 0.53 | 0.179 | 0.722 | 4/24/2/5 | 0.767 |
| I8 (reference) | 0.771 | 0.665 | 0.44 | 0.88 | 0.57 | 0.50 | **0.132** | **0.902** | 4/23/3/5 | 0.733 |
| PS-P | 0.714 | 0.662 | 0.56 | 0.77 | 0.45 | 0.50 | 0.180 | 0.748 | 5/20/6/4 | 0.700 |
| PS-5T | 0.686 | 0.607 | 0.44 | 0.77 | 0.40 | 0.42 | 0.205 | 0.607 | 4/20/6/5 | 0.633 |
| I2 (E44, defective) | 0.686 | 0.716 | 0.78 | 0.65 | 0.44 | 0.56 | 0.181 | 0.603 | 7/17/9/2 | 0.633 |
| BASE-m1.0 (price-only structural) | 0.743 | 0.682 | 0.56 | 0.81 | | | n/a | | 5/21/5/4 | 0.733 |
| SL-5T | 0.429 | 0.325 | 0.11 | 0.54 | 0.08 | 0.09 | 0.420 | 0.184 | 1/14/12/8 | 0.333 |
| LGBM-C | 0.400 | 0.269 | 0.00 | 0.54 | 0 | – | 0.323 | 0.299 | 0/14/12/9 | 0.300 |
| SL-P | 0.343 | 0.267 | 0.11 | 0.42 | 0.06 | 0.08 | 0.521 | 0.120 | 1/11/15/8 | 0.267 |
| always-LOW | 0.743 | 0.500 | 0 | 1 | | | 0.220 | | 0/26/0/9 | |
| persistence | 0.543 | 0.583 | 0.67 | 0.50 | | | 0.457 | | 6/13/13/3 | |
| E38-served (production) | 0.143 | 0.205 | 0.33 | 0.08 | | | 0.653 | 0.207 | 3/2/24/6 | |
| E41-M1 | 0.771 | 0.592 | 0.22 | 0.96 | | | 0.164 | 0.697 | 2/25/1/7 | |

**Accuracy by quarter:**

| Quarter (HIGH) | I7 | PS-P | I8 |
|---|---|---|---|
| 2024-Q3 (1) | 1.0 | 0.6 | 1.0 |
| 2024-Q4 (3) | 0.6 | 0.6 | 0.6 |
| 2025-Q1 (4) | 0.6 | 0.8 | 0.4 |
| 2025-Q4 (0) | 1.0 | 0.8 | 1.0 |
| 2026-Q1 (0) | 1.0 | 0.8 | 1.0 |
| 2026-Q2 (1) | 0.6 | 0.8 | 0.4 |
| 2026-Q3 (0) | 0.8 | 0.6 | 1.0 |

**By province (I7):** Cavite 0.71, Laguna 0.71, Quezon 0.71, Rizal 1.00 (never HIGH), Batangas 0.86.

**Extended rows** (2024-Q2 added; 8 quarters, 40 rows, 13 HIGH): I7 0.725, I8 0.700, PS-P 0.650, E41-M1 0.750, always-LOW 0.675.

**Calibration:** I7's calibration-in-the-large CI is −0.23 to 0.13 (contains 0). For I8, slope 1.02 and intercept −0.66 (E46 calibration run).

**Paired date-level Brier tests vs I7:** no difference is significant after Holm correction (7 quarters).

**Selection (pre-declared track record, targets ≤ 2026-Q2):**

| Arm | Brier |
|---|---|
| I7 | 0.171 |
| I7-E | 0.177 |
| PS-5T | 0.226 |
| LGBM-C | 0.368 |
| SL-5T | 0.480 |

I7 is selected. Its gates: A0 ✓, A1 ✓ (0.800), **A2 ✗** (HIGH recall 0.44), A3 ✓, A4 ✓; leave-one-quarter-out minimum 0.767 ✓. **The development criteria are not met.**

## 7. Five trigger groups: are they model inputs?

| Group | In I7's model (inputs) | Weight evidence | Geography |
|---|---|---|---|
| Market and prices | base projections, CPI, rice wholesale, M1, news share, policy, energy (I7-E) | dominant | provincial (CPI, rice); national (policy, energy) |
| Climate | typhoons, ENSO, palay/corn | non-zero at the 2027-Q1 origin (Cavite: dropping climate lowers p) | provincial (typhoons, production); national (ENSO) |
| Fisheries | fisheries and aquaculture production (no fish-kill event series exists) | about 0 | provincial |
| Employment | national unemployment and underemployment | small, national | national proxy |
| OFW remittances | remittances (missing 2026), USD/PHP | small | national proxy |

- Every group is connected to training and inference.
- Price-only versus five-trigger comparisons (BASE-m1.0 / PS-P / I7-BASE vs I7 / PS-5T / SL-5T) show **no measurable gain from the non-market groups**.
- The dashboard labels each group's status (`contributes`, `no_effect`, `not_recorded`) from the served model.

## 8. Frozen forecasts (unchanged; new ones added)

All target **2027-Q1**, issued 2026-10-01 unless noted. These are forecasts; the outcomes are unknown.

| Artifact | sha256 | Cavite | Laguna | Quezon | Rizal | Batangas |
|---|---|---|---|---|---|---|
| E46 I7 (served `e46`) | `5592d53e…3241e` (unchanged) | 0.061 | 0.051 | 0.146 | 0.030 | 0.039 |
| E46 I8 (issued 10-15) | `284f23f2…770` (unchanged) | 0.717 | 0.374 | 0.452 | 0.492 | 0.126 |
| E47 (I7-E / SL-P / SL-5T / LGBM-C) | `0433ff98…16da` | I7-E 0.158 | 0.093 | 0.239 | 0.057 | 0.046 |
| E47 A1 (PS-P / PS-5T) | `9bc75000…2641` | PS-P 0.313 | 0.215 | 0.367 | 0.183 | 0.116 |

All are LOW at their decision rules, except I8 (Cavite HIGH). The selected arm is I7 in both E47 runs. Full hashes are in `ARTIFACTS.md`.

## 9. Tests and live verification

| Test suite | Command | Result |
|---|---|---|
| E47 | `backend/venv/Scripts/python.exe -B -m pytest -q tests/test_e47.py` (from the E47 folder) | **9 passed** |
| E47 A1 | `… -m pytest -q tests/test_e47_a1.py` | **3 passed** |
| Backend | `backend/venv/Scripts/python.exe -m pytest -q` (from `backend/`) | **356 passed, 18 skipped** |
| Frontend | `npx vitest run` (from `frontend/`) | **36 passed** |

**What the E47 tests cover:**
- protocol and addendum freezes;
- Brent data hash and window;
- the energy window ending 10 days before issue;
- the cutoff audit (all inputs published before issue; I7 CPI through 2026-08);
- gap margins equal base − headline − threshold;
- SL-5T, LGBM-C, PS-P, PS-5T, their training-only thresholds, and I7-E unchanged when every post-origin observation is perturbed;
- price-signal labels only from published CPI;
- confusion-matrix and precision/F1 arithmetic.

**Live system** (API restarted in `e46` mode on 8001; approved frontend on 8082):

| Check | Result |
|---|---|
| Target and issue | 2027-Q1, issued 2026-10-01 |
| Score types | `food_stress_risk_probability` with `backtest` / `earlier_forecast` / `forecast` only |
| Unavailable quarters | 2023-Q2 returns 404 (unavailable, not filled) |
| Municipalities | 142/142 with a band |
| News | Quezon 3 articles |
| Five trigger groups | all with a status |
| Dashboard | renders Q1 2027 with the approved palette and the Q1 2026 → Q1 2027 timeline |
| Acceptance flag | `false` |

**Repeats:** byte-identical (`ARTIFACTS.md`).

## 10. Reproduce (from `aipheed-backend-aligned/experiments/E47_Cutoff_Discrimination`, `PY = backend/venv/Scripts/python.exe`)

```
$PY -B runner/e47_cutoff_audit.py i7 ; $PY -B runner/e47_cutoff_audit.py i8
$PY -B runner/e47_verify_e46.py ; $PY -B runner/e47_diagnostics.py
$PY -B runner/e47_evaluate.py          # E47 arms + selection + 2027-Q1 freeze
$PY -B runner/e47_evaluate_a1.py       # A1 arms
$PY -B -m pytest -q tests/test_e47.py tests/test_e47_a1.py
```

## 11. Files and commits

**New files** (E47 folder only; E44, E45 and E46 untouched):
- `PROTOCOL.md`, `ADDENDUM_A1.md` (+ `runner/*_SHA256.txt`)
- `runner/e47_cutoff_audit.py`, `e47_verify_e46.py`, `e47_diagnostics.py`, `e47_lib.py`, `e47_evaluate.py`, `e47_a1.py`, `e47_evaluate_a1.py`
- `data/brent_daily_fred_raw.csv` + `data/PROVENANCE.md`
- `tests/test_e47.py`, `tests/test_e47_a1.py`, `tests/conftest.py`
- runs `20261017T031323Z` (+ repeat `20261017T032022Z`), `a1_20261017T031747Z` (+ repeat `a1_20261017T032223Z`)
- `runs/cutoff_audit_i7.json`, `cutoff_audit_i8.json`, `verify_e46_metrics.json`, `diagnostics.json`
- `frozen/E47_PROSPECTIVE_2027Q1.json` and `E47_A1_PROSPECTIVE_2027Q1.json` (+ sha256)
- `ARTIFACTS.md`, this report

**Backend and frontend:** no changes in E47.

**Commits:** 2afd9cd (protocol freeze), d7ddfc5 (E47 run + A1 freeze), and the final report commit. Nothing is pushed.

## 12. Remaining limitations and the evidence needed

- **The blocker:** with 7 independent development quarters and 9 HIGH rows, the gap-driven HIGHs of 2024-Q4/2025-Q1 and the 2024-Q2 hunger jump are not forecastable from the as-of inputs.
  - Every tested structure trades HIGH recall for LOW recall at about AUC 0.7–0.75. I8 reaches 0.90 with its extra CPI month, but its cutoff margin is thin.
  - Non-market triggers carry no provincial signal (employment, OFW, ENSO and policy are national; remittances stop in 2025-Q4; there is no fish-kill event series).
- **The target:** T43 is an exploratory proxy (regional SWS hunger + provincial price signal), not observed provincial food insecurity. Its thresholds await adviser approval.
- **The only valid acceptance evidence is prospective:** score the frozen I7 forecast (and the E46/E47 alternatives) on 2027-Q1..Q4 as PSA CPI and SWS rounds are released, with no reselection.
- **Data that could change the blocker:**
  - provincial hunger or FIES (CBMS);
  - provincial labour and remittance series;
  - an archived real-time CPI release log, which would let I8's 15th-of-month timing be adopted with a verified cutoff.

---

## 13. Addendum: five-trigger contributions for past quarters (commits a151cba, eee70a4, 68a9bc3)

**Implementation:**
- `scripts/build_record_e46.py` refits I7 at every past issue date (2023-Q4..2026-Q2 origins), using only that date's data.
- Each refit must reproduce the committed backtest probability (asserted, to 1e-9).
- The record stores per quarter (`pastDrivers`): the five-group contributions, statuses, as-of evidence notes, an information-cutoff block and additivity checks.
- `e41_lead2` and `dashboard` serve them for past quarters. The region pools the province attributions and says so.
- The explainability note describes the five-trigger model on every quarter it attributes.

**Quarter mapping:**
- Target q is issued at 00:00 on the first day of quarter q−1, after quarter q−2. This is the rule coded in `e41_lib.origin`/`m0_of` and the one in the frozen 2027-Q1 artifact.
- Information cutoff: CPI through month 2 of q−2; typhoons and news through q−2; production, LFS and remittances through q−3; SWS rounds posted before the issue date.
- It is tested for every past quarter, including the year boundaries: 2024-Q2 → 2024-01-01, 2025-Q1 → 2024-10-01.

**Status rule:**
- **contributes:** removing the group moves food YoY, the gap or hunger by ≥ 0.1 percentage points.
- **no_effect:** a computed contribution below that.
- **insufficient_data:** none of the group's observed inputs had a value at the issue date.
- Across 225 province-quarter-group cells: 190 contributes, 35 no_effect, 0 insufficient_data. OFW always has USD/PHP, even where remittances are missing (2026).
- Percentages are shares of each group's |log-odds effect| on that quarter's own prediction. They are model attributions, not causes.

**Checks:**
- Ridge contributions sum to each component's correction within 1.8e-15.
- The hunger ridge's intercept is recorded as not attributed to any trigger.

**Quezon examples** (reproduced from the refits):

| Quarter | Issued | p | Climate | Market | OFW | Employment | Fisheries |
|---|---|---|---|---|---|---|---|
| 2026-Q2 | 2026-01-01 | 0.546 | 57% | 18% | 7% | 13% | 5% |
| 2026-Q3 | 2026-04-01 | 0.852 | 54% | 15% | 28% | 3% | 0% (no_effect) |

**Tests:** see section 9 and E48.
- Backend: 367 passed / 18 skipped.
- Frontend: 45 passed, including the merged updated-ui-with-tutorial frontend and the `insufficient_data` and `not_recorded` copy.

**Metrics:** unchanged (no model refit), re-verified by `runner/e47_verify_e46.py`. I7: 0.800 / balanced 0.684 / HIGH recall 0.44 / Brier 0.174 / AUC 0.735. **75% with discrimination is not met.**
