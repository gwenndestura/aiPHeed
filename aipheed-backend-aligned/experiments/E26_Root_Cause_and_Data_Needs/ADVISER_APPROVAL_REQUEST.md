# Adviser approval request (E26)

**Nothing below has been applied.**

- The approved target, S1 = H + 2D > τ (reading A), is unchanged.
- Criteria C1–C9 are unchanged.
- Each request lists what changes if approved and what stays the same.

**Evidence:** `ROOT_CAUSE_ANALYSIS.md`, `runs/horizon.json` and `runs/local_power.json`.

## R1. Amendment A1: the claim test for C9 (unseen quarters)

**Request.** Replace the frozen e-process claim rule with a **single pre-registered look**, defined in `PROTOCOL_AMENDMENT_A1.md` (hashed 2026-10-14T01:22:57Z, before any unseen outcome exists):

- The look is taken at the first year end at which the unseen record holds ≥ 12 scored dates, ≥ 5 HIGH and ≥ 5 LOW rows.
- The test is a one-sided exact sign-flip against **each** of persistence and calibrated persistence; a claim needs p < 0.025 against both.
- There is exactly one look. A failed look means "not established".

**Why.** The frozen e-process cannot reach its threshold before 2031 even for a forecaster that knows the true parameters (P = 0.000 in every scenario). Its bets are capped at 0.5 because a date can cost up to 1, so it needs about 75 dates at a steady advantage of 0.1. This is a defect of the test, not evidence about aiPHeed.

**Implemented** (`backend_dev/app/quarterly/ledger.py`, tested):

- The look time cannot be chosen. The look needs every sealed target up to that year end resolved, either as an outcome or as a final "no outcome" declaration.
- A second look is refused.
- The e-process remains as a monitor.

**What A1 does not do.** It does not make a claim likely. For a correctly specified model, P(accuracy claim by 2031) = 0.030.

## R2. Count a measured local outcome as evidence for Objective 3 (rankings) and Objective 5 (face validity)

**Request.** Approve reporting the agreement between aiPHeed's LGU and provincial orderings and an authorized local food-insecurity outcome, using `local_validation.agreement` / `attribution`:

- **CBMS 2024 (and 2022) FIES**, for 142 LGUs;
- **NNS 2023 FIES** by province;
- **PSA subsistence incidence** 2021/2023.

**How it would be reported:**

- as **additional** evidence on how well the rankings reflect relative vulnerability (SOP Q4);
- always beside the density-only and poverty-only orderings;
- **never as a substitute** for the DA evaluators' assessments (H4).

**Why.** No local outcome exists in the authorized data, so the rankings cannot currently be checked against anything measured.

## R3. Target improvements (options; none is applied)

| Option | Change | Effect | Cost or risk |
|---|---|---|---|
| R3a | Present the **two layers** separately in the thesis: regional risk P(H > τ) and the constructed provincial differential. S1 stays the approved composite. | Stops the provincial price term being read as a measured provincial food-insecurity difference (it is transient: between-province variance 0). | None to the target. Display only (already in the backend output). |
| R3b | **Auxiliary evaluation across SWS areas** (NCR, Balance Luzon, Visayas, Mindanao; data O5(d)) of whether the method anticipates hunger changes | About 4 times as many dates for the *method*; the approved T1 claim is unchanged | Area series are correlated (national shocks), so the effective gain is smaller. Needs authorization of the area series. |
| R3c | A **CALABARZON-specific H** tabulated from SWS microdata (O5(c)) | A regional outcome that matches the study area | Changes the approved H source. A smaller subsample means more noise. Depends on whether the microdata identify CALABARZON. |
| R3d | Score H forecasts with a **continuous proper score** (CRPS of the H forecast vs a random walk), beside the binary label | Uses the size of hunger changes, not only threshold crossings, so each date carries more information | A new criterion, so it needs approval. It does not replace C1–C9. |

## R4. NNS 2019 in Objective 5 conflicts with the study window

Objective 5 names "DOST-FNRI NNS 2019 and 2023 CALABARZON prevalence figures". The hard rule for this work allows **2021–2026 data only**, so NNS 2019 is **not used**.

**Request.** Confirm that the anchor uses NNS 2023 (and the in-window ENNS 2021 round, if any CALABARZON domain is in it), or rule otherwise.

## R5. Still pending from E25

- P1–P9 (proper scoring rule on pooled leads): E25 `ADVISER_APPROVAL_REQUEST.md`.
- A Brier claim under A1 counts only if P2 is approved.

---

## Researcher decisions (not the adviser's)

| Decision | Options |
|---|---|
| Where the operational ledger lives | The development ledgers are in `runs/ledger/` (E25 seal registered; no outcome). The production backend was not modified. |
| Authorizations | `MISSING_OBSERVATIONS_SPEC.md` O1–O8 |
| Requests to LGUs, FNRI, PSA RSSO IV-A and SWS | Letters or FOI requests. E26 does not contact anyone. |
