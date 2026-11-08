# As-of rule for the September 2026 CPI vintage (fixed 2026-10-29, before the province-wide variants are computed)

The SHA-256 of this file goes in `runner/ASOF_RULE_SHA256.txt`. It is committed before `runner/sept2026_asof_rule.py` is run.

**Status of this file.** This rule is not new. It restates rule 2 of `ADDENDUM_ROOT_CAUSE_RELEASE_DATES.md`:
- that addendum is frozen at 223369ca…;
- it was committed in d5ebf84 at 2026-10-29 09:48 PHT, before the September 2026 vintage was examined in 813293b;
- this file only spells the rule out for the rows sealed on 2026-10-28/29.

It changes no criterion, candidate, target, threshold or seal.

## Rule

1. **Unit.** One province-month. A Lead-2+ row has **one** CPI cut-off month, as in addendum rule 2. The food and all-items CPI of a province-month come from the same provincial CPI table and release, so they enter together. They are never split across months. A split, such as food at month m with all-items at m−1, produces a mixed-vintage gap that no training row has.
2. **Cut-off.** The newest reference month whose provincial release is shown by an official dated PSA source (addendum rule 1) to have been released **strictly before** the row's issue date. Under addendum rule 2, a release on the issue date itself does not count. So no intraday time is needed and none is assumed.
3. **Same rule everywhere.** The rule is applied identically to all five provinces and to Leads 2, 3 and 4. Lead 1 is issued at the quarter start with CPI through month 2 of the quarter, unchanged.
4. **Pending dates.** A province-month whose release date is owner-reported but not yet verified is `pending`. The forecast is reported under both possible outcomes of the verification. Neither is chosen.
5. **What does not set the cut-off.** Repository download timestamps are recorded as evidence that a value was public by that time. They are not release dates under addendum rule 1, so they do not set the cut-off. They are reported beside it.
6. **Scoring.** Addendum rule 5 and the protocol govern scoring. The sealed CR and CR-ANC files are scored as published. Any re-cut forecast, including the 2026-10-29 Rizal companion, is a separately labelled diagnostic record. It is not the counted forecast, because no frozen document authorizes counting it.
7. **Results do not choose the rule.** The class (HIGH or LOW) of any row under this rule is reported whatever it is. No other cut-off is substituted after seeing it. Other cut-offs are shown only as labelled sensitivities.
