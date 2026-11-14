import { useState } from "react";
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
const day = (iso: string) => new Date(iso).toLocaleDateString("en-GB", { day: "numeric", month: "long", year: "numeric", timeZone: "Asia/Manila" });

/**
 * Every forecast the system has issued (GET /api/v1/final/forecast-history), newest issue first. Forecasts are never changed;
 * a superseded issue is kept, collapsed, under the forecast that replaced it. Selecting a row of the current issue loads that
 * quarter on the map.
 */
export function ForecastHistoryModal({ open, onOpenChange, quarters, value, onSelect }: Props) {
  const { data, isLoading, error } = useForecastHistory(open);
  const [shown, setShown] = useState<Set<string>>(new Set());
  const onMap = new Set(quarters.map((q) => q.id));
  const byIssue = new Map<string, HistoryForecast[]>();
  for (const f of data?.forecasts ?? []) {
    if (!byIssue.has(f.issue_quarter)) byIssue.set(f.issue_quarter, []);
    byIssue.get(f.issue_quarter)!.push(f);
  }
  // newest issue first by its issue DATE (as text, "2026-Q4" would sort after the later "2026-11")
  const issueDate = (iq: string) => byIssue.get(iq)![0].issue_date ?? byIssue.get(iq)![0].information_cutoff;
  const issues = [...byIssue.keys()].sort((a, b) => issueDate(b).localeCompare(issueDate(a)));

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="z-[1200] max-w-2xl max-h-[85vh] overflow-y-auto">
        <DialogHeader>
          <div className="flex items-center gap-2">
            <History className="h-4 w-4 text-primary" />
            <DialogTitle className="text-sm">Forecast history</DialogTitle>
          </div>
          <DialogDescription className="text-[11px] leading-relaxed pt-1">
            All issued forecasts, newest first. A forecast is never changed after it is issued.
          </DialogDescription>
        </DialogHeader>

        {isLoading && <p className="mt-3 text-[11px] text-muted-foreground">Loading the forecast history…</p>}
        {error && <p className="mt-3 text-[11px] text-muted-foreground">The forecast history could not be loaded.</p>}
        {data && issues.length === 0 && <p className="mt-3 text-[11px] text-muted-foreground">No forecast has been issued yet.</p>}

        {issues.map((iq) => {
          const rows = byIssue.get(iq)!.slice().sort((a, b) => a.target_quarter.localeCompare(b.target_quarter) || a.province.localeCompare(b.province));
          const head = rows[0];
          const current = head.issue_status === "current issue";
          const superseded = head.issue_status === "superseded" || head.record_status === "superseded";
          const sup = data?.superseded?.[iq];
          const open_ = !superseded || shown.has(iq);
          return (
            <section key={iq} className="mt-4" data-testid={`history-issue-${iq}`}>
              <div className="flex flex-wrap items-baseline gap-x-2 text-[11px]">
                <span className={`font-semibold ${superseded ? "text-muted-foreground" : ""}`}>Issued {head.issue_label ?? qLabel(iq)}</span>
                <span className="text-muted-foreground">Data published before {day(head.information_cutoff)}</span>
                <span className="ml-auto text-[9px] font-bold uppercase tracking-wider text-muted-foreground">
                  {current ? "Current" : superseded ? "Superseded" : "Earlier issue"}
                </span>
              </div>
              {sup && (
                <p className="mt-1 text-[10px] leading-snug text-muted-foreground" data-testid={`history-superseded-${iq}`}>
                  Replaced by the forecast issued {sup.superseded_by_label}: it used data released after its cut-off.{" "}
                  <button
                    type="button"
                    className="underline hover:text-foreground"
                    onClick={() => setShown((s) => { const n = new Set(s); if (n.has(iq)) n.delete(iq); else n.add(iq); return n; })}
                  >
                    {open_ ? "Hide values" : "Show values"}
                  </button>
                </p>
              )}
              {open_ && (
                <div className={`mt-1.5 overflow-x-auto ${superseded ? "opacity-60" : ""}`}>
                  <table className="w-full text-[11px] border-collapse">
                    <thead>
                      <tr className="text-[9px] uppercase tracking-wider text-muted-foreground border-b border-border/50">
                        <th className="text-left py-1.5 pr-3">Quarter</th>
                        <th className="text-left px-2">Province</th>
                        <th className="text-right px-2">Forecast</th>
                        <th className="text-center px-2">Risk</th>
                        <th className="text-left px-2">Result</th>
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
                            <td className="py-1.5 pr-3 whitespace-nowrap">{qLabel(f.target_quarter)}</td>
                            <td className="px-2">{f.province}</td>
                            <td className="px-2 text-right font-mono-num">{fmtPct(f.risk_pct ?? f.share_pct)}</td>
                            <td className="px-2 text-center">
                              <StatusBadge level={f.risk_class === "HIGH" ? "high" : "low"} />
                            </td>
                            <td className="px-2 text-[10px]">
                              {f.withdrawn ? "Withdrawn" :
                                f.validation_status === "validated"
                                  ? `${fmtPct(f.observed_share_pct ?? 0)} measured (${f.correct ? "correct" : "incorrect"})`
                                  : "Pending"}
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              )}
            </section>
          );
        })}

        <p className="mt-4 text-[9px] text-muted-foreground leading-snug">
          Forecast: food insecurity risk (FNRI HFIAS); High risk at 50% or more. Results are
          added when FNRI publishes a provincial survey for that quarter.
          {data?.ledger?.ok === false ? " Warning: the history file failed its integrity check." : ""}
        </p>
      </DialogContent>
    </Dialog>
  );
}
