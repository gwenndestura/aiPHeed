# C-B6D-E-X2 pre-registration: Lead 2 improvement of the decomposed Eq. 3 model (fixed 2026-11-04, before any fit)

**Development evidence.** All 250 province-quarters (2013–2026) were examined in FI-FOCUS; none is untouched. Untouched
data come only from the prospective seal in the last section.

## Diagnosis (from FI-FOCUS outputs, `out/fi_provincial_fits.csv`)

- **Lead 2 of C-B6D-E-X:**
  - accuracy 0.736, balanced accuracy 0.674 (R2 and R3 fail);
  - 36 false positives, 30 false negatives.
- **The hunger part is the main error source:**
  - its call is wrong in 67% of the misclassified rows;
  - with the true regional hunger in place of the forecast (diagnostic oracle), accuracy would be 0.888;
  - the hunger part's quarterly calls are 0.74 correct against measured BL hunger > 11.0.
- **The price part is weaker at Lead 2:**
  - D̂–D correlation 0.36 (0.60 at Lead 1);
  - D̂ = 0 in 15 rows;
  - D has province-specific levels (Rizal persistently positive).

## Changes (each motivated above; all use only information available at O(t))

1. **ENS: a combined regional hunger forecast.**
   - The regional probability is Φ of the equal-weight mean of Φ⁻¹(clip(p, 0.001, 0.999)) over four stored
     walk-forward regional fits: C-B6E (with employment and OFW), C-B6, NP (non-price, with employment, OFW and news),
     and HO (hunger only).
   - An arm missing at (t, k) is left out of the mean.
   - Standard equal-weight forecast combination; no weights are estimated.
2. **FE: province-level mean reversion for D.**
   - D̂ = a_p + b_k · (D1 − a_p).
   - a_p = the mean of province p's realised D over the quarters known at O(t) (at least 8; otherwise a_p = 0).
   - b_k = least squares through the origin of (D(t' + k) − a_p) on (D1(t') − a_p) over past pairs, as in C-B6D.
   - σ_D = the residual RMSE (same fallbacks as C-B6D).
3. **CAL: walk-forward Platt recalibration.**
   - The final probability is passed through a logistic regression (C = 1e6, unpenalised in effect) of y on the
     logit of the raw probability.
   - It is fitted on the **same arm's** raw forecasts at the same lead, from origins t' < t whose labels are known at
     O(t).
   - It is used only when there are at least 40 such rows with both classes; otherwise the raw probability is kept.

## Arms

| Arm | Regional | D model | Calibration |
|---|---|---|---|
| C-B6D-E-X (reference, reproduced) | C-B6E | D1 | none |
| X-ENS | ENS | D1 | none |
| X-FE | C-B6E | FE | none |
| X-CAL | C-B6E | D1 | CAL |
| **X2 (primary)** | ENS | FE | CAL |
| PSA-only-P-X | IMPROVE_V2 PSA-only | D1 | none |

**Also on B-ext:** PERSIST-X, CLIM-X, C-B6-R (from `out/fi_provincial_fits.csv`). **On B-old (2021+):** C-B6P2,
C-B6D-E, LOGIT, NLP-only-P (from earlier outputs).

## Evaluation

- **Samples:** B-ext (q ≥ 2013-Q1, 250 rows per lead) is primary; B-old (q ≥ 2021-Q1) is reported. Lead 1 and Lead 2
  separately.
- **Metrics:** all metrics; AUC with a quarter-cluster bootstrap 95% CI.
- **R1–R7:** frozen `rules()`, with PERSIST-SI = PERSIST-X and CLIM = CLIM-X.
- **Algorithm 3:** leads 1–8.
- **Holm family (12):** X2 minus the comparator, paired Brier, quarter-cluster bootstrap, one-sided. Comparators:
  C-B6D-E-X, PERSIST-X, CLIM-X, C-B6-R, PSA-only-P-X, X-ENS; Leads 1 and 2.
- **Component report:** hunger-part accuracy against measured BL hunger > 11.0; D̂ sign accuracy and correlation;
  contribution shares (hunger vs price).

## Decision rules (fixed)

- **Lead 2 fixed:** X2 passes all R1–R7 on B-ext at Lead 2.
- **Lead 1 preserved:** X2 passes all R1–R7 on B-ext at Lead 1, and its Lead 1 accuracy ≥ 0.772 − 0.02.
- **Improvement shown:** X2 Brier < C-B6D-E-X at Lead 2, Holm p < 0.05.
- **Hunger stays meaningful:** the mean hunger-history contribution share ≥ 30% at both leads.
- **If X2 fails:** no further variant on these data. Report and rely on the prospective seal.

## Prospective seal (untouched data)

- **The forecasts of C-B6D-E-X and X2** issued 2026-10-01 (origin 2026-Q3) for 2026-Q4 (Lead 1) and 2027-Q1 (Lead 2),
  for all five provinces, are written to `out/seal_prospective_X2.csv`.
- **Its SHA-256 goes in `out/seal_prospective_X2.sha256`** before any outcome is published.
- **Scoring:** when SWS 2026-Q4 / 2027-Q1 and the PSA CPI are released.
PLAN-SHA256: f4bf89d0d2ebd7eab5546bae6578a9fc07017d4b13a8d26fc0638b1aafd33b43
