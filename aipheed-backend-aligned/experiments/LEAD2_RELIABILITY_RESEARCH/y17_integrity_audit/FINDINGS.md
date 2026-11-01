# Y17 findings: integrity audit of Y16

**Audited:** `y16_kalman_prospective/` (plan sha `208b5754…`), plus the model code it imports (`common/hmodels.py`, `runner/rlib.py`).

**Evidence:** `tests/test_adversarial.py`, 56 test cases (`TEST_RESULTS.md`), and code reading.

**Classes:**

- **DEFECT**: confirmed defect;
- **RISK**: potential risk;
- **LIMIT**: limitation of the registered design;
- **OK**: verified sound.

"Fix before 2027-01-01" means it must be corrected before the first valid issue.

## Verified sound (no action)

| ID | Area | Finding | Evidence |
|---|---|---|---|
| OK1 | Plan hash | SHA-256 of `EXPERIMENT_PLAN.md` = `PLAN_SHA256.txt` = `208b5754…6bd9699`. The plan was written at 14:17:39Z, and its hash and time were recorded at 14:17:41Z. Every Y16 code file is later (14:18:34Z onward). | `test_A1`, `test_A2`; file times |
| OK2 | Plan enforcement (normal mode) | `kprospect.plan_sha()` raises on a changed plan. It is called by `issue_seal` (issue.py) and `evaluate.evaluate`. | `test_A3` |
| OK3 | Plan ↔ code | Target > 11.3, threshold ≥ 0.50, target = origin + 2, schedule on the first day of each quarter, 120-day resolution, the 20 / 8 stage sizes, and the superiority rule (bootstrap p < 0.05 **and** CI95 upper < 0 **and** sign-test p < 0.10) all match the plan. | `test_A5`, `test_E8`, code reading |
| OK4 | Target mapping | Derived from the issue date (`origin_of` → `R.issue` round trip), not hard-coded. 2027-01-01 → origin 2026-Q4 → **target 2027-Q2**, checked for every issue date 2027–2032. | `test_B1` |
| OK5 | Manila window | Valid from 2026-12-31T16:00:00Z (01-01 00:00 Manila) to 2027-01-08T15:59:59Z (01-08 23:59:59 Manila). Invalid one second before and one second after. | `test_B2` |
| OK6 | Invalid CLI dates (normal mode) | 2027-01-02, 2027-02-01, 2027-13-01 and "not-a-date" are all rejected | `test_B3` |
| OK7 | No future data | Rounds published on 2027-01-01 or later (date-only or datetime) do not change the 2027-01-01 forecast. A round published 2026-12-20 is used. Both models share the origin, target and cutoff. | `test_B6`, Y16 tests, `test_C2` |
| OK8 | Model parity | Y16 calls `rlib.forecast("BL", t, 2, (NCR, BL, VIS, MIN))["RW"]` and `hmodels.kalman("BL", t, 2, same)`, the same calls as Y15. Values match Y15 to < 1e-4. Results are deterministic across separate processes. | `test_C1`, `test_C5`, Y16 parity test |
| OK9 | Persistence | Uses only the newest eligible BL quarter. A reading of exactly 11.3 gives Φ(0) = 0.5, which is HIGH at ≥ 0.50 (as the plan notes); the PERSIST auxiliary uses > 11.3. | `test_C3` |
| OK10 | Conventions | The minimum history (8 known quarters per area for the fit; 8 for BL to forecast), missing-quarter bridging, MoE → variance, and the commissioned-round asymmetry all match the plan and the Y16 audit | code reading |
| OK11 | Exact duplicates of project rounds | Ignored (not double-counted) | `test_D4` |
| OK12 | Input hashes | Seals hash both SWS source files and the overlay, and record SHA-256s of `hmodels.py`, `rlib.py`, `kprospect.py` and `issue.py` | `test_D6` |
| OK13 | Evaluation arithmetic | Paired d = Brier(KAL) − Brier(PERS), so negative favours Kalman. The CI and the superiority direction are consistent. Sign test counts KAL-better among non-zero d. Confusion matrix verified by hand. AUC, balanced accuracy and specificity are `None` when only one class is present. Seven rules estimable on 20 synthetic rows; R1 = FAIL at 20 rows; PERS R5 = undefined. | `test_E2`, `test_E3`, `test_E7`, Y16 tests |
| OK14 | Resolution | An outcome is unresolved before quarter end + 120 days (2026-Q2 resolves 2026-10-28, not 10-27). A resolved quarter with no round is `NaN` and listed as `missingOutcome`. | `test_E1` |
| OK15 | Real artefacts | `prospective/` is empty. The real overlay is header-only. The single dry run is registered `validProspective=False` and is excluded from evaluation. | inspection; Y16 test |

## Findings

| ID | Class | Severity | File / function | What and evidence | Impact | Fix before 2027-01-01? |
|---|---|---|---|---|---|---|
| **F1** | DEFECT | Medium | `kprospect.py`: `plan_sha`, `origin_of`, `read_overlay`, `load_seals`; `evaluate.py` | Every integrity check is an `assert`. Under `python -O` they disappear: a changed plan is accepted (`test_A4`), and 2027-01-02 is accepted as an issue date (`test_B4`). Overlay validation and seal tamper detection disappear the same way. | Silent loss of plan enforcement, date validation and tamper detection if anyone runs with `-O` or `PYTHONOPTIMIZE` | **Yes** |
| **F2** | DEFECT | Medium | `kprospect.read_overlay` | No validation of value ranges or provenance. All of these are accepted (`test_D1`, 8 cases): <br>• H = 150 or −3 <br>• MoE = −4 <br>• quarter "2026-Q9" <br>• empty source URL <br>• empty entry time <br>• a 2027-Q2 round "published" in 2026-12 (before its quarter began) <br>• publication later than the recorded entry time | Typing errors or invented rows enter forecasts and outcomes unchecked. The claimed publication date is trusted only because it is present in the file. | **Yes** |
| **F3** | DEFECT | Medium | `kprospect.install_overlay` (`pd.Timestamp(published)`) | Dates are not required to be ISO. `01/12/2027` is silently read month-first as 2027-01-12 (`test_B7`). A timezone-aware date (`2026-12-31T20:00-08:00`) is accepted by the overlay, then **crashes** the forecast (`TypeError`, tz-naive vs tz-aware). It fails closed, with no leakage (`test_B8`), but **blocks issuance**. | A day/month swap can move a round across the cutoff or the 120-day resolution date. A malformed row can stop the issuance on the day. | **Yes** |
| **F4** | DEFECT | Medium | `kprospect.install_overlay` | Duplicates are checked only against the project series, not inside the overlay. The same row entered twice is counted twice: KAL changes from 0.99836 to 0.99539 (`test_C4`). | Forecasts and outcomes silently re-weighted | **Yes** |
| **F5** | DEFECT | Medium | `kprospect.install_overlay` | (a) An overlay row with the same area, quarter and published date as a project round but a **different value** is silently ignored (`test_D3`). <br>(b) A row with the same area and quarter but a different published date is silently **added** as a further round. That is legitimate for SWS's two-round quarters, but it is not reported. | Conflicts are resolved silently instead of being reported | **Yes** (report and refuse conflicts; list added same-quarter rounds in the seal) |
| **F6** | DEFECT | Medium | `evaluate.evaluate` / `main` | The primary analysis is recomputed and written again on every run, with no lock (`test_A6`). Because outcomes are recomputed from rounds published ≤ the resolution date, a round entered late, or an edited overlay, can **change the "primary" result between runs**. | Several "primary" analyses could exist, and one could be reported selectively | Before the first evaluation (not needed for issuing) |
| **F7** | DEFECT | High | `kprospect.issue_seal` | The seal stores the overlay's path and hash, **not the rows used** (values, dates, source URLs, entry times) (`test_D5`). Plan section 5 requires evaluation to check "that earlier rows are unchanged against the copy recorded in each seal". With no copy, that is impossible for any seal issued in this format. | Overlay provenance behind each forecast cannot be audited later. The plan's append-only check cannot be implemented retroactively. | **Yes** (the seal format must carry it from the first issue) |
| **F8** | DEFECT | High | `kprospect.load_seals`; `evaluate.evaluate` | (a) A registered seal whose file was deleted is not detected: the loop runs over files, not the registry (`test_D8`). <br>(b) A second valid seal for the same issue is silently dropped; the evaluation shows `validSeals: 1` (`test_D9`). <br>(c) Editing a seal **and** its registry line consistently goes undetected (`test_D7`, RISK). | Unfavourable forecasts could disappear, and re-issues are invisible: exactly the selective-reporting failure the study must exclude | **Yes**, for (a) and (b). For (c), see F9. |
| **F9** | RISK | High | `kprospect.issue_seal` (system clock / `now_utc`) | The write time comes from the local clock, or from any caller of the library (`test_B5`: a "valid" seal for the past 2026-10-01 window was created by passing `now_utc`). Nothing outside the machine attests when a seal existed. Commits are not allowed in this project, so git cannot serve as the timestamp. | Backdated or re-generated seals cannot be distinguished from genuine ones | **Yes**, procedurally: anchor each seal hash outside the machine on the issue day (see `RECOMMENDED_FIXES.md`) |
| **F10** | DEFECT | Low | `evaluate.py` | Calibration (bins; slope when n ≥ 10 and both classes), registered in plan section 5, is not computed (`test_E4`) | One registered statistic missing | Before the first descriptive evaluation (≥ 8 resolved quarters) |
| **F11** | DEFECT | Medium | `evaluate.evaluate`; `issue.py` | Missed issue windows are not enumerated or counted (plan section 5) (`test_E5`). An issuance that **crashes** (e.g. F3) leaves no record at all. | Missed or failed issues silently disappear from the record | **Yes**, for the failure log. The missed-date count can follow before the first evaluation. |
| **F12** | DEFECT | Medium | `evaluate.evaluate` | The registered overlay append-only check is not implemented: an overlay row edited after sealing goes undetected (`test_E6`). It depends on F7. | History can be rewritten silently, changing outcomes | Before the first evaluation (seal side: F7 before issuing) |
| **F13** | RISK | Medium | issuance window × overlay | The window runs to day 8, and SWS often releases in early January. A round published on, say, Jan 5 must be excluded. It is excluded if its date is entered correctly (OK7). But the cutoff relies entirely on the **claimed** date, which is not verified (F2). | A mis-dated January release could enter a forecast | Mitigated by F2, F3 and F7. Also recommended: issue on the first day of the window. |
| **F14** | LIMIT | Medium | plan section 5; `kprospect.paired` | The registered bootstrap resamples quarters independently. Quarterly hunger and the paired loss differences are serially correlated, so the CI may be too narrow and the p too small. | Possible overstatement of the evidence for superiority | No code change. **Recommend a formal amendment, before any outcome is seen**, adding a moving-block bootstrap as a reported sensitivity, without replacing the primary test. |
| F15 | LIMIT | Informational | plan | 20 quarters gives low power for a Brier difference of about 0.02. A null result would not establish equivalence. R1 (≥ 40 rows) is unreachable before about 2037. | Interpretation | No (already stated in the plan) |
| F16 | RISK | Low | `kprospect.issue_seal` | Python, numpy, scipy and pandas versions are not recorded. The Kalman MLE (Nelder–Mead) could differ slightly across library versions. `evaluate.py`'s hash is not recorded in the evaluation outputs. | Reproducibility | Recommended (cheap) |
| F17 | RISK | Low | `issue.py --overlay` | Any overlay path can be passed. The path and hash are recorded, but evaluation always reads the default overlay. | A forecast could be made from a non-canonical overlay | Recommended: restrict valid issues to the default overlay |
| F18 | LIMIT | Informational | `evaluate.main` | Uses `dt.date.today()` (machine-local) rather than the Manila date for resolution | Off by at most one day at the 120-day boundary | No |
| F19 | LIMIT | Informational | model (unchanged) | The BL 2021+ series includes the commissioned 2025-Q1 Stratbase round, while the other areas exclude commissioned rounds. The predictive variance adds the newest quarter's mean variance (halved for two-round quarters). Both are documented and kept to preserve the specification. | Specification detail | No (do not change: it is preregistered) |

## Summary

| Question | Answer |
|---|---|
| Plan hash | Matches, and is enforced in normal execution. Not enforced under `python -O` (F1). |
| 2027-Q2 mapping and Manila window | **Correct.** |
| Future-data leakage | **No leakage path in correct operation.** The publication-date cutoff holds, both models share it, and a timezone-aware date fails closed. The cutoff depends on claimed publication dates that are not validated or recorded in the seal (F2, F3, F7, F13). |
| Overlay and sealing against conflicts and tampering | **Not yet adequate:** <br>• double counting and silent conflict handling (F4, F5); <br>• no row-level provenance in seals (F7); <br>• deleted or re-issued seals invisible (F8); <br>• no external timestamp (F9). |
| Evaluation vs preregistered rules | The arithmetic and rules are correct (OK13, OK14), but three registered items are missing: calibration (F10), the missed-issue count (F11) and the overlay append-only check (F12). The primary analysis is not locked (F6). The registered iid bootstrap ignores serial correlation (F14, a limitation). |
