# E134 Addendum 2 · Amended prospective primary (owner approval, 2026-11-01)

**Decision (owner, in chat):** "Approve amendment". This answers the E136 question: amend the E134 prospective protocol to make SEAS-LLM primary, with SIMPLE and HFM-X as challengers.

**Frozen 2026-11-01, before any prospective outcome exists.** SWS has published nothing after 2026-Q3, and the first re-issue is 2027-01-01.

## What changes

| Item | Before (E134 protocol) | After this addendum |
|---|---|---|
| Primary candidate | HFM-X | **SEAS-LLM** (E132 model, `E132_Final_Methodology/runner/e132_run.py`, `seas_forecast`) |
| Challengers | E134-ONI, E134-AREA-T, E134-AREA-O, E134-ENS | **SIMPLE** (E136: pooled level + rice CPI q/q, unemployment change, GDELT shortage share, prior SD 0.5) and **HFM-X**. The earlier E134 hypotheses stay registered and scored, as secondary. |
| First sealed forecasts | E134 seal `e4f844dd` | Primary: E132 seal `cea5a2ec` (SEAS-LLM). SIMPLE: E136 seal `9bccb2ec`. HFM-X: E133 seal `efba3235` / E134 seal `e4f844dd`. All were issued 2026-11-01. |
| Re-issue | `E134 runner/e134_reissue.py` | **`E136 runner/e136_reissue.py`**: SEAS-LLM, SIMPLE and HFM-X; write-once, `sealed/E136_REISSUE_<quarter>.csv`. The E134 re-issue may still be run for the secondary hypotheses. |
| Scoring | `score_e134.py` | **`E136 runner/score_e136.py`**: primary criterion only. It scores the 2026-11-01 seals and every re-issue for SEAS-LLM, SIMPLE and HFM-X, and reports N1–N7 once at least 10 Lead-2 quarters exist. |

## What does not change

- Target (SWS hunger, 4 areas), tolerance 1.645 × SE (primary only), 75 %, leads (`target.py`), N1–N7.
- P-DASH issue policy, point-in-time rules, 2021+ window (E134 Addendum 1).
- Adoption requirement: **≥ 75 % within and N1–N7 at Lead 2 on ≥ 10 unseen Lead-2 quarters**, then owner approval and a separate integration branch. Earliest decision: 2029-Q3.
- Production, the dashboard, FIRI and every seal file.

## Rules for the challengers

- A challenger can replace the primary only if:
  - it meets the adoption requirement on the same unseen quarters, **and**
  - the primary does not meet it.
- If both meet it, the primary stays.
- No candidate, feature, prior or rule may change after a prospective outcome is seen. Any change starts a new protocol and restarts its clock.
