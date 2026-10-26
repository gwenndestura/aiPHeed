import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "@/components/ui/dialog";
import { History, ArrowRight } from "lucide-react";
import { Quarter } from "./QuarterTimeSlider";
import { useConfig, useTimeseries, useExplainability, useFinalArchive, useFinalRiskRows } from "@/lib/queries";
import { quarterOrdinal } from "@/lib/quarters";
import { isHighRisk } from "@/lib/risk";
import { StatusBadge } from "@/components/ui/status-badge";
import { formatSigned } from "@/components/ui/metric";

interface Props {
  open: boolean;
  onOpenChange: (v: boolean) => void;
  quarters: Quarter[];
  value: string;
  onSelect: (id: string) => void;
}

/**
 * Browse past (and current) quarterly forecasts. Rows carry the verified
 * regional risk index, band, quarter-over-quarter change and dominant
 * trigger. Selecting a row loads that quarter on the map.
 */
export function ForecastHistoryModal({ open, onOpenChange, quarters, value, onSelect }: Props) {
  // The newest quarter with a nowcast score (not the calendar quarter, which
  // may have no score yet).
  const cur = quarters.filter((q) => !q.forecast && !q.noData).pop();
  const { data: config } = useConfig();
  const { data: series } = useTimeseries("region", "calabarzon", undefined, undefined, "nowcast");
  const displayCutoff = config?.thresholds.riskDisplayCutoff ?? 0.5;

  const points = series?.series ?? [];
  const rows = points.slice().reverse(); // most recent first

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="z-[1200] max-w-2xl max-h-[85vh] overflow-y-auto">
        <DialogHeader>
          <div className="flex items-center gap-2">
            <History className="h-4 w-4 text-primary" />
            <DialogTitle className="text-sm">Forecast history</DialogTitle>
          </div>
          <DialogDescription className="text-[11px] leading-relaxed pt-1">
            Past quarterly risk forecasts for the region (walk-forward: each made with information published before its quarter began). The current quarter
            {cur ? ` (${cur.label} ${cur.year})` : ""} is the newest PSA has published data for.
            Select a row to load that quarter on the map.
          </DialogDescription>
        </DialogHeader>

        <div className="mt-3 overflow-x-auto">
          <table className="w-full text-[11px] border-collapse">
            <thead>
              <tr className="text-[9px] uppercase tracking-wider text-muted-foreground border-b border-border/50">
                <th className="text-left py-1.5 pr-3">Quarter</th>
                <th className="text-right px-2">Index</th>
                <th className="text-center px-2">Band</th>
                <th className="text-right px-2">QoQ</th>
                <th className="text-left px-2">Top driver</th>
                <th className="px-1" />
              </tr>
            </thead>
            <tbody>
              {rows.map((p, i) => {
                const prev = rows[i + 1]; // rows is reversed; the previous quarter is the next entry
                const q = quarters.find((qq) => qq.id === p.quarter);
                // A change is only quarter-on-quarter between adjacent nowcast
                // quarters: the forecast quarter is a different target and model,
                // and sits after a gap.
                const prevQ = prev ? quarters.find((qq) => qq.id === prev.quarter) : undefined;
                const comparable =
                  !!prev && !q?.forecast && !prevQ?.forecast &&
                  quarterOrdinal(p.quarter) - quarterOrdinal(prev.quarter) === 1;
                const delta = comparable ? p.riskScore - prev.riskScore : null;
                const band = isHighRisk(p.riskScore, displayCutoff) ? "HIGH" : "LOW";
                // Only quarters the slider offers are listed, so a selection
                // always lands on the timeline. QoQ above still compares
                // against the true previous quarter.
                if (!q) return null;
                const selected = p.quarter === value;
                return (
                  <HistoryRow
                    key={p.quarter}
                    quarterId={p.quarter}
                    label={q ? `${q.label} ${q.year}` : p.quarter}
                    isCurrent={!!cur && q.id === cur.id}
                    isForecast={!!q?.forecast}
                    score={p.riskScore}
                    band={band}
                    delta={delta}
                    selected={selected}
                    onSelect={() => onSelect(p.quarter)}
                  />
                );
              })}
            </tbody>
          </table>
        </div>

        <p className="mt-3 text-[9px] italic text-muted-foreground leading-snug">
          Regional value = mean of the 5 provincial risk probabilities. Quarter-over-quarter change is versus the
          preceding quarter. Risk classes, not measured hunger rates or official classifications.
        </p>

        <RiskArchive enabled={open} />
        <HungerArchive enabled={open} />
      </DialogContent>
    </Dialog>
  );
}

/**
 * The province risk forecasts per quarter against the observed class (Chapter I definition): the walk-forward
 * forecasts for the quarter starting on their issue date, and the forecasts issued 2026-10-01 (not yet scored).
 */
function RiskArchive({ enabled }: { enabled: boolean }) {
  const { data } = useFinalRiskRows(enabled);
  const rows = data?.rows ?? [];
  const byQ = new Map<string, typeof rows>();
  for (const r of rows) {
    if (r.kind === "retrospective" ? r.lead !== "1" : false) continue;
    byQ.set(r.quarter, [...(byQ.get(r.quarter) ?? []), r]);
  }
  const quarters = [...byQ.keys()].sort().reverse();
  if (!quarters.length) return null;
  return (
    <div className="mt-4">
      <p className="text-[11px] font-semibold">Province risk forecasts vs what happened</p>
      <p className="text-[10px] text-muted-foreground leading-snug pt-0.5">
        High-risk provinces forecast for each quarter (issued on its first day) and the high-risk provinces later
        observed from SWS hunger and PSA food prices. Rows marked Sealed are not yet scored.
      </p>
      <div className="mt-2 overflow-x-auto">
        <table className="w-full text-[11px] border-collapse">
          <thead>
            <tr className="text-[9px] uppercase tracking-wider text-muted-foreground border-b border-border/50">
              <th className="text-left py-1.5 pr-3">Quarter</th>
              <th className="text-left px-2">Issued</th>
              <th className="text-left px-2">Forecast high</th>
              <th className="text-left px-2">Observed high</th>
              <th className="text-right px-2">Correct</th>
            </tr>
          </thead>
          <tbody>
            {quarters.map((q) => {
              const rs = byQ.get(q) ?? [];
              const sealed = rs[0].kind === "forecast";
              const scored = rs.filter((r) => r.observed);
              const names = (f: (r: (typeof rs)[number]) => boolean) =>
                rs.filter(f).map((r) => r.province).join(", ") || "none";
              return (
                <tr key={q} className="border-b border-border/25">
                  <td className="py-2 pr-3 font-semibold whitespace-nowrap">
                    {q}
                    {sealed && (
                      <span className="ml-1.5 text-label font-normal text-ink-secondary">
                        Sealed · lead {rs[0].lead}
                        {rs[0].reliable_horizon ? "" : " (indicative)"}
                      </span>
                    )}
                  </td>
                  <td className="px-2 whitespace-nowrap text-muted-foreground">{rs[0].issue_date}</td>
                  <td className="px-2">{names((r) => r.class === "HIGH")}</td>
                  <td className="px-2">{scored.length ? names((r) => r.observed === "HIGH") : "—"}</td>
                  <td className="text-right px-2 font-mono-num tabular-nums">
                    {scored.length ? `${scored.filter((r) => r.class === r.observed).length}/${scored.length}` : "—"}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

/**
 * The LightGBM hunger forecasts for Balance Luzon (one quarter ahead), each against the SWS reading that later came
 * out. Retrospective rows were made walk-forward with data published before their issue date; prospective rows are
 * sealed and not yet scored.
 */
function HungerArchive({ enabled }: { enabled: boolean }) {
  const { data } = useFinalArchive("BL", enabled);
  const rows = (data?.rows ?? [])
    .filter((r) => r.lead === 1 && (r.kind.startsWith("retrospective") || r.model === "FIL-OA"))
    .sort((a, b) => b.target_quarter.localeCompare(a.target_quarter));
  if (!rows.length) return null;
  return (
    <div className="mt-4">
      <p className="text-[11px] font-semibold">Regional hunger level forecasts, Balance Luzon (SWS), one quarter ahead</p>
      <p className="text-[10px] text-muted-foreground leading-snug pt-0.5">
        LightGBM forecast vs the latest SWS reading at the time and the reading SWS later published (% of families).
        "Above avg." is the call that hunger will be above its past-year average.
      </p>
      <div className="mt-2 overflow-x-auto">
        <table className="w-full text-[11px] border-collapse">
          <thead>
            <tr className="text-[9px] uppercase tracking-wider text-muted-foreground border-b border-border/50">
              <th className="text-left py-1.5 pr-3">Target</th>
              <th className="text-left px-2">Issued</th>
              <th className="text-right px-2">LightGBM</th>
              <th className="text-right px-2">Latest</th>
              <th className="text-right px-2">Actual</th>
              <th className="text-left px-2">Above avg.</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => {
              const pending = r.actual_level === null;
              const call = r.forecast_elevated === 1 ? "Yes" : "No";
              const result = pending ? "pending" : r.forecast_elevated === r.actual_elevated ? "correct" : "wrong";
              return (
                <tr key={`${r.kind}-${r.target_quarter}`} className="border-b border-border/25">
                  <td className="py-2 pr-3 font-semibold whitespace-nowrap">
                    {r.target_quarter}
                    {pending && <span className="ml-1.5 text-label font-normal text-ink-secondary">Sealed</span>}
                  </td>
                  <td className="px-2 whitespace-nowrap text-muted-foreground">{r.issue_date}</td>
                  <td className="text-right px-2 font-mono-num tabular-nums">{r.forecast_level?.toFixed(1) ?? "—"}</td>
                  <td className="text-right px-2 font-mono-num tabular-nums">{r.persistence_level?.toFixed(1) ?? "—"}</td>
                  <td className="text-right px-2 font-mono-num tabular-nums">{pending ? "—" : r.actual_level?.toFixed(1)}</td>
                  <td className="px-2 whitespace-nowrap">
                    {call} <span className="text-muted-foreground">({result})</span>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      <p className="mt-2 text-[9px] italic text-muted-foreground leading-snug">{data?.note}</p>
    </div>
  );
}

function HistoryRow({
  quarterId,
  label,
  isCurrent,
  isForecast,
  score,
  band,
  delta,
  selected,
  onSelect,
}: {
  quarterId: string;
  label: string;
  isCurrent: boolean;
  isForecast: boolean;
  score: number;
  band: "HIGH" | "LOW";
  delta: number | null;
  selected: boolean;
  onSelect: () => void;
}) {
  const { data: explain } = useExplainability("region", "calabarzon", quarterId);
  const top = explain?.triggers?.[0];

  return (
    <tr
      onClick={onSelect}
      className={`border-b border-border/25 cursor-pointer transition-colors hover:bg-secondary/40 ${
        selected ? "bg-secondary/50" : ""
      }`}
    >
      <td className="py-2 pr-3 font-semibold whitespace-nowrap">
        {label}
        {isCurrent && <span className="ml-1.5 text-label font-normal text-ink-secondary">Current</span>}
        {isForecast && <span className="ml-1.5 text-label font-normal text-ink-secondary">Forecast</span>}
      </td>
      <td className="text-right px-2 font-mono-num tabular-nums">{score.toFixed(2)}</td>
      <td className="text-center px-2">
        <StatusBadge level={band === "HIGH" ? "high" : "low"} />
      </td>
      <td
        className={`text-right px-2 font-mono-num tabular-nums ${
          delta === null
            ? "text-muted-foreground"
            : delta > 0.001
              ? "text-risk-high"
              : delta < -0.001
                ? "text-risk-low"
                : "text-muted-foreground"
        }`}
        title={delta === null ? "Not comparable with the previous row" : undefined}
      >
        {delta === null ? "n/a" : formatSigned(delta, 2)}
      </td>
      <td className="px-2 whitespace-nowrap">
        {top?.label ?? "—"}{" "}
        {top && <span className="text-muted-foreground font-mono-num">{top.pct}%</span>}
      </td>
      <td className="px-1 text-right">
        <ArrowRight className="h-3 w-3 text-muted-foreground inline" />
      </td>
    </tr>
  );
}
