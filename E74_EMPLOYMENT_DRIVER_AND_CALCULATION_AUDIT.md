# E74: employment driver and calculation audit

**Date:** 2026-10-20 · **Branch:** `e74-employment-driver-audit` (from `final-aipheed-thesis-e72` @ de4d362; local, not pushed)

**Evidence:**
- `aipheed-backend-aligned/experiments/E74_Employment_Driver_Audit/` (`runner/`, `out/`, `tables/`)
- regression tests in `backend/tests/integration/test_e74_employment_audit.py`

## Final decision

| Question | Answer | Evidence |
|---|---|---|
| **Is employment genuinely the top driver?** | **No.** It is the largest of the **five displayed evidence groups** for 2027-Q1 in Cavite (45%), Quezon (54%), Rizal (74%) and the region (47%); climate is larger in Laguna (58%) and Batangas (44%). It is **never the largest single push** on the index in any of the 95 served province-quarters. For 2027-Q1, observed regional hunger (H1) pushes more in all five provinces (+0.093 to +0.112, vs +0.064 to +0.077 for employment). | `out/trace_summary.json`, `tables/DRIVER_COMPARISON.md` |
| **Is its contribution calculation correct?** | **Yes, arithmetically.** All of these reproduce independently: the raw LFS value, the percentile, the weight, the push, the five-bar percentages and the signs. | Raw E1 equals the independent recompute (\|Δ\| < 1e-6) on every row. Index reconstruction error 5e-7 over 95 rows. API percentages and signed contributions match on 100/100 checks. |
| **Is its contribution meaningful local evidence?** | **No.** The calculation is correct, but its prominence comes from four structural causes, and its reading is distorted in 2024-Q4 … 2025-Q4 (§5). | §4–§5 |

## 1. Source to dashboard

| Step | Finding |
|---|---|
| Dataset | PSA Labor Force Survey, national unemployment rate, both sexes, monthly. Tracked file `aipheed-backend-aligned/experiments/E41_Lead2_Audit/data_acquired/lfs_rates_national.csv`: 2021-01 … 2026-08, unit %, values 3–9%. |
| Geography | **National (Philippines).** No provincial or regional series is in the data. |
| Publication date | Not stored in the file. The test checks that the last month used ends ≥ 3 months before the issue date, which is consistent with PSA's typical ~5–6-week LFS lag. Per-release dates are not verifiable from project files. |
| Feature (`ur_yoy`, `e41_lib.features`) | At origin t: the mean unemployment rate of quarter t−1's available months minus that of quarter t−5, in percentage points. 2027-Q1 forecast (origin 2026-Q3, issue 2026-10-01): Apr–Jun 2026 minus Apr–Jun 2025 = **+0.895 pp** (3 + 3 months). |
| Index indicator | FIRI v2 E1 = `ur_yoy`, direction "higher = more risk" (`app/ml/inference/firi.py`) |
| Score | Mid-rank percentile of E1 among its own earlier values; ≥ 8 needed, else `insufficient_history` (not counted, never zero). 2027-Q1: 17 earlier values → **0.882**. |
| Domain and weight | Household economy (E) = mean of E1 and E2. E2 (BSP remittances) is **missing for every 2026 issue**, so E1 alone is the domain. The E weight is the **equal-weight default (1.0)**, because E has too few earlier pairs to be tested against hunger. Evidence weights at 2026-Q3 exist only for A 0.35, V 0.35, C 1.84 and H 1.46 (raw). Normalised w_E = 0.167 (0.200 in Quezon, which has no news domain). |
| Push | w_E × (0.882 − 0.5) = **+0.0637** (Quezon +0.0765) |
| Explanation method | **FIRI v2 additive index breakdown**, not SHAP. Separately, the served E56 LightGBM (inside A1) uses `ur_yoy` (20 splits): its TreeSHAP for the employment group is **−0.2455 log-odds of the price-pressure probability**, identical in all provinces. The same input lowers the price model and raises the index. The two are different measurements and must not be compared. |
| Dashboard percentage | \|group push\| / Σ of \|group push\| over the five groups, rounded by largest remainder, then sorted. **Observed regional hunger, vulnerability and news are excluded** (`otherPct`), and raising and lowering pushes are mixed in one denominator. |

## 2. Variation

- **Across provinces:** E1 is identical across provinces in every quarter, so it is national evidence. The push varies by province only through weight renormalisation, when another domain such as news is missing.
- **Across quarters:**

| Period | E1 (pp) |
|---|---|
| 2022–24 | −2.9 … −0.6 (post-pandemic recovery) |
| 2024-Q4 … 2025-Q4 | −0.80 … 0.00 |
| 2026 | +0.12 … +1.32 |
| 2027-Q1 | +0.895 |

- **Missingness:** E1 is untestable (insufficient history) in 45 of 95 rows, all before 2024-Q4. There it is reported as insufficient data, never zero.

## 3. Every driver on the same footing

`tables/DRIVER_COMPARISON.md` covers 95 served rows. Push = exact contribution to FIRI − 0.5, the only measurement the bars use.

| Indicator | Level | Usable rows | Mean \|push\| | Largest single push (rows) | Independent support |
|---|---|---|---|---|---|
| H1 regional hunger (outcome evidence) | regional | 95 | 0.063 | **40** | direct outcome, regional; vs OCTA the index tracks hunger only through H1 |
| C1 El Niño alert | national | 95 | 0.063 | **32** | none (2023-24 El Niño came with disinflation) |
| A2 headline inflation | province | 95 | 0.031 | 14 | none tested |
| V1 vulnerability | province (static) | 95 | 0.025 | 5 | none (E71) |
| A3 rice price | province | 74 | 0.020 | 4 | none tested |
| **E1 unemployment change** | **national** | **50** | **0.052** | **0** | **none: employment news does not track LFS (E73); weight untested** |
| E2 remittances | national | 40 | 0.026 | 0 | none; missing in 2026 |
| C2 typhoons | province | 60 | 0.034 | 0 | climate news tracks PAGASA (E73, ρ 0.35) |
| C3 / C4 production | province | 80 / 80 | 0.027 / 0.024 | 0 | none (fish-kill news fails, E73) |
| A1 price-pressure model | province | 60 | 0.010 | 0 | price label only (E70) |
| N1 news FSSI | province | 10 | 0.036 | 0 | no forecast value (E73) |

**Verdict: no defensible overall ranking.** The indicators share one scale only as pushes on this index. They differ in:
- geography: national, regional or provincial;
- weight basis: evidence or default;
- missingness;
- independent support: only climate news and the regional hunger outcome have any.

They are therefore presented as **contributing evidence, not ranked causes**.

## 4. Why employment looks prominent (root causes)

1. **The five bars exclude the largest push.** Observed regional hunger is outside them, so the top bar is not the top factor.
2. **Weight concentration.** Remittances are missing in 2026, so E1 carries the whole household-economy weight.
3. **Untested weight.** E gets the equal-weight default, about 3× affordability's evidence-based weight.
4. **National value repeated in five provinces.** It shifts all provinces together and adds no provincial information.

## 5. A distortion in the indicator itself

E1 is scored against its own earlier values, and those are dominated by the 2022–24 recovery: unemployment fell by 1.4–2.9 points per year.

- **Inverted rows.** From 2024-Q4 to 2025-Q4, unemployment was **still falling** (−0.80 … −0.002 pp), yet E1 scored 0.75–1.0 and **raised** the index. That is 25 province-quarters (`out/employment_sensitivity.json`).
- **Overall effect.** Employment raises the index by +0.061 on average (max +0.110).
- **Class changes.** Without it, 9 province-quarters (2024-Q4 … 2026-Q3) would change from HIGH to LOW. **None changes in the 2027-Q1 forecast**, where the rise is genuine.
- **Nature of the problem.** This is a validity problem of the FIRI v2 normalisation (own-history percentile over a recovery period), not an arithmetic error.
- **Not changed.** Redefining the served index now would be a post-hoc model change on examined quarters and would conflict with the sealed FIRI v2 prospective seal. It is left for your and your adviser's decision.
- **Disclosed where it happens.** The factor card now says so, for example: "unemployment fell year on year, yet this indicator scores above its historical middle … it does not mean conditions worsened."

A related pre-existing design point: the binary El Niño indicator (C1) is scored 0 whenever there is no El Niño, so in normal quarters it lowers the index (65 of 95 rows). This is reported only, not changed.

## 6. Defects found and fixed (text and serialization only; no served value changed)

| Defect | Where | Fix |
|---|---|---|
| "Why is this province at risk?" + "Ranked" implied ranked causes | Left panel (thesis mode) | "Contributing indicators" + "Index contribution, not causes", from `servingModel.explanationMethod`; SHAP wording kept in the default service |
| PDF interpretation said "the SHAP decomposition assigns the largest share of the attributed model output", and attributed the remainder to FSSI features | `compose_formal_interpretation` (thesis mode) | Neutral text: five groups' shares; regional hunger, vulnerability and news named as outside the bars with their share; national scope; not causes |
| PDF bar text said "exact share of how far the index moved" | `report._thesis_driver_text` | "share of the five groups' combined push … not SHAP and not a ranking of causes" |
| Ranking API `whyAboveNextLower` came from another model's SHAP (D_last, H_margin, Dnow) | `/api/v1/ranking` (thesis mode) | Food-security dimension push differences of FIRI v2, with a thesis method text |
| Employment and remittance cards did not say the figure is national, or that the weight is a default | Factor cards | Scope note; weight basis (evidence vs default); direction-conflict note |
| The summary did not name the largest single push | Province summary text | "The largest single push on the index is … ; the five factor bars … are not an overall ranking of causes" |
| Test hygiene: importing the trace script switched the whole test process to thesis mode (20 failures) | `e74_trace.py` | Environment set inside `main()` only |

## 7. Regression tests (`test_e74_employment_audit.py`, 11 tests, real served rows from all five provinces)

- **Source and units:** E1 equals the independent LFS recompute on every served row; units (% and pp); identical across provinces.
- **Timing:** quarter alignment (t−1); a ≥ 3-month gap between the last LFS month and the issue date.
- **Arithmetic:** pushes reconstruct FIRI − 0.5; weights sum to 1.
- **API:** percentages equal the largest-remainder shares; ordering; direction equals sign.
- **Largest push:** H1 is the largest single push in all five 2027-Q1 provinces; employment is not.
- **Cards:** the national scope and default weight are stated.
- **Missing data:** missing E1 shows as `insufficient_data`, never zero risk.
- **Synthetic case (marked):** a negative employment push is protective.
- **PDF:** the text equals the API shares and contains no "SHAP"; the remainder share is disclosed.
- **Ranking API:** reasons come from the index breakdown.
- **Panel wording:** taken from the config.
- **Direction conflict:** disclosed where it happens; absent for 2027-Q1.

## 8. Reproduction (from `backend/`)

```
python -B ../aipheed-backend-aligned/experiments/E74_Employment_Driver_Audit/runner/e74_trace.py
python -B ../aipheed-backend-aligned/experiments/E74_Employment_Driver_Audit/runner/e74_compare.py
python -B ../aipheed-backend-aligned/experiments/E74_Employment_Driver_Audit/runner/e74_sensitivity.py
python -B ../aipheed-backend-aligned/experiments/E74_Employment_Driver_Audit/runner/e74_metrics.py
python -m pytest -q tests/integration/test_e74_employment_audit.py
```
