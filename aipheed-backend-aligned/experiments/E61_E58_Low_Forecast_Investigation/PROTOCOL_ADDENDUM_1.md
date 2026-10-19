# E61 protocol addendum 1: drift, probability combination, hunger component, feature ablations (frozen before any addendum candidate is scored)

**Written:** 2026-10-19, after `PROTOCOL.md` (C1–C4) was scored. **Freeze:** the SHA-256 (LF) of this file is written to `runner/ADDENDUM_1_SHA256.txt` before `runner/d1_predict.py` runs. Predictions are sealed in `sealed/addendum1.csv` (+ sha256) before `runner/d2_score.py` reads outcomes.

## 0. Evidence status

- Everything here is **development evidence**. The 50 rows are the same ones examined in E43–E61.
- The C1–C4 results were known when this addendum was written.
- Rows, issue dates, data cuts (`d.cut(t)`, E56 feature rules), target (T43), DEV/TEST split and the E56 nested tuning are unchanged from `PROTOCOL.md`.
- **Unchanged:** the served model, `backend/data/`, and E56–E60.

## 1. Significance rule (applies to every E61 comparison, including C1–C4 restated)

A difference in Brier versus a reference is called **statistically supported** only if both hold:
- the quarter-cluster bootstrap 95% CI of the paired mean difference (4000 draws, seed 61) excludes 0;
- the quarter-level sign test gives p < 0.05.

If only one holds, it is called **"suggestive, not established"**. With 10 quarters, the sign test cannot reach p < 0.05 unless at least 9 of 10 quarters (ties excluded) favour one side. This is stated with every result.

## 2. Drift family (price part; E56 nested tuning over the other hyperparameters)

E56 selects the drift multiplier m ∈ {1.0, 0.5, 0.0} at each origin by inner forward log-loss, so it is not fixed at zero. m = 1.0 uses the mean monthly log change of the trailing 12 months published before O(t).

| ID | Projection inside the offset | Search space |
|---|---|---|
| D0 | as E56 (m selected) | = C0 (sealed E57) |
| **D1** | **trailing-12-month drift, forced** (m = 1.0) | the E56 configurations with m = 1.0 |
| **D2** | **recent-trend drift:** mean monthly log change of the last 6 months to m0 (minimum 6 changes), applied to food and all-items, as in E44 `proj` | the E56 configurations with m replaced by "r6" (de-duplicated) |
| **D3** | **no projection:** LightGBM binary classifier on the latest observed indicators (the E56 feature sets plus `ps_margin_now`), no offset, standard intercept | the E56 configurations (m ignored, de-duplicated) |

## 3. Combination family

| ID | How P(HIGH) is formed |
|---|---|
| K0 | P_hunger × P_price (E56) |
| **K1** | **conditional:** P_hunger × P(PS ∣ hunger high). The price part is re-tuned (E56 procedure) on training rows whose target-quarter hunger (as of `d.cut(t)`) was above 11.3%. Falls back to K0's price part when those rows cover fewer than 6 quarters. |
| **K2** | **calibrated combination:** logistic regression of T43 on [logit P_price, logit P_hunger], fitted on earlier C0 forecasts whose T43 outcome was published before O(t). L2 penalty λ = 1 on both slopes around 1 and the intercept around 0. Identity (= K0) when there are fewer than 10 such rows or one class. |
| **K3** | **separate parts, no combined probability:** HIGH iff P_hunger ≥ 0.5 **and** P_price ≥ 0.5 (decision only; no Brier) |

The parts are also scored separately:
- P_price against PS (50 rows);
- P_hunger against "hunger above 11.3%" (10 quarters).

## 4. Hunger component (regional, I7 ridge)

Each variant is re-run at the 10 origins plus 2026-Q3, using `P2.hunger_frame` / `hunger_component` with data as of O(t). The predicted hunger rate H_hat is scored against the observed quarter-mean SWS hunger of the target quarter (all rounds, the T43 definition): RMSE and mean error over 10 targets, plus P_hunger Brier vs H > 11.3.

| ID | Inputs |
|---|---|
| H0 | as E56 (all hunger inputs) |
| **H1** | without total news volume (`news_n`) |
| **H2** | random walk (latest posted rate, no inputs) |

## 5. Feature ablations (price part, E56 nested tuning; "does this feature carry out-of-sample signal?")

| ID | Removed from both feature sets |
|---|---|
| FA-rice | `rice_whsl_yoy` |
| FA-emp | `ur_yoy`, `under_yoy`, `news_employment` |
| FA-ofw | `remit_usd_yoy`, `remit_php_yoy`, `fx_yoy`, `news_ofw_remittance` |

**A feature carries supported out-of-sample signal** only if removing it makes the 50-row Brier worse under section 1. Split counts of each feature in the re-fitted E56 models are reported per origin (the C0 refit must reproduce the sealed E57 values within 1e-9).

## 6. Decision rules

- **Drift and combination families.** The candidate with the lowest DEV Brier is selected. It counts as an improvement over K0/D0 only if:
  - PROTOCOL.md §4 criteria (a)–(d) hold; **and**
  - the 50-row difference is statistically supported (section 1).
- **K3** cannot be scored by Brier. It is reported by accuracy, balanced accuracy, HIGH recall and onsets, and recommended for display only if its balanced accuracy is ≥ K0's.
- **Hunger.** H1 or H2 replaces H0 for the explanation of the hunger part only if its RMSE is lower over the 10 targets **and** lower in ≥ 6 of them.
- **No served model changes in E61.** Accepted fixes are recommendations, scored prospectively once you authorize them.

## 7. Not allowed

Same as PROTOCOL.md §5.
