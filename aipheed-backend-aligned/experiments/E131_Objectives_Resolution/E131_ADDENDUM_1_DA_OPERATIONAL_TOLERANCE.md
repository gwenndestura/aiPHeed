# E131 Addendum 1: investigation of a DA Region IV-A operational tolerance

**Frozen 2026-11-01**, before any 2026-Q4 SWS reading exists. Its SHA-256 is in `runner/ADDENDUM_1_SHA256.txt`.

## Owner instruction (2026-11-01)

- Keep the frozen primary criteria: tolerance = 1.645 × SE, and the 75 % requirement.
- Investigate whether DA Region IV-A has an *independently justifiable* operational tolerance for provincial food-insecurity risk forecasts.
- If one is established: document it, get approval before the sealed 2026-Q4 forecasts are evaluated, freeze it, report it separately from the primary, and never use it to claim the 75 % objective.
- If none can be established, keep the primary evaluation only.

## What was searched

| Source | What it provides | A tolerance for food-insecurity forecasts? |
|---|---|---|
| This repository | All protocols, theses and reports (E1–E131, FINAL_*, LEAD2_*, docs) | **No.** The "decision thresholds" in LEAD2, E84 and E88 are model cut-offs tuned on validation data, not DA rules. The 11.3 % line is a researcher-set percentile (E79). |
| DEPDev Region IV-A Regional Development Reports, 2024 and 2025 (preliminary) | Food-security indicators monitored, including the regional and provincial subsistence incidence | **No.** They report indicators without alert levels or acceptable-error bands. |
| DA national: food security emergency on rice (Department Circular No. 3, 3 Feb 2025, under RA 12078) | Trigger: an "extraordinary" rice price increase, judged by the National Price Coordinating Council as rice inflation above the food-inflation target band and in double digits | **No.** It is a **price** trigger. Adopting it would replace food insecurity with food prices, which the directive forbids. |
| IPC (classification framework, coordinated in the Philippines through NNC) | Area phase rule: an area takes a phase when at least 20 % of its population is in that phase or worse | **No.** It is a classification boundary for IPC household-phase data, not a ± tolerance for hunger prevalence. The Philippine analyses found date from the ARMM era and do not cover CALABARZON. |
| NNC / WHO nutrition prevalence bands | Public-health significance of malnutrition | **No.** They measure malnutrition, a different construct. |
| SWS | Publishes sampling margins and calls changes "significant" against them | **Not operational, and not independent.** A "significant change" band (1.96 × √2 × SE ≈ 2.77 × SE) is the same sampling error as the primary rule, rescaled. It reflects no DA decision. |

**Search log:** `sources/SOURCES_LOG.md` (A1–A3).

## Decision

**No independently justifiable DA Region IV-A operational tolerance exists.** Accordingly:

1. **Only the primary evaluation is kept.** The sealed forecasts are scored with `runner/score_e131.py`, which applies the protocol §1 rule (|forecast − SWS| ≤ 1.645 × SE of the SWS quarter) and nothing else. The procedure is frozen here, before 2026-Q4 SWS is published (expected around January 2027).
2. **No secondary tolerance is reported** for E131 or for the E130 seal.

## Why a wider band without a DA basis would hide errors

**Development data,** shared rows, P-DASH, Lead 2, LLM; information only, never used for pass/fail:

| Band | Median width | Share "within" | Sharp increases counted as "within" |
|---|---|---|---|
| 1 × tolerance (primary) | ± 3.85 points | **0.50** | **0 of 7** |
| 2 × tolerance | ± 7.70 points | 0.79 | **3 of 7** |

Doubling the band would turn three missed surges into "agreements". One example is Visayas 2026-Q1: forecast 21.0, observed 28.0. A band that is not grounded in DA's decisions therefore conceals exactly the events an early-warning system exists to catch. It has no defensible decision value.

## The only legitimate route to a DA tolerance (not taken; owner decision)

A DA tolerance would be independently justified only if **DA Region IV-A decision-makers themselves** stated it, in decision terms, without seeing any model results. For example: "a hunger change of X points would change our allocation or advisory decision."

The minimum requirements:
- Elicitation is blind to E128–E131 errors.
- The aggregation rule (for example, the median respondent) is fixed in advance.
- Ethics and DA permission are obtained.
- Owner approval and a hash freeze happen **before** 2026-Q4 SWS is published.
- Reporting:
  - primary result first;
  - secondary result next to error magnitudes and surge capture;
  - never described as meeting the 75 % objective.

Until that happens, **primary only.**
