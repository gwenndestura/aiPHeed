# E174 protocol: pure zero-shot XLM-RoBERTa news signals (Objective 1, Tier 1)

Locked 2026-11-07, before any E174 result exists. Each step is run once, and the results are reported whatever they are.

## Why

Objective 1 specifies a **zero-shot XLM-RoBERTa** Tier 1. In E151, which feeds E168, each story's event probability is the mean of three readers (deviation D3; `app/e151/topics.event_probs`):
- XLM-RoBERTa zero-shot logits (`nz_*`);
- embedding similarity (`sz_*`);
- seed phrases (`lz_*`).

The topic-to-trigger mapping of BERTopic topics also uses these combined probabilities.

**Choosing pure zero-shot is required by the objective's text, not by any result.**

## What changes

1. **Tier 1.** A story's event probability = softmax over events of its **XLM-RoBERTa zero-shot scores only** (`nz_*` in `data/e151/raw/labels_raw.parquet`). These are the same zero-shot logits (`data/e151/raw/events.parquet`), standardised on stories published before 2015 exactly as in E151.
   - The off-topic rule (foreign place and no Philippine place, or an off-topic phrase in the title) is a geographic and topic filter, not a sentiment reader. It is kept unchanged.
2. **Tier 2.** BERTopic topics and story assignments are the fitted E151 ones; nothing is refitted. Each topic is re-mapped to a trigger group from the **zero-shot** probabilities of the stories fitted at that origin (published before it), using the E151 rule: the top event, or off-topic if the mean `pr_none` is ≥ 0.5.
3. **Everything downstream is the E151 code unchanged:**
   - province-quarter features (`app/e151/features.build`);
   - FSSI (`app/e151/fssi`): outlet centring, shrinkage, 3-month windows, publication-date rule.

   Outputs go to `data/e174/`. E151's files are not modified.

## Step A: FSSI for Objective 1

The **zero-shot FSSI becomes the Objective 1 FSSI**, because it matches the objective. Its checks are reported as they come out, whether better or worse than E151's:
- within-province ρ with food CPI;
- event z-scores at 2018-Q4, 2020-Q2, 2022-Q1, 2023-Q4 and 2025-Q1.

Nothing is re-weighted after seeing them.

## Step B: E174 model (E168 with zero-shot news inputs)

**Model.** E168's procedure (`app.e168.lgbm_only.task` and `run_proc`) unchanged, with the E151 news panel replaced by the zero-shot panel from Step A.

**Runs.** Leads 1–3 for ENNS 2018, 2019 and 2021.

**Decision rule (fixed now).** E174 replaces E168 as the served model only if **both** hold:
1. **Project rule:** accuracy ≥ 75 % and significantly better than the latest survey, at Leads 1, 2 and 3.
2. **Non-inferior to E168 at Lead 1:** the upper bound of the 95 % bootstrap CI (4,000 resamples, seed 174) of the Brier difference E174 − E168 is below **+0.010**. That margin is about 8 % of E168's Brier of 0.123.

**Otherwise E168 stays served.** The report then states that the zero-shot news version was built and tested but not adopted, with its numbers.

If E174 is adopted, it is served only after:
- a new live 2026-Q4 issue;
- its own ENNS 2022 seal;
- the owner's promotion in the registry.

## Not changed

- No independent annotation is claimed. A second human reader is still needed for a label-agreement study.
- No crisis quarter is overridden.
