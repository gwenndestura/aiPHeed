# C-B6D pre-registration: decomposed Eq. 3 province-quarter model (fixed 2026-11-04, before any fit)

**Development evidence.** The same 100 province-quarters (2021-Q1..2026-Q3) as C-B6P..P4, already examined. A new
design, not a retune.

## Why (diagnosis of C-B6P..P4, from `out/cb6p_labels.csv` and the existing fits)

- **Eq. 3 is correct.**
  - The deviations sum to 0 per quarter (max 1.6e-15).
  - S = H + 2D holds exactly.
  - THR recomputes to 11.0 from the 30 rows of 2021–22.
- **The provincial signal is real.**
  - The five provinces' labels differ in **10 of 20** quarters.
  - Mean |2D| is 2.56 points; in 5 quarters H ≤ THR but some province is HIGH.
- **The single-LightGBM candidates do not forecast it.**
  - Their calls differ across provinces in only 3–4 quarters.
  - Only 20 province quarters exist; the trees learn mostly from 1998–2020 regional rows, where D = NaN.
- **Design response:** forecast the two parts of Eq. 3 separately, each from the data that informs it.
  - H from the long regional history (validated regional models).
  - D from provincial price data.
  - Combine them exactly as Eq. 3 does.

## Model (fixed)

For a province p, origin t and lead k (target q = t + k):

1. **Regional part.** p_R = a regional model's walk-forward probability that BL hunger > 11.3% (stored fits, unchanged).
   σ_H = the table's `sigma_h` (pooled past forecast-error SD at the true horizon, known at O(t)).
   The implied mean is μ_H = 11.3 + σ_H · Φ⁻¹(clip(p_R, 0.001, 0.999)).
2. **Province part.** D̂ = b_k · D1(p, t), with D1 as in C-B6P (months ≤ m_avail(t)). The slope b_k is fitted for each
   lead by least squares through the origin on the training pairs (D1(p', t'), D(p', t' + k)):
   - t' < t;
   - all three CPI months of t' + k ≤ m_avail(t);
   - all five provinces pooled.
   - σ_D is the residual RMSE.
   - If fewer than 10 pairs exist: b_k = 0, and σ_D = RMS of the known D values (at least 5), else 2.0.
   - If D1 is NaN: D̂ = 0.
   - **EX variant only:** D̂ = b1 · D1 + b2 · Dh1, where Dh1 is the same construction on PSA **headline** CPI YoY
     deviation (same file, `all_items`).
3. **Combination (Eq. 3):** P(HIGH) = Φ((μ_H + 2D̂ − THR) / √(σ_H² + 4σ_D²)), with THR = 11.0. HIGH when P ≥ 0.50.

**Why no static socioeconomic inputs:** province poverty (PSA 2023) was published after most origins, so it would leak
the future; it stays in the Objective 3 ranking only. This is stated as a limitation.

## Arms

| Name | Regional part | Province part |
|---|---|---|
| **C-B6D-E** (primary) | C-B6E (C-B6 + E1 employment + E2 OFW; `FIXES_2026-11-04/out/cb6e_fits.csv`) | D1 |
| C-B6D | C-B6 (`out/cb6_fits.csv`) | D1 (ablation: value of E1/E2) |
| C-B6D-EX | C-B6E | D1 + Dh1 (province headline deviation) |
| PSA-only-P | IMPROVE_V2 PSA-only | D1 |
| NLP-only-P | IMPROVE_V2 NLP-only | none (D̂ = 0, the same σ_D) |

**Also compared:** PERSIST, LOGIT (C-B6P run), C-B6P2, C-B6-R (C-B6's regional p as each province's p).

## Evaluation

- **Sample:** province-quarters with q ≥ 2021-Q1 and an Eq. 3 label, Leads 1 and 2 separately.
- **Pairing:** each comparison uses the identical rows where both arms exist.
- **Metrics:** accuracy, balanced accuracy, precision, recall, F1, AUC-ROC, Brier.
- **R1–R7:** the frozen rules (`hr_lib.rp().rules`, as used for the provincial P0H4), with:
  - PERSIST-SI = PERSIST;
  - CLIM = the share of HIGH among the province labels known at O(t) (if none, among the BL labels known at O(t)
    with S = H);
  - ALWAYS-LOW = 0.
- **Algorithm 3:** leads 1–8.
- **Provincial skill:** accuracy on the rows of quarters whose five labels are not all equal, and the number of quarters
  in which the calls differ across provinces.
- **Statistics:** paired Brier, cluster bootstrap by target quarter (B 5000, seed 2036), one-sided.
  - Holm family 12: C-B6D-E vs PERSIST, LOGIT, PSA-only-P, NLP-only-P, C-B6P2, C-B6-R × Leads 1, 2.
  - Secondary (not in the family): C-B6D-E vs C-B6D (E1/E2) and C-B6D-EX vs C-B6D-E (headline).
- **Explanation:** the probit index of each forecast is split into:
  - the province-price term 2D̂/s;
  - the regional term, shared among the regional model's inputs in proportion to their |SHAP|, signed.
  - Employment and OFW shares are reported from this split, never forced.

## Decision rules (fixed)

- **Improves on C-B6P2:** Brier lower at both leads, one-sided p < 0.10, and accuracy ≥ C-B6P2 at both leads.
- **Meets the paper targets:** accuracy and F1 ≥ 0.75 at Leads 1 and 2, and AUC-ROC ≥ 0.80 at Lead 1.
- **Reliable at lead k:** R1–R7 all pass at lead k.
- **Employment/OFW have predictive value:** C-B6D-E Brier < C-B6D at both leads, one-sided p < 0.10.
- **Nothing is served or deployed.** Adoption is a team and adviser decision. **Reported whatever the result.**
PLAN-SHA256: c67db29d7931fee0b6e5bdfc9bc1d001e28b4dbf3b1f4660964affc2c964e5be
