# Root-cause analysis (E24v2): what limits aiPHeed's forecasts, and which limits are now fixed

**Evidence files:**

| File | Contents |
|---|---|
| `runs/DEV_20261013T222827Z/results_dev.json` | Development rows, noise ceiling |
| `runs/BX_20261013T163710Z/results_BX.json` | Unseen-quarter back-cast |
| `runs/lgu_analysis.json` | LGU ranking analysis |
| `runs/provincial_validity.json` | Provincial validity check |
| `data/comparability_gate.json` | Comparability gate |
| `PREDICTIONS_BY_QUARTER.csv` | Every lead-1 row with every arm |

**Earlier evidence still holds:** E23 and E24 reproduce exactly (`2026-10-14_E24_Resolve_Forecasting/ROOT_CAUSE_ANALYSIS.md`).

## 1. The approved label has two parts that behave completely differently

| Part | What it measures | Geography | Share of label variance | How forecastable (E24v2 evidence) |
|---|---|---|---|---|
| H, SWS hunger | Share of families reporting involuntary hunger, from a sample survey | **Balance Luzon**: one value shared by the 5 provinces | 65.2% | **Not forecastable beyond persistence with 2021–2025 data** (below) |
| 2D, relative food inflation | Provincial food CPI YoY minus the five-province mean (PSA) | **Province** | 34.8% | **Forecastable beyond persistence, shown on 94 unseen quarters** (§3) |

## 2. Why nothing beats persistence on the approved label

### 2.1 The label changes are real regional hunger movements, not survey noise

A new noise-ceiling analysis uses SWS's ±4% Balance Luzon margin, i.e. n = 600 (n = 300 as sensitivity). It asks how often sampling error alone would put the published label on the other side of the threshold:

| | n = 600 | n = 300 |
|---|---|---|
| Expected label flips from sampling error, all 40 lead-1 rows | 1.1 | 1.8 |
| …on persistence's 5 error rows | 0.25 | 0.34 |

Four of the five label changes are **far** from the threshold in sampling-error units:

| Change | z |
|---|---|
| 2023-Q4 Laguna | 2.75 |
| 2024-Q1 Laguna | 3.89 |
| 2024-Q2 Quezon | 9.49 |
| 2024-Q3 Quezon | 9.36 |

These were real movements of regional hunger (the 2023–2024 rise). Only the 2025-Q4 Batangas change (z = −0.69) is within survey noise.

**Consequence.** Accuracy is **not** capped by label noise: a perfect forecaster of true hunger would err on about 1 of 40 rows. **The binding limit is information about future regional hunger.**

### 2.2 At the forecast origin, the latest SWS round is 2–3 quarters old

| Information at the origin | Details |
|---|---|
| Latest SWS round | Fieldwork of the quarter before the origin is usually published **after** the origin. In the 2026-Q3 replay, the latest usable round is 2025-Q4: **3 quarters** before the target, because the 2026 rounds lack verified publication dates. |
| **What persistence carries** | That 2–3-quarter-old regional value |
| **What a model would need** | Information about how hunger moves over the next 2–3 quarters |

### 2.3 2021–2025 holds too little history to learn hunger dynamics

| Item | Value |
|---|---|
| Production SWS rounds in the authorized window | 20 |
| Distinct test quarters at lead 1 | 8 |
| HIGH / LOW test rows at lead 1 | 37 / 3 |

**E13 showed** that models fitted on this window over-react to the 2024 level shift.

**E24v2's local-level model:**

- treats SWS as a random walk observed with sampling error;
- has one parameter, estimated by maximum likelihood.

It is the most data-efficient H model possible. Even so, its development result is **not significantly better than persistence**:

| Comparison | Result |
|---|---|
| Accuracy, PCF vs persistence | 0.900 vs 0.875, one row, p = 0.50 |
| Brier, PCF vs persistence | 0.104 vs 0.125 |
| Brier, PCF vs calibrated persistence | 0.104 vs 0.162, p = 0.016 (development evidence only) |

### 2.4 A long SWS history exists but is not in the project, and cannot be fetched safely here

**Status:**

- SWS has published Balance Luzon hunger since the late 1990s.
- No pre-2020 SWS value exists in any project file (footer metadata checked).
- SWS web pages were **not opened**: they can display the protected 2026 rounds.

**Plan.** Amendment A2 pre-registers the T1 back-cast for when you supply that history (`runner/run_bx_t1.py`, tested on synthetic fixtures). **That is the fastest route to a T1 generalization result.**

### 2.5 News carries no measurable predictive information here

The E23/E24 ablations stand:

- the news-only arms are the worst required arms;
- FSSI is not among the strongest predictors.

The E24v2 forecaster does not use news. This is reported, not hidden (H1 is not supported in development data and is not testable).

## 3. The provincial part of the label *is* forecastable, and E23/E24 missed it

**Two things were missing:**

| Gap | Fix in E24v2 |
|---|---|
| **History** | PSA publishes provincial food CPI on the 2018 base, back-cast to 1994 (OpenSTAT `0012M4ACP28` / `ACP22`). E24v2 acquired 1994–2025 for the five provinces (public; no 2026 value requested). It reproduces the approved E12 D values to within 0.04 percentage points, with 100% sign agreement (`data/comparability_gate.json`). |
| **Information timing** | E23/E24 used government data of quarter t−1 at origin O(t). The first two monthly CPI releases of quarter t are published before O(t) (national release around the 5th, provincial proxy +14 days). Supporting evidence: the OpenSTAT tables that carry the provincial rows were last updated 2026-10-06, inside the first week of the month. That is consistent with provincial values being posted with the national release. **Exact provincial release dates remain unverified**, so the conservative +14-day proxy is kept. E24v2 adds **Dnow**, the months-1–2 provincial deviation. |

**Result on 94 never-examined quarters** (1997–2020, frozen before download; HB1–HB4 all supported after Holm, stable in both halves):

| Lead 1, T2 = 1[D > 0] | Accuracy | Brier | ROC-AUC |
|---|---|---|---|
| Persistence | 0.617 | 0.383 | 0.617 |
| Calibrated persistence | 0.609 | 0.240 | 0.595 |
| E24-frozen LR on label history (M1) | **0.670** | 0.209 | 0.742 |
| **D nowcast model (M4)** | **0.713** | **0.186** | **0.792** (95% CI 0.745–0.835) |

**Lead time (M4).**

- The E23 reliability rule holds at leads 1–5.
- Against calibrated persistence, it holds at leads 1–2.

## 4. Provincial differentiation: what the label can and cannot say

**The provincial ordering the label produces.** The label's provincial ordering is relative food inflation. It does **not** follow measured provincial poverty. These are descriptive comparisons only (n = 5 provinces, so no inference):

| Comparison (Spearman) | Value |
|---|---|
| PCF mean probability vs mean poverty incidence 2018–2023 | −0.67 |
| Mean D vs 2023 subsistence incidence | −0.60 |

Quezon has the highest measured poverty but one of the lowest composite-risk probabilities.

**What PSA measures.** PSA's measured provincial food poverty (subsistence incidence) is low and imprecise:

- CVs of 18–62%;
- in 2023 the five provinces' 95% intervals overlap (Quezon 0.1–1.7%, Rizal 1.4–3.9%).

So the measured data themselves show little provincial separation in food poverty in 2023.

**Conclusion.** Provincial forecasts are defensible **as relative food-price-pressure forecasts** (validated on unseen quarters). They are **not** defensible as differences in provincial food insecurity. The dashboard now shows the two separately, next to PSA's measured provincial values with their intervals.

## 5. The 142 LGU rankings

| Finding | Evidence |
|---|---|
| 126 of 142 LGUs have no PSA municipal poverty estimate in the authorized data | Their within-province order equals their density order (Spearman 1.0 in every province) |
| **Density and poverty run in opposite directions** | Among the 16 LGUs with municipal estimates, Spearman(poverty, density) = **−0.76**. In the approved index 0.6·poverty + 0.4·density, the density term therefore pushes against the poverty term. |
| The province probability barely matters for the order | Region-wide Spearman(risk, vulnerability) = 0.99; province probabilities in the replay range only 0.65–0.73 |

**Consequence.** For most LGUs, the current ranking is a density ranking. That cannot be read as relative vulnerability.

**The fix is a data fix.** It needs PSA's 2021 municipal small-area estimates (`2018 - 2021 SAE_with PSGC_noHUC.xlsx`). psa.gov.ph returns HTTP 403 (Cloudflare) to non-browser requests, and that was not bypassed. Ingestion and validation code is ready.

**A method question for your adviser** follows from the negative correlation: whether density should enter as a vulnerability weight at all (checklist B9).

## 6. What was fixed in code, and what needs data or decisions

| Limitation | Fixed by code in E24v2? | What remains |
|---|---|---|
| D history too short; nowcast information unused | **Yes**: long PSA series, Dnow, validated on unseen quarters | — |
| No probabilities or uncertainty for decision use | **Yes**: PCF gives calibrated probabilities, 80% intervals, a signal level, and a component split (regional vs provincial) | — |
| No route to unseen-quarter evidence for T1 | **Partly**: two blind prospective seals (2026-Q3, 2026-Q4, 2027-Q1); the A2 back-cast runner is ready | Your authorization of outcomes; the SWS history file |
| Regional hunger not forecastable from 2021–2025 | No (data limit) | Long SWS history (A2), or new quarters |
| 126 LGUs without municipal poverty | No (data limit) | PSA SAE workbook (manual download) |
| Provincial food-insecurity outcome | No (does not exist publicly) | FNRI/PSA provincial FIES, CBMS |
