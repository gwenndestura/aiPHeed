# Sealing plan: quarterly post-SWS Lead-2 forecasts (specification only; not built)

**Purpose.** Produce sealed, prospective evidence for Lead 2 issued after the SWS release (M0 from `LEAD2_POST_SWS_ISSUE`, and M2 from this study). This is the only remaining route to confirming either, because no further variant will be tested on the 2023–2026 rows.

**Start.** The first SWS release of 2027: the **2026-Q4 round**, expected in mid-January 2027. That is the first on-time issue, with **origin 2026-Q4 and target 2027-Q2**, issued on the day after that release.

**Optional late seal before the start.** Origin 2026-Q3, target 2027-Q1, specified in §2a. It is reported separately from the on-time seals.

**What is not changed:**

- the existing P0H4 seal `a498b5ef` (one issue, 2026-10-01, Lead-2 target 2027-Q1), and the e2bef0b2 and Y16 `208b5754` seals;
- the served system, Lead 1, R1–R7, the 0.50 threshold, and the dashboard's "experimental" label for Lead 2.

## 1. Issue date per origin quarter t

O'(t) = max(first day of quarter t+1, min(P(t) + 1 day, quarter end + 67 days)), where P(t) is the publication date of the last Balance Luzon SWS round fielded in quarter t. This is the rule frozen in `LEAD2_POST_SWS_ISSUE`.

| Situation | Action |
|---|---|
| Round published by the cap | Issue on P(t) + 1 day |
| No round by quarter end + 67 days | Issue on the cap date with the newest round already published. Log "capped" |
| Round published before quarter end (as in 2025-Q1) | Issue on the first day of quarter t+1 |

## 2. What the sealing step must do

1. **Pin the code:** record the git commit and the SHA-256 of every runner file used, including `LEAD2_POST_SWS_ISSUE/runner/score.py` and `LEAD2_POST_SWS_PRICE/runner/price_refit.py`. Any later change to them voids sealing until a new plan is frozen.
2. **Snapshot the inputs** as of O'(t):
   - SWS rounds published before O'(t), with publication date and source URL;
   - PSA provincial CPI up to the newest month available at O'(t) (month M from the first day of M+2), with the release date of each month;
   - news, climate and the other served inputs exactly as the served system holds them at O(t).

   Store each snapshot file with its SHA-256.
3. **Compute**, for the five CALABARZON provinces (target t+2):
   - M0 = H4(O') × P0_price;
   - M2 = H4(O') × P0_price' (CPI cutoff at O');
   - the baselines at O': persistence (newest SWS and CPI), climatology, always-LOW.
4. **Write one sealed CSV:** `sealed_post_sws_<origin>.csv`, with one row per province and model. Columns: origin, target, issue date O'(t), probability, HIGH/LOW at 0.50, newest SWS round and its publication date, CPI cutoff month, and the code and input hashes.
5. **Seal before any outcome:**
   - compute the SHA-256 of the CSV;
   - append it, with the UTC time, to an append-only `SEAL_LOG.md`;
   - commit it, or otherwise timestamp it outside the machine (for example an email to the thesis adviser, or an off-machine backup with its own timestamp), before the first SWS round of quarter t+2 is fielded.

   The seal must exist well before the outcome is known: the target round is published about 0–84 days after quarter t+2 ends.
6. **Resolve later:** when the SWS round and CPI quarter for t+2 are published, record T43c per province with the source dates, in a separate `outcomes.csv`. Never edit a sealed file.

## 2a. Optional late seal: origin 2026-Q3, target 2027-Q1

| Item | Value |
|---|---|
| Issue date | O'(2026-Q3) = **2026-10-15**: the 2026-Q3 Balance Luzon round (H 23.6) was published on 2026-10-14 (`rlib.rounds`; checked read-only) |
| SWS | Only rounds published before 2026-10-15; the newest is 2026-Q3 |
| CPI | Only months available at 2026-10-15 under the month-plus-2 rule, i.e. up to **2026-08**, as published before 2026-10-15. Any later revision of those months, and any newer month, is excluded |
| Other inputs | As the served system held them at O(2026-Q3) = 2026-10-01, exactly as for every other origin. Nothing published on or after 2026-10-15 is used |
| Computation | The same as §2 steps 1–4: M0, M2 and the baselines at O'. Each input snapshot is filtered by publication date < 2026-10-15, and its SHA-256 is recorded |
| File | `sealed_post_sws_2026-Q3_LATE.csv`, with an extra column `sealedAfterIssueDate = true` |

**Disclosure (must appear in the seal log and in every report).** This forecast was sealed **after its issue date** (2026-10-15), using only inputs published before that date. The seal must be made before any 2027-Q1 outcome exists: no later than 2026-12-31, before any 2027-Q1 SWS fieldwork. A late seal cannot rule out that knowledge of events after 2026-10-15 influenced it, so:

- it is **reported separately** from the on-time seals;
- it is **not counted** toward the ten resolved quarters in §3.

**Relation to the existing seal.** The P0H4 seal `a498b5ef` (issued 2026-10-01, same target 2027-Q1) is unchanged and remains its own record. The late seal does not replace or edit it.

## 3. Evaluation once enough quarters are resolved

- **Pre-registered:** R1–R7 at 0.50 on the sealed rows only, with persistence and climatology as sealed alongside.
- **Minimum:** about 10 resolved on-time target quarters, i.e. 50 province-quarters. The first target is 2027-Q2; the tenth is 2029-Q3. It is resolved around late 2029: the 2029-Q3 SWS round is expected 0–84 days after quarter end, and September 2029 CPI is available from 2029-11-01.
- **Late seal:** the 2026-Q3 late seal (§2a) is scored and reported on its own and is excluded from this count.
- **Reporting:** report M0 and M2 separately. Neither counts as the original Lead 2 (issued at O(t)).
- **Gaps:** a quarter missed or sealed late is reported as missing, never back-filled.

## 4. Operational risks to plan for

| Risk | Plan |
|---|---|
| A commissioned or non-standard SWS round | Use the same round rule as `rlib.rounds` (non-commissioned BL rounds) and log the choice |
| PSA CPI rebasing or revisions | Snapshot the as-published values; never use later revisions |
| Holder availability | Name the person responsible for each quarter's seal, and a backup person, so a release is not missed. The sealing step takes about 30 minutes once the code is pinned |
