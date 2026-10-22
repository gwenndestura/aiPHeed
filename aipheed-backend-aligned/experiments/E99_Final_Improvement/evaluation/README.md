# DA Region IV-A evaluation package (Chapter I H4 and H5 / SOP 4–5)

**Status on 2026-10-22: no responses collected.** Both scorers return `NO_RESPONSES`. No rating is computed before real
responses exist.

## Who

- **50 evaluators from DA Region IV-A**, the Chapter I sample. Your 2026-10-10 decision removed DEPDev.
- **Discrepancy to resolve in the manuscript.** `THESIS 2 (11).pdf` SOP 5 still names "DEPDev Region IV-A personnel,
  as usability evaluators". H5 names DA only. The scorers apply the DA-only rule.

## What to administer (model-integrated dashboard only, never mock data)

Record the dashboard version shown: the git commit and `/api/v1/config` → `servingModel`.

1. **ISO/IEC 25010 questionnaire (H5).**
   - Use `../../E98_Acceptance_Gate/instrument/DA_ISO25010_Questionnaire.md`: items 1–15, 5-point Likert.
   - The item-to-characteristic mapping is in `../../E97_Validation_Completion/iso25010/item_map.json`:

     | Characteristic | Items |
     |---|---|
     | Accuracy | 1–5 |
     | Functional suitability | 6–9 |
     | Usability | 10–15 |

2. **H4 ranking task.**
   - Each evaluator picks the province they know best.
   - They rank its 6 listed LGUs in `h4_lgu_sets.csv` from 1 (most vulnerable to food insecurity) to 6, with no ties.
   - **Show the names alphabetically, without aiPHeed's ranks or scores.**
   - In Quezon the set includes Lucena. Its aiPHeed position uses a substituted poverty value (see E99 Q5); keep it in
     the set and report its result separately.

## Export format

| File | Columns |
|---|---|
| `iso_responses_template.csv` | `respondent_id, submitted_at, agency, office_unit, consent, q1..q15` |
| `h4_responses_template.csv` | long format, `respondent_id, agency, consent, province, lgu_code, evaluator_rank` (one row per ranked LGU) |

- Use the same `respondent_id` in both files.
- `consent` must be `yes`. Use the "Sgd. Full Name" rule of the consent page.
- Do not put names or e-mails in these files.

## Eligibility (fixed now, before any response)

| Rule | ISO scorer | H4 scorer |
|---|---|---|
| Agency is DA Region IV-A | E1 | yes |
| Consent recorded | E2 | yes |
| Unique respondent id | E3 | per id |
| Valid answers | E4: 1–5, every characteristic answered | the full 6-LGU set, no ties |

Excluded rows are listed with their reason, never imputed or replaced.

## Decision rules (fixed now)

**H5** is rejected only when:
- status is COMPLETE (50 eligible responses); **and**
- each of the three characteristics has a weighted mean ≥ 3.41 ("Agree").

**H4** is rejected only when:
- there are at least 10 eligible evaluators; **and**
- the median Spearman ρ between evaluator and aiPHeed ranks is ≥ 0.40; **and**
- a one-sided Wilcoxon signed-rank test of ρ > 0 gives p < 0.05.

## Commands (from `backend/`)

```
py -3.13 ../aipheed-backend-aligned/experiments/E99_Final_Improvement/evaluation/score_iso25010_v2.py <iso_responses.csv> <out.json>
py -3.13 ../aipheed-backend-aligned/experiments/E99_Final_Improvement/evaluation/h4_ranking.py score <h4_responses.csv> <out.json>
```
