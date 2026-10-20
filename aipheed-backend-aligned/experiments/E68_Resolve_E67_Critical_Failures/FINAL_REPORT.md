# E68: resolving E67's critical failures

**Date:** 2026-10-20
**Branch:** `resolve-e67-critical-failures`, from `best-model-objectives-1-4-lead2` @ `f8c4416` (`out/original_head.txt`).
**Protocol:** `PROTOCOL.md`, frozen 2026-10-20T02:33:27Z before any arm was scored (SHA-256 `a32690a4…`).
**Companion reports:** `TARGET_VALIDITY_REPORT.md`; `FAILURE_REGISTER_AND_COMPLIANCE.md`, which holds the failure register and the Objectives 1–4 matrix.

> **Evidence status.** All 50 Lead-2 evaluation rows had been examined by E56–E67, so everything scored here is **development evidence**. The only unseen period is the future. Every E68 variant's 2026-Q4 and 2027-Q1 forecasts are therefore **sealed** (`sealed/prospective.csv`, SHA-256 `79aa6f2a…`), to be scored when PSA and SWS publish those quarters.

---

## 1. Result in one paragraph

**The > 75% Lead-2 accuracy goal is NOT met on valid evidence.** The served model is unchanged, the E56-TUNED LightGBM at 0.72 (36/50).
- **Corrections tested.** The four pre-registered corrections target documented defects:
  - M1: missing and stale data;
  - N1: national inputs;
  - K1: El Niño projection;
  - C1: M1 + K1.

  None beats it by the frozen rule.
- **Best variant (K1/C1):** 0.76 (38/50), but balanced accuracy is 0.715 and HIGH recall 0.556, so class sensitivity fails.
- **Best reading (K1-EW):** 0.82 (41/50) with balanced accuracy 0.81. It rests on two quarters of one El Niño episode and on an early-warning rule designed after these rows were seen, so it is **not a legitimate demonstration**.
- **Target finding:** on every evaluated row the target is provincial food-price pressure. A revised affordability target (T-AFF) describes 2026 better but cannot be forecast with the available inputs.
- **El Niño finding:** the El Niño question cannot be answered from the data. The only in-window episode (2023–24) came with falling inflation, so food inflation ended 4.2–6.5 points **below** projections.

What E68 delivers is correction of what the system says and records. In the opt-in mode `AIPHEED_LEAD2_MODEL=e68`:
- every input is classified at its issue date;
- observed affordability stress is shown as an observation;
- the score is named an exploratory food-stress score;
- every LOW-under-El-Niño-watch forecast explains why it is LOW and what the data cannot show.

---

## 2. Protecting existing work

| Check | Result |
|---|---|
| Start state | `best-model-objectives-1-4-lead2` @ f8c4416, equal to origin after `git fetch` |
| Uncommitted changes | only the E46 D-1 hunks of another session (`insights.py`, `e41_lead2.py`, untracked d1 files). Preserved, not committed (`out/original_uncommitted.diff`) |
| New branch | `resolve-e67-critical-failures` (`git switch -c`) |
| Frozen evidence | E38–E67 records, sealed files and tables untouched. E68 writes only under `E68_…/`, `backend/data/e68/` |
| Production default | E38, unchanged |

---

## 3. Target validity (summary; detail in `TARGET_VALIDITY_REPORT.md`)

- **T43 = PS on 50/50 evaluation rows.** Hunger was above 11.3% in every quarter from 2024 on; 47 rows have hunger above the line but T43 LOW; 12 of 21 quarters have one label for all provinces.
- **Thresholds:** frozen E40 P60s chosen from label prevalence, not model output. E68 reproduces them exactly.
- **T-AFF** (pre-registered, hindsight disclosed):
  - It changes 20 of 50 labels and moves HIGH to 2026.
  - TAFF-LGBM equals always-LOW; TAFF-RULE has balanced accuracy 0.57.
  - Not adopted. Its forward forecasts are sealed.
- **Independent outcome:** PSA subsistence incidence (2021, 2023) is the only provincial measure. With n = 5 per year and CVs up to 62% it is uninformative.
- **Claim supported:** an exploratory food-stress score (price pressure under high regional hunger). A validated food-insecurity forecast is **not** supported.

---

## 4. El Niño (Q3 2026 → Q4 2026 → Q1 2027)

**Available at issue** (`enso_context.PAGASA_ENSO`, verified against pagasa.dost.gov.ph on 2026-10-20):

| Issue date | PAGASA status in force |
|---|---|
| 2026-04-01 (target Q3) | El Niño Watch only |
| 2026-07-01 (target Q4) | El Niño Advisory No. 1 |
| 2026-10-01 (target 2027-Q1) | Climate Advisory 2026-09-23 (strong → very strong; risk of agricultural dry spells) |

Published after the last issue: Advisory No. 5 (2026-10-07).

**Rainfall, dry spell, drought:**
- PAGASA's pages hold no dated 2021–2026 archive, and the drought-assessment URL returns 404 (`sources/SOURCES.md`).
- The repository's provincial rainfall file has pre-2021 rows and is excluded by the study window.
- A drought feature therefore **cannot be back-tested** without post-issue information. None was built.

**Factors behind the decline** (E67 `r4_el_nino_trace.csv`, reproduced):
- **Price projection:** projected food inflation of 0.8–2.1% for 2027-Q1, against HIGH lines of 4.7–7.2%. Headline inflation outran food, which the gap rule counts as relief.
- **Configuration switch:** configuration 68 at the 2026-07-01 origin.
- **Climate inputs:** they reach the model (5 splits at 2027-Q1) with negligible effect.
- **Not a cause:** missing climate data.

**Forward climate arm K1** (pre-registered; it shifts the projection by the province's mean projection error in earlier El Niño-advisory quarters):

| Quantity | Value |
|---|---|
| Origins where it acts | 2023-Q4, 2024-Q1, 2026-Q2, 2026-Q3 (`tables/r1_elnino_shift.csv`) |
| 2023–24 food projection errors | **negative** in every province (−4.2 to −6.5 pts, m = 1.0) |
| Evaluation rows affected | 10 (2 quarters): correct 4 → 6, Brier 0.354 → 0.314 |
| Over all 50 rows | Brier −0.008 (CI −0.031..+0.011), quarter wins 1/1 |

K1 raises scores only because the headline errors were larger than the food errors, so the gap channel rose. It encodes the 2023 disinflation, not an El Niño effect, so it is **not a valid El Niño representation** and is not adopted. It was declared untestable before scoring (PROTOCOL §2).

**Dashboard (e68):**
- The CFSW hazard watch stays separate from the score.
- Each LOW-under-watch forecast says why it is LOW (its projection against its line) and that the one in-window El Niño cannot show the price effect.
- Nothing is forced to HIGH.

---

## 5. Missingness and stale data

| Input situation | Previously | E68 |
|---|---|---|
| Typhoon count of the in-progress quarter (2026-Q3) | stored 0 | model arm M1: NaN; serving: status `substituted` |
| News share from < 10 titles | a measured 0 | M1: NaN; serving: `too_few_articles` |
| News share 0 from ≥ 10 titles | 0 | `observed_zero` |
| SWS round older than one quarter | ignored | M1: hunger RMSE × sqrt((2 + age) / mean training horizon); serving: `stale` with data age |
| Remittances 2026 | NaN (learned branch) | `missing`, "treated as unknown, not as no change" |
| PAGASA outlook, rainfall/drought, fish-kill events | silently absent | `not_collected`, each with its reason |

- **Effect of M1 on Lead-2:** Brier −0.0013 (CI −0.0031..+0.0005). The correction is principled but not measurable on 50 rows.
- **Imputation:** none (LightGBM NaN routing). The hunger ridge's median fill is fit on the training rows of each origin only, as before.
- **Tests:** `test_missing_and_thin_inputs_become_nan_not_zero` and `test_input_status_classifies_stale_missing_and_placeholder` cover missing, stale, delayed (CPI month after issue not used) and placeholder inputs.

---

## 6. Five trigger groups

Per-group ablations use identical origins and targets (E67 R1 on T43, 50 rows). Sources: E67 `tables/r3_goal_test.csv`; E68 `tables/r3_t43_arms.csv`, `r3_t43_paired_vs_A0.csv`.

| Removed | Acc | Bal | Rec HIGH | Rec LOW | F1 | Brier | Onsets | Δ Brier vs A0 (95% CI) |
|---|---|---|---|---|---|---|---|---|
| none (A0) | 0.72 | 0.684 | 0.556 | 0.812 | 0.588 | 0.214 | 3/10 | — |
| climate | 0.68 | 0.653 | 0.556 | 0.750 | 0.556 | 0.219 | 3/10 | +0.005 (−0.006..+0.018) |
| fish | 0.74 | 0.700 | 0.556 | 0.844 | 0.606 | 0.210 | 3/10 | −0.004 (−0.010..+0.001) |
| employment | 0.72 | 0.684 | 0.556 | 0.812 | 0.588 | 0.211 | 3/10 | −0.003 (−0.013..+0.003) |
| OFW | 0.68 | 0.653 | 0.556 | 0.750 | 0.556 | 0.202 | 3/10 | −0.012 (−0.033..+0.005) |
| news | 0.74 | 0.700 | 0.556 | 0.844 | 0.606 | 0.212 | 3/10 | −0.002 (−0.007..+0.002) |
| employment + OFW (E68 N1) | 0.72 | 0.684 | 0.556 | 0.812 | 0.588 | **0.192** | 3/10 | **−0.022 (−0.041..−0.004)**, 8/2 quarters, Holm p 0.22 |
| all but market | 0.68 | 0.641 | 0.500 | 0.781 | 0.529 | 0.212 | 3/10 | −0.002 (−0.021..+0.012) |

**Why the single-group ablations are null** (`tables/r2_trigger_variance.csv`, E67 attribution):
1. The CPI projection enters as a structural offset and carries the skill. Trees are depth 1–3 with 10–100 rounds.
2. ENSO, employment, OFW and the rice-policy flags have **zero cross-province variance**: they are national or regional. They can only shift whole quarters, acting as time proxies.
3. News trigger shares are 0 in 46–100% of rows. The region-wide corpus (median about 26 admitted trigger articles per quarter) becomes very thin per province.
4. "Fish kill" is fisheries production; there is no event series.
5. The sample is 10 quarters.

**What each group can contribute now:**

| Group | Contribution |
|---|---|
| Market | the signal |
| Climate | observed inputs only; forward climate untestable in-window |
| Fisheries | production proxy only |
| Employment and OFW | national; removing them is the most promising change (N1), and it is sealed for prospective scoring |
| News | context only |

---

## 7. Lead-2 controlled comparison

All rows: the same 10 origins and 50 rows, the T43 target, and 10 independent quarters (`tables/r3_t43_arms.csv`).

| Reading | Correct | Acc (quarter-cluster CI) | Bal | Prec | Rec H / L | F1 | FAR | Brier | AUC | Onsets | Acc − always-LOW lower bound |
|---|---|---|---|---|---|---|---|---|---|---|---|
| A0 E56-TUNED (served) | 36 | 0.72 (0.56–0.84) | 0.684 | 0.625 | 0.556 / 0.812 | 0.588 | 0.19 | 0.214 | 0.649 | 3/10 | −0.06 |
| M1 missing/stale | 36 | 0.72 | 0.684 | 0.625 | 0.556 / 0.812 | 0.588 | 0.19 | 0.213 | 0.649 | 3/10 | −0.06 |
| N1 provincial-only | 36 | 0.72 | 0.684 | 0.625 | 0.556 / 0.812 | 0.588 | 0.19 | 0.192 | 0.724 | 3/10 | −0.06 |
| K1 El Niño shift | 38 | 0.76 (0.60–0.90) | 0.715 | 0.714 | 0.556 / 0.875 | 0.625 | 0.13 | 0.206 | 0.665 | 3/10 | 0.00 |
| C1 = M1 + K1 | 38 | 0.76 | 0.715 | 0.714 | 0.556 / 0.875 | 0.625 | 0.13 | 0.205 | 0.668 | 3/10 | 0.00 |
| A0-EW (P_price ≥ 0.5, post hoc) | 39 | 0.78 (0.70–0.86) | 0.780 | 0.667 | 0.778 / 0.781 | 0.718 | 0.22 | 0.182 | 0.786 | 7/10 | −0.02 |
| N1-EW (post hoc) | 39 | 0.78 | 0.780 | 0.667 | 0.778 / 0.781 | 0.718 | 0.22 | 0.167 | 0.809 | 7/10 | −0.02 |
| K1-EW / C1-EW (post hoc) | 41 | 0.82 (0.74–0.90) | 0.811 | 0.737 | 0.778 / 0.844 | 0.757 | 0.16 | 0.171 / 0.170 | 0.797 | 7/10 | +0.02 |
| Persistence | 28 | 0.56 | 0.535 | 0.400 | 0.444 / 0.625 | 0.421 | 0.38 | 0.440 | 0.535 | 0/10 | −0.34 |
| Always LOW | 32 | 0.64 | 0.500 | — | 0 / 1 | 0 | 0 | 0.360 | 0.500 | 0/10 | 0 |

**Goal test (G1 accuracy > 0.75; G2 balanced ≥ 0.70 and both recalls ≥ 0.60; G3 beats always-LOW and persistence at the quarter level; G4 pre-specified before the rows were seen; G5 target T43):**

| Reading | Outcome |
|---|---|
| K1 / C1 | G1 met; G2 fails (HIGH recall 0.556) |
| K1-EW / C1-EW | G1–G3 met; **G4 fails** (the EW rule was set by E58 after it inspected these rows; K1 was pre-registered here, but on examined rows and acting on 2 quarters) |
| All others | G1 fails |

**No reading legitimately meets the goal.** Paired Brier against A0 (Holm): no arm is better by the rule (`r3_t43_paired_vs_A0.csv`).

**Probability calibration.** This is assessed only as development diagnostics (slope 0.55 for A0). The served number is labelled "model score, not a tested probability", because the product of the two parts is not a joint probability.

**Other horizons** (separate analysis; not used for Lead-2): E63/E66 for the served procedure give lead 1 0.85 / Brier 0.130, lead 2 0.214, lead 3 0.251, and lead 4 not computable. E68 arms were not re-run at other leads; no lead-1 result is used for any Lead-2 claim.

**Unseen period.** `sealed/prospective.csv` holds 70 rows: 7 variants × 2 targets × 5 provinces. Scoring follows PROTOCOL §6 once 2026-Q4 (CPI Oct–Dec 2026, SWS Q4 2026) and 2027-Q1 are published. A test checks the seal hash.

---

## 8. News integration

| Check | Finding |
|---|---|
| E60 improved pipeline | available and reproducible (E62/E64). Pipeline v3 is served only in e64 mode, where config 23 uses no news |
| Temporal validity | news of quarter t is used only for issues after t (E62 D2); 2,118 of 2,132 E60 articles were collected after their issue dates (retrospective) |
| Coverage | E60 province coverage is 0 in 44% of province-quarters; province trigger shares are 0 in 64–100% |
| Attribution | E64 admits about 26 trigger articles per quarter region-wide (median; range 2–100); de-syndication in v3 |
| Classification vs forecasting | classifier F1 0.38 → 0.83 (E60) **did not** produce a forecasting gain: E60-C 0.215, E64-D 0.204 vs 0.214 Brier; X_news Δ −0.002 |
| Decision | not forced into the model; context layer only; M1 treats thin-news shares as unknown |

---

## 9. LGU prioritization

- **API (test):** 142 unique LGUs; Batangas 34, Cavite 23, Laguna 30, Quezon 41, Rizal 14; all finite, risk level present, 0 ties (exact ranks).
- **Browser check in e68 mode (2026-10-20):** every LGU shown in each province panel matches the API `riskIndex` to 2 dp: Quezon 41/41, Batangas 34/34, Cavite 23/23, Laguna 30/30, Rizal 14/14, so **142/142**.
- **Map:** every LGU polygon is painted with the approved low-risk colour (#EAB308), consistent with all API risk levels being "low" at 2027-Q1.
- **Sensitivity** (E66 r6, unchanged): within-province order is robust to a 0.5–0.7 poverty weight, not to dropping a component; Lucena's rank depends on an unverified substitute.
- **Climate-exposure weighting:** not added. No LGU-level exposure data exist in the system, and a new weight would be an unapproved method change.
- **Meaning:** relative prioritization within a province, not a municipal forecast. No municipal accuracy is claimed.

---

## 10. Dashboard integration (e68 mode; no frontend file changed)

| Required item | Where it appears |
|---|---|
| Dynamic Lead-2 target | timeline and banner (Q1 2027 on 2026-10-20; `forecast_target`) |
| Province results | map and panel (all LOW; Quezon 0.15) |
| LGU prioritization | panel list and map (142/142 checked) |
| Drivers | existing bars and the summary sentence |
| Model version and issue date | `summary.modelIdentity` and the sentence ("E56-TUNED, configuration 23, Lead-2, issued 2026-10-01") |
| Freshness, missingness, sufficiency | `summary.inputStatus` (23 inputs, 7 statuses) and the sentence ("Inputs at the issue date: 17 of 23 observed; stored as a placeholder: …; not collected: …; missing: …") |
| Price pressure vs exploratory score vs climate warning vs validated outcome | event text "the exploratory food-stress score (… not a measure of household food insecurity)"; separate CFSW watch; affordability shown as an observation; validation status in the sentence |
| LOW under an official climate warning | "Why the score is LOW although a climate watch is in force …", plus the E68 El Niño finding |

**Browser verification:**
- **Setup:** 2026-10-20, preview stack `aipheed-e68-stack` (API 8068, approved frontend 8098).
- **Rizal panel:** all eight required text elements are present.
- **Console:** pre-existing PMTiles basemap errors only.

---

## 11. Tests (actual results, 2026-10-20)

| Suite | Result |
|---|---|
| Backend full (`pytest -q tests`) | **495 passed, 18 skipped, 0 failed** (`out/backend_full_suite.txt`); +13 E68 tests over E67's 482 |
| Backend, committed tree only (working copies of `insights.py`/`e41_lead2.py` swapped for the staged versions, untracked E46 D-1 test excluded, then restored byte-identical) | **486 passed, 18 skipped, 0 failed** (`out/backend_committed_tree_suite.txt`); the 9 fewer are the uncommitted D-1 tests |
| Frontend vitest | 46/46 |
| Frontend production build | passed |
| `tsc --noEmit` | 6 errors, all pre-existing in `src/data/mockData.ts` (mock data not rendered) |
| Browser end-to-end | passed (sections 9–10) |

**New tests in `tests/integration/test_e68_resolve_e67.py`:**

| Area | Coverage |
|---|---|
| Protocol | frozen; A0 reproduces E57 |
| Target | T43/PS/T-AFF construction and frozen thresholds |
| Results | no arm beats A0; goal not met; T-AFF degenerate |
| Seal | prospective seal intact |
| Missing and stale data | missing/thin to NaN; input-status classes |
| Hunger widening | only widens |
| Climate timing | PAGASA timing at exact dates |
| K1 | acts only with El Niño in force; negative in 2023–24 |
| National inputs | zero cross-province variance |
| Serving | e68 numbers = e58; identity; production default |
| Explanations | LOW-under-watch, El Niño and affordability text consistent with the disclosure |
| LGUs | 142 finite and coloured |

---

## 12. Demonstration and deployment

**Local** (from `backend/`):

```
set AIPHEED_LEAD2_MODEL=e68
venv\Scripts\python.exe -m uvicorn app.main:app --port 8000
:: or API 8068 + approved frontend 8098 in one process:
venv\Scripts\python.exe -B ..\aipheed-backend-aligned\experiments\E68_Resolve_E67_Critical_Failures\runner\serve_e68_stack.py
```

**Reproduce E68** (from `backend/`):

```
venv\Scripts\python.exe -B ..\aipheed-backend-aligned\experiments\E68_Resolve_E67_Critical_Failures\runner\r1_arms.py
venv\Scripts\python.exe -B ..\aipheed-backend-aligned\experiments\E68_Resolve_E67_Critical_Failures\runner\r2_diagnostics.py
```

- `r3_score.py` refuses to re-seal. To re-run it, copy the folder.
- `r4_build_disclosure.py` rebuilds `data/e68/e68_disclosure.json`.

**Preview or production (not done; needs authorization):**
- Deploy this branch to a preview API with env `AIPHEED_LEAD2_MODEL=e68`.
- Build the frontend with `VITE_API_BASE_URL` set to that API.
- The production default stays E38 until the user and adviser decide.

**Push record:** `out/commit_record.txt`.

---

## 13. What genuinely requires outside action

1. **Outcomes for the sealed quarters:** PSA CPI Oct 2026–Mar 2027 and the SWS Q4 2026 and Q1 2027 rounds. These enable the only legitimate test of the 75% goal, and it accumulates with later quarters.
2. **A provincial or municipal food-insecurity outcome:** CBMS, provincial FIES, or DSWD/LGU caseloads.
3. **BSP 2026 remittances** (manual download). Provincial LFS if available.
4. **A dated archive of PAGASA dry-spell/drought assessments and ENSO outlooks,** to pre-register a forward climate input.
5. **Fish-kill event records** (BFAR) with dates, if they can be collected lawfully.
6. **Adviser decisions:**
   - the price clause of the target (gap vs headline);
   - the definition of "reliable";
   - whether N1 (no national inputs) becomes the next build;
   - whether e68 becomes the default.
