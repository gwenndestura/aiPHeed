import { useMemo, useState } from "react";
import { RegionData, MunicipalityData } from "@/data/types";
import { ChevronDown, ChevronRight, Newspaper, Sparkles, Info, ShieldAlert, AlertCircle } from "lucide-react";
import { Quarter } from "./QuarterTimeSlider";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "@/components/ui/dialog";
import {
  PROVINCE_QUARTER_DATA,
  getRiskLevelFromScore,
  getShapForProvince,
  SAMPLE_ARTICLES,
  type Article,
  ALERT_THRESHOLD,
  RISK_DISPLAY_CUTOFF,
  isLimitedSignal,
  getRiskLabel,
} from "@/data/quarterData";
import { GlossaryPanel } from "./GlossaryPanel";

interface Props {
  quarter: Quarter;
  selectedRegion: RegionData | null;
  selectedMunicipality?: MunicipalityData | null;
}

export function RightAnalyticsPanel({ quarter, selectedRegion, selectedMunicipality }: Props) {
  const [articlesOpen, setArticlesOpen] = useState(false);
  const [activeArticle, setActiveArticle] = useState<Article | null>(null);
  const [glossaryOpen, setGlossaryOpen] = useState(false);

  const region = selectedRegion;
  const shap = useMemo(() => getShapForProvince(region?.id ?? null), [region]);

  const baseline = 0.32;
  const finalScore = useMemo(() => {
    if (region) {
      return PROVINCE_QUARTER_DATA.find((p) => p.id === region.id)?.scoresByQuarter[quarter.id] ?? region.riskScore;
    }
    return baseline + shap.reduce((a, s) => a + s.value, 0);
  }, [region, quarter.id, shap]);

  const sortedShap = useMemo(
    () => [...shap].sort((a, b) => Math.abs(b.value) - Math.abs(a.value)),
    [shap]
  );
  const subjectName = selectedMunicipality
    ? `${selectedMunicipality.name}, ${selectedMunicipality.provinceName}`
    : region
      ? region.name
      : "CALABARZON";

  return (
    <div className="h-full flex flex-col bg-card/95 backdrop-blur-sm border-l border-border/50 overflow-hidden">
      <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4">
        <ShapNarrativeCardBody quarter={quarter} selectedRegion={region} selectedMunicipality={selectedMunicipality} />
        <NewsArticlesCardBody selectedRegion={region} />
      </div>
    </div>
  );
}

/* ─── Standalone card bodies for floating cards layout (Index.tsx) ─── */

export function ShapNarrativeCardBody({
  quarter,
  selectedRegion,
  selectedMunicipality,
}: {
  quarter: Quarter;
  selectedRegion: RegionData | null;
  selectedMunicipality?: MunicipalityData | null;
}) {
  const [glossaryOpen, setGlossaryOpen] = useState(false);
  const region = selectedRegion;
  const shap = useMemo(() => getShapForProvince(region?.id ?? null), [region]);
  const baseline = 0.32;

  const finalScore = useMemo(() => {
    if (region) {
      return PROVINCE_QUARTER_DATA.find((p) => p.id === region.id)?.scoresByQuarter[quarter.id] ?? region.riskScore;
    }
    return baseline + shap.reduce((a, s) => a + s.value, 0);
  }, [region, quarter.id, shap]);

  // Calibrate SHAP values so baseline + Σφᵢ exactly equals the displayed Risk Level shown elsewhere.
  const calibratedShap = useMemo(() => {
    const target = finalScore - baseline;
    const current = shap.reduce((a, s) => a + s.value, 0);
    if (current === 0 || !isFinite(current)) return shap;
    const k = target / current;
    return shap.map((s) => ({ ...s, value: s.value * k }));
  }, [shap, finalScore]);

  const sortedShap = useMemo(
    () => [...calibratedShap].sort((a, b) => Math.abs(b.value) - Math.abs(a.value)),
    [calibratedShap]
  );

  const subjectName = selectedMunicipality
    ? `${selectedMunicipality.name}, ${selectedMunicipality.provinceName}`
    : region ? region.name : "CALABARZON";

  return (
    <div key={`${subjectName}-${quarter.id}`} className="animate-fade-in">
      <div className="flex items-start justify-between gap-2 mb-2">
        <div className="min-w-0">
          <p className="text-[9px] uppercase tracking-widest text-muted-foreground/70 font-semibold flex items-center gap-1.5">
            {quarter.forecast && <Sparkles className="h-2.5 w-2.5 text-primary" />}
            {quarter.label} {quarter.year} · {quarter.monthsLabel}
          </p>
          <h2 className="text-sm font-bold mt-0.5 truncate">{subjectName} Summary</h2>
        </div>
        <button
          onClick={() => setGlossaryOpen(true)}
          className="shrink-0 p-1 rounded-md hover:bg-secondary/60 text-muted-foreground hover:text-foreground transition-colors"
          aria-label="Open glossary"
          title="Glossary of terms"
        >
          <Info className="h-3.5 w-3.5" />
        </button>
      </div>

      <div className="flex flex-wrap items-center gap-1.5 mb-2">
        <span
          className={`text-[9px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full font-mono-num ${
            getRiskLabel(finalScore) === "HIGH" ? "bg-risk-high/15 text-risk-high" : "bg-risk-low/15 text-risk-low"
          }`}
          title={`Forecast display cutoff: ${RISK_DISPLAY_CUTOFF}`}
        >
          {getRiskLabel(finalScore)} · risk
        </span>
        {finalScore >= ALERT_THRESHOLD && (
          <span className="text-[9px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full bg-destructive text-destructive-foreground severe-pulse flex items-center gap-1" title={`Active alert threshold: ${ALERT_THRESHOLD}`}>
            <ShieldAlert className="h-2.5 w-2.5" />
            Active alert
          </span>
        )}
        {region && isLimitedSignal(region.id, quarter.id) && (
          <span className="text-[9px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full bg-muted text-muted-foreground flex items-center gap-1">
            <AlertCircle className="h-2.5 w-2.5" />
            Limited signal
          </span>
        )}
      </div>

      <ShapDriverGroup title="Top positive drivers" tone="up" items={sortedShap.filter((s) => s.value > 0).slice(0, 4)} />
      <ShapDriverGroup title="Top suppressors" tone="down" items={sortedShap.filter((s) => s.value < 0).slice(0, 4)} />

      <FeatureWaterfall baseline={baseline} finalScore={finalScore} shap={sortedShap} />

      <p className="mt-2 px-1 text-[9px] italic text-muted-foreground leading-snug">
        Indicative estimate; not an official food insecurity classification.
      </p>

      <GlossaryPanel open={glossaryOpen} onClose={() => setGlossaryOpen(false)} />
    </div>
  );
}

function FeatureWaterfall({
  baseline,
  finalScore,
  shap,
}: {
  baseline: number;
  finalScore: number;
  shap: { feature: string; value: number }[];
}) {
  const [open, setOpen] = useState(false);
  const maxAbs = Math.max(...shap.map((s) => Math.abs(s.value)), 0.01);
  let running = baseline;
  return (
    <section className="mt-3 rounded-lg overflow-hidden border border-primary/30 bg-gradient-to-br from-primary/15 via-primary/8 to-transparent">
      <button
        onClick={() => setOpen((v) => !v)}
        className="group w-full flex items-center justify-between gap-2 px-3 py-2.5 hover:bg-primary/10 transition-colors cursor-pointer"
        aria-expanded={open}
      >
        <span className="flex items-center gap-1.5 text-[10px] font-semibold uppercase tracking-[0.18em] text-primary">
          {open ? <ChevronDown className="h-3 w-3" /> : <ChevronRight className="h-3 w-3 group-hover:translate-x-0.5 transition-transform" />}
          Feature waterfall
          <span className="ml-1 text-[8px] text-primary/60 normal-case tracking-normal font-normal">
            {open ? "advanced" : "click to expand"}
          </span>
        </span>
        <span className="text-[9px] text-primary/80 font-mono-num bg-primary/15 border border-primary/30 px-1.5 py-0.5 rounded">{shap.length} features</span>
      </button>
      {open && (
        <div className="px-3 pb-3 pt-2 bg-primary/5 border-t border-primary/20">
          <div className="flex items-center justify-between text-[9px] font-mono-num text-muted-foreground/80 mb-1">
            <span>φ₀ baseline</span>
            <span>{baseline.toFixed(3)}</span>
          </div>
          <ul className="divide-y divide-border/25">
            {shap.map((s) => {
              const positive = s.value >= 0;
              const widthPct = (Math.abs(s.value) / maxAbs) * 50;
              running += s.value;
              return (
                <li key={s.feature} className="grid grid-cols-[1fr_70px_46px] items-center gap-2 py-1">
                  <span className="truncate text-[10px] text-foreground/80">{s.feature}</span>
                  <div className="relative h-[3px]">
                    <div className="absolute inset-y-0 left-1/2 w-px bg-border/60" />
                    <div
                      className={`absolute top-0 h-full rounded-sm ${positive ? "bg-risk-high" : "bg-risk-low"}`}
                      style={{
                        left: positive ? "50%" : `${50 - widthPct}%`,
                        width: `${widthPct}%`,
                      }}
                    />
                  </div>
                  <span className={`text-right font-mono-num text-[10px] tabular-nums ${positive ? "text-risk-high" : "text-risk-low"}`}>
                    {positive ? "+" : ""}{s.value.toFixed(3)}
                  </span>
                </li>
              );
            })}
          </ul>
          <div className="flex items-center justify-between text-[10px] font-mono-num mt-1.5 pt-1 border-t border-border/30">
            <span className="uppercase tracking-wider text-muted-foreground">Final Risk Level</span>
            <span className="font-bold text-foreground">{finalScore.toFixed(3)}</span>
          </div>
        </div>
      )}
    </section>
  );
}

function ShapDriverGroup({
  title,
  tone,
  items,
}: {
  title: string;
  tone: "up" | "down";
  items: { feature: string; value: number }[];
}) {
  if (!items.length) return null;
  const positive = tone === "up";

  return (
    <section className="mb-2 space-y-1.5">
      <p className={`text-[10px] font-bold uppercase tracking-wider ${positive ? "text-risk-high" : "text-risk-low"}`}>
        {title}
      </p>
      <div className="space-y-1">
        {items.map((s) => (
          <div key={s.feature} className="rounded-md border border-border/35 bg-secondary/20 px-2 py-1.5">
            <div className="mb-0.5">
              <span className="truncate text-[10px] font-bold text-foreground/90">{s.feature}</span>
            </div>
            <p className="text-[10px] leading-snug text-muted-foreground">
              {plainDriverSentence(s.feature, s.value, positive)}
            </p>
          </div>
        ))}
      </div>
    </section>
  );
}

/* ─── Plain-language driver sentence builder ─── */
const FEATURE_PHRASING: Record<string, { up: string; down: string }> = {
  "Engel Coefficient": {
    up: "Rising share of income spent on food",
    down: "Easing share of income spent on food",
  },
  "FPSI Price Stress": {
    up: "Food CPI year-on-year acceleration",
    down: "Lower-than-regional food inflation",
  },
  "Dependency Rate": {
    up: "Higher dependency ratio in households",
    down: "Lower dependency ratio in households",
  },
  "Income Decile": {
    up: "Concentration in lower income deciles",
    down: "Stronger income decile profile",
  },
  "Household Size": {
    up: "Larger average household size",
    down: "Smaller average household size",
  },
  "Income Sources": {
    up: "Narrowing diversity of income sources",
    down: "More diversified income sources",
  },
};

function plainDriverSentence(feature: string, value: number, positive: boolean): JSX.Element {
  const phrasing = FEATURE_PHRASING[feature];
  const lead = phrasing ? (positive ? phrasing.up : phrasing.down) : feature;
  const verb = positive ? "pushed the risk score up by" : "reduced the risk score by";
  const cls = positive ? "text-risk-high" : "text-risk-low";
  return (
    <>
      {lead} {verb}{" "}
      <span className={`font-mono-num font-bold ${cls}`}>
        {positive ? "+" : ""}{value.toFixed(2)}
      </span>
      .
    </>
  );
}

export function NewsArticlesCardBody({ selectedRegion }: { selectedRegion: RegionData | null }) {
  const [open, setOpen] = useState(false);
  const [activeArticle, setActiveArticle] = useState<Article | null>(null);

  const articleCount = selectedRegion
    ? PROVINCE_QUARTER_DATA.find((p) => p.id === selectedRegion.id)?.articles ?? 0
    : PROVINCE_QUARTER_DATA.reduce((s, p) => s + p.articles, 0);

  return (
    <div>
      <button
        onClick={() => setOpen((v) => !v)}
        className="w-full flex items-center justify-between"
      >
        <div className="flex items-center gap-2">
          <Newspaper className="h-3.5 w-3.5 text-primary" />
          <span className="text-[11px] font-bold uppercase tracking-wider">News Articles Analyzed</span>
          <span className="text-[10px] text-muted-foreground tabular-nums font-mono-num font-bold">{articleCount}</span>
        </div>
        {open ? <ChevronDown className="h-3.5 w-3.5 text-muted-foreground" /> : <ChevronRight className="h-3.5 w-3.5 text-muted-foreground" />}
      </button>
      {open && (
        <div className="mt-2 space-y-1 px-1">
          {SAMPLE_ARTICLES.map((a) => (
            <button
              key={a.title}
              onClick={() => setActiveArticle(a)}
              className="w-full text-left text-[10px] py-1.5 px-2 rounded hover:bg-secondary/40 text-muted-foreground hover:text-foreground transition-colors"
            >
              <p className="truncate font-semibold text-foreground/90">{a.title}</p>
              <p className="text-[9px]">{a.source} · {a.date}</p>
            </button>
          ))}
        </div>
      )}
      <Dialog open={!!activeArticle} onOpenChange={(o) => !o && setActiveArticle(null)}>
        <DialogContent className="z-[1300] max-w-md">
          <DialogHeader>
            <DialogTitle className="text-sm">{activeArticle?.title}</DialogTitle>
            <DialogDescription className="text-[11px]">{activeArticle?.source} · {activeArticle?.date}</DialogDescription>
          </DialogHeader>
          <p className="text-[12px] text-muted-foreground leading-relaxed">{activeArticle?.excerpt}</p>
          {activeArticle?.url && (
            <a
              href={activeArticle.url}
              target="_blank"
              rel="noreferrer"
              className="text-[11px] font-semibold text-primary hover:underline break-all"
            >
              Read full article ↗
            </a>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}

export function Sparkline({ data, color, width = 50, height = 16, thick = false }: { data: number[]; color: string; width?: number; height?: number; thick?: boolean }) {
  if (!data.length) return <span style={{ width, height }} />;
  const min = Math.min(...data);
  const max = Math.max(...data);
  const range = max - min || 1;
  const pts = data
    .map((v, i) => {
      const x = (i / (data.length - 1)) * width;
      const y = height - ((v - min) / range) * height;
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(" ");
  return (
    <svg width={width} height={height} className="shrink-0 overflow-visible">
      <polyline
        fill="none"
        stroke={color}
        strokeWidth={thick ? 2 : 1.4}
        strokeLinejoin="round"
        strokeLinecap="round"
        points={pts}
        style={{ filter: `drop-shadow(0 0 3px ${color})` }}
      />
    </svg>
  );
}
