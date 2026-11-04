# Adoption decision: C-B6 becomes the main model (2026-11-04)

**Decision:** the team (project owner) made C-B6 the main model of aiPHeed's food-insecurity mode on 2026-11-04.
**Adviser approval: pending.**

## What the pre-registered rule said

`CB6_PREREGISTRATION.md` (2efd9677…) required all of:
- H7: Brier < C-b at both leads with one-sided p < 0.10;
- R1–R7;
- MRLT ≥ 2;
- accuracy ≥ 0.75;
- team and adviser approval.

| Criterion | Result |
|---|---|
| H7: Brier better than C-b | **Not met:** −0.0044 (p 0.13) and −0.0031 (p 0.20) |
| R1–R7 at Leads 1–2 | Met (rests on one changed forecast, origin 2018-Q3; `out/obj2_cb6_fragility.json`) |
| MRLT ≥ 2 | Met (2) |
| Accuracy ≥ 0.75 | Met (0.806 / 0.806) |
| Team approval | Given, 2026-11-04 |
| Adviser approval | **Pending** |

**This adoption is therefore a team decision that overrides an unmet pre-registered criterion (H7).** The thesis must
report it as such.

## Rationale given

C-B6 has the best development metrics of all candidates:
- accuracy 0.806;
- balanced accuracy 0.743;
- AUC 0.723 / 0.712;
- Brier 0.183 / 0.181;
- the only model passing R1–R7;
- 9 of 14 baseline comparisons proven.

## What changed

- **Backend:** `foodinsecurity_system.py` defaults to `backend/data/foodinsecurity_engine_cb6`. The C-B6 export's
  description fields now say "main model" (forecasts byte-identical).
- **Frontend:** the landing page and About dialog describe the served model from its own evaluation. C-b's wording is
  unchanged when C-b is served.
- **Registry:** `prospective_ce/REGISTRY_CE.json` records C-B6 as MAIN and C-b as the previous main model.

## What did not change

- **C-b, the previous main model:** its export (`backend/data/foodinsecurity_engine`), seal 67baec66, forecasts and
  prospective protocol (`SENIOR_REVIEW`) are unchanged. C-b is still sealed each quarter as the reference, and it can
  still be served (`AIPHEED_FI_DATA_DIR=…/foodinsecurity_engine`).
- **No result changed:** no model was refitted; no forecast, metric, baseline result or R1–R7 result changed.
- **The deployed site:** `render.yaml` and the Dockerfile are unchanged (deployed site: FIRI v2 default).

## Still required

1. **Adviser approval** of this adoption and of the disclosure wording.
2. **Prospective confirmation:** seal C-B6 and C-b from 2027-01-01 (`CE_PROSPECTIVE_ADDENDUM_1.md`, family P5:
   C-B6 vs C-b). If C-B6 is worse than C-b prospectively, this decision should be revisited.
