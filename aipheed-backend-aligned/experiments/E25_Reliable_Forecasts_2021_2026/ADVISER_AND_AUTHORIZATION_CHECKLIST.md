# One-page checklist: adviser decisions and researcher authorizations (E25)

## Adviser decisions (see `ADVISER_APPROVAL_REQUEST.md`)

- [ ] **D1.** Replace C1–C6 with the proposed P1–P6 (proper scoring rule, pooled leads)? Under both sets the T1 goal is **not met**.
- [ ] **D2.** Definition of "reliable lead" (Objective 2-V, SOP Q2, H2): the E23 rule or P6. Under both: **none**.
- [ ] **D3.** Keep the evaluability rule (≥ 8 dates, ≥ 5 HIGH, ≥ 5 LOW)?
- [ ] **D4.** Keep reading A (production SWS rounds only) as primary; readings B/C as sensitivity?
- [ ] **D5.** Keep the approved training-window-median threshold?
- [ ] **D6.** May the exploratory provincial target (D > 0) be reported as supporting evidence for the provincial layer only?
- [ ] **D7.** Approve the H4/H5 decision rules **before** any DA response is collected.

## Researcher authorizations (see `AUTHORIZATION_REQUEST.md`)

For each item, supply the file and its full SHA-256.

- [ ] **A1.** SWS September 2026 round (Balance Luzon) + publication date. Needed for the 2027-Q1 forecast and to score 2026-Q3.
- [ ] **A2.** Provincial food CPI YoY, July–September 2026, + release dates. Needed for the 2027-Q1 forecast and to score 2026-Q3.
- [ ] **A3.** Provincial food CPI YoY, October–November 2026 + release dates (T2 price pressure).
- [ ] **A4.** Q4 2026 news and 2026 government indicators (only for the Chapter I feature baselines).
- [ ] **B2.** SWS December 2026 round + CPI October–December 2026. Needed to score the sealed 2026-Q4 forecasts, including E25 FINAL_T1.
- [ ] **B3.** SWS March 2027 round + CPI January–March 2027. Needed to score the sealed 2027-Q1 forecasts.
- [ ] **C1.** Verified publication dates of the March and June 2026 SWS rounds (optional).
- [ ] **C2.** PSA 2021 municipal SAE workbook (126 LGUs lack a municipal poverty estimate).
- [ ] **C3.** Confirm the use of the public PSA 2021–2025 CPI index file (A6).
- [ ] **C4.** PSA's published 2021 monthly provincial food YoY (optional; extends the monthly evaluation to 66 months).
- [ ] **C5.** Decide whether `features_fused.parquet` may be read with a 2021+ read-time filter. It also holds 2020 rows; without it, no feature baseline can run.

## Participant work (H4, H5)

- [ ] Build the Google Form from `instruments/QUESTIONNAIRE.md`.
- [ ] Record the dashboard build (`dashboard_dev/dist-e25`), the record hash and the ranking-file hash.
- [ ] Run sessions with the 50 DA Region IV-A evaluators (`instruments/CONSENT_AND_FACILITATOR_GUIDE.md`).
- [ ] Score with `instruments/score_responses.py` on the unedited Forms export.
- [ ] Until then, H4 and H5 = **awaiting participant data**.

## Housekeeping (yours to decide)

- [ ] **E23 stash.** E23's 16 modified tracked files are in `stash@{0}`; they need a keep/revert decision.
- [ ] **Commit status.** E25 is uncommitted on branch `ui/no-data-quarters-risk-band` (nothing committed, pushed, merged or deployed).
