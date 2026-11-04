# C-B6E: C-B6 + employment (E1) + OFW remittances (E2) (pre-registration, fixed before any fit, 2026-11-04)

**Owner directive (2026-11-04):** "include it as model input", meaning employment and OFW remittances must be real
inputs of the served model, so that all five dashboard driver groups are model inputs.

**Development evidence:** attempt 26 on the same 62 quarters, disclosed as such.

## Prior evidence (before this fit)

- **C-E** = C-b + E1 + E2, in C-b's architecture: slightly worse than C-b (Brier +0.006 / +0.004, p 0.89 / 0.79).
  It fails R5 and R7 at Lead 1 and R7 at Lead 2 (`CE_RESULTS.md`).
- **C-E6** = C-E2's 8-setting average + E1 + E2 + rice stocks: fails R3 and R7.
- **Never tested:** E1 + E2 inside C-B6 (C-b architecture + rice stocks).

## Candidate (exactly one)

- **C-B6E = C-B6 exactly** (`runner/cb6_model._origin`, inputs `PC.CB + ST`) + `E1` and `E2`: 25 inputs.
- **E1 and E2 exactly as C-E** (`CE_PREREGISTRATION.md`, bde69c08…):
  - E1 = change in the national unemployment rate (`hr_lib._e1`; months published before O(t));
  - E2 = −(YoY % change of personal transfers, quarter t−2 vs t−6); IMF BOP; leakage check passed
    (`out/ce_checks.json`).
- Both are national, so they are the same for every SWS area row (as in C-E).
- **Unchanged:** no monotone constraints, target 11.3%, threshold 0.50.
- **Replication gate:** C-B6 must reproduce exactly first (< 1e-9), or the run stops.
- **No variant** will be tried after seeing the results.

## Evaluation

As `PLAN_CB6C.md`: 62 verdict quarters, Leads 1–2, all metrics, calls changed, R1–R7, Algorithm 3, paired Brier vs
C-B6, the 14-test Holm family with PERSIST-P, and the SHAP shares of E1 and E2.

## Serving rule (fixed)

The owner has directed that E1 and E2 be included. Their **effect** is reported honestly, whatever it is.

- **Served automatically** in place of C-B6 if C-B6E passes R1–R7 at Leads 1 and 2 **and** keeps accuracy ≥ 0.75 at
  both leads (the study's own reliability standard), even if its Brier is slightly worse than C-B6's.
- **Otherwise it is not served automatically.** The trade-off (inputs vs reliability) is reported to the owner for a
  decision.
- In either case, "employment and remittances improve the forecast" is claimed only if C-B6E's Brier is below C-B6's
  at Lead 1 with one-sided p < 0.05.

**Reported whatever the result.**
PLAN-SHA256: 0b74438ccc34248fea3c858943fe1c0ba3a432cc8febaa65f4bb17fbb7a2eb60
