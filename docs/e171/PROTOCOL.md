# E171 protocol: level-change + calibrated-deviation LightGBM (LOCKED 2026-11-06, before any E171 run)

## Status of this design: INFORMED
- E171 was designed **after** seeing E168 and E170 results on the 72 historical Lead-1 rows. It combines E168's level-drift tracking with E170's calibrated provincial deviation.
- **Its retrospective score is therefore biased upward, and it is reported but is never acceptance evidence.**
- Acceptance rests only on outcomes released after the seals in section 4.

**Owner decisions on record:**
- LightGBM is the final algorithm.
- The FIES→HFIAS bridge is allowed for the level.
- C1 is pooled.
- Gates are not deleted.
- E168 is sealed for ENNS 2022 before any outcome is seen (`data/e168/out/sealed_enns2022.json`).

**Amendments:** code defects only, never performance, logged in `docs/e171/AMENDMENTS.md` with the diff and the effect on results.

## 1. Target (unchanged)
- **Outcome:** HFIAS moderate + severe, by province. **HIGH** = 50 % or more.
- Training uses all provinces nationally. Reporting covers the five CALABARZON provinces.
- Leads 1–8 (Lead k = k + 1 quarters before the survey quarter).

## 2. Model: `μ = L0(r, origin) + ΔL̂(r, T) + Δ̂(p, T)` (logit)

**L0, the level at origin:** exactly E170 Part B (`app.e170.model.level_at`, unchanged). That is:
- the newest released provincial HFIAS round (region mean logit if 2 or more provinces were measured, else the national mean); or
- the newer published regional FIES, bridged with `logit H = 0.25 + 0.955 · logit F` and `σ_L² = 0.13² + se_F²`.

**ΔL̂, level change (LightGBM, new in E171):**
- **Training target per row:** `L_target(r, s) − L0_row`. `L0_row` is the E170 level at **that training row's own origin** (the newest round released at that origin, as-of).
- **Learner:** `LGBRes` (E168 class) with the **same** feature sets `FS`, grid `HPO`, monotone signs, pruning and weights as E168.
- **Selection:** nested by inner region-grouped CV weighted SSE on training rows only.
- **No calibration layer** on the level part.

**Δ̂, provincial deviation:** exactly E170 Part A (`app.e170.model.run_proc` logic, unchanged):
- relative-persistence baseline plus LightGBM change;
- raw/linear layer chosen by inner Brier.
- The deviation target is `y − L_target`, as in E170.

**Uncertainty:**
- `σ² = σ_Δ²(gap) + σ_ΔL²(gap) + σ_L²`.
- `σ_Δ` and `σ_ΔL` come from inner cross-fitted residuals by gap (`A4.scale`), each from its own part.
- `P(HIGH) = Φ(μ/σ)`. The 90 % half-width uses the same quantile rule as E170.

**As-of rules:** as E170.
- HFIAS lag: 6 quarters.
- FIES usable from Q1 of the second year after fieldwork, unless a publication date is documented.
- Leakage corruption must change no forecast by more than 1e-9.

## 3. Evaluation rule (fixed now, before ANY new outcome; applies to E171 and E168)
**Rows:**
- `R` = retrospective Lead-k rows: 72 at Leads 1–6, 50 at Leads 7–8.
- `N` = all qualifying prospective rows: provincial **HFIAS** moderate + severe published by DOST-FNRI after the relevant seal, for fieldwork after the origin data.
- **Every** qualifying province counts. None may be selected.

| Criterion (E156 definitions and constants unchanged) | Evaluated on |
|---|---|
| C1 accuracy above the majority rule with effective-n lower bound | **R ∪ N** (pooled) |
| C2 Brier better than persistence (CI upper bound < 0) | R ∪ N |
| C3 HIGH and LOW recall ≥ 0.5 | R ∪ N |
| **C4 calibration slope CI includes 1** | **N only, and only once N has 40 or more rows.** Until then, C4 is "not yet evaluable" and acceptance is not possible |
| C5 model ≥ persistence in at least 2 rounds | rounds in R ∪ N |
| C6 n ≥ 40 | R ∪ N |

**Why C4 is judged on N only:**
- E169 showed that the 72-row C4 rejects a truly calibrated model about 21 % of the time.
- E169 also showed that the historical miscalibration comes from the 2015-anchored level drift, which E171 is designed to model.
- Judging C4 on the same historical rows would re-test that old failure, not the new model.
- This rule is fixed **before** any new outcome is seen.
- **Every report must also show C4 on R ∪ N (the original E156 rule) beside it.**

**Requires adviser confirmation.** This evaluation rule changes where C4 is computed, compared with E156. It takes effect only if the owner's adviser confirms it **before** any new outcome is scored. Until then, both versions are reported and the original E156 rule governs the decision.

**Controls (on R, Lead 1):**
- leakage ≤ 1e-9;
- the CI upper bound of Brier(real) − Brier(shuffled) ≤ 0.005;
- group ablation reported.

**Maximum reliable lead:** the largest k with leads 1..k all passing, sequentially.

**Decision:**
| Outcome | Decision |
|---|---|
| Every criterion passes at Lead 1 under the rule in force **and** the controls hold | ACCEPTED. Production change still needs separate owner go-ahead |
| Otherwise | NOT ACCEPTED. E158 stays |

## 4. Seals (immediately after the single retrospective run, before any outcome)
- E171 for ENNS 2022 (every province, Leads 1–2, origin O3), beside E158 `f69e7a02`, E166 `49e514d2`, E170 `af0180af` and E168 (sealed 2026-11-06).
- E171 for 2027-Q1 (all provinces, issue 2026-Q4).

## 5. Forbidden
- Re-running the retrospective with variations.
- Changing constants, grids, feature lists, gates or the evaluation rule after the run or after any outcome.
- Choosing which provinces or rounds count.
- Using bridged FIES as a provincial outcome.
- Copying national values into provinces.

## 6. Deliverables
- `backend/app/e171/`, `backend/data/e171/out/`
- `docs/e171/RESULTS.md` (retrospective, labelled INFORMED)
- `docs/e171/SEALS.md`
- `docs/e171/AMENDMENTS.md`
