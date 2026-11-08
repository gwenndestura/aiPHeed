# E87 — outcome data and the five mandatory drivers (report)

**Branch.** `e84-objective-continuation`.

**Evidence.**
- Protocol: `PROTOCOL.md`, frozen before scoring (commit f6572fe).
- Run: `runs/20261021T120748Z/`. It uses the E84 rows (13 target quarters per lead) and the E83 rules.

## 1. Outcome data: what was found and obtained

**FNRI FIES observations obtained** (public FNRI documents; `data_acquired/fnri_fies_observations.csv`, with page
citations; the PDFs stay local):

| Year | Area | Moderate-to-severe household FI | Severe | Basis |
|---|---|---|---|---|
| 2021 | Batangas (province) | 29.7% (90% CI 27.3–32.2) | 1.5% | ENNS, households |
| 2021 | Cavite (province) | 31.7% (27.0–36.4) | 2.4% | ENNS, households |
| 2021 | City of Lucena | 26.2% (23.6–28.9) | 1.0% | ENNS, households |
| 2023 | CALABARZON | 19.1% (95% CI 16.9–21.3) | 1.7% | NNS, households |
| 2025 | CALABARZON | 22.6% | 1.6% | Updating Survey, population |

These are **direct observations** (FIES, 12-month recall). They are annual or cross-sectional and cannot become
quarterly labels.

**What they establish:**
- Food insecurity in CALABARZON fell from 2021 to 2023 and rose by 2025. SWS Balance Luzon hunger moved the same way:
  2023 mean about 11%; 2025 rounds 24.0% and 16.7%.
- This is the first independent face-validity evidence that the SWS series tracks real regional food insecurity.
- Poor households are about twice as food-insecure as non-poor ones in every deck (46% vs 22–25% in 2021; 35.6% vs
  11.7% in 2023). That supports using poverty as the vulnerability term in the LGU ranking.

**Not obtainable without a request** (ready-to-send drafts in `DATA_REQUESTS.md`):

| Source | Route |
|---|---|
| CBMS 2024 municipal food-insecurity items | PSA CPCD, `cbms@psa.gov.ph`, CBMS Data Request Form |
| FNRI provincial FIES for Laguna, Quezon and Rizal, and 2023/2025 provincial domains | Director, DOST-FNRI, or eFOI |
| SWS hunger microdata for CALABARZON respondents 2021–2026 | SWS Survey Data Library, cost-based |

**Blocked:**
- CALABARZON wage orders IVA-19..23 are image-only PDFs (no text layer; OCR unavailable). They are not used.
- NDRRMC, ReliefWeb and publisher full text: see E84 `DATA_SOURCES_AUDIT.md`.

## 2. Fish Kill driver: a dated event dataset now exists

`data_derived/fishkill_events.csv` holds 132 de-duplicated fish-kill-related news events, 2021–2026:
- 11 reported kills in CALABARZON (Taal Lake, Laguna de Bay, Sampaloc Lake, Cavite, Quezon);
- 78 advisories, bans or warnings;
- 43 other or outside the region.

Each event carries its first-report date (when it became public), province, water body, outlets and kind. Every
record is "news-reported (not checked against BFAR records)".

Eleven confirmed-by-news kills in six years is too sparse to forecast with. It is useful as context and for event
monitoring.

## 3. Five-driver test against the binding constraint (Lead 2 primary)

**Hunger component, by driver** (T43 composite with S-COMP prices; all 65 rows; unissued rows counted as wrong):

| Arm | T43 accuracy | HIGH recall | Brier | Paired Brier vs random walk | Hunger accuracy (H-BIN) |
|---|---|---|---|---|---|
| HUN-RW (latest reading) | 0.738 (0.800 on 60 issued) | 0.38 | 0.249 | — | 0.69 |
| + Market/Prices | 0.646 | 0.00 | 0.300 | −0.054 (worse) | 0.54 |
| + Employment | 0.631 | 0.00 | 0.294 | −0.049 (worse) | 0.54 |
| + Climate Stress | 0.708 | 0.19 | 0.249 | +0.000 (p 0.48) | 0.69 |
| + OFW Remittances | 0.646 | 0.00 | 0.296 | −0.051 (worse) | 0.54 |
| + Fish Kill | 0.646 | 0.00 | 0.282 | −0.036 (worse) | 0.54 |
| + all five | 0.677 | 0.12 | 0.259 | −0.010 (p 0.53) | 0.69 |

**No driver improves the two-quarter hunger forecast.** Three are worse than the latest reading. The ridge is fitted
on 6–10 regional pairs, and every driver except Climate is national or near-constant within a quarter.

**Learner ablation** (constrained LightGBM and logistic regression, exact five groups; issued rows only, 25 at
Lead 2):
- Market/Prices dominates at Lead 1: logistic regression on Market alone scores 0.87.
- At Lead 2, the single-group models on Fish Kill and Climate score 0.68–0.80 on 25 rows. That is 5 quarters, after
  the 2024 HIGH episode, so it is not evidence.
- Every learner still issues only 20–30 of 65 rows.

**HUN-RW at Lead 2** reaches 0.800 on its 60 issued rows but 0.738 on all rows, with HIGH recall 0.38. It does not
pass. The Brier score is worse than climatology (0.249 vs 0.219).

## 4. Status against the acceptance gate

| Requirement | Status |
|---|---|
| > 75% Lead-2 accuracy on a genuine food-insecurity outcome, beating baselines | **Not met** (best T43 0.738; regional hunger: persistence 0.69 vs always-HIGH 0.77) |
| Defensible food-insecurity outcome | SWS regional hunger, now face-validated by FNRI FIES. Provincial or municipal outcomes need requests A–C. |
| Five drivers investigated | Done. All five reach training and inference. Only Market/Prices carries predictive signal. Fish Kill now has a dated event dataset. |
| News evaluated | Headlines, lead text, event clusters (E83) and GDELT (E85): no forecasting gain |

**Exact blocker.**
- There are 12–13 independent target quarters of one regional hunger series, and no published variable anticipates
  its 2023–24 jumps.
- The Lead-2 gate needs a better-measured outcome (C: CALABARZON hunger microdata; A: CBMS; B: FNRI provincial), or
  more quarters accumulating prospectively.
- The sealed forecasts (E83, E84) will be the first unseen test in 2027.
