import { useLayoutEffect, useRef, useState } from "react";
import { RegionData, MunicipalityData, RISK_COLORS, RISK_LABELS } from "@/data/types";
import { X, TrendingUp, TrendingDown, BarChart3, ChevronRight, ArrowLeft, Briefcase, Plane, CloudRain, Store, AlertCircle, Info, Fish } from "lucide-react";
import { AboutModal } from "./AboutModal";
import { FeedbackModal } from "./FeedbackModal";
import { useCountUp } from "@/hooks/useCountUp";
import { useConfig, useExplainability, useForecast } from "@/lib/queries";
import type { Trigger } from "@/lib/apiTypes";

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
      <div className="shrink-0 border-t border-border/40 px-4 py-2.5 flex items-center justify-between gap-2 bg-card/60">
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
}: {
  quarterId?: string;
  quarterLabel?: string;
  regionsData: RegionData[];
}) {
  const { data: regionForecast } = useForecast("region", "calabarzon", quarterId || undefined, "nowcast");
  const avgScore = regionForecast?.riskScore ?? 0;
  const animScore = useCountUp(avgScore, 1000, 2);

  let high = 0, low = 0, limited = 0;
  regionsData.forEach((r) => {
    if (r.riskLevel === "high") high++;
    else low++;
    if (r.limitedSignal) limited++;
  });

  const band =
    animScore >= 0.5 ? { label: "HIGH", color: "hsl(var(--risk-high))" }
    : { label: "LOW", color: "hsl(var(--risk-low))" };

  // Position of pointer along 0..1 segmented track
  const trackPct = Math.min(Math.max(animScore, 0), 1) * 100;

  return (
    <div className="space-y-3">
      <div className="flex items-baseline justify-between gap-2">
        <p className="text-[9px] uppercase tracking-[0.22em] text-muted-foreground/80 font-semibold">
          CALABARZON — Regional Average Risk Level
        </p>
        {quarterLabel && (
          <p className="text-[9px] text-muted-foreground/70 font-mono-num tabular-nums shrink-0">{quarterLabel}</p>
        )}
      </div>

      <div
        className="relative rounded-2xl border border-border/40 bg-gradient-to-br from-secondary/35 via-card/60 to-background/40 px-5 pt-5 pb-4 overflow-hidden"
        style={{
          ['--accent-color' as any]: band.color.replace('hsl(', '').replace(')', ''),
          animation: 'rfii-hero-pulse 3.6s ease-in-out infinite',
        }}
      >
        {/* Aurora sweep */}
        <div
          className="pointer-events-none absolute -inset-[30%] opacity-50 blur-2xl"
          style={{
            background: `conic-gradient(from 0deg, transparent 0deg, ${band.color}55 90deg, transparent 180deg, ${band.color}33 270deg, transparent 360deg)`,
            animation: 'rfii-aurora 14s linear infinite',
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
            <span
              className="inline-block w-1.5 h-1.5 rounded-full"
              style={{ background: band.color, boxShadow: `0 0 10px ${band.color}, 0 0 20px ${band.color}aa` }}
            />
            <span className="text-[9px] uppercase tracking-[0.28em] text-muted-foreground/80 font-bold">
              Forecast Index
            </span>
          </div>

          {/* Hero score */}
          <div className="flex items-end gap-3">
            <span
              className="font-mono-num font-black tabular-nums leading-[0.85] tracking-tight"
              style={{
                fontSize: '5.5rem',
                color: band.color,
                textShadow: `0 0 32px ${band.color}cc, 0 0 70px ${band.color}66`,
                animation: 'rfii-score-breathe 3.2s ease-in-out infinite',
                transformOrigin: 'left bottom',
              }}
            >
              {animScore.toFixed(2)}
            </span>
            <span className="text-[10px] text-muted-foreground/70 font-mono-num pb-2">/ 1.00</span>
          </div>

          {/* Risk band pill */}
          <div className="mt-2.5">
            <span
              className="inline-flex items-center gap-1.5 text-[10px] font-bold uppercase tracking-[0.25em] px-3 py-1 rounded-full border"
              style={{
                background: `${band.color}1a`,
                color: band.color,
                borderColor: `${band.color}66`,
                boxShadow: `0 0 14px ${band.color}55`,
              }}
            >
              <span className="w-1 h-1 rounded-full" style={{ background: band.color, boxShadow: `0 0 6px ${band.color}` }} />
              {band.label} · risk
            </span>
          </div>

          <p className="mt-2.5 text-[10px] text-muted-foreground/85 leading-snug">
            Average across all {regionsData.length || 5} provinces
          </p>

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
              {/* Pointer */}
              <div
                className="absolute -top-1 -bottom-1 w-[3px] rounded-full"
                style={{
                  left: `calc(${trackPct}% - 1.5px)`,
                  background: 'hsl(var(--foreground))',
                  boxShadow: `0 0 10px ${band.color}, 0 0 20px ${band.color}cc`,
                  transition: 'left 1.4s cubic-bezier(0.22,1,0.36,1)',
                }}
              />
            </div>
            <div className="flex justify-between text-[8px] uppercase tracking-wider text-muted-foreground/60 font-mono-num mt-1.5">
              <span>0.0 low</span>
              <span>0.5</span>
              <span>1.0 high</span>
            </div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-3 gap-2">
        <SummaryChip label="HIGH" value={high} color="hsl(var(--risk-high))" />
        <SummaryChip label="LOW" value={low} color="hsl(var(--risk-low))" />
        <SummaryChip label="LIMITED" value={limited} color="hsl(var(--muted-foreground))" tip="Provinces with < 5 geocoded articles" />
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
  const { data, isLoading } = useExplainability(scope, id, quarterId || undefined);
  const drivers: Trigger[] = data?.triggers ?? [];

  return (
    <div key={`${provinceId ?? "region"}-${quarterId}`}>
      <div className="flex items-center gap-2 mb-3">
        <div className="w-1 h-4 rounded-full bg-primary" />
        <h3 className="text-[11px] font-bold uppercase tracking-wider">Why is this Province at Risk?</h3>
        <span className="text-[9px] text-muted-foreground/60 ml-auto">
          {isLoading ? "Computing…" : "Ranked"}
        </span>
      </div>
      {isLoading ? (
        <DriverRowsSkeleton />
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
}: {
  onRegionClick: (r: RegionData) => void;
  regionsData: RegionData[];
}) {
  const sortedProvinces = regionsData.slice().sort((a, b) => b.riskScore - a.riskScore);
  const maxScore = Math.max(...regionsData.map((r) => r.riskScore), 0.01);

  return (
    <div>
      <div className="flex items-center gap-2 mb-3">
        <div className="w-1 h-4 rounded-full bg-primary" />
        <h3 className="text-[11px] font-bold uppercase tracking-wider">Province Ranking</h3>
        <span className="text-[9px] text-muted-foreground/60 ml-auto">High → Low</span>
      </div>
      <div className="space-y-1.5">
        {sortedProvinces.map((r) => {
          const widthPct = (r.riskScore / maxScore) * 100;
          return (
            <button
              key={r.id}
              onClick={() => onRegionClick(r)}
              className="w-full text-left group px-1 py-1 rounded-md hover:bg-secondary/40 transition-colors"
            >
              <div className="flex items-center justify-between text-[10px] mb-1">
                <span className="font-semibold flex items-center gap-1.5">
                  <span
                    className="w-1.5 h-1.5 rounded-full"
                    style={{
                      backgroundColor: RISK_COLORS[r.riskLevel],
                      boxShadow: `0 0 6px ${RISK_COLORS[r.riskLevel]}`,
                    }}
                  />
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
              className="flex items-center gap-1.5 text-[10px] text-muted-foreground hover:text-foreground transition-colors group mb-2"
            >
              <ArrowLeft className="h-3 w-3 group-hover:-translate-x-0.5 transition-transform" />
              Back
            </button>
          )}
          <p className="text-[9px] uppercase tracking-widest text-muted-foreground/70 font-semibold">Province of</p>
          <h2 className="text-base font-bold leading-tight">{name}</h2>
        </div>
        {isLocked && onClose && (
          <button onClick={onClose} className="p-1.5 rounded-lg hover:bg-secondary transition-colors">
            <X className="h-4 w-4 text-muted-foreground" />
          </button>
        )}
      </div>
      <div className="rounded-xl border border-border/40 bg-secondary/20 px-4 py-8 flex flex-col items-center text-center space-y-2">
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
  const momPositive = region.momChange > 0;
  const qoqText = `${momPositive ? "+" : ""}${region.momChange}%`;
  const munis = municipalitiesData.slice().sort((a, b) => b.riskScore - a.riskScore);

  const displayCutoff = config?.thresholds.riskDisplayCutoff ?? 0.5;
  const alertThreshold = config?.thresholds.alertThreshold ?? 0.6;
  const limited = region.limitedSignal;
  const specLabel = region.riskScore >= displayCutoff ? "HIGH" : "LOW";
  const isActiveAlert = region.riskScore >= alertThreshold;
  const horizonLabel = config?.indicator.horizon ?? "same-quarter nowcast";

  return (
    <div className="px-5 py-4 space-y-4">
      {/* Header */}
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-start gap-3">
          <div>
            <p className="text-[9px] uppercase tracking-widest text-muted-foreground/70 font-semibold">Province of</p>
            <h2 className="text-base font-bold leading-tight">{region.name}</h2>
            <div className="flex flex-wrap items-center gap-1.5 mt-1.5">
              <span
                className="text-[9px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full font-mono-num"
                style={{ backgroundColor: `${riskColor}20`, color: riskColor }}
                title={`Forecast risk level (${displayCutoff.toFixed(2)} display cutoff)`}
              >
                {specLabel} · risk
              </span>
              {isActiveAlert && (
                <span className="text-[9px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full bg-destructive text-destructive-foreground severe-pulse" title={`Active alert: Risk Level ≥ ${alertThreshold}`}>
                  Active alert
                </span>
              )}
              {limited && (
                <span className="text-[9px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full bg-muted text-muted-foreground flex items-center gap-1" title="Province has fewer than the minimum geocoded articles">
                  <AlertCircle className="h-2.5 w-2.5" />
                  Limited signal
                </span>
              )}
              {!!region.seriesNeedingReview && (
                <span
                  className="text-[9px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full bg-muted text-muted-foreground flex items-center gap-1"
                  title={`${region.seriesNeedingReview} of ${region.seriesMonitored ?? "?"} monitored commodity series scored below the model's own confidence cutoff this quarter. They still count fully in the Risk Level Score above -- this flags them for analyst attention, it doesn't exclude them.`}
                >
                  <AlertCircle className="h-2.5 w-2.5" />
                  {region.seriesNeedingReview} need review
                </span>
              )}
            </div>
          </div>
        </div>
        {isLocked && (
          <button onClick={onClose} className="p-1.5 rounded-lg hover:bg-secondary transition-colors">
            <X className="h-4 w-4 text-muted-foreground" />
          </button>
        )}
      </div>

      {/* Confidence statement */}
      <div className="rounded-lg border border-border/40 bg-secondary/20 px-3 py-2 flex items-start gap-2">
        <Info className="h-3 w-3 text-primary mt-0.5 shrink-0" />
        <p className="text-[10px] text-muted-foreground leading-relaxed">
          This is a <b className="text-foreground">{horizonLabel}</b> estimate for{" "}
          <b className="text-foreground">{quarterId || "the selected quarter"}</b>, scored from PSA production
          data already published for that quarter.
        </p>
      </div>

      {/* Key Metrics */}
      <div className="grid grid-cols-2 gap-2.5">
        <div className="rounded-xl px-3 py-3 border border-border/50 bg-secondary/30">
          <div className="text-[8px] text-muted-foreground uppercase tracking-widest font-semibold">Risk Level Score</div>
          <div className="text-3xl font-extrabold mt-1 tracking-tight">{region.riskScore.toFixed(2)}</div>
          <div className="h-1.5 rounded-full mt-2 bg-muted overflow-hidden">
            <div className="h-full rounded-full transition-all" style={{ width: `${region.riskScore * 100}%`, backgroundColor: riskColor }} />
          </div>
        </div>
        <div className="rounded-xl px-3 py-3 border border-border/50 bg-secondary/30 overflow-hidden">
          <div className="flex items-center gap-1.5">
            {momPositive ? <TrendingUp className="h-3 w-3 text-destructive shrink-0" /> : <TrendingDown className="h-3 w-3 text-risk-low shrink-0" />}
            <span className="text-[8px] text-muted-foreground uppercase tracking-widest font-semibold">QoQ Change</span>
          </div>
          <FitText
            text={qoqText}
            className={`font-extrabold mt-1 tracking-tight ${momPositive ? "text-destructive" : "text-risk-low"}`}
            maxSize={30}
            minSize={11}
          />
        </div>
      </div>

      {/* Population */}
      <div className="rounded-xl px-3 py-2.5 border border-border/50 bg-secondary/30 flex items-center justify-between">
        <div>
          <div className="text-[8px] text-muted-foreground uppercase tracking-widest font-semibold">Population</div>
          <div className="text-sm font-bold mt-0.5 tabular-nums">{region.population.toLocaleString()}</div>
        </div>
        <BarChart3 className="h-4 w-4 text-muted-foreground/40" />
      </div>

      {/* Trigger composition */}
      <TriggerCompositionBar provinceId={region.id} quarterId={quarterId} />

      {/* Municipalities list */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <div className="w-1 h-4 rounded-full bg-primary" />
            <h3 className="text-[11px] font-bold uppercase tracking-wider">
              Cities & Municipalities
            </h3>
          </div>
          <span className="text-[9px] text-muted-foreground tabular-nums">{munis.length}</span>
        </div>
        <p className="text-[9px] text-muted-foreground/70 italic mb-2 leading-snug">
          Spatially disaggregated estimates derived from the validated province forecast.
        </p>
        <div className="space-y-1 max-h-[260px] overflow-y-auto pr-1">
          {munis.map((m) => (
            <button
              key={m.id}
              onClick={() => onMunicipalityClick(m)}
              className="w-full flex items-center justify-between bg-secondary/30 hover:bg-secondary/70 border border-border/40 hover:border-border rounded-lg px-2.5 py-2 transition-all text-left group"
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
                    {m.limitedSignal && (
                      <span className="px-1 rounded bg-muted text-muted-foreground text-[8px] font-bold uppercase tracking-wider" title="Limited signal, propagated from the province">
                        LIMITED
                      </span>
                    )}
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
        className="flex items-center gap-1.5 text-[10px] text-muted-foreground hover:text-foreground transition-colors group"
      >
        <ArrowLeft className="h-3 w-3 group-hover:-translate-x-0.5 transition-transform" />
        Back to {municipality.provinceName}
      </button>

      {/* Header */}
      <div className="flex items-start gap-3">
        <div>
          <p className="text-[9px] uppercase tracking-widest text-muted-foreground/70 font-semibold">
            {municipality.classification} of
          </p>
          <h2 className="text-base font-bold leading-tight">{municipality.name}</h2>
          <p className="text-[10px] text-muted-foreground mt-0.5">{municipality.provinceName}, CALABARZON</p>
          <div className="flex items-center gap-2 mt-1.5">
            <span
              className="text-[9px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full"
              style={{ backgroundColor: `${riskColor}20`, color: riskColor }}
            >
              {RISK_LABELS[municipality.riskLevel]}
            </span>
          </div>
        </div>
      </div>

      {/* Key Metrics */}
      <div className="grid grid-cols-2 gap-2.5">
        <div className="rounded-xl px-3 py-3 border border-border/50 bg-secondary/30">
          <div className="text-[8px] text-muted-foreground uppercase tracking-widest font-semibold">Risk Level Score</div>
          <div className="text-3xl font-extrabold mt-1 tracking-tight">{municipality.riskScore.toFixed(2)}</div>
          <div className="h-1.5 rounded-full mt-2 bg-muted overflow-hidden">
            <div
              className="h-full rounded-full transition-all"
              style={{ width: `${municipality.riskScore * 100}%`, backgroundColor: riskColor }}
            />
          </div>
        </div>
        <div className="rounded-xl px-3 py-3 border border-border/50 bg-secondary/30">
          <div className="text-[8px] text-muted-foreground uppercase tracking-widest font-semibold mb-1">Basis</div>
          <p className="text-[10px] leading-snug text-muted-foreground line-clamp-4">{municipality.disaggregationLabel}</p>
        </div>
      </div>

      {/* Demographics */}
      <div className="rounded-xl px-3 py-2.5 border border-border/50 bg-secondary/30 space-y-2">
        <div className="flex items-center justify-between">
          <div className="text-[8px] text-muted-foreground uppercase tracking-widest font-semibold">Population</div>
          <div className="text-[11px] font-bold tabular-nums">{municipality.population.toLocaleString()}</div>
        </div>
        <div className="flex items-center justify-between">
          <div className="text-[8px] text-muted-foreground uppercase tracking-widest font-semibold">Poverty Rate</div>
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
function SummaryChip({ label, value, color, tip }: { label: string; value: number; color: string; tip?: string }) {
  return (
    <div
      className="rounded-lg border border-border/40 bg-secondary/30 px-2 py-1.5 flex flex-col items-start"
      title={tip}
    >
      <span className="text-[8px] uppercase tracking-wider text-muted-foreground font-semibold">{label}</span>
      <span className="font-mono-num text-base font-bold tabular-nums leading-none mt-0.5" style={{ color }}>
        {value}
      </span>
    </div>
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
        <div className="w-1 h-4 rounded-full bg-primary" />
        <h3 className="text-[11px] font-bold uppercase tracking-wider">Trigger Composition</h3>
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
