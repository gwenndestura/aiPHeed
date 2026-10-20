import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { ArrowRight, ChevronDown } from "lucide-react";
import { TopNavbar } from "@/components/TopNavbar";
import { useAuth } from "@/lib/auth";
import logoDark from "@/assets/logo-dark.png";
import { StatusBadge } from "@/components/ui/status-badge";
import { MetricLabel } from "@/components/ui/metric";
import heroBg from "@/assets/hero-bg.jpg";
import { readStorage } from "@/lib/storage";
import { useConfig, useExplainability } from "@/lib/queries";
import { quarterPeriodLabel } from "@/lib/quarters";

const THEME_KEY = "aipheed_theme";

const AMBER = "#F5A623";
const SERIF = "Georgia, 'Times New Roman', Times, serif";
const TILE_BG = "rgba(245,166,35,0.12)";
const TILE_BORDER = "rgba(245,166,35,0.35)";

export default function Landing() {
  const [theme, setTheme] = useState<"light" | "dark">("dark");

  useEffect(() => {
    const t = (readStorage(THEME_KEY) as "light" | "dark" | null) ?? "dark";
    document.documentElement.classList.toggle("light", t === "light");
    setTheme(t);
    const obs = new MutationObserver(() => {
      setTheme(document.documentElement.classList.contains("light") ? "light" : "dark");
    });
    obs.observe(document.documentElement, { attributes: true, attributeFilter: ["class"] });
    return () => obs.disconnect();
  }, []);

  // Intersection observer fade-in
  useEffect(() => {
    const els = document.querySelectorAll<HTMLElement>("[data-reveal]");
    const io = new IntersectionObserver(
      (entries) => {
        entries.forEach((e) => {
          if (e.isIntersecting) {
            e.target.classList.add("opacity-100", "translate-y-0");
            e.target.classList.remove("opacity-0", "translate-y-4");
            io.unobserve(e.target);
          }
        });
      },
      { threshold: 0.12 }
    );
    els.forEach((el) => io.observe(el));
    return () => io.disconnect();
  }, []);

  const palette = theme === "light"
    ? {
        "--lp-bg": "#F7F7F8",
        "--lp-bg2": "#FFFFFF",
        "--lp-card": "#FFFFFF",
        "--lp-fg": "#0D0F14",
        "--lp-muted": "#4B5563",
        "--lp-muted2": "#6B7280",
        "--lp-divider": "#D1D5DB",
        "--lp-footer": "#EEF0F3",
        "--lp-overlay-1": "rgba(255,255,255,0.35)",
        "--lp-overlay-2": "rgba(255,255,255,0.65)",
        "--lp-border-strong": "rgba(0,0,0,0.35)",
        "--lp-soft-bg": "rgba(0,0,0,0.03)",
        "--lp-soft-border": "rgba(0,0,0,0.06)",
        "--lp-hover": "rgba(0,0,0,0.04)",
      } as React.CSSProperties
    : {
        "--lp-bg": "#0D0F14",
        "--lp-bg2": "#111318",
        "--lp-card": "#1A1D25",
        "--lp-fg": "#FFFFFF",
        "--lp-muted": "#9CA3AF",
        "--lp-muted2": "#6B7280",
        "--lp-divider": "#3F4451",
        "--lp-footer": "#08090D",
        "--lp-overlay-1": "rgba(13,15,20,0.35)",
        "--lp-overlay-2": "rgba(13,15,20,0.65)",
        "--lp-border-strong": "rgba(255,255,255,0.6)",
        "--lp-soft-bg": "rgba(255,255,255,0.02)",
        "--lp-soft-border": "rgba(255,255,255,0.04)",
        "--lp-hover": "rgba(255,255,255,0.05)",
      } as React.CSSProperties;

  return (
    <div
      className="min-h-screen w-full text-[var(--lp-fg)]"
      style={{ background: "var(--lp-bg)", fontFamily: "Inter, ui-sans-serif, system-ui", ...palette }}
    >
      <div className="sticky top-0 z-[1002]">
        <TopNavbar />
      </div>

      <Hero />
      <StatBand />
      <About />
      <Capabilities />
      <RiskDrivers />
      <Methodology />
      <Accuracy />
      <Disclaimer />
      <FAQ />
      <Footer />
    </div>
  );
}

/* ---------------- SHARED ---------------- */
function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <div className="mb-5">
      <p
        className="text-[11px] font-semibold uppercase"
        style={{ color: AMBER, letterSpacing: "0.18em" }}
      >
        {children}
      </p>
      <span className="mt-2 block h-[3px] w-9" style={{ background: AMBER }} />
    </div>
  );
}

function sectionHeading(extra = "") {
  return `text-[var(--lp-fg)] font-semibold leading-tight ${extra}`;
}

/* Fires once when the element scrolls into view */
function useInView<T extends HTMLElement>(threshold = 0.3) {
  const ref = useRef<T | null>(null);
  const [inView, setInView] = useState(false);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const io = new IntersectionObserver(
      ([e]) => {
        if (e.isIntersecting) {
          setInView(true);
          io.disconnect();
        }
      },
      { threshold }
    );
    io.observe(el);
    return () => io.disconnect();
  }, [threshold]);
  return { ref, inView };
}

/* Counts numeric strings up from zero; passes text through unchanged */
function CountUp({
  value,
  start,
  className,
  style,
}: {
  value: string;
  start: boolean;
  className?: string;
  style?: React.CSSProperties;
}) {
  const numeric = /^[\d,]+$/.test(value);
  const target = numeric ? parseInt(value.replace(/,/g, ""), 10) : 0;
  const [n, setN] = useState(0);
  useEffect(() => {
    if (!start || !numeric) return;
    let raf = 0;
    const duration = 1200;
    const t0 = performance.now();
    const tick = (now: number) => {
      const p = Math.min((now - t0) / duration, 1);
      const eased = 1 - Math.pow(1 - p, 3);
      setN(Math.round(target * eased));
      if (p < 1) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [start, numeric, target]);
  return (
    <span className={className} style={style}>
      {numeric ? n.toLocaleString() : value}
    </span>
  );
}

/* ---------------- HERO ---------------- */
function Hero() {
  // Server-confirmed session only (see lib/auth.tsx).
  const isAdmin = useAuth().status === "authenticated";
  return (
    <section
      className="relative overflow-hidden px-6 sm:px-10 pt-20 pb-24 text-center"
      style={{ backgroundColor: "var(--lp-bg)" }}
    >
      {/* Background image */}
      <div
        aria-hidden
        className="absolute inset-0 pointer-events-none"
        style={{
          backgroundImage: `url(${heroBg})`,
          backgroundSize: "cover",
          backgroundPosition: "center",
          opacity: 0.32,
        }}
      />
      {/* Yellow + red ambient light over the image */}
      <div
        aria-hidden
        className="absolute inset-0 pointer-events-none"
        style={{
          background:
            "radial-gradient(ellipse at 30% 20%, rgba(245,166,35,0.30), transparent 55%), radial-gradient(ellipse at 75% 80%, rgba(239,68,68,0.25), transparent 55%), linear-gradient(to bottom, var(--lp-overlay-1), var(--lp-overlay-2))",
        }}
      />
      <div className="relative mx-auto max-w-4xl" data-reveal style={{ transition: "all .5s ease" }}>
        <h1
          className="text-[var(--lp-fg)] font-semibold"
          style={{ fontFamily: SERIF, fontSize: "clamp(2.1rem, 4.6vw, 3.4rem)", lineHeight: 1.15 }}
        >
          Estimated Food-Insecurity Risk for CALABARZON
        </h1>

        <p
          className="mt-6 font-bold uppercase"
          style={{ fontSize: "clamp(1.05rem,2vw,1.4rem)", letterSpacing: "0.18em" }}
        >
          <span style={{ color: "hsl(var(--risk-low))" }}>Mapped.</span>{" "}
          <span style={{ color: "hsl(var(--risk-moderate))" }}>Explained.</span>{" "}
          <span style={{ color: "hsl(var(--risk-high))" }}>Forecasted.</span>
        </p>

        <p
          className="mt-6 mx-auto text-[16px] leading-relaxed"
          style={{ color: "var(--lp-muted)", maxWidth: 640 }}
        >
          aiPHeed is an estimated food-insecurity risk index for the five CALABARZON provinces,
          forecast two quarters ahead to help planners identify food stress before it peaks; it is
          not an official statistic.
        </p>

        <div className="mt-9 flex flex-wrap justify-center gap-3">
          <Link
            to="/dashboard"
            className="group inline-flex items-center gap-2 px-6 py-3 rounded-md shadow-md font-semibold text-[14px] transition-colors"
            style={{ background: AMBER, color: "#0D0F14" }}
          >
            Explore the map
            <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-1" />
          </Link>
          <a
            href="#methodology"
            className="group inline-flex items-center gap-2 px-6 py-3 rounded-md font-semibold text-[14px] border transition-colors hover:bg-[var(--lp-hover)]"
            style={{ borderColor: "var(--lp-fg)", color: "var(--lp-fg)" }}
          >
            Read the methodology
            <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-1" />
          </a>
          {isAdmin && (
            <Link
              to="/admin"
              className="group inline-flex items-center gap-2 px-6 py-3 rounded-md font-semibold text-[14px] border transition-colors hover:bg-[var(--lp-hover)]"
              style={{ borderColor: "var(--lp-fg)", color: "var(--lp-fg)" }}
            >
              Go to admin dashboard
              <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-1" />
            </Link>
          )}
        </div>

        {/* Risk scale legend */}
        <div className="mt-14 mx-auto max-w-2xl">
          <div
            className="h-2 w-full"
            style={{
              background: "linear-gradient(to right, #EAB308, #EF4444)",
              border: "1px solid var(--lp-divider)",
            }}
          />
          <div
            className="mt-2 flex justify-between text-[10px] font-semibold"
            style={{ color: "var(--lp-muted)", letterSpacing: "0.16em" }}
          >
            <span>LOWER RISK</span>
            <span>HIGHER RISK</span>
          </div>
        </div>
      </div>

      <p className="absolute bottom-4 right-6 text-[10px]" style={{ color: "var(--lp-muted2)" }}>
        Photo by Atom Araullo on{" "}
        <a
          href="https://www.gmanetwork.com/news/specials/content/193/the-hunger-pandemic/"
          target="_blank"
          rel="noopener noreferrer"
          className="underline hover:text-[var(--lp-fg)] transition-colors"
        >
          GMA News
        </a>
      </p>
    </section>
  );
}

/* ---------------- STAT BAND ---------------- */
function StatBand() {
  const stats = [
    { v: "5", l: "Provinces" },
    { v: "142", l: "Cities and municipalities" },
    { v: "9,667", l: "News headlines, 2021 to 2026" },
    { v: "2 quarters", l: "Forecast lead" },
  ];
  const { ref, inView } = useInView<HTMLDivElement>(0.4);
  return (
    <section
      className="px-6 sm:px-10"
      style={{
        background: "var(--lp-bg)",
        borderTop: "1px solid var(--lp-divider)",
        borderBottom: "1px solid var(--lp-divider)",
      }}
    >
      <div ref={ref} className="mx-auto max-w-6xl grid grid-cols-2 sm:grid-cols-4 py-10">
        {stats.map((s, i) => (
          <div
            key={i}
            className="px-4 sm:px-8 py-3 text-center sm:text-left sm:border-l sm:first:border-l-0"
            style={{
              borderColor: "var(--lp-divider)",
              opacity: inView ? 1 : 0,
              transform: inView ? "translateY(0)" : "translateY(8px)",
              transition: `opacity .5s ease ${i * 90}ms, transform .5s ease ${i * 90}ms`,
            }}
          >
            <CountUp
              value={s.v}
              start={inView}
              className="block font-semibold leading-none text-[var(--lp-fg)]"
              style={{ fontFamily: SERIF, fontSize: "clamp(1.35rem,2.2vw,1.8rem)" }}
            />
            <p
              className="mt-2 text-[10px] font-semibold uppercase"
              style={{ color: "var(--lp-muted)", letterSpacing: "0.14em" }}
            >
              {s.l}
            </p>
          </div>
        ))}
      </div>
    </section>
  );
}

/* ---------------- ABOUT ---------------- */
function About() {
  return (
    <section id="about" className="px-6 sm:px-10 py-24" style={{ background: "var(--lp-bg)" }}>
      <div
        className="mx-auto max-w-6xl grid lg:grid-cols-2 gap-12 items-start opacity-0 translate-y-4"
        data-reveal
        style={{ transition: "all .5s ease" }}
      >
        <div>
          <SectionLabel>About aiPHeed</SectionLabel>
          <h2 className={sectionHeading("mb-6")} style={{ fontFamily: SERIF, fontSize: "clamp(1.7rem,3vw,2.3rem)" }}>
            An estimated risk index for planning
          </h2>
          <p className="text-[15px] leading-relaxed mb-4" style={{ color: "var(--lp-muted)" }}>
            aiPHeed estimates the relative risk of food insecurity in each of the five CALABARZON
            provinces two quarters ahead. It combines public data on prices, poverty, climate, food
            production, jobs, remittances, news and hunger into one index from 0 to 1. A score of
            0.50 or higher is shown as High risk. The index is not an official statistic.
          </p>
          <p className="text-[15px] leading-relaxed mb-4" style={{ color: "var(--lp-muted)" }}>
            aiPHeed was developed as a thesis for the Bachelor of Science in Computer Science with
            Intelligent Systems Track at De La Salle University - Dasmariñas. Researchers: Destura,
            Princess Gwenn A.; Esico, Christina M.; and Melindo, Angel Vhea P. The Department of
            Agriculture did not develop aiPHeed and has not endorsed it.
          </p>
          <p className="text-[15px] leading-relaxed" style={{ color: "var(--lp-muted)" }}>
            It is intended for planning staff of the Department of Agriculture Regional Field Office
            IV-A (CALABARZON). It is published through a publicly accessible geospatial dashboard,
            which shows:
          </p>
          <ul className="mt-2 list-disc pl-5 text-[15px] leading-relaxed" style={{ color: "var(--lp-muted)" }}>
            <li>a map of the provinces, each coloured Low or High;</li>
            <li>each province's domain and factor scores;</li>
            <li>a separate food-price-pressure forecast;</li>
            <li>
              a priority ranking of all 142 cities and municipalities. The city and municipal values
              are a relative prioritization within each province, not forecasts for each city or
              municipality.
            </li>
          </ul>
        </div>

        <SummaryCard />
      </div>
    </section>
  );
}

/** "2027-Q1" -> "Q1 2027 · January – March 2027"; null when the id is not a quarter. */
function periodLabel(quarterId: string | undefined): string | null {
  const m = quarterId?.match(/^(\d{4})-Q([1-4])$/);
  return m ? quarterPeriodLabel({ year: Number(m[1]), q: Number(m[2]) }) : null;
}

/* The served regional estimate (the mean of the five province indexes), read from the API so it never goes stale. */
function SummaryCard() {
  const { data: config } = useConfig();
  const { data, isLoading, isError } = useExplainability("region", "calabarzon");
  const cutoff = config?.thresholds.riskDisplayCutoff ?? 0.5;
  const alertAt = config?.thresholds.alertThreshold ?? 0.6;
  const score = data && Number.isFinite(data.riskScore) ? data.riskScore : null;
  const level = score === null ? null : score >= cutoff ? "high" : "low";
  const issued = data?.summary?.issued;

  return (
    <div style={{ background: "var(--lp-card)", border: "1px solid var(--lp-divider)" }}>
      <div
        className="flex items-center justify-between px-6 py-3"
        style={{ borderBottom: "1px solid var(--lp-divider)" }}
      >
        <p className="text-[10px] font-semibold uppercase" style={{ color: "var(--lp-muted)", letterSpacing: "0.16em" }}>
          {periodLabel(data?.quarter) ?? "Current estimate"}
        </p>
        <div className="flex gap-2">
          {level && <StatusBadge level={level} />}
          {score !== null && score >= alertAt && <StatusBadge tone="high">Active alert</StatusBadge>}
        </div>
      </div>

      <div className="p-6">
        <h3 className="text-[var(--lp-fg)] text-base font-semibold mb-6" style={{ fontFamily: SERIF }}>
          CALABARZON regional estimate
        </h3>

        <div className="mb-6">
          <MetricLabel className="mb-2">Estimated food-insecurity risk index (mean of five provinces)</MetricLabel>
          <p className="font-semibold leading-none" style={{ fontFamily: SERIF, fontSize: "3.25rem", color: AMBER }}>
            {score === null ? "—" : score.toFixed(2)}
            <span className="text-lg ml-2" style={{ color: "var(--lp-muted2)" }}>/ 1.00</span>
          </p>
        </div>

        {level && (
          <div className="mb-3">
            <StatusBadge level={level} swatch="circle" />
          </div>
        )}

        <div
          className="relative h-2 w-full"
          style={{ background: "linear-gradient(to right, #EAB308, #F97316, #EF4444)", border: "1px solid var(--lp-divider)" }}
        >
          {score !== null && (
            <div
              className="absolute -top-1 h-4 w-[2px]"
              style={{ left: `${Math.min(Math.max(score, 0), 1) * 100}%`, background: "var(--lp-fg)" }}
            />
          )}
        </div>
        <div className="mt-2 flex justify-between text-[9px] tracking-widest" style={{ color: "var(--lp-muted2)" }}>
          <span>0.00</span>
          <span>1.00</span>
        </div>
        <p className="mt-4 text-[11px] leading-relaxed" style={{ color: "var(--lp-muted2)" }}>
          {isLoading
            ? "Loading the current estimate…"
            : isError || score === null
              ? "The current estimate could not be loaded."
              : `High risk at ${cutoff.toFixed(2)} or above.${issued ? ` Issued ${issued}.` : ""} An estimate for planning, not a probability.`}
        </p>
      </div>
    </div>
  );
}

/* ---------------- CAPABILITIES ---------------- */
function Capabilities() {
  const items = [
    { title: "Province risk map", body: "Each province is coloured Low or High risk for the forecast quarter, from an index between 0 and 1 (High at 0.50 or above)." },
    { title: "Domain breakdown", body: "Each province estimate shows its domain scores, each indicator's value, score and status, and which data were available at the issue date." },
    { title: "Food-price-pressure forecast", body: "A LightGBM model forecasts provincial food-price pressure two quarters ahead. It is one input to the index and is also shown on its own." },
    { title: "Filipino-English news evidence", body: "XLM-RoBERTa scores news headlines against ten bilingual food-insecurity hypotheses without labelled training data. The resulting Food Stress Sentiment Index is used only when a province has at least 5 articles." },
    { title: "City and municipal priority ranking", body: "All 142 cities and municipalities are ranked by the province estimate weighted by PSA poverty incidence (60 percent) and population density (40 percent): a relative prioritization, not municipal forecasts." },
    { title: "Reports and past quarters", body: "Downloadable PDF reports, and back-test estimates for past quarters, labelled as development evidence." },
  ];

  return (
    <section id="capabilities" className="px-6 sm:px-10 py-24" style={{ background: "var(--lp-bg2)" }}>
      <div className="mx-auto max-w-6xl opacity-0 translate-y-4" data-reveal style={{ transition: "all .5s ease" }}>
        <SectionLabel>Capabilities</SectionLabel>
        <h2 className={sectionHeading("mb-10 max-w-3xl")} style={{ fontFamily: SERIF, fontSize: "clamp(1.7rem,3vw,2.3rem)" }}>
          What the system shows
        </h2>

        <div
          className="grid gap-px md:grid-cols-2 lg:grid-cols-3"
          style={{ background: "var(--lp-divider)", border: "1px solid var(--lp-divider)" }}
        >
          {items.map((it, i) => (
            <div key={i} className="p-6" style={{ background: "var(--lp-card)" }}>
              <span
                className="block text-[22px] font-semibold mb-3 pb-3"
                style={{ fontFamily: SERIF, color: AMBER, borderBottom: "1px solid var(--lp-divider)" }}
              >
                {String(i + 1).padStart(2, "0")}
              </span>
              <h3 className="text-[var(--lp-fg)] font-semibold text-[15px] mb-2">{it.title}</h3>
              <p className="text-[13px] compact:text-[14px] leading-relaxed" style={{ color: "var(--lp-muted)" }}>{it.body}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

/* ---------------- RISK DRIVERS ---------------- */
/* What each of the five factor groups on the map contains (FINAL_THESIS_SYSTEM_REPORT.md section 8). */
const DRIVER_BODY: Record<string, string> = {
  market: "LightGBM food-price-pressure forecast, headline inflation and wholesale rice prices (provincial).",
  climate: "PAGASA El Niño advisory status, typhoons within 300 km, and palay and corn production.",
  employment: "Change in the national unemployment rate (PSA Labor Force Survey); the same for every province.",
  ofw_remittance: "Change in national cash remittances (BSP); the same for every province.",
  fish_kill: "Drop in fisheries production (PSA). This is production data, not a count of fish-kill events.",
};

function RiskDrivers() {
  const { data, isLoading, isError } = useExplainability("region", "calabarzon");
  const drivers = data?.triggers ?? [];
  const maxPct = Math.max(1, ...drivers.map((d) => Math.abs(d.pct)));

  return (
    <section className="px-6 sm:px-10 py-24" style={{ background: "var(--lp-bg)" }}>
      <div className="mx-auto max-w-6xl opacity-0 translate-y-4" data-reveal style={{ transition: "all .5s ease" }}>
        <SectionLabel>Risk factors</SectionLabel>
        <h2 className={sectionHeading("mb-8")} style={{ fontFamily: SERIF, fontSize: "clamp(1.6rem,2.8vw,2.1rem)" }}>
          What moved the current regional estimate
        </h2>

        <div style={{ background: "var(--lp-card)", border: "1px solid var(--lp-divider)" }}>
          <div
            className="flex items-center justify-between px-5 py-3"
            style={{ borderBottom: "1px solid var(--lp-divider)" }}
          >
            <p className="text-[10px] font-semibold uppercase" style={{ color: "var(--lp-muted)", letterSpacing: "0.16em" }}>
              Factor groups{periodLabel(data?.quarter) ? ` · ${periodLabel(data?.quarter)}` : ""}
            </p>
            <p className="text-[10px] font-semibold uppercase" style={{ color: "var(--lp-muted2)", letterSpacing: "0.1em" }}>
              Share of the index's movement
            </p>
          </div>

          {(isLoading || isError || drivers.length === 0) && (
            <p className="px-5 py-4 text-[13px]" style={{ color: "var(--lp-muted)" }}>
              {isLoading ? "Loading the current estimate…" : "The current estimate could not be loaded."}
            </p>
          )}

          {drivers.map((d, i) => {
            const noData = d.status === "insufficient_data" || d.status === "no_data";
            const isNeg = d.direction === "protective";
            const pct = noData ? 0 : (Math.abs(d.pct) / maxPct) * 100;
            const display = noData ? "No data" : `${isNeg ? "−" : "+"}${Math.abs(d.pct)}%`;
            return (
              <div
                key={d.key}
                className="grid grid-cols-1 sm:grid-cols-[1.4fr_1fr_auto] items-center gap-4 px-5 py-4"
                style={{ borderBottom: i < drivers.length - 1 ? "1px solid var(--lp-divider)" : "none" }}
              >
                <div className="min-w-0">
                  <p className="text-[var(--lp-fg)] font-semibold text-[13px]">{d.label}</p>
                  <p className="text-[12px] compact:text-[14px] leading-relaxed" style={{ color: "var(--lp-muted)" }}>
                    {DRIVER_BODY[d.key] ?? ""}
                    {noData ? " No value was published by the issue date; missing data is not a sign of low risk." : ""}
                  </p>
                </div>

                {/* Diverging magnitude bar */}
                <div
                  className="relative flex h-6 w-full items-stretch"
                  style={{ background: "var(--lp-soft-bg)", border: "1px solid var(--lp-divider)" }}
                >
                  <div className="flex-1 flex justify-end">
                    {isNeg && !noData && <div style={{ width: `${pct}%`, background: "rgba(21,128,61,0.55)" }} />}
                  </div>
                  <div style={{ width: 1, background: "var(--lp-divider)" }} />
                  <div className="flex-1">
                    {!isNeg && !noData && <div className="h-full" style={{ width: `${pct}%`, background: "rgba(185,28,28,0.55)" }} />}
                  </div>
                </div>

                <span
                  className="justify-self-start sm:justify-self-end font-mono text-[12px] font-bold px-2.5 py-1"
                  style={
                    noData
                      ? { background: "var(--lp-soft-bg)", color: "var(--lp-muted)", border: "1px solid var(--lp-divider)" }
                      : {
                          background: isNeg ? "rgba(21,128,61,0.10)" : "rgba(185,28,28,0.10)",
                          color: isNeg ? "#15803D" : "#B91C1C",
                          border: `1px solid ${isNeg ? "rgba(21,128,61,0.35)" : "rgba(185,28,28,0.35)"}`,
                        }
                  }
                >
                  {display}
                </span>
              </div>
            );
          })}
        </div>
        <p className="mt-3 text-[11px] compact:text-[14px]" style={{ color: "var(--lp-muted2)" }}>
          Red bars raise the estimate; green bars lower it. Each value is the group's share of how far the regional
          index moved from 0.50. Household vulnerability, regional hunger and news are also in the index but are not
          among these five groups. Shares describe how the estimate is built from the evidence; they are not causes.
        </p>
      </div>
    </section>
  );
}

/* ---------------- METHODOLOGY ---------------- */
function Methodology() {
  const sources = [
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

  const steps = [
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

  const notes = [
    {
      t: "Forecast lead",
      d: "Estimates are issued at the start of each quarter for the quarter two quarters ahead (Lead-2), using only information published before the issue date.",
    },
    {
      t: "Missing data",
      d: "A missing value is never counted as zero or as low risk. An indicator with no published value at the issue date is left out of its domain and marked missing; a domain with no indicators is left out, and the number of domains used is shown.",
    },
    {
      t: "Review before publication",
      d: "Each province estimate is accepted or rejected by an authorized administrator before it appears on the public map. Every decision is recorded with the reviewer, the reason and the time, and a rejected province is shown greyed out.",
    },
  ];

  const th = "text-left text-[10px] font-semibold uppercase px-4 py-3";
  const td = "align-top text-[13px] compact:text-[14px] px-4 py-3";

  return (
    <section id="methodology" className="px-6 sm:px-10 py-24" style={{ background: "var(--lp-bg2)" }}>
      <div className="mx-auto max-w-6xl opacity-0 translate-y-4" data-reveal style={{ transition: "all .5s ease" }}>
        <SectionLabel>Methodology</SectionLabel>
        <h2 className={sectionHeading("mb-12")} style={{ fontFamily: SERIF, fontSize: "clamp(1.7rem,3vw,2.3rem)" }}>
          How the risk index is built
        </h2>

        <h3 className="text-[var(--lp-fg)] font-semibold text-[13px] mb-4 uppercase" style={{ letterSpacing: "0.12em" }}>
          Data sources
        </h3>
        <p className="mb-4 text-[13px] compact:text-[14px] leading-relaxed" style={{ color: "var(--lp-muted)" }}>
          Only data from 2021 onward is used. Periods are those available at the issue date of 1 October 2026.
        </p>
        <div className="mb-16 overflow-x-auto" style={{ border: "1px solid var(--lp-divider)" }}>
          <table className="w-full min-w-[640px] border-collapse" style={{ background: "var(--lp-card)" }}>
            <thead>
              <tr style={{ borderBottom: "1px solid var(--lp-divider)", color: AMBER, letterSpacing: "0.12em" }}>
                <th className={th}>Source</th>
                <th className={th}>What it measures</th>
                <th className={th}>Period used</th>
                <th className={th}>Level</th>
              </tr>
            </thead>
            <tbody>
              {sources.map((r, i) => (
                <tr key={i} style={{ borderBottom: i < sources.length - 1 ? "1px solid var(--lp-divider)" : "none" }}>
                  <td className={`${td} font-semibold text-[var(--lp-fg)]`}>{r.s}</td>
                  <td className={td} style={{ color: "var(--lp-muted)" }}>{r.m}</td>
                  <td className={td} style={{ color: "var(--lp-muted)" }}>{r.p}</td>
                  <td className={td} style={{ color: "var(--lp-muted)" }}>{r.l}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <h3 className="text-[var(--lp-fg)] font-semibold text-[13px] mb-4 uppercase" style={{ letterSpacing: "0.12em" }}>
          Five steps
        </h3>
        <div
          className="grid gap-px sm:grid-cols-2 lg:grid-cols-3 mb-16"
          style={{ background: "var(--lp-divider)", border: "1px solid var(--lp-divider)" }}
        >
          {steps.map((s, i) => (
            <div key={i} className="p-5" style={{ background: "var(--lp-card)" }}>
              <div className="flex items-center gap-3 mb-2">
                <span
                  className="inline-flex h-8 w-8 items-center justify-center text-[13px] font-bold"
                  style={{ background: AMBER, color: "#0D0F14", fontFamily: SERIF }}
                >
                  {i + 1}
                </span>
                <p className="text-[var(--lp-fg)] font-semibold text-[13px]">{s.t}</p>
              </div>
              <p className="text-[12px] compact:text-[14px] leading-relaxed" style={{ color: "var(--lp-muted)" }}>{s.d}</p>
            </div>
          ))}
        </div>

        <div
          className="grid gap-px md:grid-cols-3"
          style={{ background: "var(--lp-divider)", border: "1px solid var(--lp-divider)" }}
        >
          {notes.map((n, i) => (
            <div key={i} className="p-5" style={{ background: "var(--lp-card)", borderLeft: `2px solid ${AMBER}` }}>
              <p className="text-[var(--lp-fg)] font-semibold text-[13px] mb-2">{n.t}</p>
              <p className="text-[12px] compact:text-[14px] leading-relaxed" style={{ color: "var(--lp-muted)" }}>{n.d}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

/* ---------------- ACCURACY ---------------- */
/* Figures copied exactly from FINAL_THESIS_SYSTEM_REPORT.md sections 1-2 and /api/v1/config (FIRI v2); never rounded here. */
function Accuracy() {
  const lgbm = [
    ["Accuracy", "0.72"],
    ["Precision", "0.63"],
    ["Recall", "0.56"],
    ["F1-score", "0.59"],
    ["AUC-ROC", "0.65"],
  ];
  const brier = [
    ["LightGBM (proposed)", "0.178"],
    ["I. Naive persistence", "0.400"],
    ["II. PSA-only indicators", "0.598"],
    ["III. News-only sentiment", "0.235"],
    ["IV. Logistic regression", "0.646"],
  ];
  const cards = [
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

  const table = (title: string, note: string, rows: string[][]) => (
    <div style={{ background: "var(--lp-card)", border: "1px solid var(--lp-divider)" }}>
      <p className="px-5 py-3 text-[var(--lp-fg)] font-semibold text-[13px]" style={{ borderBottom: "1px solid var(--lp-divider)" }}>
        {title}
      </p>
      {rows.map(([k, v], i) => (
        <div
          key={k}
          className="flex items-center justify-between px-5 py-2.5 text-[13px]"
          style={{ borderBottom: i < rows.length - 1 ? "1px solid var(--lp-divider)" : "none" }}
        >
          <span style={{ color: "var(--lp-muted)" }}>{k}</span>
          <span className="font-mono font-semibold text-[var(--lp-fg)]">{v}</span>
        </div>
      ))}
      <p className="px-5 py-3 text-[11px] compact:text-[14px] leading-relaxed" style={{ color: "var(--lp-muted2)", borderTop: "1px solid var(--lp-divider)" }}>
        {note}
      </p>
    </div>
  );

  return (
    <section id="accuracy" className="px-6 sm:px-10 py-24" style={{ background: "var(--lp-bg)" }}>
      <div className="mx-auto max-w-6xl opacity-0 translate-y-4" data-reveal style={{ transition: "all .5s ease" }}>
        <SectionLabel>Evaluation</SectionLabel>
        <h2 className={sectionHeading("mb-4")} style={{ fontFamily: SERIF, fontSize: "clamp(1.7rem,3vw,2.3rem)" }}>
          How accurate it is
        </h2>
        <p className="mb-10 max-w-3xl text-[15px] leading-relaxed" style={{ color: "var(--lp-muted)" }}>
          All results below are development evidence: every evaluated quarter was examined while the system was being
          built, and no unseen quarter has been scored yet.
        </p>

        <div className="grid gap-6 md:grid-cols-2 mb-6">
          {table(
            "Food-price-pressure forecast (LightGBM, two quarters ahead)",
            "Tested on 50 province-quarters (10 quarters).",
            lgbm,
          )}
          {table(
            "Brier score against the four baselines (lower is better)",
            "Same 45 province-quarters. The advantage is statistically established only against the PSA-only and logistic-regression baselines.",
            brier,
          )}
        </div>

        <div
          className="grid gap-px md:grid-cols-2"
          style={{ background: "var(--lp-divider)", border: "1px solid var(--lp-divider)" }}
        >
          {cards.map((c, i) => (
            <div key={i} className="p-5" style={{ background: "var(--lp-card)" }}>
              <p className="text-[var(--lp-fg)] font-semibold text-[13px] mb-2">{c.t}</p>
              <p className="text-[12px] compact:text-[14px] leading-relaxed" style={{ color: "var(--lp-muted)" }}>{c.d}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

/* ---------------- DISCLAIMER ---------------- */
function Disclaimer() {
  const points = [
    "A proxy index, not a probability. The risk index is an estimate built from related indicators. It is not a probability, not a measured food-insecurity rate, and not an official statistic or classification.",
    "Not validated as a measure of food insecurity. No provincial or municipal food-insecurity measure exists for CALABARZON to check the index against.",
    "Regional hunger is not provincial. The hunger figure comes from SWS surveys of Balance Luzon. The same value is used for all five provinces, with a sampling error of about 4 to 6 percentage points.",
    "Some inputs are national. Unemployment and remittances are national figures, the same for every province, and remittance data ends in 2025-Q4.",
    "City and municipal values are a relative prioritization within each province, based on the province estimate, poverty and population density. They are not forecasts for each city or municipality. The poverty value for Lucena City is a substitute that has not been verified.",
    "News has limits. Only headlines are used, collected after the fact, and the news classifier was checked against AI-labelled headlines, not a human-reviewed set. Many province-quarters have fewer than 5 articles, so news often does not enter the index. News, topics and El Niño information have no measured effect on forecast accuracy.",
    "Missing data is not low risk. When a source has not yet published, the indicator is left out and the estimate is based on fewer domains. The dashboard says which inputs are missing.",
    "Back-test results are not live results. Past-quarter results were computed after the fact on quarters examined during development. Only the sealed 2026-Q4 and 2027-Q1 estimates will be a true test.",
    "Small sample. Each lead time has only 9 to 12 quarters of evidence, and there was one El Niño episode in 2021 to 2026.",
    "aiPHeed outputs must not replace official assessment procedures or be used as official food-insecurity classifications or policy recommendations.",
  ];
  return (
    <section id="disclaimer" className="px-6 sm:px-10 py-20" style={{ background: "var(--lp-bg)" }}>
      <div className="mx-auto max-w-6xl opacity-0 translate-y-4" data-reveal style={{ transition: "all .5s ease" }}>
        <div
          className="p-8"
          style={{ background: "var(--lp-card)", border: "1px solid var(--lp-divider)", borderLeft: "4px solid #C2410C" }}
        >
          <p className="text-[11px] font-bold uppercase mb-4" style={{ color: "#C2410C", letterSpacing: "0.16em" }}>
            Data disclaimer and limitations
          </p>
          <ul className="space-y-3">
            {points.map((p, i) => (
              <li key={i} className="flex gap-3 text-[14px] leading-relaxed" style={{ color: "var(--lp-muted)" }}>
                <span className="mt-2 h-1.5 w-1.5 shrink-0" style={{ background: "#C2410C" }} />
                <span>{p}</span>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </section>
  );
}

/* ---------------- FAQ ---------------- */
function FAQ() {
  const items = [
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
      a: "Once per quarter, after the source data are refreshed. Estimates are reviewed before they appear on the public map.",
    },
    {
      q: "Where can I get official food-security information?",
      a: "From the Department of Agriculture Regional Field Office IV-A, the Philippine Statistics Authority and other mandated agencies. Their websites are listed at the bottom of this page.",
    },
  ];
  const [open, setOpen] = useState<number | null>(0);

  return (
    <section id="faq" className="px-6 sm:px-10 py-24" style={{ background: "var(--lp-bg2)" }}>
      <div className="mx-auto max-w-6xl opacity-0 translate-y-4" data-reveal style={{ transition: "all .5s ease" }}>
        <SectionLabel>Reference</SectionLabel>
        <h2 className={sectionHeading("mb-10")} style={{ fontFamily: SERIF, fontSize: "clamp(1.7rem,3vw,2.3rem)" }}>
          Frequently asked questions
        </h2>
        <div style={{ border: "1px solid var(--lp-divider)" }}>
          {items.map((it, i) => {
            const isOpen = open === i;
            return (
              <div
                key={i}
                style={{
                  borderBottom: i < items.length - 1 ? "1px solid var(--lp-divider)" : "none",
                  background: "var(--lp-card)",
                }}
              >
                <button
                  onClick={() => setOpen(isOpen ? null : i)}
                  className="w-full flex items-center gap-4 p-5 text-left hover:bg-[var(--lp-hover)] transition-colors"
                >
                  <span
                    className="text-[13px] font-bold shrink-0"
                    style={{ fontFamily: SERIF, color: isOpen ? AMBER : "var(--lp-muted2)" }}
                  >
                    {String(i + 1).padStart(2, "0")}
                  </span>
                  <span className="flex-1 text-[var(--lp-fg)] font-semibold text-[14px]">{it.q}</span>
                  <ChevronDown
                    className="h-5 w-5 shrink-0 transition-transform"
                    style={{ color: isOpen ? AMBER : "var(--lp-muted)", transform: isOpen ? "rotate(180deg)" : "rotate(0)" }}
                  />
                </button>
                {isOpen && (
                  <div className="pl-14 pr-5 pb-5 text-[13px] compact:text-[14px] leading-relaxed" style={{ color: "var(--lp-muted)" }}>
                    {it.a}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </section>
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

function Footer() {
  const team = [
    { name: "Destura", url: "https://www.linkedin.com/in/princess-gwenn-destura" },
    { name: "Melindo", url: "https://www.linkedin.com/in/angelvheamelindo/" },
    { name: "Esico", url: "https://www.linkedin.com/in/christina-esico/" },
  ];
  return (
    <footer
      className="relative px-6 sm:px-10 pt-16 pb-6"
      style={{ background: "#08090D", borderTop: "1px solid var(--lp-divider)" }}
    >
      <div className="mx-auto max-w-7xl">
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-4 sm:gap-6 lg:gap-10 mb-12">
          {/* Brand + description + bottom links */}
          <div className="col-span-1">
            <div className="flex items-center gap-3 mb-5">
              <img src={logoDark} alt="aiPHeed" className="h-10 sm:h-12 w-auto object-contain" />
            </div>
            <p className="text-[14px] leading-relaxed mb-6" style={{ color: "var(--lp-muted)" }}>
              aiPHeed estimates food-insecurity risk for the five CALABARZON provinces each quarter, two
              quarters ahead, combining Filipino-English natural language processing and ensemble
              machine learning to help identify food stress before it peaks. It is not an official
              statistic.
            </p>
            <p className="text-[14px] leading-relaxed mb-6" style={{ color: "var(--lp-muted)" }}>
              Contact the research team:{" "}
              <a href="mailto:aipheed.research@dlsud.edu.ph" className="underline hover:text-[var(--lp-fg)] transition-colors">
                aipheed.research@dlsud.edu.ph
              </a>
            </p>
            <div className="flex flex-wrap items-center gap-x-3 gap-y-2 text-[14px]" style={{ color: "var(--lp-muted)" }}>
              <a href="#" className="hover:text-[var(--lp-fg)] transition-colors compact:inline-flex compact:items-center compact:min-h-11 compact:min-w-11">Home</a>
              <span style={{ color: "var(--lp-divider)" }}>•</span>
              <a href="#about" className="hover:text-[var(--lp-fg)] transition-colors compact:inline-flex compact:items-center compact:min-h-11 compact:min-w-11">About</a>
              <span style={{ color: "var(--lp-divider)" }}>•</span>
              <a href="#methodology" className="hover:text-[var(--lp-fg)] transition-colors compact:inline-flex compact:items-center compact:min-h-11 compact:min-w-11">Methodology</a>
              <span style={{ color: "var(--lp-divider)" }}>•</span>
              <a href="#faq" className="hover:text-[var(--lp-fg)] transition-colors compact:inline-flex compact:items-center compact:min-h-11 compact:min-w-11">FAQ</a>
              <span style={{ color: "var(--lp-divider)" }}>•</span>
              <a href="mailto:aipheed.research@dlsud.edu.ph" className="hover:text-[var(--lp-fg)] transition-colors compact:inline-flex compact:items-center compact:min-h-11 compact:min-w-11">Contact</a>
            </div>
          </div>

          {/* Explore */}
          <div className="lg:pl-6 col-span-1">
            <h4 className="text-[var(--lp-fg)] font-semibold text-[15px] mb-5">Explore</h4>
            <ul className="space-y-3 compact:space-y-0 text-[14px]" style={{ color: "var(--lp-muted)" }}>
              <li><Link to="/dashboard" className="hover:text-[var(--lp-fg)] transition-colors compact:inline-flex compact:items-center compact:min-h-11 compact:min-w-11">Map</Link></li>
              <li><Link to="/data" className="hover:text-[var(--lp-fg)] transition-colors compact:inline-flex compact:items-center compact:min-h-11 compact:min-w-11">Data</Link></li>
              <li><Link to="/visualization" className="hover:text-[var(--lp-fg)] transition-colors compact:inline-flex compact:items-center compact:min-h-11 compact:min-w-11">Visualization</Link></li>
              <li><a href="#methodology" className="hover:text-[var(--lp-fg)] transition-colors compact:inline-flex compact:items-center compact:min-h-11 compact:min-w-11">Methodology</a></li>
              <li><a href="#accuracy" className="hover:text-[var(--lp-fg)] transition-colors compact:inline-flex compact:items-center compact:min-h-11 compact:min-w-11">Accuracy</a></li>
              <li><a href="#disclaimer" className="hover:text-[var(--lp-fg)] transition-colors compact:inline-flex compact:items-center compact:min-h-11 compact:min-w-11">Disclaimer</a></li>
            </ul>
          </div>

          {/* Related websites (official sites only) */}
          <div>
            <h4 className="text-[var(--lp-fg)] font-semibold text-[15px] mb-5">Related websites</h4>
            <ul className="space-y-3 compact:space-y-0 text-[14px]" style={{ color: "var(--lp-muted)" }}>
              {RELATED_SITES.map((s) => (
                <li key={s.url}>
                  <a
                    href={s.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="hover:text-[var(--lp-fg)] transition-colors compact:inline-flex compact:items-center compact:min-h-11 compact:min-w-11"
                  >
                    {s.name}
                  </a>
                </li>
              ))}
            </ul>
          </div>
        </div>

        <p className="pb-6 text-[12px] leading-relaxed" style={{ color: "var(--lp-muted2)" }}>
          Credits: hero photo by Atom Araullo,{" "}
          <a
            href="https://www.gmanetwork.com/news/specials/content/193/the-hunger-pandemic/"
            target="_blank"
            rel="noopener noreferrer"
            className="underline hover:text-[var(--lp-fg)] transition-colors"
          >
            GMA News
          </a>
          . Basemap ©{" "}
          <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener noreferrer" className="underline hover:text-[var(--lp-fg)] transition-colors">
            OpenStreetMap
          </a>{" "}
          contributors · ©{" "}
          <a href="https://protomaps.com" target="_blank" rel="noopener noreferrer" className="underline hover:text-[var(--lp-fg)] transition-colors">
            Protomaps
          </a>
          . Data: Philippine Statistics Authority (Consumer Price Index, wholesale rice prices, 2021 Small Area
          Estimates of poverty, 2024 Census of Population, palay, corn and fisheries production, Labor Force Survey);
          Bangko Sentral ng Pilipinas (cash remittances); PAGASA (El Niño advisories);{" "}
          <a
            href="https://www.ncei.noaa.gov/products/international-best-track-archive"
            target="_blank"
            rel="noopener noreferrer"
            className="underline hover:text-[var(--lp-fg)] transition-colors"
          >
            NOAA NCEI IBTrACS
          </a>{" "}
          (tropical cyclone tracks); Social Weather Stations (hunger survey, Balance Luzon); news headlines via Google
          News. Each source's data remains the property of its publisher. The aiPHeed index is not an official
          statistic of any of these agencies.
        </p>

        <div
          className="pt-6 flex flex-row items-center justify-between gap-x-6 gap-y-2 text-[12px] flex-wrap"
          style={{ borderTop: "1px solid rgba(255,255,255,0.06)", color: "var(--lp-muted2)" }}
        >
          <p className="flex items-center gap-x-3 flex-wrap">
            <span>© 2026 aiPHeed. All rights reserved.</span>
          </p>
          <p className="flex items-center gap-1.5 flex-wrap">
            <span>Developed by</span>
            {team.map((m, i) => (
              <span key={i} className="flex items-center gap-1.5">
                <a
                  href={m.url}
                  target="_blank"
                  rel="noreferrer"
                  className="font-semibold hover:text-[var(--lp-fg)] transition-colors compact:inline-flex compact:items-center compact:min-h-11 compact:min-w-11"
                  style={{ color: "var(--lp-muted)" }}
                >
                  {m.name}
                </a>
                {i < team.length - 1 && <span style={{ color: "var(--lp-divider)" }}>·</span>}
              </span>
            ))}
          </p>
        </div>
      </div>
    </footer>
  );
}
