# E61: BERTopic on the full province-attributed corpus (SO1). Descriptive only; not wired into the API.

## Pre-registration (written 2026-10-18, before any E61 topic model was fitted)

**What was looked at before writing this:** only corpus counts (no model was fitted):
- 2,820 province-attributed articles in `data/news_e31/articles.jsonl`;
- no article published after the authorized date (2026-10-14);
- 5 repeated titles.

**Purpose.** SO1 promises "latent food insecurity risk patterns per province-quarter" from BERTopic. The E59 fit used
the 55 relevance-screened articles and failed its stability gate (mean ARI 0.38 < 0.5). E61 refits the **same
pipeline under the same gate** on the full province-attributed corpus. This is to see whether more text gives stable
topics. **The gate is not relaxed.**

**Corpus (fixed now)**
- Every article in `data/news_e31/articles.jsonl` with `geo_province_code` in the five CALABARZON provinces.
- `quarter` must be in the authorized window, `all_quarters(authorized_until)` = 2021-Q1..2026-Q4.
- `ph_date` must be <= `authorized_through` (2026-10-14).
- **No** relevance rule and **no** XLM-R score threshold.
- Titles exactly as stored; the store's own de-duplication only. The 5 repeated titles are kept, as in E59, which
  also used stored titles.
- Article order: sorted by `article_key`, as in `app.news.topics._topic_articles`.

**Model (identical to E59; `app/news/topics.build_topic_files` / `app/ml/nlp/topic_model.TopicModelPipeline`)**
- Embeddings: paraphrase-multilingual-MiniLM-L12-v2.
- UMAP 5-d cosine, HDBSCAN eom, KeyBERT-inspired representation, CountVectorizer 1-2 grams, English stop words.
- `min_topic_size` = 10. Main fit seed 42; stability refits with seeds 43 and 44.
- ARI = `adjusted_rand_score` between the seed-42 assignment and each refit, outliers included (as in E59).

**Gate (the constants imported from `app.news.topics`; not re-typed)**
- articles >= 30 (3 x min_topic_size);
- topics >= 2;
- outlier share <= 0.5;
- mean stability ARI >= 0.5.

**Fit once.** One seed-42 fit plus the two stability refits; no re-runs, parameter changes or corpus changes after
seeing the result.

**Reported whatever the outcome**
- Article counts per quarter and per province.
- Number of topics; size of every topic, including the outliers.
- Top 10 words per topic, with weights, from the seed-42 fit.
- Outlier share; both ARIs and their mean; the gate result per criterion.

**If the gate passes**
- Written to `data/news_e61/topics/`, in the same formats as E59's publication: `manifest.json`,
  `topic_proportions.csv` (per province-quarter share of each topic, with `n_articles`) and `topics.json` (top
  words).
- **Not** wired into any API route or the dashboard. Nothing is written to `data/news_e31/`.

**If it fails**
- Nothing is written under `data/`. The manifest and the report stay in `backend/experiments/e61/`, and the failure
  is stated plainly.

**Reading.** A pass means only that the topics are stable enough to describe. They are descriptive (fitted on all
quarters, so later articles shape earlier quarters' topics), not forecast features, and they are not "risk
patterns" unless their words show that.

## Results

(Appended by the runner after the run; nothing above this line is edited.)

**Run.** paraphrase-multilingual-MiniLM-L12-v2, seed 42, stability seeds [43, 44], min_topic_size 10.
- Pre-registration md5 `4523c50f41a6e401bccc31c43ddb51e8` (stamped 2026-10-18T07:50:46Z), unchanged.
- Protected md5s identical at the start and the end: True.
- One fit plus two stability refits; nothing was re-run.

### Corpus: 2820 titles, 2021-Q1..2026-Q4 (5 repeated titles kept)

| Province | Articles |
|---|---|
| Batangas | 794 |
| Cavite | 692 |
| Laguna | 444 |
| Quezon | 429 |
| Rizal | 461 |

| Quarter | Articles |
|---|---|
| 2021-Q1 | 62 |
| 2021-Q2 | 30 |
| 2021-Q3 | 67 |
| 2021-Q4 | 30 |
| 2022-Q1 | 71 |
| 2022-Q2 | 64 |
| 2022-Q3 | 86 |
| 2022-Q4 | 95 |
| 2023-Q1 | 84 |
| 2023-Q2 | 109 |
| 2023-Q3 | 131 |
| 2023-Q4 | 111 |
| 2024-Q1 | 125 |
| 2024-Q2 | 158 |
| 2024-Q3 | 165 |
| 2024-Q4 | 162 |
| 2025-Q1 | 134 |
| 2025-Q2 | 130 |
| 2025-Q3 | 192 |
| 2025-Q4 | 143 |
| 2026-Q1 | 164 |
| 2026-Q2 | 190 |
| 2026-Q3 | 262 |
| 2026-Q4 | 55 |

Per province-quarter counts are in `E61_results.json` (`corpus.per_province_quarter`).

### Gate (unchanged from E59)

| Criterion | Threshold | Value | Pass |
|---|---|---|---|
| Articles | >= 30 | 2820 | True |
| Topics | >= 2 | 59 | True |
| Outlier share | <= 0.5 | 0.384 (1082 of 2820) | True |
| Mean stability ARI | >= 0.5 | 0.654 (seed 43: 0.651; seed 44: 0.657) | True |

**Result: PASS** (gate passed). Files written: `data\news_e61\topics\manifest.json`, `data\news_e61\topics\topic_proportions.csv`, `data\news_e61\topics\topics.json`. They are not wired into any API route.

### Topics (seed 42): size and top 10 words

| Topic | Size | Top words |
|---|---|---|
| -1 (outliers) | 1082 | - |
| 0 | 127 | filipinos, batangas city, house cavite, quezon, tourist, kawit, hidden, visit, explores, pascual gives |
| 1 | 104 | cavite laguna, ecozones, projects batangas, hectare, batangas plant, township, plant, plant batangas, inaugurates, coastal cleanup |
| 2 | 85 | sustainability, quezon province, batangas province, beneficiaries quezon, local gov, stakeholders, safety, climate, protection, gov |
| 3 | 84 | cavite tagaytay, cavite, local, caviteños, shop, san, culture, food hubs, destination, cafe |
| 4 | 59 | floods pililla, floods laguna, cavite residents, evacuated batangas, imus cavite, local officials, evacuees, flooding, cavite, cainta families |
| 5 | 56 | cavite laguna, seized cavite, arrested cavite, cavite arrested, seized quezon, cavite rizal, seized batangas, lucena city, city rizal, cavite |
| 6 | 49 | quezon town, locals, plaza, town, quezon coconut, anilag, cainta, anilag festival, nagcarlan, tanay rizal |
| 7 | 48 | cavite laguna, rizal province, laguna gov, cities laguna, rizal towns, batangas rizal, laguna, batangas towns, laguna shift, city rizal |
| 8 | 44 | typhoon victims, quezon residents, mariano, typhoon, rizal residents, pablo laguna, floods pililla, residents affected, residents, kapuso foundation |
| 9 | 44 | manila laguna, taproom laguna, pangulo, batangueño, cavite, region, laguna economy, hub cavite, ng pangulo, trias cavite |
| 10 | 40 | naic cavite, cavite, bongbong marcos, maharlika, kapuso, bataan cavite, kapuso foundation, bongbong, laguna pampanga, china |
| 11 | 40 | quezon laguna, cavite, massive cavite, laguna, cavite lgus, cavite robredo, cavite special, laguna governor, pamalakaya, kapihan |
| 12 | 38 | residents cavite, cavite towns, cavite city, tilapia bangus, cavite denr, towns, cavite, mangroves, cavite fishers, tilapia |
| 13 | 37 | batangas province, corruption, areas, batangas city, vs corruption, area, calamity, residents evacuate, state calamity, mayoral |
| 14 | 37 | cavite areas, quezon barangay, batangas towns, rain cavite, rizal areas, cabuyao laguna, manila, areas, flooding quezon, laguna habagat |
| 15 | 36 | quezon barangay, bacoor cavite, barangay, dead cavite, cavite, house cavite, killed cavite, laguna woman, cabuyao, lipa city |
| 16 | 36 | cavite rizal, cavite dead, dead cavite, batangas city, quezon province, farmers quezon, cavite road, killed batangas, utility, dead batangas |
| 17 | 33 | batangas towns, calabarzon, towns, doh calabarzon, 24 hours, ndrrmc, near, signs, centers, taal volcano |
| 18 | 30 | rizal laguna, laguna town, laguna community, laguna pampanga, laguna quezon, address laguna, liliw laguna, sought laguna, laguna, laguna wins |
| 19 | 29 | quezon coconut, coconut industry, cagayan, cacao, arrested rizal, coconut, quezon, cavinti, launches, mushroom |
| 20 | 29 | manila bay, laguna water, program laguna, poor laguna, laguna bay, laguna, laguna lake, laguna governor, parañaque, probe laguna |
| 21 | 29 | calamba laguna, mabini batangas, flood rizal, flash flood, calamba city, away floodwaters, mabini, floodwaters, flood antipolo, away flood |
| 22 | 27 | says batangas, batangas city, batangas town, projects batangas, batangas district, quezon mayor, activities batangas, batangas leviste, pogo, batangas |
| 23 | 27 | says batangas, quezon provincial, pampanga, batangas new, san jose, project meralco, meralco, batangas, project quezon, deal batangas |
| 24 | 26 | dasmariñas cavite, dasmariñas city, cavite, dasmariñas, imus cavite, city cavite, quezon town, tanza cavite, areas quezon, lucena city |
| 25 | 25 | quezon province, batangas laguna, northern quezon, province batangas, laguna batangas, laguna, batangas ports, batangas port, cargo, batangas transport |
| 26 | 23 | lipa city, bacoor cavite, visit, rizal town, bacoor city, cavite quezon, laguna, leviste, kadiwa, marcos |
| 27 | 22 | barangay, manila laguna, laguna areas, mabitac laguna, floods laguna, rizal typhoon, laguna bay, mabitac, typhoon uwan, communities |
| 28 | 22 | lucena city, cavite, bacoor, lucena, silang cavite, villar, areas, teases, lopez, south |
| 29 | 21 | quezon towns, areas quezon, calamity quezon, quezon town, barangay, cities laguna, quezon province, lucena city, pablo city, calamity amid |
| 30 | 21 | waterways, calamba city, flooded, cavite town, landfill, floods, residents cavite, san mateo, floods hit, rodriguez rizal |
| 31 | 20 | cavite resort, cavite tagaytay, cavite, sanctuary cavite, new cavite, maragondon cavite, naic cavite, 2023 cavite, carmona cavite, cavite lgu |
| 32 | 20 | bataan, bulacan cavite, p10, early, pedro laguna, bulacan, venture, cavite towns, pcg, center |
| 33 | 19 | quezon city, rizal town, quezon town, rizal, manila, batangas town, calatagan, quezon, nearby, rosa laguna |
| 34 | 19 | batangas city, cavite, city, city missing, paeng, batangas port, port, rosario cavite, passengers batangas, cavite lgu |
| 35 | 18 | manila, says pagasa, quezon province, northern quezon, quezon tropical, pepito, hits quezon, tropical, quezon quezon, paolo |
| 36 | 18 | laguna cavite, laguna, projects cavite, coastal, cavite, expands cavite, alfonso cavite, silang cavite, hub cavite, cavite cavite |
| 37 | 17 | majayjay, cavite, laguna quezon, rizal, laguna, laguna bay, binangonan, angono rizal, victims, resort |
| 38 | 17 | cavite, cavite bridge, flood, quezon town, flood antipolo, dasmariñas cavite, rizal landslide, rains, tagaytay city, dead quezon |
| 39 | 16 | cavite laguna, laguna, resort, rizal province, cops, cavite, captured, authorities, quezon, province |
| 40 | 16 | cavite city, cavite, batangas city, quezon province, quezon town, fisherfolk, police, rosario cavite, kapuso, cardona |
| 41 | 16 | laguna, sanctuary cavite, dasmariñas city, philippine, journey, sanctuary, islands, cavite, rizal, village |
| 42 | 15 | support local, bridge, uplb, filipino, balayan, program laguna, laguna gov, local gov, fda, local |
| 43 | 15 | batangas police, police, quezon, lucena city, batangas road, van, sa, city, collision quezon, taytay rizal |
| 44 | 14 | cavite gov, cavite opens, bacoor cavite, cavite, projects cavite, cavite ncr, pbbm cavite, imus cavite, new cavite, landmark |
| 45 | 14 | typhoon victims, cities bulacan, town batangas, lucena city, quezon town, montalban rizal, city lgu, typhoon, cities, montalban |
| 46 | 14 | manila cavite, quezon province, manila, cavite areas, plaza, zambales bataan, zambales, rizal areas, areas saturday, pampanga |
| 47 | 14 | calamity storm, monsoon rains, monsoon, disaster, calamity amid, storm, calamity declared, rains, massive cavite, calamity effects |
| 48 | 13 | laguna, zamboanga, ecija batangas, bacoor, pampanga, davao, vilma santos, mandanas, vilma, batangas |
| 49 | 13 | lipa city, p9, city, forge, city hall, la, leads opening, mayor, leads, pcso |
| 50 | 13 | manila, batangueño, cavite robredo, binangonan rizal, cavite, kawit cavite, 780, angono rizal, revilla, bong revilla |
| 51 | 12 | quezon province, quezon towns, laguna quezon, free laguna, quezon opens, laguna, batangas laguna, lucena city, laguna governor, hernandez |
| 52 | 12 | batangas city, quezon city, city batangas, parañaque, quezon, rizal areas, cainta, july, areas, feb |
| 53 | 12 | laguna police, cavite pnp, laguna, cavite, rizal, bacoor city, quezon, sabong, director, police director |
| 54 | 11 | manila, program laguna, production laguna, laguna bay, ecosystem, bay, laguna, fisheries, fishers, agri |
| 55 | 11 | calaca city, cavite, batangas city, caviteño, city batangas, tayabas city, bataan cavite, calaca, town batangas, quezon province |
| 56 | 11 | rizal towns, philippines, manila, quezon town, ncr rizal, rizal, rizal province, maynilad, marikina, project manila |
| 57 | 10 | arrested cavite, cavite arrested, cavite resort, cavite, nabbed cavite, dasmariñas cavite, vs cavite, dasmariñas, rizal province, bulacan |
| 58 | 10 | laguna cavite, barangays, laguna, philippine, cavite, calamba, san, villages, marcos jr, marcos |

### Reading

- **Stability.** The full corpus gives topics that pass the stability gate set before the run. The 55-title E59 fit did not pass (mean ARI 0.38).
- **Content.** Most topics are organised by **place names and general news**: tourism and local culture, industrial and economic projects, crime and arrests, politics, road accidents. They are not food-insecurity themes.
- **Food-relevant topics.** A minority of topics are about hazards and livelihoods:
  - floods, typhoons, evacuations and calamity declarations: topics 4, 8, 14, 17, 21, 27, 29, 30, 35, 38, 45 and 47;
  - fisheries, fish species and coastal or lake ecosystems: topics 12 and 54;
  - coconut and other crops: topic 19.
- **SO1 verdict.** SO1's "latent food insecurity risk patterns" are therefore **only partly** what these topics are. They describe what the province-attributed news is about, mostly not food risk.
- **What this is.** The topics are descriptive. The model is fitted on all quarters, so later articles shape the topics of earlier quarters, and they are **not** forecast features. Nothing is served and no forecast changes.
