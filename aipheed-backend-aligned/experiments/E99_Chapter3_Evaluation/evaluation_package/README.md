# E99 evaluation package: ISO/IEC 25010 (H5) and LGU ranking agreement (H4), 50 DA Region IV-A evaluators

**Base instrument.** `E98_Acceptance_Gate/instrument/DA_ISO25010_Questionnaire.md`. Items 1–15 and the scoring bands are
unchanged. E99 adds the two items below. The form is administered **only on the model-integrated dashboard**. Record
the dashboard commit and `/api/v1/config` → `servingModel` with the responses.

## Change 1: eligibility (fixed option)

Section 1, "Agency" is a **single-choice field** whose eligible option reads exactly `DA Regional Field Office IV-A`.
Any other option is excluded from the Chapter I sample and counted separately.

## Change 2: Section 7, LGU vulnerability ranking task (H4)

Chapter I H4 tests whether the municipal rankings are *consistent with DA Region IV-A evaluators' assessments of relative
food-insecurity vulnerability*. A Likert item alone (item 2) cannot test consistency, so each evaluator also ranks LGUs.

> **Section 7.** Choose the province you know best. From the list of its cities and municipalities, select the **five**
> you judge most vulnerable to food insecurity, most vulnerable first. Answer from your own knowledge; do not consult
> the aiPHeed rankings while answering.

- **Form fields:** `province` (one of the five) and `top1..top5`. Each is a dropdown of that province's LGUs, stored as
  the PSGC `lgu_code` from `backend/data/inputs/lgu_vulnerability.csv`.
- **Order of administration:** Section 7 comes **before** the respondent explores the rankings page, so the
  assessment is independent.

## Export format

| File | Columns |
|---|---|
| `iso_responses.csv` | `respondent_id, agency, q1..q15` (1–5; blank = unanswered) |
| `h4_rankings.csv` | `respondent_id, agency, province, top1..top5` |

Templates: `iso_responses_template.csv` and `h4_rankings_template.csv`.

## Scoring (fixed before collection)

```
py -3.13 score_evaluation.py iso_responses.csv h4_rankings.csv results.json      # run from backend/
```

**Export checks** (an invalid export is rejected, never partially scored): columns present, unique IDs, Likert values
1–5, LGU codes valid for the stated province, no repeated LGU.

**ISO/IEC 25010 (H5):**
- Weighted mean, SD and band for each characteristic; favourable at ≥ 3.41.
- Status COMPLETE at 50 eligible respondents, PARTIAL below 50.
- **H5 rejected** only when COMPLETE and every characteristic is favourable.

**H4:**
- Borda top 5 of the evaluators per province (≥ 3 rankings needed) vs the served vulnerability top 5.
- **H4 rejected** iff at least 4 provinces are scorable and in at least 4 of them the overlap is ≥ 3 of 5.
- The chance probability (hypergeometric) of each overlap is reported.
- **Quezon caveat:** its served top 1 is Lucena, whose poverty value is an unverified province substitute (E97).

## Status on 2026-10-22

`status_20261022.json`: **NO_RESPONSES** for both. Nothing is scored.
