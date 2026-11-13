import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "@/components/ui/dialog";
import { History } from "lucide-react";
import { Quarter } from "./QuarterTimeSlider";
import { useForecastHistory } from "@/lib/queries";
import { fmtPct } from "@/lib/risk";
import { StatusBadge } from "@/components/ui/status-badge";
import type { HistoryForecast } from "@/lib/apiTypes";

interface Props {
  open: boolean;
  onOpenChange: (v: boolean) => void;
  quarters: Quarter[];
  value: string;
  onSelect: (id: string) => void;
}

const qLabel = (q: string) => `${q.slice(5)} ${q.slice(0, 4)}`;
const day = (iso: string) => new Date(iso).toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric", timeZone: "Asia/Manila" });
const TARGET = { past: "ended", current: "this quarter", future: "ahead" } as const;

/**
 * Every forecast the system has issued (GET /api/v1/final/forecast-history), newest issue first. Forecasts are never replaced:
 * a later issue for the same quarter is listed separately, so the original stays visible. A forecast is marked validated
 * only when FNRI has published the province's result for that quarter; until then it is "awaiting outcome".
 * Selecting a row of the current issue loads that quarter on the map.
 */
export function ForecastHistoryModal({ open, onOpenChange, quarters, value, onSelect }: Props) {
  const { data, isLoading, error } = useForecastHistory(open);
  const onMap = new Set(quarters.map((q) => q.id));
  const byIssue = new Map<string, HistoryForecast[]>();
  for (const f of data?.forecasts ?? []) {
    if (!byIssue.has(f.issue_quarter)) byIssue.set(f.issue_quarter, []);
    byIssue.get(f.issue_quarter)!.push(f);
  }
  const issues = [...byIssue.keys()].sort().reverse();

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="z-[1200] max-w-2xl max-h-[85vh] overflow-y-auto">
        <DialogHeader>
          <div className="flex items-center gap-2">
            <History className="h-4 w-4 text-primary" />
            <DialogTitle className="text-sm">Forecast history</DialogTitle>
          </div>
          <DialogDescription className="text-[11px] leading-relaxed pt-1">
            Every forecast issued so far, newest first. Each is kept unchanged; any exception to the rule that a
            forecast uses only information published before its issue date is stated under that forecast. A forecast is checked against the actual result only when FNRI publishes a provincial survey for that
            quarter.
          </DialogDescription>
        </DialogHeader>

        {isLoading && <p className="mt-3 text-[11px] text-muted-foreground">Loading the forecast history…</p>}
        {error && <p className="mt-3 text-[11px] text-muted-foreground">The forecast history could not be loaded.</p>}
        {data && issues.length === 0 && <p className="mt-3 text-[11px] text-muted-foreground">No forecast has been issued yet.</p>}

        {issues.map((iq) => {
          const rows = byIssue.get(iq)!.slice().sort((a, b) => a.target_quarter.localeCompare(b.target_quarter) || a.province.localeCompare(b.province));
          const head = rows[0];
          const current = head.issue_status === "current issue";
          return (
            <section key={iq} className="mt-4" data-testid={`history-issue-${iq}`}>
              <div className="flex flex-wrap items-baseline gap-x-2 text-[11px]">
                <span className="font-semibold">Issued {qLabel(iq)}</span>
                <span className="text-muted-foreground">
                  {data?.issue_notes?.[iq]
                    ? <>data for periods before {day(head.information_cutoff)}, as published by {day(data.issue_notes[iq].published_by)}</>
                    : <>data published before {day(head.information_cutoff)}</>}{" "}
                  · made {day(head.generated_utc)} · model {head.model_version}
                </span>
                <span className="ml-auto text-[9px] font-bold uppercase tracking-wider text-muted-foreground">
                  {current ? "Current issue" : "Earlier issue"}
                </span>
              </div>
              {data?.issue_notes?.[iq] && (
                <p className="mt-1 text-[10px] leading-snug text-muted-foreground" data-testid={`history-note-${iq}`}>{data.issue_notes[iq].note}</p>
              )}
              <div className="mt-1.5 overflow-x-auto">
                <table className="w-full text-[11px] border-collapse">
                  <thead>
                    <tr className="text-[9px] uppercase tracking-wider text-muted-foreground border-b border-border/50">
                      <th className="text-left py-1.5 pr-3">Quarter</th>
                      <th className="text-left px-2">Province</th>
                      <th className="text-right px-2">Forecast share</th>
                      <th className="text-right px-2">Chance of High</th>
                      <th className="text-center px-2">Class</th>
                      <th className="text-left px-2">Actual result</th>
                    </tr>
                  </thead>
                  <tbody>
                    {rows.map((f) => {
                      const selectable = current && onMap.has(f.target_quarter);
                      return (
                        <tr
                          key={`${f.target_quarter}-${f.province}`}
                          onClick={selectable ? () => onSelect(f.target_quarter) : undefined}
                          className={`border-b border-border/25 ${selectable ? "cursor-pointer hover:bg-secondary/40" : ""} ${
                            selectable && f.target_quarter === value ? "bg-secondary/50" : ""}`}
                        >
                          <td className="py-1.5 pr-3 whitespace-nowrap">
                            {qLabel(f.target_quarter)} <span className="text-[9px] text-muted-foreground">({TARGET[f.target_status]})</span>
                          </td>
                          <td className="px-2">{f.province}</td>
                          <td className="px-2 text-right font-mono-num">{fmtPct(f.share_pct)}</td>
                          <td className="px-2 text-right font-mono-num">{f.p_high < 0.005 ? "<1%" : fmtPct(f.p_high * 100, 0)}</td>
                          <td className="px-2 text-center">
                            <StatusBadge level={f.risk_class === "HIGH" ? "high" : "low"} />
                          </td>
                          <td className="px-2 text-[10px]">
                            {f.withdrawn ? "withdrawn by an administrator" :
                              f.validation_status === "validated"
                                ? `${fmtPct(f.observed_share_pct ?? 0)} measured · ${f.correct ? "class correct" : "class wrong"}`
                                : "awaiting outcome"}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </section>
          );
        })}

        <p className="mt-4 text-[9px] italic text-muted-foreground leading-snug">
          Forecast share = forecast share of households moderately or severely food insecure (FNRI HFIAS); High risk at 50%. A forecast,
          not a measured rate or an official classification. {data?.ledger?.ok === false ? "Warning: the history file failed its integrity check." : ""}
        </p>
      </DialogContent>
    </Dialog>
  );
}
