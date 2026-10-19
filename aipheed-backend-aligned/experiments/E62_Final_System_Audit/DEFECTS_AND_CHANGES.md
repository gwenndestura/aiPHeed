# E62 defects, fixes and changed files

Committed locally at the user's request (2026-10-19) as separate E59–E62 commits. Not pushed, deployed or switched. The work is on local branch `e62-final-audit`, created from `e60-accuracy-optimization` at 88d5266. It carries the uncommitted E59–E61 working tree unchanged.

## Defects fixed in E62

| ID | Severity | Defect | Root cause | Fix | Test | Evidence the fix works |
|---|---|---|---|---|---|---|
| **D-E62-1** | Medium (explanation shows a counterintuitive direction without the caveat) | For 2027-Q1, Employment lowers P_price by −0.25 log-odds in **all five** provinces while national unemployment rose by 0.90 points. The "statistical pattern … not evidence that job losses reduce food stress" caveat appeared only for Cavite, Laguna and Quezon. Rizal and Batangas show an Employment bar (9% and 8%) as lowering the score, next to "+0.90 points", with no caveat. | `_forecast_caveat` checked only the *named reasons* (groups ≥ 10%), not every group drawn as a bar. | `dashboard.py`: the caveat follows every contributing group (`contributing`, status "contributes" and pct > 0). Backend text only; no UI element changed. | `test_e62_final_audit.py::test_employment_caveat_follows_every_drawn_bar`; `test_e61_forecast_context.py::test_employment_note_only_when_direction_conflicts` updated to the corrected rule | All 5 provinces now carry the caveat (test). The live local dashboard (E58 mode, port 8092) shows it for Rizal. |
| **D-E62-2** | Medium (evidence traceability, timing) | In E58 mode, the news beside the **2026-Q4 earlier forecast** (issued 2026-07-01) were 2026-Q3 articles, published *after* that forecast was issued. The note called them "Supporting news for the 2026-Q4 forecast … published by 2026-10-01". | `e31_news_evidence` always applied E31's one-quarter-ahead convention, even when a Lead-2 candidate governs the dashboard. | New `_lead2_news_evidence`: when a Lead-2 candidate governs, the evidence window follows the served estimate's own origin (news of q−2, published before the issue date). The E38 default path is untouched. | `test_news_beside_a_lead2_estimate_never_postdates_its_issue_date`; `test_e38_default_news_wording_unchanged` | 2026-Q4 now shows 2026-Q2 news (latest item 2026-05-25 < 2026-07-01). 2027-Q1 is unchanged (2026-Q3 news, before 2026-10-01). E38 mode is unchanged. |
| **D-E62-3** | Low (wording) | The back-test news note said "its one-quarter-ahead estimate was made with the previous quarter's news". That is wrong for a two-quarter-ahead estimate (E60 proposal P2, confirmed). | Same as D-E62-2. | Same function. The note now reads, e.g., "its two-quarter-ahead estimate was made as of 2026-04-01 with 2026-Q1 news". | Same test (OBSERVED branch) | Verified by the test and an API call. |

## Defects or weaknesses confirmed but not fixed (each needs a decision or new data)

| ID | Severity | Finding | Why not fixed in E62 |
|---|---|---|---|
| W1 | High (validity) | The target's gap condition counts a **non-food price surge as relief**. In 2026-Q2 and Q3, headline inflation was 4.6–8.0% against food 0.7–4.9%, and SWS hunger reached 23.6% (2026-Q3), yet every province except Cavite 2026-Q2 is LOW. | Changing the target is an adviser decision and must be scored prospectively. Changing it now would choose a target after seeing the outcomes. |
| W2 | Medium | The product P_hunger × P_price is **not a valid joint probability**. Dependence is shown: row-level Fisher p = 0.0008, quarter-level permutation p = 0.039. It is confounded with time: every low-hunger quarter falls in 2021–23. | Already relabelled a "model score … not a tested probability" (E61). The alternatives K1 and K2 did not improve (E61). The Fréchet bound means it cannot raise 2027-Q1 above P_price. |
| W3 | Medium | **Per-origin re-tuning switches configurations** (9 distinct over 12 origins). At 2026-Q4, configuration 68's non-price trees cut the log-odds by about −1.9 in three provinces; at 2027-Q1 the switch back to configuration 23 reversed it. | A modelling change (for example, freezing the configuration) must be evaluated on fresh data. Now documented as a source of forecast jumps. |
| W4 | Medium | The hunger part over-predicts: served ridge RMSE 8.2 vs random walk 6.1 (E61). | Changing the served model needs authorization. The change would *lower* 2027-Q1. |
| W5 | Low–medium | The hunger **input** uses approved SWS rounds only; the T43 **label** uses all rounds. At the 2026-01-01 issue date the input was 3 quarters old (2025-Q1), although the 2025-Q2 and Q3 supplementary rounds were published. | No decision effect in 2025–26 (P_hunger ≈ 1). Changing it would change the model. Documented. |
| W6 | Medium | **News leads are empty for every displayed article.** The corpus is titles only, and the feed says so ("Headlines only (the source gives no lead text)"). | Recovering leads needs a new web collection (resolving Google News redirect tokens, then fetching publisher meta descriptions). The 2026-10-14 authorization covers publisher pages, but the token-resolution step goes beyond it. A user decision is needed. Nothing is invented. |
| W7 | Low | The "Quarter-on-quarter change" is a **relative %**: Rizal shows **+898%** (0.005 → 0.050). The arithmetic is correct, but it is alarming on a near-zero base. | It is the approved UI's definition (glossary: "percentage shift"). Changing it is a design and semantics decision. |
| W8 | Low | Remittances (BSP) end in 2025-Q4. The 2027-Q1 trees route the missing value down a branch learned from 2021 rows. | This is disclosed in the sentence. The data refresh needs a manual BSP download (BSP blocks scripts). |
| W9 | Low | The legacy plain-report model bundle was pickled with scikit-learn 1.7.2 and is loaded under 1.8.0 (`InconsistentVersionWarning` in `test_plain_report`). | It is not on the E56/E58 path, and the tests pass. Re-export it, or verify its coefficients, before relying on that report. |
| W10 | Low | `tsc --noEmit` gives 6 errors, all in the untouched `src/data/mockData.ts`. There is also a 1.93 MB main JS chunk. | These are frontend changes, deferred under the no-design-change rule. Code-splitting would not change the look, but it needs your OK. |

## Files changed by E62

| File | Change |
|---|---|
| `backend/app/services/dashboard.py` | D-E62-1: caveat argument `reasons` → `contributing`. D-E62-2/3: new `_lead2_news_evidence`, called first by `e31_news_evidence`. The file also carries E61's uncommitted hunks, which are left as found. |
| `backend/tests/integration/test_e62_final_audit.py` | **New**: 9 tests (3 fixes and 6 consistency checks) |
| `backend/tests/integration/test_e61_forecast_context.py` | One assertion moved to the corrected rule (E61's file, uncommitted) |
| `.claude/launch.json` | Added the `aipheed-e62-stack` preview entry (API 8062 in E58 mode, frontend 8092) |
| `aipheed-backend-aligned/experiments/E62_Final_System_Audit/` | **New**: this audit (runner, tables, out, reports) |

**Not touched:**
- E56–E61 artifacts and protocols (21 freeze records verified, `out/r8_frozen_check.json`);
- `backend/data/`;
- the frontend source;
- the E46 D-1 hunks in `insights.py` and `e41_lead2.py`, which belong to another session.
