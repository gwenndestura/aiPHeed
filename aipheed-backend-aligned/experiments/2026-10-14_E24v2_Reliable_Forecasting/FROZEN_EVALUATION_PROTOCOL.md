# E24v2 Frozen Evaluation Protocol

**Written 2026-10-14, before:**

- any 1994–2020 PSA value was downloaded;
- any new model was fitted.

**Freeze:** `runner/PROTOCOL_SHA256.txt` holds the SHA-256 of this file. Every E24v2 runner refuses to start if the file has changed. Section 10 lists the changes made after the freeze; each is flagged where it is used.

**What E24v2 inherits unchanged:**

- the approved target T1, its threshold rule and its test rows (E23/E24);
- the six required baselines and the proposed model;
- E24's acceptance criteria C1–C9;
- E24's exploratory target T2.

**E24 remains untouched.**

**Nothing in this protocol weakens a criterion.** Every new element is an additional candidate, an additional (stricter) baseline, or an additional test set.

## 0. Why a new protocol is needed (from the E24 evidence)

- **T1's label changes are driven by the regional SWS level of the target quarter.** Persistence errs only on those rows.
- **The 2021–2025 history is 20 rounds.** It cannot estimate how a hunger series moves, so short-window models over-react (E13).
- **The only provincial part of T1 is D** (relative food inflation). D is measured by PSA every month **since 1994**, but only 2021–2025 was ever used.
- **All 2021–2025 rows have been examined.** Any result on them is development evidence.

**Two new sources of unseen evidence are therefore used:**

| Source | What it is |
|---|---|
| **(A) Back-cast (BX)** | PSA's 2018-based provincial food CPI for 1994–2020, never opened by any experiment, used to test provincial forecasting on ~95 unseen quarters |
| **(B) Prospective seal** | Forecasts made now from authorized data only for 2026-Q3 onward, whose outcomes are protected and unseen |

## 1. Evidence classes

| Class | Rows | Status |
|---|---|---|
| **A: confirmatory, unseen** | BX: T2 at targets 1995–2020 (first target set by the minimum-training rule) | Never examined. Hypotheses HB1–HB4 (Section 6) are confirmatory. |
| **B: prospective, blind** | Seal issued 2026-10-14 for targets 2026-Q3, 2026-Q4, 2027-Q1 (origin 2026-07-01) | Scored only after you authorize those outcomes. **This is the only route to C9 for T1.** |
| **C: development** | T1 and T2 at 2021–2025 (E23/E24 rows), plus 2026-Q1/Q2 (viewed in E18) | Descriptive. **Never counts as generalization.** |

## 2. Data

### 2.1 Back-cast data (acquired by `acquisition/fetch_openstat.py`; public PSA OpenSTAT)

| Table | Content | Years requested |
|---|---|---|
| `DB/2M/PI/CPI/2018NEW/0012M4ACP28.px` | CPI 2018=100, back-casted | 1994–2017 |
| `DB/2M/PI/CPI/2018NEW/0012M4ACP22.px` | CPI 2018=100 | 2018–2020 (back-cast); 2021–2025 (comparability check only) |
| `DB/2M/PI/CPI/2018NEW/0012M4ACP23.px` | Published year-on-year % | 2019–2020 (comparability check only) |

**Selections:**

- Geolocation codes 33 Batangas, 34 Cavite, 35 Laguna, 36 Quezon (excluding Lucena, as in E12), 37 Rizal.
- Commodities: 0 All items, 2 "01.1 Food", 5 "01.1.1.12 Rice".
- Monthly periods only.

**The fetch script refuses to request any year ≥ 2026** and asserts that no response contains one. Every raw response is saved, with its query, the retrieval time and its SHA-256 (`acquisition/raw/`, `acquisition/ACQUISITION_MANIFEST.json`).

**Authorization basis.** These are public, official, pre-2026 PSA statistics. They are within Chapter I §1.7's data scope ("publicly available data from PSA …") and outside every protected category: 2026 outcomes, news, restricted survey rounds. This is recorded for your confirmation in `ADVISER_AND_AUTHORIZATION_CHECKLIST.md`. **No 2026 value is requested.**

### 2.2 Derivation (identical to E12 for D)

- **Monthly year-on-year rate:** YoY(p,m) = 100·(I(p,m)/I(p,m−12) − 1), from indices. The 2018 rates join the 2017 back-cast index to the 2018 index.
- **Quarterly rate:** F(p,q) = mean of the three monthly YoY values.
- **Relative pressure:** D(p,q) = F(p,q) − mean over the five provinces. Defined only when all five provinces have all three months.
- **T2 label:** 1[D > 0].

### 2.3 Comparability gate (run after acquisition, before any back-cast scoring)

**(i) Against the approved values.** Recompute F and D for 2021-Q1…2025-Q4 from the 0012M4ACP22 indices and compare with E12's `realized_components_2021_2025.csv`. **Pass iff** max |ΔD| ≤ 0.20 percentage points **and** sign(D) agrees on ≥ 95% of rows with |D| ≥ 0.05.

**(ii) Within the back-cast period.** Compare the index-based monthly YoY for 2019–2020 with PSA's published YoY (0012M4ACP23). **Pass iff** the median |Δ| ≤ 0.15 pp.

**If either check fails, the back-cast is void** and is reported as such.

### 2.4 Pseudo-real-time information rule (single data vintage)

At origin O(t) (00:00 PHT, first day of quarter t+1):

- **Quarterly D labels** are known for quarters ≤ t−1 (as in E24 T2).
- **Monthly CPI** is known for months ≤ the **second** month of quarter t.
  - Basis: national release ≈ the 5th of the following month; the provincial proxy is +14 days (E24 register).
  - So month 2 of quarter t is out by about the 19th of month 3, before O(t). Month 3 of quarter t is not.

**Limitation (stated, not fixed).** The back-cast uses today's re-based vintage. Real-time 1995–2017 vintages on this base did not exist. CPI is not revised apart from re-basing, and D is a within-quarter difference, so the effect on D is expected to be small. Gate (i) measures the vintage difference on 2021–2025.

### 2.5 Other inputs (authorized, unchanged)

| Input | Source |
|---|---|
| 2021–2025 S1 / H / D components and SWS rounds | E12 run `20261012T151208Z` (hash-pinned) |
| 2026 January–June provincial CPI and SWS March/June 2026 | E18 authorization |
| E23/E24 predictions | Read from their sealed run folders, with seals re-verified |

### 2.6 Descriptive validity data

PSA OpenSTAT FY poverty tables, years 2018/2021/2023: subsistence incidence and poverty incidence among population, by province, with CVs. Fetched by the same script. Used **descriptively only** (Section 8).

## 3. Targets

**T1 (approved, required).**

- S1 = H + 2D.
- τ = median S1 over labels published before O(t) (E23 rule; the label counts as published iff its quarter ≤ t−1 and every definition-A SWS round of that quarter was published before O(t)).
- **Unchanged.**

**T2 (exploratory, as E24).** 1[D > 0].

## 4. New models (fixed now; no tuning on any test row)

### 4.1 Calibrated persistence (B1p): a new, stricter baseline

**P(HIGH)** = (a+1)/(n+2) among the training pairs at that lead with the same last-published label as the test row.

- Training pairs: published before O(t), the same pairs the other models use.
- Its decisions equal persistence's whenever both rates lie on the persistence side of 0.5.

**Why it is needed.** Hard persistence has Brier = error rate, so any calibrated model beats it on Brier trivially. **"Information beyond persistence" in probability terms is therefore judged against B1p.**

### 4.2 Provincial component model PCF-D (M3)

For lead k:

- **Regression:** D(p, t′+k) = β_k · Dlast(p,t′) + e, fitted by least squares **without intercept** (D is mean-zero within a quarter by construction).
- **Training pairs:** every province and every origin t′ whose target t′+k ≤ t−1, using **all D history available before O(t)** (from 1995 in BX; from 1995 plus 2021+ in classes B and C).
- **Uncertainty:** σ_k = RMS residual, with denominator n−1.
- **Output:** P(D > 0) = Φ(β_k·Dlast / σ_k).
- Dlast = the latest published quarterly D (quarter t−1).

### 4.3 Provincial nowcast model PCF-D-NOW (M4)

- **Same as M3**, with predictors [Dnow, Dlast] (least squares, no intercept).
- **Dnow(p,t)** = mean over months 1–2 of quarter t of (monthly YoY_p − five-province mean monthly YoY).
- **Rationale:** this information is available at O(t) and was not used by E23/E24, whose government features stop at t−1.

### 4.4 E24-frozen candidates (re-used exactly)

- **M1 = ABL_lr_P:** logistic regression, median imputation, standardization, C = 1, on P = [v_last, margin_last, y_last, v_mean4, v_diff].
- **M2 = ABL_lgbm_P:** nested LightGBM on P (E23 grid and inner rule).

### 4.5 PCF: probabilistic component forecaster for T1

**Output:** P(S1 > τ) = 1 − Φ((τ − μ_H − 2μ_D) / sqrt(V_H + 4σ_D²)).

The two components are independent because D sums to zero within each quarter.

**D part:** M3 at the same lead.

**H part: a local-level (random-walk-plus-noise) model of the regional SWS series.**

- **Observations:** definition-A rounds published before O(t), placed at their fieldwork quarter. Two rounds in the same quarter are two observations at the same time.
- **Sampling variance:** s² = H(100−H)/n.
  - n = 600 (SWS Balance Luzon sample, consistent with SWS's ±4% Balance Luzon margin of error).
  - Sensitivity: n = 300.
- **Level variance q:** maximum likelihood (Kalman filter, diffuse start), using only those rounds. Grid of σ_η = 0.0, 0.1, …, 8.0 percentage points per quarter.
- **Forecast:**
  - μ_H = the filtered level at the last observation;
  - V_H = P_last + g·q + s²(μ_H), where g = target quarter − last observed quarter.

**Decision:** P ≥ 0.5.

**Variant PCF-S (exploratory, class C only).** The same H filter also takes the supplementary SWS rounds that were published before O(t) (verified dates) as observations. **This variant was conceived after seeing the E24 error table** (the 2025-Q4 change follows the supplementary June 2025 round). Its development result is **therefore not evidence**. It is sealed prospectively (class B) so that it can be tested.

### 4.6 Final E24v2 candidates (declared now)

| Target | FINAL_V2 |
|---|---|
| T1 | **PCF** |
| T2 | **M4** (PCF-D-NOW) |

The E24 acceptance criteria C1–C9 are applied to FINAL_V2 **exactly as defined in E24** (Section 5 there).

**Additional rule:** "strongest applicable baseline" now also includes B1p. Adding a baseline can only make C2 harder.

## 5. Origins, leads and rows

| Class | Origins and rows |
|---|---|
| **C** | The same origins, leads (1–8) and rows as E24, asserted identical (y, threshold, province, origin) against E24's sealed `predictions_T1.csv` / `predictions_T2.csv` |
| **A (BX)** | Origins t from 1995-Q1 to 2020-Q3, leads 1–8, targets ≤ 2020-Q4. A test origin needs ≥ 8 distinct labelled training target quarters at that lead. **No 2021+ value enters BX training or testing.** |
| **B** | Origin O(2026-Q2) = 2026-07-01. Targets 2026-Q3 (k=1), 2026-Q4 (k=2), 2027-Q1 (k=3). |

**Class B inputs:**

- SWS rounds with a **verified** publication date before 2026-07-01;
  - 2026 rounds have no verified date, so they are **excluded** (conservative);
  - this also excludes the 2026-Q1 label from τ;
- D labels ≤ 2026-Q1;
- Dnow from April–May 2026 (authorized).

**Class B models:** B1, B1p, PCF, PCF-S, M2 (T1); B1, B1p, M1, M3, M4 (T2).

**Seal:** SHA-256 of the CSV, written to `SEAL_PROSPECTIVE.json` and reported.

## 6. Statistics

**Metrics:** as E24 (accuracy, balanced accuracy, precision, recall, F1, ROC-AUC, Brier, confusion counts).

**Independent unit:** the origin (quarter).

**Paired tests:** exact or seeded Monte Carlo sign-flip on per-origin differences (seed 20261013, 50,000 assignments when > 16 origins), and paired AUC permutation (E23 library).

### Confirmatory family (class A, T2, lead 1; one-sided α = 0.05; Holm over the four)

| ID | Hypothesis |
|---|---|
| **HB1** | M1 Brier < B1p Brier |
| **HB2** | M1 accuracy > B1 accuracy |
| **HB3** | M4 Brier < B1p Brier |
| **HB4** | M4 accuracy > B1 accuracy |

**Stability.** A confirmatory claim also needs the same sign of the mean difference in both halves of the BX origins (first and second half by origin date).

### Lead time (class A, T2)

**Reliability rule** (E23, unchanged), for M4:

- ≥ 8 origins;
- ≥ 5 per class;
- AUC origin-cluster bootstrap lower bound > 0.5;
- Brier better than **B1** with Holm p < 0.05 across leads 1–8.

The **stricter version** uses B1p in place of B1; both are reported.

**Furthest reliable lead** = the largest k such that every lead ≤ k passes.

### Class C

- E24's tests and criteria C1–C9 for FINAL_V2 (T1: PCF; T2: M4).
- Also PCF vs B1p (Brier).

## 7. Noise ceiling (class C, descriptive)

For each T1 lead-1 test row:

- z = (S1 − τ) / SE_H, with SE_H = sqrt(H(100−H)/n) (n = 600; 300 as sensitivity);
- p_flip = Φ(−|z|), the chance that SWS sampling error alone puts the published label on the other side of τ.

**Reported:**

- Σ p_flip over all rows;
- Σ p_flip over persistence's error rows.

**Descriptive:** it bounds how much of the label is unforecastable sampling noise.

## 8. Provincial validity and the 142 LGUs (descriptive)

- **Provincial validity.** For 2018, 2021 and 2023, compare provincial PSA subsistence incidence and poverty incidence (measured, with CVs) with the provincial means of D, S1 and the PCF probability.
  - With n = 5 provinces this is description, not inference.
- **LGU density check.** Within-province Spearman correlation between the approved risk index and population density, using the E24 v2 LGU table.

## 9. What would count as success

| Claim | Requires |
|---|---|
| **The forecasting goal (T1, Chapter I)** | E24 C1–C9 for FINAL_V2, with C9 from class B only once scored |
| **Provincial component generalizes** | HB1–HB4 as declared in Section 6, with stability |
| **Development results** | Never sufficient on their own |

## 10. Amendments after freeze

Each amendment below is logged with a reason and flagged wherever it is used.
