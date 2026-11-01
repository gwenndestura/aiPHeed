# Y16 runbook: Y18 addendum

This addendum supersedes the operational parts of `AUDIT_AND_RUNBOOK.md` section 5 where they differ. The model, target, schedule and analysis are unchanged.

## Overlay rows (`data/sws_rounds_overlay.csv`, append-only)

**Header, exactly:** `area,quarter,H,published,moe,source_url,entered_utc`

| Field | Rule |
|---|---|
| `area` | NCR, BL, VIS or MIN |
| `quarter` | `YYYY-Qn` |
| `H` | 0–100 |
| `moe` | greater than 0 and at most 15 |
| `published` | ISO date `YYYY-MM-DD` only. Never `DD/MM/YYYY`, no time, no timezone. It must not precede the quarter's first day. |
| `entered_utc` | `YYYY-MM-DDTHH:MM:SSZ`, on or after `published` |
| `source_url` | must start with `https://` |
| Whitespace | No surrounding spaces in any field |

**Rejected:**

- duplicate rows;
- conflicting rows (same area, quarter and published date with different values);
- a row with the same area, quarter and value as an existing round but a different date (probable duplicate);
- a row that conflicts with the project series.

An exact copy of a project round is ignored and reported. A genuine additional round in a quarter is accepted and reported in the seal.

**Never edit or delete a row.** Evaluation stops if a row used by a seal changes.

## Issue day (2027-01-01 .. 2027-01-08 Manila; best on the first day)

1. `python -B runner/issue.py --issue 2027-01-01`. This uses the canonical overlay and the system clock, and writes `prospective/`. Every attempt (failed or sealed) is appended to `prospective/ISSUE_ATTEMPTS.log`, and re-issues are refused.
2. **The same day:** send the printed one-line `ATTESTATION` payload (also in `prospective/attestations/`) to an approved independent recipient or timestamping service. The researcher chooses which.
3. Record the outcome: `python -B runner/attest.py --seal <seal file> --status completed --method "..." --evidence "..."`. Use `--status unavailable` with the reason if attestation could not be done. The status stays `pending` until recorded. It is never inferred.

## Evaluation

`python -B runner/evaluate.py`. It stops on any integrity failure:

- an inconsistent registry, or missing or unregistered seals;
- a seal not written with the system clock;
- a changed overlay row.

**Supplementary (registered reporting items):**

- missed issues and failed attempts;
- attestation status;
- calibration.

The primary analysis (at 20 resolved quarters) is written once to `out/PRIMARY_ANALYSIS.json`. Later runs must reproduce it exactly. The Amendment-1 block bootstrap is reported next to it and can never change a failed primary result into a pass.

## Do not

- run any Y16 script with `python -O` (it is safe since Y18, but unnecessary);
- pass `--overlay` for a real issue;
- copy, rename or hand-edit seal files or `SEALS.txt`.
