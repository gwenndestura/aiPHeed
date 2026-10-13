# Frozen Candidate Set and Selection Rule (E17 v3)

**Freeze.** This file is frozen before any candidate is run. Its SHA-256 is in `runner/PROTOCOL_SHA256.txt`, and every script checks it. **No candidate, feature, setting or rule may be added or changed afterwards.**

**Not blind.** All 2021–2025 values were examined in E9–E17.

## 1. Common backtest design

| Item | Specification |
|---|---|
| Information set for target quarter T at horizon h | All eligible observations of quarters **≤ T − h**. This mirrors the 2027-Q1 case exactly: latest observation 2025-Q4, target 2027-Q1, h = 5. |
| Training pairs at an origin | Target quarters q ≤ T − h, each paired with the information set of q − h, using the same construction as the forecast |
| Preprocessing | Ridge standardization uses training rows only. No imputation is needed: H, F and D have no gaps in their observed quarters, and unobserved H quarters are skipped, never filled. |
| Hyperparameters | **Fixed** (below). Nothing is tuned: 6–9 training points cannot support inner validation. |
| Primary horizon | **h = 5** (the 2027-Q1 horizon) |
| Diagnostics | h = 1, 2, 3, 4. Reported only; **never used for selection or as validation of h = 5.** |
| Minimum training | 6 observed target quarters for every fitted candidate |
| Evaluation origins | Only the **common** origins where every selectable candidate of that target can be computed. All candidates are scored on the same origins. |
| Minimum evidence | **Fewer than 8 common origins at h = 5 → "exploratory only".** No bootstrap or significance test is presented as evidence then; individual errors and descriptive comparisons are reported instead. |

## 2. Regional hunger H (primary)

H is the quarterly mean of all eligible SWS rounds, as in E13's primary analysis. Quarters with no round are skipped.

| ID | Candidate | Definition | Selectable |
|---|---|---|---|
| C1 | Carry-forward | H(L), where L = the latest observed quarter ≤ T − h | Baseline |
| C2 | Historical mean | Mean H over observed quarters ≤ T − h | Yes |
| C3 | Drift | H(L) + g × (T − L), with g = (H(L) − H(first)) ÷ (L − first) over observed quarters ≤ T − h | Yes |
| C4 | Ridge AR(1), existing | y = H(q) on x = H(L_q), with L_q = latest observed ≤ q − h; ridge α = 1 | Yes |
| C5 | Ridge AR with lag set {latest, previous} | x = [H(L_q), H(previous observed quarter before L_q)]; α = 1 | Yes |
| C6 | Damped robust trend | H(L) + s × Σ_{i=1}^{T−L} 0.8^i. s = Theil–Sen slope (median of pairwise slopes) over the last ≤ 8 observed quarters ≤ T − h (at least 4). φ = 0.8, fixed. | Yes |
| C7 | Ridge with indicators | x = [H(L_q), mean5 F of quarter q − h, national unemployment of quarter q − h]; α = 1 | Yes |
| C7a | Ablation | C7 without unemployment: [H(L_q), mean5 F] | **No** (diagnostic) |
| C7b | Ablation | C7 without mean5 F: [H(L_q), unemployment] | **No** (diagnostic) |

**Excluded:** a tree-based model, LightGBM, deep learning and ensembles. The training samples (6–9 points at h = 5) cannot support them.

**Selection rule for H (applied only at h = 5).** A candidate C2–C7 is selected over C1 only if **all** of these hold on the common origins:

1. **Lower pooled MAE** than C1.
2. **Lower absolute error than C1 in a strict majority** of origins.
3. **In the later half of the origins** (the last ⌈n/2⌉, in time order), its MAE is not worse than C1's.
4. **Not dependent on one quarter:** its MAE stays below C1's in **every** leave-one-origin-out subset.
5. **Its configuration was fixed before evaluation.** True for all candidates by this freeze.

**If more than one candidate qualifies,** the one with the lowest pooled MAE is chosen. **If none qualifies, C1 is kept.** If n < 8, any selection is labelled "**exploratory only; not validated**".

## 3. Provincial food inflation F and relative pressure D (secondary)

| Target | ID | Candidate | Selectable |
|---|---|---|---|
| F | F1 | Carry-forward F(p, T − h) | Baseline |
| F | F2 | Pooled mean of F over quarters ≤ T − h | Baseline |
| F | F3 | Province mean of F over quarters ≤ T − h | Baseline |
| F | F4 | Ridge AR, pooled (existing): y = F(p,q) on x = F(p, q − h); α = 1 | Yes |
| D | D1 | Carry-forward D(p, T − h) | Baseline |
| D | D2 | Zero (= pooled training mean of D) | Baseline |
| D | D3 | Province mean of D over quarters ≤ T − h | Baseline |
| D | D4 | Ridge shrink (existing): y = D(p,q) on x = D(p, q − h); α = 1 | Yes |
| D | D5 | Ridge D + province mean (existing): x = [D(p, q − h), province mean D ≤ q − h]; α = 1 | Yes |

**Selection rule for F and D (h = 5).** The unit is the quarter: the pooled MAE over the five provinces within each origin. A fitted candidate is selected only if conditions 1–4 above hold **against every baseline of that target**. Otherwise no model is selected and carry-forward is reported. The n < 8 label applies as above.

**Not selectable:** classification metrics are not used for F or D, and MAE is not used for any classification target.

## 4. Thesis risk label (classification)

**Not run.** At 2027-Q1 the implemented classifier needs 2026 news inputs, which are not authorized, and E17 found too few test quarters at k = 5. This is documented in Phase 0 and in the final report.

## 5. The 2027-Q1 forecast

The selected configuration is refitted on all approved observations (≤ 2025-Q4), or C1, F1 or D1 if nothing was selected.

- **Horizon:** h = 5.
- **Labels on every output** (example): "Research forecast of regional hunger; this is not a forecast of provincial food insecurity."
- **Uncertainty:** no interval is produced. The h = 5 history cannot support a reliable one; the past h = 5 errors of carry-forward are listed descriptively.
- **Holdout:** none. The 2026 holdout (Phase 5) is not run without authorization.
