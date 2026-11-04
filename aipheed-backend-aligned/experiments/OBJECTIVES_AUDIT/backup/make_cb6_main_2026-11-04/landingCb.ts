// Landing-page text for the C-b food-insecurity forecast (served when /api/v1/config reports the indicator
// "regional_food_insecurity_forecast"). Every figure comes from the served evaluation (CbEvaluation); the
// descriptions follow NEW_MODEL/NEWS_V2/PLAN.md, FOOD_INSECURITY_SYSTEM/PLAN.md and foodinsecurity_system.py.
import { type CbEvaluation, fmt } from "@/lib/servedModel";

export const CB_ABOUT = [
  "aiPHeed forecasts food insecurity for CALABARZON each quarter. Its forecast is the probability that involuntary hunger in Balance Luzon, as measured by the Social Weather Stations (SWS) surveys, will be above 11.3% in the quarter starting on the issue date and in the next quarter. A probability of 0.50 or higher is shown as High. It is not an official statistic or a measured food-insecurity rate.",
  "SWS measures hunger for Balance Luzon, not for each province. The forecast is therefore regional: every province has the same High or Low class. Each province's score and each city or municipality's value weight the regional forecast by PSA poverty incidence (and, for cities and municipalities, population density). They are vulnerability-weighted estimates, not measured provincial or municipal hunger rates.",
];

export const CB_ABOUT_LIST = [
  "a map of the five provinces, coloured by the regional High or Low class, with each province's vulnerability-weighted score;",
  "the relative influence of each indicator group on the forecast, from SHAP values (influence is not a cause);",
  "news evidence in Filipino and English: XLM-RoBERTa scores headlines against bilingual food-stress hypotheses without labelled training data, giving the Food Stress Sentiment Index (FSSI). The FSSI anomaly is a model input; its measured effect on the forecast is close to zero;",
  "a priority ranking of all 142 cities and municipalities: the province score times a vulnerability weight of 60% poverty incidence and 40% population density within the province. These are relative priorities, not forecasts for each city or municipality;",
  "downloadable PDF reports, and back-test results for past quarters, labelled as development evidence.",
];

export const CB_SOURCES = [
  { s: "Social Weather Stations (SWS) involuntary hunger", m: "Share of families that experienced hunger (the outcome, and its recent history as inputs)", p: "Survey rounds from 1998, as published before each issue date", l: "Regional (Balance Luzon)" },
  { s: "PSA Consumer Price Index (food, headline, rice)", m: "Year-on-year and recent monthly price changes", p: "As published before each issue date", l: "Region IV-A" },
  { s: "World Bank Commodity Price Data (Pink Sheet)", m: "World rice, cereal, crude oil and urea prices", p: "As published before each issue date", l: "World" },
  { s: "NOAA Oceanic Niño Index (ONI)", m: "El Niño / La Niña conditions", p: "As published before each issue date", l: "Global" },
  { s: "IBTrACS (NOAA) tropical cyclone tracks", m: "Typhoons passing near the provinces", p: "As available at each issue date", l: "Provincial, averaged" },
  { s: "PSA palay, corn and fisheries production", m: "Drops in local food production", p: "Quarters published before each issue date", l: "Region IV-A" },
  { s: "Google News headlines (Filipino and English)", m: "FSSI anomaly: food-stress sentiment against its own recent quarters", p: "From 2021 (anomaly from 2023-Q2); only headlines published before the issue date", l: "Region IV-A" },
  { s: "PSA 2021 Small Area Estimates of poverty; PSA 2023 provincial poverty", m: "Vulnerability weights for the province and LGU outputs (not model inputs)", p: "Fixed", l: "Provincial and municipal" },
  { s: "PSA 2024 Census of Population (POPCEN)", m: "Population density for the LGU weight (not a model input)", p: "2024 (fixed)", l: "Municipal" },
];

export const CB_STEPS = [
  { t: "What High means", d: "High means the forecast probability that SWS involuntary hunger in Balance Luzon exceeds 11.3% in the target quarter is 0.50 or more. The 11.3% line and the 0.50 cut were fixed before scoring." },
  { t: "Inputs", d: "Hunger history (latest reading, change, four-quarter mean and a horizon-specific probability), local food, headline and rice price changes, world food, oil and fertilizer prices, El Niño status, typhoons, crop and fisheries production, and the FSSI news anomaly: 21 inputs, each taken from data published before the issue date." },
  { t: "Model", d: "One LightGBM model trained on all forecast leads together (model C-b), refitted at every issue date from 1998 onward with a fixed settings grid chosen on earlier quarters only." },
  { t: "Province and city/municipal values", d: "Province score = regional probability times the province's poverty incidence relative to the poorest province; the class stays regional. City and municipal values = province score times 60% poverty incidence and 40% population density, normalized within the province." },
];

export function cbNotes(e: CbEvaluation | null) {
  const mrlt = e?.max_reliable_lead;
  return [
    { t: "Forecast lead", d: `Forecasts are issued on the first day of each quarter for the quarter starting then and the next quarter, using only information published before the issue date. Under the study's 75% accuracy rule the furthest reliable lead is ${mrlt ?? "n/a"} quarter${mrlt === 1 ? "" : "s"}; under the project's stricter seven reliability rules it is ${e?.max_reliable_lead_r1_r7 ?? "n/a"}, because accuracy in 2015-2020 was below 0.60.` },
    { t: "Missing data", d: "A missing value is never counted as zero or as low risk. An input with no published value at the issue date is left blank." },
    { t: "Review before publication", d: "Issued forecasts are staged and are not public until an authorized administrator approves them; a rejected forecast is withheld. Every decision is recorded with the reviewer, the reason and the time." },
  ];
}

export function cbResults(e: CbEvaluation | null) {
  const l1 = e?.leads["1"];
  const l2 = e?.leads["2"];
  return [
    { t: "Lead time", d: `Leads 1 to 8 were tested walk-forward. Lead 1 (accuracy ${fmt(l1?.metrics.accuracy)}) and Lead 2 (${fmt(l2?.metrics.accuracy)}) meet the 75% rule; Lead 3 does not (${fmt(e?.leads["3"]?.metrics.accuracy)}).` },
    { t: "Ranking quality and the AUC target", d: `AUC is ${fmt(l1?.metrics.auc)} at Lead 1 and ${fmt(l2?.metrics.auc)} at Lead 2, below the study's 0.80 target.` },
    { t: "Stability", d: "Accuracy in 2015-2020, when hunger crossed the 11.3% line back and forth, was below the 0.60 stability requirement. Many SWS readings in that period were close to the line, within their own sampling error, which explains part of the difficulty but not all of it." },
    { t: "What could not be tested, and the next test", d: `No provincial or municipal hunger measure exists, so the province and city/municipal values cannot be validated as hunger rates. The forecasts issued on ${e?.seal_issue_date ?? "the latest issue date"} were sealed before their outcomes were known${e?.seal_sha256 ? ` (SHA-256 ${e.seal_sha256.slice(0, 8)})` : ""}; the first four sealed quarters of 2027 will be the blind test.` },
  ];
}

export function cbDisclaimer(e: CbEvaluation | null) {
  return [
    "A regional probability. The number is the forecast probability that Balance Luzon involuntary hunger (SWS) exceeds 11.3%. It is not a measured food-insecurity rate, and not an official statistic or classification.",
    "Regional hunger is not provincial. SWS publishes Balance Luzon only, with a sampling error of about 4 to 6 percentage points. Province and city/municipal values are vulnerability-weighted estimates of the regional forecast, not measured local hunger.",
    "City and municipal values are relative priorities. They depend on PSA poverty estimates, some of which have wide margins of error, and on population density; small differences in rank are not meaningful.",
    "News has limits. Only headlines are used. The FSSI news anomaly is an input of the model, but it changed none of the past High/Low calls.",
    `Back-test results are not live results. All ${e?.leads["1"]?.n_quarters ?? ""} evaluated quarters were examined during development; only sealed forecasts scored after their outcomes are published are a true test.`,
    "Missing data is not low risk. When a source has not yet published, the input is left blank.",
    "aiPHeed outputs must not replace official assessment procedures or be used as official food-insecurity classifications or policy recommendations.",
  ];
}

export function cbFaqs(e: CbEvaluation | null) {
  const l1 = e?.leads["1"];
  return [
    { q: "What is aiPHeed?", a: "A forecast of food insecurity for CALABARZON: the probability that involuntary hunger in Balance Luzon (SWS) is above 11.3% this quarter and next, with vulnerability-weighted province and city/municipal priorities. It is a student research system, not an official statistic." },
    { q: "Is the score the probability that people will go hungry?", a: "No. It is the forecast probability that the regional hunger rate exceeds 11.3%. Province and city/municipal values weight it by poverty (and density); they are not hunger rates." },
    { q: "Did the Department of Agriculture develop or endorse aiPHeed?", a: "No. aiPHeed was developed by a student research team at De La Salle University - Dasmariñas. Its intended users are planning staff of DA Region IV-A." },
    { q: "How far ahead does it forecast?", a: `Two leads: the quarter starting on the issue date and the next quarter. Both met the study's 75% accuracy rule in back-tests; neither met the stricter stability rule.` },
    { q: "How accurate is it?", a: `In back-tests on ${l1?.n_quarters ?? ""} quarters (${l1?.period ?? ""}), accuracy was ${fmt(l1?.metrics.accuracy)} at Lead 1 against ${fmt(l1?.persistence_accuracy)} for repeating the latest reading; AUC ${fmt(l1?.metrics.auc)}. These quarters were examined during development.` },
    { q: "Why does every province have the same class?", a: "Because hunger is measured for Balance Luzon only. aiPHeed does not invent provincial hunger figures; provinces differ only in their poverty-weighted scores." },
    { q: "What happens when data is missing?", a: "The missing input is left blank, never counted as zero." },
    { q: "How often is it updated?", a: "Once per quarter, after the source data are refreshed. Issued forecasts become public only after an authorized administrator approves them." },
    { q: "Where can I get official food-security information?", a: "From the Department of Agriculture Regional Field Office IV-A, the Philippine Statistics Authority and other mandated agencies. Their websites are listed at the bottom of this page." },
  ];
}

export const CB_FOOTER =
  "aiPHeed forecasts food insecurity for CALABARZON each quarter: the probability that Balance Luzon hunger (SWS) exceeds 11.3%, from hunger history, prices, climate, production and Filipino-English news, with vulnerability-weighted province and city/municipal priorities. It is not an official statistic.";
