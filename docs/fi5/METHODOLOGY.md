# How FI5 works, in plain language

## What it predicts

Every quarter, Social Weather Stations (SWS) asks families whether they **went hungry and had nothing to eat** at
least once in the last three months. FI5 predicts whether that hunger rate, for the part of Luzon outside Metro
Manila (which includes all of CALABARZON), will be **higher than its usual level** — "usual" meaning the average of
the previous five years. That is the same "worse than normal" test that famine early-warning systems use.

It answers: *"How likely is it that hunger next quarter (or two, three, four quarters ahead) will be above
normal?"* The answer is a probability from 0 to 1; 0.5 or more is shown as HIGH.

What it does **not** do: it does not measure hunger in a particular province or town. No survey measures hunger
every quarter at that level. Province and town figures are a **priority ranking** that combines the area forecast
with how poor and how crowded each place is.

## What it looks at

Five groups of evidence. Each group combines official statistics and news about the same thing.

| Group | Official statistics | News signals |
|---|---|---|
| Market and prices | food and rice inflation (PSA CPI), palay harvest (PSA) | news volume about food shortages and farm supply (GDELT); local headlines about food prices and supply |
| Climate stress | rainfall and heat compared with normal (NASA POWER), typhoons passing near the region (IBTrACS), El Niño index (NOAA) | local headlines about typhoon, flood or drought damage to farms |
| Employment | unemployment rate and its change (PSA Labor Force Survey) | news volume about unemployment (GDELT); local headlines about job losses |
| OFW remittances | yearly change in money sent home (BSP, through the World Bank) | local headlines about overseas workers and remittances |
| Poverty and vulnerability | poverty rate (PSA) | news about food aid (GDELT); local headlines about poor families, hunger and food aid |

It also looks at the **latest hunger survey reading**, because hunger tends to stay high or low for a while.

Every number is used only from the date it was actually published. A forecast made at the end of June 2015 sees
only what was public by then.

## How the news is read

1. About 9,600 Filipino and English headlines (2021 to October 2026) are collected.
2. A multilingual language model (XLM-RoBERTa) reads each relevant headline and answers simple questions: Is it
   about food prices? Weather damage? Jobs? OFWs? Poor families or food aid? Does it report people going hungry?
   Is it a government response? Are things getting worse or better? One headline can belong to several groups.
3. Repeated reports of the same event are counted once.
4. A topic model (BERTopic) groups headlines into themes, and each theme is linked to one of the five groups.
5. For each province and quarter, the **Food Stress Sentiment Index (FSSI)** is the share of the quarter's news
   that reports worsening conditions in that group. It is a share, not a count, so a province that gets more news
   coverage does not automatically look worse. Provinces with very few articles lean on the regional value.

## How the forecast is made and checked

* One LightGBM model per forecast distance (1 to 4 quarters ahead), all using the same inputs.
* It is tested the honest way: for every quarter from 2010 to 2026, the model is trained only on what was known
  before that quarter, makes its forecast, and is then compared with what SWS later reported.
* It is compared with four simpler methods: "same as the latest reading" (persistence), official statistics only,
  news only, and logistic regression.
* A forecast distance counts as **reliable** only if accuracy is at least 75 %, at least half of the real HIGH
  quarters are caught, at least half of the HIGH warnings are right, the ranking ability (AUC) is at least 0.70,
  probabilities beat simply using the historical rate, and accuracy stays at least 60 % in each period
  (2010–15, 2016–20, 2021–26). These rules were written down before the test was run.

## How each forecast is explained

The model's contributions are added up per group and turned into one or two sentences, for example the pattern
"Food prices and supply raised the estimated chance of above-normal hunger in 2026-Q4, while jobs and unemployment
lowered it." The sentence names only groups that moved the estimate noticeably, and it says that these are the
factors the model leaned on, not proven causes.

## How towns and cities are ranked

For each of the 142 cities and municipalities:

* poverty rate (PSA 2021 small-area estimate; Lucena City uses PSA's 2021 city estimate) and population density
  (2024 census population ÷ land area) are each turned into a 0–1 rank within CALABARZON;
* vulnerability = half poverty rank + half density rank;
* priority score = 100 × forecast probability × vulnerability.

Because every place shares the same area forecast, the order of places comes from vulnerability; the forecast sets
how high the scores are overall. The ranking is a guide for where to look first, not a hunger measurement.
