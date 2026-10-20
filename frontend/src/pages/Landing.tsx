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
            aiPHeed estimates the relative risk of food insecurity in each of the five CALABARZON provinces two
            quarters ahead. It combines public data on prices, poverty, climate, food production, jobs, remittances,
            news and hunger into one index from 0 to 1. A score of 0.50 or higher is shown as High risk. The index is
            not an official statistic.
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
            <li>a map of the provinces, each coloured Low or High for the forecast quarter;</li>
            <li>
              each province's domain scores, each indicator's value, score and status, and which data were available
              at the issue date;
            </li>
            <li>
              a food-price-pressure forecast from a LightGBM model, two quarters ahead. It is one input to the index
              and is also shown on its own;
            </li>
            <li>
              news evidence in Filipino and English: XLM-RoBERTa scores news headlines against ten bilingual
              food-insecurity hypotheses without labelled training data, and the resulting Food Stress Sentiment Index
              is used only when a province has at least 5 articles;
            </li>
            <li>
              a priority ranking of all 142 cities and municipalities, from the province estimate weighted by PSA
              poverty incidence (60 percent) and population density (40 percent). These values are a relative
              prioritization within each province, not forecasts for each city or municipality;
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
  { s: "Bangko Sentral ng Pilipinas cash remittances", m: "Change in money sent home by overseas Filipinos", p: "2021 to 2025-Q4", l: "National" },
  { s: "PAGASA El Niño Alert, Advisory and Climate Advisory", m: "Whether an official El Niño advisory was in force", p: "Dated advisories, 2021 to 23 September 2026", l: "National" },
  { s: "IBTrACS (NOAA) tropical cyclone tracks", m: "Typhoons passing within 300 km", p: "2021 to 2026-Q2 (2026-Q3 incomplete)", l: "Provincial" },
  { s: "Social Weather Stations (SWS) involuntary hunger", m: "Share of families that experienced hunger", p: "Survey rounds 2021 to 2026-Q2 (latest 17.3%)", l: "Regional (Balance Luzon)" },
  { s: "Google News headlines (Filipino and English)", m: "Food-stress content of local news", p: "1 January 2021 to 14 October 2026 (9,667 headlines)", l: "Provincial" },
];

const STEPS = [
  {
    t: "Indicator scores",
    d: "Each indicator is scored from 0 to 1 by comparing it with its own earlier values. A score of 0.50 means the indicator is at its usual level; higher scores mean more risk.",
  },
  {
    t: "Six domains",
    d: "Indicators are grouped into six domains, each scored as the average of its available indicators: affordability (the LightGBM food-price-pressure forecast, headline inflation, rice prices); household vulnerability (poverty and density); climate and food production; household economy (national unemployment and remittances); news (only with at least 5 articles); and regional hunger (SWS, Balance Luzon).",
  },
  {
    t: "Combining the domains",
    d: "Domains are weighted by how closely each followed observed regional hunger in earlier quarters, using only survey rounds published before the issue date, with the weights pulled toward equal weights. At least 4 of the 6 domains are required; otherwise the province shows Insufficient data.",
  },
  {
    t: "Classification",
    d: "The index is classed High risk at 0.50 or above and Low risk below 0.50. The 0.50 threshold was fixed in advance and not tuned.",
  },
  {
    t: "City and municipal ranking",
    d: "Each city or municipality's value is the province index multiplied by a vulnerability weight of 60% poverty incidence (PSA 2021) and 40% population density (POPCEN 2024), ranked within the province and the region.",
  },
];

/* What the backend does (services/dashboard.py, services/review.py): every forecast is served unless an
   administrator rejects it; a rejected province-quarter is withheld (ForecastWithheld). */
const NOTES = [
  {
    t: "Forecast lead",
    d: "Estimates are issued at the start of each quarter for the quarter two quarters ahead (Lead-2), using only information published before the issue date.",
  },
  {
    t: "Missing data",
    d: "A missing value is never counted as zero or as low risk. An indicator with no published value at the issue date is left out of its domain and marked missing; a domain with no indicators is left out, and the number of domains used is shown.",
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
          <SubHeading>How the index is built</SubHeading>
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
/* Figures copied exactly from FINAL_THESIS_SYSTEM_REPORT.md sections 1-2 and 11 and /api/v1/config (FIRI v2); never rounded here. */
/* LightGBM food-price-pressure lead-time table: report section 11 (sealed walk-forward predictions) = /api/v1/config modelPerformance.leads. */
const LEADS = [
  { label: "One quarter ahead (Lead 1)", acc: "0.85", prec: "0.83", rec: "0.71", f1: "0.77", auc: "0.90", tested: "60 province-quarters, 12 quarters" },
  { label: "Two quarters ahead (Lead 2)", onMap: true, acc: "0.72", prec: "0.63", rec: "0.56", f1: "0.59", auc: "0.65", tested: "50 province-quarters, 10 quarters" },
  { label: "Three quarters ahead (Lead 3)", acc: "0.62", prec: "0.40", rec: "0.43", f1: "0.41", auc: "0.62", tested: "45 province-quarters, 9 quarters" },
];
const LEAD_METRICS = [
  ["acc", "Accuracy"],
  ["prec", "Precision"],
  ["rec", "Recall"],
  ["f1", "F1"],
  ["auc", "AUC"],
] as const;
const BRIER = [
  ["LightGBM (proposed)", "0.178"],
  ["I. Naive persistence", "0.400"],
  ["II. PSA-only indicators", "0.598"],
  ["III. News-only sentiment", "0.235"],
  ["IV. Logistic regression", "0.646"],
];
const RESULTS = [
  {
    t: "Lead time",
    d: "Leads of one, two and three quarters were tested. No lead met the pre-registered reliability criterion, so no reliable forecast horizon has been established.",
  },
  {
    t: "The 75% accuracy goal",
    d: "Not demonstrated for the LightGBM: accuracy was 0.72 on 50 province-quarters and 0.78 on the 45 comparison rows. Neither can be told apart from always predicting Low, and neither was measured on unseen quarters.",
  },
  {
    t: "Risk index against observed regional hunger",
    d: "Two quarters ahead, the regional average index matched whether SWS hunger in Balance Luzon was above 11.3% with accuracy 0.94 over 17 quarters; always predicting elevated and the regional hunger outlook alone each scored 0.71. No paired test establishes an advantage over these baselines. The outcome is regional, the index also uses SWS hunger as an input, and every quarter was examined during development.",
  },
  {
    t: "What could not be tested, and the next test",
    d: "No provincial or municipal food-insecurity measure exists for CALABARZON, so the index cannot be validated as a measure of food insecurity in a province or city. The estimates for 2026-Q4 and 2027-Q1 were sealed before their outcomes were known and will be scored once PSA price data for October 2026 to March 2027 and the SWS rounds for those quarters are published.",
  },
];

function OnMapTag() {
  return (
    <span className="tint-primary inline-flex items-center rounded-full px-2.5 py-0.5 text-[12px] font-semibold leading-5">
      The forecast shown on the map
    </span>
  );
}

function LeadTimeTable() {
  const th = "px-3 py-3 text-left text-[12px] font-semibold uppercase tracking-[0.1em] text-ink-muted";
  const num = "px-3 py-3 text-right font-mono text-[14px] font-semibold text-foreground";
  const onMap = "bg-[hsl(var(--primary)/0.08)]";
  return (
    <div>
      <p className="mb-2 font-bold text-foreground leading-snug">
        Food-price-pressure forecast (LightGBM) by lead time: sealed walk-forward predictions
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
              <tr key={r.label} className={`border-t edge-faint ${r.onMap ? onMap : ""}`}>
                <th scope="row" className="px-3 py-3 text-left align-middle text-[14px] font-semibold text-foreground">
                  <span className="block">{r.label}</span>
                  {r.onMap && (
                    <span className="mt-1 block">
                      <OnMapTag />
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
          <li key={r.label} className={`px-4 py-4 ${i ? "border-t edge-faint" : ""} ${r.onMap ? onMap : ""}`}>
            <p className="font-semibold text-foreground leading-snug">{r.label}</p>
            {r.onMap && (
              <p className="mt-1">
                <OnMapTag />
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

      <p className="mt-3">Accuracy falls the further ahead the forecast looks; the map forecasts two quarters ahead.</p>
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
            title="Brier score against the four baselines (lower is better)"
            note="Same 45 province-quarters. The advantage is statistically established only against the PSA-only and logistic-regression baselines."
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
  "A proxy index, not a probability. The risk index is an estimate built from related indicators. It is not a probability, not a measured food-insecurity rate, and not an official statistic or classification.",
  "Not validated as a measure of food insecurity. No provincial or municipal food-insecurity measure exists for CALABARZON to check the index against.",
  "Regional hunger is not provincial. The hunger figure comes from SWS surveys of Balance Luzon. The same value is used for all five provinces, with a sampling error of about 4 to 6 percentage points.",
  "Some inputs are national. Unemployment and remittances are national figures, the same for every province, and remittance data ends in 2025-Q4.",
  "City and municipal values are a relative prioritization within each province, based on the province estimate, poverty and population density. They are not forecasts for each city or municipality. The poverty value for Lucena City is a substitute that has not been verified.",
  "News has limits. Only headlines are used, collected after the fact, and the news classifier was checked against AI-labelled headlines, not a human-reviewed set. Many province-quarters have fewer than 5 articles, so news often does not enter the index. News, topics and El Niño information have no measured effect on forecast accuracy.",
  "Missing data is not low risk. When a source has not yet published, the indicator is left out and the estimate is based on fewer domains. The dashboard says which inputs are missing.",
  "Back-test results are not live results. Past-quarter results were computed after the fact on quarters examined during development. Only the sealed 2026-Q4 and 2027-Q1 estimates will be a true test.",
  // Quarter counts from /api/v1/config modelPerformance: LightGBM leads 1-3 use 12, 10 and 9 quarters; the FIRI v2 regional result at Lead 2 uses 17.
  "Small sample. The food-price-pressure forecast has only 9 to 12 quarters of evidence for each lead time, and the risk index's regional result two quarters ahead rests on 17 quarters. There was one El Niño episode in 2021 to 2026.",
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
    a: "An estimated food-insecurity risk index for the five CALABARZON provinces, forecast two quarters ahead to support planning. It is a student research system, not an official statistic.",
  },
  {
    q: "Is the score the probability that people will go hungry?",
    a: "No. It is an index from 0 to 1 built from related indicators, not a probability or a measured food-insecurity rate. Provinces at 0.50 or above are shown as High risk.",
  },
  {
    q: "Did the Department of Agriculture develop or endorse aiPHeed?",
    a: "No. aiPHeed was developed by a student research team at De La Salle University - Dasmariñas. Its intended users are planning staff of DA Region IV-A.",
  },
  {
    q: "How far ahead does it forecast?",
    a: "Two quarters. Each estimate is issued at the start of a quarter, using only information published before that date. No forecast horizon has yet met the study's reliability criterion.",
  },
  {
    q: "How accurate is it?",
    a: "Two quarters ahead, the food-price-pressure model reached 0.72 accuracy on past data, below the 75% goal. The risk index matched observed regional hunger with accuracy 0.94 over 17 past quarters, but that outcome is regional. All results come from quarters examined during development; see \"How accurate it is\".",
  },
  {
    q: "Are the city and municipal values forecasts?",
    a: "No. They are a relative priority ranking: the province estimate multiplied by a weight of 60% poverty incidence and 40% population density. Within a province they follow the poverty and density order.",
  },
  {
    q: "Why is the same hunger figure used for every province?",
    a: "SWS publishes hunger for Balance Luzon, not for each province. aiPHeed uses that regional figure as one domain and labels it as regional.",
  },
  {
    q: "What happens when data is missing?",
    a: "The missing indicator is left out, never counted as zero, and the dashboard says which inputs were missing. If fewer than 4 of the 6 domains are available, no estimate is shown.",
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
              aiPHeed estimates food-insecurity risk for the five CALABARZON provinces each quarter, two quarters
              ahead. It uses the FIRI v2 risk index, with a LightGBM food-price-pressure forecast as one input, and
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
