# E49 protocol: fair E38 vs E46 comparison (frozen before any E49 score)

**Written:** 2026-10-17 on branch `e46-lead2-policy`, from 26ca3e0.
**Freeze:** SHA-256 (LF) in `runner/PROTOCOL_SHA256.txt`, committed with code and tests before the comparison runs. Run once, then a byte-identical repeat.

## 0. Evidence status

Every 2022–2026 quarter has been examined in E36–E48. **No result here is an evaluation on unseen quarters.** The only unseen evaluation is the frozen 2027-Q1..Q4 prospective forecasts.

## 1. The two models predict different events

| | E38 (production default) | E46 I7 (experimental, `e46`) |
|---|---|---|
| **Target** | Thesis Equation 3: stress S1 = SWS hunger + 2 × (province food CPI YoY − five-province mean); HIGH when S1 > τ. E38 uses τ = median S1 of the labelled quarters posted before the origin (trailing, as of the origin); the thesis text states a global median | T43: SWS hunger > 11.3 AND (province food YoY > its 2021–2022 P60 OR food − headline > its P60) |
| **Horizon** | Lead 2: origin 00:00 on day 1 of quarter t+1, target t+2 | same |
| **Model** | LightGBM pool + nested selection + prior shift + inner threshold (E38 code) | component model: base-effect F/G + ridge residuals + hunger ridge (E46 code) |
| **Original result** | 39/55 = 0.709 (11 targets 2023-Q3..2026-Q3) | 0.800 (35 rows, 7 targets) |

Their accuracies measure different events and are **not** compared directly.

## 2. Comparisons (fixed now)

**Reproductions (from committed predictions):**
- E38: arm `E38-LGBM` in `E38/runs/20261015T033922Z/predictions.csv`, against its stored labels.
- E46: `I7` in `E46/runs/i7_20261017T000111Z/predictions_i7.csv`, against recomputed T43 labels.

**Target A, thesis Equation 3 with E38's as-of τ:**
- **E38:** original predictions.
- **E46-I7→EQ3** (adapted; not the original E46). From I7's own as-of forecasts at each origin t:
  - D̂ = F̂_p − mean(F̂);
  - Ŝ1 = Ĥ + 2·D̂;
  - p = 1 − Φ((τ(t) − Ŝ1)/s), where s is the root-mean-square error of Ŝ1 − S1 over earlier origins whose target S1 was posted before O(t);
  - with fewer than 3 such targets, s = √(s_H² + 3.2·s_F²) from I7's inner errors;
  - decision p ≥ 0.5.
- The labels are E38's own (S1 > τ(t)); the computation must reproduce E38's stored y.

**Target B, T43:**
- **E46 I7:** original.
- **E38→T43** (adapted; not the original E38): E38's code unchanged — features, configuration pool, nested selection, prior shift, inner threshold rule — with every label (training targets, `y_last`, prior-shift rate, evaluation) replaced by the T43 label. The posting rule is the same: a T43 label is used only once its SWS rounds were posted before the origin.

**Identical rows:** the target quarters where every arm of both targets exists (expected 2024-Q2, 2024-Q3, 2024-Q4, 2025-Q1, 2025-Q4, 2026-Q1, 2026-Q2, 2026-Q3: 8 independent quarters, 40 province rows). The same rows are used for both targets.

**Baselines, per target:**
- always-LOW;
- always-HIGH;
- persistence: the latest label of that target posted before the origin (E38's B1 for A; the exported as-of T43 label for B).

## 3. Metrics

- Accuracy (date-cluster bootstrap CI), balanced accuracy, HIGH recall, LOW recall, HIGH precision, F1, Brier, AUC (when both classes occur), confusion matrix.
- Share of HIGH and LOW calls; results by target quarter.
- Per-province standard deviation and range of probabilities across quarters.

## 4. Decision rule for the production recommendation (fixed now)

**A model may be recommended for promotion only if, on the identical rows of a target that is the thesis's or adviser-approved, it does both of the following:**
1. it beats always-LOW, always-HIGH and persistence on Brier score;
2. it has balanced accuracy ≥ 0.70 with both recalls ≥ 0.60.

**If no model does,** the recommendation is "Neither": keep the current default temporarily and disclose its limitations.

**Thresholds are not tuned on these rows.** Every decision rule is the one frozen in the original E38/E46 protocols or stated above.
