# E70 action plan: audit finding → change → test → acceptance criterion

**Start point:** `FINAL_OBJECTIVES_AND_MODEL_VALIDATION_AUDIT.md` (2026-10-20, commit 2c88d9f on `final-system-v2`).
**Branch:** `e70-objectives-completion`, cut from `final-system-v2` @ 2c88d9f. Production default (E38) and the thesis-mode default are not changed.
**Library pin:** the model code path (E40 → E41 → … → E56 → E63) is read from a clean `git archive` of `origin/final-thesis-system` @ `089bdf2`, never from the main checkout, which has uncommitted edits.

| # | Audit finding (section) | Change / method | Test | Acceptance criterion |
|---|---|---|---|---|
| F1 | T43 equals food-price pressure on all 205 rows (§2) | `e70_target_audit.py`: per row, whether the hunger condition was binding; prevalence under every 2021–22-anchored hunger threshold; approved-rounds variant | `tests/test_e70.py::test_target_audit` | The report states the label class for every lead (direct / proxy / price-dominated). No threshold is changed after seeing results. |
| F2 | "Food insecurity" vs "price pressure" wording (§2, §4) | Each result table names its target; the direct regional SWS outcome is scored separately and never per province | Report review; API text check | No table calls a price-pressure result a validated food-insecurity forecast |
| F3 | Lead-2 accuracy 0.72, 8 HIGH missed, 4 of them in 2024-Q2 (§3.1) | Error decomposition: hunger-component misses vs price-component misses | `e70_score.py` error table | Every missed HIGH is attributed to a component |
| F4 | Over-confidence, calibration slope 0.55 (§3.1) | Arm A2 SHRINK: training-only logit shrinkage of the price component | Walk-forward on identical rows; calibration slope | Pre-registered rule in PROTOCOL §6 |
| F5 | Configuration instability, 9 configurations in 10 origins (§5.2) | Arm A1 STABLE: configuration chosen by cumulative training-only inner log-loss across origins | Same | PROTOCOL §6 |
| F6 | How much is price projection alone? (brief §6) | Arm S0 STRUCT: base-effect CPI projection only, no trees | Same | Reported, not a candidate |
| F7 | Contribution of each evidence group, news value (§7 Obj 1, brief §6) | Ablations −climate, −fish_kill, −employment, −ofw_remittance, −news, −policy; single-group models | Same rows, paired Brier | Reported; a group "adds value" only if removing it worsens Brier with a quarter-cluster CI above 0 |
| F8 | Persistence / majority / climatology / Obj 4 baselines (§7 Obj 4) | Same rows, same issue dates, quarter-cluster bootstrap, two-sided sign test, McNemar, Holm | `e70_score.py` | Credible advantage only when CI excludes 0 AND Holm-adjusted sign p < 0.05 |
| F9 | Effective n ≈ 23, repeated regional inputs (§6) | ICC, design effect and within-quarter AUC for every arm | `e70_score.py` | Reported beside every accuracy |
| F10 | Leakage cannot be excluded for new arms by assumption (§5.1) | Corruption test (all post-issue raw values randomised) for R0, A1, A2, S0 at 3 origins | `e70_leak.py` | Forecasts change by 0.0 |
| F11 | Development reuse of every quarter (§4, §8) | Disclosed; new arms SEALED for 2026-Q4 and 2027-Q1 before outcomes exist | Seal sha256 recorded | No historical number is called held-out |
| F12 | Clean-checkout reproduction not shown for the model (§10) | Re-run E70 from a fresh `git archive` of this branch + the pinned library export; compare file hashes | `REPRODUCTION.md` | Byte-identical predictions |
| F13 | Obj 1: AI annotations, unvalidated bias correction (§7) | Blind, stratified human-annotation sample (headline + empty label columns) + instructions; existing metrics re-run | `obj1.py` re-run; sample file | Human labels cannot be produced by Claude: status stays PARTIAL until the researcher labels the sample |
| F14 | Obj 3: 142 LGUs (§7) | Re-run `obj3.py` on this branch | `obj3.py`; backend tests | 142/142 finite, mapped, consistent |
| F15 | Dashboard honesty (brief §7) | Only if a candidate passes PROTOCOL §6: serve it behind a new flag. Otherwise text-only disclosure fields (no new UI elements, per the approved-design rule) | Backend + frontend tests, build | No new UI element; production default unchanged |
