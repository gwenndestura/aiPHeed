import { useLayoutEffect, useRef, useState } from "react";
import { RegionData, MunicipalityData, RISK_COLORS, RISK_LABELS } from "@/data/types";
import { X, ChevronRight, ArrowLeft, Briefcase, Plane, CloudRain, Store, Fish } from "lucide-react";
import { AboutModal } from "./AboutModal";
import { FeedbackModal } from "./FeedbackModal";
import { useCountUp } from "@/hooks/useCountUp";
import { useConfig, useExplainability, useForecast } from "@/lib/queries";
import type { Trigger } from "@/lib/apiTypes";
import { StatusBadge } from "@/components/ui/status-badge";
import { ConfidenceTag } from "@/components/ui/confidence-tag";
import { Note } from "@/components/ui/note";
import { MetricLabel, formatSigned, changeTone } from "@/components/ui/metric";
import { StatusDot } from "@/components/ui/status-dot";
import { ExplainTip } from "@/components/ui/explain-tip";
import { isHighRisk } from "@/lib/risk";
import { isLoadFailure, LOAD_ERROR_MESSAGE } from "@/lib/loadError";
import { useMediaQuery } from "@/hooks/useMediaQuery";

interface Props {
  selectedRegion: RegionData | null;
  previewRegion: RegionData | null;
  selectedMunicipality: MunicipalityData | null;
  quarterId: string;
  regionsData: RegionData[];
  municipalitiesData: MunicipalityData[];
  onClose: () => void;
  onCloseMunicipality: () => void;
  onRegionClick: (r: RegionData) => void;
  onMunicipalityClick: (m: MunicipalityData) => void;
  rejectedProvinceIds?: Set<string>;
}

export function LeftPanel({
  selectedRegion,
  previewRegion,
  selectedMunicipality,
  quarterId,
  regionsData,
  municipalitiesData,
  onClose,
  onCloseMunicipality,
  onRegionClick,
  onMunicipalityClick,
  rejectedProvinceIds,
}: Props) {
  const activeRegion = selectedRegion || previewRegion;
  const isRegionRejected = !!activeRegion && !!rejectedProvinceIds?.has(activeRegion.id);
  const isMuniRejected = !!selectedMunicipality && !!rejectedProvinceIds?.has(selectedMunicipality.provinceId);

  return (
    <div className="h-full flex flex-col overflow-hidden">
      {/* Content */}
      <div className="flex-1 overflow-y-auto">
        {selectedMunicipality ? (
          isMuniRejected ? (
            <RejectedForecastPlaceholder
              name={selectedMunicipality.provinceName}
              onBack={onCloseMunicipality}
            />
          ) : (
            <MunicipalityDetail
              municipality={selectedMunicipality}
              onBack={onCloseMunicipality}
            />
          )
        ) : activeRegion ? (
          isRegionRejected ? (
            <RejectedForecastPlaceholder
              name={activeRegion.name}
              isLocked={!!selectedRegion}
              onClose={onClose}
            />
          ) : (
            <RegionDetail
              region={activeRegion}
              quarterId={quarterId}
              isLocked={!!selectedRegion}
              onClose={onClose}
              municipalitiesData={municipalitiesData}
              onMunicipalityClick={onMunicipalityClick}
            />
          )
        ) : (
          <div className="px-5 py-4 space-y-3">
            <RfiiScoreCardBody quarterId={quarterId} regionsData={regionsData} />
            <RiskDriversCardBody quarterId={quarterId} />
            <ProvinceRankingCardBody onRegionClick={onRegionClick} regionsData={regionsData} />
          </div>
        )}
      </div>

      {/* Footer: About + Feedback */}
      <div className="shrink-0 border-t border-border/40 px-4 py-2.5 flex items-center justify-between gap-2 bg-card/60" data-tour="about">
        <AboutModal />
        <span className="text-[10px] text-muted-foreground/30">·</span>
        <FeedbackModal />
      </div>
    </div>
  );
}

/* ─── Reusable card bodies (used by floating cards in Index.tsx) ─── */

export function RfiiScoreCardBody({
  quarterId,
  quarterLabel,
  regionsData,
  loadFailed = false,
}: {
  quarterId?: string;
  quarterLabel?: string;
  regionsData: RegionData[];
  /** The province list or timeline failed to load. */
  loadFailed?: boolean;
}) {
  const { data: regionForecast, error: forecastError } = useForecast("region", "calabarzon", quarterId || undefined, "nowcast");
  const failed = loadFailed || isLoadFailure(forecastError);
  // No score is not a score of zero: while loading, after a failure, or when
  // every province is withheld, show "—" and no band rather than 0.00 / LOW.
  const rawScore = regionForecast?.riskScore;
  const hasScore = !failed && typeof rawScore === "number";
  const avgScore = hasScore ? rawScore : 0;
  const animScore = useCountUp(avgScore, 1000, 2);

  let high = 0, low = 0, limited = 0;
  regionsData.forEach((r) => {
    if (r.riskLevel === "high") high++;
    else low++;
    if (r.limitedSignal) limited++;
  });

  // The server's band, else the score as displayed: 0.4993 reads "0.50",
  // and a score shown as 0.50 is HIGH.
  const isHigh = regionForecast?.riskLevel ? regionForecast.riskLevel === "high" : isHighRisk(avgScore);
  const band =
    !hasScore ? { label: "", color: "hsl(var(--muted-foreground))" }
    : isHigh ? { label: "HIGH", color: "hsl(var(--risk-high))" }
    : { label: "LOW", color: "hsl(var(--risk-low))" };

  // Position of pointer along 0..1 segmented track
  const trackPct = Math.min(Math.max(animScore, 0), 1) * 100;

  // The glow follows the band's colour (red for high, yellow for low). The
  // colour is "hsl(var(--risk-high))": `accent` is its "var(--risk-high)", so
  // `glow(0.4)` is that colour at 40% opacity. With reduced motion the glow
  // stays, still.
  const reduceMotion = useMediaQuery("(prefers-reduced-motion: reduce)");
  const accent = band.color.replace('hsl(', '').replace(')', '');
  const glow = (alpha: number) => `hsl(${accent} / ${alpha})`;

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-baseline justify-between gap-x-2 gap-y-0.5">
        <h3 className="text-[13px] font-semibold leading-tight">Regional average risk level</h3>
        {quarterLabel && (
          <p className="text-[11px] text-muted-foreground tabular-nums">{quarterLabel}</p>
        )}
      </div>

      <div
        className="relative rounded-xl border edge-faint bg-gradient-to-br from-secondary/35 via-card/60 to-background/40 px-5 pt-5 pb-4 overflow-hidden"
        style={{
          ['--accent-color' as string]: accent,
          // Still: the pulse's resting glow (rfii-hero-pulse at 0%).
          ...(reduceMotion
            ? { boxShadow: `0 0 0 1px ${glow(0.55)}, 0 0 24px -2px ${glow(0.45)}, 0 0 60px -10px ${glow(0.35)}, inset 0 0 30px -8px ${glow(0.25)}` }
            : { animation: 'rfii-hero-pulse 3.6s ease-in-out infinite' }),
        } as React.CSSProperties}
      >
        {/* Aurora sweep */}
        <div
          className="pointer-events-none absolute -inset-[30%] opacity-50 blur-2xl"
          style={{
            background: `conic-gradient(from 0deg, transparent 0deg, ${glow(0.33)} 90deg, transparent 180deg, ${glow(0.2)} 270deg, transparent 360deg)`,
            animation: reduceMotion ? undefined : 'rfii-aurora 14s linear infinite',
          }}
        />
        {/* Top edge accent line */}
        <div
          className="pointer-events-none absolute top-0 left-4 right-4 h-px"
          style={{ background: `linear-gradient(90deg, transparent, ${band.color}, transparent)` }}
        />

        <div className="relative flex flex-col">
          {/* Eyebrow */}
          <div className="flex items-center gap-2 mb-1">
            <MetricLabel className="uppercase tracking-[0.28em]">Forecast index</MetricLabel>
          </div>

          {/* Hero score. DM Mono gives the "." a full digit's width: the tighter
              spacing and gap keep "/ 1.00" beside it in the 320px side panel. */}
          <div className="flex items-end gap-2">
            <span
              className="font-mono-num font-black tabular-nums leading-[0.85] tracking-[-0.06em]"
              style={{
                fontSize: '5.5rem',
                color: band.color,
                textShadow: `0 0 32px ${glow(0.8)}, 0 0 70px ${glow(0.4)}`,
                animation: reduceMotion ? undefined : 'rfii-score-breathe 3.2s ease-in-out infinite',
                transformOrigin: 'left bottom',
              }}
            >
              {hasScore ? animScore.toFixed(2) : "—"}
            </span>
            <span className="text-[11px] text-muted-foreground font-mono-num whitespace-nowrap pb-2">/ 1.00</span>
          </div>

          {/* Risk band pill -- only for a real score */}
          {hasScore && (
            <div className="mt-2.5">
              <StatusBadge level={isHigh ? "high" : "low"} />
            </div>
          )}

          {failed ? (
            <Note label={null} className="mt-2.5">{LOAD_ERROR_MESSAGE}</Note>
          ) : (
            <p className="mt-2.5 text-[10px] text-muted-foreground/85 leading-snug">
              Average across all {regionsData.length || 5} provinces
            </p>
          )}

          {/* Segmented 0–1 risk scale with pointer */}
          <div className="mt-3.5">
            <div className="relative h-2 w-full rounded-full overflow-visible">
              <div
                className="absolute inset-0 rounded-full"
                style={{
                  background: 'linear-gradient(90deg, hsl(var(--risk-low)) 0%, hsl(var(--risk-high)) 100%)',
                  opacity: 0.85,
                }}
              />
              {/* Segment divider at 0.5 */}
              {[50].map((p) => (
                <div key={p} className="absolute top-0 bottom-0 w-px bg-background/60" style={{ left: `${p}%` }} />
              ))}
              {/* Pointer -- only for a real score */}
              {hasScore && <div
                className="absolute -top-1 -bottom-1 w-[3px] rounded-full"
                style={{
                  left: `calc(${trackPct}% - 1.5px)`,
                  background: 'hsl(var(--foreground))',
                  boxShadow: `0 0 10px ${band.color}, 0 0 20px ${glow(0.8)}`,
                  transition: 'left 1.4s cubic-bezier(0.22,1,0.36,1)',
                }}
              />}
            </div>
            <div className="flex justify-between text-[10px] uppercase tracking-wider text-muted-foreground font-mono-num mt-1.5">
              <span>0.0 low</span>
              <span>0.5</span>
              <span>1.0 high</span>
            </div>
          </div>
        </div>
      </div>

      {/* Columns share the width but never get narrower than their label. */}
      <div className="grid grid-cols-[repeat(3,minmax(max-content,1fr))] gap-2">
        <SummaryChip label="High risk" value={failed ? "—" : high} color="hsl(var(--risk-high))" />
        <SummaryChip label="Low risk" value={failed ? "—" : low} color="hsl(var(--risk-low))" />
        <SummaryChip
          label="Limited data"
          value={failed ? "—" : limited}
          color="hsl(var(--muted-foreground))"
          tip="Provinces with fewer than 5 news articles linked to them this quarter, so their forecast rests on less news evidence."
        />
      </div>
    </div>
  );
}

const TRIGGER_ICONS: Record<string, typeof Briefcase> = {
  market: Store,
  climate: CloudRain,
  fish_kill: Fish,
  employment: Briefcase,
  ofw_remittance: Plane,
};

export function RiskDriversCardBody({
  provinceId = null,
  quarterId,
}: { provinceId?: string | null; quarterId?: string }) {
  // Same source of truth as the right-panel SHAP card: every trigger group
  // the model reports, always shown (even at 0%), ranked high → low.
  const scope = provinceId ? "province" : "region";
  const id = provinceId ?? "calabarzon";
  const { data, isLoading, error } = useExplainability(scope, id, quarterId || undefined);
  const drivers: Trigger[] = data?.triggers ?? [];
  const failed = isLoadFailure(error);

  return (
    <div key={`${provinceId ?? "region"}-${quarterId}`}>
      <div className="flex items-center gap-2 mb-3">
        <h3 className="text-[13px] font-semibold leading-tight">Why is this province at risk?</h3>
        <span className="text-[9px] text-muted-foreground/60 ml-auto">
          {isLoading ? "Computing…" : failed ? "" : "Ranked"}
        </span>
      </div>
      {isLoading ? (
        <DriverRowsSkeleton />
      ) : failed ? (
        <Note label={null}>{LOAD_ERROR_MESSAGE}</Note>
      ) : (
      <div className="space-y-2">
        {drivers.map((d, i) => {
          const Icon = TRIGGER_ICONS[d.key] ?? Store;
          const color = d.color === "red" ? "hsl(var(--risk-high))" : d.color === "green" ? "hsl(var(--risk-low))" : "hsl(var(--risk-moderate))";
          return (
            <div key={d.key} className="grid grid-cols-[18px_1fr_42px] items-center gap-2">
              <Icon className="h-3.5 w-3.5 text-muted-foreground" />
              <div>
                <div className="flex items-center justify-between text-[10px] mb-1">
                  <span className="font-semibold">{d.label}</span>
                </div>
                <div className="h-2 bg-secondary/40 rounded-full overflow-hidden">
                  <div
                    className="h-full rounded-full animate-bar-fill"
                    style={{
                      animationDelay: `${i * 80}ms`,
                      width: `${d.pct}%`,
                      background: color,
                      boxShadow: `0 0 6px ${color}80`,
                    }}
                  />
                </div>
              </div>
              <span className="font-mono-num text-[10px] font-bold tabular-nums text-right" style={{ color }}>
                {d.pct}%
              </span>
            </div>
          );
        })}
      </div>
      )}
    </div>
  );
}

function DriverRowsSkeleton() {
  return (
    <div className="space-y-2 animate-pulse">
      {[85, 60, 45, 30, 20].map((w, i) => (
        <div key={i} className="grid grid-cols-[18px_1fr_42px] items-center gap-2">
          <div className="h-3.5 w-3.5 rounded-full bg-secondary/50" />
          <div>
            <div className="h-2.5 w-20 rounded bg-secondary/50 mb-1.5" />
            <div className="h-2 rounded-full bg-secondary/40 overflow-hidden">
              <div className="h-full rounded-full bg-secondary/70" style={{ width: `${w}%` }} />
            </div>
          </div>
          <div className="h-2.5 w-6 rounded bg-secondary/50 justify-self-end" />
        </div>
      ))}
    </div>
  );
}

export function ProvinceRankingCardBody({
  onRegionClick,
  regionsData,
  loadFailed = false,
}: {
  onRegionClick: (r: RegionData) => void;
  regionsData: RegionData[];
  /** The province list failed to load. */
  loadFailed?: boolean;
}) {
  const sortedProvinces = regionsData.slice().sort((a, b) => b.riskScore - a.riskScore);
  const maxScore = Math.max(...regionsData.map((r) => r.riskScore), 0.01);

  return (
    <div>
      <div className="flex items-center gap-2 mb-3">
        <h3 className="text-[13px] font-semibold leading-tight">Province ranking</h3>
        <span className="text-[9px] text-muted-foreground/60 ml-auto">High → Low</span>
      </div>
      {loadFailed && <Note label={null}>{LOAD_ERROR_MESSAGE}</Note>}
      <div className="space-y-1.5">
        {sortedProvinces.map((r) => {
          const widthPct = (r.riskScore / maxScore) * 100;
          return (
            <button
              key={r.id}
              onClick={() => onRegionClick(r)}
              className="w-full text-left group px-1 py-1 compact:min-h-11 rounded-md hover:bg-secondary/40 transition-colors"
            >
              <div className="flex items-center justify-between text-[10px] mb-1">
                <span className="font-semibold flex items-center gap-1.5">
                  <StatusDot color={RISK_COLORS[r.riskLevel]} />
                  {r.name}
                  <span className="text-[9px] text-muted-foreground ml-1 opacity-60">
                    {RISK_LABELS[r.riskLevel]}
                  </span>
                </span>
                <span className="font-mono-num font-bold tabular-nums" style={{ color: RISK_COLORS[r.riskLevel] }}>
                  {r.riskScore.toFixed(2)}
                </span>
              </div>
              <div className="h-2 bg-secondary/40 rounded-full overflow-hidden">
                <div
                  className="h-full rounded-full animate-bar-fill"
                  style={{ width: `${widthPct}%`, backgroundColor: RISK_COLORS[r.riskLevel] }}
                />
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}


/* ─── Rejected forecast placeholder ─── */
function RejectedForecastPlaceholder({
  name,
  isLocked,
  onClose,
  onBack,
}: {
  name: string;
  isLocked?: boolean;
  onClose?: () => void;
  onBack?: () => void;
}) {
  return (
    <div className="px-5 py-4 space-y-4">
      <div className="flex items-start justify-between gap-2">
        <div>
          {onBack && (
            <button
              onClick={onBack}
              className="flex items-center gap-1.5 compact:min-h-11 text-[10px] text-muted-foreground hover:text-foreground transition-colors group mb-2"
            >
              <ArrowLeft className="h-3 w-3 group-hover:-translate-x-0.5 transition-transform" />
              Back
            </button>
          )}
          <p className="text-[11px] text-muted-foreground">Province of</p>
          <h2 className="text-base font-bold leading-tight">{name}</h2>
        </div>
        {isLocked && onClose && (
          <button onClick={onClose} aria-label="Close" className="p-1.5 compact:min-h-11 compact:min-w-11 flex items-center justify-center rounded-lg hover:bg-secondary transition-colors">
            <X className="h-4 w-4 text-muted-foreground" />
          </button>
        )}
      </div>
      <div className="inner-box px-4 py-8 flex flex-col items-center text-center space-y-2">
        <span className="text-3xl text-muted-foreground/30 select-none">—</span>
        <p className="text-[11px] font-semibold text-muted-foreground">No forecast available</p>
        <p className="text-[10px] text-muted-foreground/60 leading-snug max-w-[200px]">
          This quarter's forecast has been rejected by the admin and is not available for display.
        </p>
      </div>
    </div>
  );
}

/* ─── Province (Region) Detail ─── */
function RegionDetail({
  region,
  quarterId,
  isLocked,
  onClose,
  municipalitiesData,
  onMunicipalityClick,
}: {
  region: RegionData;
  quarterId: string;
  isLocked: boolean;
  onClose: () => void;
  municipalitiesData: MunicipalityData[];
  onMunicipalityClick: (m: MunicipalityData) => void;
}) {
  const { data: config } = useConfig();
  const riskColor = RISK_COLORS[region.riskLevel];
  const qoqText = formatSigned(region.momChange, 1, "%");
  const munis = municipalitiesData.slice().sort((a, b) => b.riskScore - a.riskScore);

  const displayCutoff = config?.thresholds.riskDisplayCutoff ?? 0.5;
  const alertThreshold = config?.thresholds.alertThreshold ?? 0.6;
  const limited = region.limitedSignal;
  const isHigh = isHighRisk(region.riskScore, displayCutoff);
  const isActiveAlert = region.riskScore >= alertThreshold;
  const horizonLabel = config?.indicator.horizon ?? "same-quarter nowcast";
  // A past quarter is a backtest or an earlier forecast, not the issued
  // forecast that config.indicator.horizon describes (same request as the
  // Why panel's, shared cache).
  const { data: explain } = useExplainability("province", region.id, quarterId || undefined);
  const est = explain?.summary;
  const quarterText = quarterId ? quarterId.split("-").reverse().join(" ") : "the selected quarter";

  return (
    <div className="px-5 py-4 space-y-4">
      {/* Header */}
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-start gap-3">
          <div>
            <p className="text-[11px] text-muted-foreground">Province of</p>
            <h2 className="text-base font-bold leading-tight">{region.name}</h2>
            <div className="flex flex-wrap items-center gap-1.5 mt-1.5">
              <StatusBadge
                level={isHigh ? "high" : "low"}
                title={`Forecast risk level (${displayCutoff.toFixed(2)} display cutoff)`}
              />
              {isActiveAlert && (
                <StatusBadge tone="high" title={`Active alert: risk level at or above ${alertThreshold}`}>
                  Active alert
                </StatusBadge>
              )}
              {limited && (
                <ConfidenceTag explanation="This province had fewer than the minimum number of geocoded news articles this quarter." />
              )}
              {!!region.seriesNeedingReview && (
                <ConfidenceTag
                  explanation={`${region.seriesNeedingReview} of ${region.seriesMonitored ?? "?"} monitored commodity series scored below the model's confidence cutoff this quarter. They still count fully in the risk level score; this flags them for analyst review and does not exclude them.`}
                >
                  {region.seriesNeedingReview} series need review
                </ConfidenceTag>
              )}
            </div>
          </div>
        </div>
        {isLocked && (
          <button onClick={onClose} aria-label="Close" className="p-1.5 compact:min-h-11 compact:min-w-11 flex items-center justify-center rounded-lg hover:bg-secondary transition-colors">
            <X className="h-4 w-4 text-muted-foreground" />
          </button>
        )}
      </div>

      {/* Confidence statement */}
      <Note>
        {est && est.estimateKind === "backtest"
          ? `This is a backtest estimate for ${quarterText}, made as of ${est.issued} with only information published before that date (development evidence, not a forecast issued live). Observed outcome: ${est.observedOutcome ?? "not available"}.`
          : est && est.estimateKind === "earlier_forecast"
            ? `This is the Lead-2 forecast for ${quarterText} issued ${est.issued}, based only on information published before that date; its outcome is not yet published.`
            : `This is a ${horizonLabel} for ${quarterText}, based only on information published before the forecast was issued.`}
      </Note>

      {/* Key Metrics */}
      <div className="grid grid-cols-2 gap-2.5">
        <div className="inner-box px-3 py-3">
          <MetricLabel>Risk level score</MetricLabel>
          <div className="text-3xl font-extrabold mt-1 tracking-tight tabular-nums">{region.riskScore.toFixed(2)}</div>
          <div className="h-1.5 rounded-full mt-2 bg-muted overflow-hidden">
            <div className="h-full rounded-full transition-all" style={{ width: `${region.riskScore * 100}%`, backgroundColor: riskColor }} />
          </div>
        </div>
        <div className="inner-box px-3 py-3 overflow-hidden">
          <MetricLabel>Quarter-on-quarter change</MetricLabel>
          <FitText
            text={qoqText}
            className={`font-extrabold mt-1 tracking-tight tabular-nums ${
              { neutral: "text-foreground", danger: "text-value-danger", success: "text-value-success" }[changeTone(region.momChange)]
            }`}
            maxSize={30}
            minSize={11}
          />
        </div>
      </div>

      {/* Population */}
      <div className="inner-box px-3 py-2.5 flex items-center justify-between">
        <div>
          <MetricLabel>Population</MetricLabel>
          <div className="text-sm font-bold mt-0.5 tabular-nums">{region.population.toLocaleString()}</div>
        </div>
      </div>

      {/* Trigger composition */}
      <TriggerCompositionBar provinceId={region.id} quarterId={quarterId} />

      {/* Municipalities list */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <h3 className="text-[13px] font-semibold leading-tight">Cities and municipalities</h3>
          </div>
          <span className="text-[9px] text-muted-foreground tabular-nums">{munis.length}</span>
        </div>
        <p className="text-[9px] text-muted-foreground/70 italic mb-2 leading-snug">
          Relative prioritization derived from the province forecast with PSA poverty and population density; not validated municipal forecasts.
        </p>
        <div className="space-y-1 max-h-[260px] overflow-y-auto thin-scrollbar pr-1">
          {munis.map((m) => (
            <button
              key={m.id}
              onClick={() => onMunicipalityClick(m)}
              className="w-full flex items-center justify-between bg-secondary/60 hover:bg-secondary rounded-md px-2.5 py-2 compact:min-h-11 transition-all text-left group"
            >
              <div className="flex items-center gap-2 min-w-0">
                <span
                  className="w-1.5 h-1.5 rounded-full shrink-0"
                  style={{ backgroundColor: RISK_COLORS[m.riskLevel] }}
                />
                <div className="min-w-0">
                  <div className="text-[11px] font-semibold truncate">{m.name}</div>
                  <div className="text-[9px] text-muted-foreground/70 flex items-center gap-1.5">
                    <span>{m.classification}</span>
                    {m.limitedSignal && <ConfidenceTag className="text-[9px]">Limited data</ConfidenceTag>}
                  </div>
                </div>
              </div>
              <div className="flex items-center gap-1.5 shrink-0">
                <span className="text-[11px] font-bold tabular-nums font-mono-num" style={{ color: RISK_COLORS[m.riskLevel] }}>
                  {m.riskScore.toFixed(2)}
                </span>
                <ChevronRight className="h-3 w-3 text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity" />
              </div>
            </button>
          ))}
        </div>
      </div>

    </div>
  );
}

/* ─── Municipality / City Detail ─── */
function MunicipalityDetail({
  municipality,
  onBack,
}: {
  municipality: MunicipalityData;
  onBack: () => void;
}) {
  const riskColor = RISK_COLORS[municipality.riskLevel];

  return (
    <div className="px-5 py-4 space-y-4">
      {/* Back to province */}
      <button
        onClick={onBack}
        className="flex items-center gap-1.5 compact:min-h-11 text-[10px] text-muted-foreground hover:text-foreground transition-colors group"
      >
        <ArrowLeft className="h-3 w-3 group-hover:-translate-x-0.5 transition-transform" />
        Back to {municipality.provinceName}
      </button>

      {/* Header */}
      <div className="flex items-start gap-3">
        <div>
          <p className="text-[11px] text-muted-foreground">{municipality.classification} of</p>
          <h2 className="text-base font-bold leading-tight">{municipality.name}</h2>
          <p className="text-[10px] text-muted-foreground mt-0.5">{municipality.provinceName}, CALABARZON</p>
          <div className="flex items-center gap-2 mt-1.5">
            <StatusBadge level={municipality.riskLevel} />
          </div>
        </div>
      </div>

      {/* Key Metrics */}
      <div className="grid grid-cols-2 gap-2.5">
        <div className="inner-box px-3 py-3">
          <MetricLabel>Risk level score</MetricLabel>
          <div className="text-3xl font-extrabold mt-1 tracking-tight tabular-nums">{municipality.riskScore.toFixed(2)}</div>
          <div className="h-1.5 rounded-full mt-2 bg-muted overflow-hidden">
            <div
              className="h-full rounded-full transition-all"
              style={{ width: `${municipality.riskScore * 100}%`, backgroundColor: riskColor }}
            />
          </div>
        </div>
        <div className="inner-box px-3 py-3">
          <MetricLabel className="mb-1">Basis</MetricLabel>
          <p className="text-[10px] leading-snug text-muted-foreground line-clamp-4">{municipality.disaggregationLabel}</p>
        </div>
      </div>

      {/* Demographics */}
      <div className="inner-box px-3 py-2.5 space-y-2">
        <div className="flex items-center justify-between">
          <MetricLabel>Population</MetricLabel>
          <div className="text-[11px] font-bold tabular-nums">{municipality.population.toLocaleString()}</div>
        </div>
        <div className="flex items-center justify-between">
          <MetricLabel>Poverty rate</MetricLabel>
          <div className="text-[11px] font-bold tabular-nums">{municipality.povertyRate}%</div>
        </div>
      </div>

    </div>
  );
}

/* ─── Auto-fit text: shrinks font-size until it fits its box, never truncates ─── */
function FitText({
  text, className, maxSize = 30, minSize = 11,
}: { text: string; className?: string; maxSize?: number; minSize?: number }) {
  const ref = useRef<HTMLDivElement>(null);
  const [size, setSize] = useState(maxSize);

  useLayoutEffect(() => {
    const el = ref.current;
    if (!el) return;
    let s = maxSize;
    el.style.fontSize = `${s}px`;
    // Shrink until the real rendered text fits the real available width --
    // measured, not guessed from character count, which kept being wrong
    // for different digit widths and box sizes.
    while (el.scrollWidth > el.clientWidth && s > minSize) {
      s -= 1;
      el.style.fontSize = `${s}px`;
    }
    setSize(s);
  }, [text, maxSize, minSize]);

  return (
    <div ref={ref} className={`${className ?? ""} whitespace-nowrap`} style={{ fontSize: size }}>
      {text}
    </div>
  );
}

/* ─── Region summary chip ─── */
function SummaryChip({ label, value, color, tip }: { label: string; value: number | string; color: string; tip?: string }) {
  const box = "inner-box px-2 py-1.5 flex flex-col items-start";
  const figure = (
    <span className="font-mono-num text-base font-bold tabular-nums leading-none mt-0.5" style={{ color }}>
      {value}
    </span>
  );
  if (!tip) {
    return (
      <div className={box}>
        <MetricLabel className="whitespace-nowrap">{label}</MetricLabel>
        {figure}
      </div>
    );
  }
  // Dotted underline, as ConfidenceTag: this label has an explanation.
  return (
    <ExplainTip explanation={tip}>
      <button
        type="button"
        className={`${box} text-left cursor-help hover:bg-secondary/50 transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring`}
      >
        <MetricLabel className="whitespace-nowrap underline decoration-dotted underline-offset-2">{label}</MetricLabel>
        {figure}
      </button>
    </ExplainTip>
  );
}

/* ─── Trigger composition bar ─── */
export function TriggerCompositionBar({ provinceId, quarterId }: { provinceId: string | null; quarterId?: string }) {
  const scope = provinceId ? "province" : "region";
  const id = provinceId ?? "calabarzon";
  const { data, isLoading } = useExplainability(scope, id, quarterId || undefined);
  const triggers: Trigger[] = data?.triggers ?? [];

  return (
    <div>
      <div className="flex items-center gap-2 mb-2">
        <h3 className="text-[13px] font-semibold leading-tight">Trigger composition</h3>
      </div>
      {isLoading ? (
        <div className="animate-pulse">
          <div className="h-3 w-full rounded-md bg-secondary/40" />
          <div className="grid grid-cols-2 gap-x-3 gap-y-1.5 mt-2">
            {[0, 1, 2, 3].map((i) => (
              <div key={i} className="h-2.5 rounded bg-secondary/40" />
            ))}
          </div>
        </div>
      ) : (
      <>
      <div className="flex h-3 w-full rounded-md overflow-hidden border border-border/40">
        {triggers.map((t) => {
          const color = t.color === "red" ? "hsl(var(--risk-high))" : t.color === "green" ? "hsl(var(--risk-low))" : "hsl(var(--risk-moderate))";
          return (
            <div
              key={t.key}
              title={`${t.label} — ${t.pct}%`}
              style={{ width: `${t.pct}%`, background: color }}
              className="animate-bar-fill"
            />
          );
        })}
      </div>
      <div className="grid grid-cols-2 gap-x-3 gap-y-1 mt-2">
        {triggers.map((t) => {
          const color = t.color === "red" ? "hsl(var(--risk-high))" : t.color === "green" ? "hsl(var(--risk-low))" : "hsl(var(--risk-moderate))";
          return (
            <div key={t.key} className="flex items-center gap-1.5 text-[9px]">
              <span className="w-2 h-2 rounded-sm shrink-0" style={{ background: color }} />
              <span className="truncate text-muted-foreground">{t.label}</span>
              <span className="ml-auto font-mono-num font-bold tabular-nums text-foreground/90">
                {t.pct}%
              </span>
            </div>
          );
        })}
      </div>
      </>
      )}
    </div>
  );
}
