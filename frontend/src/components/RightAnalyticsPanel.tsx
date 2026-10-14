import { useState } from "react";
import { RegionData, MunicipalityData } from "@/data/types";
import { ChevronDown, ChevronRight, Newspaper, Info } from "lucide-react";
import { Quarter } from "./QuarterTimeSlider";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "@/components/ui/dialog";
import { useConfig, useExplainability, useNews } from "@/lib/queries";
import type { Trigger, NewsArticle } from "@/lib/apiTypes";
import { GlossaryPanel } from "./GlossaryPanel";
import { quarterPeriodLabel } from "@/lib/quarters";
import { isHighRisk } from "@/lib/risk";
import { driverCopy, TOPIC_FRIENDLY_LABELS } from "@/lib/driverCopy";
import { StatusBadge } from "@/components/ui/status-badge";
import { ConfidenceTag } from "@/components/ui/confidence-tag";
import { Note } from "@/components/ui/note";
import { StatusDot } from "@/components/ui/status-dot";
import { isLoadFailure, LOAD_ERROR_MESSAGE } from "@/lib/loadError";

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
        <NewsArticlesCardBody selectedRegion={region} quarterId={quarter.id} />
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
  const { data: config } = useConfig();

  // Same source of truth as the left "Why is this Province at Risk?" card.
  // Recomputed per province × quarter.
  const scope = region ? "province" : "region";
  const id = region?.id ?? "calabarzon";
  const { data: explain, isLoading: explainLoading, error: explainError } = useExplainability(scope, id, quarter.id);
  const triggers: Trigger[] = explain?.triggers ?? [];
  const explainFailed = isLoadFailure(explainError);

  // Badges only for a real score -- never a 0 standing in for "unknown".
  const rawScore = explain?.riskScore ?? region?.riskScore;
  const hasScore = !explainFailed && typeof rawScore === "number";
  const finalScore = hasScore ? rawScore : 0;
  const displayCutoff = config?.thresholds.riskDisplayCutoff ?? 0.5;
  const alertThreshold = config?.thresholds.alertThreshold ?? 0.6;

  const subjectName = selectedMunicipality
    ? `${selectedMunicipality.name}, ${selectedMunicipality.provinceName}`
    : region ? region.name : "CALABARZON";

  return (
    <div key={`${subjectName}-${quarter.id}`} className="animate-fade-in">
      <div className="flex items-start justify-between gap-2 mb-2">
        <div className="min-w-0">
          <p className="text-[11px] text-muted-foreground">{quarterPeriodLabel(quarter)}</p>
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
        {hasScore && (
          <StatusBadge
            level={isHighRisk(finalScore, displayCutoff) ? "high" : "low"}
            title={`Forecast display cutoff: ${displayCutoff}`}
          />
        )}
        {hasScore && finalScore >= alertThreshold && (
          <StatusBadge tone="high" title={`Active alert: risk level at or above ${alertThreshold}`}>
            Active alert
          </StatusBadge>
        )}
        {region?.limitedSignal && (
          <ConfidenceTag explanation="This province had fewer than the minimum number of geocoded news articles this quarter." />
        )}
      </div>

      {explainLoading ? (
        <ShapDriverListSkeleton />
      ) : explainFailed ? (
        <Note label={null}>{LOAD_ERROR_MESSAGE}</Note>
      ) : (
        <ShapDriverList items={triggers} />
      )}

      {!explainFailed && (
        <p className="mt-2 px-1 text-[9px] italic text-muted-foreground leading-snug">
          {explainLoading
            ? "Computing the SHAP breakdown for this quarter…"
            : (explain?.note ?? "SHAP explainability — grouped driver shares, sum to 100%. AI-generated estimate only; not an official government report.")}
        </p>
      )}

      <GlossaryPanel open={glossaryOpen} onClose={() => setGlossaryOpen(false)} />
    </div>
  );
}

function ShapDriverListSkeleton() {
  return (
    <section className="mb-2 space-y-3 animate-pulse">
      {[0, 1].map((g) => (
        <div key={g} className="space-y-1.5">
          <div className="h-2.5 w-32 rounded bg-secondary/50" />
          <div className="space-y-1">
            {[0, 1].map((i) => (
              <div key={i} className="rounded-md border border-border/35 bg-secondary/20 px-2 py-1.5">
                <div className="flex items-center justify-between mb-1.5">
                  <div className="h-2.5 w-28 rounded bg-secondary/50" />
                  <div className="h-2.5 w-6 rounded bg-secondary/50" />
                </div>
                <div className="h-2 w-full rounded bg-secondary/40 mb-1.5" />
                <div className="h-[3px] rounded-full bg-border/30" />
              </div>
            ))}
          </div>
        </div>
      ))}
    </section>
  );
}

function ShapDriverList({ items }: { items: Trigger[] }) {
  if (!items.length) return null;
  const risky = items.filter((t) => t.direction !== "protective");
  const protective = items.filter((t) => t.direction === "protective");
  return (
    <section className="mb-2 space-y-3">
      {risky.length > 0 && (
        <DriverGroup heading="Factors pushing risk up" headingColor="hsl(var(--risk-high))" items={risky} />
      )}
      {protective.length > 0 && (
        <DriverGroup heading="Factors pulling risk down" headingColor="hsl(var(--risk-moderate))" items={protective} />
      )}
    </section>
  );
}

function DriverGroup({ heading, headingColor, items }: { heading: string; headingColor: string; items: Trigger[] }) {
  return (
    <div className="space-y-1.5">
      <p className="flex items-center gap-1.5 text-[12px] font-semibold text-foreground/90">
        <StatusDot color={headingColor} />
        {heading}
      </p>
      <div className="space-y-1">
        {items.map((s) => {
          const color = s.color === "red" ? "hsl(var(--risk-high))" : s.color === "green" ? "hsl(var(--risk-low))" : "hsl(var(--risk-moderate))";
          const copy = driverCopy(s);
          return (
            <div key={s.key} className="rounded-md border border-border/35 bg-secondary/20 px-2 py-1.5">
              <div className="flex items-center justify-between mb-0.5">
                <span className="truncate text-[10px] font-bold text-foreground/90">{copy.title}</span>
                <span className="text-[10px] font-mono-num font-bold ml-2 shrink-0" style={{ color }}>{s.pct}%</span>
              </div>
              <p className="text-[10px] leading-snug text-muted-foreground">{copy.description}</p>
              <div className="mt-1 h-[3px] rounded-full bg-border/30 overflow-hidden">
                <div className="h-full rounded-full opacity-70" style={{ width: `${s.pct}%`, backgroundColor: color }} />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

export function NewsArticlesCardBody({ selectedRegion, quarterId }: { selectedRegion: RegionData | null; quarterId?: string }) {
  const [open, setOpen] = useState(false);
  const [activeArticle, setActiveArticle] = useState<NewsArticle | null>(null);

  const scope = selectedRegion ? "province" : "region";
  const id = selectedRegion?.id ?? "calabarzon";
  // Fetched even while collapsed: the header count needs it, and at region
  // scope there is no selectedRegion to fall back on, so deferring the call
  // until the drawer opened left CALABARZON reading 0. The corpus is cached
  // server-side (lru_cache), so this is a cheap read.
  const { data: news } = useNews(scope, id, quarterId);

  const articleCount = news?.articleCount ?? selectedRegion?.articleCount ?? 0;
  // Region-wide articles (province = null in the corpus) count toward
  // CALABARZON but toward no province, so the five province counts sum to
  // less than the regional one.
  const regionWide = !selectedRegion && news ? news.articleCount - news.provinceAttributed : 0;

  return (
    <div>
      <button
        onClick={() => setOpen((v) => !v)}
        className="w-full flex items-center justify-between"
      >
        <div className="flex items-center gap-2">
          <Newspaper className="h-3.5 w-3.5 text-primary" />
          <span className="text-[13px] font-semibold leading-tight">News articles analyzed</span>
          <span className="text-[10px] text-muted-foreground tabular-nums font-mono-num font-bold">{articleCount}</span>
        </div>
        {open ? <ChevronDown className="h-3.5 w-3.5 text-muted-foreground" /> : <ChevronRight className="h-3.5 w-3.5 text-muted-foreground" />}
      </button>
      {open && (
        <div className="mt-3 space-y-3 px-1">
          {news && news.sourceQuarter !== news.quarter && (
            <p className="text-[9px] italic text-muted-foreground leading-snug">
              Forecast quarter — showing {news.sourceQuarter.split("-").reverse().join(" ")} articles, the latest news the forecast was built from.
            </p>
          )}
          {regionWide > 0 && news && (
            <p className="text-[9px] italic text-muted-foreground leading-snug">
              {news.provinceAttributed} tagged to a province · {regionWide} cover CALABARZON as a whole
            </p>
          )}

          {/* Topic breakdown */}
          {news && news.topics.length > 0 && (
            <div className="space-y-2">
              {news.topics.map((t) => (
                <div key={t.key}>
                  <div className="flex items-center justify-between text-[10px] mb-0.5">
                    <span className="text-foreground/80 font-medium">{TOPIC_FRIENDLY_LABELS[t.key] ?? t.label}</span>
                    <span className="font-mono-num font-bold text-foreground/70">{t.pct}%</span>
                  </div>
                  <div className="h-[4px] rounded-full bg-border/30 overflow-hidden">
                    <div className="h-full rounded-full opacity-80" style={{ width: `${t.pct}%`, backgroundColor: "hsl(var(--primary))" }} />
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Clickable articles */}
          <div className="space-y-1 border-t border-border/30 pt-2">
            {!news?.data.length && (
              <p className="text-[10px] text-muted-foreground/70 italic px-2 py-1.5">No articles for this quarter.</p>
            )}
            {news?.data.map((a) => (
              <button
                key={a.id}
                onClick={() => setActiveArticle(a)}
                className="w-full text-left text-[10px] py-1.5 px-2 rounded hover:bg-secondary/40 text-muted-foreground hover:text-foreground transition-colors"
              >
                <p className="truncate font-semibold text-foreground/90">{a.title}</p>
                <p className="text-[9px]">{a.source}{a.date ? ` · ${a.date}` : ""}</p>
              </button>
            ))}
          </div>
        </div>
      )}

      <Dialog open={!!activeArticle} onOpenChange={(o) => !o && setActiveArticle(null)}>
        <DialogContent className="z-[1300] max-w-md">
          <DialogHeader>
            <DialogTitle className="text-sm">{activeArticle?.title}</DialogTitle>
            <DialogDescription className="text-[11px]">
              {activeArticle?.source}{activeArticle?.date ? ` · ${activeArticle.date}` : ""}
            </DialogDescription>
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
