# 300-headline annotation package (Objective 1 human validation)

**Status: ready for the two annotators. 0 of 300 labelled. No script generates labels.**

## Files (`OBJECTIVES_AUDIT/annotation/`)

| File | Content |
|---|---|
| `labels_annotator_A.csv`, `labels_annotator_B.csv` | The same 300 real headlines: `item`, `article_key` (SHA-256 id), `title`, `outlet`, `ph_date`, and the blank columns `food_insecurity_relevant`, `province`, `food_stress`, `notes` |
| `system_outputs_SEALED.csv` | The system's decisions (stratum, admitted, province code, XLM-R score). Not opened before both sheets are done |
| `ANNOTATION_GUIDE.md` | Definitions, edge cases (Taglish, government programmes, typhoons), headline-only rule |
| `adjudication.csv` | Created by `obj1_annotation_v2.py disagreements`. Lists every A ≠ B item with adjudication fields; never overwritten |

**Sample:** seed 2036, four strata:
- admitted with a province: 100;
- admitted national: 60;
- not admitted with a province: 60;
- other: 80.

Scores are reweighted by stratum size.

**Text:** titles only, because the system scores titles only.

## Workflow

1. A and B label independently, with no discussion.
2. `python runner/obj1_annotation_v2.py disagreements` → `annotation/adjudication.csv`.
3. A third member adjudicates the disagreements.
4. `python runner/obj1_annotation_v2.py score` → `out/obj1_annotation_scores_v2.json`:
   - κ and raw agreement for each label;
   - relevance P/R/F1 and the confusion matrix (sample and stratum-weighted);
   - food-stress (sentiment) accuracy/P/R/F1 and AUC;
   - geocoding accuracy and the confusion matrix.

**Safeguards:**
- Scoring refuses until each sheet is ≥ 90% filled.
- `selftest` (random labels, temporary folder, nothing saved) passed on 2026-11-04.
