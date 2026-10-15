# E44 addendum: iteration I4 (frozen before any I4 score)

**Written:** 2026-10-15, after E44 run 1 (`runs/20261015T150213Z`, commit 840781f). None of I1, I2 or I3 passed gate A1.
**Freeze:** SHA-256 of this file (LF) in `runner/ADDENDUM_I4_SHA256.txt`, committed before I4 is fitted. Run once, then a byte-identical repeat.

## Why I4 (the diagnosis, and its disclosure)

Run 1 results:
- **I2:** accuracy 0.686, balanced 0.716, HIGH recall 0.78, LOW recall 0.65, Brier 0.181. It passes A0, A2, A3 and A4 and fails A1.
- **Price component:** its raw probabilities sit between 0.5 and 1.0 for almost every province-quarter, so discrimination comes only from Platt and the threshold.

**Cause: a defect in the uncertainty structure, not a tuning choice.**
- T43's price signal is `F > c_food OR G > c_gap`, where G = food YoY − headline YoY.
- I2 drew only F as uncertain and treated the headline projection as known. G therefore inherited the full error of F (out-of-fold RMSE about 2.2 points).
- Food is part of headline CPI, so the errors of F and headline move together. The forecast error of G is smaller and correlated with F's error.
- Overstating G's uncertainty pushes P(G > c_gap) toward 0.5–1 whenever c_gap is near Ĝ.

**Disclosure:** this diagnosis used run-1 outer predictions. I4 is the fourth look at S44 and is reported as such. The change is fixed by the mechanism above, not chosen among alternatives by S44 accuracy.

## The I4 change (everything else identical to I2)

**Gap component:**
- G(t+2) = (food base_m − headline base_m) + residual_G.
- residual_G uses the same five-trigger features and the same 21-configuration grid as the food component.
- It is selected separately, by blocked leave-one-target-quarter-out RMSE over training pairs. G is observed for every quarter with complete published CPI.

**Joint price signal:**
- ρ = correlation of the out-of-fold residuals of F and G on their common training rows.
- `P(price) = 1 − Φ2((c_food − F̂)/s_F, (c_gap − Ĝ)/s_G; ρ)`, where s_F and s_G are the out-of-fold RMSEs.

**Unchanged from I2:**
- the hunger component, the joint probability P(H > 11.3) × P(price), the out-of-fold threshold and Platt rule, and the features;
- **five triggers mandatory** in both residual models and in the hunger model.

**Variants for trigger evidence:**
- I4-MKT: market only, with a random-walk hunger component;
- I4 drop-one: each group removed in turn.

**Gates:** A0–A4 on S44, the identical rows of run 1.
**Final-candidate rule (extended):** I4 becomes the final candidate if it passes A0–A4. Otherwise the run-1 rule stands: I2 is served, with "forecasting acceptance NOT met".

**Prospective freeze:** I4's 2027-Q1 forecast goes to `frozen/E44_I4_PROSPECTIVE_2027Q1.json` (sha256). Run 1's freeze is unchanged.
