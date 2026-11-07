# E180: leakage and temporal audit

| Check | Status | Evidence |
|---|---|---|
| Future survey outcomes in training | **VERIFIED none** | `app/e150/model.released(i)`: a round enters training only `ANCHOR_LAG` quarters after its reference quarter; the corruption test (unreleased rounds randomised) changes no E168 output (0.0) |
| Future SWS in the temperature shrink | VERIFIED none | SWS quarters published on/after the cut-off randomised → 0.0 change (E168, E171, E172, E173) |
| Feature as-of rules | VERIFIED (code) | `gov_row(key, q_start(i))` builds inputs as of the issue quarter; SWS inputs use `published < q_start(i)` (unit test `test_sws_inputs_ignore_quarters_published_after_the_issue_date`) |
| Issue / anchor / outcome order | VERIFIED | E178 audit: issue < outcome quarter, anchor < issue, lead = outcome - issue for all 156 untainted rows |
| Calibration / selection on held-out labels | VERIFIED none for E168 | Selection, calibration and lambda are fitted on training rows (region folds or forward rounds) |
| Data vintages (revisions) | **UNVERIFIED (MEDIUM, I12)** | CPI, production, LFS and remittance series are current releases; historical issue dates would have seen earlier, possibly revised, values. Not reconstructible from the repository |
| Repeated use of the 72 evaluation rows | **VERIFIED risk (HIGH, I06)** | About 29 experiments (E151-E179) evaluated on the same 72 rows; any result chosen after seeing them (SIMPLE, E172 diagnostics, E179 BEST72) is selection-biased, not held-out evidence |

No concrete leakage of future outcomes or future features was found in the E168 forecasting path.
