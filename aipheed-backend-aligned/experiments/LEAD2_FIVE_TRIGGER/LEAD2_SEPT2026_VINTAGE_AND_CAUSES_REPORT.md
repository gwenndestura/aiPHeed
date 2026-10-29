# Lead 2: September 2026 CPI vintage audit and ranked causes (2026-10-29)

**Branch:** `aiPHeed/lead2-lgbm-tuning` (local).

| Item | Location |
|---|---|
| Audit script | `runner/sept2026_vintage_audit.py` |
| Audit outputs | `out/sept2026_vintage_audit.json`; `out/sept2026_vintage_inputs.csv` (every sealed input: seal × province × lead × feature, with value used, CPI months, classification, evidence) |
| Tests | `backend/tests/integration/test_sept2026_vintage_audit.py` |

The sealed files, served model, frozen protocol, criteria and owner dates were not changed. The owner's attached files (`psa_cpi_september_2026_release_dates_20261029.csv`, `PSA_CPI_SEPTEMBER_2026_TIMING_AUDIT_20261029.md`) were not found on disk. The five provincial release dates were therefore taken from the owner's message and are recorded as owner-reported, with sources pending.

## 1. Are the sealed forecasts temporally valid?

**Inputs traced.**
- The sealed Lead 2-4 rows (issue 2026-10-15) use the CPI cut-off 2026-09 for five features:
  - `A1_food`, `A_mom` and `A1_food_anc` use food CPI only;
  - `A1_gap` and `A1_gap_anc` use food and all-items CPI.
- Both seals are reproduced from the committed snapshot to 4.7e-7. Their hashes are unchanged: CR dd293e2e…, CR-ANC 07c99e56….

**Provenance** (committed acquisition records, not inferred from scores):

| Snapshot | Table | Content | Retrieved |
|---|---|---|---|
| E31, commit 81b5fa86 | OpenSTAT 0012M4ACP23 (YoY, 2018=100) | **FOOD only**, 5 provinces, through 2026-09 | **2026-10-14 15:34:40 UTC (23:34 PHT), before the issue date** |
| E40, commit 9624188 | 0012M4ACP23 | food and all items | 2026-10-15 09:18:32 UTC (17:18 PHT) |
| E41, commit 7960517 | 0012M4ACP22 (index; **the model's source**) | food and all items | 2026-10-15 09:54:05 UTC (17:54 PHT) |

- The food index values used imply exactly (|Δ| = 0.0) the food YoY published by 2026-10-14 for all five provinces.
- **OpenSTAT carried the provincial figures before the provincial press releases.** Quezon's September 2026 values were on OpenSTAT on 2026-10-15, although its provincial release is dated 2026-10-16.

**Classification of the inputs** (45 in CR, 75 in CR-ANC):

| Inputs | Classification |
|---|---|
| Food-based features, all provinces | **Demonstrably available before issue** (OpenSTAT 2026-10-14, value-matched) |
| Gap features, Cavite (release 10-12), Laguna and Batangas (10-13) | Available before issue per the owner's provincial release dates. **Sources and content still to be supplied.** |
| Gap features, **Rizal** (release 10-15) and **Quezon** (release 10-16) | **Same-day timing unresolved.** All-items CPI is first proven public on the issue day (17:18 PHT); the posting time is unknown. |
| Any input | **None demonstrably released after issue**, for the source the model used |

**Impact** (diagnostic only; nothing replaced or resealed): the sealed rows are re-predicted with the same fitted models and all-items cut at 2026-08 for Rizal and Quezon.

| Seal | Row | Sealed | With all-items through 2026-08 |
|---|---|---|---|
| CR | Rizal, 2027-Q1, Lead 2 | LOW 0.327 | **HIGH 0.543** |
| CR-ANC | Rizal, 2027-Q1, Lead 2 | LOW 0.381 | **HIGH 0.669** |
| both | Quezon (all leads); Rizal Leads 3-4 | — | unchanged |

**Verdict.**
- The sealed forecasts **remain valid for prospective evaluation in 28 of 30 rows.** That is every row except Rizal Lead 2 in each seal; Rizal and Quezon Leads 3-4 and Quezon Lead 2 do not depend on the unresolved timing.
- **Rizal 2027-Q1 (Lead 2) in both seals is temporally unresolved, and its call depends on it.** It must be scored and reported separately as `timing-unresolved` until the issue-day posting time of Rizal's September 2026 all-items CPI is established. Quezon's unresolved inputs do not change any Quezon call.

**Proposed correction, for approval (not done).** Keep both sealed files untouched. Seal one labelled companion record for **Rizal 2027-Q1 only**, in both seals, with all-items CPI cut at 2026-08. Its outcome does not exist yet, so the companion is still prospective. Both versions are scored, and the companion is the one counted if the posting time is never established.

## 2. Causes of weak Lead 2, ranked by impact (CR's 13 Lead-2 errors; development rows)

| Rank | Cause | Evidence | Correctable with current data? |
|---|---|---|---|
| 1 | **Price condition changes after the issue** | 8 of 13 errors: 5 reversals (false alarms), 3 small late rises (misses, realised margin +0.19 to +0.69). The price part is right on 69% of rows. Oracle: true price → 0.938; true hunger → 0.769. | Partly. CPI refresh (CR) and anchored projections (CR-ANC) improved Brier (0.167 → 0.147 → 0.132). The rest needs forward price information that is not published before the issue. |
| 2 | **Target content** | Hunger is regional (Balance Luzon), identical across provinces and met in 11 of 13 quarters. The label equals the price condition in 100% of rows since 2023-Q4. **The model therefore mostly learns next-quarter price pressure.** | No. Needs a repeated provincial food-insecurity outcome (CBMS or FNRI FIES). |
| 3 | **Hunger survey timing** | 3 misses (2023-Q4): the latest SWS reading tied the 11.3 line, so π_H = 0.5 | No. Needs an inter-round hunger observation. |
| 4 | **Statistical fragility** | 13 quarters, 17 HIGH. R6 hangs on one row. Results flip with model setting (CR) and release-day assumption (CR-ANC). About 58 quarters needed. | No (time) |
| 5 | Model behaviour on the 2024 rice spike | 2 false alarms (2024-Q3) | Hypothesis; no issue-time rice-policy input exists |
| 6 | Release timing | No confirmed violation. Day-10 rule unverified (0 of 180 rows confirmed). 2021 training rows use 2018-based values that were published only after the rebasing. Rizal Sept 2026 is same-day (section 1). | Yes, by evidence: the pre-registered addendum re-score |
| 7 | Weak triggers | Only Market and prices is supported after correction (Leads 1-2, in CR-ANC). Climate, fish production and OFW remittances are not established. Employment/remittances and news are supported at Lead 1 only. News FSSI is missing in 83% of rows; poverty is a static profile. | No added value demonstrated; all 12 families kept |
| 8 | Class balance and calibration | 26% HIGH. Class weighting lowers recall (180/180). CR-ANC is under-confident (slope 1.45). Training-only calibration maps are unstable (fewer than 60 earlier rows). | Tested and rejected (CR-CAL, CR-WCAL, CR-T) |

**Baselines (Lead 2, 65 rows):**

| Configuration | Accuracy | Precision / recall | Brier |
|---|---|---|---|
| **CR-ANC** | **0.800** | **0.60 / 0.71** | **0.132** |
| CR | 0.800 | 0.61 / 0.65 | 0.147 |
| Served P0H4 | 0.769 | 0.60 / 0.35 | 0.194 |
| Price-projection rule × hunger | 0.738 | 0.50 / 0.65 | 0.189 |
| Price model without hunger | 0.708 | 0.47 / 0.82 | 0.200 |
| Always-LOW | 0.738 | — | — |
| Persistence | 0.723 | — | 0.277 |

The model adds value beyond price-only rules and the baselines, retrospectively. It still fails the frozen adoption rule, and its pass flips with the release assumption.

## 3. What should run next

1. **The pre-registered addendum re-score of CR-ANC** (one run, frozen rule), once all 180 province-months are confirmed. This is the only remaining experiment that can turn CR-ANC's retrospective result into an eligible one. Running any other release rule now would be selection on known results: day 15 and day 20 were already seen.
2. **Prospective scoring** of both seals as outcomes arrive (2026-Q4 first), with Rizal 2027-Q1 reported as timing-unresolved, plus the companion record if approved.
3. **Owner decision on the 2021 vintage** (2012=100 releases), before the addendum re-score.

No new model candidate is justified on the existing 13 quarters. Every correctable cause with available data has been tested (sections 20-24 of the thesis package and `LEAD2_ROOT_CAUSE_REPORT.md`).

**Maximum reliable horizon: Lead 1. Lead 2 is not demonstrated.**
