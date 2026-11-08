# E123 NLP and GDELT audit (DI-5)

## FSSI-v3 (FIS, provincial)

| Question | Finding | How checked |
|---|---|---|
| Only articles of the eligible period? | **Yes.** `pipeline_v3.admitted()` keeps articles dated 2021-01-01 to 2026-10-14; the 695 admitted articles run from 2021-01-05 to 2026-10-14. `asof(t)` uses only articles of quarter t published before O(t). | Re-run of `admitted()` and `asof()` for every origin: **0 violations** |
| Timestamps preserved? | **Yes.** Every admitted article has `ph_date` (0 missing). The as-of rule uses the Philippine-time publication timestamp. | Same |
| Duplicated content? | **No.** 0 duplicate article keys; 0 duplicate (province, normalized title, quarter) after syndication de-duplication. | Same |
| Future information? | **No.** FSSI for (province, t) uses only that quarter's admitted articles published before the issue. The bias weight uses the median article count of the five provinces **in the same quarter**. | FSSI-v3 recomputed for all 115 province-quarters and compared with the FIRI3 input: 20 scored, **max \|Δ\| = 0.0**, article counts identical (`out/fssi_recompute.csv`) |
| Intensity from current articles or historical baselines? | **Current articles only.** Each article's intensity is the maximum entailment probability of the 10 HungerGist hypotheses (zero-shot XLM-RoBERTa). There is no baseline, no normalization against earlier articles, and no historical z-score. | `app/ml/nlp/classifier.py`, `app/news/pipeline_v3.py` |
| Pretrained knowledge vs historical observations | The NLI model `joeddav/xlm-roberta-large-xnli` is a **general pretrained model**, used without fine-tuning on food-insecurity data. Its parameters come from general multilingual text and XNLI. **It cannot be claimed to have been trained only on 2021–26 data, and that is not claimed.** These parameters are not FIRI3 observations: no pre-2021 food-insecurity value or article enters a score. | Disclosed limitation (E122 W1) |
| Relevance rules | Classifier v2 rules were written on a development half of 2021–26 annotated articles (E60) | Design-time use of later articles, in the wording of rules, not in values. Disclosed (E122 W2). |

## GDELT (FIS, regional)

| Question | Finding | How checked |
|---|---|---|
| Observation period | The raw file holds daily values from 2017. **5,832 pre-2021 rows** are present but filtered (date ≥ 2021-01-01) before aggregation. Quarters used: 2021-Q1 to 2026-Q3. | Recomputed the quarterly mean of daily "shortage" volume intensity from the raw file: **max \|Δ\| = 4e-13** vs the FIRI3 input |
| Complete quarters | At least 75 days in every quarter; the availability date (start of q+1) is after every quarter end | Same |
| Baseline? | None. GDELT "Volume Intensity" is each day's share of all monitored articles. No historical normalization is applied by aiPHeed. | — |
| Limitation | Values come from one query (2026-10-25) of GDELT's current index. Historical shares could differ slightly from what was visible at each issue date (index vintage). | Disclosed; prospective snapshots record the value at issue |

## Conclusion

**FSSI-v3 and GDELT inputs are point-in-time valid** for the observations FIRI3 uses. Every value is reproduced exactly from 2021+ records available before each issue.

**Remaining limitations** concern the model and the data vintage, not the observations:
- the pretrained NLI model;
- the relevance-rule development set;
- the GDELT query vintage.
