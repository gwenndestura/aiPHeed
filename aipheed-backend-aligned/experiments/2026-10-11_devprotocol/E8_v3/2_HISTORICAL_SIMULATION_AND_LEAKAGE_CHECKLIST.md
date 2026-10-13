# E8 v3: Historical-Simulation and Leakage Checklist

**Status: DRAFT, 2026-10-12. Nothing in this checklist has been executed.**

**Sources.** Every status below comes from existing code or evidence files read during this session:

- `scripts/supplementary/devprotocol_rule_l.py`: SWS registry, CPI availability rule, schedules, protected set;
- `scripts/supplementary/improvement_study.py`, `window2021_study.py`, `reliability_diagnostics.py`: the frame lineage;
- `data/supplementary/collection_2026-10-09/cpi_2026_release_dates.csv`;
- `evidence/2026-10-09_readiness/cpi_final_month_release_dates.csv`.

**No release date was looked up, inferred or invented for this checklist.** A value's presence in a dataset is never treated as evidence that it was available.

## Status terms

| Term | Meaning |
|---|---|
| **Verified** | The registry records a dated primary or archived source. "Verified-single" means one dated source; it counts as verified and is disclosed. |
| **Proxy** | The date is derived from another series' date plus a fixed buffer (WD1: national CPI date + 14 days). **Unverified.** |
| **Schedule** | The date is derived from a documented typical release lag (`SCHEDULE_DAYS`), not from a dated release. **Unverified.** |
| **Unknown** | No date is recorded. **Excluded** (L4). |

**Margin.** Days between the documented or proxy date and the cutoff. **A margin is reported for context only; it never converts "unverified" into "verified".**

---

## A. Inputs: availability at each cutoff

Cutoffs: **C3 = 2026-07-01** (target 2026-Q3) and **C4 = 2026-10-01** (target 2026-Q4), both at 00:00 Asia/Manila.

Government inputs refer to T−2, so 2026-Q1 for C3 and 2026-Q2 for C4. SWS is the latest round published before the cutoff.

| # | Input (arms) | Value used at C3 | Status at C3 | Value used at C4 | Status at C4 |
|---|---|---|---|---|---|
| A1 | `sws_hunger` (all arms) | March 2026 round, published 2026-05-12 | **Verified**; margin 50 days | March 2026 round. The June 2026 round's publication date is **unknown**, so it is **excluded** (L4). | **Verified**. The input is 3 quarters old, exactly at the staleness limit (`SWS_MAX_AGE_QUARTERS = 3`; only age > 3 is stale), so the forecast is not INSUFFICIENT_DATA, but this must be disclosed. |
| A2 | `sws_change` (all arms) | March 2026 minus November 2025 (published 2026-01-14) | **Verified-single** (Nov 2025) + verified (Mar 2026) | Same | Same |
| A3 | `last_published_stress` (A1–A4, B1) | Latest label in the training set: 2025-Q4 (H5; 2026-Q1 is excluded by design, see B3). Proxy date 2026-01-20 (Dec 2025 national CPI 2026-01-06 + 14 days). | **Proxy (unverified)**; margin 162 days | Same, 2025-Q4 | **Proxy (unverified)**; margin 254 days |
| A4 | `cpi_rel`, `cpi_dev`, `food_cpi`, `food_cpi_yoy` (+lag1, accel) (A2, A3, B2, B3) | Provincial food CPI, final month March 2026. National release 2026-04-07; provincial proxy 2026-04-21. | **Proxy (unverified)**; margin 71 days | Final month June 2026. National release 2026-07-07; provincial proxy 2026-07-21. | **Proxy (unverified)**; margin 72 days |
| A5 | `cpi_rel_lag1` (A2, A3) | Final month December 2025; national 2026-01-06; proxy 2026-01-20 | **Proxy (unverified)** | Final month March 2026; proxy 2026-04-21 | **Proxy (unverified)** |
| A6 | `poverty_incidence` (A2, A3) | 2023 survey vintage. Release documented only as "August 2024" in a code comment (`reliability_diagnostics.py`), with no evidence file cited. | **Unverified** (month-level, uncited); margin about 22 months | Same | Same |
| A7 | National and regional government series: unemployment, remittances, fuel, Brent, FX (A3 only) | 2026-Q1 values | **Schedule (unverified)** for each family (`SCHEDULE_DAYS`) | 2026-Q2 values | **Schedule (unverified)** |
| A8 | `rice_price_regular` (+accel) (excluded from A2; available to A3) | — | **Excluded**: residual forward-filled cells (§C3) | — | Excluded |
| A9 | News (FSSI, triggers) (A4 only, descriptive) | 2026-Q2 articles | **Not assessed**: news is excluded by the sufficiency rule (0/100), and the article archive is a potential carrier (§E5) | — | Not assessed |

### A.1 Never inputs at either cutoff

These are protected:

- the September 2026 SWS round and any round with fieldwork from 2026-07-01;
- food CPI for reference months 2026-07 to 2026-12.

**Even at C4, July–August 2026 CPI is not used.** The T−2 rule uses 2026-Q2 only. July and August 2026 CPI are protected outcome components of the Q3 and Q4 labels.

### A.2 Verification route (approval A3; nothing is done without it)

| Date to verify | Route | Exposure risk | Safeguard proposed |
|---|---|---|---|
| Provincial CPI release dates, RSSO IV-A, 2021-01 to 2026-06 | PSA RSSO IV-A release pages or archived snapshots | The same pages and feeds list **July–December 2026 releases** (P2) | You perform the lookup yourself, or Claude uses only archived snapshots captured **before 2026-08-01**, recording dates only and never values |
| June 2026 SWS round publication date | SWS website or news | The SWS site and news feeds show the **September 2026 round** (P1) | Same: you do it yourself, or snapshots captured before 2026-09-01 only. **Recommended default: leave it unknown and excluded.** |

---

## B. Training labels

| Check | Status | Note |
|---|---|---|
| B1. Only labels published before the cutoff | **Specified, not executed** | Label quarters 2021-Q2 to 2025-Q4 (16 quarters). L1 rule: a label becomes available when both its SWS round and its provincial CPI final month are published. |
| B2. Label availability dates | **Unverified for every label** | Every label needs the provincial CPI date. Only 2024-Q4 has a verified provincial date (2025-01-13); all others are proxies. SWS dates are verified or verified-single for the rounds used. |
| B3. No 2026 label is built or used | **Specified (design restriction)** | The registry raises an error if a protected SWS quarter appears (`assert not any(x.quarter in PROTECTED ...)`). In the registry, 2026 SWS rounds are inputs only (`in_label_definition_A = quarter <= "2025-Q4"`). **This is a rule, not an availability fact.** The 2026-Q1 label was computable by 2026-05-12, before C3. The 2026-Q2 label was not computable at C4 under H1, because the June 2026 SWS date is unknown. Excluding 2026-Q1 gives the model *less* information than a real-time forecaster had; changing it needs approval A6. **Correction to v2 (D6):** rows with target 2026-Q1 are not training rows, because they have no label. |
| B4. Threshold τ = 14.345 computed only from labels available by 2026-07-01 | **Recorded earlier; not re-executed** | Computed from 16 labelled quarters in a prior step. It inherits B2's proxy-date status. |
| B5. Revised label vintages (WD2) | **Disclosed limitation** | Labels use the CPI values in the current tables, not the vintage available at each cutoff. Revisions after first release are possible and are not reconstructable from existing files. |

---

## C. Feature engineering, fill and rolling calculations

| Check | Status | Note |
|---|---|---|
| C1. No zero-fill of missing values | **Implemented in code** (K1). Not re-tested on the E8 frame (not built). | K1 resets zero-filled cells to NaN for the `SOURCE_GAPS` columns. |
| C2. No forward-fill across quarters | **Partial** | Fill code was not reviewed for every source table. See C3. |
| C3. Residual forward-fill: `psa_rice_price_regular` | **Known defect** | 3 forward-filled cells are not reset by K1. **Rice price is excluded from A2.** A3's selection pool must also exclude it, or the fix must be approved first (A5). |
| C4. Rolling and lag features use prior quarters only | **Implemented in code** | `cpi_dev` uses `shift(1).rolling(4, min_periods=2)`; lags use `shift(1)` within province. |
| C5. Cross-sectional features (`cpi_rel` = province minus five-province mean) | **Disclosed** | Uses the same-quarter cross-section of the input quarter (T−2), not of the target quarter. It is computed from the full five-province set, which is available at the same proxy date. |
| C6. `fssi_article_count` is zero-filled | **Disclosed** | `fillna(0)` on article counts (`improvement_study.py`). Affects news features only, which are excluded from A1–A3. |
| C7. Frame loads more files than it uses | **Leakage-surface finding** | The current development frame (`devprotocol_rule_l.development_frame` → `window2021_study.window_frame` → `improvement_study.corrected_features` → `reliability_diagnostics.load`) reads these into memory: aligned `sws_hunger.parquet` (later replaced by the registry), `features_fused`, `labels`, `psa_indicators`, `fssi_quarterly`, `trigger_proportions`, `corpus_geocoded`, `oil_prices`, `bsp_macro`, `pagasa_climate` and `province_rainfall`. Several have unverified coverage (checklist 3). **E8 must not use this frame as-is.** Approval A5 proposes an allowlist-only frame. |

---

## D. Design choices and test-quarter information

| Choice | Source of the choice | Blind-quarter information used? |
|---|---|---|
| LightGBM settings (`num_leaves=4`, 100 trees, lr 0.05, `min_child_samples=5`) | Fixed in E3 (2026-10-11) from 2021–2025 analyses | **No.** 2026-Q3/Q4 outcomes did not exist in any file used by this session. |
| Arms and input groups | E1–E7 results on 2021–2025 quarters | **No.** But the choices were informed by **reused** quarters, so those quarters are excluded from conclusions. |
| Threshold 0.50 | Fixed rule (standing instruction) | **No** |
| τ = 14.345 | 16 labels available before 2026-07-01 | **No** (proxy-dated; see B4) |
| M6 group-selection procedure | Training-only inner walk-forward | **No.** The procedure was designed after seeing E6/E7 results on reused quarters (disclosed). |
| Gross-failure margins (protocol §8.1) | A-priori arguments (uninformative Brier, SWS sampling error, the random-ranking distribution) | **No** |
| Feature filter (> 50% missing or constant) | Fixed rule, applied to training rows only | **No** |

**Disclosure.** The design was developed over seven exploratory analyses on the same 2023-Q4 to 2025-Q4 quarters, so the arms are selected, not pre-specified. **This does not leak blind-quarter information**, but it is why the reused quarters support no conclusion.

---

## E. Leakage from existing forecasts, reports, caches, logs and derived files

| # | Source | Could it carry blind-quarter information? | Control |
|---|---|---|---|
| E1 | Frozen 2026 forecast files from 2026-10-09 (`FROZEN_2026_*.csv`) | They contain targets 2026-Q1/Q2 only. **No forecast exists for 2026-Q3/Q4.** | Not inputs; not read during E8 |
| E2 | E1–E7 run outputs | Built from quarters up to 2025-Q4. Their output hashes match their manifests (report 6). | Not inputs |
| E3 | Served artifacts (`data/revised/*.parquet`) | Target quarters end at **2025-Q4** in both artifacts. This was checked 2026-10-12 by reading their `target_quarter` column; these are this session's own artifacts and contain no protected data. **No served forecast exists for 2026-Q3/Q4.** | **Not inputs**; read-only |
| E4 | Production `backend/` panels, models, predictions, `aipheed.db`, `final_predictions` | **Potential carriers** (checklist 3) | Deny-listed; hash-only |
| E5 | News corpus (`corpus_geocoded.parquet`, aligned, mtime 2026-10-08) and news-derived tables | Articles dated July–October 2026 may **report protected CPI or SWS figures as text** | Deny-listed for E8; news is excluded from A1–A3 |
| E6 | `mlflow.db` / `mlruns` (both trees) | Logged metrics and parameters of earlier production runs that may have used 2026 rows | Deny-listed; hash-only |
| E7 | Session transcripts (`~/.claude/projects/C--Users-admin-aipheed/*.jsonl`), including the scheduled-task sessions | Any session that read a protected file holds its content in the transcript | **Never read** (no `list_events`, `search_session_transcripts` or `Read`) |
| E8 | Auto-memory files (`~/.claude/projects/.../memory/*.md`) | Written by earlier sessions; content not re-checked | The memory index lines contain no values. Individual memory files are not opened for E8. |
| E9 | `Claude outputs/` (42 files), `aipheed-lean/outputs`, `aiPHeed_Simplified_Methodology/outputs` | Unknown content; dated 2026-09-09 or later | Deny-listed; hash-only |
| E10 | This E8 v3 folder | Contains no data values | — |

---

## F. Simulation validity summary (expected; nothing executed)

| Simulation | Arms | Expected status | Reason |
|---|---|---|---|
| C3 → 2026-Q3 | A1 (Core) | **Proxy-dated (unverified)** | `last_published_stress` and every training label depend on proxy provincial CPI dates |
| C3 → 2026-Q3 | A2, A3, B2, B3 | **Proxy-dated (unverified)** | Above, plus provincial CPI inputs (proxy), poverty (uncited) and schedule-dated series (A3) |
| C3 → 2026-Q3 | B1 | **Proxy-dated (unverified)** | Last published stress |
| C3 → 2026-Q3 | B4 | **Verified** (inputs only; no training) | SWS March 2026 round, verified. The *outcome* still needs the protected label. |
| C4 → 2026-Q4 | All | Same as C3 | Additionally, SWS input age 3 is at the staleness limit |

**Consequence.** No E8 result can be described as leakage-safe except B4's input timing.

All model-arm results must carry the label "**historical simulation, proxy-dated (unverified)**". This holds unless approval A3 verifies the RSSO IV-A provincial CPI dates for 2021-01 to 2026-06 (and the poverty release date for A2 and A3).
