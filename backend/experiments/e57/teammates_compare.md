# Teammate branch comparison: `e46-lead2-policy` vs my working tree

2026-10-17. Read-only comparison; nothing was merged, pulled, checked out, stashed, committed or pushed in either
folder.

- **Mine:** `C:\Users\User\aiPHeed-final-integration`, branch `final-aipheed-integration` at `430a347`, **including
  uncommitted and untracked changes**.
- **Theirs:** `C:\Users\User\aiPHeed-teammates`, a detached worktree of `origin/e46-lead2-policy` at `6fc1a4f`
  (Angel Melindo).

## Part 1: setup

- The branch you named, `e4-lead2-policy`, does not exist on origin. `e46-lead2-policy` does, and was used after
  your go-ahead.
- Your clone fetches only `final-aipheed-integration` (refspec unchanged). The teammate branch was fetched as a
  single ref: `git fetch origin e46-lead2-policy:refs/remotes/origin/e46-lead2-policy`.
- `git worktree add ..\aiPHeed-teammates origin/e46-lead2-policy --detach`: done.
- Your working tree before and after is identical:
  - branch `final-aipheed-integration`;
  - 46 status entries, the same line by line;
  - the uncommitted diff has the same md5 (`c9b733…`);
  - the 5 protected md5s are unchanged.
- **Add to VS Code:** File > Add Folder to Workspace > `C:\Users\User\aiPHeed-teammates`.
- **Note:** your commit `430a347` (Serve E49-C2 by default) is **not on GitHub**. `origin/final-aipheed-integration`
  is still at `bf94bb3`, so your teammate cannot see E48/E49/E53 or any later work.

## 1. History

| | Commits since merge base | Notes |
|---|---|---|
| Merge base | `bf94bb3` (2026-10-15, Angel Melindo) | "Final integration: dynamic next-quarter target, 2027-Q1 next-quarter forecast served, five triggers, live E2E, audit report" |
| Mine | **1 commit** (`430a347`) + uncommitted/untracked work | E49-C2 default (lead 1 only), then E50-E59, the E53 preview and the dashboard fixes, all uncommitted |
| Theirs | **53 commits** (2026-10-15..17) | Their E39-E51, mostly in `aipheed-backend-aligned/experiments/` (395 of the 449 changed files), plus backend serving and frontend tours |

**Name collision.** Both sides numbered their experiments from E39 upwards, independently. Their E49 (E38 vs E46
comparison), E50 (attribution defect) and E51 (target audit) are not the same as your E49 (calibration), E50
(overfitting) and E51 (percentile thresholds). They are in different folders (`aipheed-backend-aligned/experiments/`
vs `backend/experiments/`), so no file clashes, but references in reports and the manuscript will be ambiguous.

## 2. Files (backend/ and frontend/; venv, node_modules, __pycache__, *.db and files over 20 MB ignored)

Four model files over 20 MB were skipped (`backend/models/food_availability*_model.joblib`, both sides).

### Only in theirs (32)
- **Backend serving:** `app/api/v1/fpp.py`, `app/api/v1/lead2.py`, `app/ml/inference/e41_lead2.py`.
- **Records:** `data/e41/e41_lead2_record.json`, `data/e42/e42_lead2_record.json`, `data/e43/e43_record.json`,
  `data/e44/e44_record.json`, `data/e46/e46_record.json`, `data/fpp/fpp_record.json`,
  `data/fpp/aiPHeed_Food_Price_Pressure_exploratory.pdf`.
- **Builders:** `scripts/build_record_e41.py`, `e42`, `e43`, `e44`, `e46`, `fpp`.
- **Backend tests (9):** `test_e41_lead2`, `test_e42_lead2`, `test_e43_five_trigger`, `test_e44_final_candidate`,
  `test_e45_news_and_map`, `test_e46_corrected_candidate`, `test_e46_observed_vs_forecast`,
  `test_e48_score_variation`, `test_fpp_label_v2`.
- **Frontend:** `components/GuidedTour.tsx`, `components/MapTour.tsx`, `components/PageTours.tsx`, `lib/storage.ts`,
  `lib/tour.ts`, `test/driverCopy.test.ts`, `test/tour.test.ts`.

### Only in mine (278)
| Group | Files |
|---|---|
| `backend/experiments/` e42-e59 (incl. e54_data_check 74, e43 35, e48 16, e53 14, e55 11, e57 11, e59 8) | ~232 |
| `backend/data/e48`, `e49` (protected), `e53` | 38 |
| `backend/tests/integration/` (test_e53_served_model, test_e55_lead2_preview, test_lgu_risk_level, test_news_view, test_self_description, test_explainability_alignment, test_news_counts, test_objectives_completion, test_e49_served_model) | 9 |
| `backend/app/quarterly/verdicts.py`, `backend/data/news_e31/topics/manifest.json`, `frontend/src/test/newsView.test.tsx` | 3 |

### Changed on both sides since the merge base (9) = likely conflicts
| File | Mine | Theirs |
|---|---|---|
| `backend/app/services/dashboard.py` | +315 / -42 | +244 / -14 |
| `backend/app/api/v1/insights.py` | +64 / -10 | +39 / -3 |
| `backend/app/schemas/public.py` | +38 / -1 | +32 / -0 |
| `backend/app/api/v1/forecast.py` | +5 / -2 | +28 / -3 |
| `backend/app/api/v1/dashboard.py` | +10 / -6 | +4 / -3 |
| `backend/tests/integration/test_dynamic_target.py` | +108 / -24 | +16 / -0 |
| `frontend/src/components/RightAnalyticsPanel.tsx` | +45 / -12 | +125 / -50 |
| `frontend/src/components/LeftPanel.tsx` | +9 / -3 | +45 / -12 |
| `frontend/src/lib/apiTypes.ts` | +13 / -1 | +36 / -3 |

### Changed on one side only (file exists in both)
- **Mine only (17):**
  - Backend app: `api/v1/alerts.py`, `api/v1/quarterly.py`, `ml/inference/e31_engine.py`, `ml/nlp/topic_model.py`,
    `news/topics.py`, `quarterly/alerts_e31.py`, `quarterly/lgu_audit.py`, `quarterly/target.py`,
    `schemas/alerts.py`, `services/report.py`, `services/report_data_e31.py`.
  - Scripts: `scripts/build_record_e36.py`, `scripts/news_collect.py`.
  - Tests: `tests/conftest.py`, `test_api_dashboard.py`, `test_e36_served_model.py`.
  - Frontend: `frontend/src/lib/queries.ts`.
- **Theirs only (13):**
  - Backend: `backend/app/api/router.py` (registers fpp and lead2).
  - Frontend components: `AboutModal.tsx`, `DisplayPreferencesModal.tsx`, `MapBottomSheet.tsx`,
    `MapDashboard.tsx`, `TopNavbar.tsx`.
  - Frontend other: `index.css`, `lib/driverCopy.ts`.
  - Frontend pages: `Admin.tsx`, `Data.tsx`, `Index.tsx`, **`Landing.tsx`**, `Visualization.tsx`.

## 3. What each side did

### Served model, record and environment defaults
| | Mine | Theirs |
|---|---|---|
| Default record | **E49-C2** (`AIPHEED_RECORD`, default `e49`): E48-A1 LightGBM with trigger features + shrinkage, lead 1 | **E36** (`AIPHEED_E31_RECORD`, default `data/e36/e36_record.json`), as at the merge base; their branch has no E48/E49/E53 |
| Lead served by default | **Lead 1 only** (`AIPHEED_MAX_LEAD`, default `1`); the dashboard target is 2026-Q4 | **Lead 2** (the merge base's dynamic next-quarter target): the dashboard target is 2027-Q1, shown with E38's lead-2 row |
| Lead-2 switch | `AIPHEED_MAX_LEAD=2` adds the **E55** row (E53-A1 at lead 2, same thesis label, "experimental preview", accuracy 0.673) under `AIPHEED_RECORD=e53` | `AIPHEED_LEAD2_MODEL` (default `e38`). `e41` / `e42` / `e43` / `e44` / `e46` serve an alternative lead-2 candidate from its own record |
| Other switches | – | `LABEL_VERSION=v2`: the exploratory Food Price Pressure label (`/fpp/*`) |

### Their lead-2 policy, exactly (`app/ml/inference/e41_lead2.py`, `app/api/v1/lead2.py`, `services/dashboard.py`)

1. **The default (`e38`) changes nothing.** The dashboard keeps the merge base's behaviour: the next quarter
   (2027-Q1) is the target, served by E38's lead-2 row.
2. **The candidates forecast a different event than the thesis label.**
   - **E41/E42** forecast P(provincial food inflation > 4%) in the target quarter. Their code says: "price
     pressure, not food insecurity".
   - **E43/E44/E46** forecast a five-trigger food-stress target (T43, built from the E40 signals).
   - Each record is SHA-checked, and refused (409) if its target is not the dashboard's current target.
3. **"Governs" mode (E46).** When a candidate is enabled and its record is for the current target, it takes over
   **every quarter** on the dashboard. The index, provinces, timeline, LGUs and drivers then show the candidate's
   own as-of backtest probabilities of its own event, never the v1-label probabilities. This fixes a mismatch they
   found ("observed about 0.98, forecast about 0.2").
4. **Their own results do not support promoting any candidate.**
   - Their E46 report: "75% with balanced discrimination NOT met".
   - Their E49 (E38 vs E46 on identical rows): "neither meets the pre-registered promotion rule -> keep default
     temporarily".
   - Their E51: on the thesis label, no candidate passes.

**How it differs from mine.**
- **Default lead.** Mine serves **lead 1 by default**, because lead 2 is not reliable (my E59: Maximum Reliable
  Lead Time = 1 quarter). Theirs serves **lead 2 by default** (E38).
- **What lead 2 forecasts.** My lead-2 option (E55) forecasts the **same thesis label** and is labelled an
  experimental preview. Their lead-2 options forecast **a different target** (price pressure or T43), and in
  governs mode they replace the thesis-label scores on every quarter.

### Endpoints
- **Theirs:** `/fpp/record`, `/fpp/summary`, `/fpp/report.pdf`, `/lead2/summary`, `/lead2/provinces/{id}`.
- **Mine:** `/insights/topics`.
- **Both changed shared responses:**
  - Theirs: trigger statuses, evidence notes, the candidate's horizon and confidence.
  - Mine: explainability alignment (0% drivers omitted, hunger-survey share note, region on the index scale), news
    card counts and limited-data flags, measured conditions, LGU level = province level, Rule 7 alerts, the
    composed 75% verdict.

### Tests
- **Theirs:** 9 new backend test files. **Their backend suite passes in their folder: 368 passed, 18 skipped**
  (my venv, used read-only; imports resolved to their code; their folder still clean afterwards).
  Frontend: their commit message reports vitest 45 passing, but I didn't run it, because their worktree has no
  `node_modules` and installing would change their folder.
- **Mine:** 402 passed, 18 skipped (backend); frontend 35/35.

## 4. Flags

- **Likely conflicts:** the 9 files above. `services/dashboard.py` is the hardest (+315 vs +244, both in the
  forecast, explainability, news and municipal paths). `RightAnalyticsPanel.tsx` is next (both changed the news
  and driver sections).
- **Protected files:** theirs does not change any. `e36_record.json` is byte-identical. `e48`/`e49` (four of the
  five protected files) do not exist on their side, because they came with my unpushed `430a347`; merging would
  keep mine.
- **Frontend on their side:** 22 files. They brought in the guided tours from `updated-ui-with-tutorial`
  (`b648f79`) with a 3-way merge.
  - **Landing page changed (`Landing.tsx` +2/-1):** the theme read now uses a safe `readStorage()` wrapper instead
    of `localStorage.getItem`. Small and behaviour-neutral, but it is the landing page you asked to keep
    untouched, so it needs your approval.
- **Models and records added by them:** e41, e42, e43, e44, e46 and fpp records (plus the FPP PDF). None replaces
  an existing record. None changes the default model unless `AIPHEED_LEAD2_MODEL` or `LABEL_VERSION` is set.
- **Experiment-number collision:** E39-E51 on both sides (see section 1).

## 5. Recommendation (no merge done)

**Safe to bring in later** (additive, off by default):
1. Their new backend modules, records, builders and tests (`fpp.py`, `lead2.py`, `e41_lead2.py`, `data/e41..e46`,
   `data/fpp`, `scripts/build_record_e4x.py`, the 9 test files), plus `router.py`.
2. Their new frontend files: `GuidedTour.tsx`, `MapTour.tsx`, `PageTours.tsx`, `lib/tour.ts`, `lib/storage.ts`,
   and the tour and driverCopy tests.
3. Their changes to files I didn't touch: `MapDashboard.tsx`, `TopNavbar.tsx`, `AboutModal.tsx`,
   `DisplayPreferencesModal.tsx`, `MapBottomSheet.tsx`, `index.css`, `driverCopy.ts`, `Admin.tsx`, `Data.tsx`,
   `Index.tsx`, `Visualization.tsx`. `Landing.tsx` only with your approval.

**Conflicts** (resolve by hand): the 9 files changed on both sides. Their `services/dashboard.py` hooks (`E41L2.serves`
/ `governs` in the forecast, municipal and driver paths) must be re-applied on top of my version.

**A policy decision is needed first.** There are now two lead-2 switches with different meanings:
`AIPHEED_MAX_LEAD` (mine; same label) and `AIPHEED_LEAD2_MODEL` (theirs; different targets).
- **Recommended:** keep lead 1 as the default; the evidence is E59 (Maximum Reliable Lead Time = 1).
- Keep their candidates as opt-in experimental previews.
- Do not let "governs" mode be a default: it changes the forecast target away from the thesis label on every
  quarter.

**Suggested order:**
1. **Secure your own work first** (your decision; nothing was done): commit your uncommitted changes and push your
   branch (`430a347` is not on GitHub), so the teammate merges against your real state.
2. Bring in their **additive backend** files (records, modules, builders, tests) and `router.py`; run both suites.
3. Bring in their **non-conflicting frontend** files (tours, storage, the pages listed above); approve or skip
   `Landing.tsx`; run vitest.
4. Resolve the **9 conflicting files**: schemas and `apiTypes.ts` first (additive fields), then `insights.py`,
   `forecast.py`, `api/v1/dashboard.py`, then `services/dashboard.py`, then `LeftPanel.tsx` /
   `RightAnalyticsPanel.tsx`, then `test_dynamic_target.py`.
5. Apply the agreed lead-2 policy, so one switch documents both.
6. Rename one side's experiments, e.g. prefix theirs `A-E39..A-E51` or mine `C-E42..C-E59`, so the manuscript can
   cite them unambiguously.
7. Final check: both backend suites, frontend tests, the 5 protected md5s, and a live run of both lead-2 options.

## 6. Live comparison: what each dashboard serves (in-process, read-only, 2026-10-17)

Each checkout's own API was called with its own code and data (in-memory test database; nothing written). The CALABARZON
index is shown, with the provinces in brackets.

| | Mine, default (`e49`, lead 1) | Mine, preview (`e53`, `MAX_LEAD=2`) | Theirs, default (`LEAD2_MODEL=e38`) | Theirs, `LEAD2_MODEL=e46` |
|---|---|---|---|---|
| Opens on (current / target) | 2026-Q4 / 2026-Q4 | 2026-Q4 / 2027-Q1 | **2027-Q1** / 2027-Q1 | **2027-Q1** / 2027-Q1 |
| Model panel (dev., 65 rows) | E49-C2: acc 0.846, bal 0.841, AUC 0.855, Brier 0.151 | E53-A1: 0.785 / 0.836 / 0.880 / 0.150 | E36: 0.815 / 0.822 / 0.850 / 0.154 | **same E36 numbers**, although the scores shown come from E46 |
| 2026-Q3 | 0.912 high | 0.896 high | 0.992 high | **0.305 low** |
| 2026-Q4 | **0.778** high (Batangas 0.335) | 0.789 high (Batangas 0.284) | 0.822 high (Batangas 0.169; others 0.98-0.99) | **0.075 low** (Quezon 0.281; Rizal 0.001) |
| 2027-Q1 | not served (404) | 0.798 high (E55 preview; four provinces tied at 0.82) | **0.922** high (E38; four provinces tied at 0.952) | **0.065 low** (Quezon 0.146) |
| Drivers, 2026-Q4 region | Market 72% / Climate 26% / Fish 2%, all protective | Market 64% prot., Employment 18% up, Fish 12%, Climate 5%, OFW 1% | **Market 100%**, four drivers at 0% labelled "increases" | Market 78% prot., Climate 11% up, Employment 9%, OFW 2%, Fish 0% |

**Reading.**
1. **Same label, different models.** Mine (both setups) and their default forecast the same thesis label (S1 vs the
   trailing median), and all show 2026-Q4 high (0.78-0.82). Their default is more saturated: four provinces are at
   0.98-0.99, and 2027-Q1 is at 0.95, from E38 at lead 2 (development accuracy 0.709, below persistence). Their
   driver panel shows Market 100% with 0% drivers labelled "increases", which mine fixed (B1).
2. **E46 is a different event.** With `LEAD2_MODEL=e46`, every quarter switches to the T43 five-trigger
   food-stress target. The dashboard then says **low** (0.065-0.305) where the thesis-label models say high
   (0.78-0.92). Both can be "right" for their own target, but a reader sees the same "Risk level" card flip from
   high to low.
3. **E46's model panel is mismatched.** It still reports E36's lead-1 accuracy (0.815), which does not describe the
   E46 scores on screen. This should be fixed before e46 is ever shown.
4. **Default lead.** Their dashboard opens on 2027-Q1 (lead 2) by default; mine opens on 2026-Q4 (lead 1). My E59
   shows lead 2 is not reliable for this model family (0.709).

Housekeeping: the first attempt created an empty, git-ignored `backend/aipheed.db` (0 bytes) in the teammate folder.
It was deleted, and the comparison was rerun with the in-memory test database. Their folder is clean (0 status
entries), mine is unchanged (46).
