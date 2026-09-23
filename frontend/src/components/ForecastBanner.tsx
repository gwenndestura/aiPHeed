import { Sparkles, CalendarCheck, AlertCircle, ShieldAlert } from "lucide-react";
import { Quarter } from "./QuarterTimeSlider";
import {
  PROVINCE_QUARTER_DATA,
  getQuarterMeta,
  getRiskLabel,
  isLimitedSignal,
  ALERT_THRESHOLD,
} from "@/data/quarterData";

interface Props {
  quarter: Quarter;
}

/**
 * Spec §1 — Forecast quarter banner + Region summary card
 * Shows: quarter, horizon ("3-month-ahead"), generated-on, verification by,
 * counts of HIGH / LOW / LIMITED_SIGNAL provinces, and active alert count.
 */
export function ForecastBanner({ quarter }: Props) {
  const meta = getQuarterMeta(quarter.id);

  let high = 0, low = 0, limited = 0, alerts = 0;
  PROVINCE_QUARTER_DATA.forEach((p) => {
    const score = p.scoresByQuarter[quarter.id] ?? 0;
    if (getRiskLabel(score) === "HIGH") high++; else low++;
    if (isLimitedSignal(p.id, quarter.id)) limited++;
    if (score >= ALERT_THRESHOLD) alerts++;
  });

  return (
    <div className="glass border border-border/50 rounded-xl shadow-lg px-3 py-2 flex items-center gap-3 text-[10px]">
      <div className="flex items-center gap-1.5 pr-3 border-r border-border/40">
        {quarter.forecast && <Sparkles className="h-3 w-3 text-primary" />}
        <div>
          <div className="font-mono-num font-bold text-foreground/95 leading-tight">
            {quarter.label} {quarter.year}
          </div>
          <div className="text-[8px] text-muted-foreground uppercase tracking-wider">
            {meta.horizonLabel}
          </div>
        </div>
      </div>

      <div className="hidden sm:flex items-center gap-1.5 pr-3 border-r border-border/40">
        <CalendarCheck className="h-3 w-3 text-muted-foreground" />
        <div className="leading-tight">
          <div className="text-[8px] text-muted-foreground uppercase tracking-wider">Generated</div>
          <div className="font-mono-num text-foreground/90">{meta.generatedOn}</div>
        </div>
      </div>

      <div className="hidden md:flex items-center gap-1.5 pr-3 border-r border-border/40">
        <div className="leading-tight">
          <div className="text-[8px] text-muted-foreground uppercase tracking-wider">Verifiable by</div>
          <div className="font-mono-num text-foreground/90">{meta.verificationBy}</div>
        </div>
      </div>

      {/* Region summary chips */}
      <div className="flex items-center gap-1.5">
        <span className="px-1.5 py-0.5 rounded-md bg-risk-high/15 text-risk-high font-bold tabular-nums font-mono-num">
          {high} HIGH
        </span>
        <span className="px-1.5 py-0.5 rounded-md bg-risk-low/15 text-risk-low font-bold tabular-nums font-mono-num">
          {low} LOW
        </span>
        {limited > 0 && (
          <span className="px-1.5 py-0.5 rounded-md bg-muted text-muted-foreground font-bold tabular-nums font-mono-num flex items-center gap-1" title="Province has < 5 geocoded articles (Algorithm Rule 5)">
            <AlertCircle className="h-2.5 w-2.5" />
            {limited} LIMITED
          </span>
        )}
        {alerts > 0 && (
          <span className="px-1.5 py-0.5 rounded-md bg-destructive text-destructive-foreground font-bold tabular-nums font-mono-num flex items-center gap-1 severe-pulse" title={`Active alerts (Risk Level ≥ ${ALERT_THRESHOLD})`}>
            <ShieldAlert className="h-2.5 w-2.5" />
            {alerts} ALERT
          </span>
        )}
      </div>
    </div>
  );
}
