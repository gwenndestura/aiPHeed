# E12 Protocol: SWS Weight Analysis and Two-Layer Provincial Scoring

**Frozen 2026-10-12, before the comparative analysis.** The runner records this file's SHA-256.

**Naming.** Your request named the folder `E11_SWS_Scoring_Comparison`. E11 already exists (`2026-10-12_E11_LightGBM_Improvement`), so this experiment is **E12**. E9, E10 and E11 are read-only.

## 1. Questions

1. How should regional hunger (H) be represented?
2. How should relative provincial food-price pressure (D) be represented?
3. Does combining them give a defensible score for predicting future outcomes?

**What E12 can and cannot establish.** No independent province-level food-insecurity outcome exists in the research record, so **E12 cannot validate actual food insecurity in any province.**

| Category | What it covers | Status |
|---|---|---|
| A (descriptive) | Score behaviour, regional vs provincial information, rankings, spread, coverage, stability, classification behaviour under explicitly defined thresholds | Performed |
| B (forecast, internal consistency only) | Target = next-quarter S1, a **constructed** indicator. Because S1 defines the target, this comparison inherently favours scores closest to S1. | Performed and labelled as such |
| — | Genuine food-insecurity forecasting accuracy | **Not evaluable** |

## 2. Data

- **Source:** the E9 allowlist, read through the E12 guard (hash-pinned, row filter ≤ 2025-Q4, pre-2021 dropped). E9's frame and S1 reference are read-only from the E9 folder.
- **H[t]:** mean of the definition-A Balance-Luzon rounds in quarter t (SWS registry; publication dates verified or verified-single).
- **F[p, t]:** PSA provincial food CPI YoY (quarterly mean of monthly values); release dates are proxy (unverified).
- **D[p, t] = F[p, t] − mean of the five provinces' F[t]:** defined only when all five provinces have F.

## 3. S1 baseline (frozen)

**S1 = H + 2D.** Missing stays missing.

**Reproduction gate:**

| Reference | Required | Result (pre-run investigation, `s1_reproduction_investigation.json`) |
|---|---|---|
| E9 approved output `s1_targets_2021_2025.csv` | Max abs difference ≤ 1e-9 | **3.6e-15: pass** |
| `labels.parquet` `stress_score` | — | **3.3e-5: exceeds 1e-9** |

**Investigation of the `labels.parquet` difference:** the stored column equals round(S1, 4) in **80/80** rows. The stored components (SWS, food CPI) are identical. The difference is **4-decimal storage rounding**, not a formula difference. The reference was not modified.

**The comparative run proceeds on the full-precision S1** (E9 reference). This decision is disclosed; if you treat the stored column as the binding reference, the comparative results should be regarded as blocked.

**τ0 for S1 only:**

- The thesis median rule (`risk_score_v2.reference_threshold`): the median S1 over the complete labelled quarters published before 2023-10-01. These are 2021-Q2–Q4, 2022-Q2–Q4, 2023-Q1–Q2 (8 quarters, 40 values).
- Recorded value **10.84335** (served metadata; computed from the rounded column). Full-precision value **10.843333**.
- **No S1 value lies between the two**, so classifications are identical under either.
- **HIGH = S1 > τ0** (strict).

## 4. Candidates

| Option | Score | Parameters |
|---|---|---|
| **A** | α·H + β·D | α ∈ {0, 0.25, 0.5, 0.75, 1.0, 1.25}; β ∈ {0.5, 1.0, 1.5, 2.0, 2.5, 3.0}; 36 combinations, grouped by the exact ratio α/β |
| **B** | wH·Z(H) + (1 − wH)·Z(D) | wH ∈ {0, 0.25, 0.5, 0.75, 1}. Z uses **training-only** means and SDs per fold (H statistics over training quarters, one value per quarter; D statistics over training province rows). Zero training variance → that contribution set to 0 and flagged. |
| **C** | D | Labelled "relative provincial food-price pressure". It is Option A with α = 0 and is not counted as a separate model. |

**Baselines:**

- H alone;
- F alone (labelled "provincial food inflation, not relative");
- D alone;
- S1;
- S1 carry-forward;
- each candidate's **own-score** carry-forward.

## 5. Thresholds

| Score | Classification |
|---|---|
| S1 | τ0 (above) |
| Option A with α/β = 1/2 (exactly S1-equivalent) | **Consistently transformed** threshold (β/2)·τ0 |
| Every other score | **No approved threshold exists** → no HIGH/LOW. Continuous scores and distributions only; classification accuracy **not evaluable**. No quantile is chosen to force a class balance. |

## 6. Category B design (internal consistency)

- **Target:** S1 in quarter T. **Origin:** start of T.
- **Inputs:** H = the latest SWS published before the origin; D and F at T−2 (E9 timing); S1 carry-forward = the latest published label.
- **Folds:** the 7 quarters with ≥ 8 complete eligible training quarters (2023-Q4 to 2025-Q4). Folds with fewer than 8 are skipped and reported. **All 7 were reused in E1–E11, so the results are exploratory.**
- **Common scale:** each candidate's origin score is mapped to the S1 scale by a **training-only** least-squares line (S1_target = a + b·score). S1-scale candidates are also reported raw.
- **Metrics:**
  - MAE and RMSE on the S1 scale;
  - within-quarter concordant pairs (ranking; invariant to the mapping when b > 0);
  - regional-level error.
- **Own-score persistence:** for each candidate, its latest published value vs its realized value, with the MAE normalized by the training SD of that score, and concordance.
- **Classification:** S1 only (τ0). Class counts are reported. Metrics for a class with no examples are **undefined**, never 0.

## 7. Sensitivity

- **Leave-one-quarter-out (descriptive):**
  - over the 7 test quarters, for the Category B means;
  - over the 8 τ0 reference quarters, for the τ0 median. This bypasses the 8-quarter minimum and is descriptive only.
- **No bootstrap inference** is presented as strong evidence.

## 8. Selection rule

- A component or score is recommended **only for the purpose its evidence supports**: H for regional context, D for relative local price pressure.
- A **combined** score is recommended only if its target, interpretation and evaluation justify combining. **Category B on S1 cannot do this**, because it is circular.
- **Not used as criteria:** the number of HIGH provinces, class balance, or dashboard appearance.

## 9. Mathematical invariances (to be verified on synthetic data before any historical data is used)

1. Σ_p D = 0 for complete quarters.
2. α shifts all five scores equally within a quarter.
3. For β > 0, the within-quarter ranking = the ranking of D.
4. Within-quarter spread = β × spread(D).
5. α alone cannot change ranking or spread.
6. Equal α/β ratios are scale-equivalent; with consistently transformed thresholds, classifications are identical.
7. Option C = Option A with α = 0.
8. Option B with wH ∈ {0, 1} reduces to a rescaled D or a rescaled H; intermediate wH equals Option A with a fold-dependent effective ratio, plus a constant shift.
