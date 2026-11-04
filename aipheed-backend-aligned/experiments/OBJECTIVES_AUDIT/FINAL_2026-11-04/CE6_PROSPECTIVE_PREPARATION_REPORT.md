# C-E6 prospective validation preparation report (2026-11-04)

**Summary:**
- **Done and tested:** the prospective registry, the sealing procedure (dry-run tested, replay exact) and the future
  evaluation framework (validated against the historical results) for C-b, C-E2 and C-E6.
- **Nothing was sealed, committed, pushed or deployed.** No ledger was written. The demo still serves C-E2, and the
  dashboard is unchanged.
- **Pending future validation:** every 2027+ result.

## 1. Initial state (verified before any change)

- **Repository:** `C:\aiPHeed-final1`, branch `aiPHeed/system-fixes`, HEAD `3e15c3e`.
- **Protected files:** 200 match `integrity/protected_before_2026-11-04.sha256`.
- **Artifacts:**

  | File | SHA-256 |
  |---|---|
  | `ce2_fits.csv` | c078aa27… |
  | `ce2_results.json` | 13666bfd… |
  | `ce6_fits.csv` | 249c358b… |
  | `ce6_results.json` | 7e3ae937… |
  | `ce6_features.csv` | 011509a9… |

- **Ledgers:** C-b protocol `SENIOR_REVIEW/prospective/SEAL_LEDGER.md` b22faf62…; `backend/seals/LEDGER.md` 7b4dd9dc….

**At the end of the task:** all of the above are identical; 14 tracked modifications (the same set as before the task);
HEAD unchanged.

## 2. C-E6 pre-registration

- `CE6_PREREGISTRATION.md`: PLAN-SHA256 `6e07ee14ecfd7925561c20e7774593d15c69d1d0501f0ee5227854e604af5ac8`,
  recomputed and matching.
- **Registry entry:** `NEW_MODEL/ALLBASE/REGISTRY.csv` (C-E6, Leads 1–2).
- **Features unchanged:** ST1, ST2; stock month ≤ issue month − 4.

## 3. Prospective registry (`OBJECTIVES_AUDIT/prospective_ce/REGISTRY_CE.json`, built by `runner/ce_registry.py`)

**Every field is computed from the files** (hashes, feature lists, development metrics). `verify` recomputes everything
and must match.

| Model | Status | Pre-registration / protocol | Sealed by | Leads sealed |
|---|---|---|---|---|
| C-b | **MAIN MODEL** (adopted); seal 67baec66 verified | `SENIOR_REVIEW/PROSPECTIVE_PLAN.md` 194ecb72… | `SENIOR_REVIEW/runner/seal_next.py` (unchanged) | 1, 2 |
| C-E2 | Development candidate (local demo) | CE2 a1b469da… | `OBJECTIVES_AUDIT/runner/seal_ce.py` | 1, 2, 3 |
| C-E6 | Development candidate | CE6 6e07ee14… | `seal_ce.py` | 1, 2, 3 |

**Each entry records:**
- version (runner hash);
- method;
- the full feature list;
- sources and publication rules (E2 quarters ≤ t−2; rice stocks M ≤ issue − 4, file hash, vintage limitation);
- issuance rule;
- artifact hashes;
- development metrics;
- evaluation criteria;
- adoption status.

The code hashes cover all runners and shared libraries. `prospective_seals` is empty.

**Protocol for the C-E models:** `OBJECTIVES_AUDIT/CE_PROSPECTIVE_PLAN.md`, PLAN-SHA256
`9392917aeaabbbecf5040f13aefdea4b9ff55368c9dc9fb2e3917a85e0e4d24c`. It was fixed before any procedure ran. It adds the
C-E models without changing the C-b protocol.

## 4. January 2027 forecast procedure (`runner/seal_ce.py`)

| Step | Implementation |
|---|---|
| 1. Forecast generation | Full table rebuilt from current files (`prospective_lib.build_table` + news anomaly, as `seal_next.py`). E2 and ST1/ST2 added. `ce2_model._origin` and `ce6_model._origin` run unchanged |
| 2. Input cutoff validation | `prospective_lib.freshness` keys + `remittance_quarter_t-2` + `rice_stock_month_issue-4`. A real seal refuses unless each stale key is named (and recorded) |
| 3. Rice-stock publication rule | M = issue month − 4, from `ce6_model.st_values` (unit-tested: later months cannot change the value) |
| 4. Leakage prevention | Training labels known at O(t) only. Refuses if an SWS round of any target quarter is published |
| 5. Artifact | `sealed_ce_<issue>.csv`: model × lead rows with p, class, persistence, climatology, feature cutoffs, stale sources, code and input SHA-256s, pre-registration and plan hashes, commit |
| 6. SHA-256 | Of the artifact; written to the ledger (real mode only) |
| 7. Model identity | Pre-registration hashes checked at start. `model_id`, `prereg_sha256` and `code_sha256` on every row |
| 8. Registry recording | `REGISTRY_CE.json` lists the ledger's seals (`ce_registry.py build`) |
| 9. Dry run and replay | `--dry-run --out DIR` (never into `prospective_ce/` or `SENIOR_REVIEW/prospective/`) |
| 10. Audit trail | Ledger row (file, SHA-256, issue, targets, sealed_at, commit), plus the JSON report printed by the run |

**Real-mode guards** (none was exercised; refusal tested):
- `--seal`;
- `prospective_ce/AUTHORIZATION_<issue>.txt` containing `AUTHORIZED: seal_ce <issue>`;
- issue ≥ 2027-01-01;
- 0–14 days after the issue date;
- no target round published;
- model code committed;
- the file must not exist yet.

## 5. Sealing dry-run results

| Dry run | Result |
|---|---|
| Issue 2026-10-01 (origin 2026-Q3, has stored fits) | **Replay exact.** Rebuilt table vs stored: max difference 1.8e-15, NaN pattern equal. All 6 forecasts (C-E2 and C-E6 × Leads 1–3) differ by 0.0 |
| Issue 2027-01-01, today 2027-01-05 | **Runs end to end.** Stale: CPI food, CPI rice, ONI, Pink Sheet, typhoons, news. Remittance (2026-Q2) and rice stock (2026-09) fresh. **These numbers are NOT forecasts:** the data files end in Sept/Oct 2026. A real seal would refuse until the inputs are refreshed in January |
| C-b protocol (`seal_next.py`, earlier today) | Replay matches; ledger untouched |

## 6. Future evaluation framework (`runner/score_ce_prospective.py`)

**Sources (all read only, every SHA-256 checked against its ledger):**
- C-b and the baselines: the C-b protocol's ledger and its C-b seal, via `score_prospective.collect`.
- C-E2 and C-E6: the CE ledger.

**Labels:**
- `labels_at(date)`: only published, ended quarters; only targets ≥ 2027-Q1.
- **Tested:** at 2027-03-01, no label exists and nothing is scored.

**Per model and lead:** `score_prospective.score_lead`:
- accuracy, balanced accuracy, precision, recall, F1, AUC, Brier, ECE;
- the frozen R1–R7 with an independent recomputation;
- the 75% rule with Wilson 90%;
- **Algorithm 4:** the first 4 quarters.

**Families** (`phase_c._paired`: paired Brier, CI, one-sided cluster bootstrap, seed 2036, B 5000):
- **P1:** C-E6 vs the 7 baselines (Holm 14).
- **P2:** C-E6 vs C-E2 and vs C-b (Holm 4).
- **P3:** C-E2 vs the 7 baselines (Holm 14).

Each family is computed only from 20 labelled prospective quarters per lead for every model. Verdicts are
"insufficient" below 40.

**The four questions are reported separately:**
1. probabilities (Brier);
2. calls (exact McNemar on discordant calls);
3. stability (R7 from 40 quarters);
4. all-baseline superiority (all of P1 significant).

**Validation:** run on the stored development forecasts, the scorer reproduces **all 14** historical C-E6 tests
exactly (difference, p and n). The replay also shows two things the prospective test will face:
- **P2 under the 4-test Holm:** C-E6 vs C-E2 at Lead 1 has Holm p = 0.050, so it is not significant.
- **McNemar vs C-b:** C-E6 is wrong on 1 (Lead 1) and 2 (Lead 2) quarters where C-b is right, and never the reverse.

## 7. R3 and R7 investigation (existing evidence; `runner/obj2_r3r7_margin.py` → `out/obj2_r3r7_margin.json`)

**Correction to the earlier checklist:** R7 requires each third ≥ **0.60** and a leave-one-quarter-out minimum
≥ 0.70 (`hr_lib` rule). It is not 0.75.

| | R3 needs | R7 needs | Nearest missed LOW quarter |
|---|---|---|---|
| Lead 1 | **1** more correct LOW (TN 9 → 10 of 19) | **2** more correct calls in 2015-Q2..2020-Q4 (11 → 13 of 21) | 2018-Q1: C-E6 0.539 (C-E2 0.541). Observed 11.0%; P(true HIGH) 0.41, so the label itself is a coin flip |
| Lead 2 | 1 more correct LOW | 2 more in the middle third | 2018-Q2: 0.523 (observed 7.3%) |

**C-E6's effect:** it moved 7 of the 10 missed-LOW Lead-1 probabilities down, by 0.001–0.026. That is the right
direction but too small to cross 0.50. It changed **no** call at either lead.

**Reading:**
- R3 and R7 are 1–2 calls from passing. That is precisely why no threshold, label or period may be adjusted: one
  flipped call on a noise-level label would "pass" without evidence.
- **Needs new observations:** whether C-E6 gets LOW quarters right. 2027+ quarters will show it. A regime like
  2015–2020 cannot be re-created.
- **Needs independent data:** a regional (not national) availability or income series. The regional rice stocks exist
  only for 2026.

## 8. Audit of the "impossibility" claim (`runner/obj4_impossibility_audit.py` → `out/obj4_impossibility_audit.json`)

| Point audited | Finding |
|---|---|
| Noise-floor derivation | The plug-in floor 0.0505 is close to the posterior-integrated floor of **0.0502** (n = 600, SRS; SWS's stated ±4% is the SRS margin at p = 0.5). Sensitivity: **0.069** (n = 300 or design effect 2), **0.090** (both). It bounds the **expected** Brier only; a 62-quarter realisation can fall below it |
| Paired variance | SD of the per-quarter Brier gain 0.105–0.415 by comparison. It is assumed unchanged for a better model, which is not guaranteed (sensitivity ×0.75 / ×1.25) |
| Independent units | 62 quarters (19–20 for the news-only baselines). Leads 1 and 2 share quarters and are not independent |
| Temporal dependence | Lag-1 ρ 0.01–0.54; n_eff = n(1−ρ)/(1+ρ) (AR(1) approximation) |
| **Holm step (error in the earlier claim)** | Holm compares the i-th smallest p with α/(14−i+1). Only the strongest comparison faces α/14. **"Some targets need a Brier below the floor" was therefore wrong:** it applied α/14 to every comparison |
| Correct joint requirement (80% power) | **0.074** with SD unchanged; 0.12 if SD ×0.75; 0.02 if SD ×1.25. The single-comparison requirement at α 0.05 is 0.096–0.21 |

**Verdict on the claim:**
- **Not proven impossible.** Under the most favourable assumptions (n = 600, SRS, unchanged variance), all seven could
  be shown with a Brier of about 0.07.
- **Practically unattainable with 62 quarters:** about 0.07 is 60% below C-E6 (0.184), and within 0.02 of a perfect
  true-state forecaster. Under n = 300 or design effect 2, it lies at or below the floor.
- **Correct statement: severely underpowered, not impossible.** The earlier wording in `CE6_MODEL_IMPROVEMENT_REPORT.md`
  §14 ("below that floor, which no model can reach") overstated it, and is superseded here.

## 9. Reproducibility and leakage

**`runner/test_ce_prospective.py`: 11 passed:**
- pre-registration and plan hashes;
- a real seal is refused without authorization, and no file or ledger is created;
- dry runs cannot write into `prospective_ce/` or `SENIOR_REVIEW/prospective/`;
- exactly one mode;
- rice-stock features cannot see months after issue − 4, while the allowed month does change them;
- E2 cannot see quarters after t − 2;
- the registry is reproducible, with 3 identities, and the C-b seal verified;
- a tampered sealed file is rejected;
- no unpublished label is scored;
- the scorer reproduces the historical C-E6 family;
- the seal dry run replays the stored fits (slow test).

**Determinism:** fixed seeds (LightGBM `hr_lib`, bootstrap 2036). The replay is exact.

## 10. Dashboard and API preservation

- **No frontend, backend application, API or serving file was changed in this task.** 200/200 protected files are
  unchanged, including every file in `frontend/src`.
- **Dashboard and API tests:** 87 passed, 8 skipped. The last full backend suite gave 1,022 passed; the backend code
  has not changed since.
- **The demo still serves C-E2:** `/api/v1/config` → `ALLBASE-CE2`, MRLT 3; frontend 8081 returns 200. C-E6 is not
  added.
- **Driver groups:** the five groups are unchanged. A rice-stock display is proposed only, in
  `RICE_STOCK_DRIVER_PROPOSAL.md`; not implemented.

## 11. Files created or modified

**Created:**
- `OBJECTIVES_AUDIT/CE_PROSPECTIVE_PLAN.md` (9392917a…);
- `prospective_ce/REGISTRY_CE.json` (3d7cf6f7…; first built earlier in the task, rebuilt once after the scorer was
  added, before any seal);
- `runner/ce_prospective.py`, `seal_ce.py`, `score_ce_prospective.py`, `ce_registry.py`, `test_ce_prospective.py`,
  `obj2_r3r7_margin.py`, `obj4_impossibility_audit.py`;
- `out/obj2_r3r7_margin.json`, `out/obj4_impossibility_audit.json`;
- this report and `RICE_STOCK_DRIVER_PROPOSAL.md`.

**Modified:** none of the existing files. C-b, C-E2 and C-E6 artifacts, seals, ledgers, the C-b protocol scripts, the
backend, the frontend and production configuration are unchanged.

**Dry-run outputs:** the session scratchpad only.

## 12. Actions requiring your approval

1. **Commit** the C-E model code, plans and this procedure. A real seal refuses while the code is uncommitted.
2. **Authorize the 2027-01-01 seal:** create `prospective_ce/AUTHORIZATION_2027-01-01.txt` with
   `AUTHORIZED: seal_ce 2027-01-01`. Refresh the inputs, then run `seal_ce.py --issue 2027-01-01 --seal` between 1 and
   15 Jan 2027. The C-b protocol's own seal (`seal_next.py`) runs in the same window.
3. **Later:** commit each seal and its ledger row.
4. **Optional:** serve C-E6 in the demo, and the rice-supply driver proposal (frontend change).

| | Status |
|---|---|
| Completed implementation | Registry, sealing procedure, evaluation framework, tests, R3/R7 margin analysis, impossibility audit |
| Verified results | Replay exact; scorer reproduces history; refusals work; no leakage path found; dashboard unchanged |
| Pending future validation | All prospective metrics, Algorithm 4, families P1–P3. First labels are expected from mid-2027; families from about 20 quarters (2032) |
