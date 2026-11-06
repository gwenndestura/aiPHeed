# E170 protocol: two-part LightGBM forecasting system (LOCKED 2026-11-06)

**This protocol is fixed before any E170 forecast is computed.** Nothing below may change after:
- (a) the E170 retrospective run, or
- (b) the release of any new provincial food-insecurity outcome.

**Only a code defect may be corrected.** A defect is code that does not do what this text says. Each correction is logged with its diff in `docs/e170/AMENDMENTS.md`, together with whether it changed any result. Performance is never a reason to amend.

**Owner decisions on record (2026-11-06):**
- LightGBM is the required final algorithm.
- An FIES→HFIAS bridge is allowed for the level only.
- C1 is judged on historical plus new rows pooled.
- Gates are not removed after results (C4 stays).

**Evidence base:**
- `docs/final/RELIABILITY_ROADMAP.md`
- `E169_NEW_SIGNAL_TESTS.md`
- `E169_FIES_HFIAS_BRIDGE_FEASIBILITY.md`

## 1. Target (unchanged)
- **Outcome:** HFIAS moderate + severe household food insecurity, as a percentage, by province.
- **HIGH** = 50 % or more.
- Training uses all provinces nationally. Reporting covers Cavite, Laguna, Batangas, Rizal and Quezon.
- Leads 1–8 quarters, with Lead k = k + 1 quarters before the survey quarter (as E156 and E168).

## 2. Model
**Forecast in logit space:** `μ(province p, region r, target quarter T) = L(r, T) + Δ(p, T)`

### Part B: regional level L (the bridge), fixed constants
**Bridge** (FIES moderate + severe → HFIAS moderate + severe, logit scale):
- `logit H = 0.25 + 0.955 · logit F`
- These constants are the midpoints of the 2019 provincial fit (0.158, 0.917) and the 2021 subgroup fit (0.343, 0.994), from E169.

**Level uncertainty** (logit SD):
- `σ_L² = 0.13² (year drift, about ±3 points) + se_F²`
- `se_F` is the FIES sampling SE in logit. Where it is unpublished, it is derived from the 95 % CI, or else assumed to be 0.10.

**Level source at forecast origin t.** Use the newer of these two:

| Source | Value | When usable | Uncertainty |
|---|---|---|---|
| (i) Newest **provincial HFIAS round** usable at t (`ANCHOR_LAG` = 6 quarters, as now) | Unweighted mean logit of that region's provinces measured in that round. If fewer than 2 provinces were measured, the round's national mean logit | Fieldwork quarter + 6 quarters | Level SD 0 (it is the outcome scale) |
| (ii) Newest **regional FIES moderate + severe** published at or before t (PSA SDG 2.1.2 / FNRI NNS) | Bridged with the formula above | From the quarter after its documented public release. If undocumented, from Q1 of the second year after fieldwork (2023 NNS → 2025-Q1 at the latest) | σ_L as above |

- **"Newer"** is judged by fieldwork year.
- **Only regional or national values are used.** No national value is copied into provinces as a provincial value, and no bridged value is ever used as a provincial outcome.

### Part A: provincial deviation Δ (LightGBM)
- **Deviation:** `Δ = logit(province HFIAS) − L_round`. `L_round` is the Part B level of the same region in the same survey round, built as in source (i).
- **Baseline:** the province's own latest measured deviation (relative persistence).
- **Change model:** a LightGBM regressor predicts change in deviation from the five trigger groups (market, climate, employment, remittances, poverty).
  - Same feature sets (`GOV`, `FULL`, `GOV+cons`, `FULL+cons`) as E168, with news kept inside the groups.
  - Same monotone signs (`Pv.SIGN`) and the same correlation pruning.
  - Same hyperparameter grid (leaves 3/7, min-child 10/40, λ 5/20, trees 150/400, learning rate 0.02).
  - Same weights `1/(se² + 0.05)`.
  - Same region-grouped inner CV for nested selection on training rows only.
  - Anchors H/OH/RSS are **not** used in E170. The baseline is relative persistence only.
- **Calibration layer:** raw or linear (shrinkage of Δ), chosen by inner cross-fitted Brier on training rows only, as in E168. Platt is excluded.

### Probability
- `P(HIGH) = Φ(μ / σ)`, where `σ² = σ_Δ²(gap) + σ_L²`.
- `σ_Δ` comes from inner residuals by gap (`A4.scale`, as in E168).

### As-of rules
Every input respects its publication lag:
- HFIAS lag: 6 quarters.
- CPI: 2-month lag.
- Other inputs: as in E150 and E152.
- FIES: the publication rule above.

The leakage-corruption test (unreleased survey values replaced by noise) must change no forecast by more than 1e-9.

## 3. Evaluation
### 3.1 Retrospective rows (historical, already read)
- Run E170 once, as written, for ENNS 2018, 2019 and 2021, Leads 1–8. Report it as is.
- For 2018/2019, no FIES existed before the origins, so Part B falls back to source (i), the 2015 round. That is expected and is not to be fixed.

### 3.2 Prospective rows (the acceptance evidence)
**Seals:** immediately after the retrospective run, and before any new outcome is seen, seal hashed E170 forecasts for:
- (a) every ENNS 2022 province (beside E158 `f69e7a02` and E166 `49e514d2`);
- (b) 2027-Q1 for all provinces.

**Qualifying outcomes:**
- Provincial **HFIAS** moderate + severe published by DOST-FNRI after the seal date, for fieldwork after the latest data used at the forecast origin.
- Provincial FIES-only results are reported as a **secondary** check (forecasts converted to FIES with the inverse bridge). They are never pooled into gates.

### 3.3 Gates (E156 C1–C6, unchanged definitions and constants: SHARED 0.726, PER_CELL 1.8)
- **Gates are computed at each lead on the POOLED set:** the E170 retrospective Lead-k rows plus all qualifying prospective Lead-k rows.
- **The maximum reliable lead** is the largest k such that leads 1..k all pass C1–C6 (sequential, as in E156).
- **C1 reference (from E169):** with a 75 % retrospective accuracy, about 22 new provinces at 80 % or 50 at 75 % would be needed. This is an expectation, not a criterion.
- **Supplementary (reported, not gates):** C4 within-round calibration slope; Brier versus E158 and versus persistence; HIGH recall and precision; bias by round and by island.

### 3.4 Controls (must hold, as in E168)
- Leakage corruption: change no more than 1e-9.
- All trigger inputs shuffled across provinces: reported. **Acceptance additionally requires real inputs to be no worse than shuffled.** The CI upper bound of Brier(real) − Brier(shuffled) must be 0.005 or less.
- Group ablation: reported.

### 3.5 Decision rule
| Outcome | Decision |
|---|---|
| All C1–C6 pass at Lead 1 on the pooled set **and** the controls hold | **ACCEPTED.** E170 replaces E158 in production (deployment needs separate owner go-ahead) |
| Otherwise | **NOT ACCEPTED.** E158 stays. The result is reported as is |

## 4. What is forbidden
- Changing any constant, grid, feature list, gate, threshold or pooled set after the retrospective run or after any new outcome.
- Re-running the retrospective procedure with variations and reporting the best one.
- Choosing which new rounds or provinces to pool. All qualifying rows count.
- Using bridged FIES as a provincial outcome, or copying national values into provinces.

## 5. Deliverables
- `backend/app/e170/`, `backend/data/e170/out/`
- `docs/e170/RESULTS.md` (retrospective)
- `docs/e170/SEALS.md`
- `docs/e170/AMENDMENTS.md` (empty unless a defect is found)
