# PREREG_LEAD2: prospective evaluation of Lead 2 on sealed 2027+ quarters

**Written:** 2026-11-01, before any 2027 outcome exists (the first 2027 SWS round has not been fielded).

**Scope:** additive only. Nothing the backend serves changes: P0H4, its seal `a498b5ef`, the protocol and addenda hashes, the Lead-1 output, the FIRI v2 map scores, the driver bars and every API response.

**Lead 2 stays "experimental" everywhere until §7 is met.**

**Hash.** The SHA-256 of this file is computed over every byte before its last line, which begins `PREREG-SHA256:` and holds the hash. `backend/scripts/score_seal.py` and `seal_lead2.py` check it before use.

**Supersedes** commit `9958aba` (hash `dd6da691…`). That commit is void: a hashing error truncated that file to its first 619 bytes, before §1. No seal and no outcome existed when this replacement was written.

## 1. Why this exists

On the closed 2023–2026 quarters, no Lead-2 variant passed R1–R7:

| Variant | Result on the 65 official rows |
|---|---|
| P0H4 (served) | Fails R3, R5 and R6 |
| M0 | Fails R6 (recall 0.588) |
| M2 | Fails R3, R4 and R6 |

Those quarters are closed: nothing is retrained, re-thresholded or re-selected on them (`LEAD2_POST_SWS_PRICE/RESULTS.md`). The only remaining evidence is forecasts sealed before their outcome exists.

## 2. Candidates (all fixed; no refitting choices are left open)

The issue rule is O'(t) = max(first day of quarter t+1, min(P(t) + 1 day, quarter end + 67 days)), where P(t) is the publication date of the last non-commissioned Balance Luzon SWS round of quarter t (`LEAD2_POST_SWS_ISSUE`). Every candidate targets quarter t+2.

| ID | Candidate | Hunger part | Price part | Issued |
|---|---|---|---|---|
| **C0** | **P0H4 as served** | π_H4 at O(t) | Served P0 price arm, CPI cutoff m0(t) = month 2 of quarter t | O(t) = first day of quarter t+1 |
| **C1** | **M0** | π_H4 at O'(t) | Served P0 price arm (as C0) | O'(t) |
| **C2** | **M2** | π_H4 at O'(t) | P0 price arm refitted walk-forward with every origin's CPI cutoff = the newest month available at O'(t) (month M from the first day of M+2) | O'(t) |

Code: `LEAD2_POST_SWS_ISSUE/runner/score.py` (`post_issue`, `h4_at`, `persist_clim_at`) and `LEAD2_POST_SWS_PRICE/runner/price_refit.py` (parity-verified against the served pipeline), imported read-only.

The C0 value for a target already in `backend/data/ch1_engine/rows.csv` must equal that row (|diff| ≤ 5e-7, the stored precision).

**Baselines sealed alongside, at O'(t):**

- PERSIST-SI: newest SWS reading and newest three CPI months;
- CLIM;
- ALWAYS-LOW.

For C0's rules, the baselines are also computed at O(t), as in the served evaluation.

## 3. Decision rules (both fixed now)

| ID | Rule | HIGH when |
|---|---|---|
| **D0** | **Product** (served rule) | hunger part × price part ≥ 0.50 |
| **D1** | **Both parts** (the one alternative) | hunger part ≥ 0.50 **and** price part ≥ 0.50 |

**Why D1, from the development data only:**

- The label T43c is itself a conjunction: Balance Luzon hunger > 11.3 **and** the provincial food-price condition. D1 applies the same logic to the two estimated parts, instead of requiring their product to clear 0.50.
- On the development rows, the misses of M0 and M2 included rows where both parts were near or above 0.5 but the product was below 0.5 (`LEAD2_POST_SWS_PRICE/RESULTS.md` §4). D1 is the rule that directly addresses that pattern.
- No cutoff was searched: 0.50 is the served threshold applied to each part. Only this one alternative is registered.

**Context only, not evidence.** The development values below were computed on 2026-11-01 after D1 was fixed, on quarters already examined:

| Candidate | D0: TP/FP/FN/TN, acc, bal. acc, precision, recall | D1: TP/FP/FN/TN, acc, bal. acc, precision, recall |
|---|---|---|
| C0 | 6/4/11/44, 0.769, 0.635, 0.600, 0.353 | 6/17/11/31, 0.569, 0.499, 0.261, 0.353 |
| C1 | 10/6/7/42, 0.800, 0.732, 0.625, 0.588 | 10/10/7/38, 0.738, 0.690, 0.500, 0.588 |
| C2 | 9/8/8/40, 0.754, 0.681, 0.529, 0.529 | 13/12/4/36, 0.754, 0.757, 0.520, 0.765 |

**Under D1:**

- Classification and the classification rules (R2, R3, R4, R6, R7) use D1.
- The probability metrics (AUC, Brier) and R5 use the product probability, which is unchanged.

## 4. Outcome

- **Target:** T43c for each of the five CALABARZON provinces and each target quarter.
- **Hunger condition:** the mean of the quarter's non-commissioned Balance Luzon SWS rounds is > 11.3.
- **Price condition:** the provincial food YoY 3-month mean is > θ_food[p], or (food − all-items) > θ_gap[p], with the E40 thresholds and PSA CPI as first published.

An outcome is scored only after the target quarter's SWS result is published (`score_seal.py` refuses earlier).

## 5. Seals

- **One file per issue:** `backend/seals/<issue>_<target>.json`, written by `backend/scripts/seal_lead2.py`. It holds every candidate, both decision rules, the baselines, and each input's vintage.
- **Hash first:** its SHA-256 is appended to the append-only `backend/seals/LEDGER.md` before any outcome exists.
- **No overwrite:** an existing seal is never overwritten or edited.
- **Late seals:** a seal written after its issue date is marked "late" in the ledger, reported separately, and **excluded** from §6–§7. The first one is 2026-10-15 → 2027-Q1, written 2026-11-01.
- **Missing seals:** a quarter that is missing or sealed late is missing, never back-filled.

## 6. Metrics and rules (identical to the served evaluation)

**Metrics:** accuracy, balanced accuracy, precision, recall, specificity, AUC and Brier, each with a 95% quarter-cluster bootstrap CI (B = 2000, seed 2036).

**Rules:** R1–R7 exactly as frozen in `P0H4_LEAD12_REVIEW/runner/reproduce.rules`, threshold 0.50:

| Rule | Condition |
|---|---|
| R1 | ≥ 10 quarters and ≥ 40 rows |
| R2 | Accuracy ≥ 0.75 |
| R3 | Balanced accuracy ≥ 0.70 |
| R4 | Beats always-LOW and PERSIST-SI |
| R5 | Brier < PERSIST-SI and < CLIM, one-sided cluster p < 0.10 |
| R6 | Precision and recall both ≥ 0.60 |
| R7 | Each third ≥ 0.60, and leave-one-quarter-out minimum ≥ 0.70 |

**Rows:** on-time seals only (§5), with the baselines as sealed.

## 7. When a claim may be made

| Condition | Rule |
|---|---|
| Minimum data | No claim of any kind before **8** resolved on-time target quarters (40 province-quarters). The first on-time target is 2027-Q2 (issued after the 2026-Q4 SWS release, about mid-January 2027); the 8th is 2029-Q1 |
| Earliest 7-rule pass | R1 needs ≥ 10 quarters, so no candidate can pass all seven rules before **10** resolved on-time quarters (target 2029-Q3, resolved about late 2029). Between 8 and 9 quarters, results are reported as interim, with R1 failing |
| Primary hypothesis | **C1 (M0) under D0**: the variant closest to passing on the development rows (it failed only R6). The other five combinations (C0, C2 × D0, D1, and C1 × D1) are secondary and reported in full. A secondary-only pass is reported as exploratory, never as "Lead 2 is reliable" |
| What "reliable" means | Lead 2 may be called reliable only if the primary passes all seven rules at the first analysis with ≥ 10 resolved on-time quarters. Later quarters are added cumulatively under the same rules; no rule, cutoff or candidate changes after this file is hashed |
| Every way it is described | It always says it was issued after the SWS release (C1, C2), and is never presented as the original Lead 2 issued at O(t) |

## 8. Not changed by this file

- **The served system:** P0H4, `a498b5ef`, `rows.csv`, `evaluation.json`, R1–R7, the 0.50 threshold, Lead 1, FIRI v2 and the driver bars.
- **The other seals:** `e2bef0b2` and Y16 `208b5754`.
- **The closed 2023–2026 rows.**

PREREG-SHA256: 91fe94e0de1ec697b1fcc8e9b385512bf344d2920c386b5bb6f494e22cb2e47b
