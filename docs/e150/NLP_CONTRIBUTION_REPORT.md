# News and NLP contribution

**Result: the pipeline is much better built, and news still does not measurably improve the forecast. No news claim is made.**

## Why 97 % came from one outlet, and why attribution was weak

| Issue | Cause found |
|---|---|
| One outlet | Most Philippine outlets don't expose a public archive API. Inquirer, Philstar, GMA, PNA, SunStar and Manila Times returned 401, 403 or 404; BusinessMirror's robots.txt disallows it; Manila Bulletin and Manila Standard robots files returned errors |
| Weak attribution | Search matched anywhere in the article body, and only the title and excerpt were kept. Only 9.1 % named the province in that text |

## What changed

| Stage | E147/E148 | E150 |
|---|---|---|
| Outlets | About 97 % one outlet | 6 outlets, adding BusinessWorld and Interaksyon |
| Text | Title + excerpt | Full text of food-related articles, kept local |
| Attribution | Query match | Sentence naming the province |
| Text scored | Same article for every province | **The province's own sentences** (title + up to 3) |
| Outlet bias | None | Stress centred on each outlet's mean in the window |
| Volume | Partly corrected | Empirical-Bayes on attributed articles; attention kept separate |
| Trigger groups | Not linked | Share of attributed articles by zero-shot domain feeds market, climate, employment, remittance and poverty features |

**Volumes.** 228,445 province-article links; 97,281 unique articles. Food-related province rows: 37,988. **With a province sentence or title: 36,366 (96 %).** Strength: title 2,049; repeated 11,541; single mention 22,776. So 63 % still rest on a single sentence.

**Attributed unique articles by outlet:** Rappler 6,723, BusinessWorld 1,386, Interaksyon 387, VERA Files 184, NewsBytes 60, PCIJ 56. Rappler is 76 % overall, but **78 to 99 % in any one year** (often above 90 %), so diversity is better overall and still weak.

**Models.** Zero-shot `joeddav/xlm-roberta-large-xnli`, run on the Arc GPU; 17,323 unique texts. **Topic features are not rebuilt in E150:** the six `nb_topic` shares come from E148's panel (BERTopic with masked place names, fitted per origin on earlier documents), so they still use E148's older query-based attribution, not the new sentence attribution.

**Volume bias.** Correlation of FSSI with article count, three spot checks: −0.01, +0.12, −0.10.

## Ablation, Lead 1

| Set | Government (A-G) | Government + corrected news (A-GN) | News-only logistic |
|---|---|---|---|
| Pool accuracy | 0.861 | 0.861 | 0.806 |
| Pool LOW recall | 0.429 | 0.429 | 0.000 |
| Pool AUC | 0.777 | 0.757 | 0.634 |
| Pool Brier | 0.124 | 0.131 | 0.158 |
| 2021 accuracy | 0.88 | 0.88 | 0.80 |
| 2021 LOW recall | 0.40 | 0.60 | 0.00 |
| 2021 Brier | 0.129 | 0.131 | 0.174 |

| Test | Result | Pass? |
|---|---|---|
| A-GN − A-G Brier, pool, Lead 1 | +0.007 [−0.008, +0.023] | No |
| Holm across leads 1 to 4 | None pass; p from 0.05 to 0.80 | No |
| Wrong-province placebo, 2021, Lead 1 | 30 % of placebo draws match or beat real news; limit is 5 % | No |
| Development, Lead 1 | +0.010 [−0.011, +0.032] | No |

**The higher 2021 LOW recall with news (0.60) is one changed call out of 5 LOW rows, with no Brier gain.** It isn't evidence.

## Unmeasured quality

* **Sentiment accuracy on Filipino-English news has no local check.** A hand-labelled sample is the only direct test, and your rule excludes it.
* **Topic quality not assessed.** BERTopic topics are fitted, not reviewed by a person.
* **Duplicate detection** is by id and normalised title only, so syndicated rewrites can remain.

## What it would take

| Need | Why | Amount |
|---|---|---|
| More measured outcomes | With 72 rows, a small effect can't be detected | Next provincial round at least |
| Labelled sample | To measure sentiment and relevance | About 200 articles; **your decision** |
| Local and regional outlets | Provincial reporting; current sources are national | Licensed or partner access, since public APIs are closed |
| Stronger attribution rules | 63 % single mention | Requires human-checked rule, same sample |

**Fixed wording for the thesis:** "Province-level news features from a two-stage XLM-RoBERTa and BERTopic pipeline were tested out of sample and did not measurably improve the forecast. The pipeline remains in place for monitoring and for re-testing when new survey rounds are available."
