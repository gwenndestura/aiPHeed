# E135 frozen protocol: feature-influence optimization

**Freeze.** Written and hashed **before** any E135 result. The SHA-256 is in `runner/PROTOCOL_SHA256.txt`.

**Scope.** Branch `aiPHeed/corrected-data-pipeline`, start `45b339e`. Offline only. Production, the dashboard, FIRI and every seal are unchanged.

**Unchanged:**
- target SWS hunger, 4 areas, 2021+ (owner decision E134 Addendum 1);
- tolerance 1.645 × SE; 75 %; leads; N1–N7;
- P-DASH as the primary policy;
- evaluation sets S-U (primary) and S-E132;
- point-in-time rules of E133/E134.

**Data status.** All values seen. Development evidence only.

**The forking-paths problem, stated in advance.**
- The E133/E134 ablations already show which drivers hurt on these same 40 Lead-2 rows. Any configuration chosen by looking at them is post-hoc.
- E135 therefore makes every influence decision **inside the walk-forward**: at each issue, using only forecast errors on targets published before that issue (nested, out-of-sample).
- One post-hoc configuration (X-EXCL) is included only as a labelled reference and **cannot be selected**.

## 1. Architecture and influence controls

The models are E133/E134 state-space models. Each driver g has a sign-constrained coefficient β_g ≥ 0 with Gaussian prior N(0, s_g²), estimated by penalized maximum likelihood at every issue. Because the model is linear in β, influence is controlled through s_g (shrinkage) or by excluding g. Multiplying a feature is not used; standardization makes it equivalent to changing s_g.

**Driver pool (7):**
- A rice CPI q/q;
- C typhoons;
- E unemployment change;
- N GDELT shortage share;
- V poverty × market (area);
- aR area rainfall deficit;
- aP area palay drop.

**Full model (FULL7):** E134-AREA-T, which has all 7 at s = 1.

## 2. Candidates

| Id | Config | Influence type (directive) | Selectable |
|---|---|---|---|
| HFM-X | A, C, E, N, V at s = 1 | A (full influence, reference) | yes |
| SEAS-LLM | No drivers (E132) | Reference | yes |
| FULL7 | 7 drivers at s = 1 | A | yes |
| X-RED | HFM-X groups at s = 0.5 | B (reduced) | yes |
| X-NSD | HFM-X groups; global s chosen at each issue and lead from {0.25, 0.5, 1, 2} by the lowest past out-of-sample MSE | C (regularized, nested) | yes |
| X-SEL | From FULL7: include group g at an issue and lead only if, on past rows, MSE(FULL7) ≤ MSE(FULL7 minus g); refit with the included groups | E (selective, lead-specific, nested); D (exclusion) where it fires | yes |
| X-GREG | As X-SEL, but a group that would be excluded is kept with s_g = 0.25 instead | C (group regularization) | yes |
| X-STACK | w·HFM-X + (1 − w)·SEAS-LLM; w ∈ {0, 0.25, 0.5, 0.75, 1} chosen at each issue and lead by the lowest past MSE | Regime-aware combination | yes |
| X-COMB | Same as X-STACK, with X-SEL in place of HFM-X | Combined approach | yes, but recommended only if X-SEL and X-STACK each beat HFM-X on **both** S-U and S-E132 at Lead 2 |
| X-EXCL | HFM-X minus C (typhoons), the group whose removal improved every lead in E133 | D (exclusion), **post-hoc** | **no** |

**Nested rules.**
- "Past rows" are the same policy and lead, issue earlier than the current issue, and target published before it, all areas.
- With fewer than 8 past rows the defaults apply: s = 1; include all groups; w = 1 (HFM-X).
- Ties go to the simpler option: the smaller s, exclusion, larger w.
- MSE is the error against SWS.

## 3. Evaluation and selection

- **Report:** per model × lead × policy × set: MAE, RMSE, bias, within, coverage80, terciles, sharp increases, by area, by period (pre-surge / surge 2024 / post-break), with row counts. N1–N7 as in E134.
- **Selection rule (fixed):** highest Lead-2 within on S-U, P-DASH, among the selectable models; ties → lower MAE. Validated only if N1–N7 pass on S-U and N2 and N3 on S-E132.
- **Generalization check of the nested procedures:**
  - their choices (s, included groups, w) are reported per issue;
  - a procedure is called "stable" only if its choice is the same in at least 2/3 of the issues after its first 8 past rows.

## 4. Feature audit and group ablation

- **Feature audit:** every FIRI family and E133/E134 driver, with source, meaning, geography, frequency, publication delay, the E133 D2 screen correlation, and leave-one-out effects from FULL7 at Leads 1–4 (Δ MAE, Δ within, Δ bias overall and in the high tercile, Δ MAE by period and area). Paired cluster-bootstrap p.
- **Contribution criterion (E133):** removal worsens MAE and within, with p < 0.10.
- **Trigger groups:** each alone (with history) and each removed, from FULL7 and from HFM-X.

## 5. Seal

Prospective forecasts of the selected E135 candidate are added only if it is not HFM-X. Otherwise the E134 seal covers it. Write-once.
