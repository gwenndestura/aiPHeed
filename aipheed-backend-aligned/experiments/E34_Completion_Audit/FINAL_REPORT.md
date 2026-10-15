# E34: completion audit of the aiPHeed master prompt, and the gaps closed

**Date:** 2026-10-15.
**Branch:** `e34-main-app-integration`, created from `e31-chapter1-completion` at `ea94b7e`. Nothing was pushed or deployed.
**Folder:** `aipheed-backend-aligned/experiments/E34_Completion_Audit/`. Working notes, including an exposure log, are in `E34_NOTES.md`; commands are in `REPRODUCE.md`.

## 0. Verdict

**The project is not complete, and it must not be reported as complete.**

| Layer | Status | One-line reason |
|---|---|---|
| **System completion** | **Done locally, not deployed** | The corrected E31 pipeline now runs inside the main app (`backend/`, `frontend/`). Every suite passes, and 16/16 live end-to-end tests pass against the real server. A public deployment needs your approval. |
| **Scientific validation** (Chapter I Obj. 2–4) | **Not achieved** | No model beats persistence or always-HIGH. No reliable lead time can be established from 10 dates with 4 LOW rows. |
| **75% accuracy** (your criterion; Chapter I has none) | **Met nominally, not evidence of skill** | The served PCF21 scores 0.88 (95% CI 0.76–0.94). Always-HIGH scores 0.92. Balanced accuracy is 0.71. |
| **Prospective validation** | **Pending (external, time)** | The 2026-Q4/2027-Q1 forecasts are frozen (sha `37e0d66b…`, verified intact today). Their outcomes are released from January 2027. |
| **Objective 5 evaluation** | **Blocked (people and approval)** | It needs the 50 DA evaluators, deployment approval and an adviser decision on the NNS anchor. |

**Where the master prompt lives.** It is not stored in the repository, so its requirements were rebuilt from three sources:
- this brief (Steps 1–4);
- your 2026-10-14 authorizations (data to 2026-10-14; integration into `backend/` and `frontend/` on a new branch; no push or deploy without asking);
- Chapter I, quoted verbatim from `E25…/thesis_source/CHAPTER_I_EXTRACTION_E23.md`.

## 1. Chapter I objective-completion matrix

System completion and scientific validation are scored separately. A PASS for "implemented" is never a PASS for "validated".

| Objective (Chapter I 1.5.2, abridged) | Implemented and verified (system) | Scientifically achieved | Evidence |
|---|---|---|---|
| **General:** develop, validate and deploy aiPHeed | **PARTIAL.** Developed and integrated, but not publicly deployed | **FAIL.** Not validated | §5, §7 |
| **1.** Two-tier NLP (XLM-R zero-shot + BERTopic) → bias-corrected FSSI and latent patterns per province-quarter | **PASS.** The FSSI-v2 panel (120 rows) and the 140 admitted articles reproduce exactly from the raw store (E34 audit C5). Topics are descriptive. | **PARTIAL.** Only 7 of 120 province-quarters have sufficient evidence (titles only). Relevance labels were made by Claude, so researcher re-review is pending. | §3; `runs/e34_news_audit.json` |
| **2.** LightGBM metrics I–V, walk-forward, furthest reliable horizon | **PASS.** All metrics by lead, walk-forward and publication-aware; reproduces byte-identically (E32 rerun today) | **FAIL / BLOCKED.** No lead is reliable. The horizon cannot be determined: 46 HIGH / 4 LOW at lead 1, and detecting a 0.02 Brier gain over persistence needs about 62–64 dates | §4 |
| **3.** LGU rankings from *validated* province forecasts, weighted by PSA poverty and density | **PASS** (mechanics). 142/142 rankings; API, map, PDF and record agree (live E2E) | **FAIL** on "validated": the province forecasts are unvalidated. Inputs are **BLOCKED**: 126/142 LGUs use a province-mean poverty substitute, and density uses the **2020** census (pre-2021, conflicting with the study-window rule) | §6 |
| **4.** Comparison with four baselines | **PASS.** Identical rows and metrics; all arms in one run | **Done; the result is negative.** No arm differs from always-HIGH or persistence (McNemar p ≥ .25; no paired Brier test significant) | §4 |
| **5.** Public dashboard with maps and alerts; ISO/IEC 25010 with DA evaluators; NNS face validity | **PARTIAL.** The dashboard and alert workflow work locally on the integrated app, and E34 fixed three consistency defects. Not public. | **BLOCKED.** No evaluator data. The NNS anchor is unresolved: the 2023 CALABARZON FIES is 19.1% (lowest region), and no single-year 2019 regional figure exists | §5, §7 |

## 2. Brief requirements: audit status

| # | Requirement | Status | Evidence (file / command / result) |
|---|---|---|---|
| R1 | News completeness 2021–2026-10-14 | **PASS** relative to the source; **BLOCKED** absolutely | Ledger: 1,518/1,540 month windows COMPLETE; the 22 OPEN are October 2026, open by design. 0 cap hits; 5 HTTP 404s all retried to complete. No second source is reachable: GDELT rate-limits this host on every request, and Google News robots.txt disallows `/rss` for Claude. |
| R2 | Dates, geography, dedup, cutoffs | **PASS**, with 2 disclosures | Dates: 0 recomputation mismatches, 0 outside 2021-01-01..2026-10-14. Duplicates: 0 duplicate keys or links; 0 syndicated copies among admitted articles. Geocoder rerun: 0 mismatches. Cutoffs: both record windows recomputed identically, 0 articles after the cutoff. Disclosures in §3. |
| R3 | Does E31's pipeline give better features? | **PASS** (answered: only modestly) | E31 §6 and E32 §2, re-verified: FSSI-v2 lifts the news-only arms (NLP-LGBM Brier 0.273 → 0.239), still far behind persistence. The news count may carry a time trend (§3). |
| R4 | Train a genuinely new model if development is incomplete | **PASS** (E32; no further model in E34) | E32-PCFN, LR, LGBM and ENS were genuinely refitted per origin under a protocol frozen before fitting. E34 reproduced them byte-identically. Why no further model: §4.4. |
| R5 | Compare with PCF21, P45, persistence and baselines on identical periods | **PASS** | `runs/e34_model_audit.json` (lead 1, 10 dates, 50 rows; P45 on 45 common rows) |
| R6 | No leakage, no repeated test tuning, no unsupported generalization | **PASS**, with a caveat | Publication-aware features; scramble-the-future test (E32 16/16). Every development date had been seen before E32, so nested selection (§4.3) is reported. No result is called "unseen" except 2026-Q3. |
| R7 | Forecasts, LGU rankings, explanations, alerts, records, PDFs, APIs, frontend consistent | **PASS after E34 fixes**; 1 item for your decision | 16/16 live E2E on both backends. Fixed: D1 timeline gaps, D2 forecast flag, D3 alert badge (§5). Open: "High risk" display wording (§8). |
| R8 | Full test suites and E2E against the real app | **PASS** | Main backend 150 passed / 18 listed as superseded. E31 suite 138 passed on each backend, plus 16 live (separately 16/16 each). E32 16/16. Dashboard 43/43; build OK. |
| R9 | 75% accuracy with the correct metric and valid protocol | **PARTIAL** (nominal pass, no skill) | §4.2 |
| R10 | Backtest vs prospective kept separate | **PASS** | §4.1 labels each source. Prospective file sha `37e0d66b…` verified. |
| R11 | Integrate into `backend/` and `frontend/` on a new branch | **PASS** (new in E34) | §5 |
| R12 | No push or public deploy without asking | **PASS** | Nothing pushed. The public deploy is **BLOCKED pending your approval**. |

## 3. Historical news-coverage audit (independent re-derivation)

`runner/e34_news_audit.py` recomputes everything from the raw JSONL ledger. It imports only the rule definitions under audit (query plan, R1.1, geocoder). Output: `runs/e34_news_audit.json`.

**Collection (C1)**
- 1,545 requests: 1,435 OK, 105 EMPTY, 5 FAILED (HTTP 404, retried).
- 0 requests at the 100-item cap, so no window was truncated.
- 10,309 items were refused as non-credible sources; 32 were refused as published after the limit (hash only).

**Dates (C2)**
- 8,320 articles, all `publisher_pubdate`.
- The UTC → Manila conversion, `ph_date` and quarter recompute with 0 mismatches.
- Range: 2021-01-01 to 2026-10-14.
- 232 items (2.8%) carry a publisher date outside the window Google was asked for. They are filed by their own date, which is correct, but it shows Google's date filter is approximate.

**Duplicates (C3)**
- article_key recomputed with 0 mismatches; 0 duplicate keys; 0 duplicate links.
- Across the whole corpus:
  - 7 outlet+title pairs reappear on another date (2 within 3 days);
  - 4 cross-outlet identical titles within 3 days;
  - 2 near-duplicates (Jaccard ≥ 0.9).
- None of these is in the 140 admitted articles, so the FSSI dedup dropped 0.

**Geography (C4)**
- Geocoder rerun: 0 mismatches over 2,820 attributed titles.
- Risky patterns among attributed titles: 86 "Laguna de Bay/Laguna Lake" → Laguna; 8 "Jose Rizal/Rizal Park"; 8 "President/Manuel Quezon"; 7 "Quezon City"; 5 "Rizal Avenue".
- In the FSSI set, only 6 of 140 admitted articles are Laguna de Bay stories attributed to Laguna (2024-Q1 ×3, 2026-Q3 ×3).
  - The lake also borders Rizal, so this is **disclosed, not changed**: changing it would alter FSSI-v2 and the E32 frozen inputs.
- No person or street namesake reached the FSSI.

**Relevance and FSSI (C5)**
- 140 admitted. Panel counts are identical in all 120 rows, and evidence statuses match exactly (7 sufficient / 46 limited / 67 none).
- The admitted-key hash equals the record's (`eff85b82…`).

**Cutoffs (C6)**
- 2026-Q4 nowcast and 2027-Q1 forecast windows recompute exactly.
- 3 admitted articles per window; 0 after the cutoff; 0 before the window.
- A forecast never uses target-quarter news.

**Completeness limitation: coverage decays with age.**
- Retrieved volume per year: 594 (2021), 919, 1,119, 1,596, 2,015 (2025), and 2,077 for 2026 up to Oct 14.
- 2025/2021 = 3.4×, while the query plan is identical every month.
- So the historical record is thinner the older it is (index decay). Any news count carries a time trend, and older FSSI values rest on fewer articles.
- An absolute completeness estimate needs a second legitimate source. **BLOCKED:**
  - GDELT DOC returns "Please limit requests" or 429 from this host, and covers only a recent window;
  - licensed archives or lead text are external decisions (E29 N-TEXT).

## 4. Models: artifacts, evaluation and the 75% requirement

### 4.1 Artifacts and configuration

| Model | Artifact | Configuration | Status |
|---|---|---|---|
| PCF21 (served) | `backend/app/quarterly/pcf_engine.py` (sha `c947b27a…`) | `S1 = H + 2D` above the trailing-median τ; regional-hunger nowcast plus a provincial D model | Served, EXPERIMENTAL |
| E32-PCFN (new, E32) | `E32_New_Model/models/E32-PCFN_O2026-10-01.json` | PCF + news + rice CPI; protocol `8bea43d2`, frozen before fitting (git `4e0531f`) | Not served (failed A1/A2) |
| E32-LR / LGBM / ENS | `models/E32-LR_*.joblib` (sklearn 1.8.0), `E32-LGBM_*.txt` (lightgbm 4.6.0) | Same protocol | Frozen prospectively |
| P45 | E25 `PROPOSED_lgbm_combined` | 45-candidate LightGBM | Researcher's primary candidate; not served |

**Reproducibility.** `runner/e32_evaluate.py` was rerun today on the rebuilt environment, and `predictions.csv` is byte-identical to the frozen run (`runs/e32_repro_20261014T234245Z/`).

### 4.2 Results (development walk-forward, lead 1, 2023-Q4..2026-Q3, 10 dates, 50 rows: 46 HIGH / 4 LOW)

| Arm | Accuracy (Wilson 95%) | p(acc > .75) | Balanced acc. | Brier |
|---|---|---|---|---|
| Always-HIGH | 0.92 (0.81–0.97) | .002 | 0.50 | **0.080** |
| E32-ENS | 0.92 (0.81–0.97) | .002 | 0.84 | 0.093 |
| **PCF21 (served)** | **0.88 (0.76–0.94)** | .019 | 0.71 | 0.095 |
| Persistence, probabilistic (B1p) | 0.90 (0.79–0.96) | .007 | 0.83 | 0.096 |
| Persistence (B1) | 0.90 (0.79–0.96) | .007 | 0.83 | 0.100 |
| E32-PCFN (selected in E32) | 0.86 (0.74–0.93) | .045 | 0.70 | 0.101 |
| E32-LR | 0.88 (0.76–0.94) | .019 | 0.82 | 0.102 |
| E32-LGBM | 0.86 (0.74–0.93) | .045 | 0.70 | 0.132 |
| P45 (45 rows) | 0.82 (0.69–0.91) | .17 | 0.68 | 0.140 |
| Climatology | 0.60 | .99 | 0.55 | 0.221 |

- **McNemar** (correctness, same rows): no model differs from always-HIGH or from persistence (all p ≥ .25).
- **Unseen quarter 2026-Q3** (E31, frozen before the outcome): PCF21 5/5 correct, Brier 0.097; P45 3/5. These five rows share one regional hunger value, so they are one observation.

**The 75% requirement, judged properly**

| Test | Result |
|---|---|
| Documented metric | Chapter I Obj. 2-I names *accuracy*. Chapter I sets no threshold; 75% is your criterion. |
| Valid protocol? | Yes: walk-forward, publication-aware, frozen before fitting. But all 10 dates had been examined in earlier experiments, so they are **development** evidence, not unseen. |
| Served PCF21 | 0.88, with the 95% CI lower bound at 0.76: **above 75%** |
| Any skill? | **No.** A constant always-HIGH forecast scores 0.92. On the 4 LOW rows, PCF21 catches 2 (balanced accuracy 0.71 < 0.75). |
| **Verdict** | **Met nominally; not evidence of forecasting skill.** It cannot be written as "the model achieved over 75% accuracy" without saying that a constant forecast does better. |

### 4.3 Nested selection: the honest score of "fit several, keep the best"

At each date, the candidate with the best Brier score on strictly earlier dates was used.

| Pool | Brier | Comment |
|---|---|---|
| E32 candidates only | 0.111 | Worse than persistence (0.100); ENS chosen from 2024-Q2 |
| Candidates + PCF21 + persistence + always-HIGH | 0.109 | Picks **always-HIGH** from 2024-Q3 onward |

### 4.4 Why no further model was trained in E34

The brief asks for a new model only if development is incomplete, and for continued investigation if the criterion fails. Four findings settle it:

1. **E32 already completed model development.** It is genuine, refitted per origin, and reproduced byte-identically today.
2. **The only defensible test is unseen data, and every development date has already been looked at.** Any model selected now on those 10 dates is test-set tuning, and nested selection shows that procedure loses to persistence.
3. **Statistical power rules out a development verdict.** With per-date SD 0.064, detecting a 0.02 Brier gain over persistence at 80% power needs about 62–64 dates, which is about 16 years of quarters. Even a 0.05 gain needs about 10–11.
4. **The ceiling is the target, not the model** (E32 diagnosis, re-verified):
   - 70% of S1 variance is regional hunger, one value shared by all five provinces;
   - knowing next quarter's hunger gives 0.96 accuracy;
   - the 2025-Q2/Q3 SWS rounds are supplementary, so those quarters have no label.

**Valid route to improvement:** score the frozen prospective forecasts (2026-Q4 from January 2027, 2027-Q1 from April 2027) with `E32_New_Model/runner/e32_score_prospective.py`, and any change of target must come from your adviser.

## 5. Integration and application verification

**Promotion into the main app** (`runner/e34_promote_backend.py`, `runner/e34_promote_frontend.py`; lists in `runs/e34_*_promotion.json`)

- **Backend**
  - 34 files overwritten and 122 new; nothing deleted.
  - 8 main-only modules kept: E20 forecaster, thesis predictor/explainer, plain-language report helpers.
  - The main risk-band rule from `1658d31` (band on the displayed 2-decimal score) was restored.
  - Data is copied into **new** folders only; `backend/data/processed`, `thesis`, `e20–e22` and `aipheed.db` were not touched.
- **Frontend:** a per-file three-way merge (base `1658d31`, the commit `dashboard_dev` was copied from). 8 files taken from E31, 25 new, and 4 kept from main (lakes layer, component-city names, glossary, About title). 0 conflicts.

**Defects found and fixed**

| ID | Defect | Fix | Test |
|---|---|---|---|
| D0 | `create_admin.py` crashed on its own domain check (it read the renamed setting `ADMIN_EMAIL_DOMAIN`) | Uses `admin_email_domains` | live E2E admin tests |
| D1 | `/quarters` silently skipped 2025-Q2/Q3 (and 2026-Q4 in the forecast view), so the slider jumped without explanation. The schema had lost `reason`. | Every quarter is listed; gaps are `unavailable` with a data-derived reason (supplementary SWS rounds; "shown in the nowcast view") | `test_e34_timeline_and_forecast_flag.py`; main `test_quarters_timeline_has_no_gaps…` |
| D2 | `isForecast` was hard-coded false on `/forecast` and `/forecast/timeseries`, so the 2027-Q1 forecast was drawn as observed | Follows the row's mode, as `/config.forecastQuarters` does | same file |
| D3 | The "Active alert" badge used score ≥ 0.60 on the client and in `/forecast`, bypassing the E31 workflow (staged → administrator-confirmed). Every province showed an alert with an empty alert table. | `alert` is true only for a **confirmed** alert of that area and quarter; one regional alert is never copied to the provinces. Glossary corrected. | same file (staged, confirmed, regional and province cases); screenshot |
| D4 | Main backend tests imported text helpers that the promotion removed | `_ascii`, `_join_series` and `compose_formal_interpretation` were ported unchanged | main suite |
| D5 | 26 main tests asserted the superseded serving path | 8 now pass: 7 were adapted to E31 semantics (review statuses per Fig. 3.6.3, news alignment, label wording, timeline), and 1 passes because of D2. **18 are listed with reasons** in `backend/tests/conftest.py` (E20 contract, legacy food-availability model, plain report on the E20 path); `AIPHEED_RUN_SUPERSEDED=1` runs them | main suite |

**Test results (final runs; logs in `runs/final_*.log`, `runs/e2e_*.log`)**

| Suite | backend_dev | Promoted `backend/` |
|---|---|---|
| E31 suite (incl. 6 new E34 tests) | 138 passed, 16 live skipped | 138 passed, 16 live skipped |
| Live E2E against a running server | **16/16** | **16/16** |
| Main backend suite | n/a | 150 passed; 18 superseded (listed); with `AIPHEED_RUN_SUPERSEDED` those 18 fail as expected |
| E32 model tests | 16/16 | n/a |
| Dashboard vitest / build | 43/43, build OK | 43/43, build OK. 11 TypeScript errors, the same 11 as before the promotion (mock data and the E29 brief type); none new |

**Visual check.** Headless Edge loaded the promoted frontend against the promoted backend (`runs/screenshots/`). `/dashboard`, `/da-brief` and `/news` render from the E31 record, and every API call returned 200. After D3, no "Active alert" badge appears without a confirmed alert.

**Deployment.** Local deployment works (alembic, admin, alert staging, uvicorn). The documented fallback `AIPHEED_DATA_LAYER=legacy` **no longer works in `backend/`**: its artefacts in `data/processed` were destroyed in the 2026-10-15 git-clean incident. A public deployment is **BLOCKED pending your approval**; the Vercel site still runs the old prototype.

## 6. Remaining failures and their root causes

| Item | Root cause | Who can resolve it |
|---|---|---|
| No validated model or lead | The target is about two-thirds regional hunger, the classes are 46/4, there are 10 dates, and the next hunger round is unknown at the origin | Time (prospective quarters) and the adviser (target) |
| 75% shows no skill | 92% of labels are HIGH | Adviser: wording, metric (balanced accuracy / Brier), target |
| LGU poverty substitutes (126/142) | The 2021 municipal SAE is on psa.gov.ph behind a Cloudflare challenge, and the local workbook mixes 2018 values (study-window rule) | You: download the 2021-only municipal table |
| Density from the 2020 census (pre-2021) | 2024 POPCEN Table B (Proclamation 973, 2025) is behind the same challenge | You: download POPCEN 2024 Table B (CALABARZON) |
| FSSI evidence is thin (7/120) | Titles only; robots.txt bars lead text | Licensed source or text decision (N-TEXT) |
| News coverage decays with age | Search-index retention | Second licensed source; disclose |
| Relevance labels need re-review | Annotated by Claude | You |
| NNS face validity | Objective 5 names NNS 2019, which is pre-window and has no single-year regional figure. The 2023 value (19.1%, lowest region) is an absolute prevalence, while the label is relative to its own trailing median, so "all HIGH" does not contradict it but cannot be checked against it | Adviser (anchor R4) |
| Objective 5 evaluation | 50 DA evaluators; ISO 25010 instrument | You and DA Region IV-A |
| Public deployment | Not authorized | You |
| Legacy data layer and lost corpora | 2026-10-15 git-clean incident | Re-collection if the legacy path is ever needed |

## 7. Environment repairs (side effects of the 2026-10-15 incident)

- `backend/venv` had no `pyvenv.cfg` and 29 native remnants. It was rebuilt from the pinned `requirements.txt` (Python 3.13.2).
- `psutil` was reinstalled: it is not in the freeze, and a remnant directory shadowed it.
- `frontend/node_modules` (3 entries; E31 `dashboard_dev/node_modules` is a junction to it) was restored with `npm ci`.
- No data was restored. Copies of `corpus_geocoded.parquet` exist, but none matches the recorded hash.

## 8. Decisions needed from you

1. **Approve a public deployment** of branch `e34-main-app-integration` (or not).
2. **Display wording.** The API sends no HIGH/LOW label (`riskLabel: null`, E27 rule). The dashboard still prints "High risk" from the 0.50 display band (your `1658d31` design), next to the legend "Estimate (unvalidated)". Keep, or change to e.g. "≥ 50% (unvalidated)".
3. **Download** the PSA 2021 municipal poverty table and the 2024 POPCEN Table B, so Objective 3 uses in-window inputs.
4. **Adviser:**
   - target design;
   - the 75% wording (and a co-metric such as balanced accuracy or Brier);
   - the NNS anchor.
5. **Laguna de Bay attribution** (6 FSSI articles): keep Laguna only, or share with Rizal. A change would need a new frozen FSSI version.

---

## Addendum (E36, 2026-10-15): verified updates to this audit and the completion matrix

Source: `../E36_LightGBM_One_Quarter_Ahead/FINAL_REPORT.md` (sections 6, 7, 9, 10). The original matrix above is kept for traceability; these rows supersede it.

| Objective | Implemented and verified (system) | Scientifically achieved |
|---|---|---|
| 2. LightGBM metrics I-V | **PASS** for lead 1 with the served LightGBM (aiPHeed-E36-LGBM): 53/65 = 0.815 (date-bootstrap 95% CI 0.738-0.892), all metrics, leakage tests | **FAIL / not demonstrated**: equals always-HIGH, below persistence 0.877; no lead shown reliable |
| 3. LGU rankings | **PASS**: inputs now in-window and verified against the supplied workbooks: **141/142 LGUs use their own PSA 2021 municipal SAE**; Lucena City (HUC, absent from the no-HUC table) uses a substitute labelled unverified; **142/142 use 2024 POPCEN**. Record, API (`/lgu-ranking`, `/provinces/{id}/municipalities`), map and PDF agree (tests) | **PARTIAL**: province forecasts unvalidated; Lucena value unverified |
| 4. Baselines | **PASS**: all six SOP 3 baselines on identical rows | Negative: none beaten significantly (Holm p >= .50) |
| 5. Dashboard | **PARTIAL**: E35 display defects D1, D3-D7 fixed and tested; not deployed | **BLOCKED** (no DA evaluation) |

Section 6 rows superseded: "LGU poverty substitutes (126/142)" and "Density from the 2020 census" are **resolved** (data supplied by the researcher on 2026-10-15 and integrated on branch `e36-lgbm-one-quarter-ahead`). The old 16 "LGU-specific" values were wrong (e.g. Imus 2.8 vs 9.29) and are replaced. **Still not complete**: no validated model, prospective outcomes pending, Objective 5 evaluation not done.
