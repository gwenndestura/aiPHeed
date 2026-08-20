import { useMemo, useState } from "react";
import { RegionData, MunicipalityData } from "@/data/types";
import { ChevronDown, ChevronRight, Newspaper, Sparkles, Info, ShieldAlert, AlertCircle } from "lucide-react";
import { Quarter } from "./QuarterTimeSlider";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "@/components/ui/dialog";
import {
  PROVINCE_QUARTER_DATA,
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
  const region = selectedRegion;

  return (
    <div className="h-full flex flex-col bg-card/95 backdrop-blur-sm border-l border-border/50 overflow-hidden">
      <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4">
        <ShapNarrativeCardBody quarter={quarter} selectedRegion={region} selectedMunicipality={selectedMunicipality} />
        <NewsArticlesCardBody selectedRegion={region} />
      </div>
    </div>
  );
}

/* ─── Standalone card bodies for floating cards layout ─── */

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

  const totalAbsShap = useMemo(
    () => sortedShap.reduce((s, f) => s + Math.abs(f.value), 0),
    [sortedShap]
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
            Risk jumped suddenly this quarter
          </span>
        )}
        {region && isLimitedSignal(region.id, quarter.id) && (
          <span className="text-[9px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full bg-muted text-muted-foreground flex items-center gap-1">
            <AlertCircle className="h-2.5 w-2.5" />
            Limited signal
          </span>
        )}
      </div>

      <ShapDriverGroup title="WHY IS THE RISK HIGH?" tone="up" items={sortedShap.filter((s) => s.value > 0).slice(0, 3)} totalAbsShap={totalAbsShap} />
      <ShapDriverGroup title="WHAT IS HELPING REDUCE THE RISK?" tone="down" items={sortedShap.filter((s) => s.value < 0).slice(0, 2)} totalAbsShap={totalAbsShap} />

      <p className="mt-2 px-1 text-[9px] italic text-muted-foreground leading-snug">
        AI-generated estimate only. Not an official government report.
      </p>

      <GlossaryPanel open={glossaryOpen} onClose={() => setGlossaryOpen(false)} />
    </div>
  );
}

const FEATURE_PHRASING: Record<string, { upLabel: string; upDesc: string; downLabel: string; downDesc: string }> = {
  "Engel Coefficient": {
    upLabel: "Food and rice prices are too high",
    upDesc: "Rice, vegetables, and meat cost more than usual this quarter.",
    downLabel: "Food and rice prices are stable",
    downDesc: "Food price pressures have eased compared to previous quarters.",
  },
  "FPSI Price Stress": {
    upLabel: "Typhoon hit the region",
    upDesc: "A strong typhoon damaged farms and disrupted food supply.",
    downLabel: "No major weather disruptions",
    downDesc: "Weather conditions were favorable for food production this quarter.",
  },
  "Dependency Rate": {
    upLabel: "OFW money sent home is dropping",
    upDesc: "Families are receiving less money from relatives working abroad.",
    downLabel: "OFW remittances are stable",
    downDesc: "Families are receiving steady support from relatives abroad.",
  },
  "Income Decile": {
    upLabel: "Income levels remain low",
    upDesc: "A large share of households fall in lower income brackets.",
    downLabel: "More people are employed",
    downDesc: "Job rates are stable this quarter, helping families afford food.",
  },
  "Household Size": {
    upLabel: "Households are large and stretched",
    upDesc: "Larger households have more people to feed on limited budgets.",
    downLabel: "Household conditions are manageable",
    downDesc: "Smaller household sizes reduce pressure on food budgets.",
  },
  "Income Sources": {
    upLabel: "Few income sources",
    upDesc: "Families rely on fewer types of income, increasing vulnerability.",
    downLabel: "News is not alarming",
    downDesc: "Local news has fewer reports about food shortages this quarter.",
  },
};

function ShapDriverGroup({
  title,
  tone,
  items,
  totalAbsShap,
}: {
  title: string;
  tone: "up" | "down";
  items: { feature: string; value: number }[];
  totalAbsShap: number;
}) {
  if (!items.length) return null;
  const positive = tone === "up";
  const labelColor = positive ? "text-risk-high" : "text-risk-low";
  const barColor = positive ? "hsl(var(--risk-high))" : "hsl(var(--risk-low))";

  return (
    <section className="mb-2 space-y-1.5">
      <p className={`text-[10px] font-bold uppercase tracking-wider ${labelColor}`}>
        {title}
      </p>
      <div className="space-y-1">
        {items.map((s) => {
          const phrasing = FEATURE_PHRASING[s.feature];
          const label = phrasing ? (positive ? phrasing.upLabel : phrasing.downLabel) : s.feature;
          const description = phrasing ? (positive ? phrasing.upDesc : phrasing.downDesc) : undefined;
          const pct = totalAbsShap > 0 ? Math.round((Math.abs(s.value) / totalAbsShap) * 100) : 0;

          return (
            <div key={s.feature} className="rounded-md border border-border/35 bg-secondary/20 px-2 py-1.5">
              <div className="flex items-center justify-between mb-0.5">
                <span className="truncate text-[10px] font-bold text-foreground/90">{label}</span>
                <span className={`text-[10px] font-mono-num font-bold ml-2 shrink-0 ${labelColor}`}>{pct}%</span>
              </div>
              {description && (
                <p className="text-[10px] leading-snug text-muted-foreground">{description}</p>
              )}
              <div className="mt-1 h-[3px] rounded-full bg-border/30 overflow-hidden">
                <div className="h-full rounded-full opacity-70" style={{ width: `${Math.min(pct * 2, 100)}%`, backgroundColor: barColor }} />
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
}

const NEWS_TOPICS = [
  { label: "Food prices", pct: 42, color: "hsl(var(--risk-high))" },
  { label: "Typhoon", pct: 31, color: "hsl(var(--risk-moderate))" },
  { label: "Workers", pct: 18, color: "hsl(var(--primary))" },
  { label: "OFW", pct: 6, color: "#8b5cf6" },
  { label: "Fish kill", pct: 3, color: "#06b6d4" },
] as const;

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
        <div className="mt-3 space-y-3 px-1">
          {/* Topic breakdown */}
          <div className="space-y-2">
            {NEWS_TOPICS.map((t) => (
              <div key={t.label}>
                <div className="flex items-center justify-between text-[10px] mb-0.5">
                  <span className="text-foreground/80 font-medium">{t.label}</span>
                  <span className="font-mono-num font-bold text-foreground/70">{t.pct}%</span>
                </div>
                <div className="h-[4px] rounded-full bg-border/30 overflow-hidden">
                  <div className="h-full rounded-full opacity-80" style={{ width: `${t.pct}%`, backgroundColor: t.color }} />
                </div>
              </div>
            ))}
          </div>

          {/* Clickable articles */}
          <div className="space-y-1 border-t border-border/30 pt-2">
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
