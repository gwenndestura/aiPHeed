import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ArrowRight, ChevronDown } from "lucide-react";
import { TopNavbar } from "@/components/TopNavbar";
import { FeedbackModal } from "@/components/FeedbackModal";
import { useAuth } from "@/lib/auth";
import logoDark from "@/assets/logo-dark.png";
import logoLight from "@/assets/logo-light.png";
import heroBg from "@/assets/hero-bg.jpg";
import { readStorage } from "@/lib/storage";

const THEME_KEY = "aipheed_theme";

/* The hero photo sits under a warm tint in both themes (CLAUDE.local.md allows this gradient): the dark
   theme's --background, then a low-opacity primary amber and risk red toward the right. The text sits on
   the photo, so it uses the dark theme's own --foreground values. */
const HERO_TINT =
  "bg-[linear-gradient(115deg,hsl(240_7%_5%/0.84)_0%,hsl(240_7%_5%/0.66)_45%,hsl(var(--primary)/0.30)_80%,hsl(var(--risk-high)/0.34)_100%)]";
const HERO_TEXT = "hsl(36 22% 92%)";
const HERO_MUTED = "hsl(36 22% 92% / 0.78)";

const GMA_URL = "https://www.gmanetwork.com/news/specials/content/193/the-hunger-pandemic/";

export default function Landing() {
  useEffect(() => {
    const t = (readStorage(THEME_KEY) as "light" | "dark" | null) ?? "dark";
    document.documentElement.classList.toggle("light", t === "light");
  }, []);

  return (
    <div className="min-h-screen w-full bg-background text-foreground">
      <div className="sticky top-0 z-[1002]">
        <TopNavbar />
      </div>

      <Hero />
      <main>
        <About />
        <Methodology />
        <Accuracy />
        <Disclaimer />
        <FAQ />
      </main>
      <Footer />
    </div>
  );
}

/* ---------------- SHARED ---------------- */
/** A section below the hero: a centred heading in spaced capitals, then its content. */
function Section({ id, title, children }: { id: string; title: string; children: React.ReactNode }) {
  return (
    <section id={id} aria-labelledby={`${id}-title`} className="scroll-mt-20 px-4 sm:px-8 py-14 sm:py-20">
      <h2
        id={`${id}-title`}
        className="mb-8 sm:mb-10 text-center text-[20px] sm:text-[24px] font-bold uppercase tracking-[0.14em] text-foreground"
      >
        {title}
      </h2>
      {children}
    </section>
  );
}

/** One large rounded floating card. */
function Card({ children }: { children: React.ReactNode }) {
  return (
    <div className="surface-card mx-auto max-w-[1200px] p-6 sm:p-10 lg:p-12 text-[15px] leading-[1.8] text-ink-secondary">
      {children}
    </div>
  );
}

function SubHeading({ children }: { children: React.ReactNode }) {
  return <h3 className="mb-3 text-[17px] font-bold leading-snug text-foreground">{children}</h3>;
}

/** A short paragraph with a bold subheading (optionally numbered). */
function Point({ n, title, children }: { n?: number; title: string; children: React.ReactNode }) {
  return (
    <div>
      <h4 className="font-bold text-foreground">
        {n !== undefined && <span className="mr-1.5">{n}.</span>}
        {title}
      </h4>
      <p className="mt-1">{children}</p>
    </div>
  );
}

/* ---------------- HERO ---------------- */
function Hero() {
  // Server-confirmed session only (see lib/auth.tsx).
  const isAdmin = useAuth().status === "authenticated";
  const outline =
    "group inline-flex items-center justify-center gap-2 h-12 px-7 rounded-full border font-semibold text-[15px] transition-colors hover:bg-[hsl(36_22%_92%/0.12)] focus:outline-none focus-visible:ring-2 focus-visible:ring-ring";
  return (
    <section className="relative isolate flex min-h-[calc(100svh-64px)] items-center overflow-hidden px-4 sm:px-8 lg:px-16 py-16 sm:py-20">
      <img src={heroBg} alt="" aria-hidden className="absolute inset-0 -z-10 h-full w-full object-cover" />
      <div aria-hidden data-hero-tint className={`absolute inset-0 -z-10 ${HERO_TINT}`} />

      <div className="mx-auto w-full max-w-[1200px]">
        <div data-hero-text className="max-w-4xl text-left">
          <h1
            className="font-bold leading-[1.1] text-[clamp(2.1rem,5vw,3.75rem)]"
            style={{ color: HERO_TEXT }}
          >
            Food Insecurity Risk Forecasting System for Region IV-A
          </h1>
          <p className="mt-5 max-w-3xl text-[clamp(1.05rem,1.8vw,1.3rem)] leading-relaxed" style={{ color: HERO_MUTED }}>
            A geospatial system that estimates the food insecurity risk of the five CALABARZON provinces.
          </p>

          <div className="mt-9 flex flex-wrap gap-3">
            <Link
              to="/dashboard"
              className="group inline-flex items-center justify-center gap-2 h-12 px-7 rounded-full bg-primary text-[hsl(var(--primary-ink))] font-semibold text-[15px] shadow-control transition-[filter] hover:brightness-105 focus:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            >
              Explore the map
              <ArrowRight aria-hidden className="h-4 w-4 transition-transform group-hover:translate-x-1" />
            </Link>
            <a href="#methodology" className={outline} style={{ color: HERO_TEXT, borderColor: HERO_MUTED }}>
              How it works
            </a>
            {isAdmin && (
              <Link to="/admin" className={outline} style={{ color: HERO_TEXT, borderColor: HERO_MUTED }}>
                Go to admin dashboard
              </Link>
            )}
          </div>
        </div>
      </div>

      <p className="absolute bottom-3 right-4 sm:right-6 text-[12px]" style={{ color: HERO_MUTED }}>
        Photo by Atom Araullo on{" "}
        <a href={GMA_URL} target="_blank" rel="noopener noreferrer" className="underline hover:opacity-80">
          GMA News
        </a>
      </p>
    </section>
  );
}

/* ---------------- ABOUT ---------------- */
function About() {
  return (
    <Section id="about" title="About aiPHeed">
      <Card>
        <div className="space-y-5">
          <p>
            aiPHeed forecasts the risk of food insecurity in each of the five CALABARZON provinces for the current
            quarter and, as an experimental forecast, the next quarter. Following the study's definition, a province is
            at High risk in a quarter when regional hunger measured by SWS (Balance Luzon) is above 11.3% and the
            province's food prices are rising unusually fast. The number shown is the forecast probability of High
            risk, from 0 to 1; a probability of 0.50 or higher is shown as High risk. It is not an official statistic
            or a measured food-insecurity rate.
          </p>
          <p>
            aiPHeed was developed as a thesis for the Bachelor of Science in Computer Science with Intelligent Systems
            Track at De La Salle University - Dasmariñas. Researchers: Destura, Princess Gwenn A.; Esico, Christina M.;
            and Melindo, Angel Vhea P. The Department of Agriculture did not develop aiPHeed and has not endorsed it.
          </p>
          <p>
            It is intended for planning staff of the Department of Agriculture Regional Field Office IV-A
            (CALABARZON). It is published through a publicly accessible geospatial dashboard, which shows:
          </p>
          <ul className="list-disc pl-6 space-y-2 marker:text-primary">
            <li>
              a map of the provinces, each coloured Low or High for the selected quarter; the current quarter is the
              tested forecast and the next quarter is labelled experimental;
            </li>
            <li>
              each province's forecast in its two parts, the chance that regional hunger is above 11.3% and the chance
              of an unusual food-price rise, and which inputs had published values at the issue date;
            </li>
            <li>
              the relative influence of each indicator group on the LightGBM food-price forecast, from its SHAP
              values. Influence is not a cause;
            </li>
            <li>
              news evidence in Filipino and English: XLM-RoBERTa scores news headlines against ten bilingual
              food-insecurity hypotheses without labelled training data, and the resulting Food Stress Sentiment Index
              is computed only when a province has at least 5 articles. The headlines are shown as context;
            </li>
            <li>
              a priority ranking of all 142 cities and municipalities, from the province forecast weighted by PSA
              poverty incidence (60 percent) and population density (40 percent), shown in the province's risk colour.
              These values are a relative prioritization within each province, not forecasts for each city or
              municipality;
            </li>
            <li>downloadable PDF reports, and back-test estimates for past quarters, labelled as development evidence.</li>
          </ul>
        </div>
      </Card>
    </Section>
  );
}

/* ---------------- METHODOLOGY ---------------- */
const SOURCES = [
  { s: "PSA Consumer Price Index (food and headline)", m: "Price changes faced by households", p: "2021 to August 2026", l: "Provincial" },
  { s: "PSA wholesale rice prices", m: "Change in the price of rice", p: "2021 to 2026-Q2", l: "Provincial" },
  { s: "PSA 2021 Small Area Estimates of poverty", m: "Share of the population below the poverty line", p: "2021 (fixed)", l: "Municipal, combined to provincial" },
  { s: "PSA 2024 Census of Population (POPCEN)", m: "Population and land area, for density", p: "2024 (fixed)", l: "Municipal, combined to provincial" },
  { s: "PSA palay, corn and fisheries production", m: "Drops in local food production", p: "2021 to 2026-Q2", l: "Provincial" },
  { s: "PSA Labor Force Survey", m: "Change in the unemployment rate", p: "2021 to 2026-Q2", l: "National" },
  { s: "Bangko Sentral ng Pilipinas cash remittances", m: "Change in money sent home by overseas Filipinos", p: "2021 to 2026-Q2", l: "National" },
  { s: "World Bank Commodity Price Data (Pink Sheet)", m: "World rice, cereal, oil and fertilizer prices", p: "2021 to August 2026", l: "World" },
  { s: "PAGASA El Niño Alert, Advisory and Climate Advisory", m: "Whether an official El Niño advisory was in force", p: "Dated advisories, 2021 to 23 September 2026", l: "National" },
  { s: "IBTrACS (NOAA) tropical cyclone tracks", m: "Typhoons passing within 300 km", p: "2021 to 2026-Q2 (2026-Q3 incomplete)", l: "Provincial" },
  { s: "Social Weather Stations (SWS) involuntary hunger", m: "Share of families that experienced hunger", p: "Survey rounds 2021 to 2026-Q2 (latest 17.3%)", l: "Regional (Balance Luzon)" },
  { s: "Google News headlines (Filipino and English)", m: "Food-stress content of local news", p: "1 January 2021 to 14 October 2026 (9,667 headlines); a forecast uses only those published before its issue date", l: "Provincial" },
  { s: "GDELT news event database", m: "Share of Philippine food-security news about prices", p: "2021 to 2026-Q3", l: "National" },
];

/* The served Chapter I forecast (P0H4): backend/app/ml/inference/ch1_system.py INDICATOR and LEAD2_OPTIMIZATION. */
const STEPS = [
  {
    t: "What High risk means",
    d: "Following the study's definition, a province is High risk in a quarter when SWS hunger in Balance Luzon is above 11.3% (its 2021-2022 60th percentile) and the province's food inflation, or food inflation minus headline inflation, is above the province's own 2021-2022 60th percentile. No hunger survey covers a single province, so the provinces differ only through food prices.",
  },
  {
    t: "Hunger condition",
    d: "The chance that Balance Luzon hunger is above 11.3% in the target quarter, from the latest SWS reading published before the issue date and from how much SWS readings in all four SWS areas have moved over the same span since 2021.",
  },
  {
    t: "Food-price condition",
    d: "One LightGBM model, trained on all forecast leads together, gives the chance that the province's food prices rise unusually fast. Its inputs are 12 indicator families (food-price projection, headline inflation, rice prices, poverty and density, El Niño status, typhoons, rice and corn harvests, fisheries production, unemployment, remittances, news, and the regional hunger outlook) and world food and fertilizer prices. It is refitted at each issue date using only data published before it.",
  },
  {
    t: "Classification",
    d: "The forecast probability is the hunger chance multiplied by the food-price chance. It is classed High risk at 0.50 or above and Low risk below 0.50. The 0.50 threshold was fixed in advance and not tuned.",
  },
  {
    t: "City and municipal ranking",
    d: "Each city or municipality's value is the province probability multiplied by a vulnerability weight of 60% poverty incidence (PSA 2021) and 40% population density (POPCEN 2024), ranked within the province and the region. On the map it takes its province's risk colour.",
  },
];

/* What the backend does (services/dashboard.py, services/review.py): every forecast is served unless an
   administrator rejects it; a rejected province-quarter is withheld (ForecastWithheld). */
const NOTES = [
  {
    t: "Forecast lead",
    d: "Forecasts are issued on the first day of each quarter, using only information published before the issue date: one for the quarter just starting and one for the next quarter, three months ahead. Only the forecast for the quarter just starting passed the reliability test; the three-months-ahead forecast is shown as experimental.",
  },
  {
    t: "Missing data",
    d: "A missing value is never counted as zero or as low risk. An input with no published value at the issue date is left blank, and the dashboard lists which inputs were missing.",
  },
  {
    t: "Rejected forecasts are withheld",
    d: "Every province estimate is shown publicly unless an authorized administrator rejects it. A rejected province-quarter is withheld: its score is not published, it is left out of the rankings and the regional average, and the province is shown as withheld. Every decision is recorded with the reviewer, the reason and the time.",
  },
];

function Methodology() {
  const th = "px-4 py-3 text-left text-[12px] font-semibold uppercase tracking-[0.1em] text-ink-muted";
  const td = "px-4 py-3 align-top text-[14px] leading-relaxed";
  return (
    <Section id="methodology" title="Methodology">
      <Card>
        <SubHeading>Data sources</SubHeading>
        <p className="mb-5">
          Only data from 2021 onward is used. Periods are those available at the issue date of 1 October 2026.
        </p>

        {/* Tablet and desktop: a light table. */}
        <div className="hidden md:block overflow-hidden rounded-[var(--radius-inner)] border edge-faint">
          <table className="w-full border-collapse">
            <thead className="bg-[hsl(var(--secondary)/0.55)]">
              <tr>
                <th className={th}>Source</th>
                <th className={th}>What it measures</th>
                <th className={th}>Period used</th>
                <th className={th}>Level</th>
              </tr>
            </thead>
            <tbody>
              {SOURCES.map((r) => (
                <tr key={r.s} className="border-t edge-faint">
                  <td className={`${td} font-semibold text-foreground`}>{r.s}</td>
                  <td className={td}>{r.m}</td>
                  <td className={td}>{r.p}</td>
                  <td className={td}>{r.l}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Phones: the same rows, stacked. */}
        <ul className="md:hidden overflow-hidden rounded-[var(--radius-inner)] border edge-faint">
          {SOURCES.map((r, i) => (
            <li key={r.s} className={`px-4 py-3 text-[14px] leading-relaxed ${i ? "border-t edge-faint" : ""}`}>
              <p className="font-semibold text-foreground">{r.s}</p>
              <p>{r.m}</p>
              <p className="text-ink-muted">
                {r.p} · {r.l}
              </p>
            </li>
          ))}
        </ul>

        <div className="mt-10">
          <SubHeading>How the forecast is built</SubHeading>
          <div className="space-y-5">
            {STEPS.map((s, i) => (
              <Point key={s.t} n={i + 1} title={s.t}>
                {s.d}
              </Point>
            ))}
          </div>
        </div>

        <div className="mt-10">
          <SubHeading>Issue date, missing data and review</SubHeading>
          <div className="space-y-5">
            {NOTES.map((n) => (
              <Point key={n.t} title={n.t}>
                {n.d}
              </Point>
            ))}
          </div>
        </div>
      </Card>
    </Section>
  );
}

/* ---------------- ACCURACY ---------------- */
/* Figures copied exactly from aipheed-backend-aligned/experiments/FINAL_SYSTEM_SELECTION/out/landing_figures.json
   (runner/landing_figures.py): the served P0H4 forecast's walk-forward evaluation (backend/data/ch1_engine/
   evaluation.json) and its Lead-1 Brier comparison; never rounded here. */
const LEADS = [
  { label: "Lead 1: current quarter", reliable: true, acc: "0.84", prec: "0.69", rec: "0.65", f1: "0.67", auc: "0.87", tested: "70 province-quarters, 14 quarters" },
  { label: "Lead 2: three months ahead (experimental)", acc: "0.77", prec: "0.60", rec: "0.35", f1: "0.44", auc: "0.62", tested: "65 province-quarters, 13 quarters" },
  { label: "Lead 3: six months ahead", acc: "0.72", prec: "0.50", rec: "0.24", f1: "0.32", auc: "0.69", tested: "60 province-quarters, 12 quarters" },
];
const LEAD_METRICS = [
  ["acc", "Accuracy"],
  ["prec", "Precision"],
  ["rec", "Recall"],
  ["f1", "F1"],
  ["auc", "AUC"],
] as const;
const BRIER = [
  ["LightGBM (served forecast)", "0.132"],
  ["Naive persistence", "0.257"],
  ["Logistic regression, combined", "0.192"],
  ["Logistic regression, government data only", "0.179"],
  ["Logistic regression, news only", "0.212"],
  ["LightGBM, government data only", "0.086"],
  ["LightGBM, news only", "0.214"],
];
const RESULTS = [
  {
    t: "Lead time",
    d: "Every lead was tested walk-forward against criteria fixed before scoring. Lead 1, the current quarter, passed; Lead 2 and later did not. The furthest reliable lead is therefore the current quarter, and the three-months-ahead forecast is experimental.",
  },
  {
    t: "The 75% accuracy goal",
    d: "Met for the current quarter: accuracy 0.84 (59 of 70 province-quarters), against 0.76 for always predicting Low. Not met three months ahead: accuracy 0.77 is close to always predicting Low (0.74), and only 6 of 17 High cases were found.",
  },
  {
    t: "Why longer leads fail",
    d: "The hunger part follows the newest SWS reading, so it cannot foresee a new hunger surge before SWS publishes it. The 2023-Q4 and 2024-Q2 surges were not visible in any reading published before those forecasts, which caps how many High cases can be found three months ahead.",
  },
  {
    t: "What could not be tested, and the next test",
    d: "No provincial or municipal food-insecurity measure exists for CALABARZON, so the forecast cannot be validated as a measure of food insecurity in a province or city. The forecasts issued on 1 October 2026 were sealed before their outcomes were known (SHA-256 a498b5ef) and will be scored once PSA price data and the SWS rounds for those quarters are published.",
  },
];

function ReliableTag() {
  return (
    <span className="tint-primary inline-flex items-center rounded-full px-2.5 py-0.5 text-[12px] font-semibold leading-5">
      Passed the reliability test
    </span>
  );
}

function LeadTimeTable() {
  const th = "px-3 py-3 text-left text-[12px] font-semibold uppercase tracking-[0.1em] text-ink-muted";
  const num = "px-3 py-3 text-right font-mono text-[14px] font-semibold text-foreground";
  const highlight = "bg-[hsl(var(--primary)/0.08)]";
  return (
    <div>
      <p className="mb-2 font-bold text-foreground leading-snug">
        Food-insecurity risk forecast by lead time: walk-forward predictions
      </p>

      {/* Desktop: one table. */}
      <div className="hidden lg:block overflow-hidden rounded-[var(--radius-inner)] border edge-faint">
        <table className="w-full border-collapse">
          <thead className="bg-[hsl(var(--secondary)/0.55)]">
            <tr>
              <th className={th}>Forecast</th>
              {LEAD_METRICS.map(([, l]) => (
                <th key={l} className={`${th} text-right`}>
                  {l}
                </th>
              ))}
              <th className={th}>Tested on</th>
            </tr>
          </thead>
          <tbody>
            {LEADS.map((r) => (
              <tr key={r.label} className={`border-t edge-faint ${r.reliable ? highlight : ""}`}>
                <th scope="row" className="px-3 py-3 text-left align-middle text-[14px] font-semibold text-foreground">
                  <span className="block">{r.label}</span>
                  {r.reliable && (
                    <span className="mt-1 block">
                      <ReliableTag />
                    </span>
                  )}
                </th>
                {LEAD_METRICS.map(([k]) => (
                  <td key={k} className={num}>
                    {r[k]}
                  </td>
                ))}
                <td className="px-3 py-3 text-[14px] leading-snug">{r.tested}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Phones and tablets: one block per lead time. */}
      <ul className="lg:hidden overflow-hidden rounded-[var(--radius-inner)] border edge-faint">
        {LEADS.map((r, i) => (
          <li key={r.label} className={`px-4 py-4 ${i ? "border-t edge-faint" : ""} ${r.reliable ? highlight : ""}`}>
            <p className="font-semibold text-foreground leading-snug">{r.label}</p>
            {r.reliable && (
              <p className="mt-1">
                <ReliableTag />
              </p>
            )}
            <dl className="mt-3 grid grid-cols-3 sm:grid-cols-5 gap-x-4 gap-y-2">
              {LEAD_METRICS.map(([k, l]) => (
                <div key={k}>
                  <dt className="text-[12px] text-ink-muted">{l}</dt>
                  <dd className="font-mono text-[14px] font-semibold text-foreground">{r[k]}</dd>
                </div>
              ))}
            </dl>
            <p className="mt-2 text-[14px] text-ink-muted">Tested on {r.tested}</p>
          </li>
        ))}
      </ul>

      <p className="mt-3">
        Accuracy falls the further ahead the forecast looks. The map shows the current quarter and the next quarter,
        three months ahead; the next quarter is labelled experimental.
      </p>
    </div>
  );
}

function MetricTable({ title, note, rows }: { title: string; note: string; rows: string[][] }) {
  return (
    <div>
      <p className="mb-2 font-bold text-foreground leading-snug">{title}</p>
      <div className="overflow-hidden rounded-[var(--radius-inner)] border edge-faint">
        <table className="w-full border-collapse">
          <tbody>
            {rows.map(([k, v], i) => (
              <tr key={k} className={i ? "border-t edge-faint" : ""}>
                <th scope="row" className="px-4 py-2.5 text-left text-[14px] font-normal">
                  {k}
                </th>
                <td className="px-4 py-2.5 text-right font-mono text-[14px] font-semibold text-foreground">{v}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="mt-2 text-[14px] leading-relaxed text-ink-muted">{note}</p>
    </div>
  );
}

function Accuracy() {
  return (
    <Section id="accuracy" title="How accurate it is">
      <Card>
        <p className="mb-8">
          All results below are development evidence: every evaluated quarter was examined while the system was being
          built, and no unseen quarter has been scored yet.
        </p>
        <LeadTimeTable />
        <div className="mt-10 lg:max-w-[50%]">
          <MetricTable
            title="Brier score against the baselines, current quarter (lower is better)"
            note="Same 70 province-quarters. The advantage is statistically established against the three logistic regressions and the news-only LightGBM, but not against naive persistence; the LightGBM on government data only scored better."
            rows={BRIER}
          />
        </div>
        <div className="mt-10 space-y-5">
          {RESULTS.map((r) => (
            <Point key={r.t} title={r.t}>
              {r.d}
            </Point>
          ))}
        </div>
      </Card>
    </Section>
  );
}

/* ---------------- DISCLAIMER ---------------- */
const DISCLAIMER = [
  "A probability under a study definition. The number is the forecast probability that a province is High risk as the study defines it: regional SWS hunger above 11.3% and unusually fast food-price rises in the province. It is not a measured food-insecurity rate, and not an official statistic or classification.",
  "Not validated as a measure of food insecurity. No provincial or municipal food-insecurity measure exists for CALABARZON to check the forecast against.",
  "Regional hunger is not provincial. The hunger figure comes from SWS surveys of Balance Luzon. The same value is used for all five provinces, with a sampling error of about 4 to 6 percentage points, so the provinces differ only through food prices.",
  "Some inputs are national. Unemployment, remittances, El Niño status and the GDELT news measure are national figures, the same for every province. The unemployment input mostly follows the calendar trend, so the direction of its influence bar is not a reliable reading of job conditions.",
  "City and municipal values are a relative prioritization within each province, based on the province forecast, poverty and population density. They are not forecasts for each city or municipality. The poverty value for Lucena City is a substitute that has not been verified.",
  "News has limits. Only headlines are used, collected after the fact, and the news classifier was checked against AI-labelled headlines, not a human-reviewed set. The Food Stress Sentiment Index has no measured effect on the forecast; GDELT's national price-news measure improved current-quarter forecasts in one test chosen after earlier results, so that gain is suggestive only.",
  "Missing data is not low risk. When a source has not yet published, the input is left blank. The dashboard says which inputs are missing.",
  "Back-test results are not live results. Past-quarter results were computed after the fact on quarters examined during development. Only the sealed forecasts issued on 1 October 2026 will be a true test.",
  // Quarter counts from FINAL_SYSTEM_SELECTION/out/landing_figures.json: leads 1-3 use 14, 13 and 12 quarters.
  "Small sample. The forecasts have only 12 to 14 quarters of evidence for each lead time, all sharing one regional hunger series. There was one El Niño episode in 2021 to 2026.",
  "aiPHeed outputs must not replace official assessment procedures or be used as official food-insecurity classifications or policy recommendations.",
];

function Disclaimer() {
  return (
    <Section id="disclaimer" title="Data disclaimer and limitations">
      <Card>
        <div className="space-y-4">
          {DISCLAIMER.map((p) => (
            <p key={p}>{p}</p>
          ))}
        </div>
      </Card>
    </Section>
  );
}

/* ---------------- FAQ ---------------- */
const FAQS = [
  {
    q: "What is aiPHeed?",
    a: "A forecast of food-insecurity risk for the five CALABARZON provinces, for the current quarter and, experimentally, the next quarter, to support planning. It is a student research system, not an official statistic.",
  },
  {
    q: "Is the score the probability that people will go hungry?",
    a: "No. It is the forecast probability that a province is High risk as the study defines it: regional hunger above 11.3% and unusually fast food-price rises in the province. It is not the share of people who will go hungry. Provinces at 0.50 or above are shown as High risk.",
  },
  {
    q: "Did the Department of Agriculture develop or endorse aiPHeed?",
    a: "No. aiPHeed was developed by a student research team at De La Salle University - Dasmariñas. Its intended users are planning staff of DA Region IV-A.",
  },
  {
    q: "How far ahead does it forecast?",
    a: "Forecasts are issued on the first day of each quarter, using only information published before that date. The forecast for the quarter just starting passed the reliability test; the forecast three months ahead, for the next quarter, is experimental.",
  },
  {
    q: "How accurate is it?",
    a: "For the current quarter, accuracy was 0.84 on 70 past province-quarters (always predicting Low: 0.76). Three months ahead it was 0.77, close to always predicting Low, and most High cases were missed. All results come from quarters examined during development; see \"How accurate it is\".",
  },
  {
    q: "Are the city and municipal values forecasts?",
    a: "No. They are a relative priority ranking: the province forecast multiplied by a weight of 60% poverty incidence and 40% population density, shown in the province's risk colour. Within a province they follow the poverty and density order.",
  },
  {
    q: "Why is the same hunger figure used for every province?",
    a: "SWS publishes hunger for Balance Luzon, not for each province. aiPHeed uses that regional figure for every province and labels it as regional.",
  },
  {
    q: "What happens when data is missing?",
    a: "The missing input is left blank, never counted as zero, and the dashboard says which inputs were missing.",
  },
  {
    q: "How often is it updated?",
    a: "Once per quarter, after the source data are refreshed. Every estimate is shown publicly unless an authorized administrator rejects it; a rejected province-quarter is withheld and shown as withheld.",
  },
  {
    q: "Where can I get official food-security information?",
    a: "From the Department of Agriculture Regional Field Office IV-A, the Philippine Statistics Authority and other mandated agencies. Their websites are listed at the bottom of this page.",
  },
];

function FAQ() {
  const [open, setOpen] = useState<number | null>(null);
  return (
    <Section id="faq" title="Frequently asked questions">
      <ul className="mx-auto max-w-[1200px] space-y-3">
        {FAQS.map((it, i) => {
          const isOpen = open === i;
          return (
            <li key={it.q} className="surface-card overflow-hidden">
              <h3>
                <button
                  type="button"
                  aria-expanded={isOpen}
                  aria-controls={`faq-${i}`}
                  onClick={() => setOpen(isOpen ? null : i)}
                  className="flex w-full min-h-[60px] items-center gap-4 px-5 sm:px-7 py-4 text-left text-[15px] font-semibold text-foreground transition-colors hover:bg-[hsl(var(--secondary)/0.4)] focus:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-ring"
                >
                  <span className="flex-1">{it.q}</span>
                  <ChevronDown
                    aria-hidden
                    className={`h-5 w-5 shrink-0 text-ink-muted transition-transform ${isOpen ? "rotate-180" : ""}`}
                  />
                </button>
              </h3>
              {isOpen && (
                <p id={`faq-${i}`} className="px-5 sm:px-7 pb-5 text-[15px] leading-[1.8] text-ink-secondary">
                  {it.a}
                </p>
              )}
            </li>
          );
        })}
      </ul>
    </Section>
  );
}

/* ---------------- FOOTER ---------------- */
/* Official sites only; each URL was checked on 2026-10-20 (LANDING_COPY_REVIEW.md section 2.7). */
const RELATED_SITES = [
  { name: "DA Regional Field Office IV-A", url: "https://calabarzon.da.gov.ph/" },
  { name: "Philippine Statistics Authority", url: "https://psa.gov.ph/" },
  { name: "PSA OpenSTAT", url: "https://openstat.psa.gov.ph/" },
  { name: "Social Weather Stations", url: "https://www.sws.org.ph/" },
  { name: "PAGASA", url: "https://www.pagasa.dost.gov.ph/" },
];

const EXPLORE: { label: string; to?: string; href?: string }[] = [
  { label: "Map", to: "/dashboard" },
  { label: "Data", to: "/data" },
  { label: "Visualization", to: "/visualization" },
  { label: "About", href: "#about" },
  { label: "Methodology", href: "#methodology" },
  { label: "Accuracy", href: "#accuracy" },
  { label: "Disclaimer", href: "#disclaimer" },
  { label: "FAQ", href: "#faq" },
];

/* Researchers in the order used everywhere: Destura, Esico, Melindo. */
const TEAM = [
  { name: "Destura", url: "https://www.linkedin.com/in/princess-gwenn-destura" },
  { name: "Esico", url: "https://www.linkedin.com/in/christina-esico/" },
  { name: "Melindo", url: "https://www.linkedin.com/in/angelvheamelindo/" },
];

const FOOT_LINK =
  "transition-colors hover:text-foreground compact:inline-flex compact:items-center compact:min-h-11 compact:min-w-11";
const FOOT_HEAD = "mb-4 text-[13px] font-bold uppercase tracking-[0.14em] text-foreground";

/* The one gradient on the landing page (CLAUDE.local.md style rule): the page background into a soft
   amber and risk-red tint, existing tokens only, low enough that the footer text keeps its contrast. */
const FOOTER_BG =
  "bg-[linear-gradient(135deg,hsl(var(--background))_0%,hsl(var(--background))_40%,hsl(var(--primary)/0.14)_78%,hsl(var(--risk-high)/0.16)_100%)]";

/* The site's feedback form (components/FeedbackModal), its trigger restyled here as a footer link. */
const FEEDBACK_LINK =
  "[&>button[type]]:!text-[14px] [&>button]:text-ink-secondary [&>button]:underline [&>button]:rounded-sm [&>button:hover]:text-foreground [&>button:focus-visible]:outline-none [&>button:focus-visible]:ring-2 [&>button:focus-visible]:ring-ring [&_svg]:hidden";

function Footer() {
  const ext = { target: "_blank", rel: "noopener noreferrer" } as const;
  return (
    <footer className={`mt-6 border-t edge-faint px-4 sm:px-8 pt-14 pb-8 ${FOOTER_BG}`}>
      <div className="mx-auto max-w-[1200px]">
        <div className="grid gap-10 sm:grid-cols-2 xl:grid-cols-[1.5fr_0.8fr_1.2fr_1.1fr] xl:gap-12">
          <div>
            <img src={logoDark} alt="aiPHeed" className="dark-only mb-4 h-11 w-auto object-contain" />
            <img src={logoLight} alt="aiPHeed" className="light-only mb-4 h-11 w-auto object-contain" />
            <p className="text-[14px] leading-[1.8] text-ink-secondary">
              aiPHeed forecasts food-insecurity risk for the five CALABARZON provinces each quarter. It combines a
              regional hunger outlook from SWS with a LightGBM food-price forecast on 12 indicator families, and
              Filipino-English news analysis. It is not an official statistic.
            </p>
          </div>

          <nav aria-label="Explore">
            <h4 className={FOOT_HEAD}>Explore</h4>
            <ul className="space-y-2 compact:space-y-0 text-[14px] text-ink-secondary">
              {EXPLORE.map((e) => (
                <li key={e.label}>
                  {e.to ? (
                    <Link to={e.to} className={FOOT_LINK}>
                      {e.label}
                    </Link>
                  ) : (
                    <a href={e.href} className={FOOT_LINK}>
                      {e.label}
                    </a>
                  )}
                </li>
              ))}
            </ul>
          </nav>

          <div>
            <h4 className={FOOT_HEAD}>Contact</h4>
            <div className="space-y-4 text-[14px] leading-relaxed text-ink-secondary">
              <div>
                <span className="block font-semibold text-foreground">Research team</span>
                <p className="flex flex-wrap items-center gap-x-2">
                  {TEAM.map((m, i) => (
                    <span key={m.name} className="flex items-center gap-x-2">
                      <a href={m.url} {...ext} className={`underline compact:justify-center ${FOOT_LINK}`}>
                        {m.name}
                      </a>
                      {i < TEAM.length - 1 && <span aria-hidden>·</span>}
                    </span>
                  ))}
                </p>
                <div className={`mt-1 ${FEEDBACK_LINK}`}>
                  <FeedbackModal />
                </div>
              </div>
              <p>
                <span className="block font-semibold text-foreground">Official agricultural services</span>
                <a href="https://calabarzon.da.gov.ph/" {...ext} className={`underline ${FOOT_LINK}`}>
                  Department of Agriculture Regional Field Office IV-A (CALABARZON)
                </a>
              </p>
            </div>
          </div>

          <nav aria-label="Related websites">
            <h4 className={FOOT_HEAD}>Related websites</h4>
            <ul className="space-y-2 compact:space-y-0 text-[14px] text-ink-secondary">
              {RELATED_SITES.map((s) => (
                <li key={s.url}>
                  <a href={s.url} {...ext} className={FOOT_LINK}>
                    {s.name}
                  </a>
                </li>
              ))}
            </ul>
          </nav>
        </div>

        <div className="mt-12 border-t edge-faint pt-6 text-[13px] text-ink-muted">
          <p>© 2026 aiPHeed. All rights reserved.</p>
        </div>
      </div>
    </footer>
  );
}
