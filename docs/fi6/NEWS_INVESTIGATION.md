# News usefulness investigation (FI6-N)

## 0. Why the current news cannot help, whatever the features

| Finding | Evidence | Consequence |
|---|---|---|
| The corpus starts in 2021 | 9,628 headlines, 2021-01 to 2026-10 | 2010–2020 training and test quarters have no corpus news, so LightGBM cannot learn a news effect, and only ~20 labelled quarters with 6 HIGH overlap with news |
| It was collected retrospectively through a search engine | Google News RSS with `after:`/`before:`. Probe on 2026-11-02: 0–11 items per targeted query per quarter for 2008–2019, against hundreds per quarter after 2021 | Coverage is whatever the engine still indexes, so volume grows 193 → 882 per quarter; the trend is collection, not events |
| Headlines only | 730 of 9,667 leads could be extracted (robots or bot walls) | Location, numbers and event detail are mostly lost |
| Weak geography | 67 % of headlines have no province | Province FSSI is mostly the regional value |
| Restated statistics | Inflation, unemployment and remittance release headlines | They duplicate government features already in the model |

**What the model needs is a source-consistent, date-stamped archive that covers the same years as the target.**
Better classification of the 2021+ headlines cannot fix a coverage problem.

## 1. What a food-insecurity forecaster needs from news (by domain)

* **The rule.** FEWS NET and IPC analysis rests on observed shocks to availability and access, and on household
  coping and hardship. WFP HungerMap's nowcasts lean on prices, climate shocks, conflict and macroeconomic stress.
  Balashankar et al. (2023) found news useful when it was read as signals of specific drivers.
* **What qualifies.** So the useful news is **events that change food availability or household purchasing power
  before official statistics show them**, plus **direct reports of hardship**.

| Domain | Event types to collect (risk-increasing unless stated) | Not useful / handled separately |
|---|---|---|
| Market and prices | price spikes of rice or staples, shortages, supply/import disruption, hoarding, crop or post-harvest losses that reduce supply; *risk-reducing*: price falls, supply restored | PSA inflation-release headlines (restate CPI) |
| Climate stress | typhoon, flood, drought or El Niño, extreme rain or heat damaging crops, fisheries or livestock; agricultural damage figures (₱, hectares); distribution blocked by weather | weather forecasts without impact |
| Employment | layoffs, closures, retrenchment, livelihood loss (farmers, fishers, drivers), work stoppages; *risk-reducing*: hiring, job recovery | PSA LFS release headlines (restate unemployment) |
| OFW remittances | OFW repatriation or displacement, deployment bans, host-country crises, remittance disruption | BSP remittance-release headlines (restate remittances) |
| Poverty and vulnerability | families unable to obtain food, hunger or malnutrition reports, evacuation or displacement, loss of homes or income; assistance **needs** | an assistance *announcement* is a government response, not evidence that hunger went up or down |

## 2. Sources

Only sources that publish a public, date-filtered archive and whose robots.txt allows API access, so every year is
collected the same way.

| Source | Type | Archive from | Access | robots.txt | Use |
|---|---|---|---|---|---|
| Rappler | national news | 2012 | WordPress REST API (title, date, excerpt) | allowed | main volume |
| Bulatlat | alternative press (labour, farmers, poor communities) | 2008 | WP REST | allowed (crawl-delay 10 s) | hardship and livelihood events; editorial stance recorded |
| VERA Files | investigative / fact-check | 2008 | WP REST | allowed | background |
| NewsBytes.PH | national news | 2012 | WP REST | allowed | volume |
| PinoyWeekly | alternative press | ~2008 | WP REST (redirect) | allowed (5 s) | hardship and livelihood events |
| PCIJ | investigative | ~2008 | WP REST | allowed | background |

**Excluded:**
* **Login required:** Inquirer (its robots.txt also disallows crawling), DA, DSWD IV-A.
* **robots.txt disallows:** BusinessMirror.
* **Behind bot walls:** Manila Bulletin, PIA, DA IV-A.
* **No public API:** PNA, Philstar, GMA.

Official agency figures (NDRRMC damage, PAGASA, PSA) already enter as government indicators. The Google News corpus
from 2021 on stays as the Objective 1 province-quarter corpus but is **not** a model input, because its collection
regime differs.

## 3. Queries and collection

* **Geographic anchors** (one query per site × year × anchor; WordPress search requires every word): Batangas,
  Cavite, Laguna, Quezon, Rizal, CALABARZON, "Southern Tagalog", Lucena, Antipolo, Calamba.
* **National driver queries:** OFW, remittance, repatriation, "deployment ban", "rice price", "rice shortage",
  "food prices", layoff, retrenchment, "El Niño", "typhoon damage", "crop damage", hunger, malnutrition, gutom,
  bigas.
* **Kept per article:** WordPress id, title, publication date (the site's `date`, Philippine time), modified date,
  URL, excerpt (lead text), source, query, retrieval time. The retrieval time is never used as a publication date.
* **Storage:** raw responses stay local (third-party text, gitignored); derived features, ledgers and counts are
  committed.

## 4. Geography

1. **Namesakes masked first:** Quezon City, Manuel Quezon, Jose Rizal, Rizal Park, Rizal Avenue, Rizal Memorial.
2. **Province attribution:** a province counts when its name appears unmasked. "Quezon" and "Rizal" also need
   "province", "lalawigan ng", or a co-occurring LGU of that province.
3. **LGU attribution:** an LGU counts when its name appears with its province, or when the name is distinctive (for
   example Dasmariñas, Antipolo, Calamba, Lucena). Common names (San Juan, Santa Cruz, Rosario, Bay, Real, Pila…)
   need the province.
4. **Region-wide:** CALABARZON, Southern Tagalog, Region IV-A, Laguna de Bay.
5. **Recorded per article:** `geo_level` (lgu / province / region / national) and every affected province. No
   location is invented. National articles count only in the remittance domain and, where marked national, the
   market domain.

## 5. Classification (XLM-RoBERTa zero-shot, then BERTopic)

* **Tier 1:**
  1. A recall-oriented keyword gate on title + excerpt.
  2. XLM-R domain labels (unchanged hypotheses).
  3. **Event-type hypotheses per domain** (section 1), **direction** ("makes it harder for families to get
     enough food" vs "makes it easier"), and evidence type (risk / ongoing disruption / observed hardship /
     government response / background).
* **Restated-statistic flag:** a rule, not ML. It fires when the text reports an official release that the model
  already uses (inflation rate, unemployment rate, remittance figure, poverty statistics).
* **Severity:** regex extraction of ₱ damage amounts, hectares, and families or persons affected/evacuated.
* **Events:**
  * Articles collapse to one event when they share a domain, have cosine ≥ 0.85, and fall within 10 days.
  * The number of independent sources per event is kept.
  * One event counts once per quarter, however many outlets report it.
* **Tier 2:** BERTopic is fitted on 2012–2016 relevant events and then frozen. Topics stay descriptive, not model
  inputs.

## 6. Features (per quarter, as-of quarter end; at most two per domain)

* **Main feature, `risk_events_<domain>`:** the number of CALABARZON-attributed (or national, for remittance)
  risk-increasing events, excluding restated statistics, divided by the number of CALABARZON-anchored articles
  collected in that quarter from the same sources. Dividing by coverage controls for changing volume, so a province
  or year with more journalists does not look worse. The share is z-scored against earlier quarters only.
* **`climate_damage`:** log of the total ₱ agricultural damage reported in CALABARZON climate events.
* **`displaced_families`:** log of the number of families reported affected or evacuated.

Seven news features in all, each used only from its publication date.

## 7. Validation of the news dataset

1. **Coverage audit:** articles per source per quarter, anchored share, and the share of each domain.
2. **Date audit:** publication ≤ retrieval, modified vs published, and no article after its quarter's issue date
   used.
3. **Geography audit:** rule-based attributions, with counts by level.
4. **Human annotation kit:** 200 stratified archive articles (relevance, domain, event type, direction,
   geography, hunger report). The model labels are hidden. Precision, recall and kappa are reported once a person
   fills it. Until then the labels are reported as unverified.

## 8. Forecasting test (locked before running, same FI6 target, origins and rules)

* **Comparisons:**
  1. government only;
  2. news only;
  3. government + news;
  4. government + news without each news domain, one at a time.
* **Measures:** accuracy, precision, recall, F1, AUC, Brier, and HIGH detection.
* **Early-warning check:** do news-only features move before the official indicators?
* **What counts as an improvement:** a gain is claimed only if the bootstrap interval of the Brier difference
  excludes 0.
