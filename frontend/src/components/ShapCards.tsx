// The two approved cards, fed by the exact SHAP of the official FINAL forecast (/api/v1/final/shap/province).
//   ShapTopBars      left "Why is this at risk?": the original bar rows, top 5 inputs, "Other factors", then "See all".
//   ShapPlainSummary right card: 2-3 plain sentences for the public.
// Bar % = the input's share of the model's total input influence (absolute SHAP, log-odds), so the rows add up to 100%.
// Colour: the approved rule (trigger_color): above the red cut-off, red if it raises the risk and low-risk colour if it lowers it;
// smaller ones the moderate colour. No new colours.
import { useState } from "react";
import { Briefcase, CloudRain, Home, Landmark, Clock, Store, Utensils, Wheat } from "lucide-react";
import { useConfig } from "@/lib/queries";
import { useFinalShap, type ShapGroup } from "@/lib/finalShap";
import type { Trigger } from "@/lib/apiTypes";
import { Note } from "@/components/ui/note";
import { isLoadFailure, LOAD_ERROR_MESSAGE } from "@/lib/loadError";
import { OTHER_FACTORS_NOTE } from "@/lib/driverCopy";

const GROUP_ICON: Record<string, typeof Store> = {
  market: Store, climate: CloudRain, ag_production: Wheat, employment: Briefcase, household_economy: Landmark, poverty: Home, hunger: Utensils,
};

/** The approved trigger colour rule: above the red cut-off, red when it raises the risk, low-risk colour when it lowers it; else moderate. */
export function groupColour(g: ShapGroup, cutoff: number): "red" | "green" | "yellow" {
  return g.pct <= cutoff || g.direction === "no_effect" ? "yellow" : g.direction === "increases_risk" ? "red" : "green";
}
const CSS = { red: "hsl(var(--risk-high))", green: "hsl(var(--risk-low))", yellow: "hsl(var(--risk-moderate))" };

/** The groups as the approved Trigger shape, for the right panel's original factor cards. Key = label so the card title is the label. */
export function groupsAsTriggers(groups: ShapGroup[], cutoff: number): Trigger[] {
  return groups.map((g) => ({
    key: g.label, label: g.label, share: g.pct / 100, pct: g.pct, signedContribution: g.signedContribution, direction: g.direction,
    color: groupColour(g, cutoff), status: g.status, statusNote: "", evidenceNote: "", plainEvidence: g.plainEvidence, newsSignalProportion: null,
  }) as unknown as Trigger);
}

export function ShapTopBars({ id, quarterId }: { id: string; quarterId?: string }) {
  const [all, setAll] = useState(false);
  const { data, isLoading, error } = useFinalShap(id, quarterId);
  const { data: config } = useConfig();
  const cutoff = config?.thresholds.triggerRedCutoff ?? 20;
  if (isLoadFailure(error)) return <Note label={null}>{LOAD_ERROR_MESSAGE}</Note>;
  if (isLoading || !quarterId || !data) return <p className="text-[10px] text-muted-foreground">Loading…</p>;
  if (!data?.available) return <Note label={null}>{data?.reason ?? "No explanation is available for this quarter."}</Note>;
  const groups = data.groups ?? [];
  const shown = all ? groups : groups.slice(0, 5);
  const other = all ? (data.otherPct ?? 0) : Math.max(0, 100 - shown.reduce((s, g) => s + g.pct, 0));
  return (
    <div className="space-y-2" data-testid="shap-top-bars">
      {shown.map((g, i) => {
        const Icon = GROUP_ICON[g.key] ?? Clock;
        const color = CSS[groupColour(g, cutoff)];
        return (
          <div key={g.key} className="grid grid-cols-[18px_1fr_42px] items-center gap-2" title={g.plainEvidence}>
            <Icon className="h-3.5 w-3.5 text-muted-foreground" />
            <div>
              <div className="flex items-center justify-between text-[10px] mb-1">
                <span className="font-semibold">{g.label}</span>
              </div>
              <div className="h-2 bg-secondary/40 rounded-full overflow-hidden">
                <div className="h-full rounded-full animate-bar-fill"
                     style={{ animationDelay: `${i * 80}ms`, width: `${g.pct}%`, background: color, boxShadow: `0 0 6px ${color}80` }} />
              </div>
            </div>
            <span className="font-mono-num text-[10px] font-bold tabular-nums text-right" style={{ color }}>{g.pct}%</span>
          </div>
        );
      })}
      {other > 0 && (
        <div className="grid grid-cols-[18px_1fr_42px] items-center gap-2" title={OTHER_FACTORS_NOTE}>
          <span className="h-3.5 w-3.5" />
          <div>
            <div className="flex items-center justify-between text-[10px] mb-1">
              <span className="font-semibold text-muted-foreground">{all ? "Time since the last survey" : "Other factors"}</span>
            </div>
            <div className="h-2 bg-secondary/40 rounded-full overflow-hidden">
              <div className="h-full rounded-full bg-muted-foreground/50" style={{ width: `${other}%` }} />
            </div>
          </div>
          <span className="font-mono-num text-[10px] font-bold tabular-nums text-right text-muted-foreground">{other}%</span>
        </div>
      )}
      {groups.length > 5 && (
        <button onClick={() => setAll(!all)} className="text-[10px] font-semibold text-primary hover:underline" aria-expanded={all}>
          {all ? "Show top 5" : "See all"}
        </button>
      )}
    </div>
  );
}

export function ShapPlainSummary({ id, quarterId }: { id: string; quarterId?: string }) {
  const { data, isLoading } = useFinalShap(id, quarterId);
  if (isLoading || !data) return null;
  if (!data.available) return <p className="text-[11px] text-muted-foreground leading-relaxed">{data.reason}</p>;
  return (
    <div className="space-y-1.5" data-testid="shap-plain-summary">
      {(data.summary ?? []).map((s) => (
        <p key={s} className="text-[11px] text-foreground/85 leading-relaxed">{s}</p>
      ))}
    </div>
  );
}
