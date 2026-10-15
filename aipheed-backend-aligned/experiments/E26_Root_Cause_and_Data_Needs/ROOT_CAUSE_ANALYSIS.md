# Root cause: why aiPHeed cannot yet show reliable, useful and accurate forecasts

**Evidence used:**

- **Diagnostics** on development quarters 2021-Q1…2026-Q2, which were all examined before (sections A–C of `FROZEN_ANALYSIS_PROTOCOL.md`).
- **A synthetic simulation** whose parameters were fitted on authorized 2021–2026 data (section D and amendment A2).

**What these analyses do not do:** none of them selects a model, threshold, feature or target. Numbers come from `runs/root_cause.json`, `runs/voi_predictions.csv` and `runs/horizon.json`; all three reproduce byte for byte (`runs/reproducibility.json`).

**Answer in one paragraph.** The limitation is **not code**. Five data and design facts cause it:

- The approved label is dominated by **one regional survey series**.
- That series moves like a **random walk with survey noise**, so persistence is close to the best possible forecast.
- The **expanding-median threshold** makes almost every evaluation row HIGH.
- The **provincial part of the label is a short-lived price fluctuation**, not a stable local difference, and **no local food-insecurity outcome exists** in the authorized data.
- **Too few independent quarters** exist, or will exist soon, to show that any model beats persistence.

A fresher regional reading would help. A correctly specified model with a strong leading signal still has a small chance of a valid claim before 2031.

---

## Cause 1. The label is one regional series repeated five times

| Quantity (2021-Q1…2026-Q2, reading A) | Value |
|---|---|
| Quarters in the window | 22 |
| SWS production rounds | 20 |
| Quarters with an approved label | **18** (none for 2021-Q1, 2022-Q1, 2025-Q2, 2025-Q3) |
| Independent regional outcome series | **1** (SWS Balance Luzon hunger, H) |
| Provincial food-insecurity outcomes in the authorized data | **0** |
| T1 rows (province × quarter) | 90 |
| Share of label variance from the regional H | **0.68** |
| Share of label variance from 2D (provincial relative food inflation) | 0.32 |

H is identical for the five provinces, so the 90 rows carry about 18 regional observations plus a provincial price term. The **unit of evidence is the forecast date, not the row**: 8 dates at lead 1 in E25, 7 at lead 2, 5 at lead 3.

## Cause 2. The threshold makes the evaluation quarters almost all HIGH

The threshold τ is the median of the labels published before the origin.

- **Over all 90 rows**, a median split gives 45 LOW rows.
- **On the evaluation dates**, the threshold comes from earlier quarters whose labels were lower. Later quarters therefore sit above it:

| Lead | Dates | HIGH rows | LOW rows | Label changes |
|---|---|---|---|---|
| 1 | 8 | 37 | 3 | 5 |
| 2 | 7 | 33 | 2 | 6 |
| 3 | 5 | 23 | 2 | 4 |
| 4–6 | 2–3 | 9–14 | 1–2 | 1–2 |

**Consequences:**

- Accuracy above 75% is automatic: persistence scores 0.83–0.89 and always-HIGH 0.91–0.94.
- Criterion C6 (≥ 5 LOW rows) is unreachable at every lead.
- Against 0/1 persistence, the best attainable one-sided p is 2^−m, where m is the number of dates on which persistence errs (E25 `docs/REACHABILITY.md`).

## Cause 3. Regional hunger behaves like a noisy random walk, so persistence is near-optimal

**Fitted on the 2021–2026 production rounds:**

- local-level innovation sd **2.70 percentage points per quarter**;
- level at 2026-Q2 **18.08**;
- a quarter has no production round with probability **0.143**.

**Survey noise in round-to-round changes** (19 changes, variance 14.2):

| Balance Luzon sample per round | Share of change variance that is sampling noise | P(observed direction = true direction) |
|---|---|---|
| 300 respondents | **0.58** | 0.72 |
| 600 respondents | **0.29** | 0.82 |

The per-round sample size is **not verified** in the authorized data (see `SOURCE_INVESTIGATION.md` S1).

For a random walk, the best forecast of the next level is the current filtered level. A probabilistic model can therefore improve **calibration** (the Brier score) over 0/1 persistence, but it cannot anticipate the **direction** of the next move from the series itself. This is what E25 found: PCF21 ties persistence on accuracy and wins on Brier only before multiplicity adjustment.

## Cause 4. Timing: the current quarter's reading is not published at the origin

At origin O(t), the first day of quarter t+1, the forecaster does not yet have SWS quarter t.

- The SWS round for quarter t has its fieldwork inside t but is published after it ends.
- The label of t also needs D(t), whose third CPI month is released in quarter t+1.

**Value of information** (section C). The rows are identical across all sets and models; the p-value is a one-sided exact sign-flip over dates of the Brier difference.

| Lead (dates; HIGH/LOW) | Set | Model | Accuracy | Brier | Label changes anticipated | p vs persistence, same set |
|---|---|---|---|---|---|---|
| 1 (9; 41/4) | I0 status quo | B1 persistence | 0.889 | 0.111 | 0 of 5 | — |
| | I0 | B1p calibrated | 0.889 | 0.152 | 0 of 5 | 0.97 |
| | I0 | PCF21 | 0.867 | 0.103 | 0 of 5 | 0.36 |
| | I0 | PCF21_NOW | 0.889 | 0.104 | 1 of 5 | 0.38 |
| | **I1 timely regional round** | PCF21 | 0.911 | **0.080** | **2 of 5** | 0.21 |
| | I3 label of t known | B1 | 0.889 | 0.111 | 0 of 5 | — |
| | I3 | PCF21 | 0.911 | 0.083 | 1 of 5 | 0.14 |
| | IO oracle (target H known) | — | 0.956 | 0.038 | 4 of 5 | 0.047 |
| 2 (7; 33/2) | I0 | B1 | 0.829 | 0.171 | 0 of 6 | — |
| | I0 | B1p | 0.829 | 0.129 | 0 of 6 | 0.086 |
| | I0 | PCF21 | 0.857 | 0.132 | 1 of 6 | 0.047 |
| | **I1** | PCF21 | 0.914 | **0.082** | **3 of 6** | **0.031** |
| | I1 | PCF21_NOW | 0.886 | 0.084 | 2 of 6 | 0.047 |
| | I3 | B1 | 0.914 | **0.086** | 0 of 3 | — |
| | I3 | PCF21 | 0.914 | 0.077 | 1 of 3 | **0.43** |
| | IO oracle | — | 0.943 | 0.041 | 4 of 6 | 0.031 |
| 3 (5; 23/2) | I0 | B1 | 0.840 | 0.160 | 0 of 4 | — |
| | I0 | PCF21 | 0.880 | 0.120 | 1 of 4 | 0.0625 |
| | **I1** | PCF21 | 0.920 | **0.091** | 2 of 4 | 0.0625 |
| | I3 | B1 | 0.880 | 0.120 | 0 of 3 | — |
| | I3 | PCF21 | 0.920 | 0.088 | 1 of 3 | 0.125 |

The complete table, including B1p and PCF21_NOW under every set, is in `runs/root_cause.json`.

**Reading.**

1. **A timely regional reading (I1) is the most valuable realistic information.** It lowers the PCF21 Brier score to about 0.08 at every lead and anticipates 2 to 3 label changes. At lead 2 it beats persistence with the same label information (p = 0.031, 7 dates). This is development evidence and exploratory: three leads and four sets were examined, and no multiplicity adjustment is applied.
2. **Most of that value is knowing the current regional level earlier.** When the label of quarter t is also known (I3), persistence itself improves (lead 2: Brier 0.171 → 0.086). PCF21's margin over persistence with the same information then disappears (p = 0.43).
3. **The months 1–2 CPI reading (PCF21_NOW) adds nothing to T1 at any lead.** This matches E25.
4. **Even the oracle,** which knows the target quarter's regional hunger, anticipates only 4 of 5 (lead 1) and 4 of 6 (lead 2) changes. The remaining changes depend on the provincial price term.

## Cause 5. The provincial part is a short-lived price fluctuation, and there is no local outcome

| Quantity (D, 2021-Q1…2026-Q2) | Value |
|---|---|
| Total variance of D | 2.78 |
| Pooled AR(1) persistence φ | **0.73** (a deviation halves in about 2.2 quarters) |
| Between-province variance of long-run province means (empirical Bayes, as in D_HIER) | **0.00** |
| Raw province means | Rizal +0.58, Quezon −0.01, Batangas −0.02, Laguna −0.22, Cavite −0.33 |

With φ = 0.73 over 22 quarters, the standard error of one province mean is about 0.9. Every raw mean is therefore within about one standard error of zero.

**Over 2021–2026, no province has a detectably persistent food-price disadvantage.** The 2D term marks temporary relative price pressure, so it cannot show which provinces are persistently at higher food-insecurity risk.

D is also a **constructed** indicator: provincial food inflation minus the five-province mean. It is not a measurement of food insecurity, and the authorized data contain **no provincial or municipal food-insecurity outcome** against which a provincial or LGU ranking could be checked. The backend (`pcf_engine.forecast`) therefore reports it separately (two-layer output, section G) and label it "CONSTRUCTED INDICATOR — not a verified food-insecurity outcome".

## Cause 6. Too few independent unseen quarters

**Horizon simulation** (section D and amendment A2): 10,000 paths, seed 20261014. The simulated forecaster **knows the true parameters**, so every probability is an upper bound for a real model. Dates accrue from target 2026-Q4.

| By year end | Scored dates (median) | P(evaluable: ≥ 8 dates, ≥ 5 HIGH, ≥ 5 LOW) |
|---|---|---|
| 2027 | 4 | 0.00 |
| 2028 | 8 | 0.42 |
| 2029 | 11 | 0.74 |
| 2031 | 18 | 0.83 |

**Chance of a valid claim against both persistence baselines by the end of 2031:**

| Scenario | Frozen e-process rule | A1 single look, accuracy (approved C2) | A1 single look, Brier (if P2 approved) | **A3 success** (beats all 4 references), accuracy | A3 success, Brier |
|---|---|---|---|---|---|
| S0 status quo | 0.000 | **0.030** | 0.126 | **0.0003** | 0.009 |
| S_timely (round of t at O(t)) | 0.000 | 0.056 | 0.179 | 0.003 | 0.023 |
| Leading signal ρ = 0.5 | 0.000 | 0.043 | 0.152 | 0.002 | 0.015 |
| Leading signal ρ = 0.7 | 0.000 | 0.071 | 0.194 | 0.004 | 0.028 |
| Leading signal ρ = 0.9 | 0.000 | **0.125** | 0.293 | **0.012** | 0.059 |

A3 is the brief's success standard: beat persistence, calibrated persistence, always-HIGH and climatology, each at 0.05/4 (`PROTOCOL_AMENDMENT_A3.md`, pending approval).

**Minimum signal requirement (amendment A2).** No tested timeliness or signal strength up to ρ = 0.9 makes a valid claim more likely than not by 2031. Under the success standard (A3), none reaches even 0.06.

The reason is not the model. The per-date advantage of even an ideal forecaster over calibrated persistence is small (Brier 0.027 in S0, 0.067 at ρ = 0.9), and label changes are rare. On the approved accuracy metric, **a claim of beating persistence on unseen quarters is very unlikely to be demonstrable within the thesis timeline, whatever the model.**

**The frozen e-process cannot reach its threshold before 2031 in any scenario.** With bets capped at 0.5, a steady advantage of 0.1 per date reaches e ≈ 2.6 after 20 dates (threshold 40). This design defect is why amendment A1 exists. A1 is pending adviser approval.

---

## What would remove each cause

| Cause | What removes it | Type | Status |
|---|---|---|---|
| 1 One regional series | More independent outcome units: LGU or provincial food-insecurity outcomes (CBMS FIES, FNRI NNS, PSA subsistence incidence). Other SWS area series as auxiliary evidence for the method. | Data + adviser approval to count them | `MISSING_OBSERVATIONS_SPEC.md` O1–O4 |
| 2 Threshold → almost all HIGH | Not removable without changing the approved target or criteria. Report Brier, change anticipation and HIGH/LOW counts beside accuracy. | Adviser decision | `ADVISER_APPROVAL_REQUEST.md` R3 |
| 3 Random walk + survey noise | Verified per-round SWS sample sizes, so the model weights each round correctly (implemented as optional `n_respondents`). A leading signal of regional hunger changes (none found in authorized data). | Data | O5, O7 |
| 4 Timing | An earlier regional reading (SWS microdata or a release-date commitment). Nothing in the code can create it. | Data (external) | O5 |
| 5 No local outcome; D transient | CBMS 2022/2024 LGU FIES: 142 units, 80% power to detect a rank correlation of 0.3. A 5-province cross-section can detect only ρ ≥ 0.9 (`runs/local_power.json`). | Data + authorization | O1 |
| 6 Too few unseen quarters | Keep sealing every quarter. Authorize each outcome. Approve A1. The first valid look comes at the end of 2029 at the earliest (median 11 dates by then), more likely 2030. | Time + authorization + adviser | O6, R1 |
