# FI6-N: can properly collected news add forecasting information? (results)

The design is in [NEWS_INVESTIGATION.md](NEWS_INVESTIGATION.md). The comparison design was locked
(`b10406be6120…`, `backend/data/fi6/out_news/METHOD_LOCK_NEWS.json`) before evaluation, and the features were
unchanged since the lock. Every number below comes from `backend/data/fi6/out_news/` and
`backend/data/fi6/news_archive/audit.json`.

## 1. What changed in the news data

| | Old corpus (FI5/FI6) | New archive (FI6-N) |
|---|---|---|
| Collection | Google News search, retrospective | Publisher archives (WordPress REST API), same method every year |
| Period | 2021-01 to 2026-10 | 2008-03 to 2026-10 (usable from 2012-Q3) |
| Sources | ~50 outlets, mixed by year | Rappler, VERA Files, NewsBytes.PH, PCIJ (robots.txt checked; Bulatlat and PinoyWeekly refused connections and were dropped) |
| Text | headline only | headline + lead paragraph |
| Articles kept | 9,643 | 62,698 (19,983 roundups and sports/entertainment/lifestyle items excluded) |
| Relevant (XLM-R) | 1,147 | 2,879 → 2,841 events |
| Restated official statistics removed | not handled | 500, of which 247 CPI, 51 LFS, 80 remittance, 17 poverty and 107 **SWS hunger survey** reports (the outcome itself) |
| Evaluated quarters with news | ~20 | 45 of 62 |

**Geography.** Location comes from the title or lead for 2,408 articles (LGU 1,875, province 283, region 250). For
47,449 more it comes only from the article body (the API search matched the place, but the lead does not name it),
and these are kept as a weaker level, `body_mention`. 12,841 are national.

**Imbalance.** Batangas has about 480 anchored articles per quarter and Rizal about 31, so province cells are
shrunk toward the region (shrink weight 0.57 for Rizal, 0.82 for Batangas).

**Duplicates.** Only 3 events were reported by more than one archive source, so cross-outlet duplication is small
in this source set.

**Labels.** Domain counts are market 897, climate 540, employment 843, remittance 414 and poverty 576. By evidence
type: ongoing disruption 1,200, potential risk 675, government response 518, observed hardship 469.

**Compute.** Classification ran on the CPU (PyTorch, 18 threads) and the Intel Arc GPU (OpenVINO fp32, identical
outputs to the CPU), with 14,338 articles scored.

## 2. Controlled forecasting comparison (same FI6 target, origins, model, rules; 62 targets, 11 HIGH)

Lead 1:

| Feature set | Accuracy | Precision | Recall | F1 | AUC | Brier | ΔBrier vs government only (95 % CI) |
|---|---|---|---|---|---|---|---|
| Government only | 0.839 | 0.600 | 0.273 | 0.375 | 0.702 | 0.129 | — |
| News only (+ latest reading) | 0.855 | 0.667 | 0.364 | 0.471 | 0.742 | 0.120 | −0.009 (−0.025, +0.003) |
| **Government + news** | 0.839 | 0.600 | 0.273 | 0.375 | **0.765** | **0.119** | **−0.010 (−0.021, −0.002)** |
| … without market news | 0.839 | 0.600 | 0.273 | 0.375 | 0.738 | 0.121 | −0.007 (−0.014, −0.002) |
| … without climate news | 0.839 | 0.600 | 0.273 | 0.375 | 0.750 | 0.121 | −0.008 (−0.014, −0.002) |
| … without employment news | 0.839 | 0.600 | 0.273 | 0.375 | 0.742 | 0.122 | −0.007 (−0.013, −0.001) |
| … without remittance news | 0.839 | 0.600 | 0.273 | 0.375 | 0.743 | 0.122 | −0.007 (−0.013, −0.002) |
| … without poverty news | 0.839 | 0.600 | 0.273 | 0.375 | 0.727 | 0.124 | −0.005 (−0.011, +0.001) |
| NLP-only baseline (classifier, no SWS info) | 0.726 | 0.200 | 0.182 | 0.190 | 0.463 | 0.183 | +0.054 |
| Naive persistence | 0.871 | 0.667 | 0.545 | 0.600 | 0.743 | 0.116 | −0.013 (−0.057, +0.023) |

On the 45 origins where news exists, government + news has AUC 0.835 against 0.752 for government only, and
Brier 0.095 against 0.109 (Δ −0.014, CI −0.029 to −0.002).

Gain from adding news, all leads (Brier, government + news minus government only):

| Lead | ΔBrier | 95 % CI | Bonferroni 98.75 % CI | News helps (locked rule) |
|---|---|---|---|---|
| 1 | −0.0099 | (−0.021, −0.0015) | (−0.025, −0.0006) | **yes** |
| 2 | −0.0052 | (−0.0098, +0.0001) | (−0.0118, +0.0006) | no (borderline) |
| 3 | −0.0012 | (−0.006, +0.006) | — | no |
| 4 | −0.0006 | (−0.008, +0.007) | — | no |

## 3. What this means

1. **Properly collected news adds measurable information at lead 1, and the result survives a correction for
   testing four leads.** The old corpus showed nothing, because its problem was coverage, not NLP. Once news
   existed for most of the evaluated quarters, it helped.
2. **The gain is in probability quality, not in classifications.** AUC rises from 0.70 to 0.77 and Brier falls by
   about 8 %. No forecast crosses the 0.5 line, so accuracy, precision and recall are unchanged. The model still
   fails the recall rule (0.27 < 0.50) and is still not a reliable classifier.
3. **The information is spread across domains.** Removing any single news domain keeps most of the gain.
   Poverty/hardship news contributes most; its removal leaves an interval that touches 0.
4. **News helps the anchored model, not on its own.** The NLP-only classifier without any SWS information is worse
   than climatology (Brier 0.183 vs 0.149). News is useful as an adjustment to the latest reading.
5. **Persistence is still the best single classifier at lead 1:** accuracy 0.871 and recall 0.55, against 0.839 and
   0.27. With news, LightGBM's Brier (0.119) is now close to persistence's (0.116); the interval includes zero.
6. **Beyond lead 1 there is no gain.** That is consistent with news describing current conditions rather than
   events two or more quarters ahead.

## 4. Limitations

* **Unverified labels.** The labels have not yet been checked by people. The kit is
  `backend/data/fi6/nlp_validation/archive_annotation_sheet.csv`, 200 articles with model labels hidden in
  `archive_model_key.csv`.
* **Source mix.** One outlet (Rappler) supplies 95 % of the archive. A second large source with an open archive
  (PNA, Inquirer) could not be used: login required, or no public API.
* **Weak geography.** 76 % of the location evidence is a body mention.
* **Severity is rarely extractable from leads.** Peso damage and displacement figures were found in few articles;
  full article bodies would improve them.
* **Development evidence only.** These quarters were also used for FI5/FI6. The sealed 2026-Q4+ forecasts are the
  clean test.

## 5. Reproduce (from `backend/`)

Collect the archive (resumable; respects robots.txt and crawl delays):

```bash
python -m app.fi6.news_archive collect --sites rappler,verafiles,newsbytes,pcij
```

Write the to-score list:

```bash
python -m app.fi6.news_events prepare
```

Score the articles. The GPU worker runs OpenVINO on the Intel Arc in the separate venv, and the CPU worker runs
PyTorch in the main venv:

```bash
C:\Users\admin\aipheed_fi5_xpu\Scripts\python.exe -m app.fi6.news_events worker --part 0:0.6 --backend openvino-GPU
```

```bash
python -m app.fi6.news_events worker --part 0.6:1 --backend torch --threads 18
```

Then build events, features and audits, lock the comparison, evaluate, and issue the forecasts:

```bash
python -m app.fi6.news_events build
```

```bash
python -m app.fi6.news_model lock
```

```bash
python -m app.fi6.news_model evaluate
```

```bash
python -m app.fi6.news_model issue
```
