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
            A geospatial system that forecasts food-insecurity risk in the five CALABARZON provinces one to three
            quarters ahead, using the approved E168 LightGBM model.
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
            aiPHeed forecasts food-insecurity risk in the five CALABARZON provinces with the approved E168 model. A
            province is at High risk in a quarter when 50% or more of its households are moderately or severely food
            insecure on the FNRI Household Food Insecurity Access Scale (HFIAS). The number shown is the forecast
            probability of High risk, from 0 to 1; a probability of 0.50 or higher is shown as High risk. It is a model
            forecast, not an official statistic or a measured food-insecurity rate.
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
              a map of the provinces, each coloured Low or High for the selected quarter, one to three quarters
              ahead of the issue date;
            </li>
            <li>
              each province's forecast: the probability of High risk, the forecast share of food-insecure households
              with its 90% range, and which inputs had published values at the issue date;
            </li>
            <li>
              the relative influence of the main factor groups on each forecast, from the model's exact additive
              contributions. Influence is not a cause;
            </li>
            <li>
              recent news headlines in Filipino and English about food prices, harvests, weather and jobs in the
              province, shown as context;
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
/* The approved forecast (E168): backend/app/e168/lgbm_only.py, serve.py; docs/final/FINAL_SYSTEM_REPORT_E168.md. */
const STEPS = [
  {
    t: "What High risk means",
    d: "A province is High risk in a quarter when 50% or more of its households are moderately or severely food insecure on the FNRI Household Food Insecurity Access Scale (HFIAS). FNRI measures this by province in its nutrition surveys.",
  },
  {
    t: "Survey starting point",
    d: "Each forecast starts from the province's latest FNRI survey level published before the issue date (surveys are released about six quarters after fieldwork).",
  },
  {
    t: "Forecast change (LightGBM)",
    d: "A small, strongly regularised LightGBM model forecasts how much the province's level will change from that starting point, using only information published before the issue date. All choices are made on training data only.",
  },
  {
    t: "Classification",
    d: "The forecast level and its uncertainty give the probability of High risk. It is classed High risk at 0.50 or above and Low risk below 0.50.",
  },
  {
    t: "City and municipal ranking",
    d: "Each city or municipality's value is the province's E168 probability multiplied by a vulnerability weight of 60% poverty incidence (PSA 2021) and 40% population density (POPCEN 2024), ranked within the province and the region. On the map it takes its province's risk colour.",
  },
];

/* What the backend does (services/dashboard.py, services/review.py): every forecast is served unless an
   administrator rejects it; a rejected province-quarter is withheld (ForecastWithheld). */
const NOTES = [
  {
    t: "Forecast lead",
    d: "Forecasts are issued at the start of a quarter, using only information published before the issue date, for the next one, two and three quarters. All three meet the acceptance rule: accuracy of at least 75% and better than the latest survey.",
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
  return (
    <Section id="methodology" title="Methodology">
      <Card>
        <div>
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
/* Figures from backend/data/e168/out/thesis_metrics.json and lead_horizon.json (E168, 72 provincial forecasts for the
   ENNS 2018, 2019 and 2021 rounds); baselines on the same rows from backend/data/e151/out/prov_oof.csv. */
const LEADS = [
  { label: "1 quarter ahead", reliable: true, acc: "0.750", prec: "0.595", rec: "0.88", f1: "0.71", auc: "0.891", tested: "72 provincial forecasts, 3 survey rounds" },
  { label: "2 quarters ahead", reliable: true, acc: "0.778", prec: "0.629", rec: "0.88", f1: "0.73", auc: "0.893", tested: "72 provincial forecasts, 3 survey rounds" },
  { label: "3 quarters ahead", reliable: true, acc: "0.750", prec: "0.600", rec: "0.84", f1: "0.70", auc: "0.873", tested: "72 provincial forecasts, 3 survey rounds" },
  { label: "4 quarters ahead (not shown on the map)", acc: "0.736", prec: "0.588", rec: "0.80", f1: "0.68", auc: "0.860", tested: "72 provincial forecasts, 3 survey rounds" },
];
const LEAD_METRICS = [
  ["acc", "Accuracy"],
  ["prec", "Precision"],
  ["rec", "Recall"],
  ["f1", "F1"],
  ["auc", "AUC"],
] as const;
const BRIER = [
  ["LightGBM (E168, served forecast)", "0.123"],
  ["Naive persistence (latest survey)", "0.213"],
  ["PSA indicators only (logistic)", "0.228"],
  ["News only (logistic)", "0.219"],
  ["Logistic regression, all inputs", "0.307"],
];
const RESULTS = [
  {
    t: "Lead time",
    d: "The acceptance rule (accuracy of at least 75% and a Brier score significantly better than reusing the latest survey) is met 1, 2 and 3 quarters ahead. Four quarters ahead accuracy is 0.736, so the furthest accepted lead is three quarters. The model still beats the latest survey up to six quarters ahead.",
  },
  {
    t: "The 75% accuracy goal",
    d: "Met 1 to 3 quarters ahead: 54 of 72 forecasts correct one quarter ahead (0.750), against 0.625 for reusing the latest survey and 0.653 for always predicting Low. One and three quarters ahead are exactly at 75%, so one more wrong forecast would fall below it. The rule was set on 7 November 2026, after these results were known.",
  },
  {
    t: "Known tendencies",
    d: "The model rarely misses a High province (recall 0.84 to 0.88) but about 2 in 5 High calls were false alarms. On average it over-predicts the food-insecure share by about 3 points, more in Luzon. Of the factor groups tested one at a time, only market prices measurably improved accuracy.",
  },
  {
    t: "What could not be tested, and the next test",
    d: "Only 5 of the 72 tested forecasts are CALABARZON provinces, all observed Low, so detecting a High province in CALABARZON is untested. The forecasts for the ENNS 2022 survey round were sealed before their outcomes were known (SHA-256 f8228fae) and will be scored when FNRI publishes provincial results.",
  },
];

function ReliableTag() {
  return (
    <span className="tint-primary inline-flex items-center rounded-full px-2.5 py-0.5 text-[12px] font-semibold leading-5">
      Meets the acceptance rule
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
        E168 food-insecurity risk forecast by lead time: chronological, as-of predictions
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
        Accuracy falls the further ahead the forecast looks. The map shows the forecasts 1, 2 and 3 quarters ahead.
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
          All results below are development evidence: every tested survey round was examined while the system was
          being built, and no unseen round has been scored yet.
        </p>
        <LeadTimeTable />
        <div className="mt-10 lg:max-w-[50%]">
          <MetricTable
            title="Brier score against the baselines, one quarter ahead (lower is better)"
            note="Same 72 provincial forecasts. The advantage over naive persistence is statistically established (95% interval below zero); against the other baselines only the point estimates are compared."
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
  "A forecast probability, not a measurement. The number is E168's forecast probability that 50% or more of a province's households are moderately or severely food insecure (FNRI HFIAS). It is not a measured food-insecurity rate, and not an official statistic or classification.",
  "Validated on few survey rounds. The forecast was tested on 72 provincial forecasts from three FNRI survey rounds (2018, 2019, 2021). Only 5 were CALABARZON provinces, all observed Low.",
  "The acceptance rule was set after the results. Accuracy of at least 75% and better than the latest survey was adopted on 7 November 2026, after these results were known; one and three quarters ahead are exactly at 75%.",
  "City and municipal values are a relative prioritization within each province, based on the province forecast, poverty and population density. They are not forecasts for each city or municipality. Some cities have no PSA 2021 municipal poverty estimate; this is stated where it applies.",
  "News has limits. Only headlines are used, collected after the fact, and the news dataset was reviewed and signed off by Department of Agriculture staff; no item-by-item second annotation was done.",
  "Missing data is not low risk. When a source has not yet published, the input is left blank. The dashboard says which inputs are missing.",
  "Back-test results are not live results. They were computed after the fact on survey rounds examined during development. The sealed forecasts for the ENNS 2022 round will be a true test.",
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
    a: "A student research system that forecasts food-insecurity risk in the five CALABARZON provinces. The map shows the approved E168 forecast: the probability that 50% or more of a province's households are moderately or severely food insecure (FNRI HFIAS). It is a model forecast, not an official statistic.",
  },
  {
    q: "Is the score the probability that people will go hungry?",
    a: "No. It is the forecast probability that 50% or more of a province's households are moderately or severely food insecure (FNRI HFIAS). It is not the share of people who will go hungry. Provinces at 0.50 or above are shown as High risk.",
  },
  {
    q: "Did the Department of Agriculture develop or endorse aiPHeed?",
    a: "No. aiPHeed was developed by a student research team at De La Salle University - Dasmariñas. Its intended users are planning staff of DA Region IV-A.",
  },
  {
    q: "How far ahead does it forecast?",
    a: "Forecasts are issued at the start of a quarter, using only information published before that date, for the next one, two and three quarters. All three meet the acceptance rule.",
  },
  {
    q: "How accurate is it?",
    a: "One quarter ahead, 54 of 72 past provincial forecasts were correct (0.750), against 0.625 for reusing the latest survey. Two and three quarters ahead: 0.778 and 0.750. All results come from survey rounds examined during development; see \"How accurate it is\".",
  },
  {
    q: "Are the city and municipal values forecasts?",
    a: "No. They are a relative priority ranking: the province forecast multiplied by a weight of 60% poverty incidence and 40% population density, shown in the province's risk colour. Within a province they follow the poverty and density order.",
  },
  {
    q: "Why does the forecast start from a survey?",
    a: "FNRI's nutrition surveys are the only provincial measure of household food insecurity. Each forecast starts from the latest published survey level and forecasts the change from it with LightGBM.",
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
              aiPHeed forecasts food-insecurity risk for the five CALABARZON provinces with the approved E168 model:
              a LightGBM forecast of the change from each province's latest FNRI survey level. It is not an official
              statistic.
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
