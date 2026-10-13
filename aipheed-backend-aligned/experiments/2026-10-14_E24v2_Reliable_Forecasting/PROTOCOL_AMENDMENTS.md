# E24v2 protocol amendments (FROZEN_EVALUATION_PROTOCOL.md §10)

**Why amendments live here.** The frozen protocol keeps its original hash (`c8bce7ce…`), and every runner still checks that hash. This file has its own hash, recorded in `runner/AMENDMENTS_SHA256.txt` when the amendments were written.

**None of these amendments changes a target, a threshold, a test row, a confirmatory hypothesis or an acceptance criterion.**

## A1. Additional descriptive baseline in the back-cast: CLIM

- **What it is:** each province's training HIGH frequency, Laplace-smoothed.
- **When it was added:** while writing `run_bx.py`, before the back-cast was run. It was not listed in §5.
- **Effect:** none on HB1–HB4, which compare only M1/M4 with B1/B1p. It is reported descriptively.

## A2. Pre-registration of a T1 back-cast for when long SWS history is supplied

**Written 2026-10-14, before any pre-2021 SWS value exists in this project or has been seen in this work.** SWS web pages were not opened, because they can display protected 2026 rounds.

**Data required (from you).** SWS "families experiencing involuntary hunger", Balance Luzon:

- every round from 1998 to 2020;
- fieldwork dates;
- publication date where known;
- the source document for each row;
- **no row after 2020**.

The file must be authorized by file path and SHA-256 (`runner/run_bx_t1.py` refuses otherwise).

**Timing rule.**

- A round counts at origin O(t) only if its verified publication date is before O(t).
- **Where no publication date is known,** it counts only if its fieldwork quarter ≤ t−1. This is conservative: SWS has historically published within ~1–3 months of fieldwork.

**Labels and rows.**

- S1 = H + 2D with D from the back-cast (gate passed).
- τ = E23 rule.
- Targets from the first quarter with ≥ 8 labelled training quarters through 2020-Q4.

**Models:**

- B1, B1p;
- FINAL_V2_PCF (as frozen);
- PCF_NOW (A3);
- M2 (E24-frozen LightGBM on P).

**Confirmatory hypotheses** (lead 1, one-sided α = 0.05, Holm over the three):

| ID | Hypothesis |
|---|---|
| **HT1** | PCF Brier < B1p Brier |
| **HT2** | PCF accuracy > B1 accuracy |
| **HT3** | PCF_NOW accuracy > B1 accuracy |

**Stability:** the same sign in both halves.

**This is the route to a T1 generalization result before 2028** (the alternative is about 12–20 new quarters of prospective evidence).

## A3. PCF_NOW: the T1 forecaster with the validated D nowcast as its D part

**Definition.** Identical to FINAL_V2_PCF, except that μ_D and σ_D come from M4 (predictors [Dnow, Dlast]) instead of M3.

**Justification.**

- In the back-cast, M4 forecasts the sign of D far better than M3 (accuracy 0.713 vs 0.617 at lead 1; HB3 and HB4 supported). That evidence is on unseen quarters, independent of the T1 development rows.
- D is the **only** provincial part of S1, so a better D forecast is the only route to better provincial differentiation within a quarter.

**Status.**

- **Development (class C) results are descriptive.** The T1 development results of FINAL_V2_PCF had been seen when A3 was written.
- **PCF_NOW is sealed prospectively (class B)** in a second seal with the same origin and information set as the first.
- **FINAL_V2 for T1 remains PCF**, as frozen. PCF_NOW does not replace it unless prospective or A2 evidence supports it.
