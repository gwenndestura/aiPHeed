# AIPHEED E135 · Feature-influence optimization: final research package

**Evidence status.**
- Protocol `ca2269e` was frozen before any E135 result.
- All SWS values (2021-Q2 … 2026-Q3) had already been seen, so these are **development results**.
- Every adaptive influence choice was made inside the walk-forward, from past errors only.
- Production, the dashboard, FIRI and every seal are unchanged. Window 2021+ (owner decision, E134 Addendum 1).

## Outcome

- **No influence configuration reaches 75 % or passes N1–N7 at any lead. The maximum reliable lead is none.**
- **The frozen selection rule keeps HFM-X:** Lead-2 within 0.50 (20 of 40 rows), MAE 4.87, N2 and N5 failing.
- **Best verified improvement: X-RED** (the HFM-X drivers with a tighter prior, reduced influence). On S-E132 (28 rows) it raises Lead-2 agreement from 0.43 to **0.54** and lowers MAE from 4.96 to 4.35, at the cost of one S-U row (0.475) and surge accuracy. It is not selected under the frozen rule.
- **Adaptive "learn whom to trust" procedures fail.** In-fold selection, shrinkage and stacking all score 0.30–0.43 at Lead 2. Their choices are unstable and switch drivers off just before the 2024 surge.
- **Remaining gap at Lead 2 (S-U):** 10 more of the 40 rows must fall within tolerance (30 needed), plus N5 (stability). On S-E132, X-RED is 0.54, so 6 more of 28 rows are needed.

## 1. Feature audit

`E135_FEATURE_AUDIT.csv` has 18 rows covering every FIRI v2 family A1–H1 and the E133/E134 additions. For each it gives the source, meaning, geography, frequency, publication rule, the E133 D2 screen correlation, and leave-one-out effects from FULL7 at Leads 1–4: Δ MAE, Δ within, p, Δ bias, Δ high-tercile bias, and Δ MAE by period and area.

## 2. Harmful, weak and conditionally useful features

**Basis:** leave-one-out from FULL7, P-DASH, S-U. Leads 1/2/3/4 have 44/40/36/32 rows.
- **Demonstrated:** removal worsens MAE and within, with p < 0.10.
- **Harmful:** removal improves MAE without lowering within, with p > 0.90.

| Feature / group | Original influence (FULL7, prior SD 1) | Optimized influence | Useful at | Harmful at | Decision | Why |
|---|---|---|---|---|---|---|
| aP palay drop (C3 at area level) | Included | **Excluded** | — | **Leads 2, 3** (Δ MAE −0.44, −0.65 when removed) | Exclude | Consistently harmful; misleading high-hunger signal |
| C typhoons in PAR | Included | Exclude (post-hoc X-EXCL) or reduce | — | Lead 1 harmful; Leads 2–4 removal also lowers MAE (−0.32 at L2) | Not used in the candidate, which is fixed by the frozen rule. X-EXCL improves MAE (4.55) but is post-hoc. | Weak and stale (E119 period rule) |
| aR area rainfall deficit | Included | Lead 4 only | **Lead 4** (Δ +0.46, p < 0.001) | Lead 2 neutral to slightly harmful | Keep only as a Lead-4 hypothesis | Drought exposure acts with a long delay |
| A rice CPI q/q | Included | Reduced (prior SD 0.5 in X-RED) | Surge 2024 (removal +0.77 MAE) | Post-break 2025+ (removal −0.66 MAE) | Keep, reduced | Conditionally useful. Its sign helps during price shocks and misleads when prices fall but hunger rises. No in-fold rule could tell the regimes apart in time. |
| E unemployment change | Included | Full | **Leads 2, 4** (L2: Δ +0.27, within −0.10, p 0.08) | — | Keep | Demonstrated in FULL7. It reduces high-hunger under-prediction (removal worsens it by 1.1). In E133's HFM-X context its L2 p was 0.20, so the result is context-dependent. |
| N GDELT shortage share | Included | Full | **Leads 2, 4** (tiny: Δ +0.10, within −0.025, p < 0.001) | — | Keep | Small but consistent |
| V poverty × market | Included | — | — | Lead 1 (negligible) | Keep (no effect) | Triennial data; scaling carries little information |

**These influences are estimated β under the stated priors, or measured ablation deltas. No weight in this report is assigned by hand.**

## 3. Influence experiments (Phase 3) and trigger groups (Phase 4)

**Lead 2, P-DASH.** S-U has 40 rows / 10 quarters; S-E132 has 28 / 7. Full tables: `E135_FEATURE_INFLUENCE_EXPERIMENTS.csv`, `E135_LEAD_COMPARISON.csv`.

| Config (directive type) | Model | S-U within | S-U MAE | S-U RMSE | High bias | Sharp increases | Coverage | S-E132 within | S-E132 MAE |
|---|---|---|---|---|---|---|---|---|---|
| A full | HFM-X | **0.50** | 4.87 | 6.42 | −7.14 | **8** | 0.75 | 0.43 | 4.96 |
| A full + area | FULL7 | 0.50 | 5.39 | 7.08 | −8.49 | 6 | 0.72 | 0.43 | 5.67 |
| B reduced | X-RED | 0.475 | 4.79 | 6.23 | −7.38 | 3 | 0.75 | **0.54** | **4.35** |
| C regularized (nested) | X-NSD | 0.35 | 5.36 | 6.90 | −7.94 | 1 | 0.65 | 0.50 | 4.56 |
| C group regularized (nested) | X-GREG | 0.43 | 5.48 | 6.83 | −8.89 | 3 | 0.62 | 0.46 | 5.32 |
| D excluded (post-hoc) | X-EXCL | 0.475 | **4.55** | 6.12 | **−6.91** | 7 | 0.78 | 0.43 | 4.68 |
| E selective (nested) | X-SEL | 0.40 | 5.54 | 6.86 | −8.94 | 3 | 0.60 | 0.43 | 5.27 |
| Combination | X-STACK | 0.33 | 6.02 | 7.82 | −8.32 | 2 | 0.68 | 0.43 | 5.21 |
| Combined | X-COMB | 0.30 | 6.07 | 7.63 | −9.89 | 0 | 0.62 | 0.39 | 5.53 |
| Reference | SEAS-LLM | 0.45 | 5.72 | 7.58 | −7.64 | 3 | 0.55 | 0.61 | 4.78 |

**X-COMB is not recommendable.** Its components do not beat HFM-X on both sets (protocol §2).

**Trigger groups** (`E135_TRIGGER_GROUP_ABLATION.csv`; each removed and each alone, from FULL7 and from E133's HFM-X):

| Group | Status |
|---|---|
| Market | Conditionally useful (surge) |
| Climate | Typhoons harmful or weak; rainfall Lead 4 only; ONI is a prospective hypothesis (E134-ONI) |
| Employment | Demonstrated at Leads 2 and 4 in FULL7 |
| News | Demonstrated at Leads 2 and 4, tiny effect |
| Poverty | None |

**No group dominates.** Each alone (with history) gives Lead-2 MAE 4.92–6.00. Employment alone and market alone are the best, at 5.29 and 4.92.

## 4. Lead comparison and reliability

`E135_LEAD_COMPARISON.csv` gives rows, quarters, within, MAE, RMSE, bias, high-tercile bias, coverage, sharp increases, p against persistence, and failed rules per model and lead, for both sets.

**No entry passes N1–N7.**

**HFM-X fails:**

| Lead | Failed rules |
|---|---|
| 1 | N2, N5, N6 |
| 2 | N2, N5 |
| 3 | N1, N2, N4, N5, N6, N7 |
| 4 | N1, N2, N4, N5, N6 |

**X-RED fails** N2 and N5 at Lead 2 on S-U, and N1, N2, N5 and N6 on S-E132.

## 5. High hunger and generalization

See `E135_HIGH_HUNGER_BIAS_REPORT.md` and `E135_OVERFITTING_GENERALIZATION_REPORT.md`.

- **High-hunger bias.** Removing misleading signals reduces it by at most 0.2–1.0 points per group. Most of it is lag (ORACLE-NOW −8.3). No configuration reduces it without harming the other terciles.
- **Generalization.** No configuration generalizes across regimes:
  - HFM-X is best in the surge (0.56);
  - X-RED is best before the surge (0.71);
  - SEAS-LLM is best after the break (0.71).
- **Adaptive procedures** overfit the previous regime.

## 6. Acceptance criteria (Phase 9)

| # | Criterion | Status |
|---|---|---|
| 1 | Food insecurity remains the target | **Met** |
| 2 | Original tolerance preserved | **Met** |
| 3 | ≥ 75 % agreement | **Not met.** Best 0.50 (S-U) and 0.61 (S-E132, SEAS-LLM); X-RED 0.54 on S-E132. |
| 4 | Lead-2 N1–N7 | **Not met** |
| 5 | Improved generalization | **Not met.** X-RED improves S-E132 but loses surge accuracy. |
| 6 | No increase in overfitting | **Met for fixed configs.** Adaptive procedures overfit and are rejected. |
| 7 | High-hunger bias addressed without damage | **Not met** |
| 8 | Contributions by valid ablation | **Met as evidence:** E and N demonstrated (Leads 2 and 4); aR at Lead 4; aP and C harmful |
| 9 | Point-in-time data | **Met** (E133/E134 rules, in-fold standardization and decisions) |
| 10 | Reproducibility | **Met** (`runner/e135_run.py` ~3 min; `runner/e135_summary.py`; tests) |

## 7. Recommendation

- **No integration.** HFM-X stays the prospective candidate under the E134 protocol, and the E134 seal (`e4f844dd`) covers it.
- **Possible prospective hypothesis:** X-RED (prior SD 0.5), with palay excluded and rainfall kept as a Lead-4 hypothesis. It was chosen after seeing development data, so it could only be confirmed prospectively, and **registering it would need your decision**. No E135 seal was written, because the selected model is HFM-X (protocol §5).

**Reproduce:**
```
python -I runner/e135_run.py
python -I runner/e135_summary.py
```
Tests: `backend/tests/unit/test_e135_influence.py`.
