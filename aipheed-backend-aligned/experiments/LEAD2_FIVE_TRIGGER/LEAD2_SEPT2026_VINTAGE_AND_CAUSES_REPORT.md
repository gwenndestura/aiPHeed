# Lead 2: September 2026 CPI vintage audit and ranked causes (2026-10-29)

**Branch:** `aiPHeed/lead2-lgbm-tuning` (local).

| Item | Location |
|---|---|
| Audit script | `runner/sept2026_vintage_audit.py` |
| Audit outputs | `out/sept2026_vintage_audit.json`; `out/sept2026_vintage_inputs.csv` (every sealed input: seal × province × lead × feature, with value used, CPI months, classification, evidence) |
| Tests | `backend/tests/integration/test_sept2026_vintage_audit.py` |

The sealed files, served model, frozen protocol, criteria and owner dates were not changed. The owner's attached files (`psa_cpi_september_2026_release_dates_20261029.csv`, `PSA_CPI_SEPTEMBER_2026_TIMING_AUDIT_20261029.md`) were not found on disk. The five provincial release dates were therefore taken from the owner's message and are recorded as owner-reported, with sources pending.

> **Superseded in part (2026-10-29, section 4).** The section 1 verdict ("28 of 30 rows valid; only Rizal Lead 2 depends on the timing") and the companion's scoring rule are withdrawn. The sensitivity behind them split one province-month across two CPI months: September food with August all-items. That construction is not a consistent as-of cut-off. Under the frozen rule (addendum rule 2, restated in `ASOF_RULE_SEPT2026.md`), Rizal 2027-Q1 is LOW in both seals. Instead, **9 of the 30 Lead 2-4 rows** have a class that depends on whether September 2026 is counted. Section 4 has the evidence.

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

**Verdict (withdrawn; see section 4).**
- The sealed forecasts **remain valid for prospective evaluation in 28 of 30 rows.** That is every row except Rizal Lead 2 in each seal; Rizal and Quezon Leads 3-4 and Quezon Lead 2 do not depend on the unresolved timing.
- **Rizal 2027-Q1 (Lead 2) in both seals is temporally unresolved, and its call depends on it.** It must be scored and reported separately as `timing-unresolved` until the issue-day posting time of Rizal's September 2026 all-items CPI is established. Quezon's unresolved inputs do not change any Quezon call.

**Correction (approved by the owner 2026-10-29, sealed).** Both sealed files are untouched (hashes checked before and after). One labelled companion record for **Rizal 2027-Q1, Lead 2 only**, in both seals, is sealed separately:

| Item | Value |
|---|---|
| Script | `runner/rizal_companion_seal.py` |
| File | `sealed/rizal_2027q1_companion.csv`, SHA-256 `b1edb799f6f08158161164e8fab96c8ec3954cba91d8af36fe6392866753094a` (manifest `sealed/rizal_2027q1_companion.sha256`) |
| Sealed | 2026-10-29 11:09 UTC; latest existing outcome 2026-Q3, so the 2027-Q1 outcome did not exist |
| Inputs | Same fitted models and inputs as the originals (original row reproduced to 1e-5), except all-items CPI through 2026-08 in `A1_gap` / `A1_gap_anc`. Food CPI stays at 2026-09 |
| CR | LOW 0.327 → companion **HIGH 0.543** |
| CR-ANC | LOW 0.381 → companion **HIGH 0.669** |

**Scoring rule (withdrawn 2026-10-29).** This record said the companion would be the one counted. No frozen document authorizes that. Addendum rule 5 and `ASOF_RULE_SEPT2026.md` rule 6 apply instead: the sealed originals are scored as published, and the companion is kept unchanged as a labelled diagnostic record. Its construction, September food with August all-items, violates as-of rule 1. The `scoring_rule` field inside the companion manifest is part of the sealed record and is left as written; this withdrawal overrides it (erratum E5).

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
2. **Prospective scoring** of both seals as outcomes arrive (2026-Q4 first), with the 9 timing-dependent rows of section 4 reported separately.
3. **Owner decision on the 2021 vintage** (2012=100 releases), before the addendum re-score.

No new model candidate is justified on the existing 13 quarters. Every correctable cause with available data has been tested (sections 20-24 of the thesis package and `LEAD2_ROOT_CAUSE_REPORT.md`).

**Maximum reliable horizon: Lead 1. Lead 2 is not demonstrated.**

## 4. As-of audit of the September 2026 vintage (2026-10-29; supersedes the section 1 verdict)

**Files.**

| Item | Location |
|---|---|
| Rule | `ASOF_RULE_SEPT2026.md`, SHA-256 `4ac9bde8…` in `runner/ASOF_RULE_SHA256.txt`. Committed (6340f2e) **before** the province-wide variants were computed |
| Script | `runner/sept2026_asof_rule.py` |
| Outputs | `out/sept2026_asof_rule.json`; `out/sept2026_gap_trace.csv` (every gap feature, raw values → formula → value); `out/sept2026_asof_variants.csv` (every row, every variant) |
| Tests | `backend/tests/integration/test_sept2026_asof_rule.py` |

### 4.1 What "issued 2026-10-15" means

- No forecast in these files was produced on 2026-10-15. All three are reconstructions of what would have been issued on that nominal date:

  | File | Sealed at (UTC) |
  |---|---|
  | `cr_prospective.csv` | 2026-10-28 15:06 |
  | `cranc_prospective.csv` | 2026-10-29 01:39 |
  | `rizal_2027q1_companion.csv` | 2026-10-29 11:09 |

- So every file is judged by one question: which CPI values were public before the nominal issue date?
- No 2027-Q1 outcome existed at any of the three seal times, so all three remain prospective.

### 4.2 Source chain of the CPI the model reads

| Table | Official URL | Retrieved (UTC) | Commit | Check |
|---|---|---|---|---|
| Index, 0012M4ACP22: "Consumer Price Index for All Income Households by Commodity Group (2018=100): January 2018 - September 2026" (**the model's source**) | `https://openstat.psa.gov.ph/PXWeb/api/v1/en/DB/2M/PI/CPI/2018NEW/0012M4ACP22.px` | 2026-10-15 09:54:05 (17:54 PHT) | 7960517 | The raw response's SHA-256 (`5fbb3825…`) equals the acquisition record. All 690 monthly cells decode to exactly the values in `E41_Lead2_Audit/data_acquired/cpi_index_ACP22.csv`: 0 mismatches |
| YoY, 0012M4ACP23, food and all items | `…/0012M4ACP23.px` | 2026-10-15 09:18:32 (17:18 PHT) | 9624188 | raw `6e498c6c…` |
| YoY, 0012M4ACP23, **food only** (the query asked for commodity code 2 only, so no all-items cell was retrieved) | `…/0012M4ACP23.px`. Table title at retrieval: "… January 2019 - September 2026" | 2026-10-14 15:34:40 (23:34 PHT) | 81b5fa8 (committed 2026-10-15 00:43 PHT) | — |

**Why the companion's HIGH appeared: Rizal, 2027-Q1, Lead 2.**
- Base months b are 2026-01, 2026-02 and 2026-03.
- Formula: A1_gap = mean_b 100(F[m]/F[b] − 1) − mean_b 100(A[m′]/A[b] − 1) − TH_gap, with TH_gap = 0.92.
- Index values used: food Aug 144.9, Sep 149.5; all items Aug 146.0, Sep 147.7.

| Cut-off | Mean food YoY | Mean all-items YoY | A1_gap | A1_gap_anc |
|---|---|---|---|---|
| Sealed: Sep / Sep | 4.902 | 5.434 | −1.451 | −1.454 |
| Companion: Sep food / Aug all items | 4.902 | 4.220 | **−0.238** | **−0.486** |
| Rule: Aug / Aug | 1.674 | 4.220 | −3.466 | −3.500 |

- Food rose 3.2% from August to September. All items, which contains food, rose 1.2%.
- Pairing September food with August all-items keeps the food jump but removes its effect on the headline index. That pushes the gap above **both** consistent values.
- No training row ever combines the two series at different months: `cpi_refresh.csv` holds one `m0r` per row.
- So the companion's HIGH is a by-product of a construction the model never saw. It is not the effect of applying an information cut-off.

The trace for every province and Leads 2-4, at all three cut-offs, is in `out/sept2026_gap_trace.csv`. It reproduces the sealed feature values to 1e-9.

### 4.3 Was each September 2026 series public before 2026-10-15? (official evidence only)

| Series | Strongest evidence | Before 2026-10-15? |
|---|---|---|
| **Food**, all 5 provinces | OpenSTAT 0012M4ACP23 food YoY, retrieved 2026-10-14 23:34 PHT. The index table's food values imply the same YoY to the published 0.1 rounding (largest difference 0.05) | **Yes, as information.** The index table itself (0012M4ACP22) is first observed on 2026-10-15 17:54 PHT. Its release time is unknown; another table's retrieval is not taken as proof for it |
| **All items**, all 5 provinces | First retrieval: 2026-10-15 17:18 PHT (ACP23) and 17:54 PHT (ACP22). Index-implied YoY matches ACP23 to rounding | **Not shown for any province.** The 2026-10-14 retrieval did not request all items. The table's title already said "September 2026", but that does not show the all-items cells were filled |
| Provincial releases | Owner-reported: Cavite 10-12, Laguna 10-13, Batangas 10-13, Rizal 10-15, Quezon 10-16. Sources and saved copies are not yet supplied. `psa_cpi_release_dates_TO_FILL_v2.csv` marks all five 2026-09 rows `unresolved` | Cavite, Laguna and Batangas would be before the issue **if verified**. Rizal is the same day, which does not count under rule 2. Quezon is after |
| Web archive | Wayback CDX for 2026-10-01 to 2026-10-16: no capture of 0012M4ACP22 or 0012M4ACP23, and no Region IV-A CPI release page | — |

**Conclusion on timing.**
- **All items:** no official record shows September 2026 all-items CPI public before 2026-10-15, for any province. Only the owner-reported provincial dates suggest it for Cavite, Laguna and Batangas.
- **Food:** the information was public on 2026-10-14. The exact table the model reads was not demonstrated before the issue.
- **Rizal:** the same-day release does not satisfy "strictly before" under addendum rule 2, so no intraday time needs to be established.

### 4.4 One rule, applied everywhere

The rule is addendum rule 2, frozen in d5ebf84 before this vintage was examined. `ASOF_RULE_SEPT2026.md` restates it:
- one cut-off month per province-month;
- the release must be strictly before the issue date;
- food and all-items are never split across months;
- unverified dates are reported both ways.

The rule was committed before the variants were run. Results by variant (same fitted models; all 5 provinces × Leads 2-4 × both seals = 30 rows):

| Variant | Status | HIGH rows (CR / CR-ANC) | Rizal 2027-Q1 L2, CR | Rizal 2027-Q1 L2, CR-ANC |
|---|---|---|---|---|
| V0 sealed: September for all | Day-10 rule; September unverified | 6 / 9 | LOW 0.327 | LOW 0.381 |
| **V3 rule, September not verified for any province** | **Rule as of today** | 0 / 6 | **LOW 0.120** | **LOW 0.185** |
| **V2 rule, owner dates verified as reported** (Cavite, Laguna, Batangas September; Rizal, Quezon August) | Rule if the owner's dates are confirmed | 4 / 8 | **LOW 0.120** | **LOW 0.185** |
| V1 companion construction (food Sep / all Aug for Rizal, Quezon) | Violates rule 1; diagnostic only | — | HIGH 0.543 | HIGH 0.669 |
| V4 per-feature split (food features Sep, gap Aug/Aug) | Violates rule 1; sensitivity | — | LOW 0.160 | LOW 0.294 |

- **Rizal 2027-Q1 Lead 2 is LOW under every consistent cut-off** (V0, V2, V3, and even V4). It is HIGH only under the split construction.
- The companion's change from LOW to HIGH is therefore **not** a valid consequence of the correct availability cut-off.
- **Rows whose class depends on the unverified September 2026 timing:** 9 of 30. Each is HIGH with September counted and LOW without:

  | Seal | Province | Lead | Target | Sealed, Sep | Without Sep | Under owner dates |
  |---|---|---|---|---|---|---|
  | CR | Cavite | 3 | 2027-Q2 | HIGH 0.607 | LOW 0.468 | HIGH |
  | CR | Cavite | 4 | 2027-Q3 | HIGH 0.603 | LOW 0.336 | HIGH |
  | CR | Laguna | 3 | 2027-Q2 | HIGH 0.579 | LOW 0.342 | HIGH |
  | CR | Laguna | 4 | 2027-Q3 | HIGH 0.575 | LOW 0.340 | HIGH |
  | CR | Rizal | 3 | 2027-Q2 | HIGH 0.542 | LOW 0.411 | **LOW** |
  | CR | Rizal | 4 | 2027-Q3 | HIGH 0.538 | LOW 0.252 | **LOW** |
  | CR-ANC | Batangas | 4 | 2027-Q3 | HIGH 0.532 | LOW 0.467 | HIGH |
  | CR-ANC | Laguna | 4 | 2027-Q3 | HIGH 0.586 | LOW 0.439 | HIGH |
  | CR-ANC | Rizal | 4 | 2027-Q3 | HIGH 0.586 | LOW 0.300 | **LOW** |

  The other 21 Lead 2-4 rows and all 10 Lead 1 rows have the same class under either cut-off.

**Records.**
- The originals (dd293e2e…, 07c99e56…) are unchanged and are scored as published (addendum rule 5).
- The 2026-10-29 companion (b1edb799…) is retained unchanged as a separate, labelled diagnostic record. It is **not** the counted forecast.
- The as-of variants are written to `out/sept2026_asof_variants.csv` and committed before any 2026-Q4 to 2027-Q3 outcome exists. They are not sealed forecasts.

### 4.5 Unresolved questions (for the owner)

1. The sources and saved copies of the five September 2026 provincial releases (owner-reported 10-12 to 10-16). These decide the 6 rows above marked HIGH under owner dates.
2. Which publication counts as the "release" under addendum rule 1: the provincial press release or the OpenSTAT table posting?
   - OpenSTAT held Quezon's September values on 2026-10-15, before its 10-16 press release.
   - Food values were on OpenSTAT by 2026-10-14.
   - The addendum does not settle this. It needs a recorded decision before the CR-ANC re-score.
3. Whether the OpenSTAT posting time of the September 2026 index table (0012M4ACP22) can be documented from PSA's side.

## 5. Lead 2 under the frozen criteria (provisional: timing unverified)

**Scope.**
- These are the existing development scores (65 Lead-2 rows, origins 2022-Q4 to 2026-Q2, `out/root_cause.json`). They use the pre-registered day-10 release rule, which is **unverified**: 0 of 180 province-months are confirmed.
- Re-scoring under verified dates is the blocked addendum re-score. It was **not run**.
- Nothing was refitted for this section.

| Lead 2 | Acc. | Bal. acc. | Prec. | **HIGH recall** | TP/FP/FN/TN | **False alarms** | Brier | Cal. slope / in-the-large | R1-R7 |
|---|---|---|---|---|---|---|---|---|---|
| Served P0H4 | 0.769 | 0.635 | 0.600 | 0.353 | 6/4/11/44 | 4 | 0.194 | 0.47 / +0.033 | fails R3, R5, R6 |
| **B0 = P0H4-U (retained Lead-2 model)** | 0.800 | 0.732 | 0.625 | **0.588** | 10/6/7/42 | 6 | 0.167 | 1.04 / +0.068 | **fails R6** (recall < 0.60) |
| CR | 0.800 | 0.751 | 0.611 | 0.647 | 11/7/6/41 | 7 | 0.147 | 1.50 / +0.085 | passes |
| CR-ANC | 0.800 | 0.770 | 0.600 | 0.706 | 12/8/5/40 | 8 | 0.132 | 1.45 / +0.057 | passes |
| Always-LOW | 0.738 | 0.500 | — | 0 | — | 0 | — | — | — |
| Persistence | 0.723 | 0.699 | 0.478 | 0.647 | 11/12/6/36 | 12 | 0.277 | 0.09 / +0.092 | — |
| Climatology | — | — | — | — | — | — | 0.228 | — | — |

**Against B0 and the adoption rule.**
- **CR-ANC:**
  - Brier is −0.036 better than B0 (p = 0.039).
  - It adds 3 new hits and 4 new false alarms, and precision is −0.025 lower.
  - It fails `final.adoption_rule` (precision within 0.02; new false alarms ≤ new hits). It is not eligible.
- **CR** fails the same rule (2 new hits, 3 new false alarms).
- **Frozen decision** (PROTOCOL_LEAD2_FINAL): Lead 2 is reliable only if B0, or an adopted candidate, passes R1-R7. B0 fails R6. No candidate is adopted. **Lead 2 is not reliable.**

**Calibration.**
- B0's calibration slope is close to 1 (1.04); its calibration-in-the-large is 0.068 (as computed in `out/root_cause.json`).
- CR and CR-ANC are under-confident (slopes 1.45-1.50).
- Training-only recalibration (CR-CAL, CR-WCAL) failed R6 at Lead 2.

**Overfitting.**
- CR-ANC, walk-forward over 15 origins: mean training Brier 0.167 against mean next-quarter test Brier 0.197.
- The price part reported in `out/lead2_objectives_audit.json` has the same pattern; its worst origins are 2022-Q4 (test 0.48) and 2023-Q4 (0.39).
- The gap is moderate. It is driven by regime changes, not by the training fit.

**Temporal generalization (CR-ANC).**
- Accuracy by thirds of the evaluation period: 0.80, 0.75, 0.85.
- Lowest leave-one-quarter-out accuracy: 0.78. Development rows 0.771; later rows 0.833.
- 8 hyper-parameter settings: all pass R1-R7 (accuracy 0.80-0.85).
- **Release-day sensitivity:**
  - day 15 fails R6 (recall 0.59);
  - day 20 passes.
  - So the pass depends on the unverified release timing, the question section 4 shows is unresolved.

**The five trigger groups (Lead 2).**
- Leave-one-group-out Brier change for B0 (`out/ablation.json`). A positive Δ means removing the group hurts. Holm adjustment is across the five groups.
- CR-ANC block ablation from `out/root_cause.json`, where employment and remittances form one block.

| Trigger group | B0 ΔBrier when removed | p (Holm) | Calls changed | CR-ANC ΔBrier | Lead-2 evidence |
|---|---|---|---|---|---|
| Market / prices | +0.037 | 0.014 (0.063) | 55% | +0.072, Holm p < 0.001 | **The only group with a material, consistent contribution** |
| Climate | −0.005 (removal helps) | 0.997 | 11% | +0.003, Holm p = 1.0 (0.997) | Not established |
| Employment | +0.003 | 0.24 (0.71) | 17% | combined block +0.001, Holm p = 0.13 | Not established |
| Fish production | −0.001 | 0.57 (1.0) | 20% | −0.001 | Not established |
| OFW remittances | +0.000007 | 0.013 (0.063) | 0.2% | (in the combined block) | Statistically detectable but negligible in size |

Removing all five triggers raises B0's Lead-2 Brier by 0.046 (p = 0.015). Almost all of that is the market group.

**Verdict.**
- **Lead 2 is not demonstrated to be reliable.** The retained model fails R6. The two candidates that pass R1-R7 fail the frozen adoption rule.
- Their pass also rests on release timing that is still unverified.
- The prospective files cannot change this until outcomes arrive. 9 of their 30 Lead 2-4 rows depend on the unverified September 2026 timing.
- **The maximum reliable horizon remains Lead 1.**
- **The CR-ANC re-score stays blocked** until all 180 province-months are verified and the release definition (question 4.5.2) is recorded.
