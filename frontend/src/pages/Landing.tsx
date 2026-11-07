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
            A geospatial system that forecasts food-insecurity risk in the five CALABARZON provinces with the thesis
            model E168 (LightGBM), validated on DOST-FNRI provincial food-security surveys.
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
            aiPHeed forecasts food-insecurity risk in the five CALABARZON provinces. For each province, the thesis model
            E168 gives the probability that at least half of households will be moderately or severely food insecure in
            the coming quarter, as measured by the DOST-FNRI Household Food Insecurity Access Scale (HFIAS). The number
            shown is that probability, from 0 to 1; 0.50 or higher is shown as High risk. It is a forecast, not an
            official statistic or a measured food-insecurity rate.
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
              a map of the provinces, each coloured Low or High for the selected quarter; quarters before 2027-Q1 are
              back-forecasts made with only the data available at the time;
            </li>
            <li>
              the relative influence of the five risk-driver groups and of the other model inputs on each forecast,
              from E168's SHAP values (the shares add up to 100%). Influence is not a cause;
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
            <li>downloadable PDF reports, and back-forecasts for past quarters, labelled as forecasts.</li>
          </ul>
        </div>
      </Card>
    </Section>
  );
}

/* ---------------- METHODOLOGY ---------------- */
const SOURCES = [
  { s: "DOST-FNRI food-security surveys (HFIAS)", m: "Share of households moderately or severely food insecure (the forecast target and starting point)", p: "NNS 2013, FNRI 2015, ENNS 2018, 2019, 2021", l: "Provincial" },
  { s: "PSA Consumer Price Index (food, rice, headline)", m: "Price changes faced by households", p: "to the issue date", l: "Provincial" },
  { s: "PSA palay, corn and fisheries production", m: "Changes in local food production", p: "to the issue date", l: "Provincial" },
  { s: "NASA POWER rainfall and soil moisture", m: "Rain and dryness compared with normal", p: "to the issue date", l: "Provincial (centroid)" },
  { s: "IBTrACS (NOAA) tropical cyclone tracks", m: "Typhoons passing near the province", p: "to the issue date", l: "Provincial" },
  { s: "NOAA Oceanic Niño Index", m: "El Niño / La Niña conditions", p: "to the issue date", l: "Global" },
  { s: "PSA Labor Force Survey", m: "Unemployment rate and its change", p: "to the issue date", l: "National" },
  { s: "Bangko Sentral ng Pilipinas cash remittances", m: "Change in money sent home by overseas Filipinos", p: "to the issue date", l: "National" },
  { s: "PSA 2021 Small Area Estimates of poverty; 2020 Census", m: "Poverty, subsistence and population density", p: "2021 / 2020 (fixed)", l: "Provincial and municipal" },
  { s: "PSA regional household consumption", m: "Household consumption relative to the region", p: "to the issue date", l: "Regional" },
  { s: "News headlines (Filipino and English)", m: "Food Stress Sentiment Index and topic shares", p: "2013 to 2026-Q4; a forecast uses only those published before its issue date", l: "Provincial, area and national" },
  { s: "Social Weather Stations (SWS) involuntary hunger", m: "Used only to scale how confident each forecast is", p: "to the issue date", l: "Area (e.g. Balance Luzon)" },
];

/* The thesis model E168 (backend/app/e168/lgbm.py; docs/e168/PROTOCOL.md). */
const STEPS = [
  {
    t: "What High risk means",
    d: "A province is High risk in a quarter when at least half of its households are moderately or severely food insecure on the DOST-FNRI Household Food Insecurity Access Scale (HFIAS). The forecast is the probability of that.",
  },
  {
    t: "Starting point",
    d: "Each forecast starts from the province's most recent DOST-FNRI survey result, adjusted toward its own history or its region (chosen automatically on past data only).",
  },
  {
    t: "LightGBM adjustment",
    d: "A LightGBM model learns how survey results changed between rounds from food prices, climate (rain, soil moisture, typhoons, El Niño), food production, employment, remittances, poverty, density and news. It is refitted at each issue date using only data published before it.",
  },
  {
    t: "Confidence and classification",
    d: "The adjusted score is shrunk toward 50% by an amount learned from past forecasts, then turned into a probability. 0.50 or above is High risk; the threshold was fixed in advance and not tuned.",
  },
  {
    t: "City and municipal ranking",
    d: "Each city or municipality's value is the province probability multiplied by a vulnerability weight of 60% poverty incidence (PSA 2021) and 40% population density (2020 census), ranked within the province. On the map it takes its province's risk colour.",
  },
];

/* What the backend does (services/dashboard.py, services/review.py): every forecast is served unless an
   administrator rejects it; a rejected province-quarter is withheld (ForecastWithheld). */
const NOTES = [
  {
    t: "Forecast lead",
    d: "Forecasts are issued on the first day of each quarter for the next quarter, using only information published before the issue date. By the study's rule (at least 75% accuracy) E168 is reliable up to three quarters ahead.",
  },
  {
    t: "Missing data",
    d: "A missing value is never counted as zero or as low risk: LightGBM treats it as missing. Provinces with fewer than 5 news articles in the quarter are marked Limited data.",
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
          Survey history from 2013 is used. Every input is taken as it was published before each issue date.
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
/* E168's locked evaluation (backend/data/e168/out/results.json): 72 DOST-FNRI province results per lead (ENNS 2018, 2019,
   2021), each forecast made only with data published before it. */
const LEADS = [
  { label: "Lead 1: one quarter ahead", reliable: true, acc: "0.778", prec: "0.622", rec: "0.920", f1: "0.742", auc: "0.895", tested: "72 province results (56 correct)" },
  { label: "Lead 2: two quarters ahead", reliable: true, acc: "0.764", prec: "0.605", rec: "0.920", f1: "0.730", auc: "0.887", tested: "72 province results (55 correct)" },
  { label: "Lead 3: three quarters ahead", reliable: true, acc: "0.750", prec: "0.595", rec: "0.880", f1: "0.710", auc: "0.860", tested: "72 province results (54 correct)" },
];
const LEAD_METRICS = [
  ["acc", "Accuracy"],
  ["prec", "Precision"],
  ["rec", "Recall"],
  ["f1", "F1"],
  ["auc", "AUC"],
] as const;
const BRIER = [
  ["E168 (served forecast)", "0.139"],
  ["Naive persistence (last survey)", "0.213"],
  ["Logistic regression, combined", "0.307"],
  ["Logistic regression, government data only", "0.234"],
  ["Logistic regression, news only", "0.218"],
  ["LightGBM, government data only", "0.137"],
  ["LightGBM, news only", "0.149"],
];
const RESULTS = [
  {
    t: "Lead time",
    d: "By the study's rule (at least 75% accuracy) E168 is reliable up to three quarters ahead (0.778, 0.764 and 0.750). Under six stricter checks it passes all six one quarter ahead, and five of six two quarters ahead: the lower confidence bound of accuracy (0.641) is just below always guessing Low (0.653), because only 72 survey results are available.",
  },
  {
    t: "Against the baselines",
    d: "E168 is more accurate than every comparison model one quarter ahead (persistence 0.625, logistic regression 0.597 to 0.639, LightGBM on one data source 0.667 to 0.736) and has a clearly better Brier score than persistence and the logistic models.",
  },
  {
    t: "Where it makes mistakes",
    d: "Most errors are false alarms near 50% in ENNS 2018, after food insecurity fell nationwide between 2015 and 2018. F1 is 0.742, just under the 0.75 target, because the model catches 92% of High provinces at the cost of some false alarms.",
  },
  {
    t: "What could not be tested, and the next test",
    d: "DOST-FNRI has not published provincial food-security results after 2021, so the forecasts for 2023 to 2026 cannot be checked. The 2027-Q1 forecast was sealed before any outcome existed (SHA-256 28f2c918) and will be scored when a provincial survey covering it is published.",
  },
];

function ReliableTag() {
  return (
    <span className="tint-primary inline-flex items-center rounded-full px-2.5 py-0.5 text-[12px] font-semibold leading-5">
      Meets the 75% accuracy rule
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
        E168 food-insecurity forecast by lead time: tested on DOST-FNRI provincial surveys
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
        Accuracy falls the further ahead the forecast looks. Leads 1 to 3 meet the study's 75% accuracy rule; Lead 1 also
        passes all six stricter reliability checks.
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
          All results below are retrospective: each forecast used only data published before it, but the 72 survey
          results were also examined during development. The sealed 2027-Q1 forecast is the first unseen test.
        </p>
        <LeadTimeTable />
        <div className="mt-10 lg:max-w-[50%]">
          <MetricTable
            title="Brier score against the baselines, one quarter ahead (lower is better)"
            note="Same 72 province results. E168 is significantly better than naive persistence and the three logistic regressions; against the two single-source LightGBM models the difference is not significant."
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
  "A probability, not a measured rate. The number is the forecast probability that at least half of a province's households are moderately or severely food insecure (HFIAS). It is not an official statistic or classification.",
  "Validated on survey years only. E168 was tested on 72 DOST-FNRI province results from 2018, 2019 and 2021. DOST-FNRI has not published provincial results after 2021, so the quarters shown for 2023 to 2026 are back-forecasts that cannot be checked.",
  "Some inputs are national. Unemployment, remittances and El Niño are national or global figures, the same for every province; their influence is national context, not a provincial measurement.",
  "City and municipal values are a relative prioritization within each province, based on the province forecast, poverty and population density. They are not forecasts for each city or municipality.",
  "News has limits. Headlines were collected after the fact and classified automatically; the classifier's check against human-annotated headlines is reported separately. Recent coverage is thin (a few to a dozen articles per province per quarter), and a quarter with no articles reads as neutral news.",
  "Inputs are today's releases. Price, production and labour figures are the versions available now; later revisions were not available at the historical issue dates. Survey results are dated to the middle of the survey year.",
  "Influence is not a cause. The driver shares are SHAP attributions of the model's forecast; they show what the model relied on, not what caused food insecurity.",
  "Small sample. Only 72 survey results per lead time are available, and they were used throughout development; the sealed 2027-Q1 forecast is the true test.",
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
    a: "A student research system that forecasts food-insecurity risk in the five CALABARZON provinces with the thesis model E168 (LightGBM), tested on DOST-FNRI provincial food-security surveys. It is not an official statistic.",
  },
  {
    q: "Is the score the probability that people will go hungry?",
    a: "No. It is the forecast probability that at least half of the province's households are moderately or severely food insecure (HFIAS). It is not the share of people who will go hungry. Provinces at 0.50 or above are shown as High risk.",
  },
  {
    q: "Did the Department of Agriculture develop or endorse aiPHeed?",
    a: "No. aiPHeed was developed by a student research team at De La Salle University - Dasmariñas. Its intended users are planning staff of DA Region IV-A.",
  },
  {
    q: "How far ahead does it forecast?",
    a: "Forecasts are issued on the first day of each quarter for the next quarter, using only information published before that date. By the study's 75% accuracy rule, E168 is reliable up to three quarters ahead.",
  },
  {
    q: "How accurate is it?",
    a: "On 72 DOST-FNRI province results, accuracy was 0.778 one quarter ahead, 0.764 two quarters ahead and 0.750 three quarters ahead (always predicting Low: 0.653). AUC was 0.895 one quarter ahead. See \"How accurate it is\".",
  },
  {
    q: "Are the city and municipal values forecasts?",
    a: "No. They are a relative priority ranking: the province forecast multiplied by a weight of 60% poverty incidence and 40% population density, shown in the province's risk colour. Within a province they follow the poverty and density order.",
  },
  {
    q: "Is SWS hunger the forecast target?",
    a: "No. The target is the DOST-FNRI provincial food-security survey (HFIAS). SWS hunger (published for areas such as Balance Luzon, not for provinces) is used only to scale how confident each forecast is.",
  },
  {
    q: "What happens when data is missing?",
    a: "The missing input is treated as missing, never as zero or low risk. Provinces with fewer than 5 news articles in the quarter are marked Limited data.",
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
              aiPHeed forecasts food-insecurity risk for the five CALABARZON provinces with the thesis model E168
              (LightGBM), tested on DOST-FNRI provincial food-security surveys. It is not an official statistic.
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
