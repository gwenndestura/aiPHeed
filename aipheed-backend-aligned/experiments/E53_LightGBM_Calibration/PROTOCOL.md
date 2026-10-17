# E53 protocol: E52 calibration, the LightGBM requirement, and the five-trigger contribution (frozen before any E53 score)

**Written:** 2026-10-17 on branch `e46-lead2-policy` at 2867b11.
**Freeze:** the SHA-256 of this file (LF line endings) is in `runner/PROTOCOL_SHA256.txt` and is committed before the run. The run happens once, followed by a byte-identical repeat. Any change after freezing is logged in `DEVIATIONS.md`.

## 0. Evidence status

- **What has already been seen:**
  - E52's scores on the 10 PS target quarters 2024-Q2..2026-Q3 (50 rows).
  - The per-quarter accuracies.
  - Calibration-in-the-large of −0.094.
- **What has not been seen:** no E53 arm (calibrated E52, any LightGBM model, any trigger ablation) has been scored. All E53 results on those quarters remain **development evidence**.
- **Independent test:** the 2027 quarters, which are frozen (section 7).
- The 2027-Q1 E52 forecast (`E52_PS_PROSPECTIVE_2027Q1.json`, sha `dc01bb84…`) is kept unchanged.

## 1. Target, rows, timing (identical to E52)

- **Target:** PS, provincial food-price pressure.
  - **HIGH** if PSA food CPI YoY (quarter mean) > the province's 2021–2022 60th percentile, **or** food minus headline > its 2021–2022 60th percentile.
- **Evaluation rows:** the 50 E52 rows (`E52/runs/20261017T132935Z/rows.csv`), 2024-Q2..2026-Q3, matched on (target, province).
- **Every arm:**
  - is scored on exactly these rows;
  - issues its forecast at origin O(t) = 00:00 on day 1 of quarter t+1, for target t+2;
  - uses the as-of feature frame of E46 I7 (`e46_lib.features`, `e44_components.bases`; cutoffs verified in E47);
  - trains only on targets ≤ t−1 (outcomes published before the origin), with the data vintage `d.cut(t)`.
- **Baseline predictions:** reused from E52's `rows.csv`; they are already computed under identical conditions.

## 2. Arms

| ID | Description |
|---|---|
| **R0** E52 | E46 I7 price component, ridge residuals, refitted here. Must reproduce the committed `I7_p_price` within 1e-9 at every origin; otherwise the run stops. |
| **C1** E52 + intercept calibration | logit p′ = logit p + b. b is the posterior mode with prior N(0, 1²), fitted on that origin's inner forward-chaining out-of-fold probabilities and their as-of PS labels (targets ≤ t−1 only; the same folds that select the ridge). Fewer than 10 inner rows, or one class only → identity. |
| **C2** E52 + Platt calibration | logit p′ = a·logit p + b. Priors a ~ N(1, 0.5²) and b ~ N(0, 1²); same data and fallback as C1. logit p is clipped to [−6, 6]. |
| **LGB-R** primary LightGBM candidate | E52's component structure with the ridge residual learner replaced by a LightGBM regressor: food and gap = base-effect projection + LightGBM residual; same bivariate-normal probability; decision ≥ 0.5. Grid per component: multiplier m ∈ {1.0, 0.5, 0.0} × {no residual} ∪ {num_leaves ∈ {2, 4}} × {n_estimators ∈ {50, 200}} × {features ∈ {all five groups + news + policy, market only}}. Fixed: learning_rate 0.05, min_data_in_leaf 10, lambda_l2 10, feature_fraction 0.8, no bagging, deterministic, seed 53, native missing-value handling. Selection: the same embargoed forward-chaining RMSE as E52; ties broken by simplicity (no residual, then fewer leaves, then fewer trees, then market-only). |
| **LGB-C** secondary | LightGBM binary classifier on the PS label of each training target. Features: E52's residual inputs + base projections + distance-to-threshold features (base food − province food threshold, base gap − province gap threshold) for each m. Grid: {constant (training prevalence)} ∪ {num_leaves ∈ {2, 4}} × {n_estimators ∈ {50, 200}}; same fixed settings; selection by embargoed forward-chaining log-loss. Decision ≥ 0.5. |
| **LGB-RL** secondary | LGB-R with `linear_tree=True` and linear_lambda 10. It is reported separately because it is closer to a linear model. |
| **A-g** trigger ablation, g ∈ {climate, fish_kill, employment, ofw_remittance, news, policy} | R0 refitted with group g's residual inputs removed |
| **A-mkt** | R0 with market inputs only. The base projection, which belongs to the market group, is always kept. |

- **The primary LightGBM candidate is LGB-R.**
- LGB-C and LGB-RL are secondary. If only a secondary arm passes, the report flags the multiplicity (three LightGBM attempts), and the arm needs prospective confirmation.

## 3. Metrics

- **Per arm, on the 50 rows:**
  - accuracy with a quarter-cluster bootstrap CI (1000 draws);
  - balanced accuracy, recall HIGH/LOW, precision, F1, Brier, AUC;
  - confusion matrix and per-quarter accuracy and confusion;
  - leave-one-quarter-out accuracy;
  - calibration-in-the-large CITL = mean(y) − mean(p);
  - calibration slope and intercept (logistic regression of y on logit p);
  - a reliability table (bins 0–0.2, …, 0.8–1).
- **Code:** E51's `metrics` and `block`, copied without change.
- **Bootstrap seeds:** E52 arms seed 51 in E52's order (reproduces E52's CIs); E53 arms seed 53.
- **Paired comparison against R0:** quarter-cluster bootstrap 95% CI of the Brier difference.

## 4. Acceptance

**A1–A5 (E52's criteria, against every baseline B1–B7, climatology, always HIGH and always LOW):**

| ID | Criterion |
|---|---|
| A1 | accuracy ≥ 0.75 |
| A2 | balanced accuracy ≥ 0.70, both recalls ≥ 0.60 |
| A3 | Brier < every baseline's |
| A4 | balanced accuracy > every baseline's |
| A5 | minimum leave-one-quarter-out accuracy ≥ 0.70 |

**Calibration (new):**

| ID | Criterion |
|---|---|
| K1 | \|CITL\| ≤ 0.05 |
| K2 | Brier ≤ R0's Brier |

**Decisions:**
- **A calibrated E52 (C1 or C2) replaces R0** as the development candidate only if it passes A1–A5 **and** K1 and K2. If both pass, C1 is chosen (fewer parameters).
- **LGB-R meets the Chapter 1 LightGBM requirement for development** if it passes A1–A5. The report also states K1 and its standing against R0.
- **A trigger group "adds reliable predictive information"** only if removing it (A-g) raises the Brier with a 95% CI above 0. Otherwise the group is described as an input with no demonstrated predictive value on these rows. **Groups are not forced into the model.**

## 5. Explanations

- **Method:** the served probability (calibrated, if a calibrated arm is adopted) is attributed with the E50 method: each group's inputs are moved to their training mean, all else fixed, and the log-odds change is recorded. Market includes the base projections.
- **Calibrated arms:** attribution uses the calibrated probability. It must still reconcile with the model's F̂ and Ĝ (checks < 1e-8).
- **LightGBM arms, if served:** the same grouped training-mean attribution of the served probability is used; for a tree model it is a SHAP-style grouped approximation, stated as such.

## 6. Serving

- An arm adopted under section 4 is served only behind `AIPHEED_LEAD2_MODEL=e53`.
- E38 stays the default; e46 and e52 are unchanged.

## 7. Prospective freeze (independent test)

**What is frozen:**
- For every arm that passes its acceptance rule in section 4: its 2027-Q1 probabilities from origin 2026-10-01, using only data published before that date, written once to `frozen/E53_<arm>_PROSPECTIVE_2027Q1.json` with its sha256.
- E52's frozen file is kept unchanged.

**Evaluation script:** `runner/e53_prospective.py` scores every frozen file against the 2027 PS outcomes once they are published, against persistence and always-HIGH/LOW. Until then it reports "pending".

**Rules:**
- A frozen file is never edited. A leakage defect would be documented and corrected in a new versioned file.
- No future outcome is used to tune anything.

## 8. Not allowed

- Changing the label, its thresholds, the 0.5 decision, the rows, or the baselines.
- Choosing among arms on the evaluation rows except by the rules above.
- Any pre-2021 data.
- Reading outcomes after 2026-Q3.
