import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "@/components/ui/dialog";
import { History, ArrowRight } from "lucide-react";
import { Quarter } from "./QuarterTimeSlider";
import { useConfig, useTimeseries, useExplainability } from "@/lib/queries";

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
  const cur = quarters.find((q) => q.current);
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
            <DialogTitle className="text-sm">Forecast history — CALABARZON</DialogTitle>
          </div>
          <DialogDescription className="text-[11px] leading-relaxed pt-1">
            Past quarterly forecasts and their verified regional risk. The current quarter
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
                const delta = prev ? p.riskScore - prev.riskScore : 0;
                const band = p.riskScore >= displayCutoff ? "HIGH" : "LOW";
                const q = quarters.find((qq) => qq.id === p.quarter);
                const selected = p.quarter === value;
                return (
                  <HistoryRow
                    key={p.quarter}
                    quarterId={p.quarter}
                    label={q ? `${q.label} ${q.year}` : p.quarter}
                    isCurrent={!!q?.current}
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
          Regional index = mean of the 5 provincial forecasts. Quarter-over-quarter change is versus the
          preceding quarter. AI-generated estimates; not official food-insecurity classifications.
        </p>
      </DialogContent>
    </Dialog>
  );
}

function HistoryRow({
  quarterId,
  label,
  isCurrent,
  score,
  band,
  delta,
  selected,
  onSelect,
}: {
  quarterId: string;
  label: string;
  isCurrent: boolean;
  score: number;
  band: "HIGH" | "LOW";
  delta: number;
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
        {isCurrent && (
          <span className="ml-1.5 text-[8px] font-bold uppercase tracking-wider text-risk-low">now</span>
        )}
      </td>
      <td className="text-right px-2 font-mono-num tabular-nums">{score.toFixed(2)}</td>
      <td className="text-center px-2">
        <span
          className={`text-[9px] font-bold uppercase px-1.5 py-0.5 rounded-full ${
            band === "HIGH" ? "bg-risk-high/15 text-risk-high" : "bg-risk-low/15 text-risk-low"
          }`}
        >
          {band}
        </span>
      </td>
      <td
        className={`text-right px-2 font-mono-num tabular-nums ${
          delta > 0.001 ? "text-risk-high" : delta < -0.001 ? "text-risk-low" : "text-muted-foreground"
        }`}
      >
        {delta > 0 ? "+" : ""}
        {delta.toFixed(2)}
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
