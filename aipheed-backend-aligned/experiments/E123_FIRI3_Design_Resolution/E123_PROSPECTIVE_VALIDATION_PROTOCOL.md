# E123 prospective validation protocol (FIRI3 v1.2)

**Code.** `runner/prospective.py`, tested in `backend/tests/unit/test_e123_firi3.py::test_prospective_snapshot_immutable`.

**Purpose.** A descriptive prospective record of FIRI3 beside FIRI v2. It is **not** a predictive validation, and **not** the thesis model comparison.

## 1. First origin

| Item | Value |
|---|---|
| Origin | **2026-Q4** |
| Issue date | **2027-01-01** |
| Earliest run | On or after 2027-01-01. `issue_snapshot()` refuses earlier, because releases between now and the issue date would be missed. |
| Data | The E119 inputs refreshed with every release published before 2027-01-01. No observation is fabricated or pre-filled. |
| Status today (2026-10-31) | **No prospective snapshot exists, and none can be issued yet.** The 23 snapshots in `snapshots/` are **retrospective** (2021-Q1..2026-Q3). |

## 2. Snapshot contents

`prospective/<origin>/` is written once and never overwritten:

| File | Contents |
|---|---|
| `scores.csv` | Per province and region: issue date, unit, FIRI3 overall, band, the six indicator scores, CCS (+ band), SVS (+ position), fixed core, cross-province core, indicators used and missing, completeness, verification share, leave-one-out range, contributing features, and the served FIRI v2 value where one exists |
| `features.csv` | Every feature: raw and aligned value, observed period, availability date, publication / verification status, prior count, score, dataset id |
| `indicators.csv` | Component scores, components available and defined |
| `manifest.json` | Origin, issue date, `kind = prospective`, issued-on date, FIRI3 version, protocol / Amendment 1 / Amendment 2 SHA-256, SHA-256 of every source dataset, and file hashes |

## 3. Later data

- **Revisions or late releases.** `record_observation()` recomputes the same origin and writes `observation_<date>.csv` and `comparison_<date>.csv` **beside** the snapshot.
- **The snapshot is never modified.** `verify()` checks every file against its manifest, and `record_observation()` refuses to run if a snapshot fails that check.

## 4. Each quarter, compare (descriptively)

| Comparison | Measure |
|---|---|
| FIRI3 vs FIRI v2 | Score level, band, province ranking, coverage, completeness, verification share |
| Stability | Change from the previous prospective snapshot; split into feature change and availability change |
| Indicator contributions | Shares and pushes, as in E123 |
| SWS | When the SWS round for the issue quarter and later is released: Spearman of the regional FIRI3 / CCS with SWS Balance Luzon, **described only**. SWS is never used to tune weights, thresholds, indicators or past snapshots. |

**What cannot be claimed:**
- predictive validity from one or a few quarters;
- provincial validation (no provincial outcome exists).

## 5. Before the first issue

1. Refresh the E119 inputs (CPI, prices, production, LFS, remittances, NASA POWER, IBTrACS, GDELT, news corpus), keeping their raw-file hashes.
2. Keep FIRI3 frozen at v1.2. Any change needs a new amendment approved before the issue.
3. Record the FIRI v2 value served for the same origin.
4. Run `issue_snapshot("2026-Q4", …)` on or after 2027-01-01, then `verify()`.

## 6. Separation from the thesis

The thesis model comparison is a separate experiment, not done here:
- proposed LightGBM;
- naive persistence;
- PSA-only;
- NLP-only;
- logistic regression.

FIRI3 is **not** a ground-truth label and does not validate provincial supervised forecasting.
