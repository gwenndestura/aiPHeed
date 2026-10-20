# E73 protocol: remediation of Objectives 1–4 (frozen before any E73 search or computation)

**Frozen:** 2026-10-20. sha256 (LF) in `runner/PROTOCOL_SHA256.txt`. **Branch:** `final-aipheed-thesis-e72`.

## 0. Rules

- **No human labels are produced or simulated.** Synthetic data appears only in unit tests, labelled as synthetic.
- **Web searches are restricted:**
  - only for outcome or reference data of 2021–2025, or methodology;
  - no "latest", "current" or 2026 queries for PSA CPI, BSP or SWS series;
  - `sws.org.ph` is not opened.
- **Provenance.** Every value admitted from the web is written to `inputs/provenance.csv` at the moment it is found: URL, outlet, publication date, fieldwork dates, value, and the text it was read from. A value that cannot be traced to its source text is not admitted.
- Any exposure of a 2026-H2 SWS or PSA CPI value is logged in `CONTAMINATION_LOG.md`.
- **No served value changes** unless a rule below says it may.

## 1. Objective 1: independent-reference validation of the news layer (WS1)

**Data.** Admitted v3 articles (`app.news.pipeline_v3.admitted()`), counted by publication quarter. Provincial triggers use province-attributed articles. National triggers use all admitted articles.

### 1a. Criterion validity of trigger classification against official event measures

| Trigger | Official reference | Level |
|---|---|---|
| climate | PAGASA tropical cyclones | province-quarter |
| market | PSA food CPI YoY | province-quarter |
| fish_kill | −(fish + aquaculture YoY) | province-quarter |
| employment | LFS unemployment + underemployment | national quarter |
| ofw_remittance | −remittance YoY | national quarter |

- **Statistics:** Spearman ρ with a quarter-cluster bootstrap 95% CI (B = 4000, seed 73). For provincial triggers, also a within-province version (values demeaned by province).
- **Pass for a trigger:** pooled CI lower bound > 0.

### 1b. Bias correction

Compared against the reference event composite (mean adverse percentile of the official measures above, 2021–22 reference, as in E71):
- FSSI-v3 as served (log weight);
- uncorrected mean intensity;
- a pre-specified empirical-Bayes alternative: mean intensity shrunk toward that quarter's mean over provinces, weight n/(n + k), k = median n of cells with n > 0.

**Pass rules:**
- The served correction is **validated** only if its ρ exceeds the uncorrected ρ with the bootstrap CI of the difference > 0.
- The EB alternative may replace the served correction only if it beats both with CI > 0.

### 1c. Coverage

Report, by province, outlet, language test, trigger and quarter:
- article counts;
- share of province-quarters SUFFICIENT;
- national share.

### 1e. Regional news value

**Question.** Does news add skill for the regional hunger outcome?

**Method.** Expanding-window forecasts of SWS hunger at t + 2 (approved rounds published before O(t)):
- RW = the latest reading;
- RW + b × z(news) = the latest reading plus a slope on the standardised count of admitted articles in quarter t, fitted on earlier pairs only (≥ 6).

**Pass:** lower mean absolute error AND absolute errors smaller in a majority of quarters (two-sided sign test p < 0.05).

## 2. Objective 2: independent outcomes (WS2)

### 2a. Searches

1. a second regional involuntary-hunger survey with quarterly rounds 2021–2025 (for example OCTA Research *Tugon ng Masa*);
2. FNRI NNS 2023 household FIES by province;
3. CBMS 2022/2024 FIES by city or municipality in CALABARZON.

### 2b. Second regional hunger series O2

O2 is used only if there are ≥ 6 rounds in the window for the area containing CALABARZON (Balance Luzon or Luzon outside NCR, or CALABARZON if published).

- **Quarter:** the fieldwork quarter.
- **"Elevated":** O2 value > median of the O2 rounds with fieldwork in 2021–2023. If there are fewer than 3 such rounds, the median of the first 4 rounds.
- **Compared at Lead 2, with the estimate issued before the round:**
  - FIRI v2 regional class (mean of the five province indices ≥ 0.5);
  - FIRI v2 without its regional-hunger domain;
  - the latest SWS reading > 11.3;
  - always-elevated.
- **Metrics:** accuracy (Wilson), balanced accuracy, exact McNemar vs always-elevated, Spearman of the regional mean index vs the O2 level with a bootstrap CI, and concurrent SWS–O2 Spearman (construct check).
- **O2 has never been used in this project, so it is genuinely unseen evidence.**
- **80% rule:** independently supported at Lead 2 only if O2 accuracy ≥ 0.80 AND balanced accuracy ≥ 0.70 AND Spearman CI lower bound > 0.

### 2c. Provincial and LGU outcomes

- **O3 (FIES by province):** Spearman with the 2023 province means of FIRI v2, FIRI v2 without H, FIR71, and E56 P(price). Face validity only: with 5 units, ρ ≥ 0.9 is needed for p < 0.05.
- **O4 (CBMS FIES by LGU), if ≥ 30 LGUs:** Spearman of the LGU prioritization index vs FIES, compared with poverty-only and density-only. Within-province results are also reported.

## 3. Objective 3: prioritization robustness (WS3)

**Alternatives to the approved 0.6 poverty + 0.4 density with min-max scaling inside each province:**
- weights 0.5/0.5, 0.7/0.3, 0.8/0.2, 1/0 and 0/1;
- rank normalisation instead of min-max;
- log-density.

**Reported:**
- within-province Spearman of the LGU order vs the approved order;
- top-5 overlap per province;
- the share of LGUs whose priority tercile changes.

**Robust:** every alternative with poverty weight ≥ 0.5 keeps Spearman ≥ 0.9 in every province.

**LGU band.** An opt-in flag `AIPHEED_LGU_BAND=province` gives every LGU its province's estimated class, with the LGU value kept as within-province priority. The default stays unchanged.

## 4. Objective 4: stability of comparisons (WS4)

- Sub-periods: target quarters ≤ 2024-Q4 vs ≥ 2025-Q1.
- Models: FIRI v2 (regional outcome) and E56 vs persistence (T43).
- Per-province results.
- Holm adjustment within each family.

## 5. Explanations (WS5)

- The backend exposes `explanationMethod` in `/api/v1/config`: "TreeSHAP" when the served drivers are TreeSHAP, and "Index contribution breakdown" in thesis mode.
- Frontend headings read it, with "SHAP" as the fallback. This is a text change only: no new element, colour or layout.
- Factor-card text names the food-security dimension of each indicator.
