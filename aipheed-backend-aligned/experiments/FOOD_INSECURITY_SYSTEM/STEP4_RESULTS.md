# FOOD_INSECURITY_SYSTEM, Step 4: REF+news served (backend only) — results

**Plan:** `PLAN.md` revision 2, SHA-256 `4d4e2a2c…0840` (commit `8cbe9ed`). `runner/export_fi.py` checks the hash
before it runs, and a test checks that it refuses an edited plan.

**Switch:** `AIPHEED_LEAD2_MODEL=thesis` and `AIPHEED_MAP_MODEL=foodinsecurity`. The FIRI default and `ch1` mode are
unchanged, and so are `render.yaml`, the Dockerfile and the frontend.

**Evidence status:** development evidence.

## 1. What is served

| Item | Value |
|---|---|
| Model | IMPROVE_V2 REF+news (`OPTION_1/out/forecasts_refnews.csv`), model label `IMPROVE_V2-REFNEWS`. Nothing refitted |
| Rows | 85 = 17 quarters × 5 provinces: Lead-1 walk-forward targets 2023-Q1..2026-Q3, plus the forecasts issued 2026-10-01: 2026-Q4 (Lead 1) and 2027-Q1 (Lead 2) |
| Seal | The 2027-Q1 row equals `OPTION_1/sealed_prospective_REFNEWS.csv` (SHA-256 `cc1ff11b…`, P 0.869247, HIGH). The export asserts this |
| Reliability | Maximum Reliable Lead Time 2 (Algorithm 3: Lead 1 and Lead 2 accuracy 0.758; Lead 3 0.694). R1–R7: 0 (fails R3, R5, R7). News: 2.8% of SHAP. REF without news: 0.790 |
| Lead 1 vs Lead 2 | Equal at origin 2026-Q3 (both 0.869), but **not** at every origin. The "lead input has no effect" sentence (PLAN §1) is therefore not printed |

## 2. Province score (PLAN §2)

PSA 2023 poverty incidence among families comes from Table 1, fetched by `runner/fetch_psa.py` on 2026-11-03. The raw
JSON and its SHA-256 are in `backend/data/foodinsecurity_engine/psa/`.

| Province | Poverty 2023 (CV) | Weight | Score, 2026-Q4 and 2027-Q1 | Class | Price band, 2026-Q4 / 2027-Q1 | Food poverty 2023 (CV) |
|---|---|---|---|---|---|---|
| Quezon | 6.9% (14.4) | 1.000 | 0.869 | HIGH | Low / Low | 0.5% (38.5, low precision) |
| Rizal | 5.6% (13.5) | 0.812 | 0.705 | HIGH | Low / Low | 1.5% (24.5) |
| Laguna | 5.4% (13.3) | 0.783 | 0.680 | HIGH | Low / Low | 0.8% (35.0, low precision) |
| Batangas | 4.9% (16.2) | 0.710 | 0.617 | HIGH | Low / Low | 0.8% (33.9, low precision) |
| Cavite | 4.3% (16.4) | 0.623 | 0.542 | HIGH | Low / Low | 0.4% (53.3, low precision) |

- **The order is the same in every quarter.** It follows provincial poverty: Quezon, Rizal, Laguna, Batangas, Cavite.
- **The price band changes over quarters,** and with it what each province shows. For example, Quezon in 2026-Q3 is
  Medium (0.58).
- **Weighting never lowers the class.** In past quarters with a regional probability ≥ 0.50, some province scores fall
  below 0.50 and the class is still HIGH. A test pins this on the API.

## 3. LGUs (PLAN §3)

- **Lucena:** PSA Table 2a publishes the City of Lucena's own value: 2021 poverty incidence among population **10%**
  (CV 17%), published to the whole per cent. It is used and cited, so the Quezon fallback is not needed. It replaces the
  unverified 16.8.
- **Copy, not edit.** The value lives in a served copy, `backend/data/foodinsecurity_engine/lgu_vulnerability.csv`. The
  input file is unchanged.
- **Index:** 0.6 × poverty + 0.4 × density, both min-max within the province, times the province score. Colour = the
  regional class. All 142 LGUs are checked by a test.

## 4. News (PLAN §4; rule fixed before any flag was computed; not tuned)

**Regional sentence (E112).** For 2026-Q3, the issue quarter of the forecasts: "no news category rose 5 points or
more year on year" (881 articles).

**Province flag (E85).** The rule fires on **45 of 85 rows (53%)**:

| Province | Rows flagged |
|---|---|
| Cavite | 12 |
| Laguna | 10 |
| Quezon | 10 |
| Rizal | 7 |
| Batangas | 6 |

| Family | Rows flagged |
|---|---|
| DISASTER | 18 |
| PRICE | 8 |
| Other families, alone or combined | 19 |

**On the issued forecasts (2026-Q4, 2027-Q1),** Cavite, Laguna and Quezon are flagged for DISASTER coverage in
2026-Q3:

| Province | DISASTER coverage, 2026-Q3 | Usual |
|---|---|---|
| Cavite | 72% | 42% |
| Laguna | 45% | 30% |
| Quezon | 83% | 53% |

Rizal and Batangas are not flagged. These become 6 provincial alert candidates (staged) next to the 2 regional HIGH
candidates.

**Reading.** Firing on half the rows is too often for an early warning. The rule was fixed in advance and is reported
as it came out. Changing it would need a new plan revision written with these counts known, and would then be
exploratory.

## 5. Alignment check: H1 (PLAN §7, "to be confirmed")

Feature-level mean |SHAP| over the 62 labelled quarters:

| Lead | Top three | Food CPI year on year | FSSI-v3 (N1R) |
|---|---|---|---|
| 1 | `h_mean4` 55%, `W_rice_yoy` 13%, `true_h` 4% | 5th (3.1%) | 26th (≈ 0%) |
| 2 | `h_mean4` 55%, `W_rice_yoy` 13%, `true_h` 4% | 4th (3.0%) | 26th (≈ 0%) |

Neither feature is in the top three. **H1 is not rejected.**

## 6. Code and tests

**Changed:**
- `foodinsecurity_system.py`: rewritten per the plan, same interface;
- `export_fi.py`: rewritten;
- `fetch_psa.py`: new;
- `e31_engine.E31Disaggregator.disaggregate`: optional `vul_path`;
- `dashboard.py`, five hooks, gated on this mode:
  - province `riskLevel` from the regional class;
  - LGU colour from the regional probability;
  - served LGU inputs path;
  - Lucena provenance;
  - a missing price part tolerated.

**Tests:** `test_foodinsecurity_mode.py`, 25 tests, all pass.

**Full backend suite:**

| Run | Passed | Skipped | Failed |
|---|---|---|---|
| Before | 1004 | 18 | 0 |
| After | 1012 | 18 | 0 |

## 7. Revision 3 (EXPLORATORY): the stricter news-flag rule, and flags kept out of public text

**Plan.** `PLAN.md` revision 3, SHA-256 `2c685b93…ad38` (commit `0d7e620`). It was written after the §4 counts were
known, so this section is exploratory, not a test.

**Served rule.** Unchanged (§4): 45 of 85 rows flagged. Its flags are staged alert candidates only. The public text
fields now describe the province news coverage ("disaster coverage 72% against a usual 42% (8-quarter mean)") without
naming a flag. A test checks that "early-warning flag" and "news flag" never appear in `/explainability`,
`/forecast` or `/provinces`.

**Stricter rule** (≥ 2.0 SD, ≥ 10 points, ≥ 30 province articles; `runner/strict_flag.py` → `out/strict_flag.json`;
report only, not served, not staged):

| | Served rule (§4) | Stricter rule (§8.2) |
|---|---|---|
| Rows flagged (of 85) | 45 (53%) | **20 (24%)** |
| By province | Cavite 12, Laguna 10, Quezon 10, Rizal 7, Batangas 6 | Quezon 6, Rizal 5, Batangas 4, Laguna 4, Cavite 1 |
| Quarters with any flag | 15 of 17 | 11 of 17 |
| Families | DISASTER 18, PRICE 8, other 19 | DISASTER 8, AGRI 7, LIVELIHOOD 4, FOODSEC 3, PRICE 3 |
| Issued forecasts (2026-Q4, 2027-Q1) | Cavite, Laguna, Quezon | **none** |

**Reading.**
- Every strict flag is also a served flag.
- The 30-article floor removed nothing: every row has at least 30 province articles. The 2 SD and 10-point thresholds
  did all the narrowing.
- The 2026-Q3 disaster rises (Cavite +30 points, Quezon +30, Laguna +15) do not pass 2 SD, because these provinces'
  disaster coverage swings widely from quarter to quarter.
- Neither rule has been shown to anticipate hunger (E85 found no predictive news value). As planned, no third rule was
  tried.
