# Human annotation guide (Objective 1 validation)

`HUMAN_ANNOTATION_SAMPLE.csv` holds 300 headlines drawn once (seed 70) from the 9,665 in-window headlines of the served corpus. The model's labels are in `model_key.csv`. **Do not open `model_key.csv` before you finish labelling**, so that the labels stay blind.

These are the only labels that can validate the relevance classifier, the trigger assignment and the geographic attribution. The labels used so far (E60/E64) were AI-generated, so they cannot serve as a human reference. Claude did not fill in any label column.

Fill one row per headline:

| Column | Values | Rule |
|---|---|---|
| `human_relevant` | `1` / `0` | 1 if the headline reports something that affects food availability, food access or food prices for households in CALABARZON or nationally (prices, supply, harvest, typhoon or crop damage, fish kills, jobs or income, remittances, food aid). 0 otherwise. |
| `human_trigger` | `market`, `climate`, `fish_kill`, `employment`, `ofw_remittance` or blank | The main food-stress channel. Fill it only when relevant = 1. |
| `human_province` | `PH040100000` Cavite, `PH040200000` Laguna, `PH040300000` Quezon, `PH040400000` Rizal, `PH040500000` Batangas, or `national` | The province the headline is about, or `national` if it names none of the five. |
| `human_food_stress` | `up`, `down` or `none` | Does the event raise or lower food stress? |
| `annotator` | initials | Two annotators on the same rows allow an agreement check (Cohen's κ). |
| `notes` | free text | Optional. |

After labelling, run this from `backend/`:

```
python -B ../aipheed-backend-aligned/experiments/E70_Objectives_Completion/runner/e70_annotation.py score
```

It writes `annotation_score.json` with the following, weighted to the whole corpus by stratum:
- relevance precision, recall and F1;
- trigger agreement;
- province agreement;
- the list of disagreements.
