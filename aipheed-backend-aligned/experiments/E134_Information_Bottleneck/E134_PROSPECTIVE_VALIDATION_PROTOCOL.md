# E134 prospective validation protocol (frozen 2026-11-01)

**Purpose.** To evaluate the E134 candidate on SWS quarters that were **not** used for feature selection, model selection, tuning or comparison: 2026-Q4 onward. Every earlier quarter was seen.

## Frozen elements

| # | Element | Frozen value |
|---|---|---|
| 1 | Candidate | **HFM-X** (E133 `runner/e133_models.py` + `e133_run.py`, commit `56d1ec1`). Selected by the E134 rule. |
| 2 | Registered hypotheses scored alongside | **E134-ONI** (= E133 PH2: ONI as the climate driver; post-hoc origin disclosed); E134-AREA-T; E134-AREA-O; E134-ENS |
| 3 | Features | HFM-X: rice CPI q/q (A), typhoons in PAR (C), unemployment change (E), GDELT shortage share (N), poverty × market (V), SWS history (H). ONI and area drivers only in the registered hypotheses. |
| 4 | Preprocessing | In-fold standardization at each issue; publication rules as in the leakage audit; 2021+ only |
| 5 | Issue policy | **P-DASH**: first day of each quarter. P-REL is not part of this protocol; adopting it needs owner approval. |
| 6 | Re-issue | At each quarter start, refit on rounds published before it, forecast Leads 1–4, and append (write-once) to `sealed/E134_REISSUE_<quarter>.csv` with its sha256 (`python -I runner/e134_reissue.py <YYYY-MM-01>`). Before each re-issue, re-run the acquisition scripts (E131 CPI, E133 B30, E134 POWER/palay, E119 drivers) with data published **before** the issue date, and log any driver that could not be refreshed. Such a driver is held at its last value by the frozen rule. |
| 7 | Tolerance | \|forecast − SWS\| ≤ 1.645 × SE (binomial SE from published margins). **Primary only.** |
| 8 | Reliability | N1–N7 unchanged (`e130_lib.numeric_reliability`) |
| 9 | Forecast generation date | First seal 2026-11-01 (`sealed/E134_PROSPECTIVE_SEAL.csv`, sha256 `e4f844dd…`; targets 2026-Q4 … 2027-Q3). Later re-issues on 2027-01-01, 2027-04-01, … |
| 10 | Scoring | `python -I runner/score_e134.py`. It verifies the seal hash, accepts only quarters after 2026-Q3 from `E131_Objectives_Resolution/data/sws_rounds_after_2026Q3.csv`, and writes append-only outputs. |
| 11 | Minimum sample | **≥ 10 unseen Lead-2 target quarters** (≥ 40 area rows) before any adoption decision |
| 12 | Adoption | ≥ 75 % within tolerance **and** N1–N7 at Lead 2 on the unseen quarters, then owner approval and a separate integration branch |

## Timetable

- **First unseen target:** 2026-Q4, published by SWS around January 2027.
- **The tenth Lead-2 target quarter is 2029-Q2 at the earliest**, so the earliest adoption decision is in 2029-Q3. Missing SWS quarters (as in 2022-Q1 and 2025-Q1) push this back by one quarter each.

## Prohibitions

- No change to the candidate, features, priors or rules after a prospective outcome is seen. Any such change starts a new protocol, whose clock restarts.
- Prospective results must not be reported as development evidence, or the reverse.
- E131, E132 and E133 seals are scored with their own scorers, unchanged.
