# Headline annotation guide (Objective 1 validation set)

**Files:**
- `labels_annotator_A.csv` and `labels_annotator_B.csv`: the same 300 headlines in the same order. Each team member
  fills **one file independently**, without discussing items until both are complete.
- `system_outputs_SEALED.csv` holds what aiPHeed decided for each headline. **Do not open it before both sheets are
  complete.** Labels made after seeing the system's output are not valid.

**Sample:** 300 headlines drawn at random (seed 2036) from four groups of the 9,667-headline corpus:
- 100 that the system admitted and assigned to a province;
- 60 admitted without a province;
- 60 not admitted but naming a province;
- 80 others.

Because the groups are sampled at different rates, the scoring script reweights by group size for corpus-level
figures.

## Columns to fill

| Column | Values | Rule |
|---|---|---|
| `food_insecurity_relevant` | 1 / 0 | **1** if the headline reports something that affects people's access to enough food in the Philippines: food prices or affordability, food supply or shortages, harvest or fisheries losses, disasters damaging food or livelihoods, jobs or income loss, hunger, or food assistance. **0** otherwise: politics, crime, sports, entertainment, business news unrelated to food access, or foreign news without a Philippine food angle |
| `province` | Cavite, Laguna, Batangas, Rizal, Quezon, or blank | The CALABARZON province the event happens in, from the headline text only. A city or municipality counts for its province (e.g. Lipa → Batangas; Lucena → Quezon). Blank if none, if several provinces, or if the place is outside CALABARZON |
| `food_stress` | 1 / 0 (only when relevant = 1) | **1** if the headline signals worsening food conditions (rising prices, shortage, loss, displacement, hunger). **0** if neutral or improving (prices falling, aid delivered, harvest up) |
| `notes` | Free text | Optional: unclear items, language (English, Filipino, Taglish) |

## Edge cases

- **Taglish and Filipino:** treat them the same as English.
- **Headline only:** do not open the link. The system sees the title only, so the reference must too.
- **Government programmes** (e.g. "DA distributes seeds"): relevant = 1, food_stress = 0.
- **"Rice prices stable":** relevant = 1, food_stress = 0.
- **Typhoon headlines:** relevant = 1 only if damage to people, crops, fisheries or livelihoods is stated or clearly
  implied.

## After both files are complete

> **Current workflow (2026-11-04).** This supersedes the steps below where they differ, and matches
> `FINAL_2026-11-04/HEADLINE_ANNOTATION_PACKAGE.md`:
> 1. Check that both sheets still hold the same 300 items: `item` 1–300, identical `article_key` and `title`.
> 2. `python ../runner/obj1_annotation_v2.py disagreements` → `adjudication.csv`, the A ≠ B items.
> 3. A third team member fills `adjudication.csv`, recording disagreements there and not in `notes`.
> 4. `python ../runner/obj1_annotation_v2.py score` → `../out/obj1_annotation_scores_v2.json`.
>
> **The scoring reports:** κ, relevance P/R/F1, XLM-R stress accuracy and AUC, and geocoding accuracy.
>
> **Sealed system outputs:** `system_outputs_SEALED.csv`, SHA-256
> `f8e668d4080025900278f3ef4c7f301926d35f82644e06248879ebbccc64c883`. The hash is recorded 2026-11-04 and the file is
> identical to commit 2d762ab. Re-check the hash before scoring.
>
> **Earlier steps:** `obj1_nlp.py score` still runs, unchanged, but gives the smaller metric set.

1. Run `python ../runner/obj1_nlp.py score`.
2. The script reports:
   - Cohen's κ for relevance and province;
   - the precision and recall of the relevance classifier;
   - geocoder accuracy;
   - the AUC of the XLM-RoBERTa intensity against `food_stress`, on items where both annotators agree.
3. Disagreements are resolved afterwards by discussion; record the resolved label in `notes`. The κ is reported from
   the independent labels.

The script refuses to score unless both annotators have labelled at least 90% of the items. It never creates or
imputes a label.
