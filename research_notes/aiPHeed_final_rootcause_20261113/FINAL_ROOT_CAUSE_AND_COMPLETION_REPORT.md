# aiPHeed FINAL (RATE + MIND): Root-Cause Resolution and Project Completion

Date: 2026-11-13. Basis: the 2026-11-12 Seven-Rule Acceptance Report (`aiPHeed_final_cw_20261112/FINAL_SEVEN_RULE_REPORT.md`), read in full, and its locked forecasts.

**What was done in this round**
- No model was refitted.
- No configuration, threshold, class weight or feature was scored on the 72 forward province-rounds.
- No synthetic data was used.
- The seven rules, E196, H_cw, FINAL and every seal are unchanged.

The analysis reads the locked forecasts (`cw_rows_all_leads.csv`) and the public survey tables only. Scripts are in `scripts/`; numbers are in `evidence/RC_*`.

---

## 1. Why FINAL does not pass (plain language)

FINAL is right more often than H_cw (86 % against 82 % at one quarter ahead). Its probabilities are also better calibrated. But it fails on the same five province-rounds where H_cw is weak, and on those it is more sure of itself:

- **Lanao del Norte and Misamis Oriental, 2019.** Both sat just above the HIGH line (50 % of households moderately or severely food insecure) in 2015. Nationally, food insecurity fell between 2015 and 2019, and FINAL assumed these two provinces would fall with the country. They did not: Lanao del Norte rose from 55.6 % to 59.0 %, and Misamis Oriental stayed at 54.8 %.
- **Masbate, Occidental Mindoro and Agusan del Sur, 2021.** These provinces were far above the line in 2015 (65 to 68 %). Between 2015 and 2021, most provinces like them fell steeply (North Cotabato −34 points, Sarangani −25, Negros Oriental −20). These three fell only 7 to 10 points, so they stayed HIGH. Every model predicted the steep fall.

**Effect on the two failed rules.** Rule 4 (HIGH recall) needs one more of these five provinces found at Lead 1. Rule 3 (Brier interval below zero) is lost almost entirely on these same 15 forecasts (five provinces, three leads each).

Nothing in the current inputs tells the model which provinces did not follow the national trend. That is missing information, not a tuning problem.

## 2. Technical root cause of Rules 3 and 4

### Rule 4: Lead 1 HIGH recall 0.80 (needs 0.84)

| Lead | HIGH rows | Found by FINAL | Found by H_cw | Needed | FINAL misses (probability) |
|---|---|---|---|---|---|
| 1 | 25 | 20 | 22 | **21** | Agusan del Sur 0.41, Lanao del Norte 0.32, Masbate 0.15, Misamis Oriental 0.38, Occidental Mindoro 0.20 |
| 2 | 25 | 20 | 21 | 20 | same five |
| 3 | 25 | 19 | 20 | 19 | Aklan 0.47, Palawan 0.49, Lanao del Norte, Masbate, Misamis Oriental, Occidental Mindoro |

Rule 4 fails by **one province** at Lead 1 (`RC4_high_recall_by_lead.csv`).

### Rule 3: pooled paired Brier −0.0006 [−0.0152, +0.0156]

The result was reproduced exactly with the protocol's resampling: province-round clusters, 6,000 draws, seed 7. Contributions to the pooled difference against H_cw (`RC3_decomposition_by_group.csv`):

| Rows | n | Contribution | Reading |
|---|---|---|---|
| Both models right | 171 | **−0.0123** | FINAL is sharper and closer to the truth |
| Both models wrong | 28 | **+0.0120** | FINAL is sharper and further from the truth (mean distance from 0.5: FINAL 0.225, H_cw 0.161) |
| Only FINAL wrong | 6 | +0.0043 | Lanao del Norte, Misamis Oriental |
| Only H_cw wrong | 11 | −0.0046 | the five removed false alarms |

To pass at 72 clusters, the pooled difference must reach about **−0.0155**.

The five provinces above are FINAL's five largest losses against H_cw: Occidental Mindoro +0.80, Lanao del Norte +0.61, Misamis Oriental +0.55, Masbate +0.50, Agusan del Sur +0.27.

**Where the failure sits.** I tested what-ifs on the locked forecasts (`RC3_whatif_bounds.json`). These locate the failure; they are **not results**.

| What-if (nothing else changed) | Pooled difference [95 % interval] | Rule 3 |
|---|---|---|
| FINAL as scored | −0.0006 [−0.0152, +0.0156] | fail |
| The five provinces at H_cw's probability | −0.0132 [−0.0231, −0.0036] | pass |
| The five provinces called HIGH at 0.60 | −0.0256 [−0.0418, −0.0113] | pass |

Rules 3 and 4 therefore have **one common cause**: the same five province-rounds. Of the Brier loss on those five, 57 % comes from the three 2021 provinces. This corrects the 12 November bound, which showed that recovering only Lanao del Norte and Misamis Oriental leaves Rule 3 failing: the 2021 provinces are needed for Rule 3.

### Province by province (survey facts: `RC_five_provinces.csv`, `RC_2019_near_cutoff_anchor_peers.csv`, `RC_2021_high_anchor_peers.csv`)

| Province (round) | 2013 | 2015 (anchor ± SE) | Outcome | Change | FINAL / H_cw / latest survey | What explains it | Why the inputs miss it |
|---|---|---|---|---|---|---|---|
| Lanao del Norte (2019) | 64.2 | 55.6 ± 4.4 | 59.0 | +3.4 | 0.32 / 0.52 / 0.69 | **Marawi displacement, 2017**: about 139,700 displaced persons hosted (DSWD / Protection Cluster, 30 June 2017). That is very large against the province's population. Published before the April 2019 origin. | No input observes displacement. Its change inputs are all within ±1.2 SD of the round. RATE multiplies the national decline by 16 quarters. |
| Misamis Oriental (2019) | 63.1 | 54.1 ± 5.7 | 54.8 | +0.7 | 0.38 / 0.53 / 0.64 | **Not established.** About 18,000 displaced hosted, roughly 1–2 % of residents: too small to be the main cause. The outcome is only about 2 SE above the line (q = 0.97), so part of this is survey noise near the cut-off. | Only provincial adverse news stands out (+2.8 SD), and that input carries no signal on the training transition. |
| Masbate (2021) | 63.2 | 68.3 ± 5.9 | 59.4 | −8.9 | 0.15 / 0.28 / 0.93 | **Not established.** | Poverty inputs do not separate it: North Cotabato and Sarangani are poorer on the model's poverty input, yet fell 25–34 points. |
| Occidental Mindoro (2021) | 65.2 | 66.7 ± 5.9 | 56.3 | −10.4 | 0.20 / 0.35 / 0.91 | **Not established.** Rainfall since the anchor is +2.6 SD, already an input. | Same as Masbate. |
| Agusan del Sur (2021) | 70.3 | 64.7 ± 4.4 | 57.9 | −6.8 | 0.41 / 0.49 / 0.87 | **Not established.** Possible conflict-related displacement (Caraga) is a hypothesis only. | Area news +1.3 SD, palay +1.5 SD; neither separates it. |

**Comparison provinces near the cut-off, 2019** (anchors 51–58 %):

- Mindanao provinces stayed level or rose: Lanao del Norte +3.4, Misamis Oriental +0.7, Zamboanga Sibugay +4.9, Agusan del Norte +13.5, South Cotabato +0.5.
- Luzon provinces fell: Ilocos Norte −24.6, Pangasinan −14.8.
- The 2017–2019 period was the Marawi siege and martial law across Mindanao. This regional pattern is visible only in the test outcomes, so it may **not** be used to build or select a feature.

**Comparison provinces with a high anchor, 2021** (anchor ≥ 60 %):

- Changes ranged from −6.8 to −33.7 points.
- The latest survey alone was right for the three missed provinces and wrong for the four that fell (North Cotabato, Sarangani, both Negros provinces).
- The 2013→2015 history separates Negros only: its 2015 value was a one-round spike above 2013 that later reverted. It does not separate the SOCCSKSARGEN pair.

**Mechanism.** The 2021 test gap is 24 quarters, longer than any training gap. RATE scales the learned per-quarter decline by the gap: the mean 2021 error went from −0.09 to −0.26 on the logit scale (12 November evidence). H_cw misses the same three provinces, so mechanism alone does not explain them.

**Measurement.** 38 of 72 anchors lie within 1.96 SE of the 50 % line. FINAL's error rate is 0.13 near the line and 0.15 away from it, so survey noise does not concentrate the errors.

**Conclusion.** Different explanations apply to different provinces:

- Lanao del Norte: a documented displacement shock no input carries.
- Misamis Oriental: a borderline outcome; no shock established.
- The 2021 three: smaller-than-typical decline over 24 quarters (COVID period included), unexplained by any available input.

## 3. Genuine additional data sources

Status: **V** = verified this round (13 November), **V12** = verified 12 November, **NV** = not verified (page refused or not opened).

| Source | What it gives | Province field | Period | Publication date usable for as-of | Format | Status |
|---|---|---|---|---|---|---|
| DSWD DROMIC situation reports | Per incident: affected and displaced families and persons, inside and outside evacuation centres, annex by region, province and municipality | Yes | Site archive 2014–2016 (Google Drive folders), per-incident pages 2016–2026; **no 2013 entry** | Yes ("as of" date in each report title) | PDF reports, one series per incident | V (archive years); province annex V on 2024 reports via search |
| Protection Cluster IDP Protection Assessment (UNHCR + DSWD), Marawi | Displaced families and persons by host province and municipality | Yes | 2017–2018 (issues 1–7) | Yes | PDF | V12 (issue 1 table); issues 4–7 located V |
| Mindanao Displacement Dashboard (Protection Cluster) | Monthly displacement by incident, provinces named | Narrative | About April 2014 to at least December 2021 (2019 and 2021 issues mirrored on ecoi.net) | Yes (monthly issue) | PDF narrative; Mindanao only | V12 / V (mirrors); dashboard page itself refused (403) |
| UCDP Georeferenced Event Dataset | Geocoded conflict events with deaths; admin-1 field | Yes (admin-1, coordinates) | 1989–2025 (version 26.1) | Annual versions: a forecast may use only the version released before its origin | CSV / API | V (current version and coverage); admin fields V from API docs; release date of version 19.1 NV |
| IDMC event data (HDX) | Displacement events | Unclear | HDX file covers only the last 180 days; historical stocks 2008–2021 are national | Partly | CSV | Listing seen; page refused (403); **not usable as a provincial history** as listed |
| IOM DTM Philippines (HDX) | Event-specific displacement tracking (e.g. Yolanda, Marawi) | Probably | Listed 2013-11-30 to 2021-04-30 | Unknown | CSV / XLSX | NV (403) |
| ACLED | Conflict events | Yes | Philippines from 2016 | Yes | API | Known coverage starts 2016: **no variation on the 2013→2015 training transition** |
| PSA quarterly Labour Force Survey, regional | Unemployment and underemployment | Region only | Quarterly | Yes | OpenStat | Not on disk; region-level only |
| PSA provincial poverty (2015, 2018, 2021) | Poverty incidence | Yes | Three-yearly | 2018 provincial release date NV; 2021 released 2022 (after the 2021 origin) | OpenStat | Partly in the model already (`p_poverty`); 2021 not usable |
| VIIRS night lights (monthly) | Economic-activity proxy | Any area | 2012-04 onward | Short lag | Raster | V12; download and zonal statistics needed; unproven |
| FNRI provincial HFIAS rounds | The outcome itself | Yes | 2013, 2015, 2018, 2019, 2021 | n/a | PDF / Heat Map | ENNS 2022: owner states it is not obtainable. The 2023 NNS uses FIES, not HFIAS (verified 11-04). |

## 4. Feature feasibility assessment

| Candidate | Defensible link to food insecurity | Available before the origin | Varies in training rows | Would address | Feasibility | Verdict |
|---|---|---|---|---|---|---|
| **Conflict displacement since the anchor survey** (peak displaced persons per 1,000 residents; DROMIC + Protection Cluster; unreported province-quarters kept missing, never 0) | Strong: conflict displacement is a recognised driver of acute food insecurity | Yes (report "as of" dates) | Partly: 2014–2015 incidents (Maguindanao) give a few nonzero provinces; 2013 incidents (Zamboanga siege, Yolanda) are **outside the DROMIC archive**, so the 2013→2015 transition is incomplete | Lanao del Norte; possibly Agusan del Sur; **not** Masbate or Occidental Mindoro | Several days of manual PDF table extraction. A sparse input (few nonzero provinces), so LightGBM may barely use it | **Feasible to compile; cannot be validated on current rows** (it was identified from a test province) |
| Disaster displacement (same source) | Weaker: mostly short-lived. Typhoon-prone LOW provinces (Sorsogon, Southern Leyte) improved anyway | Yes | Yes | Risk of **more** false alarms | As above | Keep separate from conflict; do not add without prospective testing |
| UCDP conflict-event intensity since the anchor | Moderate (conflict, not displacement) | Yes, by release version | Yes, all years | Lanao del Norte (2017 Marawi events in Lanao del Sur, next door) | Easy (one CSV) | Best low-effort complement to displacement |
| Regional quarterly LFS change | Moderate | Yes | Yes (regional) | Cannot separate provinces inside a region (Misamis Occidental improved, Oriental did not) | Easy | Low value for these failures |
| VIIRS change since the anchor | Indirect | Yes | Yes | Unknown | Moderate | Exploratory only |
| A long-gap damping of RATE (mechanism, not data) | n/a | n/a | n/a | The 2021 provinces | Easy | **Cannot be chosen now**: any setting would be tuned to the 2021 rows. A pre-registration candidate for the next round only |

The five trigger groups on the dashboard stay as they are. Displacement would be a model input inside the existing structure, or a sixth trigger. A sixth trigger would need your approval, because the thesis defines five.

## 5. Validation-integrity plan

**Three separate evidence classes, always reported apart:**

1. **Locked historical results (frozen).**
   - What: the 72 province-rounds × 3 leads (ENNS 2018, 2019, 2021).
   - About 38 FINAL configurations have already been scored on them. From now on they are reported only as they stand: FINAL 5 of 7, FINAL-CW 4 of 7.
   - **No new feature, threshold, weighting or configuration is scored on them.** Any later score on these rows must be labelled "retrospective, reused rows, not evidence".
   - The what-ifs in section 2 are locating diagnostics, not results.
2. **Development (allowed).**
   - The 2013→2015 training transition (78 provinces, training data in every fold): checks whether a new input relates to provincial change. The news displacement signal was tested this way: right direction, p = 0.21.
   - Data compilation and audits: coverage, as-of dates, missing-not-zero.
   - The held-out FNRI 2015 round was already used once to choose FINAL. Further use is a sanity check only, declared as reuse.
   - No 2018, 2019 or 2021 outcome may be read in development.
3. **Independent future validation.**
   - A provincial HFIAS round that no forecast has seen.
   - Protocol and code hashed **before** the outcomes are seen.
   - Forecasts sealed before release: existing seals FINAL / H_cw / IMPUTE / RATE `4ad9267f`, E196 `d12b6a8c`. A future FINAL + displacement candidate gets its own seal.
   - The seven rules are applied to that round alone, with the pass rule written down beforehand.

**What a new round must contain** (power from FINAL's observed per-province Brier spread, `RC_summary.json`):

| Provinces in the new round | Rule 3 interval half-width |
|---|---|
| 20 | 0.029 |
| 25 | 0.027 |
| 40 | 0.020 |
| 50 | 0.018 |
| 72 | 0.015 |

- **Rule 3** passes only if the true improvement is larger than the half-width. FINAL's forward estimate is −0.0006, so it would not pass on any feasible round. Its held-out estimate is −0.042, which would pass with about 25 provinces. Which of the two is true is exactly what the round would settle.
- **Rule 4.** With 10 HIGH provinces, one miss moves recall by 0.10, so the round must contain at most one missed HIGH province out of 10 (0.90 ≥ 0.84). With 25 HIGH provinces, at most 4 may be missed.
- **Instrument risk.** FNRI's 2023 round used FIES. If no further provincial HFIAS round is fielded, the HFIAS-based rules cannot be re-tested at all. A FIES-to-HFIAS bridge (the ENNS 2021 paired subgroups) would then be your decision.

## 6. Can 7/7 be established now?

| Question | Answer |
|---|---|
| 1. What prevents Rule 3 | The concentrated, confident errors on five province-rounds (15 forecasts), about +2.7 Brier units, cancel FINAL's gains on the rest. At 72 clusters the pooled improvement must reach about −0.0155; it is −0.0006. |
| 2. What prevents Rule 4 | One HIGH province at Lead 1 (20 of 25 found; 21 needed). |
| 3. Missing inputs that could address them | Conflict displacement (Lanao del Norte; possibly Agusan del Sur) and conflict-event intensity. No identified genuine input explains Misamis Oriental or the 2021 Masbate / Occidental Mindoro cases. |
| 4. Experiments still allowed | Compiling displacement and UCDP data; association tests on the 2013→2015 transition; locking a FINAL + displacement protocol; sealing its forecasts. Software work. |
| 5. What needs a new survey round | Any claim that FINAL, or any FINAL variant, passes Rules 3 and 4. Any test of a displacement input. Any long-gap damping. |
| 6. Legitimate 7/7 with current evidence? | **No.** Every candidate fix was identified from the failed test provinces, so scoring it on those rows cannot validate it. No untouched provincial HFIAS round is available. Even a perfect displacement input would plausibly fix one or two of the five provinces. That could close Rule 4 (one province needed) but would probably not close Rule 3, which also needs the 2021 provinces. |

FINAL's truthful status is unchanged: better calibrated, fewer false alarms, no gain in HIGH detection, **5 of 7**. E196 remains production.

---

## 7. Application defects fixed (E196 worktree `C:\Users\admin\aipheed_e196`, branch `e196-thesis-model`, not committed)

| # | Defect | Fix |
|---|---|---|
| 1 | `/quarters` stated cut-off 2026-10-01 while the outlook stated 2026-11-01 | The dashboard's forecast target keeps the quarter clock for the target quarter. It now takes origin and cut-off from the served artifact when that artifact was issued in the current quarter; the quarter-start date is kept as `quarter_start`. One helper, `e168_system.served_issue()`, is the single source. |
| 2 | Indicator horizon said "issued 2026-10-01; Leads 1-3" for an issue cut off 2026-11-01 that serves Leads 1–4 | The horizon is built from the served issue. For the original E168 export the sentence and object are exactly as before. |
| 3 | `/config.servingModel` named only the retired FIRI v2 thesis record | Added `servingModel.mapModel`: the approved model, issue, cut-off, served leads and target quarters. The existing fields keep their contract. |
| 4 | About dialog said E168, "one to three quarters", "Leads 1 and 3 exactly at 75 %", "from 4 quarters ahead accuracy is below 75 %", next to live rows showing E196 reliable at Leads 1–4 | Text corrected in the existing elements only. No layout, colour or new element. |
| 5 | About dialog "Further horizons tested" showed an empty value under E196 | Shows "None beyond 4 quarters ahead". |
| 6 | Forecast history dialog said "E168 forecasts" | Now says E196. |
| 7 | Seven protocol locks and four "production untouched" hashes failed on Windows only: CRLF checkout of LF-hashed files | Added those folders and files to the repository's existing byte-for-byte list (`.gitattributes -text`), restored the exact stored bytes, and re-indexed. Content diff: none. The E140 `model.py` lock was recorded from CRLF bytes, so it keeps normal conversion (documented). |
| 8 | 12 tests failed on missing gitignored raw data in this worktree (IBTrACS, news archive, E144 news items, E124 store) | Copied from the other worktrees into their gitignored locations, byte-checked; created the empty E124 store folder. No tracked file changed. |
| 9 | Two-working-directory API test: local `aipheed.db` was a 0-byte, never-migrated file | `alembic upgrade head` (production does this at start-up). |
| 10 | Stale tests expecting E168 as production (name, 15 rows, 2026-10-01 cut-off, registry hash, E178 compared with "current production") | Updated to the registry-approved E196 (2026-11-11) or, for E178, pinned to the E168 issue it actually ran on (`a01aa189…`, still on disk unchanged). Every E168 historical assertion is kept. |

Also found, **not fixed (deployment items for you):**
- **Basemap.** `/basemap.pmtiles` is gitignored. The live site returns `index.html` for that path, so the map has no background tiles unless the production build sets `VITE_BASEMAP_PMTILES_URL` to another host. I could not confirm that setting from here.
- **Tests that exercise production assumptions only on Windows.** The E140 lock (CRLF-recorded) and the `firi.py` hash (CRLF-recorded) would fail on Linux CI. This was already the case before this round.

## 8. Test results

| Suite | Before | After |
|---|---|---|
| Backend (pytest, full) | 36 failed, 1,689 passed, 1 collection error | **5 failed, 1,733 passed**, 32 skipped, 0 collection errors |
| API checks over HTTP, production settings | 17 / 18 (cut-off inconsistency) | **22 / 22** (4 new checks: indicator cut-off, model identity, evaluation identity, every public route the frontend calls answers without a server error) |
| Frontend (Vitest) | 101 passed | **101 passed** (one test updated to E196) |
| Frontend type check and production build | build succeeded | **clean; build succeeds** |
| New regression tests (`test_served_issue_consistency.py`) | n/a | **4 passed** |

Remaining backend failures, all explained:
- **`test_e137::test_protocol_lock_matches_code`.** A genuine post-lock change: the 8 November monthly-refresh commit extended `app/e137/features.py` after its 3 November lock. I did not re-lock it. Re-locking is your decision.
- **`test_e144` (2 tests).** They need an E144 candidate issue (`python -m app.e144.issue`) that was never run in any worktree. Running it would add a new sealed forecast to the prospective register, which this brief excludes.
- **E119-R2 and E120 validation checks.** They require `backend/app` and `frontend/src` to have no uncommitted edits, so they fail while this round's fixes are uncommitted. Expected to pass after commit; not verified.

## 9. Files changed

E196 worktree (uncommitted):

- `.gitattributes`
- `backend/app/ml/inference/e168_system.py`: `served_issue()`, `_horizon_text()`, `indicator()`
- `backend/app/services/dashboard.py`: `forecast_target()`, `_served_issue_on_map()`, `serving_model()`
- `backend/tests/integration/test_served_issue_consistency.py` (new)
- `backend/tests/integration/test_e168_dashboard.py`
- `backend/tests/unit/test_e168_regenerate.py`
- `backend/tests/unit/test_final_audit.py`
- `backend/tests/unit/test_e178_results.py`
- `backend/tests/unit/test_e178_scenarios.py`
- `backend/tests/unit/test_e184_deploy.py`
- `frontend/src/components/AboutModal.tsx`
- `frontend/src/components/ForecastHistoryModal.tsx`
- `frontend/src/test/landing.test.tsx`
- Byte-restored, with no content change: 83 files under `backend/app/e137`–`e144` and `backend/app/hfias`, `docs/e137`–`e144`, plus `backend/app/ml/inference/firi3.py`.
- Local, gitignored only: raw data copies, `backend/aipheed.db` migrated, the empty E124 store folder.

The pre-existing user-manual changes in that worktree were not touched.

Research folder `research_notes/aiPHeed_final_rootcause_20261113/`:
- `scripts/rootcause.py`, `scripts/whatif.py`
- `app_scripts/api_checks.py`
- `evidence/RC_summary.json`, `RC3_*.csv|json`, `RC4_high_recall_by_lead.csv`, `RC_*.csv`, `api_checks.json`
- this report

Session folder: `.claude/launch.json` (two preview entries, `e196fix-api` and `e196fix-web`).

## 10. Completion and deployment readiness

| Area | Status |
|---|---|
| FINAL (RATE + MIND) | **Not accepted: 5 of 7.** Cannot reach a legitimate 7/7 with current evidence. Next step needs your approval: compile conflict displacement (DROMIC 2014+, Protection Cluster, UCDP), lock a FINAL + displacement protocol, seal it for the next provincial HFIAS round. |
| E196 (production) | Unchanged model and artifact (sha `c3d3ccd5…`). |
| Application | Cut-off, model identity and About text are consistent with the served E196 issue. API 22 / 22, frontend 101 / 101 and a clean build. Backend: see section 8. |
| Ready to deploy? | **The software fixes are ready to commit and review.** Deployment still needs: (1) your go-ahead to commit and merge `e196-thesis-model`; (2) a basemap host or an equivalent build setting; (3) a decision on the E137 re-lock. None of these touch the model. |
